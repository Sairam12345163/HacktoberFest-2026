"""Minimal Ollama client (stdlib only). Talks to a local open-weight model."""
import json
import os
import urllib.error
import urllib.request

DEFAULT_MODEL = os.environ.get("FPP_MODEL", "qwen2.5-coder:7b")  # Apache-2.0 open weights


class ModelError(RuntimeError):
    """Raised when the local model can't be reached or misbehaves."""


def _host(host=None):
    h = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    return h if h.startswith("http") else "http://" + h


def chat(messages, model=None, host=None, schema=None, timeout=600, on_token=None):
    """Stream a chat request; if `schema` is given, Ollama constrains output to it.

    `on_token(n)` is called with the running chunk count so UIs can show progress.
    """
    model = model or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.2},
    }
    if schema:
        payload["format"] = schema
    req = urllib.request.Request(
        _host(host) + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    parts, n = [], 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw.decode())
                except ValueError as e:
                    raise ModelError("Unexpected response from Ollama") from e
                if isinstance(obj, dict) and obj.get("error"):
                    raise ModelError(f"Ollama error: {obj['error']}")
                piece = ((obj.get("message") or {}).get("content")) or ""
                if piece:
                    parts.append(piece)
                    n += 1
                    if on_token:
                        on_token(n)
                if obj.get("done"):
                    break
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ModelError(f"Model '{model}' not found. Run: ollama pull {model}") from e
        raise ModelError(f"Ollama returned HTTP {e.code}") from e
    except OSError as e:  # URLError, timeouts, connection resets
        raise ModelError(
            f"Cannot reach Ollama at {_host(host)} (or it stopped responding). "
            "Is `ollama serve` running?"
        ) from e
    content = "".join(parts)
    if not content.strip():
        raise ModelError("The model returned an empty response.")
    return content


def list_models(host=None, timeout=10):
    """Names of models available on the Ollama server."""
    req = urllib.request.Request(_host(host) + "/api/tags")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except OSError as e:
        raise ModelError(
            f"Cannot reach Ollama at {_host(host)}. Is `ollama serve` running?"
        ) from e
    return [m.get("name", "") for m in data.get("models", [])]


def has_model(have, model):
    return any(m == model or m.split(":")[0] == model for m in have)
