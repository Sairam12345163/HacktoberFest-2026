"""Core logic for the Error Screenshot Explainer.

No Streamlit imports here, so everything is unit-testable and the UI stays thin.
Gemma 4 is called through the Gemini API (google-genai SDK).
"""
from __future__ import annotations

import io
import json
import re
import time
from dataclasses import dataclass

from PIL import Image

# Gemma 4 models served by the Gemini API
MODELS = ["gemma-4-26b-a4b-it", "gemma-4-31b-it"]
LANGS = ["English", "Hindi", "Telugu"]
LEVELS = {
    "Beginner": "Explain like I'm a first-year student. Avoid jargon and define any term you use.",
    "Developer": "Be concise and technical. Skip the basics.",
}
MAX_UPLOAD_MB = 8
SEVERITIES = ("blocking", "warning", "info")
CONFIDENCES = ("high", "medium", "low")


class ExplainerError(Exception):
    """An error whose message is safe and helpful to show directly to the user."""


# ---------------------------------------------------------------- prompt ----

PROMPT = """You are a patient senior developer helping a student who is stuck on an error.
Read the attached screenshot carefully: the exact error text, file names, line numbers, the
programming language, the tool (terminal, IDE, browser console) and the operating system if visible.

Rules:
- Base every statement on what is visible. Never invent file names, versions or line numbers.
- Put the single most probable cause first. List up to two alternative causes only if they are realistic.
- Give commands for the OS and shell visible in the screenshot (PowerShell vs bash). If unknown, give
  the cross-platform command.
- Fix steps must be short, ordered and concrete (at most 5).
- If the screenshot shows a secret (API key, password, token), say in if_still_stuck that it must be
  rotated and never shared.
- If the image is not an error or is unreadable, say so in error_summary and set confidence to "low".
- If the screenshot does not contain enough information to be sure of the root cause, say what is
  missing in likely_cause and set confidence to "low" or "medium".
- code_fix: give corrected code only when the failing code is visible or the fix is a short, certain
  snippet. Otherwise use an empty string. Never guess at code you cannot see.
- prevention_tips: at most 3 short, practical tips to avoid this error next time.

Reply with ONLY a JSON object, no markdown fences, no extra text:
{
  "tool_or_language": "what the screenshot shows, e.g. Python 3.11 in a PowerShell terminal",
  "error_line": "the exact key error line copied from the screenshot",
  "error_summary": "the error in one plain sentence",
  "likely_cause": "the most probable root cause, referring to specifics seen in the screenshot",
  "alternative_causes": ["other realistic causes, may be empty"],
  "severity": "blocking | warning | info",
  "fix_steps": ["short, ordered, concrete steps to fix it"],
  "commands": ["exact terminal commands to try, may be empty"],
  "code_fix": "corrected code snippet, or an empty string",
  "code_language": "language of code_fix for syntax highlighting, e.g. python, javascript, sql",
  "prevention_tips": ["how to avoid this error in future, may be empty"],
  "if_still_stuck": "what to check or search next",
  "confidence": "high | medium | low"
}
Keep the JSON keys in English. Write every value in <<LANG>>. <<STYLE>>"""


def build_prompt(lang: str = "English", level: str = "Beginner", extra: str = "") -> str:
    prompt = PROMPT.replace("<<LANG>>", lang).replace("<<STYLE>>", LEVELS.get(level, LEVELS["Beginner"]))
    if extra and extra.strip():
        prompt += f"\n\nExtra context from the user: {extra.strip()[:500]}"
    return prompt


# ------------------------------------------------------------ validation ----


def prepare_image(data: bytes, max_side: int = 1600) -> bytes:
    """Validate an uploaded image and downscale it to a PNG so the API call is fast."""
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ExplainerError(f"That image is larger than {MAX_UPLOAD_MB} MB. Please upload a smaller screenshot.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # not an image, truncated, decompression bomb...
        raise ExplainerError("That file isn't a readable image. Upload a PNG, JPG or WebP screenshot.") from exc
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def parse_model_json(text: str) -> dict | None:
    """Pull a JSON object out of a model reply, tolerating code fences and chatter."""
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value)]


