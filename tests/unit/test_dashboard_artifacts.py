import json
from pathlib import Path


def test_grafana_dashboard_is_parseable() -> None:
    dashboard = json.loads(Path("dashboards/grafana/uniclassify-overview.json").read_text())

    assert dashboard["title"] == "UniClassify Overview"
    assert dashboard["panels"]


def test_observability_docs_include_privacy_rule() -> None:
    content = Path("docs/observability/dashboard.md").read_text()

    assert "must not display raw prompt text" in content
