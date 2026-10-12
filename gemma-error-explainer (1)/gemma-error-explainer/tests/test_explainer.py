import io
import json
from pathlib import Path

import pytest
from PIL import Image

import explainer as ex
from helpers import GOOD, GOOD_JSON, FakeClient, png_bytes
from samples import load_samples

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)


# ---- parsing / normalising -------------------------------------------------


def test_parse_handles_fences_and_chatter():
    text = "Sure! Here you go:\n```json\n" + GOOD_JSON + "\n```\nHope that helps."
    assert ex.parse_model_json(text)["error_summary"] == "pandas is missing."


@pytest.mark.parametrize("text", ["", "no json here", "{broken", "[1, 2, 3]"])
def test_parse_rejects_garbage(text):
    assert ex.parse_model_json(text) is None


def test_normalize_clamps_and_defaults():
    r = ex.normalize({"error_summary": "x", "fix_steps": "just one step", "severity": "BOGUS", "confidence": "HIGH"})
    assert r["fix_steps"] == ["just one step"]
    assert r["severity"] == "warning"
    assert r["confidence"] == "high"
    assert r["commands"] == [] and r["alternative_causes"] == [] and r["prevention_tips"] == []
    assert r["code_fix"] == "" and r["code_language"] == "text"


def test_normalize_new_report_fields():
    r = ex.normalize(GOOD)
    assert len(r["alternative_causes"]) == 2
    assert len(r["prevention_tips"]) == 3
    assert r["code_fix"] == "import pandas as pd"
    assert r["code_language"] == "python"  # lower-cased, punctuation stripped


def test_normalize_strips_step_numbering():
    assert ex.normalize(GOOD)["fix_steps"] == ["Install it", "Run again"]


def test_is_usable():
    assert ex.is_usable(ex.normalize(GOOD))
    assert not ex.is_usable(ex.normalize({"likely_cause": "only a cause"}))


# ---- images -----------------------------------------------------------------


def test_prepare_image_downscales_to_png():
    out = ex.prepare_image(png_bytes((3200, 2000)))
    img = Image.open(io.BytesIO(out))
    assert img.format == "PNG" and max(img.size) <= 1600


def test_prepare_image_accepts_rgba():
    assert ex.prepare_image(png_bytes(mode="RGBA"))


def test_prepare_image_rejects_non_image():
    with pytest.raises(ex.ExplainerError, match="readable image"):
        ex.prepare_image(b"definitely not an image")


def test_prepare_image_rejects_huge_file():
    with pytest.raises(ex.ExplainerError, match="larger than"):
        ex.prepare_image(b"0" * (ex.MAX_UPLOAD_MB * 1024 * 1024 + 1))


# ---- prompt -----------------------------------------------------------------


def test_build_prompt_includes_language_style_and_context():
    p = ex.build_prompt("Telugu", "Developer", "I just made a venv")
    assert "Telugu" in p and "technical" in p and "I just made a venv" in p
    assert "<<" not in p


def test_prompt_asks_for_every_report_field_and_admits_uncertainty():
    p = ex.build_prompt()
    for key in ("code_fix", "code_language", "prevention_tips", "error_line", "fix_steps"):
        assert f'"{key}"' in p
    assert "Never guess at code" in p and "not contain enough information" in p


# ---- API flow ---------------------------------------------------------------


def test_explain_happy_path():
    client = FakeClient([GOOD_JSON])
    out = ex.explain_screenshot("k", "gemma-4-26b-a4b-it", png_bytes(), client=client)
    assert out.result["severity"] == "blocking" and not out.seeded
    model, contents = client.models.calls[0]
    assert model == "gemma-4-26b-a4b-it" and len(contents) == 2


def test_progress_callback_reports_real_steps():
    steps = []
    ex.explain_screenshot("k", "gemma-4-31b-it", png_bytes(), client=FakeClient([GOOD_JSON]), progress=steps.append)
    assert "gemma-4-31b-it" in steps[0] and len(steps) == 2


