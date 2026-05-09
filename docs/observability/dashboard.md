# Observability Dashboard

## Metrics

The backend exposes Prometheus-compatible text at `/metrics`.

Current metric families:

- `uniclassify_http_requests_total`
- `uniclassify_http_request_duration_seconds_sum`
- `uniclassify_http_request_duration_seconds_count`
- `uniclassify_worker_outcomes_total`

## Grafana

The starter dashboard is stored at:

- `dashboards/grafana/uniclassify-overview.json`

It tracks request rate, average latency and worker outcomes by model/status/cache-hit labels.

## Streamlit

`scripts/dashboard_app.py` is optional and guarded by a `streamlit` import check. It is intentionally not part of the production API runtime dependencies.

## Privacy Rule

Dashboards must not display raw prompt text or classified user text. Use request IDs, counts, model codes, status, risk labels and aggregate billing metrics.
