"""
Security tests for XSS protection and input validation.
Tests HTML sanitization, script injection prevention, and content security policy.
"""

import pytest
import re
import html
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class HTMLSanitizer:
    """HTML sanitizer for XSS protection."""
    
    # Allowed HTML tags for preview content
    ALLOWED_TAGS = {
        'div', 'span', 'p', 'br', 'strong', 'em', 'b', 'i', 'u',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li'
    }
    
    # Allowed attributes
    ALLOWED_ATTRIBUTES = {
        'class', 'id', 'style', 'data-card-id', 'data-page'
    }
    
    @staticmethod
    def sanitize_html(html_content):
        """Sanitize HTML content to prevent XSS."""
        if not html_content:
            return ""
        
        # Remove script tags and their content
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove javascript: URLs and their content
        html_content = re.sub(r'javascript:[^"\'>\s]*', '', html_content, flags=re.IGNORECASE)

        # Remove on* event handlers
        html_content = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
        
        # Remove dangerous tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'textarea', 'button']
        for tag in dangerous_tags:
            pattern = f'<{tag}[^>]*>.*?</{tag}>'
            html_content = re.sub(pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # Also remove self-closing versions
            pattern = f'<{tag}[^>]*/?>'
            html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE)
        
        return html_content
    
    @staticmethod
    def escape_user_input(user_input):
        """Escape user input for safe HTML inclusion."""
        if not user_input:
            return ""
        
        # HTML escape
        escaped = html.escape(str(user_input), quote=True)
        
        # Additional escaping for potential XSS vectors
        escaped = escaped.replace('&lt;script', '&amp;lt;script')
        escaped = escaped.replace('javascript:', 'javascript&#58;')
        
        return escaped
    
    @staticmethod
    def validate_css_property(css_value):
        """Validate CSS property value for safety."""
        if not css_value:
            return ""
        
        # Remove potentially dangerous CSS
        dangerous_patterns = [
            r'expression\s*\(',
            r'javascript:',
            r'@import',
            r'url\s*\(\s*["\']?\s*javascript:',
            r'behavior\s*:',
            r'-moz-binding',
        ]
        
        for pattern in dangerous_patterns:
            css_value = re.sub(pattern, '', css_value, flags=re.IGNORECASE)
        
        return css_value


