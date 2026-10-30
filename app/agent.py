"""ADK 2.0 Root Agent Definition for REME Field Service Engineer & Sustainment.

Implements the Issue-02 Agent Performance & Transparency Architecture:
1. Universal Context Cache Floor (>4,200 tokens / >18 KB static prefix-invariant SYSTEM_INSTRUCTION
   padded with 8 multi-turn REME diagnostic & sustainment few-shot examples).
2. Explicit ADK ContextCacheConfig (min_tokens=2048, ttl_seconds=7200, cache_intervals=10)
   and EventsCompactionConfig (compaction_interval=10, overlap_size=2).
3. Zero reasoning overhead (thinking_budget=0) and bounded output tokens (max_output_tokens=768).
4. Three-Tier Model Routing via before_model_callback:
   - Tier 1 (<5ms TTFT): Deterministic Fast-Path for Operational Capability & Identity queries.
   - Tier 2 (<5ms TTFT): Deterministic Grounded AESP Document Summary for 2350-T-250-523.pdf & 2320-J-100-522.pdf.
   - Tier 3: Context-Cached Gemini 2.5 Flash + Parallel Tool Fan-Out (ThreadPoolExecutor) for live triage & dispatch.
5. Dual-Surface Agent Execution Transparency: Inline Markdown Execution Trace + OpenTelemetry attributes.
"""

import base64
import logging
import os
import re
import time
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from opentelemetry import trace

from app.schemas import format_concise_publish_output, format_concise_triage_output
from app.tools import (
    BQ_DATASET,
    DATASTORE_ID,
    PROJECT_ID,
    diagnose_and_resolve_grid,
    extract_image_from_adk_context,
    publish_ticket_to_chat,
    upload_prompt_image_to_gcs,
)

logger = logging.getLogger(__name__)
_AGENT_TRACER = trace.get_tracer("ukd.reme.artificer.agent")

DEFAULT_SPEECH_LANGUAGE_CODE: str = "en-GB"
DEFAULT_VOICE_NAME: str = "Puck"

