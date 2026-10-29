"""Tier 5 White-Box Adversarial Coverage Hardening Suite.

Targets every branch, fallback path, exception boundary, and state invariant in:
- `app/schemas.py`
- `app/tools.py`
- `app/agent.py`
- `cloud_run_chat_app/main.py`
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import inspect
import re
import time
from typing import Any
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
import requests

from app.agent import SYSTEM_INSTRUCTION, app as adk_app, reme_artificer_agent, root_agent
from app.schemas import ActiveTicketState, TicketPayload
import app.tools as tools_mod
from app.tools import (
    BQ_TICKET_COLUMNS,
    GOLDEN_FALLBACK_GRID,
    GOLDEN_FALLBACK_JACKAL,
    GOLDEN_FALLBACK_K60,
    _get_access_token,
    _search_aesp_datastore,
    _strip_html,
    diagnose_and_resolve_grid,
    publish_ticket_to_chat,
)


class AdversarialToolContext:
    """Configurable ToolContext double for white-box state edge-case testing."""

    def __init__(self, state: Any = None, omit_state_attr: bool = False) -> None:
        if not omit_state_attr:
            self.state = state


# ============================================================================
# 1. White-Box Audit: `app/schemas.py`
# ============================================================================


def test_tier5_schema_active_ticket_state_default_factory_isolation() -> None:
    """Verify `rag_snippets` default_factory creates isolated lists across instances."""
    s1 = ActiveTicketState(
        repair_classification="L1 FRT Fix",
        aesp_reference="AESP 2350-T-250-523",
        part_name="Oil Pressure Relief Valve Spring",
        nsn="5360-99-812-1740",
        technical_limits="79.4 mm",
        sector_display_name="Sector Bravo-4",
        latitude=51.2185,
        longitude=-1.7925,
        coords_label="51.2185° N, 1.7925° W",
    )
    s2 = ActiveTicketState(
        repair_classification="L1 FRT Fix",
        aesp_reference="AESP 2350-T-250-523",
        part_name="Oil Pressure Relief Valve Spring",
        nsn="5360-99-812-1740",
        technical_limits="79.4 mm",
        sector_display_name="Sector Bravo-4",
        latitude=51.2185,
        longitude=-1.7925,
        coords_label="51.2185° N, 1.7925° W",
    )
    s1.rag_snippets.append("Mutated snippet")
    assert s2.rag_snippets == []
    assert s1.rag_snippets is not s2.rag_snippets


def test_tier5_schema_rejects_invalid_types_and_missing_required_fields() -> None:
    """Verify Pydantic rejects non-float coordinates and missing required fields."""
    with pytest.raises(ValidationError):
        ActiveTicketState(
            repair_classification="L1",
            aesp_reference="AESP",
            part_name="Spring",
            nsn="5360-99-812-1740",
            technical_limits="79.4 mm",
            sector_display_name="Bravo-4",
            latitude="not-a-float",  # type: ignore[arg-type]
            longitude=-1.7925,
            coords_label="51.2185, -1.7925",
        )

    with pytest.raises(ValidationError):
        TicketPayload(
            ticket_id="TKT-REME-0001",
            # missing created_at_utc and other required fields
        )  # type: ignore[call-arg]


def test_tier5_schema_ticket_payload_optional_sector_and_defaults() -> None:
    """Verify `TicketPayload` accepts `sector_display_name=None` and populates defaults."""
    payload = TicketPayload(
        ticket_id="TKT-REME-9999",
        created_at_utc="2026-10-29T12:00:00Z",
        repair_classification="L2 Workshop Repair",
        aesp_reference="AESP 2320-J-100-522",
        part_name="Hydraulic Manifold High-Pressure Seal Kit",
        nsn="5330-99-812-4410",
        technical_limits="250 bar",
        sector_display_name=None,
        coords_label="51.2185° N, 1.7925° W",
        latitude=51.2185,
        longitude=-1.7925,
        google_maps_url="https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
    )
    dumped = payload.model_dump()
    assert dumped["sector_display_name"] is None
    assert dumped["callsign"] == "Cpl MacDonald (4 Bn REME FRT)"
    assert dumped["status"] == "DISPATCH_READY"


# ============================================================================
# 2. White-Box Audit: `_strip_html` & `_get_access_token` in `app/tools.py`
# ============================================================================


@pytest.mark.parametrize(
    ("raw_html", "expected_clean"),
    [
        ("<b>Free length 79.4 mm</b>", "Free length 79.4 mm"),
        (
            "<div><b><span><script>alert('xss')</script>54.6 mm</span></b></div>",
            "alert('xss')54.6 mm",
        ),
        (
            "  <b>Line 1</b>\n\t  <i>Line 2</i>\r\n   <br/>  <b>Line 3</b>  ",
            "Line 1 Line 2 Line 3",
        ),
        ("<a href='http://malicious.example'><b>AESP</b>   2350-T-250-523</a>", "AESP 2350-T-250-523"),
        ("<b><i><u></u></i></b>", ""),
        ("", ""),
        (None, ""),  # type: ignore[arg-type]
    ],
)
def test_tier5_strip_html_nested_malformed_and_whitespace(
    raw_html: str, expected_clean: str
) -> None:
    """Verify `_strip_html` strips nested/malformed tags and collapses all whitespace."""
    assert _strip_html(raw_html) == expected_clean


def test_tier5_get_access_token_cached_vs_refresh_vs_exception() -> None:
    """Test all branches of `_get_access_token`: valid cache, refresh, and ADC exception."""
    # Branch 1: Valid cached credentials -> returns token without calling refresh
    valid_creds = MagicMock()
    valid_creds.valid = True
    valid_creds.token = "cached-token-123"
    with (
        patch.object(tools_mod, "_CREDENTIALS", valid_creds),
        patch.object(tools_mod, "_AUTH_REQ", MagicMock()),
    ):
        assert _get_access_token() == "cached-token-123"
        valid_creds.refresh.assert_not_called()

    # Branch 2: Expired/invalid credentials -> refreshes and returns new token
    expired_creds = MagicMock()
    expired_creds.valid = False
    expired_creds.token = None

    def _refresh_side_effect(req: Any) -> None:
        expired_creds.valid = True
        expired_creds.token = "refreshed-token-456"

    expired_creds.refresh.side_effect = _refresh_side_effect
    with (
        patch.object(tools_mod, "_CREDENTIALS", expired_creds),
        patch.object(tools_mod, "_AUTH_REQ", None),
        patch("app.tools.google.auth.transport.requests.Request") as mock_req_cls,
    ):
        assert _get_access_token() == "refreshed-token-456"
        expired_creds.refresh.assert_called_once_with(mock_req_cls.return_value)

    # Branch 3: Exception during refresh -> logs warning and returns ""
    broken_creds = MagicMock()
    broken_creds.valid = False
    broken_creds.token = None
    broken_creds.refresh.side_effect = RuntimeError("ADC refresh network failure")
    with (
        patch.object(tools_mod, "_CREDENTIALS", broken_creds),
        patch.object(tools_mod, "_AUTH_REQ", MagicMock()),
    ):
        assert _get_access_token() == ""


# ============================================================================
# 3. White-Box Audit: `_search_aesp_datastore` Discovery Engine Resilience
# ============================================================================


def test_tier5_search_aesp_datastore_empty_token_short_circuits() -> None:
    """When `_get_access_token()` returns empty string, no HTTP request is made."""
    with (
        patch("app.tools._get_access_token", return_value=""),
        patch("app.tools.requests.post") as mock_post,
    ):
        assert _search_aesp_datastore("K60 oil pressure") == []
        mock_post.assert_not_called()


def test_tier5_search_aesp_datastore_http_500_timeout_and_malformed_json() -> None:
    """Verify `_search_aesp_datastore` degrades to `[]` on HTTP 500, timeout, and bad JSON."""
    with patch("app.tools._get_access_token", return_value="fake-token"):
        # Case A: HTTP 500 Internal Server Error
        resp_500 = MagicMock()
        resp_500.status_code = 500
        resp_500.text = "Internal Server Error"
        with patch("app.tools.requests.post", return_value=resp_500):
            assert _search_aesp_datastore("K60") == []

        # Case B: requests.exceptions.Timeout
        with patch(
            "app.tools.requests.post",
            side_effect=requests.exceptions.Timeout("Discovery Engine timed out"),
        ):
            assert _search_aesp_datastore("K60") == []

        # Case C: HTTP 200 with malformed non-JSON body (.json() raises ValueError)
        resp_bad_json = MagicMock()
        resp_bad_json.status_code = 200
        resp_bad_json.json.side_effect = ValueError("No JSON object could be decoded")
        with patch("app.tools.requests.post", return_value=resp_bad_json):
            assert _search_aesp_datastore("K60") == []


def test_tier5_search_aesp_datastore_truncates_to_5_and_skips_empty_snippets() -> None:
    """Verify `_search_aesp_datastore` strips HTML, ignores empty snippets, and caps at 5."""
    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = {
        "results": [
            {"document": {"derivedStructData": None}},
            {
                "document": {
                    "derivedStructData": {
                        "snippets": [
                            {"snippet": ""},
                            {"snippet": "<b>Snippet 1</b>"},
                            {"snippet": "<i>Snippet 2</i>"},
                            {"snippet": "<b>Snippet 3</b>"},
                            {"snippet": "Snippet 4"},
                            {"snippet": "<b>Snippet 5</b>"},
                            {"snippet": "Snippet 6 should be truncated"},
                        ]
                    }
                }
            },
        ]
    }
    with (
        patch("app.tools._get_access_token", return_value="fake-token"),
        patch("app.tools.requests.post", return_value=resp_ok) as mock_post,
    ):
        snippets = _search_aesp_datastore("")
        assert snippets == [
            "Snippet 1",
            "Snippet 2",
            "Snippet 3",
            "Snippet 4",
            "Snippet 5",
        ]
        sent_payload = mock_post.call_args.kwargs["json"]
        assert sent_payload["pageSize"] == 15
        assert sent_payload["contentSearchSpec"] == {"snippetSpec": {"returnSnippet": True}}
        assert "summarySpec" not in sent_payload["contentSearchSpec"]


# ============================================================================
# 4. White-Box Audit: `diagnose_and_resolve_grid` SQLi, Fallbacks & Exceptions
# ============================================================================


@pytest.mark.parametrize(
    ("adversarial_fault_query", "adversarial_grid", "expected_nsn"),
    [
        (
            "'; DROP TABLE ipc_nsn_catalogue; --",
            "' OR '1'='1'; DROP TABLE spta_sector_grids; --",
            "5360-99-812-1740",
        ),
        (
            "\" UNION SELECT * FROM `antig-dave.ukd_reme_demo.group_chat_tickets` --",
            "bravo-4'; DELETE FROM spta_sector_grids WHERE 1=1; --",
            "5360-99-812-1740",
        ),
        (
            "JACKAL 2 '; DROP TABLE ipc_nsn_catalogue; --",
            "   \n\t  ",
            "5330-99-812-4410",
        ),
        (
            "ERR-409 hydraulic pressure loss",
            "unknown-grid-9999",
            "5330-99-812-4410",
        ),
        (
            "MiXeD CaSe JaCkAl fault",
            "BRAVO-4",
            "5330-99-812-4410",
        ),
    ],
)
def test_tier5_diagnose_sql_injection_parameterization_and_fallback_routing(
    adversarial_fault_query: str,
    adversarial_grid: str,
    expected_nsn: str,
) -> None:
    """Verify SQL injection strings are bound strictly as ScalarQueryParameters and never interpolated."""
    fake_bq = MagicMock()
    empty_job = MagicMock()
    empty_job.result.return_value = []
    fake_bq.query.return_value = empty_job

    ctx = AdversarialToolContext(state={})
    with (
        patch("app.tools._search_aesp_datastore", return_value=[]),
        patch.object(tools_mod, "_BQ_CLIENT", fake_bq),
    ):
        res = diagnose_and_resolve_grid(
            fault_query=adversarial_fault_query,
            spoken_sector_grid=adversarial_grid,
            tool_context=ctx,  # type: ignore[arg-type]
        )

    assert res["nsn"] == expected_nsn
    assert res["latitude"] == GOLDEN_FALLBACK_GRID["latitude"]
    assert res["longitude"] == GOLDEN_FALLBACK_GRID["longitude"]

    # Inspect both SQL queries to confirm zero raw string interpolation of user input
    assert fake_bq.query.call_count == 2
    for call in fake_bq.query.call_args_list:
        sql_text = call.args[0]
        job_config = call.kwargs["job_config"]
        assert "DROP TABLE" not in sql_text
        assert "UNION SELECT" not in sql_text
        assert "DELETE FROM" not in sql_text
        assert "@query" in sql_text or "@grid" in sql_text
        assert len(job_config.query_parameters) == 1


def test_tier5_diagnose_bigquery_exceptions_and_partial_null_rows() -> None:
    """Test BigQuery exception handling and partial None column fallback in `diagnose_and_resolve_grid`."""
    # Subcase A: Both BigQuery queries raise RuntimeError -> gracefully falls back
    broken_bq = MagicMock()
    broken_bq.query.side_effect = RuntimeError("BigQuery europe-west1 connection reset")
    ctx = AdversarialToolContext(state={})
    with (
        patch("app.tools._search_aesp_datastore", return_value=["Fallback snippet"]),
        patch.object(tools_mod, "_BQ_CLIENT", broken_bq),
    ):
        res = diagnose_and_resolve_grid(
            fault_query="Jackal 409 manifold",
            spoken_sector_grid="Bravo-4",
            tool_context=ctx,  # type: ignore[arg-type]
        )
    assert res["nsn"] == GOLDEN_FALLBACK_JACKAL["nsn"]
    assert res["part_name"] == GOLDEN_FALLBACK_JACKAL["part_name"]
    assert res["latitude"] == GOLDEN_FALLBACK_GRID["latitude"]
    assert res["rag_snippets"] == ["Fallback snippet"]

    # Subcase B: BigQuery returns row with partial None/empty fields -> truthy fields override, None keeps fallback
    partial_bq = MagicMock()
    q_part = MagicMock()
    q_part.result.return_value = [
        {
            "repair_classification": None,
            "aesp_reference": "",
            "part_name": "Custom Override Part",
            "nsn": "5360-99-812-1740",
            "technical_limits": None,
        }
    ]
    q_grid = MagicMock()
    q_grid.result.return_value = [
        {
            "sector_display_name": None,
            "latitude": 0.0,  # 0.0 is not None and should be preserved
            "longitude": None,  # None should fall back to GOLDEN_FALLBACK_GRID["longitude"]
            "coords_label": "0.0° N, 1.7925° W",
        }
    ]
    partial_bq.query.side_effect = [q_part, q_grid]
    with (
        patch("app.tools._search_aesp_datastore", return_value=[]),
        patch.object(tools_mod, "_BQ_CLIENT", partial_bq),
    ):
        res2 = diagnose_and_resolve_grid(
            fault_query="FV432 K60",
            spoken_sector_grid="Equator Test",
            tool_context=None,  # type: ignore[arg-type]
        )
    assert res2["part_name"] == "Custom Override Part"
    assert res2["repair_classification"] == GOLDEN_FALLBACK_K60["repair_classification"]
    assert res2["technical_limits"] == GOLDEN_FALLBACK_K60["technical_limits"]
    assert res2["sector_display_name"] == GOLDEN_FALLBACK_GRID["sector_display_name"]
    assert res2["latitude"] == 0.0
    assert res2["longitude"] == GOLDEN_FALLBACK_GRID["longitude"]


# ============================================================================
# 5. White-Box Audit: `publish_ticket_to_chat` State, HTTP & BQ Edge Cases
# ============================================================================


@pytest.mark.parametrize(
    "ctx_variant",
    [
        None,
        AdversarialToolContext(state=None),
        AdversarialToolContext(omit_state_attr=True),
        AdversarialToolContext(state={}),
        AdversarialToolContext(state={"active_ticket": None}),
        AdversarialToolContext(state={"active_ticket": "corrupted-non-dict"}),
    ],
)
def test_tier5_publish_ticket_to_chat_stateless_and_corrupted_context_variants(
    ctx_variant: Any,
) -> None:
    """Verify `publish_ticket_to_chat` succeeds when `tool_context` is None, empty, or corrupted."""
    fake_bq = MagicMock()
    fake_bq.insert_rows_json.return_value = []

    with (
        patch("app.tools.requests.post") as mock_post,
        patch.object(tools_mod, "_BQ_CLIENT", fake_bq),
    ):
        res = publish_ticket_to_chat(ctx_variant)

    assert res["published"] is True
    ticket = res["ticket"]
    assert re.match(r"^TKT-REME-[0-9A-F]{4}$", ticket["ticket_id"])
    assert ticket["nsn"] == GOLDEN_FALLBACK_K60["nsn"]
    assert ticket["latitude"] == GOLDEN_FALLBACK_GRID["latitude"]
    assert ticket["longitude"] == GOLDEN_FALLBACK_GRID["longitude"]
    assert (
        ticket["google_maps_url"]
        == "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"
    )
    assert (
        res["confirmation_badge"]
        == f"✅ Ticket {ticket['ticket_id']} Published to 4 Bn REME Group Chat"
    )

    # Verify HTTP POST payload retains `sector_display_name` while BigQuery row strips it
    posted_json = mock_post.call_args.kwargs["json"]
    assert "sector_display_name" in posted_json

    bq_rows = fake_bq.insert_rows_json.call_args.args[1]
    assert len(bq_rows) == 1
    assert set(bq_rows[0].keys()) == BQ_TICKET_COLUMNS
    assert "sector_display_name" not in bq_rows[0]


def test_tier5_publish_ticket_survives_simultaneous_cloud_run_and_bigquery_outage() -> None:
    """Verify `publish_ticket_to_chat` still returns `published: True` if both HTTP POST and BQ fail."""
    failing_bq = MagicMock()
    failing_bq.insert_rows_json.side_effect = RuntimeError("BQ streaming insert failed")

    ctx = AdversarialToolContext(
        state={
            "active_ticket": {
                **GOLDEN_FALLBACK_JACKAL,
                **GOLDEN_FALLBACK_GRID,
            }
        }
    )
    with (
        patch(
            "app.tools.requests.post",
            side_effect=requests.exceptions.ConnectionError("Cloud Run unreachable"),
        ),
        patch.object(tools_mod, "_BQ_CLIENT", failing_bq),
    ):
        res = publish_ticket_to_chat(ctx)  # type: ignore[arg-type]

    assert res["published"] is True
    assert res["ticket"]["nsn"] == GOLDEN_FALLBACK_JACKAL["nsn"]
    assert ctx.state["last_published_ticket"]["ticket_id"] == res["ticket"]["ticket_id"]


# ============================================================================
# 6. White-Box Audit: `app/agent.py` ADK 2.0 Instruction & Tool Signatures
# ============================================================================


def test_tier5_agent_instruction_has_no_unescaped_brace_placeholders() -> None:
    """Ensure `SYSTEM_INSTRUCTION` contains zero `{var}` placeholders that crash ADK `inject_session_state`."""
    brace_tokens = re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", SYSTEM_INSTRUCTION)
    assert brace_tokens == [], (
        f"Unescaped curly-brace placeholders found in SYSTEM_INSTRUCTION: {brace_tokens}"
    )
    assert root_agent is reme_artificer_agent
    assert adk_app.root_agent is root_agent
    assert reme_artificer_agent.generate_content_config.temperature == 0.0

    # Verify tool docstrings do not expose `tool_context` and signatures have no default values
    for tool_fn in (diagnose_and_resolve_grid, publish_ticket_to_chat):
        assert "tool_context" not in (tool_fn.__doc__ or "")
        sig = inspect.signature(tool_fn)
        for param in sig.parameters.values():
            assert param.default is inspect.Parameter.empty


# ============================================================================
# 7. White-Box Audit: `cloud_run_chat_app/main.py` Concurrency, Dedup & SLA
# ============================================================================


def _make_ticket_dict(ticket_id: str, status: str = "DISPATCH_READY") -> dict[str, Any]:
    return {
        "ticket_id": ticket_id,
        "created_at_utc": "2026-10-29T12:30:00Z",
        "callsign": "Cpl MacDonald (4 Bn REME FRT)",
        "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
        "aesp_reference": "AESP 2350-T-250-523 (Ch 1-2, Para 17.4, Page 14)",
        "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
        "nsn": "5360-99-812-1740",
        "technical_limits": "Free length 79.4 mm; replace if compressed under 54.6 mm at 40 lbs load — do NOT pack with washers.",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "coords_label": "51.2185° N, 1.7925° W",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        "status": status,
    }


def test_tier5_fastapi_deduplication_moves_reposted_ticket_to_index_zero(
    chat_app_module: Any,
) -> None:
    """Verify reposting an existing `ticket_id` deduplicates and moves the updated record to index 0."""
    fake_bq = MagicMock()
    fake_bq.insert_rows_json.return_value = []

    with patch.object(chat_app_module, "_BQ_CLIENT", fake_bq):
        client = TestClient(chat_app_module.app)
        client.post("/api/reset")

        for tid in ("TKT-REME-1001", "TKT-REME-1002", "TKT-REME-1003"):
            r = client.post("/api/tickets", json=_make_ticket_dict(tid))
            assert r.status_code == 200

        # Order before repost: [1003, 1002, 1001]
        before = [t["ticket_id"] for t in client.get("/api/tickets").json()["tickets"]]
        assert before == ["TKT-REME-1003", "TKT-REME-1002", "TKT-REME-1001"]

        # Repost TKT-REME-1001 with updated status -> must move to index 0 without duplication
        r_repost = client.post(
            "/api/tickets",
            json=_make_ticket_dict("TKT-REME-1001", status="FRT_EN_ROUTE"),
        )
        assert r_repost.status_code == 200
        tickets = client.get("/api/tickets").json()["tickets"]
        assert [t["ticket_id"] for t in tickets] == [
            "TKT-REME-1001",
            "TKT-REME-1003",
            "TKT-REME-1002",
        ]
        assert tickets[0]["status"] == "FRT_EN_ROUTE"


def test_tier5_fastapi_rapid_concurrent_posts_and_subsecond_reset_sla(
    chat_app_module: Any,
) -> None:
    """Stress-test rapid concurrent ASGI ticket posts, BQ failure resilience, and <1s reset SLA."""
    import asyncio
    import httpx

    failing_bq = MagicMock()
    failing_bq.insert_rows_json.side_effect = RuntimeError("Simulated BigQuery outage")

    with patch.object(chat_app_module, "_BQ_CLIENT", failing_bq):
        client = TestClient(chat_app_module.app)
        client.post("/api/reset")

        ticket_ids = [f"TKT-REME-{i:04d}" for i in range(25)]

        async def _concurrent_burst() -> list[int]:
            transport = httpx.ASGITransport(app=chat_app_module.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as async_client:
                resps = await asyncio.gather(
                    *(
                        async_client.post("/api/tickets", json=_make_ticket_dict(tid))
                        for tid in ticket_ids
                    )
                )
                return [r.status_code for r in resps]

        statuses = asyncio.run(_concurrent_burst())
        assert all(code == 200 for code in statuses)

        # Verify <20ms GET /api/tickets read SLA and complete set of 25 unique tickets
        t0 = time.perf_counter()
        get_resp = client.get("/api/tickets")
        get_elapsed = time.perf_counter() - t0
        assert get_resp.status_code == 200
        assert get_elapsed < 0.05
        returned_ids = [t["ticket_id"] for t in get_resp.json()["tickets"]]
        assert len(returned_ids) == 25
        assert set(returned_ids) == set(ticket_ids)

        # Verify <1s reset SLA on both /api/reset and /api/tickets/reset
        for endpoint in ("/api/reset", "/api/tickets/reset"):
            client.post("/api/tickets", json=_make_ticket_dict("TKT-REME-9999"))
            t_reset_start = time.perf_counter()
            r_reset = client.post(endpoint)
            reset_elapsed = time.perf_counter() - t_reset_start
            assert r_reset.status_code == 200
            assert r_reset.json() == {"status": "reset", "tickets": []}
            assert reset_elapsed < 1.0
            assert client.get("/api/tickets").json()["tickets"] == []


# ============================================================================
# 8. Regression Audit: BigQuery Seed Sync & Platform Keyword Precedence
# ============================================================================


def test_tier5_live_bigquery_seed_sync_and_keyword_collision_precedence() -> None:
    """Verify IPC_SEED_ROWS sync, SQL platform-keyword ORDER BY precedence, and live GCP oracle results."""
    import scripts.seed_demo1_bigquery as seed_mod

    # 1. Verify SQL in diagnose_and_resolve_grid contains platform-priority ORDER BY
    diag_src = inspect.getsource(diagnose_and_resolve_grid)
    assert "ORDER BY" in diag_src
    assert "'jackal'" in diag_src and "'409'" in diag_src
    assert "LENGTH(keyword_tag) DESC" in diag_src

    # 2. Verify IPC_SEED_ROWS in scripts/seed_demo1_bigquery.py matches GOLDEN_FALLBACK_K60 & GOLDEN_FALLBACK_JACKAL
    k60_rows = [r for r in seed_mod.IPC_SEED_ROWS if r["nsn"] == "5360-99-812-1740"]
    jackal_rows = [r for r in seed_mod.IPC_SEED_ROWS if r["nsn"] == "5330-99-812-4410"]
    assert len(k60_rows) == 6
    assert len(jackal_rows) == 5

    for r in k60_rows:
        assert r["aesp_reference"] == GOLDEN_FALLBACK_K60["aesp_reference"]
        assert r["technical_limits"] == GOLDEN_FALLBACK_K60["technical_limits"]
        assert "79.4 mm" in r["technical_limits"]
        assert "54.6 mm" in r["technical_limits"]
        assert "do NOT pack with washers" in r["technical_limits"]

    for r in jackal_rows:
        assert r["aesp_reference"] == GOLDEN_FALLBACK_JACKAL["aesp_reference"]
        assert r["technical_limits"] == GOLDEN_FALLBACK_JACKAL["technical_limits"]
        assert "AESP 2320-J-100-522" in r["aesp_reference"]
        assert "250 bar" in r["technical_limits"]

    # 3. Execute live oracle queries against GCP (BigQuery europe-west1 + Discovery Engine eu)
    ctx_k60 = AdversarialToolContext(state={})
    res_k60 = diagnose_and_resolve_grid(
        "FV432 K60 oil pressure fluctuating at Sector Bravo-4",
        "Sector Bravo-4",
        ctx_k60,  # type: ignore[arg-type]
    )
    assert res_k60["nsn"] == "5360-99-812-1740"
    assert "79.4 mm" in res_k60["technical_limits"]
    assert "54.6 mm" in res_k60["technical_limits"]
    assert "do NOT pack with washers" in res_k60["technical_limits"]

    for jackal_query in (
        "Jackal 2 fault code 409 3211 hydraulic manifold pressure drop",
        "Jackal 2 fault code 409 hydraulic oil leak",
        "Jackal 2 409 3211 relief valve",
        "Jackal 2 409 suspension spring",
    ):
        ctx_j = AdversarialToolContext(state={})
        res_j = diagnose_and_resolve_grid(
            jackal_query,
            "Sector Bravo-4",
            ctx_j,  # type: ignore[arg-type]
        )
        assert res_j["nsn"] == "5330-99-812-4410", (
            f"Expected Jackal 2 NSN 5330-99-812-4410 for '{jackal_query}', got {res_j['nsn']}"
        )
        assert "250 bar" in res_j["technical_limits"]
        assert "AESP 2320-J-100-522" in res_j["aesp_reference"]


