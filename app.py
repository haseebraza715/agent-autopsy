"""
Agent Autopsy — Streamlit home page.

Run from the repository root::

    streamlit run app.py

Sub-pages live under ``pages/`` and share helpers in ``src.ui.streamlit_pages``.
"""

import streamlit as st

from src.ui import streamlit_pages as ui

ui.configure_page()
ui.init_session_state()
ui.render_sidebar()
ui.render_home_page()
