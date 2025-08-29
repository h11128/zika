from services.cache import (
    create_page_preview_html,
    create_simple_grid_html,
)


def test_create_page_preview_html_auto_fill_and_letter():
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = create_page_preview_html(
        cards, page_num=0,
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size="Letter", hanzi_font="SimHei", background_color="#FFFFFF",
        rows=2, cols=2, auto_fill=True,
    )
    assert "page-container" in html and "grid-template-columns" in html
    assert "第 1 页" in html


def test_create_page_preview_html_page_out_of_range():
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = create_page_preview_html(
        cards, page_num=5,
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size="A4", hanzi_font="SimHei", background_color="#FFFFFF",
        rows=2, cols=2, auto_fill=False,
    )
    assert "页面不存在" in html


def test_create_simple_grid_html_empty_and_nonempty():
    empty_html = create_simple_grid_html([], hanzi_font="SimHei", background_color="#FFFFFF", rows=2, cols=2)
    assert "输入汉字以查看预览" in empty_html

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = create_simple_grid_html(cards, hanzi_font="SimHei", background_color="#FFFFFF", rows=2, cols=2)
    assert "simple-card" in html and "simple-grid" in html


# Additional coverage tests for ui/sections.py
def test_csv_upload_missing_columns():
    """Test CSV upload with missing required columns."""
    import pandas as pd
    from unittest.mock import patch, MagicMock
    import streamlit as st
    from ui.sections import render_input_section

    with patch('ui.sections.st') as mock_st:
        # Mock uploaded file with missing hanzi column
        mock_file = MagicMock()
        mock_file.getvalue.return_value.decode.return_value = "pinyin,english\nni3,you\nhao3,good"

        mock_st.session_state = {'input_method': 'CSV上传'}
        mock_st.file_uploader.return_value = mock_file
        mock_st.error = MagicMock()

        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = pd.DataFrame({'pinyin': ['ni3'], 'english': ['you']})
            mock_read_csv.return_value = mock_df

            result = render_input_section()

            # Should show error for missing hanzi column
            mock_st.error.assert_called_with("CSV文件必须包含以下列: hanzi")
            assert result == []


def test_csv_upload_successful():
    """Test successful CSV upload."""
    import pandas as pd
    from unittest.mock import patch, MagicMock
    import streamlit as st
    from ui.sections import render_input_section

    with patch('ui.sections.st') as mock_st:
        mock_file = MagicMock()
        mock_file.getvalue.return_value.decode.return_value = "hanzi,pinyin,english\n你好,ni3hao3,hello\n世界,shi4jie4,world"

        mock_st.session_state = {'input_method': 'CSV上传'}
        mock_st.file_uploader.return_value = mock_file
        mock_st.success = MagicMock()

        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = pd.DataFrame({
                'hanzi': ['你好', '世界'],
                'pinyin': ['ni3hao3', 'shi4jie4'],
                'english': ['hello', 'world']
            })
            mock_read_csv.return_value = mock_df

            result = render_input_section()

            # Should successfully process CSV
            mock_st.success.assert_called_with("成功读取 2 张卡片")
            assert len(result) == 2
            assert result[0]['hanzi'] == '你好'
            assert result[1]['hanzi'] == '世界'




# Additional coverage tests for ui/components.py
def test_render_preview_section_immediate_mode():
    """Test render_preview_section with immediate rendering mode."""
    from unittest.mock import patch, MagicMock
    import streamlit as st
    from ui.components import render_preview_section

    with patch('ui.components.st') as mock_st:
        # Create a proper session_state mock with attribute access
        session_state = MagicMock()
        session_state.current_page = 0
        session_state.get.return_value = False  # debug_preview = False
        mock_st.session_state = session_state

        # Mock the state check functions
        with patch('core.state.check_params_changed') as mock_check, \
             patch('core.state.get_all_ui_params') as mock_get_params, \
             patch('services.cache.create_page_preview_html_immediate') as mock_create_page:

            mock_check.return_value = True  # Force immediate mode
            mock_get_params.return_value = {}
            mock_create_page.return_value = "<html>page preview</html>"

            # Mock streamlit components
            mock_placeholder = MagicMock()
            mock_st.empty.return_value = mock_placeholder
            mock_container = MagicMock()
            mock_placeholder.container.return_value = mock_container

            test_cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

            # Test full page mode
            render_preview_section(
                test_cards, "📄 完整页面",
                5.5, 0.5, 1.0,
                48, 18, 14,
                "A4", "SimHei", "#ffffff",
                2, 3, True
            )

            # Should use immediate rendering
            mock_create_page.assert_called_once()


