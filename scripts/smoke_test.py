from __future__ import annotations

import json
import os
import sys
from urllib.request import urlopen


def fetch_json(base_url: str, path: str) -> dict:
    with urlopen(f"{base_url}{path}", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def fetch_text(base_url: str, path: str) -> str:
    with urlopen(f"{base_url}{path}", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned HTTP {response.status}")
        return response.read().decode("utf-8")


def main() -> int:
    base_url = os.getenv("SECURE_PROMPT_GUARD_BASE_URL", "http://127.0.0.1:8000")
    checks = {
        "/health": fetch_json(base_url, "/health"),
        "/openapi.json": fetch_json(base_url, "/openapi.json"),
        "/api/v1/models": fetch_json(base_url, "/api/v1/models"),
    }
    metrics = fetch_text(base_url, "/metrics")
    if "secure_prompt_guard_http_requests_total" not in metrics:
        raise RuntimeError("/metrics did not expose expected metric family")
    print(json.dumps({"base_url": base_url, "checks": list(checks)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