class TestXSSProtection:
    """Test XSS protection mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sanitizer = HTMLSanitizer()
    
    def test_script_tag_removal(self):
        """Test that script tags are removed."""
        malicious_html = '<div>Hello <script>alert("XSS")</script> World</div>'
        sanitized = self.sanitizer.sanitize_html(malicious_html)
        
        assert '<script>' not in sanitized
        assert 'alert(' not in sanitized
        assert 'Hello  World' in sanitized or 'Hello World' in sanitized
    
    def test_javascript_url_removal(self):
        """Test that javascript: URLs are removed."""
        malicious_html = '<a href="javascript:alert(\'XSS\')">Click me</a>'
        sanitized = self.sanitizer.sanitize_html(malicious_html)
        
        assert 'javascript:' not in sanitized
        assert 'alert(' not in sanitized
    
    def test_event_handler_removal(self):
        """Test that event handlers are removed."""
        test_cases = [
            '<div onclick="alert(\'XSS\')">Click</div>',
            '<img src="x" onerror="alert(\'XSS\')">',
            '<body onload="maliciousFunction()">',
            '<input onchange="stealData()">',
        ]
        
        for malicious_html in test_cases:
            sanitized = self.sanitizer.sanitize_html(malicious_html)
            
            # Check that no event handlers remain
            assert not re.search(r'\s*on\w+\s*=', sanitized, re.IGNORECASE)
            assert 'alert(' not in sanitized
    
    def test_dangerous_tag_removal(self):
        """Test that dangerous tags are removed."""
        dangerous_tags = [
            '<iframe src="http://evil.com"></iframe>',
            '<object data="malicious.swf"></object>',
            '<embed src="evil.swf">',
            '<form action="http://evil.com"><input type="password"></form>',
        ]
        
        for malicious_html in dangerous_tags:
            sanitized = self.sanitizer.sanitize_html(malicious_html)
            
            # Check that dangerous tags are removed
            assert '<iframe' not in sanitized
            assert '<object' not in sanitized
            assert '<embed' not in sanitized
            assert '<form' not in sanitized
            assert '<input' not in sanitized
    
    def test_user_input_escaping(self):
        """Test user input escaping."""
        test_cases = [
            ('<script>alert("XSS")</script>', '&lt;script&gt;alert("XSS")&lt;/script&gt;'),
            ('javascript:alert(1)', 'javascript&#58;alert(1)'),
            ('<img src=x onerror=alert(1)>', '&lt;img src=x onerror=alert(1)&gt;'),
            ('"><script>alert(1)</script>', '"&gt;&lt;script&gt;alert(1)&lt;/script&gt;'),
        ]
        
        for malicious_input, expected_pattern in test_cases:
            escaped = self.sanitizer.escape_user_input(malicious_input)
            
            # Verify dangerous content is escaped
            assert '<script>' not in escaped
            assert 'javascript:' not in escaped
            # Check that HTML tags are escaped (< becomes &lt;)
            if '<' in malicious_input:
                assert '&lt;' in escaped or '&gt;' in escaped
    
    def test_css_injection_protection(self):
        """Test CSS injection protection."""
        malicious_css_values = [
            'expression(alert("XSS"))',
            'javascript:alert(1)',
            'url("javascript:alert(1)")',
            '@import "http://evil.com/style.css"',
            'behavior: url(evil.htc)',
            '-moz-binding: url(evil.xml)',
        ]
        
        for malicious_css in malicious_css_values:
            sanitized = self.sanitizer.validate_css_property(malicious_css)
            
            # Verify dangerous CSS is removed
            assert 'expression(' not in sanitized
            assert 'javascript:' not in sanitized
            assert '@import' not in sanitized
            assert 'behavior:' not in sanitized
            assert '-moz-binding' not in sanitized
    
    def test_nested_xss_attempts(self):
        """Test nested XSS attempts."""
        nested_xss = [
            '<scr<script>ipt>alert("XSS")</scr</script>ipt>',
            '<div><script>alert(1)</script><span>text</span></div>',
            '<<script>script>alert(1)<</script>/script>',
        ]
        
        for malicious_html in nested_xss:
            sanitized = self.sanitizer.sanitize_html(malicious_html)
            
            # Verify no script content remains
            assert '<script>' not in sanitized
            assert 'alert(' not in sanitized
    
    def test_allowed_content_preservation(self):
        """Test that allowed content is preserved."""
        safe_html = '''
        <div class="card" id="card-1" style="color: blue;">
            <h2>Card Title</h2>
            <p>This is <strong>safe</strong> content with <em>emphasis</em>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </div>
        '''
        
        sanitized = self.sanitizer.sanitize_html(safe_html)
        
        # Verify safe content is preserved
        assert '<div class="card"' in sanitized
        assert '<h2>' in sanitized
        assert '<strong>' in sanitized
        assert '<em>' in sanitized
        assert '<ul>' in sanitized
        assert '<li>' in sanitized
        assert 'style="color: blue;"' in sanitized


class TestInputValidation:
    """Test input validation mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sanitizer = HTMLSanitizer()
    
    def test_chinese_text_validation(self):
        """Test validation of Chinese text input."""
        valid_inputs = [
            '你好世界',
            '学习中文很有趣',
            '这是一个测试',
            '中文 English 混合',
        ]
        
        invalid_inputs = [
            '<script>alert("XSS")</script>',
            'javascript:alert(1)',
            '"><img src=x onerror=alert(1)>',
        ]
        
        for valid_input in valid_inputs:
            escaped = self.sanitizer.escape_user_input(valid_input)
            # Valid Chinese should be preserved (though escaped)
            assert len(escaped) > 0
        
        for invalid_input in invalid_inputs:
            escaped = self.sanitizer.escape_user_input(invalid_input)
            # Dangerous content should be escaped
            assert '<script>' not in escaped
            assert 'javascript:' not in escaped
            # Check that HTML tags are escaped
            if '<' in invalid_input:
                assert '&lt;' in escaped or '&gt;' in escaped
    
    def test_pinyin_validation(self):
        """Test validation of pinyin input."""
        valid_pinyin = [
            'nǐ hǎo',
            'xué xí',
            'zhōng wén',
            'cèshì',
        ]
        
        malicious_pinyin = [
            'nǐ<script>alert(1)</script>hǎo',
            'javascript:alert(1)',
            'xué" onerror="alert(1)" xí',
        ]
        
        for valid in valid_pinyin:
            escaped = self.sanitizer.escape_user_input(valid)
            # Should preserve pinyin characters
            assert len(escaped) > 0
        
        for malicious in malicious_pinyin:
            escaped = self.sanitizer.escape_user_input(malicious)
            # Should escape dangerous content
            assert '<script>' not in escaped
            assert 'javascript:' not in escaped
            # Check that HTML tags are escaped
            if '<' in malicious:
                assert '&lt;' in escaped or '&gt;' in escaped
    
    def test_file_upload_validation(self):
        """Test file upload validation."""
        # Mock file validation
        def validate_file_type(filename):
            allowed_extensions = {'.csv', '.txt'}
            dangerous_extensions = {'.exe', '.js', '.html', '.php', '.asp'}
            
            ext = os.path.splitext(filename.lower())[1]
            
            if ext in dangerous_extensions:
                return False, "Dangerous file type"
            elif ext in allowed_extensions:
                return True, "Valid file type"
            else:
                return False, "Unsupported file type"
        
        # Test valid files
        valid_files = ['data.csv', 'input.txt', 'cards.CSV']
        for filename in valid_files:
            is_valid, message = validate_file_type(filename)
            assert is_valid, f"Valid file {filename} rejected: {message}"
        
        # Test dangerous files
        dangerous_files = ['malware.exe', 'script.js', 'page.html', 'backdoor.php']
        for filename in dangerous_files:
            is_valid, message = validate_file_type(filename)
            assert not is_valid, f"Dangerous file {filename} accepted"
    
    def test_url_validation(self):
        """Test URL validation for external resources."""
        def validate_url(url):
            if not url:
                return False, "Empty URL"
            
            # Check for dangerous protocols
            dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
            for protocol in dangerous_protocols:
                if url.lower().startswith(protocol):
                    return False, f"Dangerous protocol: {protocol}"
            
            # Only allow http/https
            if not (url.startswith('http://') or url.startswith('https://')):
                return False, "Only HTTP/HTTPS allowed"
            
            return True, "Valid URL"
        
        # Test valid URLs
        valid_urls = [
            'https://example.com',
            'http://localhost:8080',
            'https://fonts.googleapis.com/css',
        ]
        
        for url in valid_urls:
            is_valid, message = validate_url(url)
            assert is_valid, f"Valid URL {url} rejected: {message}"
        
        # Test dangerous URLs
        dangerous_urls = [
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            'vbscript:msgbox(1)',
            'file:///etc/passwd',
        ]
        
        for url in dangerous_urls:
            is_valid, message = validate_url(url)
            assert not is_valid, f"Dangerous URL {url} accepted"


