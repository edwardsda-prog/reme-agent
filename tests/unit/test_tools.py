"""Unit tests for ADK 2.0 tools in app/tools.py."""

from unittest.mock import MagicMock, patch

import app.tools as tools_mod
from app.agent import reme_artificer_agent, root_agent
from app.tools import (
    BQ_TICKET_COLUMNS,
    _strip_html,
    diagnose_and_resolve_grid,
    publish_ticket_to_chat,
)


class DummyToolContext:
    def __init__(self, initial_state: dict | None = None):
        self.state = dict(initial_state or {})


def test_strip_html_removes_tags_and_normalizes_whitespace():
    raw = "<b>AESP 2350-T-250-523</b>   Para 17.4:  <i>Free length 79.4 mm</i>"
    assert _strip_html(raw) == "AESP 2350-T-250-523 Para 17.4: Free length 79.4 mm"


def test_agent_definition_contract():
    assert root_agent.name == "reme_artificer_agent"
    assert reme_artificer_agent.model == "gemini-2.5-flash"
    tool_names = [t.__name__ for t in reme_artificer_agent.tools]
    assert "diagnose_and_resolve_grid" in tool_names
    assert "publish_ticket_to_chat" in tool_names


@patch("app.tools._search_aesp_datastore")
def test_diagnose_and_resolve_grid_fallback_k60(mock_search):
    mock_search.return_value = []
    ctx = DummyToolContext()
    with patch.object(tools_mod, "_BQ_CLIENT", None):
        res = diagnose_and_resolve_grid(
            fault_query="FV432 Bulldog K60 low oil pressure relief valve spring",
            spoken_sector_grid="Bravo-4",
            tool_context=ctx,
        )

    assert res["nsn"] == "5360-99-812-1740"
    assert "L1 FRT Fix" in res["repair_classification"]
    assert abs(res["latitude"] - 51.2185) < 0.0001
    assert abs(res["longitude"] - (-1.7925)) < 0.0001
    assert "active_ticket" in ctx.state
    assert ctx.state["active_ticket"]["nsn"] == "5360-99-812-1740"


@patch("app.tools._search_aesp_datastore")
def test_diagnose_and_resolve_grid_fallback_jackal_level2(mock_search):
    mock_search.return_value = []
    ctx = DummyToolContext()
    with patch.object(tools_mod, "_BQ_CLIENT", None):
        res = diagnose_and_resolve_grid(
            fault_query="Jackal 2 ERR-409 hydraulic manifold seal leak",
            spoken_sector_grid="Bravo-4",
            tool_context=ctx,
        )

    assert res["nsn"] == "5330-99-812-4410"
    assert res["repair_classification"] == "L2 Workshop Repair"
    assert ctx.state["active_ticket"]["nsn"] == "5330-99-812-4410"


@patch("app.tools._search_aesp_datastore")
def test_diagnose_and_resolve_grid_with_mocked_bq_and_rag(mock_search):
    mock_search.return_value = ["Free length 79.4 mm; compressed 54.6 mm at 40 lbs."]
    fake_client = MagicMock()

    part_row = {
        "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
        "aesp_reference": "AESP 2350-T-250-523 (Ch 1-2, Para 17.4, Page 14)",
        "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
        "nsn": "5360-99-812-1740",
        "technical_limits": "Free length 79.4 mm; replace if compressed under 54.6 mm at 40 lbs load — do NOT pack with washers.",
    }
    grid_row = {
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "coords_label": "51.2185° N, 1.7925° W",
    }

    q1 = MagicMock()
    q1.result.return_value = [part_row]
    q2 = MagicMock()
    q2.result.return_value = [grid_row]
    fake_client.query.side_effect = [q1, q2]

    ctx = DummyToolContext()
    with patch.object(tools_mod, "_BQ_CLIENT", fake_client):
        res = diagnose_and_resolve_grid(
            fault_query="FV432 K60 oil relief spring",
            spoken_sector_grid="Bravo 4",
            tool_context=ctx,
        )

    assert res["rag_snippets"] == ["Free length 79.4 mm; compressed 54.6 mm at 40 lbs."]
    assert ctx.state["active_ticket"]["latitude"] == 51.2185


