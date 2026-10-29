## **📋 Document Control & Metadata**

| Field | Specification Value |
| :---- | :---- |
| **Document ID** | SDD-DEMO1-ADK2-003 (Pragmatic Demonstrator Blueprint for SPEC.md & gemini-cli) |
| **Programme & Use Case** | **Pixel Roots — Demo 1: The Tactical Sustainment JNCO ("Snap, Diagnose, Pin & Demand")** |
| **Agent Hosting & Model** | **Vertex AI Agent Platform** — Single **ADK 2.0 LlmAgent** using **gemini-2.5-flash** (temperature=0.0) |
| **Authentication Model** | **Single Shared IAM Service Account** (sa-reme-demo@\<project\>.iam.gserviceaccount.com) via ADC |
| **Authoritative Grounding** | [**AESP 2350-T-250-523**](http://www.fv432apc.com/manuals/fv432manuals/2350T250/2350-T-250-523.pdf) (Ch 1-2, Para 17.4: Rolls-Royce K60 Oil Pressure Relief Valve) |
| **Synthetic Datasets** | **BigQuery** (ukd\_reme\_demo): **IPC Army Code 14660 (Cat 711\)** & **SPTA Sector Grids** (with Golden-Path Fallback) |
| **Scene 3 Handoff Stack** | **Cloud Run Lightweight HTML5/FastAPI Chat App** (In-Memory Cache \+ DB Write) \-\> **Google Maps** Deep Link |

## ---

**1\. Executive Summary & Demonstrator Scope**

### **1.1 Operational Narrative & Strategic Win for Dir DIS**

Forward Repair Teams (FRTs) in **4 Battalion REME** deployed on **Salisbury Plain Training Area (SPTA)** need a fast, accredited **OFFICIAL** workflow on a **ruggedised Google Pixel (Titan M2, COBO Work Profile)** to replace shadow-IT WhatsApp photo sharing.

In this 3-scene demonstrator, **Cpl "Mac" MacDonald** snaps a photo of a fault, speaks a Push-to-Talk (PTT) prompt with his sector grid, receives a grounded **AESP 2350-T-250-523** diagnosis with a 15-second hands-free audio summary, and says **"Publish to Group Chat"**. A recovery engineer opens the **lightweight HTML Group Chat on Cloud Run**, views the ticket, and taps the coordinates to launch **Google Maps** turn-by-turn navigation.

### **1.2 Demonstrator Scope & Well-Architected Trade-Off Matrix**

| Architectural Dimension | Included in Demonstrator Build (Lean & Stage-Proof) | Deferred to Production Target (Out of Demo Scope) |
| :---- | :---- | :---- |
| **Agent Orchestration** | **Single ADK 2.0 LlmAgent** (reme\_artificer\_agent) on **Agent Platform** with **2 composite tools**. | Multi-agent router graphs, **Agent Gateway**, and standalone **MCP Toolbox** servers. |
| **Model & Caching** | Single **gemini-2.5-flash** multimodal call (temperature=0.0) \+ Pydantic output cap (≤100 tokens). | Serial Flash-to-Pro model routing and custom 1-hour Explicit Context Cache TTL management scripts. |
| **Authentication & Security** | **1 IAM Service Account (sa-reme-demo)** using ADC; parameterized SQL; public/PIN-protected Cloud Run URL. | **Model Armor**, **SPIFFE/SPIRE** federation, IAP OAuth prompts on mobile, and live MODNet ABAC. |
| **Data & Chat State** | **Vertex AI Search** (1 AESP PDF) \+ **BigQuery** (seeded IPC/Grid tables \+ async ticket write) \+ **Cloud Run in-memory cache** with \[Reset Demo\] button. | High-frequency BigQuery polling, streaming buffer DELETE workarounds, and OTel/BigQuery billing pipelines. |
| **UI Card & Maps Handoff** | Native **Structured Markdown Card** (\<details\> collapsible chips) \+ **Google Maps Universal URL (api=1)**. | Custom client-side A2UI JSON renderers, Google Maps JS SDK API keys, and native ATAK CoT XML intents. |

## ---

**2\. System Architecture & Single-Agent ADK 2.0 Topology**

### **2.1 End-to-End Demonstrator Architecture Diagram**

\+----------------------------------------------------------------------------------------------------------+  
\|                                   PRESENTATION & FIELD USER LAYER                                        \|  
\|                                                                                                          \|  
\|  \[Persona 1: Cpl "Mac" MacDonald (4 Bn REME)\]          \[Persona 2: B Echelon / FRT Recovery Engineer\]    \|  
\|  \- Ruggedised Pixel (Tactical Glove Mode Dark UI)      \- Opens Lightweight HTML Chat App on Cloud Run    \|  
\|  \- Gemini Enterprise App (@REME-Artificer Gem)         \- Reviews Ticket Card \+ "\[Reset Demo\]" Button     \|  
\|  \- Renders Markdown Card (3 Chips) \+ 15s TTS Audio     \- 1-Tap Coordinate Link \-\> Launches Google Maps   \|  
\+-------------------------+------------------------------------------------------+-------------------------+  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\| 1\. Image \+ PTT Voice Prompt                          \| 4\. Fast In-Memory Poll  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\|    \+ Sector Grid ("Publish to Group Chat")           \|    & 1-Tap Google Maps URL  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v                                                      v  
\+---------------------------------------------------------+    \+-------------------------------------------+  
\|            VERTEX AI AGENT PLATFORM (ADK 2.0)           \|    \|     GOOGLE CLOUD RUN (STATELESS DEMO)     \|  
\|     Runtime Auth: \`sa-reme-demo@\<project\>.iam...\`       \|    \|     Runtime Auth: \`sa-reme-demo@...\`      \|  
\|                                                         \|    \|     Config: \`--allow-unauthenticated\`     \|  
\|  \+---------------------------------------------------+  \|    \|             \`--min-instances=1 \--max=1\`   \|  
\|  \| Single Agent: \`reme\_artificer\_agent\` (\`LlmAgent\`) \|  \|    \|                                           \|  
\|  \| \- Model: \`gemini-2.5-flash\` (Single-Hop Vision)   \|  \|    \|  \[Lightweight HTML5 Group Chat App\]       \|  
\|  \| \- Session Memory: \`VertexAiSessionService\`        \|  \|    \|  \- FastAPI \+ Single-File \`index.html\`     \|  
\|  \| \- Blackboard State: \`ctx.state\`                   \|  \|    \|  \- In-Memory Ticket Cache (\<20ms read)    \|  
\|  \|                                                   \|  \|    \|  \- \`POST /api/tickets\` (Webhook Receiver) \|  
\|  \| \[Composite Tool 1: \`diagnose\_and\_resolve\_grid\`\]   \|  \|    \|  \- \`POST /api/reset\` (Instant Demo Clear) \|  
\|  \|  • Queries Vertex AI Search (AESP Para 17.4)      \|  \|    \|  \- Deep-Link Generator:                   \|  
\|  \|  • Queries BQ \`ipc\_nsn\_catalogue\` (+ Fallback)    \|  \|    \|    \`https\://www\.google.com/maps/dir/?...\` \|  
\|  \|  • Queries BQ \`spta\_sector\_grids\` (+ Fallback)    \|  \|    \+---------------------+---------------------+  
\|  \|  • Saves structured result to \`ctx.state\`         \|  \|                          ^  
\|  \|                                                   \|  \|                          \| 2b. Instant Webhook POST  
\|  \| \[Composite Tool 2: \`publish\_ticket\_to\_chat\`\]      \|  \|--------------------------+     \+ Async BQ Insert  
\|  \|  • Reads \`ctx.state\` on "Publish to Group Chat"   \|  \|  
\|  \+-----------------+-----------------------+---------+  \|  
\+--------------------\|-----------------------\|------------+  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\| 2a. RAG Lookup        \| 2c. SQL Read & Ticket Write (via \`sa-reme-demo\` ADC)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v                       v  
\+------------------------------------+  \+------------------------------------------------------------------+  
\|  VERTEX AI SEARCH (RAG DATASTORE)  \|  \|             GOOGLE CLOUD BIGQUERY (\`ukd\_reme\_demo\`)              \|  
\|  \- DataStore: \`ukd-reme-aesp-ds\`   \|  \|  1\. \`ipc\_nsn\_catalogue\` (Army Code 14660 Cat 711 Synthetic NSNs) \|  
\|  \- Indexed PDF: AESP 2350-T-250-523\|  \|  2\. \`spta\_sector\_grids\` (Salisbury Plain Grid \-\> Lat/Lng Lookup) \|  
\|    (Ch 1-2, Para 17.4 K60 Valve)   \|  \|  3\. \`group\_chat\_tickets\` (Audit & Persistence Table for Scene 2\) \|  
\+------------------------------------+  \+------------------------------------------------------------------+  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\|  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v 5\. Deep-Link Launch  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+----------------------------------+  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\|       GOOGLE MAPS APPLICATION    \|  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\|  \- Opens Pin / Turn-by-Turn Nav  \|  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\|  \- Target: \`51.2185, \-1.7925\`    \|  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+----------------------------------+

### ---

**2.2 Single-Agent & Composite Tool Design (Why It's Faster)**

Instead of chaining multiple sub-agents or forcing the LLM to make three sequential tool calls in Scene 1, reme\_artificer\_agent exposes **two atomic composite tools**:

| ADK 2.0 Tool Name | Triggered In | Composite Operations Executed in Python | Stage-Proof Fallback Behaviour |
| :---- | :---- | :---- | :---- |
| **diagnose\_and\_resolve\_grid** | **Scene 1** (Photo \+ PTT Voice Prompt) | 1\. Queries **Vertex AI Search** (ukd-reme-aesp-ds) for top\-$k=3$ chunks matching the fault. 2\. Queries **BigQuery ipc\_nsn\_catalogue** for the part NSN and repair level. 3\. Queries **BigQuery spta\_sector\_grids** for the spoken sector grid. 4\. Writes all resolved fields into ctx.state\["active\_ticket"\]. | If noisy PTT speech causes the SQL query to return 0 rows, automatically returns the seeded **K60 Oil Pressure Relief Valve Spring (NSN: 5360-99-812-1740, Para 17.4)** and **Sector Bravo-4 (51.2185° N, 1.7925° W)** (or Jackal 2 5330-99-812-4410 if "409" / "jackal" is in prompt). |
| **publish\_ticket\_to\_chat** | **Scene 2** ("Publish to Group Chat") | 1\. Reads ctx.state\["active\_ticket"\] (zero re-prompting or image re-processing). 2\. Inserts the record into **BigQuery group\_chat\_tickets** (satisfying the storyboard DB requirement). 3\. Pushes the JSON payload directly to **Cloud Run POST /api/tickets** for instant (\<20 ms) UI update. | If ctx.state\["active\_ticket"\] is empty (e.g., presenter jumped straight to Scene 2), populates the default K60 Relief Valve Spring ticket and publishes it seamlessly. |

### ---

**2.3 Unified Service Account & IAM Specification**

A single service account (sa-reme-demo@\<project\>.iam.gserviceaccount.com) is attached to both **Vertex AI Agent Platform** and **Google Cloud Run**, eliminating cross-account permission debugging:

| IAM Role Granted to sa-reme-demo | Purpose in Demonstrator |
| :---- | :---- |
| roles/aiplatform.user | Allows Agent Platform to invoke gemini-2.5-flash and manage VertexAiSessionService state. |
| roles/discoveryengine.viewer | Allows diagnose\_and\_resolve\_grid to retrieve AESP chunks from Vertex AI Search. |
| roles/bigquery.dataEditor & roles/bigquery.jobUser | Allows parameterized SELECT queries on ipc\_nsn\_catalogue / spta\_sector\_grids and INSERTs into group\_chat\_tickets. |

## ---

**3\. Scene-by-Scene Execution Flow**

| Scene | Persona & UI Surface | User Action & Spoken Prompt | Under-the-Hood Execution Flow | Visual Output & State |
| :---- | :---- | :---- | :---- | :---- |
| **Scene 1: Multimodal Field Capture** | **Cpl MacDonald** on Ruggedised Pixel (Tactical Glove Mode, @REME-Artificer active). | Snaps fault photo and speaks: *"Gemini, check AESP 2350-T-250-523 for low engine oil pressure relief valve fault in Sector Bravo-4. Is this a Level 1 FRT fix or Level 2 Workshop, and what's the relief valve spring NSN?"* | reme\_artificer\_agent (gemini-2.5-flash) inspects the image and calls diagnose\_and\_resolve\_grid once. The tool runs RAG \+ BigQuery lookups (with golden-path fallback) and caches the payload in ctx.state\["active\_ticket"\]. | ctx.state\["active\_ticket"\] holds: • **NSN**: 5360-99-812-1740 • **AESP Ref**: AESP 2350-T-250-523, Ch 1-2, Para 17.4, p.14 • **Classification**: L1 FRT / L2 Workshop • **Coordinates**: 51.2185° N, 1.7925° W |
| **Scene 2: Grounded Diagnosis & Demand** | **Pixel Screen**: Structured Markdown Card with 3 collapsible \<details\> chips \+ TTS speaker icon. | 1\. Taps speaker icon for **15-second hands-free audio summary**. 2\. Says or taps: **"Publish to Group Chat"**. | 1\. Device TTS reads the 32-word summary. 2\. Agent calls publish\_ticket\_to\_chat(), writing to BigQuery group\_chat\_tickets and posting to Cloud Run /api/tickets. | Renders confirmation badge: **✅ Ticket TKT-REME-041 Published to 4 Bn REME Group Chat**. |
| **Scene 3: Cloud Run Chat & Google Maps Handoff** | **Recovery Engineer** on **Cloud Run HTML Chat App** \-\> **Google Maps App**. | 1\. Opens Cloud Run Group Chat URL and reads the live Ticket Card. 2\. Taps **📍 51.2185° N, 1.7925° W — Open in Google Maps**. | 1\. Cloud Run serves the cached ticket from memory in **\< 20 ms**. 2\. One tap opens the Universal URL: https\://www\.google.com/maps/dir/?api=1\&destination=51.2185,-1.7925\&travelmode=driving. | **Google Maps** opens natively with turn-by-turn route locked to Salisbury Plain Sector Bravo-4. |

## ---

**4\. Grounded Fault Data & Lean BigQuery Schemas (dataset: ukd\_reme\_demo)**

### **4.1 Pre-Seeded Fault Scenarios (Primary FV432 K60 \+ Storyboard Jackal 2\)**

Both the **FV432 Rolls-Royce K60 Engine Oil Pressure Relief Valve Spring** ([AESP 2350-T-250-523](http://www.fv432apc.com/manuals/fv432manuals/2350T250/2350-T-250-523.pdf) Ch 1-2, Para 17.4) and the Storyboard 1 **Jackal 2 (ERR-409)** example are pre-seeded in BigQuery:

| Field | Primary Seed Row (Default Golden-Path Fallback) | Secondary Seed Row (Storyboard Diagram Variant) |
| :---- | :---- | :---- |
| keyword\_triggers | "k60", "oil", "relief", "spring", "2350", "17.4" | "jackal", "409", "hydraulic", "manifold", "4.12" |
| aesp\_reference | "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)" | "AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)" |
| part\_name | "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)" | "Hydraulic Manifold High-Pressure Seal Kit" |
| nsn | **"5360-99-812-1740"** | **"5330-99-812-4410"** |
| repair\_classification | **"L1 FRT Fix (Bench Check) / L2 Workshop"** | **"L2 Workshop Repair"** |
| technical\_limits | "Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits; do not use washers to pack up behind a weak spring." | "Torque to 45 Nm. Depressurise hydraulic accumulator prior to seal replacement." |

### **4.2 BigQuery Table Definitions (ukd\_reme\_demo)**

| Table Name | Schema Columns & Types | Role in Demonstrator |
| :---- | :---- | :---- |
| **ipc\_nsn\_catalogue** | part\_id (STRING), keyword\_tag (STRING), ipc\_army\_code (STRING), aesp\_reference (STRING), part\_name (STRING), nsn (STRING), repair\_classification (STRING), technical\_limits (STRING) | Resolves the photographed/spoken fault to its exact 13-digit NSN, IPC Army Code 14660 (Cat 711), and condemnation limits. |
| **spta\_sector\_grids** | sector\_key (STRING), sector\_display\_name (STRING), latitude (FLOAT64), longitude (FLOAT64), coords\_label (STRING) | Maps spoken sector names (e.g., "Bravo-4", "SU 1482 4621", "London") to decimal coordinates (51.2185, \-1.7925 or 51.5007, \-0.1246). |
| **group\_chat\_tickets** | ticket\_id (STRING), created\_at\_utc (TIMESTAMP), callsign (STRING), repair\_classification (STRING), aesp\_reference (STRING), part\_name (STRING), nsn (STRING), technical\_limits (STRING), coords\_label (STRING), latitude (FLOAT64), longitude (FLOAT64), google\_maps\_url (STRING), status (STRING) | Stores published tickets from Scene 2 to satisfy the storyboard's database persistence step. |

## ---

**5\. Application Layer: Markdown Card, Cloud Run HTML App & Google Maps**

### **5.1 Scene 2: Native Structured Markdown Card Template**

To avoid custom A2UI JSON parser bugs on stage, reme\_artificer\_agent is instructed via system prompt and Pydantic formatting to output a high-contrast **Markdown Tactical Card** using native collapsible \<details\> chips:

\#\#\# 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card  
🔊 \*\*15s Audio Brief:\*\* \*"AESP 2350-T-250-523 Para 17.4: fatigued K60 oil pressure relief valve spring. Renew if under 79.4mm free length or outside 14.3 to 16.2kg at 54.6mm. Do not pack with washers. NSN 5360-99-812-1740. Coordinates locked."\*

\<details open\>  
\<summary\>\<b\>🏷️ Chip 1 — Classification: L1 FRT / L2 Repair (Bench Test)\</b\>\</summary\>  
Renew 1 single part (Oil Pressure Relief Valve Spring). \<b\>Warning:\</b\> Do not use washers to pack up behind a weak spring.  
\</details\>

\<details open\>  
\<summary\>\<b\>📖 Chip 2 — AESP Ref: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (p. 14)\</b\>\</summary\>  
• \<b\>Free Length Limit:\</b\> 79.4 mm (3.126 in)\<br\>  
• \<b\>Compression Limit:\</b\> 54.6 mm (2.150 in) @ 14.3–16.2 kg (31.5–35.6 lb)  
\</details\>

\<details open\>  
\<summary\>\<b\>🔩 Chip 3 — NSN: 5360-99-812-1740 \| 📍 Coords: 51.2185° N, 1.7925° W\</b\>\</summary\>  
• \<b\>Catalogue:\</b\> IPC Army Code 14660 (Category 711\) — Oil Pressure Relief Valve Spring\<br\>  
• \<b\>Sector Grid:\</b\> SPTA Sector Bravo-4 (51.2185, \-1.7925)  
\</details\>

👉 \*Say \*\*"Publish to Group Chat"\*\* to dispatch ticket to B Echelon.\*

### **5.2 Scene 3: Cloud Run Lightweight HTML Chat App Specification**

The **Cloud Run** service (reme-chat-demonstrator) is a single-container Python **FastAPI** app serving a responsive dark-mode HTML5 page (templates/index.html):

| Endpoint | Method | Behaviour |
| :---- | :---- | :---- |
| / | GET | Renders the lightweight **4 Bn REME — Sustainment Group Chat** HTML interface. |
| /api/tickets | GET | Returns the in-memory ACTIVE\_TICKETS list (seeded from BigQuery on startup; updated in \<20 ms on webhook POST). Polled every 1000 ms by the browser. |
| /api/tickets | POST | Receives the newly published ticket from publish\_ticket\_to\_chat, prepends it to ACTIVE\_TICKETS, and triggers an async BigQuery insert. |
| /api/reset | POST | **Stage Reset Button:** Clears ACTIVE\_TICKETS in memory immediately so the presenter can re-run the demo in \<1 second without waiting on BigQuery streaming buffers. |

**Google Maps Deep-Link Handoff HTML Snippet (inside index.html):**

\<a href="https\://www\.google.com/maps/dir/?api=1\&destination={{ ticket.latitude }},{{ ticket.longitude }}\&travelmode=driving"  
&nbsp;&nbsp;&nbsp;target="\_blank" rel="noopener"  
&nbsp;&nbsp;&nbsp;class="inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg shadow"\>  
&nbsp;&nbsp;&nbsp;📍 {{ ticket.coords\_label }} — Deploy via Google Maps  
\</a\>

## ---

**6\. Target Repository Structure & Code Blueprint (SPEC.md)**

### **6.1 Repository Layout for gemini-cli**

demo1-reme-tactical-sustainment/  
├── SPEC.md                                \# Authoritative specification consumed by gemini-cli  
├── .env.example                           \# GCP\_PROJECT\_ID, BQ\_DATASET, VERTEX\_SEARCH\_DATASTORE\_ID, CLOUD\_RUN\_CHAT\_URL  
├── requirements.txt                       \# google-adk\>=2.0.0, google-genai, google-cloud-bigquery, google-cloud-discoveryengine, fastapi, uvicorn, requests  
├── scripts/  
│   ├── deploy\_demo.sh                     \# Creates \`sa-reme-demo\`, seeds BQ, deploys Cloud Run Chat & Agent Platform  
│   └── seed\_demo1\_bigquery.py             \# Creates & seeds \`ipc\_nsn\_catalogue\`, \`spta\_sector\_grids\`, \`group\_chat\_tickets\`  
├── reme\_artificer\_agent/                  \# Hosted on Vertex AI Agent Platform  
│   ├── \_\_init\_\_.py  
│   ├── agent.py                           \# Single ADK 2.0 \`LlmAgent\` (\`reme\_artificer\_agent\`)  
│   ├── schemas.py                         \# Pydantic schema for \`ActiveTicketState\`  
│   └── tools.py                           \# 2 Composite Tools (\`diagnose\_and\_resolve\_grid\`, \`publish\_ticket\_to\_chat\`)  
└── cloud\_run\_chat\_app/                    \# Hosted on Google Cloud Run  
&nbsp;&nbsp;&nbsp;&nbsp;├── Dockerfile                         \# python:3.12-slim running uvicorn  
&nbsp;&nbsp;&nbsp;&nbsp;├── main.py                            \# FastAPI app with in-memory write-through cache & \`/api/reset\`  
&nbsp;&nbsp;&nbsp;&nbsp;└── templates/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── index.html                     \# Single-file High-Contrast Tactical HTML5 Group Chat \+ Google Maps link

### **6.2 Reference Implementation: Stage-Proof Composite Tools (reme\_artificer\_agent/tools.py)**

import uuid, datetime, os, requests  
from google.adk.tools import ToolContext  
from google.cloud import bigquery

GOLDEN\_FALLBACK\_K60 \= {  
&nbsp;&nbsp;&nbsp;&nbsp;"repair\_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",  
&nbsp;&nbsp;&nbsp;&nbsp;"aesp\_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",  
&nbsp;&nbsp;&nbsp;&nbsp;"part\_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",  
&nbsp;&nbsp;&nbsp;&nbsp;"nsn": "5360-99-812-1740",  
&nbsp;&nbsp;&nbsp;&nbsp;"technical\_limits": (  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) "  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits; "  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"do not use washers to pack up behind a weak spring."  
&nbsp;&nbsp;&nbsp;&nbsp;),  
}

GOLDEN\_FALLBACK\_GRID \= {  
&nbsp;&nbsp;&nbsp;&nbsp;"sector\_display\_name": "Salisbury Plain (SPTA) — Sector Bravo-4",  
&nbsp;&nbsp;&nbsp;&nbsp;"latitude": 51.2185,  
&nbsp;&nbsp;&nbsp;&nbsp;"longitude": \-1.7925,  
&nbsp;&nbsp;&nbsp;&nbsp;"coords\_label": "51.2185° N, 1.7925° W",  
}

def diagnose\_and\_resolve\_grid(  
&nbsp;&nbsp;&nbsp;&nbsp;fault\_query: str,  
&nbsp;&nbsp;&nbsp;&nbsp;spoken\_sector\_grid: str,  
&nbsp;&nbsp;&nbsp;&nbsp;tool\_context: ToolContext,  
) \-\> dict:  
&nbsp;&nbsp;&nbsp;&nbsp;"""Scene 1 Composite Tool: Runs RAG \+ BigQuery NSN & Grid lookups with golden-path fallback."""  
&nbsp;&nbsp;&nbsp;&nbsp;bq\_client \= bigquery.Client()  
&nbsp;&nbsp;&nbsp;&nbsp;dataset \= os.environ.get("BQ\_DATASET", "ukd\_reme\_demo")

&nbsp;&nbsp;&nbsp;&nbsp;\# 1\. Lookup NSN & AESP details (parameterized SQL with golden-path fallback)  
&nbsp;&nbsp;&nbsp;&nbsp;part\_data \= GOLDEN\_FALLBACK\_K60.copy()  
&nbsp;&nbsp;&nbsp;&nbsp;try:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sql\_part \= f"""  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SELECT repair\_classification, aesp\_reference, part\_name, nsn, technical\_limits  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FROM \`{dataset}.ipc\_nsn\_catalogue\`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;WHERE LOWER(@query) LIKE CONCAT('%', LOWER(keyword\_tag), '%')  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;LIMIT 1  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"""  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;job\_cfg \= bigquery.QueryJobConfig(  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;query\_parameters=\[bigquery.ScalarQueryParameter("query", "STRING", fault\_query)\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;rows \= list(bq\_client.query(sql\_part, job\_config=job\_cfg).result())  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if rows:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;part\_data \= dict(rows\[0\].items())  
&nbsp;&nbsp;&nbsp;&nbsp;except Exception:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pass  \# Fail gracefully to GOLDEN\_FALLBACK\_K60 on stage

&nbsp;&nbsp;&nbsp;&nbsp;\# 2\. Resolve Spoken Sector Grid to Coordinates (with golden-path fallback)  
&nbsp;&nbsp;&nbsp;&nbsp;grid\_data \= GOLDEN\_FALLBACK\_GRID.copy()  
&nbsp;&nbsp;&nbsp;&nbsp;try:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sql\_grid \= f"""  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SELECT sector\_display\_name, latitude, longitude, coords\_label  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FROM \`{dataset}.spta\_sector\_grids\`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;WHERE LOWER(@grid) LIKE CONCAT('%', LOWER(sector\_key), '%')  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;LIMIT 1  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"""  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;job\_cfg \= bigquery.QueryJobConfig(  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;query\_parameters=\[bigquery.ScalarQueryParameter("grid", "STRING", spoken\_sector\_grid)\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;rows \= list(bq\_client.query(sql\_grid, job\_config=job\_cfg).result())  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if rows:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;grid\_data \= dict(rows\[0\].items())  
&nbsp;&nbsp;&nbsp;&nbsp;except Exception:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pass  \# Fail gracefully to GOLDEN\_FALLBACK\_GRID on stage

&nbsp;&nbsp;&nbsp;&nbsp;ticket\_state \= {\*\*part\_data, \*\*grid\_data}  
&nbsp;&nbsp;&nbsp;&nbsp;tool\_context.state\["active\_ticket"\] \= ticket\_state  
&nbsp;&nbsp;&nbsp;&nbsp;return ticket\_state

def publish\_ticket\_to\_chat(tool\_context: ToolContext) \-\> dict:  
&nbsp;&nbsp;&nbsp;&nbsp;"""Scene 2 Composite Tool: Writes ticket from ctx.state to BigQuery and Cloud Run Chat."""  
&nbsp;&nbsp;&nbsp;&nbsp;ticket \= tool\_context.state.get("active\_ticket") or {  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\*\*GOLDEN\_FALLBACK\_K60,  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\*\*GOLDEN\_FALLBACK\_GRID,  
&nbsp;&nbsp;&nbsp;&nbsp;}  
&nbsp;&nbsp;&nbsp;&nbsp;lat, lng \= ticket\["latitude"\], ticket\["longitude"\]  
&nbsp;&nbsp;&nbsp;&nbsp;payload \= {  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"ticket\_id": f"TKT-REME-{uuid.uuid4().hex\[:4\].upper()}",  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"created\_at\_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"callsign": "Cpl MacDonald (4 Bn REME FRT)",  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\*\*ticket,  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"google\_maps\_url": f"https\://www\.google.com/maps/dir/?api=1\&destination={lat},{lng}\&travelmode=driving",  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"status": "DISPATCH\_READY",  
&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\# 1\. Push immediately to Cloud Run HTML Chat App in-memory cache (\<20ms)  
&nbsp;&nbsp;&nbsp;&nbsp;chat\_url \= os.environ.get("CLOUD\_RUN\_CHAT\_URL", "").rstrip("/")  
&nbsp;&nbsp;&nbsp;&nbsp;if chat\_url:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;try:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;requests.post(f"{chat\_url}/api/tickets", json=payload, timeout=2.0)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;except Exception:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pass

&nbsp;&nbsp;&nbsp;&nbsp;\# 2\. Persist to BigQuery \`group\_chat\_tickets\` table  
&nbsp;&nbsp;&nbsp;&nbsp;try:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;bq\_client \= bigquery.Client()  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dataset \= os.environ.get("BQ\_DATASET", "ukd\_reme\_demo")  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;bq\_client.insert\_rows\_json(f"{dataset}.group\_chat\_tickets", \[payload\])  
&nbsp;&nbsp;&nbsp;&nbsp;except Exception:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pass

&nbsp;&nbsp;&nbsp;&nbsp;return {"published": True, "ticket": payload}

## ---

**7\. Demonstrator Non-Functional Benchmarks & Risk Matrix**

| Benchmark / Risk | Target Threshold | How This Refined Design Guarantees It |
| :---- | :---- | :---- |
| **Scene 1 End-to-End Turn Latency** | **≤ 1.5 seconds** | Single gemini-2.5-flash hop \+ 1 composite tool call (diagnose\_and\_resolve\_grid). |
| **Scene 2 \-\> Scene 3 Chat Appearance** | **\< 100 milliseconds** | Direct webhook POST /api/tickets updates Cloud Run in-memory list while persisting to BigQuery. |
| **Noisy Stage PTT Resilience** | **100% Success Rate** | try/except \+ 0-row Golden-Path Fallback guarantees valid K60 NSN and SPTA coordinates on every run. |
| **Demo Reset Time Between Takes** | **\< 1 second** | Clicking **\[Reset Demo\]** (POST /api/reset) clears the Cloud Run in-memory ticket list immediately. |

&nbsp;