class TestContentSecurityPolicy:
    """Test Content Security Policy implementation."""
    
    def test_csp_header_generation(self):
        """Test CSP header generation."""
        def generate_csp_header():
            """Generate Content Security Policy header."""
            directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline'",  # Streamlit requires unsafe-inline
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
            
            return "; ".join(directives)
        
        csp_header = generate_csp_header()
        
        # Verify CSP contains essential directives
        assert "default-src 'self'" in csp_header
        assert "script-src" in csp_header
        assert "style-src" in csp_header
        assert "frame-ancestors 'none'" in csp_header
        assert "base-uri 'self'" in csp_header
    
    def test_csp_violation_detection(self):
        """Test CSP violation detection."""
        def check_csp_violation(content):
            """Check if content would violate CSP."""
            violations = []
            
            # Check for inline scripts
            if re.search(r'<script[^>]*>(?![\s]*</script>)', content, re.IGNORECASE):
                violations.append("Inline script detected")
            
            # Check for javascript: URLs
            if re.search(r'javascript:', content, re.IGNORECASE):
                violations.append("JavaScript URL detected")
            
            # Check for external resources from non-whitelisted domains
            external_resources = re.findall(r'src=["\']https?://([^/"\'>]+)', content, re.IGNORECASE)
            allowed_domains = {'fonts.googleapis.com', 'fonts.gstatic.com'}
            
            for domain in external_resources:
                if domain not in allowed_domains:
                    violations.append(f"External resource from non-whitelisted domain: {domain}")
            
            return violations
        
        # Test content that should pass CSP
        safe_content = '''
        <div class="card">
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==">
            <link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet">
        </div>
        '''
        
        violations = check_csp_violation(safe_content)
        assert len(violations) == 0, f"Safe content triggered CSP violations: {violations}"
        
        # Test content that should violate CSP
        unsafe_content = '''
        <div>
            <script>alert("XSS")</script>
            <a href="javascript:alert(1)">Click</a>
            <img src="https://evil.com/tracker.gif">
        </div>
        '''
        
        violations = check_csp_violation(unsafe_content)
        assert len(violations) > 0, "Unsafe content did not trigger CSP violations"


if __name__ == "__main__":
    pytest.main([__file__])