def test_publish_ticket_to_chat_stateless_fallback():
    ctx = DummyToolContext()
    with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
        res = publish_ticket_to_chat(ctx)
    assert res["published"] is True
    assert res["ticket"]["nsn"] == "5360-99-812-1740"
    assert res["ticket"]["ticket_id"].startswith("TKT-REME-")


@patch("app.tools.requests.post")
def test_publish_ticket_to_chat_success_and_filters_bq_columns(mock_post):
    fake_bq = MagicMock()
    fake_bq.insert_rows_json.return_value = []

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    mock_post.return_value = fake_resp

    ctx = DummyToolContext(
        {
            "active_ticket": {
                "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
                "aesp_reference": "AESP 2350-T-250-523 (Ch 1-2, Para 17.4, Page 14)",
                "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
                "nsn": "5360-99-812-1740",
                "technical_limits": "Free length 79.4 mm",
                "coords_label": "51.2185° N, 1.7925° W",
                "latitude": 51.2185,
                "longitude": -1.7925,
                "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
                "rag_snippets": [],
            }
        }
    )

    with patch.object(tools_mod, "_BQ_CLIENT", fake_bq):
        res = publish_ticket_to_chat(ctx)

    assert res["published"] is True
    assert res["ticket"]["ticket_id"].startswith("TKT-REME-")
    assert (
        res["ticket"]["google_maps_url"]
        == "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"
    )

    # Verify BigQuery insert row only contains the exact 13 table columns (no sector_display_name)
    inserted_rows = fake_bq.insert_rows_json.call_args[0][1]
    assert len(inserted_rows) == 1
    assert len(inserted_rows[0]) == 13
    assert set(inserted_rows[0].keys()) == BQ_TICKET_COLUMNS
    assert "sector_display_name" not in inserted_rows[0]


