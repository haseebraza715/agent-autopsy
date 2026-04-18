from src.ui import streamlit_pages as ui

ui.configure_page(page_title="Reports — Agent Autopsy")
ui.init_session_state()
ui.render_sidebar()
ui.render_reports_page()