def _strip_marker(step: str) -> str:
    """Drop a leading '1.' / '2)' / '-' the model may add, since the UI numbers the steps itself."""
    return re.sub(r"^\s*(?:\d+[.)]|[-*•])\s+", "", step)


def normalize(data: dict) -> dict:
    """Coerce whatever the model returned into the exact shape the UI expects."""
    severity = str(data.get("severity", "")).strip().lower()
    confidence = str(data.get("confidence", "")).strip().lower()
    return {
        "tool_or_language": str(data.get("tool_or_language") or "unknown").strip(),
        "error_line": str(data.get("error_line") or "").strip(),
        "error_summary": str(data.get("error_summary") or "").strip(),
        "likely_cause": str(data.get("likely_cause") or "").strip(),
        "alternative_causes": _as_list(data.get("alternative_causes"))[:2],
        "severity": severity if severity in SEVERITIES else "warning",
        "fix_steps": [_strip_marker(s) for s in _as_list(data.get("fix_steps"))][:6],
        "commands": _as_list(data.get("commands"))[:5],
        "code_fix": str(data.get("code_fix") or "").strip("\n"),
        "code_language": re.sub(r"[^a-z0-9+#-]", "", str(data.get("code_language") or "").lower()) or "text",
        "prevention_tips": _as_list(data.get("prevention_tips"))[:3],
        "if_still_stuck": str(data.get("if_still_stuck") or "").strip(),
        "confidence": confidence if confidence in CONFIDENCES else "low",
    }


def is_usable(result: dict) -> bool:
    return bool(result["error_summary"]) and bool(result["fix_steps"] or result["likely_cause"])


# ---------------------------------------------------------- API plumbing ----


def classify_exception(exc: Exception) -> str:
    """Turn a raw SDK/network exception into something a student can act on."""
    msg = str(exc).lower()
    if any(s in msg for s in ("api key", "api_key", "unauthenticated", "permission_denied", "401", "403")):
        return "Gemini rejected your API key. Re-copy it from Google AI Studio and paste it in the sidebar."
    if any(s in msg for s in ("429", "quota", "resource_exhausted", "rate limit")):
        return "Rate limit or quota reached. Wait a few seconds and retry, or switch model in the sidebar."
    if any(s in msg for s in ("404", "not found", "is not supported")):
        return "That Gemma model isn't available for your key. Pick the other model in the sidebar."
    if any(s in msg for s in ("safety", "blocked", "prohibited")):
        return "Gemma declined to process that image. Try a different screenshot."
    if any(s in msg for s in ("timeout", "timed out", "connection", "network", "name resolution", "unavailable", "503")):
        return "Couldn't reach the Gemini API (network or service issue). Check the Wi-Fi and retry, or use Offline demo mode."
    return f"Something went wrong calling Gemma: {str(exc)[:200]}"


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        s in msg
        for s in ("429", "500", "502", "503", "504", "unavailable", "timeout", "timed out", "connection", "overloaded")
    )


def get_client(api_key: str):
    if not api_key or not api_key.strip():
        raise ExplainerError("Add your Gemini API key in the sidebar first (it's free from Google AI Studio).")
    from google import genai

    return genai.Client(api_key=api_key.strip())


def image_part(png: bytes):
    from google.genai import types

    return types.Part.from_bytes(data=png, mime_type="image/png")