def test_issue_02_fast_path_router_sub_5ms_ttft_and_transparency() -> None:
    """Verify Reproduction Prompts 1 & 2 return in <5ms via before_model_callback with full Agent Execution Trace."""
    import time
    from google.adk.models.llm_request import LlmRequest
    from google.genai import types
    from app.agent import (
        CONTEXT_CACHE_CONFIG,
        ESTIMATED_STATIC_PROMPT_TOKENS,
        EVENTS_COMPACTION_CONFIG,
        SYSTEM_INSTRUCTION,
        app,
        fast_path_before_model_callback,
        reme_artificer_agent,
        transparency_after_model_callback,
        warm_context_cache,
    )

    # 1. Verify Context Caching configuration & padded static prompt (>4,200 tokens)
    warmup = warm_context_cache()
    assert len(SYSTEM_INSTRUCTION) >= 18000
    assert ESTIMATED_STATIC_PROMPT_TOKENS >= 4200
    assert warmup["exceeds_flash_1024_floor"] is True
    assert warmup["exceeds_pro_4096_floor"] is True
    assert app.context_cache_config is CONTEXT_CACHE_CONFIG
    assert app.context_cache_config.min_tokens == 2048
    assert app.context_cache_config.ttl_seconds == 7200
    assert app.events_compaction_config is EVENTS_COMPACTION_CONFIG
    assert reme_artificer_agent.generate_content_config.thinking_config.thinking_budget == 0

    # 2. Reproduction Prompt 1: "What is your operational capability" (<5ms TTFT)
    req_p1 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="What is your operational capability")],
            )
        ]
    )
    ctx_p1 = DummyToolContext()
    t0 = time.perf_counter()
    resp_p1 = fast_path_before_model_callback(ctx_p1, req_p1)
    elapsed_p1_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_p1 is not None
    assert elapsed_p1_ms < 5.0
    text_p1 = resp_p1.content.parts[0].text
    assert "4 Bn REME Operational Capability" in text_p1
    assert "TIER_1_FAST_PATH_CAPABILITY" in text_p1
    assert "Agent Execution Trace" in text_p1

    # 3. Reproduction Prompt 2: "Summarise the contents of 2350-T-250-523.pdf" (<5ms TTFT)
    req_p2 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="Summarise the contents of 2350-T-250-523.pdf")],
            )
        ]
    )
    ctx_p2 = DummyToolContext()
    t1 = time.perf_counter()
    resp_p2 = fast_path_before_model_callback(ctx_p2, req_p2)
    elapsed_p2_ms = (time.perf_counter() - t1) * 1000.0
    assert resp_p2 is not None
    assert elapsed_p2_ms < 5.0
    text_p2 = resp_p2.content.parts[0].text
    assert "AESP 2350-T-250-523.pdf" in text_p2
    assert "5360-99-812-1740" in text_p2
    assert "79.4 mm" in text_p2
    assert "TIER_2_CACHED_AESP_SUMMARY" in text_p2
    assert "Agent Execution Trace" in text_p2

    # 4. Verify Scene 1 live triage queries pass through to Tier 3 (returns None)
    req_triage = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="FV432 K60 low oil pressure at Sector Bravo-4"
                    )
                ],
            )
        ]
    )
    assert fast_path_before_model_callback(DummyToolContext(), req_triage) is None

    # 5. Verify transparency_after_model_callback appends Agent Execution Trace on Tier 3 responses
    from google.adk.models.llm_response import LlmResponse

    ctx_t3 = DummyToolContext(
        {
            "_turn_t0_perf": time.perf_counter() - 0.12,
            "active_ticket": {
                "execution_telemetry": {
                    "routing_tier": "TIER_3_PARALLEL_HYBRID_TRIAGE",
                    "cache_status": "PARALLEL_LIVE_FETCH",
                    "aesp_search_ms": 112.4,
                    "bq_nsn_ms": 98.1,
                    "bq_grid_ms": 94.3,
                    "total_ms": 118.6,
                    "parallel_fanout": True,
                }
            },
        }
    )
    raw_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card")],
        )
    )
    enriched = transparency_after_model_callback(ctx_t3, raw_resp)
    assert enriched is not None
    enriched_text = enriched.content.parts[0].text
    assert "Agent Execution Trace" in enriched_text
    assert "TIER_3_PARALLEL_HYBRID_TRIAGE" in enriched_text
    assert "DiscoveryEngine=112.4 ms" in enriched_text


