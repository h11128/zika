"""
Unit tests for services/security.py
Tests input sanitization, CSP implementation, rate limiting, and XSS protection.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from services.security import (
    SecurityLevel, InputType, SecurityConfig, ValidationResult,
    InputSanitizer, ContentSecurityPolicy, RateLimiter, SecurityValidator,
    get_security_validator, validate_card_input, secure_html_content,
    check_user_rate_limit, get_security_status
)


class TestSecurityConfig:
    """Test security configuration."""
    
    def test_default_config(self):
        """Test default security configuration."""
        config = SecurityConfig()
        assert config.level == SecurityLevel.MODERATE
        assert config.max_input_length == 10000
        assert config.max_filename_length == 255
        assert config.enable_csp is True
        assert config.enable_rate_limiting is True
        assert config.enable_xss_protection is True
        assert 'div' in config.allowed_html_tags
        assert 'color' in config.allowed_css_properties
    
    def test_custom_config(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            level=SecurityLevel.STRICT,
            max_input_length=5000,
            enable_csp=False,
            rate_limit_requests_per_minute=50
        )
        assert config.level == SecurityLevel.STRICT
        assert config.max_input_length == 5000
        assert config.enable_csp is False
        assert config.rate_limit_requests_per_minute == 50


class TestValidationResult:
    """Test validation result functionality."""
    
    def test_validation_result_creation(self):
        """Test validation result creation."""
        result = ValidationResult(
            is_valid=True,
            sanitized_value="clean text",
            warnings=["Minor issue"],
            errors=[],
            original_length=10,
            sanitized_length=10
        )
        
        assert result.is_valid is True
        assert result.sanitized_value == "clean text"
        assert len(result.warnings) == 1
        assert len(result.errors) == 0
        assert result.original_length == 10
        assert result.sanitized_length == 10


class TestInputSanitizer:
    """Test input sanitization functionality."""
    
    def test_sanitizer_creation(self):
        """Test sanitizer creation."""
        sanitizer = InputSanitizer()
        assert sanitizer.config.level == SecurityLevel.MODERATE
        assert len(sanitizer._xss_patterns) > 0
    
    def test_hanzi_validation_valid(self):
        """Test valid hanzi input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("你好世界", InputType.HANZI)
        
        assert result.is_valid is True
        assert result.sanitized_value == "你好世界"
        assert len(result.errors) == 0
    
    def test_hanzi_validation_with_invalid_chars(self):
        """Test hanzi input with invalid characters."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("你好<script>alert('xss')</script>世界", InputType.HANZI)
        
        assert result.is_valid is True
        assert "<script>" not in result.sanitized_value
        assert "你好" in result.sanitized_value
        assert "世界" in result.sanitized_value
    
    def test_pinyin_validation_valid(self):
        """Test valid pinyin input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("nǐ hǎo shì jiè", InputType.PINYIN)
        
        assert result.is_valid is True
        assert result.sanitized_value == "nǐ hǎo shì jiè"
        assert len(result.errors) == 0
    
    def test_pinyin_validation_with_invalid_chars(self):
        """Test pinyin input with invalid characters."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("nǐ hǎo<script>alert('xss')</script>", InputType.PINYIN)
        
        assert result.is_valid is True
        assert "<script>" not in result.sanitized_value
        assert "nǐ hǎo" in result.sanitized_value
    
    def test_english_validation_valid(self):
        """Test valid English input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("Hello, world! How are you?", InputType.ENGLISH)
        
        assert result.is_valid is True
        assert result.sanitized_value == "Hello, world! How are you?"
        assert len(result.errors) == 0
    
    def test_english_validation_with_xss(self):
        """Test English input with XSS attempt."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("Hello<script>alert('xss')</script>world", InputType.ENGLISH)
        
        assert result.is_valid is True
        assert "<script>" not in result.sanitized_value
        assert "Hello" in result.sanitized_value
        assert "world" in result.sanitized_value
    
    def test_filename_validation_valid(self):
        """Test valid filename input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("my_document.pdf", InputType.FILENAME)
        
        assert result.is_valid is True
        assert result.sanitized_value == "my_document.pdf"
        assert len(result.errors) == 0
    
    def test_filename_validation_path_traversal(self):
        """Test filename with path traversal attempt."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("../../../etc/passwd", InputType.FILENAME)
        
        assert result.is_valid is True
        assert ".." not in result.sanitized_value
        assert "/" not in result.sanitized_value
        assert "etcpasswd" in result.sanitized_value
    
    def test_html_validation_with_xss(self):
        """Test HTML input with XSS attempts."""
        sanitizer = InputSanitizer()
        malicious_html = """
        <div>Safe content</div>
        <script>alert('xss')</script>
        <img src="x" onerror="alert('xss')">
        <iframe src="javascript:alert('xss')"></iframe>
        """
        
        result = sanitizer.validate_input(malicious_html, InputType.HTML_CONTENT)
        
        assert result.is_valid is True
        assert "<script>" not in result.sanitized_value
        assert "onerror=" not in result.sanitized_value
        assert "<iframe>" not in result.sanitized_value
        assert "Safe content" in result.sanitized_value
    
    def test_json_validation_valid(self):
        """Test valid JSON input."""
        sanitizer = InputSanitizer()
        json_data = '{"name": "test", "value": 123}'
        
        result = sanitizer.validate_input(json_data, InputType.JSON_DATA)
        
        assert result.is_valid is True
        assert '"name":"test"' in result.sanitized_value or '"name": "test"' in result.sanitized_value
    
    def test_json_validation_invalid(self):
        """Test invalid JSON input."""
        sanitizer = InputSanitizer()
        invalid_json = '{"name": "test", "value":}'
        
        result = sanitizer.validate_input(invalid_json, InputType.JSON_DATA)
        
        assert result.is_valid is True
        assert result.sanitized_value == "{}"  # Fallback to empty object
    
    def test_url_validation_valid(self):
        """Test valid URL input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("https://example.com/path", InputType.URL)
        
        assert result.is_valid is True
        assert result.sanitized_value == "https://example.com/path"
    
    def test_url_validation_invalid(self):
        """Test invalid URL input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("javascript:alert('xss')", InputType.URL)
        
        assert result.is_valid is True
        assert result.sanitized_value == ""  # Invalid URL becomes empty
    
    def test_css_validation_safe(self):
        """Test safe CSS input."""
        sanitizer = InputSanitizer()
        result = sanitizer.validate_input("color: red; font-size: 14px;", InputType.CSS_VALUE)
        
        assert result.is_valid is True
        assert "color: red" in result.sanitized_value
        assert "font-size: 14px" in result.sanitized_value
    
    def test_css_validation_dangerous(self):
        """Test dangerous CSS input."""
        sanitizer = InputSanitizer()
        dangerous_css = "color: red; expression(alert('xss')); javascript:alert('xss');"
        
        result = sanitizer.validate_input(dangerous_css, InputType.CSS_VALUE)
        
        assert result.is_valid is True
        assert "expression(" not in result.sanitized_value
        assert "javascript:" not in result.sanitized_value
        assert "color: red" in result.sanitized_value
    
    def test_input_length_validation(self):
        """Test input length validation."""
        config = SecurityConfig(max_input_length=10)
        sanitizer = InputSanitizer(config)
        
        long_input = "a" * 20
        result = sanitizer.validate_input(long_input, InputType.ENGLISH)
        
        assert result.is_valid is False
        assert len(result.sanitized_value) == 10
        assert len(result.errors) > 0
        assert "too long" in result.errors[0].lower()


class TestContentSecurityPolicy:
    """Test Content Security Policy functionality."""
    
    def test_csp_creation(self):
        """Test CSP creation."""
        csp = ContentSecurityPolicy()
        assert csp.config.enable_csp is True
    
    def test_csp_header_generation(self):
        """Test CSP header generation."""
        csp = ContentSecurityPolicy()
        header = csp.generate_csp_header()
        
        assert "default-src 'self'" in header
        assert "script-src 'self'" in header
        assert "object-src 'none'" in header
        assert "frame-ancestors 'none'" in header
    
    def test_csp_header_with_nonce(self):
        """Test CSP header with nonce."""
        csp = ContentSecurityPolicy()
        nonce = "test-nonce-123"
        header = csp.generate_csp_header(nonce)
        
        assert f"'nonce-{nonce}'" in header
        assert "script-src 'self'" in header
    
    def test_nonce_generation(self):
        """Test nonce generation."""
        csp = ContentSecurityPolicy()
        nonce1 = csp.generate_nonce()
        nonce2 = csp.generate_nonce()
        
        assert len(nonce1) > 0
        assert len(nonce2) > 0
        assert nonce1 != nonce2  # Should be unique
    
    def test_html_wrapping_with_csp(self):
        """Test HTML wrapping with CSP."""
        csp = ContentSecurityPolicy()
        html_content = "<div>Test content</div>"
        
        wrapped = csp.wrap_html_with_csp(html_content, "Test Title")
        
        assert "<!DOCTYPE html>" in wrapped
        assert "Content-Security-Policy" in wrapped
        assert "X-Content-Type-Options" in wrapped
        assert "X-Frame-Options" in wrapped
        assert "X-XSS-Protection" in wrapped
        assert "<div>Test content</div>" in wrapped
        assert "Test Title" in wrapped
    
    def test_html_wrapping_disabled(self):
        """Test HTML wrapping when CSP is disabled."""
        config = SecurityConfig(enable_csp=False)
        csp = ContentSecurityPolicy(config)
        html_content = "<div>Test content</div>"
        
        wrapped = csp.wrap_html_with_csp(html_content)
        
        assert wrapped == html_content  # Should return unchanged


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_creation(self):
        """Test rate limiter creation."""
        limiter = RateLimiter()
        assert limiter.config.enable_rate_limiting is True
        assert limiter.config.rate_limit_requests_per_minute == 100
    
    def test_rate_limiting_within_limit(self):
        """Test rate limiting within allowed limit."""
        config = SecurityConfig(rate_limit_requests_per_minute=5)
        limiter = RateLimiter(config)
        
        # Make requests within limit
        for i in range(5):
            assert not limiter.is_rate_limited("user1", "test_action")
    
    def test_rate_limiting_exceeds_limit(self):
        """Test rate limiting when limit is exceeded."""
        config = SecurityConfig(rate_limit_requests_per_minute=3)
        limiter = RateLimiter(config)
        
        # Make requests up to limit
        for i in range(3):
            assert not limiter.is_rate_limited("user1", "test_action")
        
        # Next request should be rate limited
        assert limiter.is_rate_limited("user1", "test_action")
    
    def test_rate_limiting_different_users(self):
        """Test rate limiting for different users."""
        config = SecurityConfig(rate_limit_requests_per_minute=2)
        limiter = RateLimiter(config)
        
        # User1 makes requests
        assert not limiter.is_rate_limited("user1", "test_action")
        assert not limiter.is_rate_limited("user1", "test_action")
        assert limiter.is_rate_limited("user1", "test_action")  # Exceeded
        
        # User2 should not be affected
        assert not limiter.is_rate_limited("user2", "test_action")
        assert not limiter.is_rate_limited("user2", "test_action")
    
    def test_rate_limiting_different_actions(self):
        """Test rate limiting for different actions."""
        config = SecurityConfig(rate_limit_requests_per_minute=2)
        limiter = RateLimiter(config)
        
        # Action1 reaches limit
        assert not limiter.is_rate_limited("user1", "action1")
        assert not limiter.is_rate_limited("user1", "action1")
        assert limiter.is_rate_limited("user1", "action1")  # Exceeded
        
        # Action2 should not be affected
        assert not limiter.is_rate_limited("user1", "action2")
        assert not limiter.is_rate_limited("user1", "action2")
    
    def test_rate_limit_status(self):
        """Test rate limit status reporting."""
        config = SecurityConfig(rate_limit_requests_per_minute=5)
        limiter = RateLimiter(config)
        
        # Make some requests
        limiter.is_rate_limited("user1", "test_action")
        limiter.is_rate_limited("user1", "test_action")
        
        status = limiter.get_rate_limit_status("user1", "test_action")
        
        assert status['requests_in_window'] == 2
        assert status['limit'] == 5
        assert status['remaining'] == 3
        assert 'reset_time' in status
    
    def test_rate_limiting_disabled(self):
        """Test rate limiting when disabled."""
        config = SecurityConfig(enable_rate_limiting=False)
        limiter = RateLimiter(config)
        
        # Should never be rate limited when disabled
        for i in range(1000):
            assert not limiter.is_rate_limited("user1", "test_action")


class TestSecurityValidator:
    """Test main security validator functionality."""
    
    def test_validator_creation(self):
        """Test security validator creation."""
        validator = SecurityValidator()
        assert validator.config.level == SecurityLevel.MODERATE
        assert validator.sanitizer is not None
        assert validator.csp is not None
        assert validator.rate_limiter is not None
    
    def test_card_data_validation_valid(self):
        """Test valid card data validation."""
        validator = SecurityValidator()
        card_data = {
            'hanzi': '你好',
            'pinyin': 'nǐ hǎo',
            'english': 'hello'
        }
        
        results = validator.validate_card_data(card_data)
        
        assert 'hanzi' in results
        assert 'pinyin' in results
        assert 'english' in results
        assert all(result.is_valid for result in results.values())
    
    def test_card_data_validation_with_xss(self):
        """Test card data validation with XSS attempts."""
        validator = SecurityValidator()
        card_data = {
            'hanzi': '你好<script>alert("xss")</script>',
            'pinyin': 'nǐ hǎo<script>alert("xss")</script>',
            'english': 'hello<script>alert("xss")</script>'
        }
        
        results = validator.validate_card_data(card_data)
        
        assert all(result.is_valid for result in results.values())
        assert all('<script>' not in result.sanitized_value for result in results.values())
        assert '你好' in results['hanzi'].sanitized_value
        assert 'nǐ hǎo' in results['pinyin'].sanitized_value
        assert 'hello' in results['english'].sanitized_value
    
    def test_secure_preview_html(self):
        """Test secure preview HTML generation."""
        validator = SecurityValidator()
        html_content = "<div>Safe content</div><script>alert('xss')</script>"
        
        secure_html = validator.secure_preview_html(html_content, "Test Preview")
        
        assert "<!DOCTYPE html>" in secure_html
        assert "Content-Security-Policy" in secure_html
        assert "Test Preview" in secure_html
        assert "<script>" not in secure_html
        assert "Safe content" in secure_html
    
    def test_rate_limit_checking(self):
        """Test rate limit checking."""
        config = SecurityConfig(rate_limit_requests_per_minute=2)
        validator = SecurityValidator(config)
        
        # Within limit
        assert not validator.check_rate_limit("user1", "test_action")
        assert not validator.check_rate_limit("user1", "test_action")
        
        # Exceeds limit
        assert validator.check_rate_limit("user1", "test_action")
    
    def test_security_posture_reporting(self):
        """Test security posture reporting."""
        validator = SecurityValidator()
        posture = validator.get_security_posture()
        
        assert 'security_level' in posture
        assert 'csp_enabled' in posture
        assert 'rate_limiting_enabled' in posture
        assert 'xss_protection_enabled' in posture
        assert 'browser_storage_limitations' in posture
        
        assert posture['security_level'] == SecurityLevel.MODERATE.value
    
    def test_security_events_logging(self):
        """Test security events logging."""
        validator = SecurityValidator()
        
        # Trigger some security events
        card_data = {'hanzi': '你好<script>alert("xss")</script>'}
        validator.validate_card_data(card_data)
        
        events = validator.get_security_events()
        assert len(events) > 0
        assert events[0]['type'] == 'input_validation'
        assert 'timestamp' in events[0]


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.security.get_security_validator')
    def test_validate_card_input_function(self, mock_get_validator):
        """Test validate card input convenience function."""
        mock_validator = MagicMock()
        mock_validator.validate_card_data.return_value = {'hanzi': ValidationResult(True, '你好')}
        mock_get_validator.return_value = mock_validator
        
        card_data = {'hanzi': '你好'}
        results = validate_card_input(card_data)
        
        assert 'hanzi' in results
        mock_validator.validate_card_data.assert_called_once_with(card_data)
    
    @patch('services.security.get_security_validator')
    def test_secure_html_content_function(self, mock_get_validator):
        """Test secure HTML content convenience function."""
        mock_validator = MagicMock()
        mock_validator.secure_preview_html.return_value = "<html>secure</html>"
        mock_get_validator.return_value = mock_validator
        
        html_content = "<div>test</div>"
        secure_html = secure_html_content(html_content, "Test")
        
        assert secure_html == "<html>secure</html>"
        mock_validator.secure_preview_html.assert_called_once_with(html_content, "Test")
    
    @patch('services.security.get_security_validator')
    def test_check_user_rate_limit_function(self, mock_get_validator):
        """Test check user rate limit convenience function."""
        mock_validator = MagicMock()
        mock_validator.check_rate_limit.return_value = False
        mock_get_validator.return_value = mock_validator
        
        is_limited = check_user_rate_limit("user123", "test_action")
        
        assert is_limited is False
        mock_validator.check_rate_limit.assert_called_once_with("user123", "test_action")


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_security_workflow(self):
        """Test complete security validation workflow."""
        validator = SecurityValidator()
        
        # Validate card data with mixed content
        card_data = {
            'hanzi': '你好世界<script>alert("xss")</script>',
            'pinyin': 'nǐ hǎo shì jiè',
            'english': 'Hello world!'
        }
        
        # Validate inputs
        validation_results = validator.validate_card_data(card_data)
        
        # All should be valid after sanitization
        assert all(result.is_valid for result in validation_results.values())
        
        # XSS should be removed
        assert '<script>' not in validation_results['hanzi'].sanitized_value
        assert '你好世界' in validation_results['hanzi'].sanitized_value
        
        # Create HTML content
        html_content = f"""
        <div class="card">
            <div class="hanzi">{validation_results['hanzi'].sanitized_value}</div>
            <div class="pinyin">{validation_results['pinyin'].sanitized_value}</div>
            <div class="english">{validation_results['english'].sanitized_value}</div>
        </div>
        """
        
        # Secure the HTML
        secure_html = validator.secure_preview_html(html_content, "Card Preview")
        
        # Verify security features
        assert "Content-Security-Policy" in secure_html
        assert "X-XSS-Protection" in secure_html
        assert "你好世界" in secure_html
        assert "<script>" not in secure_html
        
        # Check security posture
        posture = validator.get_security_posture()
        assert posture['csp_enabled'] is True
        assert posture['xss_protection_enabled'] is True
        
        # Verify events were logged
        events = validator.get_security_events()
        assert len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__])
