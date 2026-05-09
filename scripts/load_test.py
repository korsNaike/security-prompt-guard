from __future__ import annotations

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen


def hit(url: str) -> float:
    start = time.perf_counter()
    with urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP {response.status}")
        response.read()
    return time.perf_counter() - start


def main() -> int:
    base_url = os.getenv("SECURE_PROMPT_GUARD_BASE_URL", "http://127.0.0.1:8000")
    requests = int(os.getenv("LOAD_TEST_REQUESTS", "50"))
    concurrency = int(os.getenv("LOAD_TEST_CONCURRENCY", "5"))
    url = f"{base_url}/health"

    latencies: list[float] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(hit, url) for _ in range(requests)]
        for future in as_completed(futures):
            latencies.append(future.result())

    print(
        {
            "url": url,
            "requests": requests,
            "concurrency": concurrency,
            "min_ms": round(min(latencies) * 1000, 2),
            "avg_ms": round(statistics.mean(latencies) * 1000, 2),
            "max_ms": round(max(latencies) * 1000, 2),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
