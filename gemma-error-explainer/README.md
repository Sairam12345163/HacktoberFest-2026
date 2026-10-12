# 🛠️ Error Screenshot Explainer

**Hacktoberfest Hack Day Hyderabad · MLH × NIAT · Best Use of Gemma 4**

Students get stuck on cryptic error screenshots. Upload one and **Gemma 4** (called through the **Gemini API**) reads it and returns a diagnostic report: the exact error line, the likely cause, numbered fix steps, commands to run, a code correction and prevention tips. Ask follow-ups, or get the answer in Hindi or Telugu.

## Define

| | |
|---|---|
| **One user** | A student or beginner developer stuck on an error they can't decode |
| **One problem** | Error screenshots are cryptic, and the fix depends on details inside the image |
| **One wow moment** | Upload a screenshot, and Gemma reads the *exact* error line out of the image and returns the cause and fix |

Core loop: **user shares** a screenshot → **Gemma understands** it → **app responds** with a report → **user acts** on it.

## Why Gemma 4 is essential

Gemma 4 does all the work on the live path: it reads the pixels (terminal text, file names, line numbers, OS and shell), reasons about the cause, and writes the fix in the user's language and level. The only pre-written answers are the clearly labelled offline-demo results.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open **Settings** (top right) and paste your Gemini API key from [Google AI Studio](https://aistudio.google.com). Or set it first:

```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your_key"
# Mac / Linux
export GEMINI_API_KEY=your_key
```

Models: `gemma-4-26b-a4b-it` (default, faster) and `gemma-4-31b-it` (stronger), chosen in Settings.

## What you get

**Workspace (left)**
- Three input modes: **Upload Screenshot**, **Try Sample**, **Camera**
- Drag-and-drop upload (PNG, JPG, WebP, up to 8 MB), a preview with file name, size and dimensions, and **Replace** / **Remove** actions
- A gallery of 8 sample errors: Python traceback, JavaScript TypeError, React rendering error, Node.js module error, SQL database error, API authentication error, Git push rejected, Python IndentationError
- Optional context, Beginner/Developer level, English/Hindi/Telugu output
- **Analyze Error** button with disabled and loading states

**Diagnostic report (right)**
- Error summary and the exact error line, error type, root cause, other possibilities
- Recommended fix: numbered steps and a copyable command block
- Code correction with syntax highlighting (only when Gemma can determine it)
- Prevention tips, a "still stuck?" tip, and a warning when confidence is low
- Copy buttons on every code block, a "Copy full report" view and a Markdown download
- Follow-up chat about the same screenshot
- Live progress while analysing, friendly error messages and a **Retry analysis** button

**Reliability**
- Image type and size checks, automatic JSON repair if the reply is malformed, normalised output
- One automatic retry on transient failures; clear messages for a bad key, quota, wrong model, network or safety block
- **Offline demo mode** (Settings): pre-computed results for the built-in samples with no API call, clearly labelled as such

## Project layout

```
app.py              Page layout and interactions (Streamlit)
ui.py               Report rendering, header, hero, empty and error states
assets/styles.css   Design tokens and component styles (light theme, teal accent, Inter)
explainer.py        Prompt, Gemini API call, validation, retries (no UI code)
samples.py          Loads the built-in samples
make_samples.py     Regenerates samples/*.png and seeded_results.json
samples/            Sample screenshots + their offline results
tests/              Unit and UI tests (pytest)
.streamlit/         Theme and upload limit (keep maxUploadSize in sync with explainer.MAX_UPLOAD_MB)
DEMO.md             30-second story, 2-minute script, judge checklist
```

## Tests

```bash
pip install pytest
pytest
```

The tests use a fake Gemini client, so they need no API key or network.

## Troubleshooting

| Problem | Fix |
|---|---|
| Analyze Error is greyed out | Add a screenshot, and add your API key in Settings (or turn on Offline demo mode with a sample) |
| "Gemini rejected your API key" | Re-copy the key from AI Studio into Settings |
| "That Gemma model isn't available" | Pick the other model in Settings |
| Rate limit or quota | Wait a few seconds and select Retry analysis, or switch model |
| No Wi-Fi | Settings → Offline demo mode, then Input → Try Sample |
| `streamlit` not recognised | `python -m streamlit run app.py` |
| A layout looks off | Hard-refresh the browser (Ctrl + F5); the styles are loaded from `assets/styles.css` |
# HacktoberFest-2026
