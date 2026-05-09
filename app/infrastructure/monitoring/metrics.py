from collections import Counter, defaultdict


class MetricsRegistry:
    def __init__(self) -> None:
        self.http_requests: Counter[tuple[str, str, str]] = Counter()
        self.http_duration_sum: Counter[tuple[str, str]] = Counter()
        self.http_duration_count: Counter[tuple[str, str]] = Counter()
        self.worker_outcomes: Counter[tuple[str, str, str]] = Counter()
        self.cache_hits: Counter[tuple[str, str]] = Counter()
        self._extra_gauges: dict[str, float] = defaultdict(float)

    def record_http(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        status_family = f"{status_code // 100}xx"
        self.http_requests[(method, path, status_family)] += 1
        self.http_duration_sum[(method, path)] += duration_seconds
        self.http_duration_count[(method, path)] += 1

    def record_worker(self, *, model_code: str, status: str, cache_hit: bool) -> None:
        self.worker_outcomes[(model_code, status, str(cache_hit).lower())] += 1
        if cache_hit:
            self.cache_hits[(model_code, status)] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP secure_prompt_guard_http_requests_total "
            "HTTP requests by method, path and status family.",
            "# TYPE secure_prompt_guard_http_requests_total counter",
        ]
        for (method, path, status), value in sorted(self.http_requests.items()):
            lines.append(
                "secure_prompt_guard_http_requests_total"
                f'{{method="{method}",path="{path}",status="{status}"}} {value}'
            )

        lines.extend(
            [
                "# HELP secure_prompt_guard_http_request_duration_seconds_sum Total HTTP latency.",
                "# TYPE secure_prompt_guard_http_request_duration_seconds_sum counter",
            ]
        )
        for (method, path), value in sorted(self.http_duration_sum.items()):
            lines.append(
                "secure_prompt_guard_http_request_duration_seconds_sum"
                f'{{method="{method}",path="{path}"}} {value:.6f}'
            )
        for (method, path), value in sorted(self.http_duration_count.items()):
            lines.append(
                "secure_prompt_guard_http_request_duration_seconds_count"
                f'{{method="{method}",path="{path}"}} {value}'
            )

        lines.extend(
            [
                "# HELP secure_prompt_guard_worker_outcomes_total Classification worker outcomes.",
                "# TYPE secure_prompt_guard_worker_outcomes_total counter",
            ]
        )
        for (model_code, status, cache_hit), value in sorted(self.worker_outcomes.items()):
            lines.append(
                "secure_prompt_guard_worker_outcomes_total"
                f'{{model_code="{model_code}",status="{status}",cache_hit="{cache_hit}"}} {value}'
            )

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        self.http_requests.clear()
        self.http_duration_sum.clear()
        self.http_duration_count.clear()
        self.worker_outcomes.clear()
        self.cache_hits.clear()
        self._extra_gauges.clear()


metrics_registry = MetricsRegistry()
