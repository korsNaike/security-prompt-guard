from app.api.v1.router import api_router


def test_api_router_includes_analytics_routes() -> None:
    route_paths = {route.path for route in api_router.routes}

    assert "/analytics/summary" in route_paths
    assert "/analytics/usage" in route_paths
    assert "/analytics/costs" in route_paths
    assert "/analytics/models" in route_paths
