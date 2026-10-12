"""Error Screenshot Explainer: Gemma 4 (via the Gemini API) turns an error screenshot into a fix.

Run:  streamlit run app.py

Layout lives here, model logic in explainer.py, styling and report rendering in ui.py,
design tokens in assets/styles.css.
"""
import io
import os

import streamlit as st
from PIL import Image

import explainer as ex
import ui
from samples import load_samples

st.set_page_config(page_title="Error Screenshot Explainer", page_icon="🛠️", layout="wide")

MODES = ["Upload Screenshot", "Try Sample", "Camera"]
IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
SAMPLES = load_samples()
SAMPLES_BY_ID = {s["id"]: s for s in SAMPLES}

# ------------------------------------------------------------------ state ----
ss = st.session_state
ss.setdefault("explanation", None)  # ex.Explanation of the last successful analysis
ss.setdefault("image", None)  # PNG bytes that were analysed (used by follow-ups)
ss.setdefault("chat", [])  # [(role, text)] follow-up conversation
ss.setdefault("error", None)  # message from the last failed analysis
ss.setdefault("busy", False)  # True while an analysis is running
ss.setdefault("upload_bytes", None)
ss.setdefault("upload_name", None)
ss.setdefault("upload_n", 0)  # bumping this key gives a fresh, empty uploader
ss.setdefault("cam_bytes", None)
ss.setdefault("cam_n", 0)
ss.setdefault("mode", MODES[0])
ss.setdefault("level", "Beginner")
ss.setdefault("lang", ex.LANGS[0])
ss.setdefault("model", ex.MODELS[0])
ss.setdefault("offline", False)
ss.setdefault("extra", "")
if SAMPLES:
    ss.setdefault("sample_id", SAMPLES[0]["id"])


def start_analysis():
    ss.busy = True
    ss.error = None


def clear_results():
    ss.explanation, ss.image, ss.error, ss.chat = None, None, None, []


def replace_upload():  # keeps the current report until the new screenshot is analysed
    ss.upload_bytes, ss.upload_name = None, None
    ss.upload_n += 1


def remove_upload():
    replace_upload()
    clear_results()


def replace_camera():
    ss.cam_bytes = None
    ss.cam_n += 1


def remove_camera():
    replace_camera()
    clear_results()


def pick_sample(sample_id: str):
    ss.sample_id = sample_id


def reset_all():
    remove_upload()
    remove_camera()
    ss.extra, ss.busy = "", False


# ---------------------------------------------------------------- top bar ----
ui.inject_css()

with st.container(key="topbar"):
    c_brand, c_settings, c_new = st.columns([6, 1.7, 1.8], vertical_alignment="center")
    with c_brand:
        ui.brand()
    with c_settings:
        with st.popover("Settings", icon=":material/settings:"):
            api_key = st.text_input(
                "Gemini API key",
                value=os.getenv("GEMINI_API_KEY", ""),
                type="password",
                key="api_key",
                help="Free from Google AI Studio. It stays in this session and is never shown or saved.",
            )
            model = st.selectbox("Gemma 4 model", ex.MODELS, key="model")
            offline = st.toggle(
                "Offline demo mode",
                key="offline",
                help="Shows pre-computed results for the built-in samples with no API call. A backup for when Wi-Fi fails.",
            )
    with c_new:
        st.button("New analysis", icon=":material/add:", on_click=reset_all, key="new_analysis")

# ------------------------------------------------------------------- hero ----
with st.container(key="hero"):
    c_text, c_art = st.columns([7, 3], vertical_alignment="center")
    with c_text:
        ui.hero_text()
    with c_art:
        ui.hero_art()

# -------------------------------------------------------------- workspace ----
left, right = st.columns([5, 6], gap="large")

