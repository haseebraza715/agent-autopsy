from src.ui import streamlit_pages as ui

ui.configure_page(page_title="Trace Viewer — Agent Autopsy")
ui.init_session_state()
ui.render_sidebar()
ui.render_trace_viewer_page()
