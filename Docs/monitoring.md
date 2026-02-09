## Monitoring & Observability

### Endpoints
- `/healthz` → basic app liveness
- `/readyz` → DB/cache readiness
- `/metrics` → request counters (cache-based)

### Logs
Structured JSON logs include:
- request_id
- tenant_id
- user_id
- path, method
- status_code, latency_ms

### Dashboards (baseline)
- 5xx rate
- latency p95
- webhook error count
- AI endpoint rate limit hits

### Alerts (baseline)
- readyz != ok
- 5xx rate > 2% for 5 minutes
- nginx reload failures
