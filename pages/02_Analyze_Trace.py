from agent_autopsy.ui import streamlit_pages as ui

ui.configure_page(page_title="Analyze — Agent Autopsy")
ui.init_session_state()
ui.render_sidebar()
ui.render_analyze_page()