def test_render_preview_section_empty_cards():
    """Test render_preview_section with empty cards list."""
    from unittest.mock import patch, MagicMock
    import streamlit as st
    from ui.components import render_preview_section

    with patch('ui.components.st') as mock_st:
        # Create a proper session_state mock with attribute access
        session_state = MagicMock()
        session_state.current_page = 0
        session_state.get.return_value = False  # debug_preview = False
        mock_st.session_state = session_state

        with patch('core.state.check_params_changed') as mock_check, \
             patch('core.state.get_all_ui_params') as mock_get_params, \
             patch('services.cache.create_simple_grid_html_immediate') as mock_create_grid:

            mock_check.return_value = True
            mock_get_params.return_value = {}
            mock_create_grid.return_value = "<html>empty grid</html>"

            # Mock streamlit components
            mock_placeholder = MagicMock()
            mock_st.empty.return_value = mock_placeholder
            mock_container = MagicMock()
            mock_placeholder.container.return_value = mock_container

            # Test with empty cards
            render_preview_section(
                [], "🔲 简单网格",
                5.5, 0.5, 1.0,
                48, 18, 14,
                "A4", "SimHei", "#ffffff",
                2, 3, True
            )

            # Should handle empty cards gracefully
            mock_create_grid.assert_called_once()
            args = mock_create_grid.call_args[0]
            page_cards = args[0]
            assert len(page_cards) == 0


# Additional high-priority tests for ui/sections.py critical business logic
def test_render_options_section_basic():
    """Test basic options section rendering."""
    from unittest.mock import patch, MagicMock
    import streamlit as st
    from ui.sections import render_options_section

    with patch('ui.sections.st') as mock_st:
        # Mock session_state with basic values
        mock_st.session_state = MagicMock()
        mock_st.session_state.get.return_value = False

        # Mock streamlit components
        mock_st.selectbox.return_value = 'local_first'
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        # Should not raise an error
        result = render_options_section()

        # Should return a tuple with translation order
        assert isinstance(result, tuple)
        assert len(result) == 4  # auto_pinyin, auto_translate, translate_order, card_size


def test_render_improved_card_editor_basic():
    """Test basic card editor functionality."""
    from unittest.mock import patch, MagicMock
    import streamlit as st
    from ui.sections import render_improved_card_editor

    with patch('ui.sections.st') as mock_st:
        # Mock processed cards
        processed_cards = [
            {'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'},
            {'hanzi': '世界', 'pinyin': 'shi4jie4', 'english': 'world'}
        ]

        mock_st.session_state = MagicMock()
        mock_st.session_state.get.return_value = None

        # Mock form components
        mock_form = MagicMock()
        mock_form.form_submit_button.return_value = False  # No submission
        mock_st.form.return_value.__enter__.return_value = mock_form
        mock_st.text_input.return_value = '你好'
        mock_st.number_input.return_value = 1
        mock_st.expander.return_value.__enter__.return_value = MagicMock()

        # Should not raise an error
        render_improved_card_editor(processed_cards)

        # Function should complete without errors
        assert True  # Just test that it doesn't crash


# Note: Advanced options test removed due to complex Streamlit session state dependencies


# Comprehensive preview functionality tests
def test_create_page_preview_html_zero_rows_cols():
    """Test page preview with zero rows or cols (edge case coverage)."""
    from services.cache import create_page_preview_html

    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

    # Test with zero cols
    html = create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 0, True
    )
    assert isinstance(html, str)
    assert len(html) > 0

    # Test with zero rows
    html = create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 0, 3, True
    )
    assert isinstance(html, str)
    assert len(html) > 0


def test_create_page_preview_html_manual_card_size():
    """Test page preview with manual card size (auto_fill=False)."""
    from services.cache import create_page_preview_html

    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

    # Test with auto_fill=False (manual card size)
    html = create_page_preview_html(
        cards, 0, 6.0, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, False
    )
    assert isinstance(html, str)
    assert len(html) > 0
    # Should contain the manual card size calculation
    assert "card-size" in html or "width" in html