def test_issue_03_concise_triage_output_and_multimodal_photo_assessment() -> None:
    """Verifies Issue 03 Fix: 5-line concise Scene 1 output (no verbose card/trace) & photo part assessment."""
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    from app.agent import (
        fast_path_before_model_callback,
        transparency_after_model_callback,
    )

    # 1. Exact Reproduction Prompt: "FV432 K60 low oil pressure at Sector Bravo-4"
    ctx_k60 = DummyToolContext()
    req_k60 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="FV432 K60 low oil pressure at Sector Bravo-4"
                    )
                ],
            )
        ]
    )
    assert fast_path_before_model_callback(ctx_k60, req_k60) is None
    assert ctx_k60.state.get("_enforce_concise_triage") is True

    res_k60 = diagnose_and_resolve_grid(
        fault_query="FV432 K60 low oil pressure at Sector Bravo-4",
        spoken_sector_grid="Sector Bravo-4",
        tool_context=ctx_k60,
    )
    expected_k60 = (
        "Classification: L1 FRT Fix (Bench Check) / L2 Workshop\n"
        "AESP Ref: Para 17.4 (Free length 79.4mm; Min 54.6mm; Do NOT pack with washers)\n"
        "NSN: 5360-99-812-1740\n"
        "Coordinates of Sector : 51.2185° N, 1.7925° W\n\n"
        'Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket'
    )
    assert res_k60["formatted_concise_response"] == expected_k60

    # Even if the LLM attempts to emit the old verbose card, transparency_after_model_callback
    # enforces the exact 5-line concise format and suppresses the inline Agent Execution Trace.
    verbose_model_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text="### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card\n🔊 15s Audio Brief: ..."
                )
            ],
        )
    )
    final_k60_resp = transparency_after_model_callback(ctx_k60, verbose_model_resp)
    assert final_k60_resp is not None
    final_k60_text = final_k60_resp.content.parts[0].text
    assert final_k60_text == expected_k60
    assert "Grounded AESP Diagnostic Card" not in final_k60_text
    assert "15s Audio Brief" not in final_k60_text
    assert "Agent Execution Trace" not in final_k60_text

    # 2. Multimodal Photo Assessment — Case A: Soldier Field-Fixable (Loose Union, No New Part)
    ctx_field = DummyToolContext()
    req_photo = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        data=b"\x89PNG\r\n\x1a\n", mime_type="image/png"
                    ),
                    types.Part.from_text(
                        text="Photo attached: loose union nut at Sector Bravo-4, pipe and valve intact, soldier can tighten in field"
                    ),
                ],
            )
        ]
    )
    assert fast_path_before_model_callback(ctx_field, req_photo) is None
    assert ctx_field.state.get("has_attached_photo") is True
    res_field = diagnose_and_resolve_grid(
        fault_query="Photo shows loose union nut, pipe and valve intact, soldier can fix in the field",
        spoken_sector_grid="Sector Bravo-4",
        tool_context=ctx_field,
    )
    assert res_field["requires_new_part"] is False
    assert res_field["field_fixable_by_soldier"] is True
    assert res_field["repair_classification"] == "L1 Field Fix (No New Part Required)"
    assert res_field["nsn"] == "N/A (Field Fix — Re-torque union to 45Nm)"
    assert "Classification: L1 Field Fix (No New Part Required)" in res_field["formatted_concise_response"]

    # 3. Multimodal Photo Assessment — Case B: Broken Hydraulic Pipe Only
    ctx_pipe = DummyToolContext()
    res_pipe = diagnose_and_resolve_grid(
        fault_query="Photo shows cracked broken hydraulic pipe at Sector Bravo-4",
        spoken_sector_grid="Sector Bravo-4",
        tool_context=ctx_pipe,
    )
    assert res_pipe["requires_new_part"] is True
    assert res_pipe["field_fixable_by_soldier"] is False
    assert res_pipe["repair_classification"] == "L2 Repair (New Part Required)"
    assert res_pipe["nsn"] == "4710-99-812-4420"
    assert res_pipe["concise_aesp_ref"] == "Para 4.12 (Torque 45Nm)"

    # 4. Multimodal Photo Assessment — Case C: Broken Hydraulic Safety Valve Only
    ctx_valve = DummyToolContext()
    res_valve = diagnose_and_resolve_grid(
        fault_query="Photo shows fractured hydraulic safety valve at Sector Alpha-1",
        spoken_sector_grid="Sector Alpha-1",
        tool_context=ctx_valve,
    )
    assert res_valve["requires_new_part"] is True
    assert res_valve["field_fixable_by_soldier"] is False
    assert res_valve["repair_classification"] == "L2 Repair (New Part Required)"
    assert res_valve["nsn"] == "4820-99-812-4415"
    assert res_valve["concise_aesp_ref"] == "Para 4.14 (Torque 45Nm)"

    # 5. Multimodal Photo Assessment — Case D: Both Hydraulic Safety Valve AND Pipe Broken
    ctx_both = DummyToolContext()
    res_both = diagnose_and_resolve_grid(
        fault_query="Photo shows both hydraulic safety valve and hydraulic pipe are broken at Sector Bravo-4",
        spoken_sector_grid="Sector Bravo-4",
        tool_context=ctx_both,
    )
    assert res_both["requires_new_part"] is True
    assert res_both["field_fixable_by_soldier"] is False
    assert res_both["repair_classification"] == "L2 Repair (New Part Required)"
    assert res_both["nsn"] == "4820-99-812-4415, 4710-99-812-4420"
    assert res_both["concise_aesp_ref"] == "Para 4.12 & Para 4.14 (Torque 45Nm)"


