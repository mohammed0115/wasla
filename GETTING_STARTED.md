# Getting Started with Wasla (Waslah)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Create Superuser

```bash
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/

## Testing Phase 5 Features

### Health Checks

```bash
# Basic liveness check
curl http://127.0.0.1:8000/healthz

# Readiness check (DB + cache)
curl http://127.0.0.1:8000/readyz

# Metrics endpoint
curl http://127.0.0.1:8000/metrics
```

### Security Headers

```bash
# Verify security headers are present
curl -I http://127.0.0.1:8000/healthz | grep -E "X-|Content-Security|Referrer"
```

### Rate Limiting

```bash
# Test rate limiting (will get 429 after limit)
for i in {1..15}; do
  curl -X POST http://127.0.0.1:8000/auth/login/
done
```

### Domain Provisioning

```bash
# Provision pending domains (requires domains in DB)
python manage.py provision_domains
```

## Running Tests

```bash
# Run all tests
python manage.py test

# Run Phase 5 specific tests
python manage.py test apps.observability.tests

# Run with verbosity
python manage.py test apps.observability.tests -v 2
```

## Project Structure

```
wasla/
├── apps/                      # Django apps
│   ├── accounts/             # User management
│   ├── ai/                   # AI features
│   ├── analytics/            # Analytics
│   ├── cart/                 # Shopping cart
│   ├── catalog/              # Products & categories
│   ├── checkout/             # Checkout process
│   ├── customers/            # Customer management
│   ├── domains/              # Custom domain provisioning
│   ├── observability/        # Health checks, metrics, logging
│   ├── orders/               # Order management
│   ├── payments/             # Payment processing
│   ├── security/             # Rate limiting, headers
│   ├── tenants/              # Multi-tenant support
│   └── ...
├── Docs/                     # Documentation
│   ├── ssl.md               # SSL provisioning runbook
│   ├── monitoring.md        # Monitoring guide
│   ├── incident.md          # Incident response
│   └── ...
├── infrastructure/           # Infrastructure configs
│   └── nginx/
│       └── domain.conf.j2   # Nginx template
├── static/                   # Static files
├── templates/                # Django templates
├── wasla_sore/              # Main Django config
├── manage.py
├── requirements.txt
└── PHASE5_SUMMARY.md        # Phase 5 completion summary
```

## Environment Variables

### Development

```bash
export DJANGO_DEBUG=1
export DJANGO_SECRET_KEY="your-secret-key"
export ENVIRONMENT=development
```

### Production

```bash
export DJANGO_DEBUG=0
export DJANGO_SECRET_KEY="your-secure-secret-key"
export ENVIRONMENT=production
export DJANGO_SESSION_COOKIE_SECURE=1
export DJANGO_CSRF_COOKIE_SECURE=1
export DJANGO_SECURE_SSL_REDIRECT=1
export CUSTOM_DOMAIN_SSL_ENABLED=1
export CUSTOM_DOMAIN_NGINX_ENABLED=1
```

## Documentation

- **[Phase 5 Summary](PHASE5_SUMMARY.md)** - Complete overview of Phase 5 implementation
- **[Developer Guide](Docs/DEVELOPER_GUIDE.md)** - Development setup and guidelines
- **[Technical Architecture](Docs/TECHNICAL_ARCHITECTURE.md)** - System architecture
- **[SSL Runbook](Docs/ssl.md)** - SSL provisioning procedures
- **[Monitoring Guide](Docs/monitoring.md)** - Observability setup
- **[Incident Response](Docs/incident.md)** - Incident handling procedures

## Key Features

### Multi-Tenant E-commerce Platform
- Multiple stores on single platform
- Tenant isolation at data level
- Custom domain support per store

### Security (Phase 5)
- Security headers (CSP, X-Frame-Options, etc.)
- Rate limiting on sensitive endpoints
- Secure cookie configuration
- Input validation and size limits

### Observability (Phase 5)
- Health check endpoints
- Metrics collection
- Structured JSON logging
- Request ID tracking
- Response time tracking

### Domain Provisioning (Phase 5)
- Automated domain verification
- SSL certificate issuance (Let's Encrypt)
- Safe Nginx configuration management
- Rollback on failure

## Common Commands

```bash
# Database
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Data
python manage.py seed_sample --tenant default
python manage.py validate_flows --tenant store1

# Domain Management
python manage.py provision_domains

# Testing
python manage.py test
python manage.py check
python manage.py check --deploy

# Static Files
python manage.py collectstatic
```

## Support

For issues or questions about the project, please refer to:
1. The comprehensive documentation in the `Docs/` folder
2. The Phase 5 summary document
3. The inline code comments and docstrings

## License

See repository for license information.
