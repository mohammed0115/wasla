## Incident Response Runbook

### Severity Levels
- SEV1: Platform outage / payments down
- SEV2: Partial outage / domain routing failures
- SEV3: Degraded performance

### Immediate Actions
1) Check `/healthz` and `/readyz`
2) Inspect recent logs (request_id, tenant_id)
3) Validate Nginx config: `nginx -t`
4) Roll back recent changes if needed

### Domain Routing Issues
- Verify domain status in DB
- Rerun `python manage.py provision_domains`
- Confirm DNS A/CNAME records

### Post-Incident
- Capture root cause
- Document timeline
- Add preventive checks
