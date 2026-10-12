"""Presentation layer: design-system injection and the diagnostic report.

All model-generated text is escaped before it goes into HTML, or rendered with Streamlit's
safe markdown (which never executes HTML).
"""
from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

import explainer as ex

ASSETS = Path(__file__).parent / "assets"
esc = html.escape

# Lucide "wrench" glyph, drawn white on a teal rounded square
_WRENCH = (
    "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94"
    "l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
)
_BRAND_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36">'
    '<rect width="36" height="36" rx="9" fill="#0d9488"/>'
    '<g transform="translate(6 6)" fill="none" stroke="#fff" stroke-width="2" '
    f'stroke-linecap="round" stroke-linejoin="round"><path d="{_WRENCH}"/></g></svg>'
)
# A screenshot with an error line on the left turning into a checked fix
_HERO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="132" viewBox="0 0 240 132" fill="none">'
    '<rect x="1" y="1" width="238" height="130" rx="12" fill="#fff" stroke="#e2e8f0"/>'
    '<path d="M1 13a12 12 0 0 1 12-12h214a12 12 0 0 1 12 12v18H1z" fill="#f1f5f9"/>'
    '<circle cx="18" cy="16" r="4" fill="#fca5a5"/><circle cx="32" cy="16" r="4" fill="#fcd34d"/>'
    '<circle cx="46" cy="16" r="4" fill="#86efac"/>'
    '<rect x="16" y="44" width="150" height="8" rx="4" fill="#fecaca"/>'
    '<rect x="16" y="60" width="110" height="8" rx="4" fill="#e2e8f0"/>'
    '<rect x="16" y="76" width="130" height="8" rx="4" fill="#e2e8f0"/>'
    '<rect x="16" y="98" width="208" height="22" rx="8" fill="#f0fdfa" stroke="#99f6e4"/>'
    '<path d="M28 109l4 4 8-9" stroke="#0d9488" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
    '<rect x="50" y="106" width="120" height="6" rx="3" fill="#5eead4"/></svg>'
)


def _uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


BRAND_ICON = _uri(_BRAND_SVG)
HERO_ART = _uri(_HERO_SVG)


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def inject_css() -> None:
    """Inject the design system. The wrapper container hides itself via CSS once loaded."""
    css = (ASSETS / "styles.css").read_text(encoding="utf-8")
    css = "\n".join(line for line in css.splitlines() if line.strip())
    with st.container(key="css"):
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand() -> None:
    st.markdown(
        f'<div class="brand"><img class="brand-icon" src="{BRAND_ICON}" alt="" width="36" height="36"/>'
        '<div><div class="brand-name">Error Screenshot Explainer</div>'
        '<div class="brand-tag">Debug from a screenshot</div></div>'
        '<span class="badge">Gemma 4</span></div>',
        unsafe_allow_html=True,
    )


def hero_text() -> None:
    st.markdown(
        '<h1 class="hero-title">Understand Any Error. Fix It Faster.</h1>'
        '<p class="hero-sub">Turn confusing error screenshots into clear explanations and '
        "actionable solutions with AI.</p>",
        unsafe_allow_html=True,
    )


def hero_art() -> None:
    st.markdown(f'<img class="hero-art" src="{HERO_ART}" alt="A screenshot with an error becoming a fix"/>', unsafe_allow_html=True)


def card_title(text: str) -> None:
    st.markdown(f'<div class="card-title">{esc(text)}</div>', unsafe_allow_html=True)


def hint(text: str) -> None:
    st.markdown(f'<div class="hint">{esc(text)}</div>', unsafe_allow_html=True)


def meta(text: str) -> None:
    st.markdown(f'<div class="meta">{esc(text)}</div>', unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<div class="sec">{esc(label)}</div>', unsafe_allow_html=True)


def empty_state() -> None:
    st.markdown(
        '<div class="empty"><div class="empty-title">Your diagnostic report will appear here</div>'
        '<div class="empty-sub">Gemma 4 reads the exact error text in your screenshot, then explains it.</div>'
        "<ol><li>Add a screenshot of the error, or pick a sample</li>"
        "<li>Select Analyze Error</li>"
        "<li>Follow the fix steps and copy the commands</li></ol>"
        '<div class="empty-note">Screenshots are sent to the Gemini API for analysis. '
        "Hide passwords and API keys before you upload.</div></div>",
        unsafe_allow_html=True,
    )


def error_card(message: str) -> None:
    st.markdown(
        f'<div class="alert alert-error"><div class="alert-title">Analysis failed</div>{esc(message)}</div>',
        unsafe_allow_html=True,
    )


SEVERITY_LABEL = {"blocking": "Blocking error", "warning": "Warning", "info": "Notice"}
CONFIDENCE_LABEL = {"high": "High confidence", "medium": "Medium confidence", "low": "Low confidence"}


def _pills(e: ex.Explanation) -> str:
    r = e.result
    source = "Pre-computed demo result" if e.seeded else f"{e.model}, {e.seconds}s"
    kind = "neutral" if e.seeded else "live"
    return (
        '<div class="pills">'
        f'<span class="pill pill-sev pill-{esc(r["severity"])}">{SEVERITY_LABEL[r["severity"]]}</span>'
        f'<span class="pill pill-neutral">{CONFIDENCE_LABEL[r["confidence"]]}</span>'
        f'<span class="pill pill-{kind}">{esc(source)}</span></div>'
    )


def render_report(e: ex.Explanation) -> None:
    """The diagnostic report. Sections only appear when the model's answer supports them."""
    r = e.result
    with st.container(key=f"report_{r['severity']}"):
        st.markdown(_pills(e), unsafe_allow_html=True)

        section("Error summary")
        st.markdown(f'<div class="summary">{esc(r["error_summary"])}</div>', unsafe_allow_html=True)
        if r["error_line"]:
            st.code(r["error_line"], language=None)

        section("Error type")
        st.markdown(f'<span class="chip">{esc(r["tool_or_language"])}</span>', unsafe_allow_html=True)

        section("Root cause")
        if r["confidence"] == "low":
            st.warning("The screenshot doesn't give enough detail to be sure. Treat this as a best guess.")
        if r["likely_cause"]:
            st.markdown(r["likely_cause"])
        if r["alternative_causes"]:
            with st.expander("Other possibilities"):
                for cause in r["alternative_causes"]:
                    st.markdown(f"- {cause}")

        if r["fix_steps"] or r["commands"]:
            section("Recommended fix")
        if r["fix_steps"]:
            st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(r["fix_steps"], 1)))
        if r["commands"]:
            st.code("\n".join(r["commands"]), language="bash")

        if r["code_fix"]:
            section("Code correction")
            st.code(r["code_fix"], language=r["code_language"])

        if r["prevention_tips"]:
            section("Prevention tips")
            with st.expander("How to avoid this next time"):
                for tip in r["prevention_tips"]:
                    st.markdown(f"- {tip}")

        if r["if_still_stuck"]:
            st.info(f"Still stuck? {r['if_still_stuck']}")

        section("Share or save")
        st.download_button(
            "Download report",
            ex.to_markdown(r),
            file_name="error-report.md",
            mime="text/markdown",
            icon=":material/download:",
            key="download",
        )
        with st.expander("Copy full report"):
            st.code(ex.to_markdown(r), language="markdown")
