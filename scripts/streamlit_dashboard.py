import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def fetch_json(path: str, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_BASE_URL}{path}", headers=headers)
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


st.set_page_config(page_title="UniClassify", layout="wide")
st.title("UniClassify")

try:
    health = fetch_json("/health")
    models = fetch_json("/api/v1/models")
except (HTTPError, URLError) as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

st.subheader("Service")
st.json(health)

st.subheader("Models")
st.json(models)

token = st.text_input("API token", type="password")
if token:
    cols = st.columns(3)
    with cols[0]:
        st.subheader("Balance")
        st.json(fetch_json("/api/v1/billing/balance", token))
    with cols[1]:
        st.subheader("Analytics")
        st.json(fetch_json("/api/v1/analytics/summary", token))
    with cols[2]:
        st.subheader("Usage")
        st.json(fetch_json("/api/v1/analytics/usage", token))
