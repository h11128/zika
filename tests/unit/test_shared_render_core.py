"""
Unit tests for shared render core integration.
Tests the integration between preview/export and the unified render core.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.preview_types import PreviewParams, LayoutOptions, Typography, VisualOptions, convert_preview_params_to_render_options
from services.render_core import RenderOptions, RenderResult


class TestSharedRenderCoreIntegration:
    """Test shared render core integration with preview and export."""
    
    def test_convert_preview_params_to_render_options(self):
        """Test conversion from PreviewParams to RenderOptions."""
        # Create test preview params
        layout = LayoutOptions(
            layout_rows=3, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        
        typography = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )
        
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        preview_params = PreviewParams(
            layout=layout,
            typography=typography,
            visual=visual
        )
        
        # Convert to render options
        render_options = convert_preview_params_to_render_options(preview_params)
        
        # Verify conversion
        assert isinstance(render_options, RenderOptions)
        assert render_options.layout_rows == 3
        assert render_options.layout_cols == 2
        assert render_options.card_size_cm == 5.5
        assert render_options.gap_cm == 0.5
        assert render_options.margin_cm == 1.0
        assert render_options.page_size == 'A4'
        assert render_options.layout_auto_fill is True

        assert render_options.hanzi_font_size_pt == 48
        assert render_options.pinyin_font_size_pt == 18
        assert render_options.english_font_size_pt == 14
        assert render_options.hanzi_font_family == 'SimHei'

        assert render_options.background_color == '#ffffff'
    
    @patch('core.feature_flags.get_feature_flag')
    @patch('services.render_core.render_cards_unified')
    def test_preview_controller_uses_shared_core(self, mock_render, mock_feature_flag):
        """Test that preview controller uses shared render core when enabled."""
        from ui.preview_controller import PreviewController
        
        # Enable shared render core
        mock_feature_flag.return_value = True
        
        # Mock successful render result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = '<html>test content</html>'
        mock_render.return_value = mock_result
        
        # Create test data
        processed_cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        
        typography = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )
        
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        
        # Create controller and test
        controller = PreviewController()
        
        # Test page preview
        result = controller._create_page_preview_html_immediate(processed_cards, 0, params)
        
        # Verify shared render core was called
        assert mock_render.called
        assert result == '<html>test content</html>'
        
        # Verify render options were passed correctly
        call_args = mock_render.call_args
        assert call_args[0][0] == processed_cards  # cards
        assert isinstance(call_args[0][1], RenderOptions)  # render_options
        assert call_args[1]['output_format'] == 'html'
    
    @patch('core.feature_flags.get_feature_flag')
    @patch('services.render_core.render_cards_unified')
    def test_preview_controller_fallback_on_failure(self, mock_render, mock_feature_flag):
        """Test that preview controller falls back to legacy on shared core failure."""
        from ui.preview_controller import PreviewController
        
        # Enable shared render core
        mock_feature_flag.return_value = True
        
        # Mock failed render result
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = 'Test error'
        mock_render.return_value = mock_result
        
        # Create test data
        processed_cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        
        typography = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )
        
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        
        # Mock legacy function
        with patch('services.cache_v2.create_page_preview_html') as mock_legacy:
            mock_legacy.return_value = '<html>legacy content</html>'
            
            # Create controller and test
            controller = PreviewController()
            result = controller._create_page_preview_html_immediate(processed_cards, 0, params)
            
            # Verify shared render core was attempted
            assert mock_render.called
            
            # Verify fallback to legacy was used
            assert mock_legacy.called
            assert result == '<html>legacy content</html>'
    
    @patch('core.feature_flags.get_feature_flag')
    def test_preview_controller_disabled_shared_core(self, mock_feature_flag):
        """Test that preview controller uses legacy when shared core is disabled."""
        from ui.preview_controller import PreviewController
        
        # Disable shared render core
        mock_feature_flag.return_value = False
        
        # Create test data
        processed_cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        
        typography = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )
        
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        
        # Mock legacy function
        with patch('services.cache_v2.create_page_preview_html') as mock_legacy:
            mock_legacy.return_value = '<html>legacy content</html>'
            
            # Create controller and test
            controller = PreviewController()
            result = controller._create_page_preview_html_immediate(processed_cards, 0, params)
            
            # Verify legacy was used directly
            assert mock_legacy.called
            assert result == '<html>legacy content</html>'
    
    @patch('core.feature_flags.get_feature_flag')
    @patch('services.render_core.render_cards_unified')
    def test_pdf_export_uses_shared_core(self, mock_render, mock_feature_flag):
        """Test that PDF export uses shared render core when enabled."""
        from src.layout_pdf import generate_pdf_with_shared_core
        from services.render_core import RenderOptions

        # Enable shared render core
        mock_feature_flag.return_value = True

        # Mock successful render result
        mock_result = MagicMock()
        mock_result.success = True
        mock_render.return_value = mock_result

        # Create test data
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        output_path = '/tmp/test.pdf'

        render_options = RenderOptions(
            layout_rows=2, layout_cols=2, gap_cm=0.5, margin_cm=1.0,
            card_size_cm=5.5, page_size='A4', layout_auto_fill=True,
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei',
            background_color='#ffffff'
        )
        
        # Test PDF generation
        result = generate_pdf_with_shared_core(cards, output_path, render_options)
        
        # Verify shared render core was called
        assert mock_render.called
        assert result is True
        
        # Verify render options were passed correctly
        call_args = mock_render.call_args
        assert call_args[0][0] == cards  # cards
        assert call_args[0][1] == render_options  # render_options
        assert call_args[1]['output_format'] == 'pdf'
        assert call_args[1]['output_path'] == output_path
    
    @patch('core.feature_flags.get_feature_flag')
    @patch('services.render_core.render_cards_unified')
    def test_pdf_export_fallback_on_failure(self, mock_render, mock_feature_flag):
        """Test that PDF export falls back to legacy on shared core failure."""
        from src.layout_pdf import generate_pdf_with_shared_core, PDFCardGenerator
        from services.render_core import RenderOptions

        # Enable shared render core
        mock_feature_flag.return_value = True

        # Mock failed render result
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = 'Test error'
        mock_render.return_value = mock_result

        # Create test data
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        output_path = '/tmp/test.pdf'

        render_options = RenderOptions(
            layout_rows=2, layout_cols=2, gap_cm=0.5, margin_cm=1.0,
            card_size_cm=5.5, page_size='A4', layout_auto_fill=True,
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei',
            background_color='#ffffff'
        )
        
        # Mock legacy PDF generator
        with patch.object(PDFCardGenerator, 'generate_pdf') as mock_legacy:
            mock_legacy.return_value = True
            
            # Test PDF generation
            result = generate_pdf_with_shared_core(cards, output_path, render_options)
            
            # Verify shared render core was attempted
            assert mock_render.called
            
            # Verify fallback to legacy was used
            assert mock_legacy.called
            assert result is True
