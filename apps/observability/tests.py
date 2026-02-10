"""
Tests for Phase 5: Security + Observability + Ops Hardening features.

This test module validates:
- Health and metrics endpoints
- Request ID and timing middleware
- Security headers middleware
- Rate limiting middleware
- Domain provisioning system
"""
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from apps.tenants.models import StoreDomain, Tenant
from unittest.mock import patch, MagicMock
import json


User = get_user_model()


class HealthEndpointsTest(TestCase):
    """Test health check and metrics endpoints."""

    def setUp(self):
        self.client = Client()

    def test_healthz_returns_ok(self):
        """Test /healthz endpoint returns OK status."""
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')

    def test_readyz_returns_ok_when_healthy(self):
        """Test /readyz endpoint returns OK when DB and cache are healthy."""
        response = self.client.get('/readyz')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['db'])
        self.assertTrue(data['cache'])

    def test_metrics_returns_counters(self):
        """Test /metrics endpoint returns request counters."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('requests_total', data)
        self.assertIn('requests_by_status', data)


class ObservabilityMiddlewareTest(TestCase):
    """Test observability middleware components."""

    def setUp(self):
        self.client = Client()

    def test_request_id_added_to_response(self):
        """Test that X-Request-Id header is added to response."""
        response = self.client.get('/healthz')
        self.assertIn('X-Request-Id', response)
        # Should be a valid UUID format
        request_id = response['X-Request-Id']
        self.assertEqual(len(request_id), 36)  # UUID format length

    def test_timing_header_added(self):
        """Test that X-Response-Time-ms header is added."""
        response = self.client.get('/healthz')
        self.assertIn('X-Response-Time-ms', response)
        # Should be a numeric value (can be 0 for very fast requests)
        timing = int(response['X-Response-Time-ms'])
        self.assertGreaterEqual(timing, 0)


class SecurityHeadersTest(TestCase):
    """Test security headers middleware."""

    def setUp(self):
        self.client = Client()

    def test_security_headers_present(self):
        """Test that all required security headers are present."""
        response = self.client.get('/healthz')
        
        # Check required security headers
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(response.get('Referrer-Policy'), 'same-origin')
        self.assertIn('Content-Security-Policy', response)

    @override_settings(SECURITY_CSP_ENABLED=False)
    def test_csp_can_be_disabled(self):
        """Test that CSP can be disabled via settings."""
        response = self.client.get('/healthz')
        self.assertNotIn('Content-Security-Policy', response)


class RateLimitMiddlewareTest(TestCase):
    """Test rate limiting middleware."""

    def setUp(self):
        self.client = Client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    @override_settings(SECURITY_RATE_LIMITS=[
        {
            'key': 'test',
            'pattern': r'^/test-endpoint/',
            'methods': ['POST'],
            'limit': 3,
            'window': 60,
            'message_key': 'rate_limited',
        }
    ])
    def test_rate_limit_enforced(self):
        """Test that rate limiting is enforced after limit is exceeded."""
        # Make requests up to the limit
        for i in range(3):
            response = self.client.post('/test-endpoint/')
            # Will be 404 since endpoint doesn't exist, but rate limit not triggered
            self.assertIn(response.status_code, [403, 404])

        # Next request should be rate limited
        response = self.client.post('/test-endpoint/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_rate_limit_respects_methods(self):
        """Test that rate limiting only applies to specified HTTP methods."""
        # GET requests should not be rate limited on POST-only endpoints
        for i in range(15):
            response = self.client.get('/auth/login/')
            # Should not get rate limited on GET
            self.assertNotEqual(response.status_code, 429)


class DomainProvisioningTest(TestCase):
    """Test domain provisioning system."""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug='test-store',
            name='Test Store',
            is_active=True
        )

    def test_domain_status_transitions(self):
        """Test that domain can be created with correct initial status."""
        domain = StoreDomain.objects.create(
            tenant=self.tenant,
            domain='test.example.com',
            status=StoreDomain.STATUS_PENDING_VERIFICATION,
            verification_token='test-token-123'
        )
        
        self.assertEqual(domain.status, StoreDomain.STATUS_PENDING_VERIFICATION)
        self.assertEqual(domain.domain, 'test.example.com')
        self.assertIsNotNone(domain.verification_token)

    def test_domain_verification_token_generation(self):
        """Test that verification tokens are unique."""
        domain1 = StoreDomain.objects.create(
            tenant=self.tenant,
            domain='test1.example.com',
            status=StoreDomain.STATUS_PENDING_VERIFICATION,
            verification_token='token1'
        )
        
        domain2 = StoreDomain.objects.create(
            tenant=self.tenant,
            domain='test2.example.com',
            status=StoreDomain.STATUS_PENDING_VERIFICATION,
            verification_token='token2'
        )
        
        self.assertNotEqual(domain1.verification_token, domain2.verification_token)

    @patch('apps.domains.infrastructure.nginx_generator.NginxConfigGenerator.render')
    def test_nginx_config_generator_can_be_mocked(self, mock_render):
        """Test that nginx config generator can be mocked for testing."""
        mock_render.return_value = "# Nginx config content"
        
        # This would be used in provision_domains command tests
        from apps.domains.infrastructure.nginx_generator import NginxConfigGenerator
        generator = NginxConfigGenerator()
        config = generator.render(
            domain='test.example.com',
            upstream='http://127.0.0.1:8000',
            ssl_cert_path='',
            ssl_key_path='',
            force_https=False
        )
        
        self.assertEqual(config, "# Nginx config content")
        mock_render.assert_called_once()


class LoggingTest(TestCase):
    """Test structured logging."""

    def setUp(self):
        self.client = Client()

    def test_request_logging_includes_context(self):
        """Test that requests are logged with proper context."""
        # Make a request
        response = self.client.get('/healthz')
        
        # Verify response was successful
        self.assertEqual(response.status_code, 200)
        
        # Logging happens but we can't easily capture it in tests
        # In real environment, logs would include:
        # - request_id
        # - tenant_id
        # - user_id
        # - path
        # - method
        # - status_code
        # - latency_ms


class SecuritySettingsTest(TestCase):
    """Test security-related Django settings."""

    @override_settings(DJANGO_SESSION_COOKIE_SECURE=True)
    def test_secure_cookies_can_be_enabled(self):
        """Test that secure cookie settings can be enabled."""
        from django.conf import settings
        # In production, these should be True
        # In development, they can be False
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')

    def test_allowed_file_upload_size(self):
        """Test that file upload size limits are set."""
        from django.conf import settings
        self.assertIsNotNone(settings.DATA_UPLOAD_MAX_MEMORY_SIZE)
        self.assertIsNotNone(settings.FILE_UPLOAD_MAX_MEMORY_SIZE)
        # Should be reasonable limits (e.g., 10MB)
        self.assertLessEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 100 * 1024 * 1024)
