from pathlib import Path


def test_streamlit_dashboard_script_exists_and_is_api_backed() -> None:
    script = Path("scripts/streamlit_dashboard.py")

    content = script.read_text()

    assert "import streamlit as st" in content
    assert "API_BASE_URL" in content
    assert "requests" not in content
    assert "urllib.request" in content
    assert 'st.form("api-token-form")' in content
    assert 'st.form_submit_button("Apply token")' in content
    assert "/api/v1/analytics/by-label" in content
    assert "/api/v1/classifications?limit=10" in content
    assert "/api/v1/billing/transactions" in content