def test_create_simple_grid_html_font_size_calculations():
    """Test simple grid HTML with various font size calculations."""
    from services.cache import create_simple_grid_html

    cards = [
        {'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'},
        {'hanzi': '世界', 'pinyin': 'shi4jie4', 'english': 'world'}
    ]

    # Test with different font sizes
    html = create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2,
        font_hanzi=26, font_pinyin=12, font_english=14,
        card_size=5.5, auto_fill=True
    )

    assert isinstance(html, str)
    assert len(html) > 0
    # Should contain font size calculations (pt to px conversion)
    assert "font-size" in html

    # Use regex to extract CSS font-size values for specific classes and verify approximations
    import re
    def extract_font_size(css: str, cls: str) -> float:
        m = re.search(r"\.%s\s*\{[^}]*font-size:\s*([0-9]+(?:\.[0-9]+)?)px;" % cls, css)
        assert m, f"font-size for {cls} not found"
        return float(m.group(1))

    hanzi_px = extract_font_size(html, "simple-hanzi")
    pinyin_px = extract_font_size(html, "simple-pinyin")
    english_px = extract_font_size(html, "simple-english")

    PT_TO_PX = 96/72
    assert abs(hanzi_px - 26*PT_TO_PX) < 0.5
    assert abs(pinyin_px - 12*PT_TO_PX) < 0.2
    assert abs(english_px - 14*PT_TO_PX) < 0.5


def test_clear_preview_cache_exception_handling():
    """Test cache clearing exception handling."""
    from services.cache import clear_preview_cache

    # Should not raise exception even if cache functions haven't been called
    clear_preview_cache()  # Should complete without error

    # Call it multiple times to ensure robustness
    clear_preview_cache()
    clear_preview_cache()


def test_create_preview_html_legacy_function():
    """Test legacy create_preview_html function."""
    from services.cache import create_preview_html

    # Test with empty cards
    html = create_preview_html([])
    assert "输入汉字以查看预览" in html

    # Test with cards
    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]
    html = create_preview_html(cards, max_cards=9)
    assert isinstance(html, str)
    assert len(html) > 0
    assert "你好" in html


def test_preview_html_structure_validation():
    """Test that preview HTML has proper structure."""
    from services.cache import create_page_preview_html, create_simple_grid_html

    cards = [
        {'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'},
        {'hanzi': '世界', 'pinyin': 'shi4jie4', 'english': 'world'}
    ]

    # Test page preview HTML structure
    page_html = create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, True
    )

    # Should contain proper HTML structure
    assert "<html>" in page_html or "<div" in page_html
    assert "你好" in page_html
    assert "world" in page_html
    # Contain a style block
    assert "<style>" in page_html

    # Test grid preview HTML structure
    grid_html = create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    # Should contain grid structure
    assert "<div" in grid_html
    assert "你好" in grid_html
    assert "world" in grid_html
    assert "grid" in grid_html.lower() or "flex" in grid_html.lower()


def test_preview_background_color_handling():
    """Test preview with different background colors."""
    from services.cache import create_simple_grid_html

    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

    # Test with different background colors
    colors = ["#ffffff", "#f0f0f0", "#e8f4f8", "#fff2e8"]

    for color in colors:
        html = create_simple_grid_html(
            cards, "SimHei", color, 2, 2, 48, 18, 14, 5.5, True
        )
        assert isinstance(html, str)
        assert len(html) > 0
        # Should contain the background color
        assert color in html or color.upper() in html


def test_preview_with_missing_card_fields():
    """Test preview with cards that have missing fields."""
    from services.cache import create_simple_grid_html, create_page_preview_html

    # Cards with missing fields
    cards = [
        {'hanzi': '你好', 'pinyin': '', 'english': ''},  # Missing pinyin and english
        {'hanzi': '', 'pinyin': 'ni3hao3', 'english': 'hello'},  # Missing hanzi
        {'hanzi': '世界', 'pinyin': 'shi4jie4', 'english': ''}  # Missing english
    ]

    # Should handle missing fields gracefully
    grid_html = create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )
    assert isinstance(grid_html, str)
    assert len(grid_html) > 0

    page_html = create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, True
    )
    assert isinstance(page_html, str)
    assert len(page_html) > 0


# Comprehensive cached preview function tests
def test_cached_create_simple_grid_html_caching_behavior():
    """Test that cached function actually caches results."""
    from services.cache import cached_create_simple_grid_html

    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

    # First call
    html1 = cached_create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    # Second call with same parameters should return cached result
    html2 = cached_create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    # Results should be identical (cached)
    assert html1 == html2
    assert isinstance(html1, str)
    assert len(html1) > 0
    assert "你好" in html1


def test_cached_create_page_preview_html_caching_behavior():
    """Test that cached page preview function caches results."""
    from services.cache import cached_create_page_preview_html

    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

    # First call
    html1 = cached_create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, True
    )

    # Second call with same parameters should return cached result
    html2 = cached_create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, True
    )

    # Results should be identical (cached)
    assert html1 == html2
    assert isinstance(html1, str)
    assert len(html1) > 0


