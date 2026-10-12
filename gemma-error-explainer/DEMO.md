# Demo guide (under 2 minutes)

## The 30-second story

> "Students get stuck on cryptic error screenshots and spend hours searching for the cause. Our app takes the screenshot itself. Gemma 4 reads the exact error out of the image, explains it in plain language, and gives the fix and the commands. Watch."

## 2-minute script

| Time | Do | Say |
|---|---|---|
| 0:00 | Show the page | One-sentence problem (above) |
| 0:15 | Choose **Try Sample** → **Python traceback**. Show the screenshot **first**. | "Here's an error screenshot. No text typed in." |
| 0:25 | Select **Analyze Error** | "Gemma 4 is reading the image through the Gemini API." |
| 0:40 | Point at the error line, root cause, numbered fix, command block | **The multimodal moment:** it pulled the error line out of the pixels and chose a PowerShell-correct fix |
| 1:00 | Switch **Language** to Telugu, analyze again | "Same screenshot, explained in my language." |
| 1:20 | Ask a follow-up: "Why does this happen?" | "It remembers the screenshot and the conversation." |
| 1:45 | Wrap up | "One user, one problem, Gemma 4 does the work. Questions?" |

Before presenting, run your main screenshot **twice in a row** to confirm it is stable. Try one real screenshot from your own machine too.

## Judge / demo check (from the build plan)

- [ ] Show the input first, then the Gemma 4 result
- [ ] Explain the user problem in one sentence
- [ ] Show one moment where multimodal understanding creates value
- [ ] Keep the demo under 2 minutes and leave time for questions
- [ ] Have a fallback screenshot or sample input if the API call fails

## If something fails

1. API error or no Wi-Fi: **Settings** → turn on **Offline demo mode**, then Input → **Try Sample**. Say: "This is the pre-computed backup of the same flow." (The report is labelled "Pre-computed demo result".)
2. Wrong model error: Settings → pick the other Gemma 4 model, then **Retry analysis**.
3. Last resort: show a screenshot of a good result you saved earlier.

## Likely judge questions

- **Why Gemma 4?** It understands the image directly (multimodal), so the user doesn't have to retype or paraphrase the error. One call does reading and reasoning.
- **What stops it making things up?** The prompt forbids inventing details, asks for the exact visible error line, only returns a code fix when it is certain, reports a confidence level, and the UI warns when confidence is low. The output is validated and normalised.
- **What if the reply is malformed?** The app asks Gemma once more for strict JSON before showing an error.
- **Is it more than a chatbot?** Yes: a single-purpose tool with a structured diagnostic report (severity, cause, steps, commands, code fix, prevention). The follow-up chat is secondary.
- **What about privacy?** Screenshots go to the Gemini API for analysis; the app tells users to hide keys and passwords first, and the API key is never shown or saved.
- **What would you build next?** Paste-from-clipboard, a history of past errors, and IDE integration.