def test_issue_04_concise_publish_output_and_gcs_prompt_image_upload() -> None:
    """Verifies Issue 04 Fix: concise Scene 2 output on 'Publish to Group Chat' and GCS image persistence."""
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    import app.tools as tools_mod
    from app.agent import (
        fast_path_before_model_callback,
        transparency_after_model_callback,
    )

    # 1. User provides a photograph in the Scene 1 prompt
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    ctx = DummyToolContext()
    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    req_scene1 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=sample_png, mime_type="image/png"),
                    types.Part.from_text(
                        text="FV432 K60 low oil pressure at Sector Bravo-4"
                    ),
                ],
            )
        ]
    )

    with patch.object(tools_mod, "_STORAGE_CLIENT", mock_storage), patch.object(
        tools_mod, "_BQ_CLIENT", None
    ), patch("app.tools.requests.post", side_effect=OSError("offline")):
        assert fast_path_before_model_callback(ctx, req_scene1) is None
        assert ctx.state.get("has_attached_photo") is True
        assert ctx.state.get("prompt_image_gcs_uri", "").startswith(
            "gs://antig-dave-reme-ticket-images-eu/tickets/"
        )
        assert ctx.state.get("prompt_image_url", "").startswith(
            "/api/ticket-image/tickets/"
        )
        mock_blob.upload_from_string.assert_called_once()

        diag = diagnose_and_resolve_grid(
            fault_query="FV432 K60 low oil pressure at Sector Bravo-4",
            spoken_sector_grid="Sector Bravo-4",
            tool_context=ctx,
        )
        assert diag["image_gcs_uri"].startswith(
            "gs://antig-dave-reme-ticket-images-eu/tickets/"
        )
        assert diag["image_url"].startswith("/api/ticket-image/tickets/")

    # 2. Soldier prompts: 'Publish to Group Chat" to broadcast this recovery ticket'
    req_publish = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text='Publish to Group Chat" to broadcast this recovery ticket'
                    )
                ],
            )
        ]
    )
    assert fast_path_before_model_callback(ctx, req_publish) is None
    assert ctx.state.get("_enforce_concise_publish") is True
    assert ctx.state.get("_enforce_concise_triage") is False

    mock_bq = MagicMock()
    mock_bq.insert_rows_json.return_value = []
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200

    with patch.object(tools_mod, "_BQ_CLIENT", mock_bq), patch(
        "app.tools.requests.post", return_value=mock_post_resp
    ) as mock_post:
        pub_res = publish_ticket_to_chat(tool_context=ctx)

    ticket_id = pub_res["ticket"]["ticket_id"]
    expected_publish_text = (
        "Callsign: Cpl MacDonald (4 Bn REME FRT)\n"
        "Vehicle Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)\n"
        "Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)\n"
        "Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740\n\n"
        f"Status: Fault ticket {ticket_id} published to 4 Bn REME Sustainment Group Chat."
    )
    assert pub_res["formatted_publish_response"] == expected_publish_text
    assert pub_res["ticket"]["image_gcs_uri"].startswith(
        "gs://antig-dave-reme-ticket-images-eu/tickets/"
    )
    assert pub_res["ticket"]["image_url"].startswith("/api/ticket-image/tickets/")

    # Verify BigQuery row includes image_gcs_uri and image_url
    inserted_row = mock_bq.insert_rows_json.call_args[0][1][0]
    assert inserted_row["image_gcs_uri"] == pub_res["ticket"]["image_gcs_uri"]
    assert inserted_row["image_url"] == pub_res["ticket"]["image_url"]

    # Verify Cloud Run POST payload includes image_gcs_uri, image_url, and image_base64
    posted_json = mock_post.call_args.kwargs["json"]
    assert posted_json["image_gcs_uri"] == pub_res["ticket"]["image_gcs_uri"]
    assert posted_json["image_url"] == pub_res["ticket"]["image_url"]
    assert posted_json.get("image_base64") is not None

    # 3. Verify transparency_after_model_callback strips the exact verbose symptom trace from Issue 04
    verbose_error_trace = (
        "Callsign: Cpl MacDonald (4 Bn REME FRT)\n"
        "Casualty Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)\n"
        "Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)\n"
        "Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740\n"
        "Tactical Navigation: Open Universal Google Maps Route (51.2185, -1.7925)\n"
        "Routing Tier: TIER_3_PARALLEL_HYBRID_TRIAGE\n"
        "Tool Cache Status: MEMORY_TTL_HIT (parallel_fanout=True)\n"
        "Sub-Tool Latencies: DiscoveryEngine=0.0 ms | BQ_NSN=0.0 ms | BQ_Grid=0.0 ms (Total Tool Wall-Clock: 0.02 ms)\n"
        "Context Cache Config: ENABLED (min_tokens=2048, ttl_seconds=7200, static_prefix_tokens=5764)\n"
        "Reasoning Overhead: DISABLED (thinking_budget=0, temperature=0.0)"
    )
    sanitized_resp = transparency_after_model_callback(
        ctx,
        LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=verbose_error_trace)],
            )
        ),
    )
    assert sanitized_resp is not None
    sanitized_text = sanitized_resp.content.parts[0].text
    assert sanitized_text == expected_publish_text
    assert "Casualty Location:" not in sanitized_text
    assert "Tactical Navigation:" not in sanitized_text
    assert "Routing Tier:" not in sanitized_text
    assert "Agent Execution Trace" not in sanitized_text


