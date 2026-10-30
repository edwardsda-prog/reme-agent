# Issue Fix: The Agent speaks in an American British Accent

## Current Symptoms
- **Observed Behavior:** When the user select the text to speech button on the Gemini Enterprise Mobile Application, the voice is American British 


## Expected Behavior
When the user select the text to speech button on the Gemini Enterprise Mobile Application, the voice must be British English


## Target Files

- `app/agent.py`: Configure `speech_config=types.SpeechConfig(language_code="en-GB", ...)` and British English (`en-GB`) orthography/TTS rules on `reme_artificer_agent`.
- `scripts/setup_reme_datastore.py`: Set `languageInfo: {"languageCode": "en-GB"}` on the Discovery Engine datastore.
- `cloud_run_chat_app/templates/index.html`: Set `<html lang="en-GB">` and add `en-GB` Web Speech API (`SpeechSynthesisUtterance.lang = "en-GB"`) readout support.
- `tests/unit/test_tools.py` & `tests/unit/test_chat_api.py`: Regression tests verifying `en-GB` speech config and HTML/JS `en-GB` TTS configuration.

## Context Validation Rules
- Ensure the accent is British English
- First Validate the capability of the Gemini Enterprise Mobile Application to confirm the accent can be changed

---

## Capability Validation & Resolution Runbook

### 1. How the Gemini Enterprise Mobile App TTS ("Listen") Button Works
- Custom ADK Reasoning Engine agents registered in Gemini Enterprise (`pixel_mobile_demos` in `location=eu`) stream UTF-8 text chunks via the `:streamQuery` REST endpoint.
- Tapping the **Text-to-Speech (Speaker / "Listen")** button on an agent message in the Gemini Enterprise Mobile Application invokes **client-side speech synthesis** on the ruggedised Google Pixel device (via Google Speech Recognition & Synthesis / Android WebView `SpeechSynthesis`).

### 2. Ruggedised Pixel / Gemini Enterprise Mobile App Configuration (`en-GB`)
To ensure the mobile application's native TTS button speaks in a **British English (`en-GB`)** voice:
1. **Android System Language**:
   - Navigate to **Settings → System → Languages & input → Languages**.
   - Add **`English (United Kingdom)`** (`en-GB`) and move it to **#1 (Top Priority)**.
2. **Android Text-to-Speech Output Engine**:
   - Navigate to **Settings → Accessibility → Text-to-speech output** (or **Settings → System → Languages & input → Text-to-speech output**).
   - Set **Preferred engine** to **Speech Recognition & Synthesis from Google**.
   - Tap **Language** → select **`English (United Kingdom)`** (and install UK English voice data under the engine settings gear).
3. **Gemini Mobile App Voice Selection**:
   - Open the Gemini Mobile App → tap **Profile Icon → Settings → Gemini's voice** → select the British English voice (**Capella** / British English).
