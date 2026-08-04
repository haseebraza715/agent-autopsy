"""
Agent Autopsy — Streamlit home page.

Run from the repository root::

    streamlit run app.py

Sub-pages live under ``pages/`` and share helpers in ``src.ui.streamlit_pages``.
"""

import streamlit as st

try:
    from agent_autopsy.ui import streamlit_pages as ui
except ModuleNotFoundError as exc:
    st.set_page_config(
        page_title="Agent Autopsy",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.error("Agent Autopsy failed to start because a Python dependency is missing.")
    st.code(str(exc))
    st.markdown(
        """
If you are deploying on Streamlit Cloud, make sure it installs this repository's
`requirements.txt`, which should pull in the local package and the `gui,llm` extras.
        """
    )
    st.stop()

ui.configure_page()
ui.init_session_state()
ui.render_sidebar()
ui.render_home_page()
