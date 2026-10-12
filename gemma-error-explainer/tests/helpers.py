"""Shared fakes: a Gemini client that returns scripted replies, and tiny image builders."""
import io
import json

from PIL import Image

GOOD = {
    "tool_or_language": "Python in PowerShell",
    "error_line": "ModuleNotFoundError: No module named 'pandas'",
    "error_summary": "pandas is missing.",
    "likely_cause": "Not installed in this environment.",
    "alternative_causes": ["Wrong venv", "Wrong Python", "third one gets clamped"],
    "severity": "blocking",
    "fix_steps": ["1. Install it", "2) Run again"],
    "commands": ["pip install pandas"],
    "code_fix": "import pandas as pd",
    "code_language": "Python!",
    "prevention_tips": ["Use a venv", "Pin versions", "Use requirements.txt", "fourth gets clamped"],
    "if_still_stuck": "Run pip list",
    "confidence": "high",
}
GOOD_JSON = json.dumps(GOOD)


class FakeResp:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate_content(self, model, contents):
        self.calls.append((model, contents))
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return FakeResp(reply)


class FakeClient:
    """Returns each scripted reply once, then repeats the last one."""

    def __init__(self, replies):
        self.models = FakeModels(replies)


def png_bytes(size=(200, 100), mode="RGB"):
    out = io.BytesIO()
    Image.new(mode, size, (10, 20, 30)).save(out, format="PNG")
    return out.getvalue()
