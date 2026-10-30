"""Pydantic v2 Data Contracts for REME Sustainment Agent & Group Chat App."""

from typing import Optional
from pydantic import BaseModel, Field


class ExecutionTelemetry(BaseModel):
    """Typed execution telemetry surfaced for agent performance and transparency."""

    routing_tier: str = Field(
        default="TIER_3_PARALLEL_HYBRID_TRIAGE",
        description="Active execution routing tier",
    )
    cache_status: str = Field(
        default="PARALLEL_LIVE_FETCH",
        description="Context or in-memory TTL cache hit/miss state",
    )
    aesp_search_ms: float = Field(
        default=0.0,
        description="Elapsed milliseconds for Discovery Engine AESP snippet retrieval",
    )
    bq_nsn_ms: float = Field(
        default=0.0,
        description="Elapsed milliseconds for BigQuery ipc_nsn_catalogue lookup",
    )
    bq_grid_ms: float = Field(
        default=0.0,
        description="Elapsed milliseconds for BigQuery spta_sector_grids lookup",
    )
    total_ms: float = Field(
        default=0.0,
        description="Total wall-clock execution time in milliseconds",
    )
    parallel_fanout: bool = Field(
        default=True,
        description="Whether Vertex AI Search and BigQuery lookups executed concurrently",
    )
    sources_consulted: list[str] = Field(
        default_factory=list,
        description="Ordered list of sovereign data sources consulted during the turn",
    )


class ActiveTicketState(BaseModel):
    """Session state stored in tool_context.state['active_ticket'] after Scene 1."""

    repair_classification: str = Field(..., description="L1 FRT Fix or L2 Workshop")
    aesp_reference: str = Field(..., description="Manual chapter/paragraph/page citation")
    concise_aesp_ref: str = Field(
        default="Para 17.4 (Free length 79.4mm; no packing washers)",
        description="Concise AESP paragraph and primary engineering limit for 5-line output",
    )
    part_name: str = Field(..., description="Official IPC part name")
    nsn: str = Field(..., description="13-digit NATO Stock Number or field-fix indicator")
    technical_limits: str = Field(..., description="Engineering tolerances and safety warnings")
    sector_display_name: str = Field(..., description="Human-readable training area sector")
    latitude: float = Field(..., description="WGS84 latitude")
    longitude: float = Field(..., description="WGS84 longitude")
    coords_label: str = Field(..., description="Formatted coordinate string")
    visual_assessment: str = Field(
        default="Component replacement required per AESP inspection limits",
        description="Multimodal photograph or fault inspection assessment (field fix vs new part)",
    )
    requires_new_part: bool = Field(
        default=True,
        description="Whether a replacement component/NSN must be demanded from stores",
    )
    field_fixable_by_soldier: bool = Field(
        default=False,
        description="Whether the soldier/crew can complete the repair in the field without a new part",
    )
    formatted_concise_response: str = Field(
        default="",
        description="Pre-formatted 5-line concise Scene 1 triage response",
    )
    formatted_publish_response: str = Field(
        default="",
        description="Pre-formatted concise Scene 2 publish response",
    )
    image_gcs_uri: Optional[str] = Field(
        default=None,
        description="GCS URI of the user-provided prompt photograph associated with the ticket",
    )
    image_url: Optional[str] = Field(
        default=None,
        description="Chat Application proxy URL (/api/ticket-image/...) for displaying the ticket photograph",
    )
    rag_snippets: list[str] = Field(default_factory=list, description="Extracted AESP search snippets")
    execution_telemetry: Optional[ExecutionTelemetry] = Field(
        default=None,
        description="Structured execution timing and transparency metadata",
    )


def format_concise_triage_output(
    repair_classification: str,
    concise_aesp_ref: str,
    nsn: str,
    coords_label: str,
) -> str:
    """Renders the exact 5-line concise Scene 1 triage response defined in Issue-03."""
    return (
        f"Classification: {repair_classification}\n"
        f"AESP Ref: {concise_aesp_ref}\n"
        f"NSN: {nsn}\n"
        f"Coordinates of Sector : {coords_label}\n\n"
        'Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket'
    )


def format_concise_publish_output(
    callsign: str = "Cpl MacDonald (4 Bn REME FRT)",
    sector_display_name: str = "Salisbury Plain (SPTA) — Sector Bravo-4",
    coords_label: str = "51.2185° N, 1.7925° W",
    aesp_reference: str = "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
    part_name: str = "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
    nsn: str = "5360-99-812-1740",
    ticket_id: Optional[str] = None,
    *,
    vehicle_location: Optional[str] = None,
    grounded_manual: Optional[str] = None,
    demand_component: Optional[str] = None,
) -> str:
    """Renders the exact concise Scene 2 publish acknowledgement response defined in Issue-04 & Issue-06."""
    loc_line = (
        vehicle_location
        if vehicle_location
        else f"{sector_display_name} ({coords_label})"
    )
    manual_line = grounded_manual if grounded_manual else aesp_reference
    comp_line = (
        demand_component
        if demand_component
        else f"{part_name} — NSN: {nsn}"
    )
    status_line = (
        f"Status: Fault ticket {ticket_id} published to 4 Bn REME Sustainment Group Chat."
        if ticket_id
        else "Status: Fault ticket published to 4 Bn REME Sustainment Group Chat."
    )
    return (
        f"Callsign: {callsign}\n"
        f"Vehicle Location: {loc_line}\n"
        f"Grounded Manual: {manual_line}\n"
        f"Demand Component: {comp_line}\n\n"
        f"{status_line}"
    )


class TicketPayload(BaseModel):
    """Complete ticket schema persisted to BigQuery and broadcast to Cloud Run."""

    ticket_id: str = Field(..., description="Unique REME work ticket ID (e.g., TKT-REME-4821)")
    created_at_utc: str = Field(..., description="ISO-8601 UTC timestamp")
    callsign: str = "Cpl MacDonald (4 Bn REME FRT)"
    repair_classification: str
    aesp_reference: str
    part_name: str
    nsn: str
    technical_limits: str
    sector_display_name: Optional[str] = "Salisbury Plain (SPTA) — Sector Bravo-4"
    coords_label: str
    latitude: float
    longitude: float
    google_maps_url: str
    status: str = "DISPATCH_READY"
    image_gcs_uri: Optional[str] = Field(
        default=None,
        description="GCS URI of the user-provided prompt photograph",
    )
    image_url: Optional[str] = Field(
        default=None,
        description="Chat Application proxy URL (/api/ticket-image/...) for the ticket photograph",
    )
    formatted_publish_response: Optional[str] = Field(
        default=None,
        description="Pre-formatted concise Scene 2 publish response",
    )


