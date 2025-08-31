"""
Security Hardening Module.
Implements input sanitization, CSP for preview HTML, XSS protection, and security validation.
"""

import re
import html
import json
import hashlib
import time
import threading
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque

from core.feature_flags import get_feature_flag


class SecurityLevel(Enum):
    """Security validation levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


class InputType(Enum):
    """Types of input for validation."""
    HANZI = "hanzi"
    PINYIN = "pinyin"
    ENGLISH = "english"
    FILENAME = "filename"
    HTML_CONTENT = "html_content"
    JSON_DATA = "json_data"
    URL = "url"
    CSS_VALUE = "css_value"


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    level: SecurityLevel = SecurityLevel.MODERATE
    max_input_length: int = 10000
    max_filename_length: int = 255
    max_html_size_bytes: int = 1024 * 1024  # 1MB
    enable_csp: bool = True
    enable_rate_limiting: bool = True
    rate_limit_requests_per_minute: int = 100
    enable_xss_protection: bool = True
    allowed_html_tags: Set[str] = field(default_factory=lambda: {
        'div', 'span', 'p', 'br', 'strong', 'em', 'u', 'i', 'b',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
        'table', 'tr', 'td', 'th', 'thead', 'tbody'
    })
    allowed_css_properties: Set[str] = field(default_factory=lambda: {
        'color', 'background-color', 'font-size', 'font-family', 'font-weight',
        'text-align', 'margin_cm', 'padding', 'border', 'width_cm', 'height_cm',
        'display', 'position', 'top', 'left', 'right', 'bottom'
    })


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized_value: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    original_length: int = 0
    sanitized_length: int = 0


class InputSanitizer:
    """Input sanitization and validation."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        
        # Compile regex patterns for performance
        self._hanzi_pattern = re.compile(r'^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\s\d\w\-.,!?()（）。，！？]*$')
        self._pinyin_pattern = re.compile(r'^[a-zA-ZāáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙÜǕǗǙǛ\s\d\-.,!?()]*$')
        self._english_pattern = re.compile(r'^[a-zA-Z\s\d\-.,!?()\'\"]*$')
        self._filename_pattern = re.compile(r'^[a-zA-Z0-9\-_.\s()]+$')
        self._url_pattern = re.compile(r'^https?://[^\s<>"{}|\\^`\[\]]*$')
        
        # XSS patterns to detect and remove
        self._xss_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),
            re.compile(r'<iframe[^>]*>', re.IGNORECASE),
            re.compile(r'<object[^>]*>', re.IGNORECASE),
            re.compile(r'<embed[^>]*>', re.IGNORECASE),
            re.compile(r'<link[^>]*>', re.IGNORECASE),
            re.compile(r'<meta[^>]*>', re.IGNORECASE),
            re.compile(r'<style[^>]*>.*?</style>', re.IGNORECASE | re.DOTALL),
        ]
    
    def validate_input(self, value: str, input_type: InputType) -> ValidationResult:
        """Validate and sanitize input based on type."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                errors=["Input must be a string"]
            )
        
        original_length = len(value)
        warnings = []
        errors = []
        
        # Length validation
        max_length = self._get_max_length(input_type)
        if original_length > max_length:
            errors.append(f"Input too long: {original_length} > {max_length}")
            value = value[:max_length]
            warnings.append(f"Input truncated to {max_length} characters")
        
        # Type-specific validation and sanitization
        if input_type == InputType.HANZI:
            sanitized = self._sanitize_hanzi(value)
        elif input_type == InputType.PINYIN:
            sanitized = self._sanitize_pinyin(value)
        elif input_type == InputType.ENGLISH:
            sanitized = self._sanitize_english(value)
        elif input_type == InputType.FILENAME:
            sanitized = self._sanitize_filename(value)
        elif input_type == InputType.HTML_CONTENT:
            sanitized = self._sanitize_html(value)
        elif input_type == InputType.JSON_DATA:
            sanitized = self._sanitize_json(value)
        elif input_type == InputType.URL:
            sanitized = self._sanitize_url(value)
        elif input_type == InputType.CSS_VALUE:
            sanitized = self._sanitize_css(value)
        else:
            sanitized = self._sanitize_generic(value)
        
        # Check if sanitization changed the input
        if sanitized != value:
            warnings.append("Input was sanitized for security")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized,
            warnings=warnings,
            errors=errors,
            original_length=original_length,
            sanitized_length=len(sanitized)
        )
    
    def _get_max_length(self, input_type: InputType) -> int:
        """Get maximum length for input type."""
        if input_type == InputType.FILENAME:
            return self.config.max_filename_length
        elif input_type == InputType.HTML_CONTENT:
            return self.config.max_html_size_bytes
        else:
            return self.config.max_input_length
    
    def _sanitize_hanzi(self, value: str) -> str:
        """Sanitize Chinese characters input."""
        # Remove any HTML/script content
        sanitized = self._remove_xss_patterns(value)
        
        # Validate character set
        if not self._hanzi_pattern.match(sanitized):
            # Remove invalid characters
            sanitized = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\s\d\w\-.,!?()（）。，！？]', '', sanitized)
        
        return sanitized.strip()
    
    def _sanitize_pinyin(self, value: str) -> str:
        """Sanitize pinyin input."""
        # Remove any HTML/script content
        sanitized = self._remove_xss_patterns(value)
        
        # Validate character set
        if not self._pinyin_pattern.match(sanitized):
            # Remove invalid characters
            sanitized = re.sub(r'[^a-zA-ZāáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙÜǕǗǙǛ\s\d\-.,!?()]', '', sanitized)
        
        return sanitized.strip()
    
    def _sanitize_english(self, value: str) -> str:
        """Sanitize English text input."""
        # Remove any HTML/script content
        sanitized = self._remove_xss_patterns(value)
        
        # Validate character set
        if not self._english_pattern.match(sanitized):
            # Remove invalid characters
            sanitized = re.sub(r'[^a-zA-Z\s\d\-.,!?()\'\"]', '', sanitized)
        
        return sanitized.strip()
    
    def _sanitize_filename(self, value: str) -> str:
        """Sanitize filename input."""
        # Remove any HTML/script content
        sanitized = self._remove_xss_patterns(value)
        
        # Remove path traversal attempts
        sanitized = sanitized.replace('..', '').replace('/', '').replace('\\', '')
        
        # Validate character set
        if not self._filename_pattern.match(sanitized):
            # Remove invalid characters
            sanitized = re.sub(r'[^a-zA-Z0-9\-_.\s()]', '', sanitized)
        
        return sanitized.strip()
    
    def _sanitize_html(self, value: str) -> str:
        """Sanitize HTML content."""
        # Remove XSS patterns
        sanitized = self._remove_xss_patterns(value)
        
        # HTML escape for safety
        sanitized = html.escape(sanitized, quote=True)
        
        return sanitized
    
    def _sanitize_json(self, value: str) -> str:
        """Sanitize JSON data."""
        try:
            # Parse and re-serialize to ensure valid JSON
            parsed = json.loads(value)
            sanitized = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
            return sanitized
        except (json.JSONDecodeError, TypeError):
            # Return empty JSON object if invalid
            return "{}"
    
    def _sanitize_url(self, value: str) -> str:
        """Sanitize URL input."""
        # Remove any HTML/script content
        sanitized = self._remove_xss_patterns(value)
        
        # Validate URL pattern
        if not self._url_pattern.match(sanitized):
            return ""  # Invalid URL
        
        return sanitized.strip()
    
    def _sanitize_css(self, value: str) -> str:
        """Sanitize CSS value."""
        # Remove any script content
        sanitized = self._remove_xss_patterns(value)
        
        # Remove potentially dangerous CSS
        sanitized = re.sub(r'expression\s*\(', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'@import', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def _sanitize_generic(self, value: str) -> str:
        """Generic sanitization for unknown input types."""
        # Remove XSS patterns and HTML escape
        sanitized = self._remove_xss_patterns(value)
        sanitized = html.escape(sanitized, quote=True)
        return sanitized.strip()
    
    def _remove_xss_patterns(self, value: str) -> str:
        """Remove known XSS patterns."""
        sanitized = value
        for pattern in self._xss_patterns:
            sanitized = pattern.sub('', sanitized)
        return sanitized


class ContentSecurityPolicy:
    """Content Security Policy implementation for preview HTML."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
    
    def generate_csp_header(self, nonce: Optional[str] = None) -> str:
        """Generate CSP header for preview HTML."""
        if not self.config.enable_csp:
            return ""
        
        directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for preview
            "img-src 'self' data:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ]
        
        if nonce:
            # Add nonce to script-src if provided
            directives[1] = f"script-src 'self' 'nonce-{nonce}'"
        
        return "; ".join(directives)
    
    def generate_nonce(self) -> str:
        """Generate cryptographic nonce for CSP."""
        import secrets
        return secrets.token_urlsafe(16)
    
    def wrap_html_with_csp(self, html_content: str, title: str = "Preview") -> str:
        """Wrap HTML content with CSP headers."""
        if not self.config.enable_csp:
            return html_content
        
        nonce = self.generate_nonce()
        csp_header = self.generate_csp_header(nonce)
        
        # Create secure HTML wrapper
        secure_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width_cm=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="{csp_header}">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <meta http-equiv="X-XSS-Protection" content="1; mode=block">
    <title>{html.escape(title)}</title>