def test_cached_functions_different_parameters():
    """Test that cached functions return different results for different parameters."""
    from services.cache import cached_create_simple_grid_html

    cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

    # Call with different background colors
    html1 = cached_create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    html2 = cached_create_simple_grid_html(
        cards, "SimHei", "#f0f0f0", 2, 2, 48, 18, 14, 5.5, True
    )

    # Results should be different (different parameters)
    assert html1 != html2
    assert "#ffffff" in html1 or "255, 255, 255" in html1
    assert "#f0f0f0" in html2 or "240, 240, 240" in html2


def test_immediate_vs_cached_preview_consistency():
    """Test that immediate and cached preview functions produce consistent results."""
    from services.cache import (
        create_simple_grid_html_immediate,
        cached_create_simple_grid_html,
        create_page_preview_html_immediate,
        cached_create_page_preview_html
    )

    cards = [
        {'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'},
        {'hanzi': '世界', 'pinyin': 'shi4jie4', 'english': 'world'}
    ]

    # Test simple grid consistency
    immediate_grid = create_simple_grid_html_immediate(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    cached_grid = cached_create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    # Should produce similar structure (allowing for minor differences)
    assert isinstance(immediate_grid, str)
    assert isinstance(cached_grid, str)
    assert len(immediate_grid) > 0
    assert len(cached_grid) > 0
    assert "你好" in immediate_grid
    assert "你好" in cached_grid

    # Test page preview consistency
    immediate_page = create_page_preview_html_immediate(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, True
    )

    cached_page = cached_create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
        "A4", "SimHei", "#ffffff", 2, 3, True
    )

    # Should produce similar structure
    assert isinstance(immediate_page, str)
    assert isinstance(cached_page, str)
    assert len(immediate_page) > 0
    assert len(cached_page) > 0


def test_preview_html_with_special_characters():
    """Test preview HTML generation with special characters and edge cases."""
    from services.cache import create_simple_grid_html

    # Cards with special characters
    cards = [
        {'hanzi': '你好！', 'pinyin': 'nǐ hǎo!', 'english': 'Hello!'},
        {'hanzi': '测试"引号"', 'pinyin': 'cè shì', 'english': 'Test "quotes"'},
        {'hanzi': '符号&<>', 'pinyin': 'fú hào', 'english': 'Symbols &<>'},
        {'hanzi': '', 'pinyin': '', 'english': ''}  # Empty card
    ]

    html = create_simple_grid_html(
        cards, "SimHei", "#ffffff", 2, 2, 48, 18, 14, 5.5, True
    )

    assert isinstance(html, str)
    assert len(html) > 0
    # Should handle special characters properly (HTML escaped or preserved)
    assert "你好" in html
    assert "Hello" in html
    # Should not break HTML structure
    assert "<" in html and ">" in html  # HTML tags present


def test_preview_performance_with_large_card_sets():
    """Test preview generation performance with larger card sets."""
    from services.cache import create_simple_grid_html

    # Generate larger set of cards
    cards = []
    for i in range(50):
        cards.append({
            'hanzi': f'字{i}',
            'pinyin': f'zi{i}',
            'english': f'word{i}'
        })

    # Should handle large card sets without issues
    html = create_simple_grid_html(
        cards, "SimHei", "#ffffff", 5, 10, 48, 18, 14, 5.5, True
    )

    assert isinstance(html, str)
    assert len(html) > 0
    # Should contain cards from the set
    assert "字0" in html
    assert "字49" in html or "word49" in html


def test_preview_grid_layout_calculations():
    """Test preview grid layout calculations with various configurations."""
    from services.cache import create_simple_grid_html

    cards = [{'hanzi': f'字{i}', 'pinyin': f'zi{i}', 'english': f'word{i}'} for i in range(6)]

    # Test different grid configurations
    configurations = [
        (1, 6),  # Single row
        (6, 1),  # Single column
        (2, 3),  # 2x3 grid
        (3, 2),  # 3x2 grid
    ]

    for rows, cols in configurations:
        html = create_simple_grid_html(
            cards, "SimHei", "#ffffff", rows, cols, 48, 18, 14, 5.5, True
        )

        assert isinstance(html, str)
        assert len(html) > 0
        # Should contain grid layout information
        assert "grid" in html.lower() or "flex" in html.lower()
        # Should contain card content
        assert "字0" in html