def test_progress_reports_repair_step():
    steps = []
    ex.explain_screenshot("k", "m", png_bytes(), client=FakeClient(["garbage", GOOD_JSON]), progress=steps.append)
    assert any("restate" in s for s in steps)


def test_explain_repairs_bad_json_once():
    client = FakeClient(["I think it is a missing module", GOOD_JSON])
    out = ex.explain_screenshot("k", "m", png_bytes(), client=client)
    assert out.result["error_summary"] == "pandas is missing."
    assert len(client.models.calls) == 2


def test_explain_gives_up_after_repair_fails():
    client = FakeClient(["nope", "still nope"])
    with pytest.raises(ex.ExplainerError, match="structured answer"):
        ex.explain_screenshot("k", "m", png_bytes(), client=client)


def test_transient_error_is_retried():
    client = FakeClient([RuntimeError("503 Service Unavailable"), GOOD_JSON])
    out = ex.explain_screenshot("k", "m", png_bytes(), client=client)
    assert out.result["confidence"] == "high"
    assert len(client.models.calls) == 2


def test_auth_error_is_not_retried_and_is_friendly():
    client = FakeClient([RuntimeError("403 PERMISSION_DENIED: API key not valid")])
    with pytest.raises(ex.ExplainerError, match="API key"):
        ex.explain_screenshot("k", "m", png_bytes(), client=client)
    assert len(client.models.calls) == 1


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("429 RESOURCE_EXHAUSTED quota", "quota"),
        ("404 model not found", "other model"),
        ("blocked by safety filter", "declined"),
        ("Connection reset by peer", "Offline demo mode"),
    ],
)
def test_classify_exception(raw, expected):
    assert expected in ex.classify_exception(RuntimeError(raw))


def test_empty_reply_raises():
    with pytest.raises(ex.ExplainerError, match="empty reply"):
        ex.explain_screenshot("k", "m", png_bytes(), client=FakeClient(["   "]))


def test_missing_api_key():
    with pytest.raises(ex.ExplainerError, match="API key"):
        ex.explain_screenshot("  ", "m", png_bytes())


def test_follow_up_sends_question_history_and_image():
    client = FakeClient(["Because the venv is different."])
    ans = ex.follow_up(
        "k", "m", png_bytes(), ex.normalize(GOOD), [("user", "first q"), ("assistant", "first a")], "why?", client=client
    )
    assert ans == "Because the venv is different."
    _, contents = client.models.calls[0]
    assert "why?" in contents[1] and "first q" in contents[1] and "pandas is missing." in contents[1]


def test_to_markdown_has_all_sections():
    md = ex.to_markdown(ex.normalize(GOOD))
    for part in (
        "# pandas is missing.",
        "## Likely cause",
        "## Other possibilities",
        "## Fix steps",
        "pip install pandas",
        "## Code correction",
        "```python",
        "## Prevention tips",
    ):
        assert part in md


# ---- bundled samples ---------------------------------------------------------

REQUIRED_SAMPLES = {
    "Python traceback",
    "JavaScript TypeError",
    "React rendering error",
    "Node.js module error",
    "SQL database error",
    "API authentication error",
}


def test_gallery_has_the_requested_sample_types():
    assert REQUIRED_SAMPLES <= {s["title"] for s in load_samples()}


def test_bundled_samples_are_valid_and_complete():
    for s in load_samples():
        assert ex.prepare_image(s["path"].read_bytes())
        result = ex.normalize(s["result"])
        assert ex.is_usable(result), s["id"]
        assert result["prevention_tips"], s["id"]
        assert result["error_line"], s["id"]


# ---- project consistency ------------------------------------------------------


def test_upload_limit_in_config_matches_code():
    tomllib = pytest.importorskip("tomllib")
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["server"]["maxUploadSize"] == ex.MAX_UPLOAD_MB


def test_stylesheet_is_balanced_and_covers_the_hooks_the_app_uses():
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    assert css.count("{") == css.count("}")
    for hook in ("st-key-topbar", "st-key-hero", "st-key-workspace", "st-key-results", "st-key-report_blocking", "prefers-reduced-motion"):
        assert hook in css, hook