</head>
<body>
{html_content}
</body>
</html>"""
        
        return secure_html


class RateLimiter:
    """Rate limiting for API calls and user actions."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._request_counts: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()
    
    def is_rate_limited(self, identifier: str, action: str = "default") -> bool:
        """Check if identifier is rate limited for action."""
        if not self.config.enable_rate_limiting:
            return False
        
        key = f"{identifier}:{action}"
        current_time = time.time()
        window_start = current_time - 60.0  # 1 minute window
        
        with self._lock:
            # Clean old requests
            request_times = self._request_counts[key]
            while request_times and request_times[0] < window_start:
                request_times.popleft()
            
            # Check if limit exceeded
            if len(request_times) >= self.config.rate_limit_requests_per_minute:
                return True
            
            # Record this request
            request_times.append(current_time)
            return False
    
    def get_rate_limit_status(self, identifier: str, action: str = "default") -> Dict[str, Any]:
        """Get rate limit status for identifier."""
        key = f"{identifier}:{action}"
        current_time = time.time()
        window_start = current_time - 60.0
        
        with self._lock:
            request_times = self._request_counts[key]
            
            # Count recent requests
            recent_requests = sum(1 for t in request_times if t >= window_start)
            
            return {
                'requests_in_window': recent_requests,
                'limit': self.config.rate_limit_requests_per_minute,
                'remaining': max(0, self.config.rate_limit_requests_per_minute - recent_requests),
                'reset_time': window_start + 60.0
            }


