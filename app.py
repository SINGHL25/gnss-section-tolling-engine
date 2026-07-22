"""Streamlit front end for GNSS Section Tolling Engine.

Two ways to run this repository, neither of which needs the other:

  * Open ``demo/index.html`` in any browser. It is self-contained, so it needs
    nothing installed at all, and it is what gets published to GitHub Pages.
  * Run this app for the same demo plus the source, the scenarios and the tests
    in one place::

        pip install -r requirements.txt
        streamlit run app.py

This file draws only. All the engineering lives in ``gnss_tolling``, which imports
nothing outside the standard library.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st

REPO = Path(__file__).resolve().parent
PKG = "gnss_tolling"
TITLE = "GNSS Section Tolling Engine"
SUBTITLE = "POSITION · MAP-MATCH · SECTION · DISTANCE RATE"

st.set_page_config(page_title=TITLE, page_icon="◧", layout="wide")

st.markdown("""
<style>
  .stApp { background:#0D1117; }
  .block-container { padding-top:2rem; max-width:1500px; }
  .hdr { border:1px solid #212B36; background:#151C24; padding:14px 18px; margin-bottom:14px; }
  .hdr h1 { margin:0; font-size:16px; font-weight:600; letter-spacing:.22em;
            text-transform:uppercase; color:#D8E2EC; }
  .hdr .sub { font-family:ui-monospace,Menlo,monospace; font-size:11px;
              color:#7D8FA3; margin-top:5px; letter-spacing:.05em; }
  .pill { display:inline-block; font-family:ui-monospace,Menlo,monospace; font-size:9.5px;
          padding:1px 7px; border:1px solid #212B36; margin-right:4px; color:#7D8FA3; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"<div class='hdr'><h1>{TITLE}</h1><div class='sub'>{SUBTITLE}</div></div>",
            unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def python_files() -> dict:
    out = {}
    skip = {"__pycache__", ".pytest_cache", ".venv", ".git"}
    for p in sorted(REPO.rglob("*.py")):
        if any(part in skip for part in p.parts):
            continue
        try:
            out[str(p.relative_to(REPO))] = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return out


sources = python_files()
demo = REPO / "demo" / "index.html"
readme = REPO / "README.md"

tab_demo, tab_read, tab_code, tab_scen, tab_test = st.tabs(
    ["Demo", "Overview", "Code", "Scenarios", "Tests"])

with tab_demo:
    if demo.exists():
        st.caption("Self-contained — the same file GitHub Pages serves. "
                   "It runs entirely in the browser.")
        if hasattr(st, "iframe"):
            st.iframe(demo, height=1400)
        else:
            import streamlit.components.v1 as components
            components.html(demo.read_text(encoding="utf-8"), height=1400, scrolling=True)
    else:
        st.info("This repository has no demo/index.html.")

with tab_read:
    if readme.exists():
        st.markdown(readme.read_text(encoding="utf-8"))
    else:
        st.caption("No README found.")

with tab_code:
    if not sources:
        st.caption("No Python files found.")
    else:
        left, right = st.columns([1, 2.6])
        with left:
            chosen = st.radio("File", list(sources), label_visibility="collapsed")
        with right:
            text = sources[chosen]
            st.markdown(
                f"<span class='pill'>{text.count(chr(10)) + 1} lines</span>"
                f"<span class='pill'>{len(text):,} chars</span>",
                unsafe_allow_html=True)
            st.code(text, language="python", line_numbers=True)

with tab_scen:
    try:
        import inspect

        module = __import__(PKG)
        names = list(getattr(module, "SCENARIOS", {}))
        if not names:
            st.caption("This package exposes no scenarios.")
        else:
            st.caption(f"{len(names)} scenario(s). The demo tab runs them interactively; "
                       "this shows what each one builds.")
            picked = st.selectbox("Scenario", names)
            # Signatures differ across the portfolio: some scenarios need extra
            # context the demo supplies, so ask rather than assume.
            builder = module.apply_scenario
            needed = [q for q in inspect.signature(builder).parameters.values()
                      if q.default is q.empty
                      and q.kind in (q.POSITIONAL_ONLY, q.POSITIONAL_OR_KEYWORD)]
            if len(needed) > 1:
                extra = ", ".join(q.name for q in needed[1:])
                st.info(f"apply_scenario also needs {extra} in this package, which the "
                        "demo tab supplies. Showing the scenario list only.")
                st.write(names)
                st.stop()
            built = builder(picked)
            st.markdown(f"<span class='pill'>{type(built).__name__}</span>",
                        unsafe_allow_html=True)
            if hasattr(built, "__dict__"):
                st.json({k: str(v)[:400] for k, v in vars(built).items()}, expanded=False)
            elif isinstance(built, (list, tuple)):
                st.write(f"{len(built)} item(s)")
                st.json([str(x)[:200] for x in list(built)[:12]], expanded=False)
            else:
                st.write(built)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
        st.warning(f"Could not load scenarios: {exc}")

with tab_test:
    st.caption("Runs the suite in this checkout. Streamlit Cloud can run it too.")
    if st.button("Run the tests", width="stretch"):
        try:
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                                  cwd=str(REPO), capture_output=True,
                                  text=True, timeout=300)
            body = (proc.stdout or "") + (proc.stderr or "")
            (st.success if proc.returncode == 0 else st.error)(
                f"pytest exited {proc.returncode}")
            st.code(body[-10000:] or "(no output)", language=None)
        except FileNotFoundError:
            st.error("pytest is not installed in this environment.")
        except subprocess.TimeoutExpired:
            st.error("The test run timed out.")