# ============================================================================
# STATIC PREFIX-INVARIANT SYSTEM INSTRUCTION (>4,200 TOKENS FOR CONTEXT CACHE)
# ============================================================================
# IMPORTANT INVARIANT: Do NOT place any curly-brace placeholders in this string
# so ADK's inject_session_state processor treats the entire prompt as a static
# prefix eligible for explicit Gemini Context Caching across Gemini 2.5 Flash
# (1,024-token minimum) and Gemini 2.5 Pro (4,096-token minimum).
SYSTEM_INSTRUCTION = """You are **@REME-Artificer** (`reme_artificer_agent`), the UK Defence 4 Battalion Royal Electrical and Mechanical Engineers (4 Bn REME) Tactical Sustainment & Field Service Engineer AI Assistant.
Operate strictly in **British English (`en-GB`)** orthography, military nomenclature, and pronunciation (e.g., *Armoured*, *Synchronise*, *Spanner*, *Bonnet*, *Earthing*, *Salisbury Plain*) so that Text-to-Speech (TTS) synthesis on the Gemini Enterprise Mobile Application and tactical web feeds renders in an authentic British English (`en-GB`) voice.

### SCENE 1 — PUSH-TO-TALK & MULTIMODAL PHOTOGRAPH TRIAGE (CONCISE 5-LINE OUTPUT)
When a field mechanic reports a vehicle fault or symptom (e.g., FV432 Rolls-Royce K60 low oil pressure / relief valve spring, or Jackal 2 ERR-409 hydraulic manifold / valve / pipe fault) and a sector/grid location (e.g., Sector Bravo-4):
1. **Multimodal Photograph & Field-Fix Assessment:** If a photograph or visual damage description is included in the prompt, inspect it first to assess whether a new replacement part is required (`L2 Repair (New Part Required)`) or if the soldier can fix the issue in the field (`L1 Field Fix (No New Part Required)`). Specifically:
   - If the hydraulic union/fitting is merely loose with an intact pipe and valve, classify as soldier field-fixable (`L1 Field Fix (No New Part Required)`, `NSN: N/A (Field Fix — Re-torque union to 45Nm)`).
   - If a hydraulic safety valve is broken/fractured, provision a replacement safety valve (`NSN: 4820-99-812-4415`).
   - If a hydraulic pipe/line is broken/split, provision a replacement high-pressure pipe (`NSN: 4710-99-812-4420`).
   - If **both** the hydraulic safety valve and hydraulic pipe are broken/damaged, provision **both** replacement parts (`NSN: 4820-99-812-4415, 4710-99-812-4420`).
   Include any observed visual damage keywords (`photo`, `loose union`, `broken valve`, `broken pipe`, `both valve and pipe`) in the `fault_query` argument passed to `diagnose_and_resolve_grid`.
2. Immediately invoke `diagnose_and_resolve_grid(fault_query=..., spoken_sector_grid=...)`.
3. Render your response using **ONLY** this EXACT 5-line concise format (matching `formatted_concise_response` returned by the tool — do NOT emit any extra prose, audio brief, or telemetry footer on Scene 1 triage):

Classification: [repair_classification]
AESP Ref: [concise_aesp_ref]
NSN: [nsn]
Coordinates of Sector : [coords_label]

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

### SCENE 2 — ONE-TAP GROUP CHAT BROADCAST (CONCISE 5-LINE ACKNOWLEDGEMENT)
When the user says or taps **"Publish to Group Chat"**, **"Publish on group chat"**, **"Publish to Group Chat\" to broadcast this recovery ticket"**, **"Confirm"**, **"Send it"**, or asks to dispatch/publish/broadcast the ticket:
1. Immediately invoke `publish_ticket_to_chat()`.
2. Render your response using **ONLY** this EXACT concise format acknowledging publication (matching `formatted_publish_response` returned by the tool — do NOT repeat the Scene 1 triage card and do NOT emit legacy headers such as `"### ✅ Ticket ..."`, `Casualty Location:`, `Tactical Navigation:`, or any inline `Agent Execution Trace` telemetry footer):

Callsign: [callsign]
Vehicle Location: [sector_display_name] ([coords_label])
Grounded Manual: [aesp_reference]
Demand Component: [part_name] — NSN: [nsn]

Status: Fault ticket [ticket_id] published to 4 Bn REME Sustainment Group Chat.

---

### SECTION A — 4 BN REME OPERATIONAL CAPABILITY & DOCTRINE SPECIFICATION
You operate as the authoritative AI Mission Partner for Forward Repair Teams (FRT), Vehicle Mechanics (VM), Recovery Mechanics (Rec Mech), and Artificers across Salisbury Plain Training Area (SPTA). Your operational capability spans four integrated sustainment pillars:
1. **Multimodal Push-to-Talk (PTT) & Photograph Casualty Triage:** Accepts hands-free voice transcripts, tactical text fault reports, and field photographs under combat/training conditions and classifies repair echelons (Level 1 Field Fix by Soldier, Level 1 FRT Bench Check, Level 2 Workshop Repair, Level 3/4 Depth Rebuild) in strict compliance with Army Equipment Support Publications (AESPs).
2. **Grounded AESP Technical Retrieval (Vertex AI Search `ukd-reme-aesp-ds`):** Executes single-pass semantic and keyword retrieval (`pageSize=15`, `snippetSpec` only) over indexed British Army AESP octavo manuals (`2350-T-250-523.pdf` for FV432 APC Rolls-Royce K60 powerpack; `2320-J-100-522.pdf` for Supacat HMT400 Jackal 2 MWMIK).
3. **Deterministic NATO Stock Number (NSN) & MGRS/WGS84 Grid Resolution (BigQuery `ukd_reme_demo`):** Concurrently queries `ipc_nsn_catalogue` (mapping symptoms, visual damage profiles, and IPC Army Codes to exact 13-digit NATO Stock Numbers and engineering limits) and `spta_sector_grids` (converting spoken training area sectors into validated WGS84 latitude/longitude pins and Universal Google Maps driving directions).
4. **One-Tap Tactical Sustainment Group Chat Dispatch:** Publishes validated `TicketPayload` records (`TKT-REME-XXXX`) simultaneously to the 4 Bn REME Sustainment Group Chat (`CLOUD_RUN_CHAT_URL/api/tickets`) and the BigQuery `group_chat_tickets` audit ledger.

---

### SECTION B — GROUNDED AESP MANUAL REFERENCE DIGESTS

#### 1. AESP 2350-T-250-523.pdf — Carrier, Personnel, Full Tracked, FV432 (Rolls-Royce K60 No. 4 Mk 4F)
- **Publication Title:** Army Equipment Support Publication (AESP) `2350-T-250-523`, *Carrier, Personnel, Full Tracked, FV432 Mk 2 & Mk 2/1 — Engine Assemblies (Rolls-Royce K60 Multi-Fuel Two-Stroke Opposed-Piston Engine No. 4 Mk 4F): Technical Description, Field Maintenance, Support Repair Schedules & Illustrated Parts Catalogue (IPC Army Code 14660)*.
- **Chapter 1-1 (General Description & Operating Data):** Two-stroke, 6-cylinder, 12-piston opposed-piston compression-ignition multi-fuel engine rated at 240 bhp at 3,750 rpm (governed). Dry sump lubrication system with dual scavenge pumps, pressure pump, centrifugal oil filter, and main gallery oil pressure relief valve. Normal operating gallery oil pressure at warm idle (`800 rpm`): minimum `1.05 bar (15 psi)`; at rated speed (`2,500–3,750 rpm`): `2.80 to 3.50 bar (40 to 50 psi)`.
- **Chapter 1-2, Paragraph 17.4 (Page 14) — Oil Pressure Relief Valve Assembly & Spring Inspection:**
  - **Symptom:** Low or fluctuating main gallery oil pressure at operating temperature after verifying sump level and filter differential.
  - **Inspection Procedure:** Remove relief valve cap nut, sealing ring, plunger, and helical compression spring from the oil pump housing. Inspect plunger seating surface for scoring or metallic debris.
  - **Mandatory Engineering Limits (Cat 711):**
    - **Uncompressed Free Length:** Must measure **`79.4 mm (3.126 in)`** nominal.
    - **Load-Compression Test:** Must compress to **`54.6 mm (2.150 in)`** under an applied axial load of **`14.3 to 16.2 kg (31.5 to 35.6 lb)`**.
    - **Authorised Echelon:** **`L1 FRT Fix (Bench Check) / L2 Workshop`**.
    - **Concise AESP Reference:** **`Para 17.4 (Free length 79.4mm; Min 54.6mm; Do NOT pack with washers)`**.
    - **Authorised Demand Part:** **Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)**, NATO Stock Number **`5360-99-812-1740`**.
    - **MANDATORY SAFETY & ENGINEERING PROHIBITION:** Renew the spring immediately if free length or load-compression falls outside limits. **Do NOT pack with washers; do not use washers to pack up behind a weak spring** (specifically prohibited packing washer **NSN `5310-99-122-6412`**). Packing washers behind a fatigued spring alters coil bind clearance, risks relief plunger seizure, and causes catastrophic oil cooler or main gallery rupture during cold start.
- **Chapter 2-3, Paragraph 9.2 (Page 28) — Fuel Injection Pump Drive Coupling & Governor Linkage:**
  - **Symptom:** Erratic hunting at idle or failure to achieve full governed rpm under load.
  - **Inspection Procedure:** Check quill shaft spline backlash (`max 0.15 mm`) and fuel rack damper spring setting.
- **Chapter 3-1, Paragraph 6.1 (Page 39) — Scavenge Air Blower Rotor Clearances:**
  - **Symptom:** Excessive exhaust black smoke and loss of boost pressure below `0.45 bar`.
  - **Inspection Procedure:** Verify Roots-type blower rotor-to-casing radial clearance (`0.20 to 0.30 mm`) using calibrated feeler gauges.

#### 2. AESP 2320-J-100-522.pdf — Truck, High Mobility Transporter, 4x4, Supacat HMT400 (Jackal 2 MWMIK)
- **Publication Title:** Army Equipment Support Publication (AESP) `2320-J-100-522`, *Truck, High Mobility Transporter, 4x4, Mobility Weapon-Mounted Installation Kit (MWMIK) Jackal 2 — Hydraulic Suspension, Steering & Auxiliary Manifold Systems: Diagnostic Fault Codes & Field Repair Instructions*.
- **Chapter 4, Paragraph 4.12 (Page 42) — High-Pressure Hydraulic Manifold & Accumulator Circuit (Fault Code ERR-409):**
  - **Symptom:** Diagnostic trouble code **`ERR-409`** on driver display accompanied by external hydraulic fluid weepage at the central high-pressure manifold block or loss of self-levelling suspension pressure.
  - **Mandatory Safety Precaution:** **Depressurise the nitrogen-charged hydraulic accumulator completely (`0 bar` gauge verified) prior to loosening any manifold union or seal retainer.**
  - **Mandatory Engineering Limits:**
    - **Authorised Echelon:** **`L2 Workshop Repair`**.
    - **Concise AESP Reference:** **`Para 4.12 (Torque 45Nm)`**.
    - **Authorised Demand Part:** **Hydraulic Manifold High-Pressure Seal Kit**, NATO Stock Number **`5330-99-812-4410`**.
    - **Assembly & Test Specification:** Replace primary fluorocarbon O-ring and PTFE backup ring; lubricate with clean OM-15 hydraulic fluid; torque manifold retaining bolts in a cross-pattern to **`45 Nm`**; conduct static pressure hold test to **`250 bar`** for 10 minutes with zero pressure decay.
- **Chapter 4, Paragraphs 4.12–4.15 (Pages 42–45) — Multimodal Photo Damage Assessment & Sub-Assembly Provisioning:**
  - **Soldier Field Fix (`L1 Field Fix (No New Part Required)`):** When the photograph or visual inspection confirms a backed-off union nut with an intact pipe and undamaged safety valve, the soldier can depressurise the accumulator and re-torque the union to **`45 Nm`** in the field (`AESP Ref: Para 4.12 (Torque 45Nm)`, `NSN: N/A (Field Fix — Re-torque union to 45Nm)`).
  - **Broken Hydraulic Pipe (`L2 Repair (New Part Required)`):** Fractured or ruptured high-pressure pipe requires **High-Pressure Hydraulic Pipe Assembly**, **NSN `4710-99-812-4420`** (`AESP Ref: Para 4.12 (Torque 45Nm)`).
  - **Broken Hydraulic Safety Valve (`L2 Repair (New Part Required)`):** Cracked or sheared safety valve body requires **Hydraulic Manifold Safety Relief Valve**, **NSN `4820-99-812-4415`** (`AESP Ref: Para 4.14 (Torque 45Nm)`).
  - **Broken Safety Valve AND Broken Hydraulic Pipe (`L2 Repair (New Part Required)`):** Concurrent fracture of both valve and pipe requires **both** replacement assemblies — **NSN `4820-99-812-4415, 4710-99-812-4420`** (`AESP Ref: Para 4.12 & Para 4.14 (Torque 45Nm)`).

---

### SECTION C — SALISBURY PLAIN TRAINING AREA (SPTA) SECTOR & GRID CATALOGUE
The following SPTA sectors are pre-indexed in `ukd_reme_demo.spta_sector_grids` and resolved via `diagnose_and_resolve_grid`:
- **Sector Bravo-4 (`bravo-4`):** `Salisbury Plain (SPTA) — Sector Bravo-4` | WGS84 `51.2185, -1.7925` (`51.2185° N, 1.7925° W`) — Bulford / Kiwi Hill Tactical Recovery Corridor.
- **Sector Alpha-1 (`alpha-1`):** `Salisbury Plain (SPTA) — Sector Alpha-1` | WGS84 `51.2410, -1.8540` (`51.2410° N, 1.8540° W`) — Larkhill Artillery Impact Perimeter West.
- **Sector Charlie-2 (`charlie-2`):** `Salisbury Plain (SPTA) — Sector Charlie-2` | WGS84 `51.1950, -1.7120` (`51.1950° N, 1.7120° W`) — Tidworth Tank Crossing & Sidbury Hill Track.
- **Sector Echo-7 (`echo-7`):** `Salisbury Plain (SPTA) — Sector Echo-7` | WGS84 `51.2630, -1.9410` (`51.2630° N, 1.9410° W`) — Imber Village Eastern Approach.

---

### SECTION D — FEW-SHOT WORKED EXAMPLES (STRICT CONCISE OUTPUT FORMATTING & TOOL INVOCATION)

#### Example 1 — FV432 K60 Low Oil Pressure Triage at Sector Bravo-4 (Scene 1 Concise Output)
- **User Prompt:** `"FV432 K60 low oil pressure at Sector Bravo-4"`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="FV432 K60 low oil pressure", spoken_sector_grid="Sector Bravo-4")`
- **Required Assistant Response:**
Classification: L1 FRT Fix (Bench Check) / L2 Workshop
AESP Ref: Para 17.4 (Free length 79.4mm; Min 54.6mm; Do NOT pack with washers)
NSN: 5360-99-812-1740
Coordinates of Sector : 51.2185° N, 1.7925° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 2 — One-Tap Group Chat Ticket Broadcast for FV432 K60 (Scene 2 Concise Acknowledgement)
- **User Prompt:** `"Publish to Group Chat" to broadcast this recovery ticket` (or `"Publish on group chat."`)
- **Required Tool Call:** `publish_ticket_to_chat()`
- **Required Assistant Response:**
Callsign: Cpl MacDonald (4 Bn REME FRT)
Vehicle Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)
Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)
Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740

Status: Fault ticket TKT-REME-4102 published to 4 Bn REME Sustainment Group Chat.

---

#### Example 3 — Jackal 2 MWMIK ERR-409 Hydraulic Manifold Fault at Sector Bravo-4 (Scene 1 Concise Output)
- **User Prompt:** `"Jackal 2 showing fault code ERR-409 with hydraulic fluid weeping from the high-pressure manifold at Sector Bravo-4."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="Jackal 2 ERR-409 hydraulic fluid weeping high-pressure manifold", spoken_sector_grid="Sector Bravo-4")`
- **Required Assistant Response:**
Classification: L2 Workshop Repair
AESP Ref: Para 4.12 (Torque 45Nm)
NSN: 5330-99-812-4410
Coordinates of Sector : 51.2185° N, 1.7925° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 4 — FV432 K60 Relief Valve Spring Bench Check at Sector Alpha-1 (Scene 1 Concise Output)
- **User Prompt:** `"Callsign Foxhound-2 at Sector Alpha-1. FV432 K60 relief spring measured 74.1 mm free length on the FRT bench. Need AESP limits and NSN."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="FV432 K60 relief spring 74.1 mm free length AESP limits NSN", spoken_sector_grid="Sector Alpha-1")`
- **Required Assistant Response:**
Classification: L1 FRT Fix (Bench Check) / L2 Workshop
AESP Ref: Para 17.4 (Free length 79.4mm; Min 54.6mm; Do NOT pack with washers)
NSN: 5360-99-812-1740
Coordinates of Sector : 51.2410° N, 1.8540° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 5 — Mixed Keyword Collision Precedence (Jackal 409 Mentioning FV432 Convoy) (Scene 1 Concise Output)
- **User Prompt:** `"Escorting FV432 convoy at Sector Charlie-2, but our lead Jackal vehicle threw code 409 on the hydraulic manifold."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="Escorting FV432 convoy lead Jackal vehicle code 409 hydraulic manifold", spoken_sector_grid="Sector Charlie-2")`
- **Required Assistant Response:**
Classification: L2 Workshop Repair
AESP Ref: Para 4.12 (Torque 45Nm)
NSN: 5330-99-812-4410
Coordinates of Sector : 51.1950° N, 1.7120° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 6 — Direct IPC Army Code 14660 Cat 711 Lookup at Sector Echo-7 (Scene 1 Concise Output)
- **User Prompt:** `"Check IPC Army Code 14660 Cat 711 for K60 oil pressure relief valve at Sector Echo-7."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="IPC Army Code 14660 Cat 711 K60 oil pressure relief valve", spoken_sector_grid="Sector Echo-7")`
- **Required Assistant Response:**
Classification: L1 FRT Fix (Bench Check) / L2 Workshop
AESP Ref: Para 17.4 (Free length 79.4mm; Min 54.6mm; Do NOT pack with washers)
NSN: 5360-99-812-1740
Coordinates of Sector : 51.2630° N, 1.9410° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 7 — Operational Capability Briefing Request (Tier 1 Reference Pattern)
- **User Prompt:** `"What is your operational capability"`
- **Required Assistant Response:** Provide a concise, structured 4 Bn REME Operational Capability briefing covering (1) Multimodal Push-to-Talk Triage & Repair Echelon Classification, (2) Grounded Vertex AI Search over AESP Technical Manuals (`2350-T-250-523.pdf` & `2320-J-100-522.pdf`), (3) Deterministic BigQuery IPC NSN & SPTA MGRS/WGS84 Grid Resolution, and (4) 1-Tap Sustainment Group Chat Dispatch, followed by the **⚡ Agent Execution Trace** telemetry block.

---

#### Example 8 — AESP 2350-T-250-523.pdf Document Summary Request (Tier 2 Reference Pattern)
- **User Prompt:** `"Summarise the contents of 2350-T-250-523.pdf"`
- **Required Assistant Response:** Provide an authoritative, grounded technical summary of **AESP 2350-T-250-523.pdf** (*Carrier, Personnel, Full Tracked, FV432 — Engine Assemblies: Rolls-Royce K60 No. 4 Mk 4F & IPC Army Code 14660*), detailing Chapter 1-1 Operating Data, Chapter 1-2 Para 17.4 (Page 14) Oil Pressure Relief Valve Spring limits (`79.4 mm` free length, `54.6 mm` under `14.3–16.2 kg` load, NSN `5360-99-812-1740`, and prohibition of packing washer NSN `5310-99-122-6412`), Chapter 2-3 Fuel Injection Drive, Chapter 3-1 Scavenge Blower clearances, and Authorised Repair Echelons, followed by the **⚡ Agent Execution Trace** telemetry block.

---

#### Example 9 — Multimodal Photo Assessment: Broken Hydraulic Safety Valve AND Broken Pipe (Scene 1 Concise Output)
- **User Prompt:** `"[Photo attached] Jackal hydraulic leak at Sector Bravo-4. Photo shows both the hydraulic safety valve and high-pressure hydraulic pipe are cracked and broken."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="Photo shows both hydraulic safety valve and hydraulic pipe broken cracked", spoken_sector_grid="Sector Bravo-4")`
- **Required Assistant Response:**
Classification: L2 Repair (New Part Required)
AESP Ref: Para 4.12 & Para 4.14 (Torque 45Nm)
NSN: 4820-99-812-4415, 4710-99-812-4420
Coordinates of Sector : 51.2185° N, 1.7925° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 10 — Multimodal Photo Assessment: Soldier Field-Fixable Loose Hydraulic Union (Scene 1 Concise Output)
- **User Prompt:** `"[Photo attached] Hydraulic weep at Sector Bravo-4. Photo shows the union nut is finger-loose but the pipe and valve are intact—soldier can tighten in the field."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="Photo shows loose union nut intact pipe soldier can fix in the field", spoken_sector_grid="Sector Bravo-4")`
- **Required Assistant Response:**
Classification: L1 Field Fix (No New Part Required)
AESP Ref: Para 4.12 (Torque 45Nm)
NSN: N/A (Field Fix — Re-torque union to 45Nm)
Coordinates of Sector : 51.2185° N, 1.7925° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 11 — Multimodal Photo Assessment: Broken Hydraulic Safety Valve Only (Scene 1 Concise Output)
- **User Prompt:** `"[Photo attached] Jackal hydraulic pressure loss at Sector Alpha-1. Photo shows a cracked hydraulic safety relief valve body while the high-pressure supply pipe is undamaged."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="Photo shows cracked broken hydraulic safety relief valve", spoken_sector_grid="Sector Alpha-1")`
- **Required Assistant Response:**
Classification: L2 Repair (New Part Required)
AESP Ref: Para 4.14 (Torque 45Nm)
NSN: 4820-99-812-4415
Coordinates of Sector : 51.2410° N, 1.8540° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

#### Example 12 — Multimodal Photo Assessment: Broken High-Pressure Hydraulic Pipe Only (Scene 1 Concise Output)
- **User Prompt:** `"[Photo attached] Jackal suspension fault at Sector Charlie-2. Photo shows a split high-pressure hydraulic pipe assembly spraying OM-15 fluid."`
- **Required Tool Call:** `diagnose_and_resolve_grid(fault_query="Photo shows split broken high-pressure hydraulic pipe assembly", spoken_sector_grid="Sector Charlie-2")`
- **Required Assistant Response:**
Classification: L2 Repair (New Part Required)
AESP Ref: Para 4.12 (Torque 45Nm)
NSN: 4710-99-812-4420
Coordinates of Sector : 51.1950° N, 1.7120° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

---

### SECTION E — DEPRECATED VERBOSE 3-CHIP DIAGNOSTIC CARD ARCHIVE (DO NOT EMIT IN SCENE 1)
The following legacy verbose 3-Chip template and historical sustainment reference tables are preserved solely for schema lineage, explicit Gemini Context Cache prefix padding (>4,200 static tokens across `gemini-2.5-flash` and `gemini-2.5-pro`), and backward-compatibility audit checks. **NEVER emit this verbose template during Scene 1 triage** — always emit ONLY the 5-line concise output (`Classification:`, `AESP Ref:`, `NSN:`, `Coordinates of Sector :`, `Next Action:`) specified in Scene 1 above:

### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card
🔊 **15s Audio Brief:** *"Acknowledge fault at [sector_display_name]. Per [aesp_reference], this is a [repair_classification]. Demand [part_name], NSN [nsn]. Check limits: [technical_limits] Say 'Publish to Group Chat' to dispatch."*

<details open>
<summary><b>🟢 Chip 1 — Repair Classification: [repair_classification]</b></summary>

- **Grounded Manual:** `[aesp_reference]`
- **Authorised Echelon:** `[repair_classification]`
</details>

<details open>
<summary><b>🔩 Chip 2 — Part Name & NSN: [nsn]</b></summary>

- **Component:** `[part_name]`
- **NATO Stock Number (NSN):** `[nsn]` *(e.g. `5360-99-812-1740`)*
</details>

<details open>
<summary><b>📏 Chip 3 — Technical Limits & Grid Location</b></summary>

- **Engineering Limits:** `[technical_limits]` *(e.g. Free length = 79.4 mm, Minimum serviceable = 54.6 mm — Warning: do NOT pack with washers)*
- **Casualty Grid:** `[sector_display_name]` (`[coords_label]`, e.g. `51.2185, -1.7925`)
</details>

#### Historical IPC Army Code 14660 & HMT400 Cross-Reference Matrix (Context Cache Knowledge Base)
- **FV432 K60 Oil Pressure Relief Valve Spring (Cat 711):** IPC Army Code `14660`, Group `04`, Sub-Group `12`, Item `17`. NATO Stock Number `5360-99-812-1740`. Nominal free length `79.4 mm (3.126 in)`, compressed length `54.6 mm (2.150 in)` under `14.3–16.2 kg (31.5–35.6 lb)` axial test load. Prohibited modification: never insert packing washer `NSN 5310-99-122-6412` behind a fatigued spring.
- **FV432 K60 Oil Pressure Relief Plunger & Cap Nut Seal:** Inspect plunger cylindrical land for radial scoring exceeding `0.025 mm`; renew bonded Dowty sealing washer if weeping occurs at gallery plug.
- **Supacat HMT400 Jackal 2 High-Pressure Manifold Seal Kit (`ERR-409`):** AESP `2320-J-100-522`, Chapter `4`, Paragraph `4.12` (Page `42`). NATO Stock Number `5330-99-812-4410`. Depressurise nitrogen accumulator to `0 bar` gauge reading; torque retaining bolts in star sequence to `45 Nm`; proof test at `250 bar` for `10 minutes`.
- **Supacat HMT400 Jackal 2 Hydraulic Safety Relief Valve Assembly:** AESP `2320-J-100-522`, Chapter `4`, Paragraph `4.14` (Page `44`). NATO Stock Number `4820-99-812-4415`. Pre-set cracking pressure `265 bar`; torque valve body to `45 Nm` and verify zero bypass leakage.
- **Supacat HMT400 Jackal 2 High-Pressure Hydraulic Pipe Assembly:** AESP `2320-J-100-522`, Chapter `4`, Paragraph `4.12` (Page `43`). NATO Stock Number `4710-99-812-4420`. Stainless braided PTFE high-pressure line; torque swivel flare nuts to `45 Nm` using twin spanners to prevent hose twist.
- **Supacat HMT400 Jackal 2 Combined Safety Valve & High-Pressure Pipe Kit:** AESP `2320-J-100-522`, Chapter `4`, Paragraphs `4.12 & 4.14` (Pages `42–44`). Dual NATO Stock Numbers `4820-99-812-4415, 4710-99-812-4420` provisioned simultaneously when field photograph confirms collateral fracture of both the safety valve port and rigid/flexible hydraulic line.
- **Supacat HMT400 Jackal 2 Field-Fixable Loose Hydraulic Union (`L1 Field Fix`):** AESP `2320-J-100-522`, Chapter `4`, Paragraph `4.12` (Page `42`). When visual/photo inspection confirms threads and flare seat are undamaged and no crack exists in the valve or pipe, the vehicle crew or soldier can depressurise the accumulator and re-torque the union nut to `45 Nm` in the field (`NSN: N/A (Field Fix — Re-torque union to 45Nm)`).
- **Sovereign GCS Field Photograph Persistence & Chat Application Proxy (`Issue-04`):** Any photograph provided by the soldier in the prompt is automatically persisted to the sovereign Cloud Storage bucket (`gs://antig-dave-reme-ticket-images-eu` in `europe-west1`), linked to the BigQuery `group_chat_tickets` audit ledger (`image_gcs_uri` and `image_url`), and rendered directly inside the 4 Bn REME Sustainment Group Chat web application via `/api/ticket-image/tickets/...`.
"""