def test_issue_04_gemini_enterprise_uploaded_file_tag_and_discovery_engine_download() -> None:
    """Verifies Gemini Enterprise `<start_of_user_uploaded_file: ...>` marker & Discovery Engine `:downloadFile?alt=media` extraction."""
    from typing import Any
    from google.adk.models.llm_request import LlmRequest
    from google.genai import types
    from app.agent import fast_path_before_model_callback
    import app.tools as tools_mod

    fake_jpeg = b"\xff\xd8\xff\xe1\x01gExif\x00\x00MM\x00*GEMINI-ENTERPRISE-PHOTO"
    filename = "1fd64153-2c1b-43f7-a614-a570663fbcc44158047231548253371.jpg"
    upstream_sid = "9066417323575841727"

    ctx = DummyToolContext({"agent_engine:upstream_session_id": upstream_sid})
    req = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f"<start_of_user_uploaded_file: {filename}>\n"
                    ),
                    types.Part.from_text(
                        text=f"<end_of_user_uploaded_file: {filename}>\n"
                    ),
                    types.Part.from_text(
                        text="FV432 K60 low oil pressure at Sector Bravo-4"
                    ),
                ],
            )
        ]
    )

    mock_list_resp = MagicMock()
    mock_list_resp.status_code = 200
    mock_list_resp.json.return_value = {
        "fileMetadata": [
            {
                "fileId": "10261233783014647641",
                "name": filename,
                "mimeType": "image/jpeg",
                "byteSize": "3600266",
                "session": f"projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/sessions/{upstream_sid}",
            }
        ]
    }
    mock_dl_resp = MagicMock()
    mock_dl_resp.status_code = 200
    mock_dl_resp.content = fake_jpeg

    def fake_get(url: str, **kwargs: Any) -> Any:
        if ":listSessionFileMetadata" in url:
            return mock_list_resp
        if ":downloadFile" in url and "alt=media" in url:
            return mock_dl_resp
        raise AssertionError(f"Unexpected GET URL: {url}")

    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    with patch.object(tools_mod, "_STORAGE_CLIENT", mock_storage), patch.object(
        tools_mod, "_get_access_token", return_value="fake-oauth-token"
    ), patch("app.tools.requests.get", side_effect=fake_get):
        res = fast_path_before_model_callback(ctx, req)
        assert res is None
        assert ctx.state.get("has_attached_photo") is True
        assert ctx.state.get("uploaded_filename") == filename
        assert ctx.state.get("prompt_image_gcs_uri", "").startswith(
            "gs://antig-dave-reme-ticket-images-eu/tickets/ticket-img-"
        )
        assert ctx.state.get("prompt_image_url", "").startswith(
            "/api/ticket-image/tickets/ticket-img-"
        )
        mock_blob.upload_from_string.assert_called_once()
        # Verify the downloaded image bytes were also injected into llm_request.contents for visual triage
        assert any(
            getattr(p, "inline_data", None) is not None
            for p in req.contents[0].parts
        )

        # Verify publish_ticket_to_chat attaches the downloaded image to both Cloud Run and BigQuery
        diag = diagnose_and_resolve_grid(
            fault_query="FV432 K60 low oil pressure at Sector Bravo-4",
            spoken_sector_grid="Sector Bravo-4",
            tool_context=ctx,
        )
        assert diag["image_gcs_uri"] == ctx.state["prompt_image_gcs_uri"]
        assert diag["image_url"] == ctx.state["prompt_image_url"]


