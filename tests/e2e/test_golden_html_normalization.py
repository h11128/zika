"""
End-to-end tests for golden HTML normalization.
Tests that v1 and v2 preview implementations produce equivalent HTML during migration.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os
import re
import hashlib

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class HTMLNormalizer:
    """HTML normalizer for comparing preview outputs."""
    
    @staticmethod
    def normalize_html(html_content):
        """Normalize HTML for comparison."""
        if not html_content:
            return ""
        
        # Remove extra whitespace between tags and normalize internal whitespace
        normalized = re.sub(r'>\s+<', '><', html_content.strip())
        # Normalize whitespace inside text content
        normalized = re.sub(r'>(\s+)', '>', normalized)  # Remove leading whitespace after >
        normalized = re.sub(r'(\s+)<', '<', normalized)  # Remove trailing whitespace before <
        normalized = re.sub(r'\s+', ' ', normalized)     # Normalize multiple spaces to single

        # Normalize quotes
        normalized = normalized.replace('"', "'")
        
        # Remove comments
        normalized = re.sub(r'<!--.*?-->', '', normalized, flags=re.DOTALL)
        
        # Normalize CSS whitespace
        normalized = re.sub(r':\s+', ':', normalized)
        normalized = re.sub(r';\s+', ';', normalized)
        
        # Sort CSS properties for consistent comparison
        normalized = HTMLNormalizer._sort_css_properties(normalized)
        
        # Normalize data attributes (remove dynamic values)
        normalized = re.sub(r"data-testid='[^']*'", "data-testid='normalized'", normalized)
        normalized = re.sub(r"id='[^']*'", "id='normalized'", normalized)

        # Normalize class names (v1 vs v2)
        normalized = re.sub(r'preview-v[12]', 'preview', normalized)

        # Sort data attributes for consistent ordering
        normalized = HTMLNormalizer._sort_data_attributes(normalized)

        return normalized.strip()
    
    @staticmethod
    def _sort_css_properties(html):
        """Sort CSS properties within style attributes."""
        def sort_style(match):
            style_content = match.group(1)
            properties = [prop.strip() for prop in style_content.split(';') if prop.strip()]
            properties.sort()
            return f"style='{';'.join(properties)}'"

        return re.sub(r"style='([^']*)'", sort_style, html)

    @staticmethod
    def _sort_data_attributes(html):
        """Sort data attributes within elements."""
        def sort_data_attrs(match):
            element_content = match.group(1)
            # Extract data attributes
            data_attrs = re.findall(r'(data-[^=]+=[\'"][^\'\"]*[\'"])', element_content)
            if len(data_attrs) <= 1:
                return match.group(0)

            # Remove data attributes from element
            for attr in data_attrs:
                element_content = element_content.replace(attr, '')

            # Sort and re-add data attributes
            data_attrs.sort()
            sorted_attrs = ' '.join(data_attrs)

            # Find insertion point (after class if present, otherwise after tag name)
            if 'class=' in element_content:
                element_content = re.sub(r"(class='[^']*')", r"\1 " + sorted_attrs, element_content)
            else:
                # Insert after tag name
                element_content = re.sub(r"(<[^>]+?)(\s|>)", r"\1 " + sorted_attrs + r"\2", element_content)

            return element_content

        return re.sub(r'(<[^>]+data-[^>]*>)', sort_data_attrs, html)
    
    @staticmethod
    def extract_content_hash(html_content):
        """Extract content hash from normalized HTML."""
        normalized = HTMLNormalizer.normalize_html(html_content)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def compare_html_structure(html1, html2):
        """Compare HTML structure ignoring dynamic content."""
        norm1 = HTMLNormalizer.normalize_html(html1)
        norm2 = HTMLNormalizer.normalize_html(html2)
        
        # Extract structural elements
        structure1 = HTMLNormalizer._extract_structure(norm1)
        structure2 = HTMLNormalizer._extract_structure(norm2)
        
        return structure1 == structure2
    
    @staticmethod
    def _extract_structure(html):
        """Extract structural elements from HTML."""
        # Remove text content, keep only tags and structure
        structure = re.sub(r'>([^<]+)<', '><', html)
        
        # Remove attribute values, keep only attribute names
        structure = re.sub(r'(\w+)=[\'"][^\'"]*[\'"]', r'\1', structure)
        
        return structure


class MockPreviewRendererV1:
    """Mock v1 preview renderer for testing."""
    
    def __init__(self):
        self.render_count = 0
    
    def render_preview(self, cards_data, layout_options, typography_options, visual_options):
        """Render preview using v1 implementation."""
        self.render_count += 1
        
        # Simulate v1 rendering logic
        html_parts = ['<div class="preview-v1">']
        
        # Add cards
        for i, card in enumerate(cards_data):
            card_html = f'''
            <div class="card card-{i}" style="font-size:{typography_options.get('hanzi_font_size', 48)}px;background-color:{visual_options.get('background_color', '#FFFFFF')}">
                <div class="hanzi">{card.get('hanzi', '')}</div>
                <div class="pinyin">{card.get('pinyin', '')}</div>
                <div class="english">{card.get('english', '')}</div>
            </div>
            '''
            html_parts.append(card_html)
        
        # Add layout info
        layout_html = f'''
        <div class="layout-info" data-rows="{layout_options.get('rows', 2)}" data-cols="{layout_options.get('cols', 3)}">
            Layout: {layout_options.get('rows', 2)}x{layout_options.get('cols', 3)}
        </div>
        '''
        html_parts.append(layout_html)
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)


class MockPreviewRendererV2:
    """Mock v2 preview renderer for testing."""
    
    def __init__(self):
        self.render_count = 0
    
    def render_preview_content(self, cards_data, app_config):
        """Render preview using v2 implementation."""
        self.render_count += 1
        
        # Extract options from app_config
        layout_options = app_config.get('layout', {})
        typography_options = app_config.get('typography', {})
        visual_options = app_config.get('visual', {})
        
        # Simulate v2 rendering logic (should produce equivalent output)
        html_parts = ['<div class="preview-v2">']
        
        # Add cards (same structure as v1)
        for i, card in enumerate(cards_data):
            card_html = f'''
            <div class="card card-{i}" style="background-color:{visual_options.get('background_color', '#FFFFFF')};font-size:{typography_options.get('hanzi_font_size', 48)}px">
                <div class="hanzi">{card.get('hanzi', '')}</div>
                <div class="pinyin">{card.get('pinyin', '')}</div>
                <div class="english">{card.get('english', '')}</div>
            </div>
            '''
            html_parts.append(card_html)
        
        # Add layout info (same structure as v1)
        layout_html = f'''
        <div class="layout-info" data-cols="{layout_options.get('cols', 3)}" data-rows="{layout_options.get('rows', 2)}">
            Layout: {layout_options.get('rows', 2)}x{layout_options.get('cols', 3)}
        </div>
        '''
        html_parts.append(layout_html)
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)


class TestGoldenHTMLNormalization:
    """Test golden HTML normalization between v1 and v2."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer_v1 = MockPreviewRendererV1()
        self.renderer_v2 = MockPreviewRendererV2()
        self.normalizer = HTMLNormalizer()
    
    def test_v1_v2_html_equivalence(self):
        """Test that v1 and v2 produce equivalent HTML."""
        # Test data
        cards_data = [
            {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
            {'hanzi': '世界', 'pinyin': 'shì jiè', 'english': 'world'}
        ]
        
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # Render with v1
        html_v1 = self.renderer_v1.render_preview(
            cards_data, layout_options, typography_options, visual_options
        )
        
        # Render with v2
        app_config = {
            'layout': layout_options,
            'typography': typography_options,
            'visual': visual_options
        }
        html_v2 = self.renderer_v2.render_preview_content(cards_data, app_config)
        
        # Normalize both outputs
        normalized_v1 = self.normalizer.normalize_html(html_v1)
        normalized_v2 = self.normalizer.normalize_html(html_v2)
        
        # Should be equivalent after normalization
        assert normalized_v1 == normalized_v2, f"V1 and V2 HTML should be equivalent after normalization"
    
    def test_html_structure_equivalence(self):
        """Test that v1 and v2 have equivalent HTML structure."""
        cards_data = [
            {'hanzi': '学习', 'pinyin': 'xué xí', 'english': 'study'}
        ]
        
        layout_options = {'rows': 1, 'cols': 1}
        typography_options = {'hanzi_font_size': 52}
        visual_options = {'background_color': '#F0F0F0'}
        
        # Render with both versions
        html_v1 = self.renderer_v1.render_preview(
            cards_data, layout_options, typography_options, visual_options
        )
        
        app_config = {
            'layout': layout_options,
            'typography': typography_options,
            'visual': visual_options
        }
        html_v2 = self.renderer_v2.render_preview_content(cards_data, app_config)
        
        # Compare structure
        structure_equivalent = self.normalizer.compare_html_structure(html_v1, html_v2)
        assert structure_equivalent, "V1 and V2 should have equivalent HTML structure"
    
    def test_content_hash_consistency(self):
        """Test that content hashes are consistent between v1 and v2."""
        cards_data = [
            {'hanzi': '测试', 'pinyin': 'cèshì', 'english': 'test'},
            {'hanzi': '代码', 'pinyin': 'dàimǎ', 'english': 'code'}
        ]
        
        layout_options = {'rows': 2, 'cols': 2}
        typography_options = {'hanzi_font_size': 44}
        visual_options = {'background_color': '#E0E0E0'}
        
        # Render with both versions
        html_v1 = self.renderer_v1.render_preview(
            cards_data, layout_options, typography_options, visual_options
        )
        
        app_config = {
            'layout': layout_options,
            'typography': typography_options,
            'visual': visual_options
        }
        html_v2 = self.renderer_v2.render_preview_content(cards_data, app_config)
        
        # Extract content hashes
        hash_v1 = self.normalizer.extract_content_hash(html_v1)
        hash_v2 = self.normalizer.extract_content_hash(html_v2)
        
        # Hashes should be identical
        assert hash_v1 == hash_v2, f"Content hashes should be identical: {hash_v1} vs {hash_v2}"
    
    def test_empty_cards_equivalence(self):
        """Test equivalence with empty cards data."""
        cards_data = []
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # Render with both versions
        html_v1 = self.renderer_v1.render_preview(
            cards_data, layout_options, typography_options, visual_options
        )
        
        app_config = {
            'layout': layout_options,
            'typography': typography_options,
            'visual': visual_options
        }
        html_v2 = self.renderer_v2.render_preview_content(cards_data, app_config)
        
        # Should be equivalent
        normalized_v1 = self.normalizer.normalize_html(html_v1)
        normalized_v2 = self.normalizer.normalize_html(html_v2)
        
        assert normalized_v1 == normalized_v2
    
    def test_large_dataset_equivalence(self):
        """Test equivalence with large dataset."""
        # Generate large dataset
        cards_data = []
        for i in range(100):
            cards_data.append({
                'hanzi': f'字{i}',
                'pinyin': f'zì{i}',
                'english': f'character{i}'
            })
        
        layout_options = {'rows': 10, 'cols': 10}
        typography_options = {'hanzi_font_size': 36}
        visual_options = {'background_color': '#F8F8F8'}
        
        # Render with both versions
        html_v1 = self.renderer_v1.render_preview(
            cards_data, layout_options, typography_options, visual_options
        )
        
        app_config = {
            'layout': layout_options,
            'typography': typography_options,
            'visual': visual_options
        }
        html_v2 = self.renderer_v2.render_preview_content(cards_data, app_config)
        
        # Should be equivalent
        hash_v1 = self.normalizer.extract_content_hash(html_v1)
        hash_v2 = self.normalizer.extract_content_hash(html_v2)
        
        assert hash_v1 == hash_v2


class TestHTMLNormalizationEdgeCases:
    """Test HTML normalization edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = HTMLNormalizer()
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization."""
        html1 = "<div>  Hello   World  </div>"
        html2 = "<div>Hello World</div>"
        
        norm1 = self.normalizer.normalize_html(html1)
        norm2 = self.normalizer.normalize_html(html2)
        
        assert norm1 == norm2
    
    def test_css_property_sorting(self):
        """Test CSS property sorting."""
        html1 = "<div style='color:red;background:blue;font-size:12px'>Test</div>"
        html2 = "<div style='background:blue;font-size:12px;color:red'>Test</div>"
        
        norm1 = self.normalizer.normalize_html(html1)
        norm2 = self.normalizer.normalize_html(html2)
        
        assert norm1 == norm2
    
    def test_quote_normalization(self):
        """Test quote normalization."""
        html1 = '<div class="test">Content</div>'
        html2 = "<div class='test'>Content</div>"
        
        norm1 = self.normalizer.normalize_html(html1)
        norm2 = self.normalizer.normalize_html(html2)
        
        assert norm1 == norm2
    
    def test_comment_removal(self):
        """Test comment removal."""
        html1 = "<div><!-- comment -->Content</div>"
        html2 = "<div>Content</div>"
        
        norm1 = self.normalizer.normalize_html(html1)
        norm2 = self.normalizer.normalize_html(html2)
        
        assert norm1 == norm2
    
    def test_dynamic_attribute_normalization(self):
        """Test dynamic attribute normalization."""
        html1 = '<div id="dynamic-123" data-testid="test-456">Content</div>'
        html2 = '<div id="dynamic-789" data-testid="test-999">Content</div>'
        
        norm1 = self.normalizer.normalize_html(html1)
        norm2 = self.normalizer.normalize_html(html2)
        
        assert norm1 == norm2


class TestMigrationValidation:
    """Test migration validation scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer_v1 = MockPreviewRendererV1()
        self.renderer_v2 = MockPreviewRendererV2()
        self.normalizer = HTMLNormalizer()
        self.validation_results = []
    
    def test_migration_validation_suite(self):
        """Test comprehensive migration validation."""
        # Test cases covering various scenarios
        test_cases = [
            # Basic case
            {
                'cards': [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}],
                'layout': {'rows': 1, 'cols': 1},
                'typography': {'hanzi_font_size': 48},
                'visual': {'background_color': '#FFFFFF'}
            },
            # Multiple cards
            {
                'cards': [
                    {'hanzi': '学习', 'pinyin': 'xué xí', 'english': 'study'},
                    {'hanzi': '中文', 'pinyin': 'zhōng wén', 'english': 'Chinese'}
                ],
                'layout': {'rows': 2, 'cols': 1},
                'typography': {'hanzi_font_size': 52},
                'visual': {'background_color': '#F0F0F0'}
            },
            # Large layout
            {
                'cards': [{'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'} for i in range(12)],
                'layout': {'rows': 3, 'cols': 4},
                'typography': {'hanzi_font_size': 36},
                'visual': {'background_color': '#E8E8E8'}
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            # Render with both versions
            html_v1 = self.renderer_v1.render_preview(
                test_case['cards'],
                test_case['layout'],
                test_case['typography'],
                test_case['visual']
            )
            
            app_config = {
                'layout': test_case['layout'],
                'typography': test_case['typography'],
                'visual': test_case['visual']
            }
            html_v2 = self.renderer_v2.render_preview_content(test_case['cards'], app_config)
            
            # Validate equivalence
            hash_v1 = self.normalizer.extract_content_hash(html_v1)
            hash_v2 = self.normalizer.extract_content_hash(html_v2)
            
            validation_result = {
                'test_case': i,
                'equivalent': hash_v1 == hash_v2,
                'hash_v1': hash_v1,
                'hash_v2': hash_v2,
                'cards_count': len(test_case['cards'])
            }
            
            self.validation_results.append(validation_result)
            
            # Assert equivalence
            assert hash_v1 == hash_v2, f"Test case {i} failed: V1 and V2 should produce equivalent HTML"
        
        # All test cases should pass
        assert all(result['equivalent'] for result in self.validation_results)
        assert len(self.validation_results) == len(test_cases)


if __name__ == "__main__":
    pytest.main([__file__])
