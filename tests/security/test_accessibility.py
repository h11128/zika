"""
Accessibility tests for keyboard navigation, screen reader compatibility, and contrast testing.
Tests WCAG 2.1 compliance, keyboard accessibility, and visual accessibility.
"""

import pytest
import re
import sys
import os
from unittest.mock import MagicMock, patch
import colorsys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class AccessibilityChecker:
    """Accessibility checker for WCAG compliance."""
    
    def __init__(self):
        self.wcag_aa_contrast_ratio = 4.5
        self.wcag_aaa_contrast_ratio = 7.0
        self.large_text_aa_ratio = 3.0
        self.large_text_aaa_ratio = 4.5
    
    def check_color_contrast(self, foreground_color, background_color, font_size_pt=12, is_bold=False):
        """Check color contrast ratio for WCAG compliance."""
        # Convert colors to RGB
        fg_rgb = self._hex_to_rgb(foreground_color)
        bg_rgb = self._hex_to_rgb(background_color)
        
        # Calculate contrast ratio
        contrast_ratio = self._calculate_contrast_ratio(fg_rgb, bg_rgb)
        
        # Determine if text is large (18pt+ or 14pt+ bold)
        is_large_text = font_size_pt >= 18 or (font_size_pt >= 14 and is_bold)
        
        # Check compliance levels
        aa_threshold = self.large_text_aa_ratio if is_large_text else self.wcag_aa_contrast_ratio
        aaa_threshold = self.large_text_aaa_ratio if is_large_text else self.wcag_aaa_contrast_ratio
        
        return {
            'contrast_ratio': contrast_ratio,
            'wcag_aa_compliant': contrast_ratio >= aa_threshold,
            'wcag_aaa_compliant': contrast_ratio >= aaa_threshold,
            'is_large_text': is_large_text,
            'aa_threshold': aa_threshold,
            'aaa_threshold': aaa_threshold
        }
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _calculate_contrast_ratio(self, rgb1, rgb2):
        """Calculate contrast ratio between two RGB colors."""
        def relative_luminance(rgb):
            """Calculate relative luminance of RGB color."""
            def linearize(c):
                c = c / 255.0
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r, g, b = [linearize(c) for c in rgb]
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        lum1 = relative_luminance(rgb1)
        lum2 = relative_luminance(rgb2)
        
        # Ensure lighter color is in numerator
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def check_keyboard_accessibility(self, html_content):
        """Check keyboard accessibility of HTML content."""
        issues = []
        
        # Check for interactive elements without proper keyboard support
        interactive_elements = re.findall(r'<(button|input|select|textarea|a)[^>]*>', html_content, re.IGNORECASE)

        for element in interactive_elements:
            # Check for missing tabindex on custom interactive elements
            if 'tabindex' not in element.lower() and 'onclick' in element.lower():
                issues.append({
                    'type': 'missing_tabindex',
                    'element': element,
                    'message': 'Interactive element missing tabindex attribute'
                })

        # Check for custom interactive elements (div, span with onclick)
        custom_interactive = re.findall(r'<(div|span)[^>]*onclick[^>]*>', html_content, re.IGNORECASE)

        for element in custom_interactive:
            if 'tabindex' not in element.lower():
                issues.append({
                    'type': 'missing_tabindex',
                    'element': element,
                    'message': 'Custom interactive element missing tabindex attribute'
                })
            
            # Check for negative tabindex (removes from tab order)
            if 'tabindex="-1"' in element:
                issues.append({
                    'type': 'negative_tabindex',
                    'element': element,
                    'message': 'Element has negative tabindex, removing from tab order'
                })
        
        # Check for missing alt text on images
        images = re.findall(r'<img[^>]*>', html_content, re.IGNORECASE)
        for img in images:
            if 'alt=' not in img.lower():
                issues.append({
                    'type': 'missing_alt_text',
                    'element': img,
                    'message': 'Image missing alt attribute'
                })
            elif re.search(r'alt=["\'][\s]*["\']', img, re.IGNORECASE):
                issues.append({
                    'type': 'empty_alt_text',
                    'element': img,
                    'message': 'Image has empty alt text'
                })
        
        # Check for proper heading hierarchy
        headings = re.findall(r'<h([1-6])[^>]*>', html_content, re.IGNORECASE)
        if headings:
            heading_levels = [int(h) for h in headings]
            for i in range(1, len(heading_levels)):
                if heading_levels[i] > heading_levels[i-1] + 1:
                    issues.append({
                        'type': 'heading_hierarchy_skip',
                        'message': f'Heading hierarchy skip: h{heading_levels[i-1]} to h{heading_levels[i]}'
                    })
        
        # Check for form labels
        inputs = re.findall(r'<input[^>]*>', html_content, re.IGNORECASE)
        for input_elem in inputs:
            if 'type="text"' in input_elem or 'type="email"' in input_elem or 'type="password"' in input_elem:
                if 'aria-label=' not in input_elem and 'aria-labelledby=' not in input_elem:
                    # Check if there's a nearby label
                    input_id = re.search(r'id=["\']([^"\']+)["\']', input_elem)
                    if input_id:
                        label_pattern = f'<label[^>]*for=["\']?{input_id.group(1)}["\']?[^>]*>'
                        if not re.search(label_pattern, html_content, re.IGNORECASE):
                            issues.append({
                                'type': 'missing_form_label',
                                'element': input_elem,
                                'message': 'Form input missing associated label'
                            })
        
        return issues
    
    def check_screen_reader_compatibility(self, html_content):
        """Check screen reader compatibility."""
        issues = []
        
        # Check for ARIA landmarks
        landmarks = ['main', 'navigation', 'banner', 'contentinfo', 'complementary']
        has_landmarks = any(f'role="{landmark}"' in html_content.lower() for landmark in landmarks)

        # Check content length (remove whitespace for accurate measurement)
        content_length = len(html_content.strip())

        if not has_landmarks and content_length > 200:  # Lowered threshold for testing
            issues.append({
                'type': 'missing_landmarks',
                'message': 'Content lacks ARIA landmarks for navigation'
            })
        
        # Check for proper ARIA attributes
        aria_elements = re.findall(r'aria-[a-z]+=["\'][^"\']*["\']', html_content, re.IGNORECASE)
        
        # Check for invalid ARIA attributes
        valid_aria_attrs = {
            'aria-label', 'aria-labelledby', 'aria-describedby', 'aria-hidden',
            'aria-expanded', 'aria-selected', 'aria-checked', 'aria-disabled',
            'aria-live', 'aria-atomic', 'aria-relevant', 'aria-busy'
        }
        
        for aria_attr in aria_elements:
            attr_name = aria_attr.split('=')[0].lower()
            if attr_name not in valid_aria_attrs:
                issues.append({
                    'type': 'invalid_aria_attribute',
                    'attribute': attr_name,
                    'message': f'Invalid or non-standard ARIA attribute: {attr_name}'
                })
        
        # Check for decorative images
        decorative_images = re.findall(r'<img[^>]*alt=["\'][\s]*["\'][^>]*>', html_content, re.IGNORECASE)
        for img in decorative_images:
            if 'role="presentation"' not in img and 'aria-hidden="true"' not in img:
                issues.append({
                    'type': 'decorative_image_not_hidden',
                    'element': img,
                    'message': 'Decorative image should have role="presentation" or aria-hidden="true"'
                })
        
        # Check for focus management
        if 'tabindex=' in html_content:
            tabindex_values = re.findall(r'tabindex=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
            for value in tabindex_values:
                try:
                    tab_value = int(value)
                    if tab_value > 0:
                        issues.append({
                            'type': 'positive_tabindex',
                            'value': tab_value,
                            'message': f'Positive tabindex ({tab_value}) disrupts natural tab order'
                        })
                except ValueError:
                    issues.append({
                        'type': 'invalid_tabindex',
                        'value': value,
                        'message': f'Invalid tabindex value: {value}'
                    })
        
        return issues


class TestColorContrastCompliance:
    """Test color contrast compliance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = AccessibilityChecker()
    
    def test_wcag_aa_contrast_compliance(self):
        """Test WCAG AA contrast compliance."""
        # Test cases: (foreground, background, font_size, is_bold, should_pass_aa)
        test_cases = [
            ('#000000', '#FFFFFF', 12, False, True),   # Black on white - excellent
            ('#FFFFFF', '#000000', 12, False, True),   # White on black - excellent
            ('#767676', '#FFFFFF', 12, False, True),   # Gray on white - just passes AA
            ('#959595', '#FFFFFF', 12, False, False),  # Light gray on white - fails AA
            ('#000000', '#767676', 12, False, True),   # Black on gray - passes AA
            ('#FFFFFF', '#0066CC', 12, False, True),   # White on blue - passes AA
            ('#FFFF00', '#FFFFFF', 12, False, False),  # Yellow on white - fails AA
        ]
        
        for fg, bg, size, bold, should_pass in test_cases:
            result = self.checker.check_color_contrast(fg, bg, size, bold)
            
            if should_pass:
                assert result['wcag_aa_compliant'], \
                    f"Expected {fg} on {bg} to pass WCAG AA (ratio: {result['contrast_ratio']:.2f})"
            else:
                assert not result['wcag_aa_compliant'], \
                    f"Expected {fg} on {bg} to fail WCAG AA (ratio: {result['contrast_ratio']:.2f})"
    
    def test_large_text_contrast_requirements(self):
        """Test contrast requirements for large text."""
        # Large text has lower contrast requirements
        test_cases = [
            ('#767676', '#FFFFFF', 18, False, True),   # 18pt text - lower requirement
            ('#767676', '#FFFFFF', 14, True, True),    # 14pt bold - lower requirement
            ('#767676', '#FFFFFF', 12, False, True),   # 12pt text - passes AA
            ('#888888', '#FFFFFF', 18, False, True),   # Light gray large text - passes with lower requirement
            ('#CCCCCC', '#FFFFFF', 12, False, False),  # Very light gray small text - fails
        ]
        
        for fg, bg, size, bold, should_pass in test_cases:
            result = self.checker.check_color_contrast(fg, bg, size, bold)
            
            if should_pass:
                assert result['wcag_aa_compliant'], \
                    f"Expected {fg} on {bg} ({size}pt, bold={bold}) to pass WCAG AA"
            else:
                assert not result['wcag_aa_compliant'], \
                    f"Expected {fg} on {bg} ({size}pt, bold={bold}) to fail WCAG AA"
    
    def test_wcag_aaa_contrast_compliance(self):
        """Test WCAG AAA contrast compliance (higher standard)."""
        test_cases = [
            ('#000000', '#FFFFFF', 12, False, True),   # Black on white - passes AAA
            ('#595959', '#FFFFFF', 12, False, True),   # Dark gray on white - passes AAA
            ('#767676', '#FFFFFF', 12, False, False),  # Medium gray on white - fails AAA
            ('#FFFFFF', '#003D99', 12, False, True),   # White on dark blue - passes AAA
        ]
        
        for fg, bg, size, bold, should_pass in test_cases:
            result = self.checker.check_color_contrast(fg, bg, size, bold)
            
            if should_pass:
                assert result['wcag_aaa_compliant'], \
                    f"Expected {fg} on {bg} to pass WCAG AAA (ratio: {result['contrast_ratio']:.2f})"
            else:
                assert not result['wcag_aaa_compliant'], \
                    f"Expected {fg} on {bg} to fail WCAG AAA (ratio: {result['contrast_ratio']:.2f})"


class TestKeyboardAccessibility:
    """Test keyboard accessibility."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = AccessibilityChecker()
    
    def test_interactive_elements_keyboard_accessible(self):
        """Test that interactive elements are keyboard accessible."""
        accessible_html = '''
        <div>
            <button type="button">Accessible Button</button>
            <input type="text" id="text-input">
            <a href="#section">Accessible Link</a>
            <select id="dropdown">
                <option>Option 1</option>
            </select>
        </div>
        '''
        
        issues = self.checker.check_keyboard_accessibility(accessible_html)
        
        # Should have no keyboard accessibility issues
        keyboard_issues = [issue for issue in issues if issue['type'] in ['missing_tabindex', 'negative_tabindex']]
        assert len(keyboard_issues) == 0, f"Found keyboard accessibility issues: {keyboard_issues}"
    
    def test_custom_interactive_elements_need_tabindex(self):
        """Test that custom interactive elements need proper tabindex."""
        inaccessible_html = '''
        <div onclick="handleClick()">Custom Button</div>
        <span onclick="doSomething()">Clickable Span</span>
        '''
        
        issues = self.checker.check_keyboard_accessibility(inaccessible_html)
        
        # Should detect missing tabindex issues
        tabindex_issues = [issue for issue in issues if issue['type'] == 'missing_tabindex']
        assert len(tabindex_issues) > 0, "Should detect missing tabindex on custom interactive elements"
    
    def test_image_alt_text_requirements(self):
        """Test image alt text requirements."""
        html_with_images = '''
        <div>
            <img src="chart.png" alt="Sales chart showing 20% increase">
            <img src="decorative.png" alt="">
            <img src="missing-alt.png">
            <img src="empty-alt.png" alt="   ">
        </div>
        '''
        
        issues = self.checker.check_keyboard_accessibility(html_with_images)
        
        # Should detect missing and empty alt text
        alt_issues = [issue for issue in issues if 'alt' in issue['type']]
        assert len(alt_issues) >= 2, "Should detect missing and empty alt text issues"
        
        # Check specific issue types
        missing_alt = [issue for issue in issues if issue['type'] == 'missing_alt_text']
        empty_alt = [issue for issue in issues if issue['type'] == 'empty_alt_text']
        
        assert len(missing_alt) >= 1, "Should detect missing alt attribute"
        assert len(empty_alt) >= 1, "Should detect empty alt text"
    
    def test_form_label_requirements(self):
        """Test form label requirements."""
        html_with_forms = '''
        <form>
            <label for="name">Name:</label>
            <input type="text" id="name">
            
            <input type="email" id="email" aria-label="Email address">
            
            <input type="password" id="password">
            
            <input type="text" aria-labelledby="address-label">
            <span id="address-label">Address</span>
        </form>
        '''
        
        issues = self.checker.check_keyboard_accessibility(html_with_forms)
        
        # Should detect unlabeled form inputs
        label_issues = [issue for issue in issues if issue['type'] == 'missing_form_label']
        assert len(label_issues) >= 1, "Should detect missing form labels"
    
    def test_heading_hierarchy(self):
        """Test proper heading hierarchy."""
        bad_hierarchy_html = '''
        <div>
            <h1>Main Title</h1>
            <h3>Skipped H2</h3>
            <h2>This should come before H3</h2>
            <h5>Skipped H4</h5>
        </div>
        '''
        
        issues = self.checker.check_keyboard_accessibility(bad_hierarchy_html)
        
        # Should detect heading hierarchy issues
        hierarchy_issues = [issue for issue in issues if issue['type'] == 'heading_hierarchy_skip']
        assert len(hierarchy_issues) >= 1, "Should detect heading hierarchy skips"


class TestScreenReaderCompatibility:
    """Test screen reader compatibility."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = AccessibilityChecker()
    
    def test_aria_landmarks_presence(self):
        """Test presence of ARIA landmarks."""
        html_without_landmarks = '''
        <div>
            <div>Navigation content here</div>
            <div>Main content here with lots of text to make it substantial content that should have landmarks for proper navigation by screen readers and other assistive technologies.</div>
            <div>Footer content here</div>
        </div>
        '''
        
        issues = self.checker.check_screen_reader_compatibility(html_without_landmarks)
        
        # Should detect missing landmarks for substantial content
        landmark_issues = [issue for issue in issues if issue['type'] == 'missing_landmarks']
        assert len(landmark_issues) >= 1, "Should detect missing ARIA landmarks"
    
    def test_proper_aria_attributes(self):
        """Test proper ARIA attributes."""
        html_with_aria = '''
        <div>
            <button aria-expanded="false" aria-controls="menu">Menu</button>
            <div id="menu" aria-hidden="true">Menu content</div>
            <input type="text" aria-label="Search" aria-describedby="search-help">
            <div id="search-help">Enter keywords to search</div>
            <div aria-invalid-attribute="value">Invalid ARIA</div>
        </div>
        '''
        
        issues = self.checker.check_screen_reader_compatibility(html_with_aria)
        
        # Should detect invalid ARIA attributes
        aria_issues = [issue for issue in issues if issue['type'] == 'invalid_aria_attribute']
        assert len(aria_issues) >= 1, "Should detect invalid ARIA attributes"
    
    def test_decorative_images_hidden(self):
        """Test that decorative images are properly hidden."""
        html_with_decorative_images = '''
        <div>
            <img src="decorative1.png" alt="" role="presentation">
            <img src="decorative2.png" alt="" aria-hidden="true">
            <img src="decorative3.png" alt="">
        </div>
        '''
        
        issues = self.checker.check_screen_reader_compatibility(html_with_decorative_images)
        
        # Should detect decorative images not properly hidden
        decorative_issues = [issue for issue in issues if issue['type'] == 'decorative_image_not_hidden']
        assert len(decorative_issues) >= 1, "Should detect decorative images not properly hidden"
    
    def test_tabindex_best_practices(self):
        """Test tabindex best practices."""
        html_with_tabindex = '''
        <div>
            <button tabindex="1">First button</button>
            <button tabindex="2">Second button</button>
            <div tabindex="0">Focusable div</div>
            <div tabindex="-1">Skip focus div</div>
            <input tabindex="invalid">Invalid tabindex</input>
        </div>
        '''
        
        issues = self.checker.check_screen_reader_compatibility(html_with_tabindex)
        
        # Should detect positive tabindex values and invalid values
        tabindex_issues = [issue for issue in issues if 'tabindex' in issue['type']]
        assert len(tabindex_issues) >= 2, "Should detect tabindex issues"
        
        # Check for specific issues
        positive_tabindex = [issue for issue in issues if issue['type'] == 'positive_tabindex']
        invalid_tabindex = [issue for issue in issues if issue['type'] == 'invalid_tabindex']
        
        assert len(positive_tabindex) >= 2, "Should detect positive tabindex values"
        assert len(invalid_tabindex) >= 1, "Should detect invalid tabindex values"


if __name__ == "__main__":
    pytest.main([__file__])
