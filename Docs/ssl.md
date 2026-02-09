## SSL Provisioning Runbook

### Overview
Custom domains are provisioned offline via the management command:
`python manage.py provision_domains`

The pipeline performs:
1) DNS + HTTP verification
2) SSL issuance (certbot)
3) Nginx config render
4) `nginx -t`
5) `systemctl reload nginx`

### Prerequisites
- DNS A or CNAME record points to the server
- HTTP challenge reachable: `/.well-known/wassla-domain-verification/<token>`
- Certbot installed and configured

### Common Failures
- DNS mismatch → fix A/CNAME, rerun command
- Certbot missing → install and retry
- Nginx test fails → fix config and rerun

### Recovery
If a reload fails, the command restores previous config and marks domain as FAILED.
Update DNS or config and rerun.