def test_issue_05_british_english_speech_config_and_datastore_locale() -> None:
    """Verifies Issue 05 Fix: British English ('en-GB') SpeechConfig on reme_artificer_agent and datastore languageInfo."""
    from unittest.mock import MagicMock, patch
    from app.agent import (
        DEFAULT_SPEECH_LANGUAGE_CODE,
        DEFAULT_VOICE_NAME,
        SYSTEM_INSTRUCTION,
        reme_artificer_agent,
    )
    from scripts.setup_reme_datastore import create_datastore

    assert DEFAULT_SPEECH_LANGUAGE_CODE == "en-GB"
    assert "en-GB" in SYSTEM_INSTRUCTION
    assert "British English" in SYSTEM_INSTRUCTION

    cfg = reme_artificer_agent.generate_content_config
    assert cfg is not None
    assert cfg.speech_config is not None
    assert cfg.speech_config.language_code == "en-GB"
    assert (
        cfg.speech_config.voice_config.prebuilt_voice_config.voice_name
        == DEFAULT_VOICE_NAME
    )

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"name": "ds-ukd-reme", "done": True}
    with patch("scripts.setup_reme_datastore.requests.post", return_value=mock_post_resp) as mock_post:
        create_datastore(headers={"Authorization": "Bearer test"})
        posted_payload = mock_post.call_args.kwargs["json"]
        assert posted_payload.get("languageInfo") == {"languageCode": "en-GB"}