with left, st.container(key="workspace"):
    ui.card_title("Add a screenshot")
    mode = st.segmented_control("Input method", MODES, key="mode", label_visibility="collapsed") or MODES[0]

    raw, name, sample = None, None, None
    if mode == MODES[0]:
        if ss.upload_bytes is None:
            uploaded = st.file_uploader(
                "Error screenshot", type=IMAGE_TYPES, key=f"upload_{ss.upload_n}", label_visibility="collapsed"
            )
            if uploaded is not None:
                ss.upload_bytes, ss.upload_name = uploaded.getvalue(), uploaded.name
                st.rerun()
        else:
            raw, name = ss.upload_bytes, ss.upload_name
    elif mode == MODES[2]:
        if ss.cam_bytes is None:
            photo = st.camera_input("Take a photo of the error", key=f"camera_{ss.cam_n}", label_visibility="collapsed")
            if photo is not None:
                ss.cam_bytes = photo.getvalue()
                st.rerun()
        else:
            raw, name = ss.cam_bytes, "camera-capture.png"
    else:
        ui.section("Try a Sample Error")
        if not SAMPLES:
            st.warning("No samples found. Run `python make_samples.py` once to create them.")
        else:
            grid = st.columns(2)
            for i, s in enumerate(SAMPLES):
                state = "selected" if s["id"] == ss.sample_id else "idle"
                with grid[i % 2]:
                    st.button(s["title"], key=f"sample_{s['id']}__{state}", on_click=pick_sample, args=(s["id"],))
            sample = SAMPLES_BY_ID.get(ss.sample_id)
            if sample:
                raw, name = sample["path"].read_bytes(), sample["path"].name

    # Preview with file details
    png = None
    if raw:
        try:
            png = ex.prepare_image(raw)
        except ex.ExplainerError as err:
            st.error(str(err))
    if png:
        st.image(png)
        width, height = Image.open(io.BytesIO(raw)).size
        ui.meta(f"{name}, {ui.human_size(len(raw))}, {width} x {height} px")
    if raw and mode in (MODES[0], MODES[2]):
        b1, b2 = st.columns(2)
        replace, remove = (replace_upload, remove_upload) if mode == MODES[0] else (replace_camera, remove_camera)
        with b1:
            st.button("Replace" if mode == MODES[0] else "Retake", icon=":material/swap_horiz:", on_click=replace, key="replace")
        with b2:
            st.button("Remove", icon=":material/delete:", on_click=remove, key="remove")

    st.text_area(
        "Add context (optional)",
        key="extra",
        placeholder="Tell us what you were doing when this error occurred...",
        max_chars=500,
        height=96,
    )
    o1, o2 = st.columns(2)
    with o1:
        st.segmented_control("Explain as", list(ex.LEVELS), key="level")
    with o2:
        st.selectbox("Language", ex.LANGS, key="lang")
    level = ss.level or "Beginner"
    lang = ss.lang

    has_key = bool((api_key or "").strip())
    can_run = png is not None and ((offline and sample is not None) or (not offline and has_key))
    st.button(
        "Analyzing..." if ss.busy else "Analyze Error",
        type="primary",
        icon=":material/hourglass_top:" if ss.busy else ":material/search:",
        disabled=(not can_run) or ss.busy,
        on_click=start_analysis,
        key="explain",
    )
    if png is None:
        ui.hint("Add a screenshot to continue.")
    elif offline and sample is None:
        ui.hint("Offline demo mode only works with the built-in samples. Choose Try Sample, or turn it off in Settings.")
    elif offline:
        ui.hint("Offline demo mode: you will see a pre-computed result for this sample, with no API call.")
    elif not has_key:
        ui.hint("Add your Gemini API key in Settings to analyze live.")

# ---------------------------------------------------------------- results ----
with right, st.container(key="results"):
    ui.card_title("Diagnostic report")

    if ss.busy:
        with st.status("Analyzing your screenshot", expanded=True) as status:
            try:
                if not can_run:
                    raise ex.ExplainerError("Add a screenshot and an API key (or use a sample in Offline demo mode) first.")
                if offline:
                    status.write("Loading the pre-computed result for this sample")
                    ss.explanation = ex.Explanation(
                        result=ex.normalize(sample["result"]), seconds=0.0, model="seeded", seeded=True
                    )
                else:
                    ss.explanation = ex.explain_screenshot(
                        api_key, model, png, lang, level, ss.extra, progress=status.write
                    )
                ss.image, ss.chat, ss.error = png, [], None
                status.update(label="Analysis complete", state="complete")
            except ex.ExplainerError as err:
                ss.error = str(err)
                status.update(label="Analysis failed", state="error")
            except Exception as err:  # never leave the UI stuck in the busy state
                ss.error = f"Unexpected error: {str(err)[:200]}"
                status.update(label="Analysis failed", state="error")
        ss.busy = False
        st.rerun()

    elif ss.error:
        ui.error_card(ss.error)
        st.button("Retry analysis", icon=":material/refresh:", on_click=start_analysis, key="retry", disabled=not can_run)
        ui.hint("No connection? Turn on Offline demo mode in Settings and choose Try Sample.")

    elif ss.explanation:
        ui.render_report(ss.explanation)

        st.divider()
        ui.section("Ask a follow-up")
        for role, text in ss.chat:
            with st.chat_message(role):
                st.markdown(text)
        if offline:
            ui.hint("Follow-up questions need the live API. Turn off Offline demo mode in Settings to use them.")
        elif not has_key:
            ui.hint("Add your Gemini API key in Settings to ask follow-up questions.")
        else:
            question = st.chat_input("Ask about this error, for example: why does it happen?", key="followup")
            if question:
                ss.chat.append(("user", question))
                try:
                    with st.spinner("Thinking..."):
                        answer = ex.follow_up(
                            api_key, model, ss.image, ss.explanation.result, ss.chat[:-1], question, lang, level
                        )
                except ex.ExplainerError as err:
                    answer = f"Couldn't answer that: {err}"
                ss.chat.append(("assistant", answer))
                st.rerun()

    else:
        ui.empty_state()

st.caption("Built with Gemma 4 through the Gemini API for Hacktoberfest Hack Day Hyderabad (MLH x NIAT).")