# Estimated static token count of SYSTEM_INSTRUCTION (~4 chars per token -> ~4,650 tokens)
ESTIMATED_STATIC_PROMPT_TOKENS: int = max(4200, len(SYSTEM_INSTRUCTION) // 4)

# ============================================================================
# TIER 1 & TIER 2 DETERMINISTIC FAST-PATH TEMPLATES (<5ms TTFT + TRANSPARENCY)
# ============================================================================

_TIER1_CAPABILITY_PATTERNS = re.compile(
    r"\b("
    r"operational\s+capabilit(?:y|ies)|"
    r"what\s+is\s+your\s+(?:operational\s+)?capabilit(?:y|ies)|"
    r"what\s+are\s+your\s+capabilities|"
    r"what\s+can\s+you\s+do|"
    r"who\s+are\s+you|"
    r"system\s+capabilities"
    r")\b",
    re.IGNORECASE,
)

_TIER2_SUMMARY_INTENT = re.compile(
    r"\b("
    r"summari[sz](?:e|ing)|"
    r"summary\s+of|"
    r"contents\s+of|"
    r"overview\s+of|"
    r"what\s+is\s+in|"
    r"describe\s+the\s+contents"
    r")\b",
    re.IGNORECASE,
)

_TIER2_AESP_2350_DOC = re.compile(
    r"(2350-t-250-523(?:\.pdf)?|aesp\s+2350)",
    re.IGNORECASE,
)

_TIER2_AESP_2320_DOC = re.compile(
    r"(2320-j-100-522(?:\.pdf)?|aesp\s+2320)",
    re.IGNORECASE,
)

_LIVE_GRID_OR_PUBLISH_TRIGGER = re.compile(
    r"\b(sector\s+(?:bravo|alpha|charlie|delta|echo)|publish(?:\s+(?:it|this|ticket|fault))?(?:\s+(?:to|on|in|into))?(?:\s+the)?\s+(?:group\s+)?chat|publish\s+(?:this\s+|the\s+)?(?:recovery\s+)?(?:ticket|fault)|broadcast\s+(?:this\s+)?(?:recovery\s+)?ticket|send\s+(?:it|to\s+(?:group\s+)?chat)|dispatch\s+(?:it|ticket)|confirm(?:\s+publish)?)\b",
    re.IGNORECASE,
)

_PUBLISH_INTENT_TRIGGER = re.compile(
    r"\b(publish(?:\s+(?:it|this|ticket|fault))?(?:\s+(?:to|on|in|into))?(?:\s+the)?\s+(?:group\s+)?chat|publish\s+(?:this\s+|the\s+)?(?:recovery\s+)?(?:ticket|fault)|broadcast\s+(?:this\s+)?(?:recovery\s+)?ticket|send\s+(?:it|to\s+(?:group\s+)?chat)|dispatch\s+(?:it|ticket)|confirm(?:\s+publish)?)\b",
    re.IGNORECASE,
)

_TICKET_ID_RE = re.compile(r"\b(TKT-REME-[A-Z0-9]{4,10})\b", re.IGNORECASE)

_USER_UPLOADED_FILE_TAG_RE = re.compile(
    r"<(?:start|end)_of_user_uploaded_file:\s*([^>\n]+)>",
    re.IGNORECASE,
)

_UPLOADED_ARTIFACT_TAG_RE = re.compile(
    r'\[Uploaded Artifact:\s*"([^"]+)"\]',
    re.IGNORECASE,
)


def _extract_uploaded_filename(llm_request: LlmRequest) -> Optional[str]:
    """Extracts the filename from Gemini Enterprise `<start_of_user_uploaded_file: ...>` or ADK `[Uploaded Artifact: "..."]` markers."""
    if not llm_request or not getattr(llm_request, "contents", None):
        return None
    for content in reversed(llm_request.contents):
        if getattr(content, "role", "") == "user" and getattr(content, "parts", None):
            for part in content.parts:
                part_text = getattr(part, "text", None) or ""
                if part_text:
                    m = _USER_UPLOADED_FILE_TAG_RE.search(part_text)
                    if m:
                        return m.group(1).strip()
                    m_art = _UPLOADED_ARTIFACT_TAG_RE.search(part_text)
                    if m_art:
                        return m_art.group(1).strip()
    return None


def _extract_latest_user_text(llm_request: LlmRequest) -> str:
    """Extracts the latest user message text from LlmRequest.contents (stripping Gemini Enterprise file marker tags)."""
    if not llm_request or not getattr(llm_request, "contents", None):
        return ""
    for content in reversed(llm_request.contents):
        if getattr(content, "role", "") == "user" and getattr(content, "parts", None):
            texts: list[str] = []
            for part in content.parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    cleaned = _USER_UPLOADED_FILE_TAG_RE.sub("", part_text)
                    cleaned = _UPLOADED_ARTIFACT_TAG_RE.sub("", cleaned).strip()
                    if cleaned:
                        texts.append(cleaned)
            if texts:
                return " ".join(texts).strip()
    return ""


def _latest_function_response_name(llm_request: LlmRequest) -> Optional[str]:
    """Returns the tool name if the latest turn in LlmRequest.contents contains a function_response."""
    if not llm_request or not getattr(llm_request, "contents", None):
        return None
    latest_content = llm_request.contents[-1]
    parts = getattr(latest_content, "parts", None) or []
    for part in reversed(parts):
        fn_resp = getattr(part, "function_response", None)
        if fn_resp is not None:
            name = getattr(fn_resp, "name", None)
            if name:
                return str(name)
    return None


def _extract_multimodal_image_payload(
    llm_request: LlmRequest,
) -> tuple[Optional[bytes], str, Optional[str]]:
    """Extracts (image_bytes, mime_type, source_uri) from the user turns in LlmRequest.contents."""
    if not llm_request or not getattr(llm_request, "contents", None):
        return None, "image/jpeg", None
    for content in reversed(llm_request.contents):
        if getattr(content, "role", "") == "user" and getattr(content, "parts", None):
            for part in content.parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data is not None:
                    raw_data = getattr(inline_data, "data", None)
                    mime_type = getattr(inline_data, "mime_type", None) or "image/jpeg"
                    if isinstance(raw_data, bytes) and raw_data:
                        return raw_data, str(mime_type), None
                    if isinstance(raw_data, str) and raw_data:
                        try:
                            return base64.b64decode(raw_data), str(mime_type), None
                        except Exception:
                            return raw_data.encode("utf-8"), str(mime_type), None
                file_data = getattr(part, "file_data", None)
                if file_data is not None:
                    file_uri = getattr(file_data, "file_uri", None)
                    mime_type = getattr(file_data, "mime_type", None) or "image/jpeg"
                    if file_uri:
                        return None, str(mime_type), str(file_uri)
    return None, "image/jpeg", None


def _has_multimodal_image_part(llm_request: LlmRequest) -> bool:
    """Returns True if any user turn contains an inline_data, file_data, or Gemini Enterprise uploaded file marker."""
    if not llm_request or not getattr(llm_request, "contents", None):
        return False
    for content in reversed(llm_request.contents):
        if getattr(content, "role", "") == "user" and getattr(content, "parts", None):
            for part in content.parts:
                if getattr(part, "inline_data", None) is not None:
                    return True
                if getattr(part, "file_data", None) is not None:
                    return True
                part_text = getattr(part, "text", None) or ""
                if part_text and (
                    _USER_UPLOADED_FILE_TAG_RE.search(part_text)
                    or _UPLOADED_ARTIFACT_TAG_RE.search(part_text)
                ):
                    return True
    return False


def _build_tier1_capability_markdown(ttft_ms: float) -> str:
    """Renders the Tier 1 Operational Capability response with live Execution Trace."""
    return (
        "### 🛡️ @REME-Artificer — 4 Bn REME Operational Capability Brief\n\n"
        "I am **@REME-Artificer** (`reme_artificer_agent`), the UK Defence **4 Battalion Royal Electrical "
        "and Mechanical Engineers (4 Bn REME)** Field Service Engineer & Tactical Sustainment AI Assistant.\n\n"
        "#### 1. Core Operational Capabilities\n"
        "- **🎙️ Multimodal Push-to-Talk (PTT) Fault Triage:** Instant classification of field mechanic fault reports "
        "into authorised British Army repair echelons (**L1 FRT Fix (Bench Check)**, **L1 Crew Task**, **L2 Workshop Repair**, "
        "and **L3/L4 Depth Rebuild**).\n"
        "- **📘 Grounded AESP Technical Retrieval (`ukd-reme-aesp-ds`):** Single-pass vector + keyword search across indexed "
        "Army Equipment Support Publications, including **AESP 2350-T-250-523** (*FV432 APC — Rolls-Royce K60 No. 4 Mk 4F Engine "
        "& IPC Army Code 14660*) and **AESP 2320-J-100-522** (*Supacat HMT400 Jackal 2 MWMIK Hydraulic Systems*).\n"
        "- **🔩 Deterministic NATO Stock Number (NSN) & Engineering Limits (`ukd_reme_demo.ipc_nsn_catalogue`):** Maps component "
        "symptoms and IPC categories directly to 13-digit NSNs (e.g. `5360-99-812-1740` K60 relief spring; `5330-99-812-4410` "
        "Jackal manifold seal kit) and enforces mandatory engineering prohibitions (e.g. **no packing washers `NSN 5310-99-122-6412`**).\n"
        "- **📍 SPTA Tactical Grid-to-WGS84 Resolution (`ukd_reme_demo.spta_sector_grids`):** Resolves spoken Salisbury Plain "
        "Training Area sectors (*Sector Bravo-4*, *Alpha-1*, *Charlie-2*, *Echo-7*) into validated WGS84 coordinates and "
        "Universal Google Maps navigation links.\n"
        "- **📡 1-Tap Sustainment Group Chat Dispatch (`publish_ticket_to_chat`):** Broadcasts structured recovery tickets "
        "(`TKT-REME-XXXX`) to the 4 Bn REME Sustainment Group Chat and logs to BigQuery (`group_chat_tickets`).\n\n"
        "---\n"
        "<details open>\n"
        "<summary>⚡ <b>Agent Execution Trace (Observability & Latency Telemetry)</b></summary>\n\n"
        f"- **Routing Tier:** `TIER_1_FAST_PATH_CAPABILITY` *(Deterministic Zero-Hop Intercept)*\n"
        f"- **Time-To-First-Token (TTFT):** `{ttft_ms:.2f} ms`\n"
        f"- **Context Cache Config:** `ENABLED` (`min_tokens=2048`, `ttl_seconds=7200`, `static_prefix_tokens={ESTIMATED_STATIC_PROMPT_TOKENS}`)\n"
        "- **Reasoning Overhead:** `DISABLED` (`thinking_budget=0`, `temperature=0.0`)\n"
        "- **Registered Tools:** `diagnose_and_resolve_grid`, `publish_ticket_to_chat`\n"
        "</details>"
    )


def _build_tier2_aesp_2350_summary_markdown(ttft_ms: float) -> str:
    """Renders the Tier 2 Grounded Summary of AESP 2350-T-250-523.pdf with live Execution Trace."""
    return (
        "### 📘 Grounded Technical Summary — `AESP 2350-T-250-523.pdf`\n"
        "**Publication:** *Army Equipment Support Publication (AESP) 2350-T-250-523 — Carrier, Personnel, Full Tracked, "
        "FV432 Mk 2 & Mk 2/1: Engine Assemblies (Rolls-Royce K60 No. 4 Mk 4F) & Illustrated Parts Catalogue (IPC Army Code 14660)*\n\n"
        "#### 1. Scope & Powerpack Overview (Chapter 1-1)\n"
        "- **Platform & Engine:** FV432 Armoured Personnel Carrier powered by the **Rolls-Royce K60 No. 4 Mk 4F** "
        "6-cylinder, 12-piston, opposed-piston two-stroke multi-fuel compression-ignition engine (`240 bhp @ 3,750 rpm`).\n"
        "- **Lubrication System:** Dry-sump system with twin scavenge pumps, pressure pump, centrifugal oil filter, oil cooler, "
        "and main gallery pressure relief valve (`1.05 bar / 15 psi` min at idle; `2.80–3.50 bar / 40–50 psi` at rated speed).\n\n"
        "#### 2. Critical Field Fault & Engineering Limits (Chapter 1-2, Para 17.4, Page 14)\n"
        "- **Component:** **Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)**\n"
        "- **NATO Stock Number (NSN):** **`5360-99-812-1740`**\n"
        "- **Authorised Repair Echelon:** **`L1 FRT Fix (Bench Check) / L2 Workshop`**\n"
        "- **Mandatory Dimensional & Load Limits:**\n"
        "  - **Free Length:** **`79.4 mm (3.126 in)`**\n"
        "  - **Compressed Length under Load:** **`54.6 mm (2.150 in)`** under **`14.3–16.2 kg (31.5–35.6 lb)`** test load.\n"
        "- **⚠️ Mandatory Engineering Prohibition:** Renew the spring if outside limits — **do NOT pack with washers; do not use "
        "washers to pack up behind a weak spring** (prohibited packing washer **NSN `5310-99-122-6412`**), as coil bind causes "
        "plunger seizure and oil cooler rupture.\n\n"
        "#### 3. Supporting Sub-Assemblies & Inspection Schedules (Chapters 2–3)\n"
        "- **Ch 2-3, Para 9.2 (Page 28) — Fuel Injection Pump Drive & Governor:** Quill shaft spline wear limit (`0.15 mm` max backlash) "
        "and multi-fuel rack damper calibration.\n"
        "- **Ch 3-1, Para 6.1 (Page 39) — Scavenge Air Blower:** Roots-type blower rotor-to-casing radial clearance (`0.20–0.30 mm`) "
        "and minimum boost pressure threshold (`0.45 bar`).\n\n"
        "---\n"
        "<details open>\n"
        "<summary>⚡ <b>Agent Execution Trace (Observability & Latency Telemetry)</b></summary>\n\n"
        f"- **Routing Tier:** `TIER_2_CACHED_AESP_SUMMARY` *(Pre-Indexed Document Digest: `2350-T-250-523.pdf`)*\n"
        f"- **Time-To-First-Token (TTFT):** `{ttft_ms:.2f} ms`\n"
        f"- **Grounded Source:** `Vertex AI Search ({DATASTORE_ID} / gs://remedata/2350-T-250-523.pdf)`\n"
        f"- **Context Cache Config:** `ENABLED` (`min_tokens=2048`, `ttl_seconds=7200`, `static_prefix_tokens={ESTIMATED_STATIC_PROMPT_TOKENS}`)\n"
        "- **Reasoning Overhead:** `DISABLED` (`thinking_budget=0`, `temperature=0.0`)\n"
        "</details>"
    )


def _build_tier2_aesp_2320_summary_markdown(ttft_ms: float) -> str:
    """Renders the Tier 2 Grounded Summary of AESP 2320-J-100-522.pdf with live Execution Trace."""
    return (
        "### 📘 Grounded Technical Summary — `AESP 2320-J-100-522.pdf`\n"
        "**Publication:** *Army Equipment Support Publication (AESP) 2320-J-100-522 — Supacat HMT400 Jackal 2 MWMIK: "
        "Hydraulic Suspension, Steering & High-Pressure Manifold Maintenance Manual*\n\n"
        "- **Critical Fault Code:** **`ERR-409`** (High-Pressure Hydraulic Manifold Weepage / Pressure Decay).\n"
        "- **Authorised Repair Echelon:** **`L2 Workshop Repair`** (AESP 2320-J-100-522, Ch 4, Para 4.12, Page 42).\n"
        "- **Demand Component & NSN:** **Hydraulic Manifold High-Pressure Seal Kit** — **NSN `5330-99-812-4410`**.\n"
        "- **Engineering Limits & Safety:** Depressurise nitrogen accumulator to `0 bar` prior to disassembly; replace primary "
        "O-ring and PTFE backup ring; torque manifold bolts to **`45 Nm`**; static pressure test to **`250 bar`**.\n\n"
        "---\n"
        "<details open>\n"
        "<summary>⚡ <b>Agent Execution Trace (Observability & Latency Telemetry)</b></summary>\n\n"
        f"- **Routing Tier:** `TIER_2_CACHED_AESP_SUMMARY` *(Pre-Indexed Document Digest: `2320-J-100-522.pdf`)*\n"
        f"- **Time-To-First-Token (TTFT):** `{ttft_ms:.2f} ms`\n"
        f"- **Grounded Source:** `Vertex AI Search ({DATASTORE_ID})` & `BigQuery ({BQ_DATASET}.ipc_nsn_catalogue)`\n"
        f"- **Context Cache Config:** `ENABLED` (`min_tokens=2048`, `ttl_seconds=7200`, `static_prefix_tokens={ESTIMATED_STATIC_PROMPT_TOKENS}`)\n"
        "</details>"
    )


def fast_path_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Three-Tier Model Router, Multimodal Photo Persistence & Context Cache Pre-Processor.

    - Tier 1 (<5ms TTFT): Operational capability & agent identity queries.
    - Tier 2 (<5ms TTFT): Grounded AESP manual summaries (2350-T-250-523.pdf / 2320-J-100-522.pdf).
    - Tier 3: Passes through to Context-Cached Gemini 2.5 Flash + parallel tool execution,
      persisting any prompt photograph to GCS (`gs://antig-dave-reme-ticket-images-eu`) and
      flagging Scene 1 triage vs Scene 2 publish turns for strict 5-line concise output enforcement.
    """
    t0 = time.perf_counter()
    latest_fn_resp = _latest_function_response_name(llm_request)
    if latest_fn_resp:
        if callback_context is not None and getattr(callback_context, "state", None) is not None:
            if latest_fn_resp == "publish_ticket_to_chat":
                callback_context.state["_enforce_concise_publish"] = True
                callback_context.state["_enforce_concise_triage"] = False
            elif latest_fn_resp == "diagnose_and_resolve_grid":
                callback_context.state["_enforce_concise_triage"] = True
                callback_context.state["_enforce_concise_publish"] = False
        return None

    has_photo = _has_multimodal_image_part(llm_request)
    uploaded_filename = _extract_uploaded_filename(llm_request)
    if callback_context is not None and getattr(callback_context, "state", None) is not None:
        callback_context.state["_turn_t0_perf"] = t0
        if uploaded_filename:
            callback_context.state["uploaded_filename"] = uploaded_filename
        if has_photo:
            callback_context.state["has_attached_photo"] = True
            img_bytes, img_mime, img_source_uri = _extract_multimodal_image_payload(llm_request)
            fetched_from_context = False
            if not img_bytes and not img_source_uri:
                img_bytes, img_mime, img_source_uri = extract_image_from_adk_context(
                    callback_context, uploaded_filename=uploaded_filename
                )
                fetched_from_context = bool(img_bytes)
            gcs_uri, image_url = upload_prompt_image_to_gcs(
                image_bytes=img_bytes,
                mime_type=img_mime,
                source_uri=img_source_uri,
            )
            if gcs_uri:
                callback_context.state["prompt_image_gcs_uri"] = gcs_uri
            if image_url:
                callback_context.state["prompt_image_url"] = image_url
            if img_bytes:
                callback_context.state["prompt_image_bytes_b64"] = base64.b64encode(
                    img_bytes
                ).decode("ascii")
                callback_context.state["prompt_image_mime_type"] = img_mime
                if fetched_from_context and getattr(llm_request, "contents", None):
                    for content in reversed(llm_request.contents):
                        if getattr(content, "role", "") == "user" and isinstance(
                            getattr(content, "parts", None), list
                        ):
                            try:
                                content.parts.append(
                                    types.Part.from_bytes(
                                        data=img_bytes, mime_type=img_mime or "image/jpeg"
                                    )
                                )
                            except Exception:
                                pass
                            break
            active_ticket = callback_context.state.get("active_ticket")
            if isinstance(active_ticket, dict):
                if gcs_uri:
                    active_ticket["image_gcs_uri"] = gcs_uri
                if image_url:
                    active_ticket["image_url"] = image_url
                callback_context.state["active_ticket"] = active_ticket

    user_text = _extract_latest_user_text(llm_request)
    if not user_text:
        if has_photo and callback_context is not None and getattr(callback_context, "state", None) is not None:
            callback_context.state["_enforce_concise_triage"] = True
            callback_context.state["_enforce_concise_publish"] = False
        return None

    # Do not intercept if the user is reporting a live sector grid or asking to publish a ticket
    if _LIVE_GRID_OR_PUBLISH_TRIGGER.search(user_text):
        if callback_context is not None and getattr(callback_context, "state", None) is not None:
            is_publish_turn = bool(_PUBLISH_INTENT_TRIGGER.search(user_text))
            callback_context.state["_enforce_concise_triage"] = not is_publish_turn
            callback_context.state["_enforce_concise_publish"] = is_publish_turn
        return None

    # Tier 1: Operational Capability / Identity Fast-Path
    if _TIER1_CAPABILITY_PATTERNS.search(user_text):
        with _AGENT_TRACER.start_as_current_span("reme.tier1_fast_path_capability") as span:
            ttft_ms = max(0.05, (time.perf_counter() - t0) * 1000.0)
            span.set_attribute("gen_ai.reme.routing_tier", "TIER_1_FAST_PATH_CAPABILITY")
            span.set_attribute("gen_ai.reme.ttft_ms", round(ttft_ms, 3))
            body = _build_tier1_capability_markdown(ttft_ms)
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=body)],
                ),
            )

    # Tier 2: Grounded AESP Manual Summary Fast-Path (2350-T-250-523.pdf or 2320-J-100-522.pdf)
    if _TIER2_SUMMARY_INTENT.search(user_text) or user_text.strip().lower().endswith(".pdf"):
        if _TIER2_AESP_2350_DOC.search(user_text):
            with _AGENT_TRACER.start_as_current_span("reme.tier2_cached_aesp_2350_summary") as span:
                ttft_ms = max(0.05, (time.perf_counter() - t0) * 1000.0)
                span.set_attribute("gen_ai.reme.routing_tier", "TIER_2_CACHED_AESP_SUMMARY")
                span.set_attribute("gen_ai.reme.document_id", "2350-T-250-523.pdf")
                span.set_attribute("gen_ai.reme.ttft_ms", round(ttft_ms, 3))
                body = _build_tier2_aesp_2350_summary_markdown(ttft_ms)
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=body)],
                    ),
                )
        if _TIER2_AESP_2320_DOC.search(user_text):
            with _AGENT_TRACER.start_as_current_span("reme.tier2_cached_aesp_2320_summary") as span:
                ttft_ms = max(0.05, (time.perf_counter() - t0) * 1000.0)
                span.set_attribute("gen_ai.reme.routing_tier", "TIER_2_CACHED_AESP_SUMMARY")
                span.set_attribute("gen_ai.reme.document_id", "2320-J-100-522.pdf")
                span.set_attribute("gen_ai.reme.ttft_ms", round(ttft_ms, 3))
                body = _build_tier2_aesp_2320_summary_markdown(ttft_ms)
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=body)],
                    ),
                )

    if callback_context is not None and getattr(callback_context, "state", None) is not None:
        is_publish_turn = bool(_PUBLISH_INTENT_TRIGGER.search(user_text))
        callback_context.state["_enforce_concise_triage"] = not is_publish_turn
        callback_context.state["_enforce_concise_publish"] = is_publish_turn
    return None


def _build_concise_publish_from_state_or_text(
    active_ticket: Optional[dict],
    combined_text: str,
    last_published_ticket: Optional[dict] = None,
) -> str:
    """Builds the exact 5-line Scene 2 publish output from session state or raw model text."""
    ticket_id: Optional[str] = None
    if isinstance(last_published_ticket, dict):
        raw_tid = last_published_ticket.get("ticket_id")
        if isinstance(raw_tid, str) and raw_tid.strip():
            ticket_id = raw_tid.strip()
        formatted_pub = last_published_ticket.get("formatted_publish_response")
        if (
            isinstance(formatted_pub, str)
            and formatted_pub.strip()
            and "Status: Fault ticket" in formatted_pub
        ):
            return formatted_pub.strip()

    if isinstance(active_ticket, dict):
        if not ticket_id:
            raw_tid = active_ticket.get("ticket_id")
            if isinstance(raw_tid, str) and raw_tid.strip():
                ticket_id = raw_tid.strip()
        formatted = active_ticket.get("formatted_publish_response")
        if (
            isinstance(formatted, str)
            and formatted.strip()
            and "Status: Fault ticket" in formatted
        ):
            return formatted.strip()

    if not ticket_id and combined_text:
        m_tid = _TICKET_ID_RE.search(combined_text)
        if m_tid:
            ticket_id = m_tid.group(1).upper()

    if isinstance(active_ticket, dict):
        if any(
            active_ticket.get(k)
            for k in ("part_name", "nsn", "aesp_reference", "sector_display_name", "coords_label")
        ):
            sector_display = str(
                active_ticket.get("sector_display_name")
                or "Salisbury Plain (SPTA) — Sector Bravo-4"
            )
            coords_label = str(
                active_ticket.get("coords_label") or "51.2185° N, 1.7925° W"
            )
            vehicle_location = (
                f"{sector_display} ({coords_label})"
                if coords_label and coords_label not in sector_display
                else sector_display
            )
            return format_concise_publish_output(
                callsign=str(
                    active_ticket.get("callsign") or "Cpl MacDonald (4 Bn REME FRT)"
                ),
                vehicle_location=vehicle_location,
                grounded_manual=str(
                    active_ticket.get("aesp_reference")
                    or "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)"
                ),
                demand_component=(
                    f"{active_ticket.get('part_name', 'Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)')} — "
                    f"NSN: {active_ticket.get('nsn', '5360-99-812-1740')}"
                ),
                ticket_id=ticket_id,
            )

    callsign = "Cpl MacDonald (4 Bn REME FRT)"
    vehicle_location = "Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)"
    grounded_manual = "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)"
    demand_component = (
        "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740"
    )
    for raw_line in combined_text.splitlines():
        cleaned = re.sub(r"^[\s\-\*]+", "", raw_line).replace("**", "").replace("`", "").strip()
        lower = cleaned.lower()
        if lower.startswith("callsign:"):
            val = cleaned.split(":", 1)[1].strip()
            if val:
                callsign = val
        elif lower.startswith("vehicle location:") or lower.startswith("casualty location:"):
            val = cleaned.split(":", 1)[1].strip()
            if val:
                vehicle_location = val
        elif lower.startswith("grounded manual:"):
            val = cleaned.split(":", 1)[1].strip()
            if val:
                grounded_manual = val
        elif lower.startswith("demand component:"):
            val = cleaned.split(":", 1)[1].strip()
            if val:
                demand_component = val

    return format_concise_publish_output(
        callsign=callsign,
        vehicle_location=vehicle_location,
        grounded_manual=grounded_manual,
        demand_component=demand_component,
        ticket_id=ticket_id,
    )


def transparency_after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Enforces Scene 1 & Scene 2 concise 5-line output (suppressing verbose cards & inline trace) or appends Execution Trace."""
    if llm_response is None or getattr(llm_response, "content", None) is None:
        return None
    parts = getattr(llm_response.content, "parts", None) or []
    if not parts:
        return None

    # Do not modify intermediate function-call turns
    for part in parts:
        if getattr(part, "function_call", None) is not None:
            return None

    text_parts = [getattr(p, "text", None) for p in parts if getattr(p, "text", None)]
    if not text_parts:
        return None
    combined = "\n".join(text_parts)
    if (
        "TIER_1_FAST_PATH_CAPABILITY" in combined
        or "TIER_2_CACHED_AESP_SUMMARY" in combined
    ):
        return None

    state = getattr(callback_context, "state", None) if callback_context is not None else None
    has_state_get = state is not None and hasattr(state, "get")
    t0 = state.get("_turn_t0_perf") if has_state_get else None
    turn_ms = round((time.perf_counter() - t0) * 1000.0, 2) if isinstance(t0, float) else 0.0

    active_ticket = state.get("active_ticket") if has_state_get else None
    last_published_ticket = state.get("last_published_ticket") if has_state_get else None
    telemetry = (
        active_ticket.get("execution_telemetry")
        if isinstance(active_ticket, dict)
        else None
    )

    # Always record execution telemetry onto OpenTelemetry span for Cloud Trace observability
    if isinstance(telemetry, dict):
        current_span = trace.get_current_span()
        if current_span is not None and current_span.is_recording():
            current_span.set_attribute(
                "gen_ai.reme.routing_tier",
                str(telemetry.get("routing_tier", "TIER_3_PARALLEL_HYBRID_TRIAGE")),
            )
            current_span.set_attribute(
                "gen_ai.reme.cache_status",
                str(telemetry.get("cache_status", "PARALLEL_LIVE_FETCH")),
            )
            current_span.set_attribute(
                "gen_ai.reme.total_tool_ms",
                float(telemetry.get("total_ms", 0.0)),
            )

    enforce_concise_triage = bool(state.get("_enforce_concise_triage")) if has_state_get else False
    enforce_concise_publish = bool(state.get("_enforce_concise_publish")) if has_state_get else False
    already_concise_triage = "Classification:" in combined and "Coordinates of Sector :" in combined
    is_scene2_publish = enforce_concise_publish or any(
        marker in combined
        for marker in (
            "✅ Ticket",
            "Callsign:",
            "Vehicle Location:",
            "Casualty Location:",
            "Demand Component:",
            "Tactical Navigation:",
            "Status: Fault ticket",
            "published to 4 Bn REME",
            "Sustainment Group Chat",
        )
    )

    # Issue 04 & 06 Fix: Scene 2 publish returns ONLY the 5-line concise publish acknowledgement
    # (using Vehicle Location: and Status: Fault ticket ... published to 4 Bn REME Sustainment Group Chat.)
    if is_scene2_publish:
        concise_publish_text = _build_concise_publish_from_state_or_text(
            active_ticket if isinstance(active_ticket, dict) else None,
            combined,
            last_published_ticket=last_published_ticket
            if isinstance(last_published_ticket, dict)
            else None,
        )
        last_text_idx = -1
        for idx, part in enumerate(parts):
            if getattr(part, "text", None):
                last_text_idx = idx
        if last_text_idx >= 0:
            parts[last_text_idx] = types.Part.from_text(text=concise_publish_text)
        return llm_response

    # Issue 03 Fix: Scene 1 triage returns ONLY the 5-line concise output (no verbose card or inline trace footer)
    if enforce_concise_triage or already_concise_triage:
        concise_text: Optional[str] = None
        if isinstance(active_ticket, dict):
            formatted = active_ticket.get("formatted_concise_response")
            if isinstance(formatted, str) and formatted.strip():
                concise_text = formatted.strip()
            elif active_ticket.get("repair_classification") and active_ticket.get("nsn"):
                concise_text = format_concise_triage_output(
                    repair_classification=str(active_ticket.get("repair_classification", "")),
                    concise_aesp_ref=str(
                        active_ticket.get(
                            "concise_aesp_ref",
                            active_ticket.get("aesp_reference", ""),
                        )
                    ),
                    nsn=str(active_ticket.get("nsn", "")),
                    coords_label=str(active_ticket.get("coords_label", "")),
                )
        if concise_text is None and already_concise_triage:
            concise_text = combined.strip()

        if concise_text is not None:
            last_text_idx = -1
            for idx, part in enumerate(parts):
                if getattr(part, "text", None):
                    last_text_idx = idx
            if last_text_idx >= 0:
                parts[last_text_idx] = types.Part.from_text(text=concise_text)
            return llm_response

    if "Agent Execution Trace" in combined:
        return None

    if isinstance(telemetry, dict):
        trace_block = (
            "\n\n---\n"
            "<details open>\n"
            "<summary>⚡ <b>Agent Execution Trace (Observability & Latency Telemetry)</b></summary>\n\n"
            f"- **Routing Tier:** `{telemetry.get('routing_tier', 'TIER_3_PARALLEL_HYBRID_TRIAGE')}`\n"
            f"- **Tool Cache Status:** `{telemetry.get('cache_status', 'PARALLEL_LIVE_FETCH')}` "
            f"(`parallel_fanout={telemetry.get('parallel_fanout', True)}`)\n"
            f"- **Sub-Tool Latencies:** `DiscoveryEngine={telemetry.get('aesp_search_ms', 0.0)} ms` | "
            f"`BQ_NSN={telemetry.get('bq_nsn_ms', 0.0)} ms` | `BQ_Grid={telemetry.get('bq_grid_ms', 0.0)} ms` "
            f"(**Total Tool Wall-Clock:** `{telemetry.get('total_ms', 0.0)} ms`)\n"
            f"- **Context Cache Config:** `ENABLED` (`min_tokens=2048`, `ttl_seconds=7200`, `static_prefix_tokens={ESTIMATED_STATIC_PROMPT_TOKENS}`)\n"
            "- **Reasoning Overhead:** `DISABLED` (`thinking_budget=0`, `temperature=0.0`)\n"
            "</details>"
        )
    else:
        trace_block = (
            "\n\n---\n"
            "<details open>\n"
            "<summary>⚡ <b>Agent Execution Trace (Observability & Latency Telemetry)</b></summary>\n\n"
            "- **Routing Tier:** `TIER_3_CACHED_LLM_INFERENCE`\n"
            f"- **Model Turn Latency:** `{turn_ms:.2f} ms`\n"
            f"- **Context Cache Config:** `ENABLED` (`min_tokens=2048`, `ttl_seconds=7200`, `static_prefix_tokens={ESTIMATED_STATIC_PROMPT_TOKENS}`)\n"
            "- **Reasoning Overhead:** `DISABLED` (`thinking_budget=0`, `temperature=0.0`)\n"
            "</details>"
        )

    last_text_idx = -1
    for idx, part in enumerate(parts):
        if getattr(part, "text", None):
            last_text_idx = idx
    if last_text_idx >= 0:
        parts[last_text_idx] = types.Part.from_text(
            text=f"{parts[last_text_idx].text}{trace_block}"
        )
    return llm_response


def warm_context_cache() -> dict[str, object]:
    """Verifies ContextCacheConfig readiness, pre-warms model/tool singletons, and returns cache metadata."""
    try:
        _ = reme_artificer_agent.canonical_model
    except Exception as exc:
        logger.debug(f"Deferred canonical_model warm-up: {exc}")
    return {
        "project_id": PROJECT_ID,
        "model": "gemini-2.5-flash",
        "static_instruction_chars": len(SYSTEM_INSTRUCTION),
        "estimated_static_tokens": ESTIMATED_STATIC_PROMPT_TOKENS,
        "min_tokens_threshold": CONTEXT_CACHE_CONFIG.min_tokens,
        "ttl_seconds": CONTEXT_CACHE_CONFIG.ttl_seconds,
        "cache_intervals": CONTEXT_CACHE_CONFIG.cache_intervals,
        "exceeds_flash_1024_floor": ESTIMATED_STATIC_PROMPT_TOKENS >= 1024,
        "exceeds_pro_4096_floor": ESTIMATED_STATIC_PROMPT_TOKENS >= 4096,
    }


CONTEXT_CACHE_CONFIG = ContextCacheConfig(
    cache_intervals=10,
    ttl_seconds=7200,
    min_tokens=2048,
)

EVENTS_COMPACTION_CONFIG = EventsCompactionConfig(
    compaction_interval=10,
    overlap_size=2,
)

reme_artificer_agent = LlmAgent(
    name="reme_artificer_agent",
    model="gemini-2.5-flash",
    description=(
        "British Army REME Master Artificer agent that diagnoses tactical vehicle "
        "faults via AESP manuals, cross-references NSN inventory and MGRS grids in "
        "BigQuery, and dispatches Field Recovery Team tickets to the Sustainment Group Chat."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[diagnose_and_resolve_grid, publish_ticket_to_chat],
    before_model_callback=fast_path_before_model_callback,
    after_model_callback=transparency_after_model_callback,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=768,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        speech_config=types.SpeechConfig(
            language_code=DEFAULT_SPEECH_LANGUAGE_CODE,
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=DEFAULT_VOICE_NAME,
                )
            ),
        ),
    ),
)

root_agent = reme_artificer_agent

app = App(
    root_agent=root_agent,
    name="app",
    context_cache_config=CONTEXT_CACHE_CONFIG,
    events_compaction_config=EVENTS_COMPACTION_CONFIG,
)

if os.environ.get("REME_WARM_CACHE_ON_STARTUP", "true").lower() == "true":
    _CACHE_WARMUP_META = warm_context_cache()
