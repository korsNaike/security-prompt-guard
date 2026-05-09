from __future__ import annotations


def main() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Install `streamlit` to run the optional dashboard.") from exc

    st.set_page_config(page_title="UniClassify Analytics", layout="wide")
    st.title("UniClassify Analytics")
    st.caption("Operational dashboard placeholder. Do not display raw classified text.")
    st.metric("Requests", "Use Prometheus/Grafana")
    st.metric("Billing", "Use admin API")
    st.metric("Models", "Use /api/v1/admin/models")


if __name__ == "__main__":
    main()
