from fastapi.testclient import TestClient

from app.infrastructure.monitoring.metrics import metrics_registry
from app.main import app


def test_metrics_endpoint_exposes_prometheus_text() -> None:
    metrics_registry.reset()
    client = TestClient(app)

    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "uniclassify_http_requests_total" in response.text
    assert 'path="/health"' in response.text
