import json
from pathlib import Path


def test_grafana_dashboard_is_parseable() -> None:
    dashboard = json.loads(Path("dashboards/grafana/secure-prompt-guard-overview.json").read_text())

    assert dashboard["title"] == "SecurePrompt Guard Overview"
    assert dashboard["panels"]
