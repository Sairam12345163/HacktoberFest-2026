"""UI tests using Streamlit's headless AppTest (no browser, no network, fake Gemini client)."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import explainer as ex
from helpers import GOOD_JSON, FakeClient, png_bytes
from samples import load_samples

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SAMPLE = "Try Sample"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)


def start(**state):
    at = AppTest.from_file(APP, default_timeout=30)
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def html(at):
    return "\n".join(m.value for m in at.markdown)


def use_client(monkeypatch, *replies):
    client = FakeClient(list(replies))
    monkeypatch.setattr(ex, "get_client", lambda key: client)
    return client


# ---- first impression --------------------------------------------------------


def test_page_loads_with_header_hero_and_empty_state():
    at = start()
    assert not at.exception
    page = html(at)
    assert "Error Screenshot Explainer" in page
    assert "Understand Any Error. Fix It Faster." in page
    assert "Turn confusing error screenshots into clear explanations and actionable solutions with AI." in page
    assert "Your diagnostic report will appear here" in page
    assert at.button(key="explain").disabled
    assert "Add a screenshot to continue." in html(at)


def test_context_box_has_the_requested_placeholder_and_limit():
    box = start().text_area(key="extra")
    assert box.placeholder == "Tell us what you were doing when this error occurred..."
    assert box.max_chars == 500


def test_gallery_lists_the_six_requested_samples():
    at = start(mode=SAMPLE)
    labels = {b.label for b in at.button if b.key and b.key.startswith("sample_")}
    assert {"Python traceback", "JavaScript TypeError", "React rendering error", "Node.js module error",
            "SQL database error", "API authentication error"} <= labels


def test_clicking_a_sample_selects_it_and_shows_a_preview():
    at = start(mode=SAMPLE)
    at.button(key="sample_js_type_error__idle").click().run()
    assert at.session_state["sample_id"] == "js_type_error"
    assert any(b.key == "sample_js_type_error__selected" for b in at.button)
    assert "js_type_error.png" in html(at)


# ---- offline demo mode --------------------------------------------------------


def test_offline_sample_flow_shows_a_labelled_precomputed_report():
    at = start(mode=SAMPLE, offline=True)
    at.button(key="explain").click().run()
    assert not at.exception
    page = html(at)
    assert 'class="summary"' in page and "pandas" in page
    assert "Blocking error" in page and "Pre-computed demo result" in page
    assert any("pip install pandas" in c.value for c in at.code)


@pytest.mark.parametrize("sample", load_samples(), ids=lambda s: s["id"])
def test_every_sample_renders_a_full_report_offline(sample):
    at = start(mode=SAMPLE, offline=True, sample_id=sample["id"])
    at.button(key="explain").click().run()
    assert not at.exception
    assert 'class="summary"' in html(at)
    expected = ex.normalize(sample["result"])
    if expected["code_fix"]:
        assert any(expected["code_fix"] in c.value for c in at.code), "code correction block"
    assert any("Copy full report" in e.label for e in at.expander)


def test_offline_with_an_upload_explains_the_limit_and_blocks_analysis():
    at = start(offline=True, upload_bytes=png_bytes(), upload_name="mine.png")
    assert at.button(key="explain").disabled
    assert "only works with the built-in samples" in html(at)


# ---- live mode ---------------------------------------------------------------


def test_live_mode_without_a_key_is_blocked_with_a_hint():
    at = start(mode=SAMPLE)
    assert at.button(key="explain").disabled
    assert "Add your Gemini API key in Settings" in html(at)


def test_live_analysis_uses_the_model_and_renders_every_section(monkeypatch):
    client = use_client(monkeypatch, GOOD_JSON)
    at = start(mode=SAMPLE, model="gemma-4-31b-it", extra="I just made a venv")
    at.text_input(key="api_key").set_value("fake-key").run()
    assert not at.button(key="explain").disabled
    at.button(key="explain").click().run()
    assert not at.exception
    page = html(at)
    for text in ("pandas is missing.", "Error summary", "Error type", "Root cause", "Recommended fix",
                 "Code correction", "Prevention tips", "gemma-4-31b-it"):
        assert text in page, text
    model, contents = client.models.calls[0]
    assert model == "gemma-4-31b-it"
    assert "I just made a venv" in contents[1]
    assert not at.session_state["busy"]


def test_failure_shows_an_actionable_error_and_retry_recovers(monkeypatch):
    use_client(monkeypatch, RuntimeError("403 PERMISSION_DENIED: API key not valid"))
    at = start(mode=SAMPLE)
    at.text_input(key="api_key").set_value("bad-key").run()
    at.button(key="explain").click().run()
    assert not at.exception and not at.session_state["busy"]
    assert "Analysis failed" in html(at) and "rejected your API key" in html(at)
    assert not at.button(key="retry").disabled

    use_client(monkeypatch, GOOD_JSON)
    at.button(key="retry").click().run()
    assert not at.exception
    assert 'class="summary"' in html(at) and at.session_state["error"] is None


def test_low_confidence_answers_carry_an_uncertainty_warning(monkeypatch):
    low = json.loads(GOOD_JSON) | {"confidence": "low"}
    use_client(monkeypatch, json.dumps(low))
    at = start(mode=SAMPLE)
    at.text_input(key="api_key").set_value("k").run()
    at.button(key="explain").click().run()
    assert any("best guess" in w.value for w in at.warning)


def test_follow_up_question_gets_an_answer(monkeypatch):
    client = use_client(monkeypatch, GOOD_JSON, "Because the venv differs.")
    at = start(mode=SAMPLE)
    at.text_input(key="api_key").set_value("k").run()
    at.button(key="explain").click().run()
    at.chat_input(key="followup").set_value("Why does this happen?").run()
    assert not at.exception
    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert any("Because the venv differs." in m.value for m in at.markdown)
    assert "Why does this happen?" in client.models.calls[-1][1][1]


# ---- upload workspace ----------------------------------------------------------


def test_upload_preview_shows_file_name_size_and_dimensions():
    at = start(upload_bytes=png_bytes((640, 360)), upload_name="crash.png")
    assert not at.exception
    assert "crash.png" in html(at) and "640 x 360 px" in html(at)
    assert {"replace", "remove"} <= {b.key for b in at.button}


def test_corrupt_upload_gets_a_clear_message_and_can_be_removed():
    at = start(upload_bytes=b"not an image", upload_name="broken.png")
    assert any("isn't a readable image" in e.value for e in at.error)
    assert at.button(key="explain").disabled
    at.button(key="remove").click().run()
    assert at.session_state["upload_bytes"] is None


def test_replace_keeps_the_report_but_remove_clears_it():
    at = start(mode=SAMPLE, offline=True)
    at.button(key="explain").click().run()
    assert at.session_state["explanation"] is not None

    at.session_state["mode"] = "Upload Screenshot"
    at.session_state["upload_bytes"] = png_bytes()
    at.session_state["upload_name"] = "x.png"
    at.run()
    at.button(key="replace").click().run()
    assert at.session_state["upload_bytes"] is None and at.session_state["explanation"] is not None

    at.session_state["upload_bytes"] = png_bytes()
    at.run()
    at.button(key="remove").click().run()
    assert at.session_state["explanation"] is None


def test_new_analysis_resets_everything():
    at = start(mode=SAMPLE, offline=True, extra="some context")
    at.button(key="explain").click().run()
    at.button(key="new_analysis").click().run()
    assert at.session_state["explanation"] is None and at.session_state["extra"] == ""
    assert "Your diagnostic report will appear here" in html(at)


# ---- safety -------------------------------------------------------------------


def test_error_messages_are_html_escaped():
    at = start(error="<script>alert(1)</script>")
    page = html(at)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)" not in page


def test_model_text_is_escaped_in_the_report(monkeypatch):
    evil = json.loads(GOOD_JSON) | {"error_summary": "<img src=x onerror=alert(1)>", "tool_or_language": "<b>x</b>"}
    use_client(monkeypatch, json.dumps(evil))
    at = start(mode=SAMPLE)
    at.text_input(key="api_key").set_value("k").run()
    at.button(key="explain").click().run()
    page = html(at)
    assert "&lt;img src=x onerror=alert(1)&gt;" in page and "<img src=x onerror" not in page
    assert "&lt;b&gt;x&lt;/b&gt;" in page