def call_model(client, model: str, contents, retries: int = 1, backoff: float = 1.5, sleep=None) -> str:
    """Call generate_content, retrying once on transient failures, raising ExplainerError otherwise."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = client.models.generate_content(model=model, contents=contents)
        except Exception as exc:
            last = exc
            if attempt < retries and _is_transient(exc):
                (sleep or time.sleep)(backoff * (attempt + 1))
                continue
            break
        text = getattr(resp, "text", None) or ""
        if not text.strip():
            raise ExplainerError("Gemma returned an empty reply. Try again or switch model in the sidebar.")
        return text
    raise ExplainerError(classify_exception(last)) from last


# ----------------------------------------------------------- main actions ----


@dataclass
class Explanation:
    result: dict
    seconds: float
    model: str
    seeded: bool = False


def explain_screenshot(
    api_key: str,
    model: str,
    png: bytes,
    lang: str = "English",
    level: str = "Beginner",
    extra: str = "",
    client=None,
    progress=None,
) -> Explanation:
    """Screenshot in, structured explanation out. One repair attempt if the reply isn't valid JSON.

    `progress`, if given, is called with a short status string at each real processing step.
    """
    note = progress or (lambda message: None)
    client = client or get_client(api_key)
    prompt = build_prompt(lang, level, extra)
    t0 = time.time()
    note(f"Sending the screenshot to {model} through the Gemini API")
    raw = call_model(client, model, [image_part(png), prompt])
    note("Reading Gemma's response")
    data = parse_model_json(raw)
    result = normalize(data) if data else None
    if not result or not is_usable(result):
        note("The reply wasn't structured. Asking Gemma to restate it")
        repair = (
            prompt
            + "\n\nYour previous reply was not valid JSON:\n"
            + raw[:2000]
            + "\n\nReply again with ONLY the JSON object."
        )
        raw = call_model(client, model, [image_part(png), repair], retries=0)
        data = parse_model_json(raw)
        result = normalize(data) if data else None
    if not result or not is_usable(result):
        raise ExplainerError("Gemma's reply couldn't be read as a structured answer. Try again or use a clearer screenshot.")
    return Explanation(result=result, seconds=round(time.time() - t0, 1), model=model)


def follow_up(
    api_key: str,
    model: str,
    png: bytes,
    previous: dict,
    history: list[tuple[str, str]],
    question: str,
    lang: str = "English",
    level: str = "Beginner",
    client=None,
) -> str:
    """Answer a follow-up question about the same screenshot."""
    client = client or get_client(api_key)
    convo = "\n".join(f"{role}: {text}" for role, text in history)
    prompt = (
        f"You already analysed this screenshot and concluded: {json.dumps(previous, ensure_ascii=False)}\n"
        f"Conversation so far:\n{convo or '(none)'}\n\n"
        f"Answer the new question briefly and concretely in {lang}. {LEVELS.get(level, LEVELS['Beginner'])}\n"
        f"Question: {question.strip()[:800]}"
    )
    return call_model(client, model, [image_part(png), prompt]).strip()


def to_markdown(r: dict) -> str:
    lines = [f"# {r.get('error_summary') or 'Error'}", ""]
    if r.get("error_line"):
        lines += ["```", r["error_line"], "```", ""]
    lines += ["## Likely cause", r.get("likely_cause", ""), ""]
    if r.get("alternative_causes"):
        lines += ["## Other possibilities"] + [f"- {c}" for c in r["alternative_causes"]] + [""]
    lines += ["## Fix steps"] + [f"{i}. {s}" for i, s in enumerate(r.get("fix_steps") or [], 1)]
    if r.get("commands"):
        lines += ["", "## Commands", "```bash", *r["commands"], "```"]
    if r.get("code_fix"):
        lines += ["", "## Code correction", f"```{r.get('code_language', '')}", r["code_fix"], "```"]
    if r.get("prevention_tips"):
        lines += ["", "## Prevention tips"] + [f"- {t}" for t in r["prevention_tips"]]
    if r.get("if_still_stuck"):
        lines += ["", f"**Still stuck?** {r['if_still_stuck']}"]
    return "\n".join(lines) + "\n"
