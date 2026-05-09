from app.main import app


def test_app_metadata() -> None:
    assert app.title == "SecurePrompt Guard"
    assert app.version == "0.1.0"
    assert (
        app.description
        == "SecurePrompt Guard API for prompt injection, jailbreak, harmful prompt, "
        "and data exfiltration classification."
    )


def test_health_route_registered() -> None:
    route_paths = {route.path for route in app.routes}

    assert "/health" in route_paths
    assert "/ready" in route_paths
    assert "/docs" in route_paths
    assert "/openapi.json" in route_paths