class SecurityValidator:
    """Main security validation and hardening service."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.sanitizer = InputSanitizer(config)
        self.csp = ContentSecurityPolicy(config)
        self.rate_limiter = RateLimiter(config)
        
        # Security event logging
        self._security_events: List[Dict[str, Any]] = []
        self._max_events = 1000
    
    def validate_card_data(self, card_data: Dict[str, str]) -> Dict[str, ValidationResult]:
        """Validate and sanitize card data."""
        results = {}
        
        # Validate each field
        if 'hanzi' in card_data:
            results['hanzi'] = self.sanitizer.validate_input(card_data['hanzi'], InputType.HANZI)
        
        if 'pinyin' in card_data:
            results['pinyin'] = self.sanitizer.validate_input(card_data['pinyin'], InputType.PINYIN)
        
        if 'english' in card_data:
            results['english'] = self.sanitizer.validate_input(card_data['english'], InputType.ENGLISH)
        
        # Log security events
        for field, result in results.items():
            if not result.is_valid or result.warnings:
                self._log_security_event('input_validation', {
                    'field': field,
                    'valid': result.is_valid,
                    'warnings': result.warnings,
                    'errors': result.errors
                })
        
        return results
    
    def secure_preview_html(self, html_content: str, title: str = "Preview") -> str:
        """Secure preview HTML with CSP and sanitization."""
        # Sanitize HTML content
        validation_result = self.sanitizer.validate_input(html_content, InputType.HTML_CONTENT)
        sanitized_html = validation_result.sanitized_value
        
        # Wrap with CSP
        secure_html = self.csp.wrap_html_with_csp(sanitized_html, title)
        
        # Log if content was modified
        if not validation_result.is_valid or validation_result.warnings:
            self._log_security_event('html_sanitization', {
                'original_length': validation_result.original_length,
                'sanitized_length': validation_result.sanitized_length,
                'warnings': validation_result.warnings
            })
        
        return secure_html
    
    def check_rate_limit(self, user_id: str, action: str = "default") -> bool:
        """Check if user action is rate limited."""
        is_limited = self.rate_limiter.is_rate_limited(user_id, action)
        
        if is_limited:
            self._log_security_event('rate_limit_exceeded', {
                'user_id': user_id,
                'action': action,
                'status': self.rate_limiter.get_rate_limit_status(user_id, action)
            })
        
        return is_limited
    
    def get_security_posture(self) -> Dict[str, Any]:
        """Get current security posture and configuration."""
        return {
            'security_level': self.config.level.value,
            'csp_enabled': self.config.enable_csp,
            'rate_limiting_enabled': self.config.enable_rate_limiting,
            'xss_protection_enabled': self.config.enable_xss_protection,
            'max_input_length': self.config.max_input_length,
            'rate_limit_per_minute': self.config.rate_limit_requests_per_minute,
            'recent_security_events': len(self._security_events),
            'browser_storage_limitations': {
                'localStorage_available': True,  # Assume available, would check in browser
                'storage_quota_limited': True,
                'cross_origin_isolated': False,
                'secure_context_required': True
            }
        }
    
    def get_security_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events."""
        return self._security_events[-limit:]
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security event."""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details
        }
        
        self._security_events.append(event)
        
        # Limit event history
        if len(self._security_events) > self._max_events:
            self._security_events = self._security_events[-self._max_events:]
        
        # Log to standard logging
        logging.info(f"Security event: {event_type}", extra={'security_event': event})


# Global security validator
_security_validator: Optional[SecurityValidator] = None


def get_security_validator() -> SecurityValidator:
    """Get global security validator instance."""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator()
    return _security_validator


# Convenience functions
def validate_card_input(card_data: Dict[str, str]) -> Dict[str, ValidationResult]:
    """Validate card input data."""
    return get_security_validator().validate_card_data(card_data)


def secure_html_content(html_content: str, title: str = "Preview") -> str:
    """Secure HTML content with CSP and sanitization."""
    return get_security_validator().secure_preview_html(html_content, title)


def check_user_rate_limit(user_id: str, action: str = "default") -> bool:
    """Check if user action is rate limited."""
    return get_security_validator().check_rate_limit(user_id, action)


def get_security_status() -> Dict[str, Any]:
    """Get current security status."""
    return get_security_validator().get_security_posture()