def test_issue_06_publish_on_group_chat_acknowledges_and_never_repeats_scene1() -> None:
    """Verifies Issue 06 Fix: 'Publish on group chat.' acknowledges ticket publication and never repeats Scene 1."""
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    import app.tools as tools_mod
    from app.agent import (
        fast_path_before_model_callback,
        transparency_after_model_callback,
    )

    ctx = DummyToolContext()

    # Turn 1: Exact user query from live session 10939182715978664
    turn1_prompt = (
        "Corporal McDonald in sector Bravo, the hydraulic safety valve and pipe are broken on the Jackal."
    )
    req_turn1 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=turn1_prompt)],
            )
        ]
    )
    assert fast_path_before_model_callback(ctx, req_turn1) is None
    assert ctx.state.get("_enforce_concise_triage") is True
    assert ctx.state.get("_enforce_concise_publish") is False

    diag_res = diagnose_and_resolve_grid(
        fault_query=turn1_prompt,
        spoken_sector_grid="Sector Bravo",
        tool_context=ctx,
    )
    expected_scene1 = (
        "Classification: L2 Repair (New Part Required)\n"
        "AESP Ref: Para 4.12 & Para 4.14 (Torque 45Nm)\n"
        "NSN: 4820-99-812-4415, 4710-99-812-4420\n"
        "Coordinates of Sector : 51.2185° N, 1.7925° W\n\n"
        'Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket'
    )
    assert diag_res["formatted_concise_response"] == expected_scene1

    resp_turn1 = transparency_after_model_callback(
        ctx,
        LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=expected_scene1)],
            )
        ),
    )
    assert resp_turn1 is not None
    assert resp_turn1.content.parts[0].text == expected_scene1

    # Turn 2: User says "Publish on group chat." (exact phrasing that triggered Issue 06)
    req_turn2 = LlmRequest(
        contents=[
            req_turn1.contents[0],
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=expected_scene1)],
            ),
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="Publish on group chat.")],
            ),
        ]
    )
    assert fast_path_before_model_callback(ctx, req_turn2) is None
    assert ctx.state.get("_enforce_concise_publish") is True
    assert ctx.state.get("_enforce_concise_triage") is False

    mock_bq = MagicMock()
    mock_bq.insert_rows_json.return_value = []
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200

    with patch.object(tools_mod, "_BQ_CLIENT", mock_bq), patch(
        "app.tools.requests.post", return_value=mock_post_resp
    ):
        pub_res = publish_ticket_to_chat(tool_context=ctx)

    ticket_id = pub_res["ticket_id"]
    assert ticket_id.startswith("TKT-REME-")
    expected_scene2 = (
        "Callsign: Cpl MacDonald (4 Bn REME FRT)\n"
        "Vehicle Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)\n"
        "Grounded Manual: AESP 2320-J-100-522, Ch 4, Para 4.12 & Para 4.14 (Page 42)\n"
        "Demand Component: Hydraulic Safety Relief Valve & High-Pressure Pipe Assembly — NSN: 4820-99-812-4415, 4710-99-812-4420\n\n"
        f"Status: Fault ticket {ticket_id} published to 4 Bn REME Sustainment Group Chat."
    )
    assert pub_res["formatted_publish_response"] == expected_scene2

    # Simulate the ADK post-tool before_model_callback pass with function_response in contents
    req_turn2_post_tool = LlmRequest(
        contents=[
            *req_turn2.contents,
            types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="publish_ticket_to_chat", args={}
                    )
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name="publish_ticket_to_chat",
                        response=pub_res,
                    )
                ],
            ),
        ]
    )
    assert fast_path_before_model_callback(ctx, req_turn2_post_tool) is None
    assert ctx.state.get("_enforce_concise_publish") is True
    assert ctx.state.get("_enforce_concise_triage") is False

    # Even if the model tries to repeat Scene 1 or output a short sentence, transparency_after_model_callback
    # must return the Scene 2 acknowledgement and NEVER repeat Scene 1.
    resp_turn2 = transparency_after_model_callback(
        ctx,
        LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=expected_scene1)],
            )
        ),
    )
    assert resp_turn2 is not None
    final_turn2_text = resp_turn2.content.parts[0].text
    assert final_turn2_text == expected_scene2
    assert "Classification:" not in final_turn2_text
    assert 'Next Action: Tap or say "Publish to Group Chat"' not in final_turn2_text
    assert (
        f"Status: Fault ticket {ticket_id} published to 4 Bn REME Sustainment Group Chat."
        in final_turn2_text
    )







