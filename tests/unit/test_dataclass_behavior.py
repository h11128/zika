"""
Unit tests for dataclass hash/equality behavior.
Tests that dataclasses used in the system have proper hash and equality semantics.
"""

import pytest
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any

# Import dataclasses to test
from services.preview_types import LayoutOptions, Typography, VisualOptions
from services.layout import PaginateInfo, LayoutMetrics, CardPosition
from services.persistence import UserSnapshot, ExportRecord


class TestLayoutOptionsDataclass:
    """Test LayoutOptions dataclass behavior."""
    
    def test_creation_and_basic_properties(self):
        """Test basic creation and property access."""
        layout = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        assert layout.layout_rows == 2
        assert layout.layout_cols == 3
        assert layout.layout_auto_fill is True
        assert layout.card_size_cm == 5.0
        assert layout.gap_cm == 0.5
        assert layout.margin_cm == 1.0
        assert layout.page_size == 'A4'
    
    def test_equality_same_values(self):
        """Test equality for same values."""
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout2 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        assert layout1 == layout2
        assert not (layout1 != layout2)
    
    def test_equality_different_values(self):
        """Test inequality for different values."""
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout2 = LayoutOptions(
            layout_rows=3, layout_cols=3, layout_auto_fill=True,  # Different rows
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        assert layout1 != layout2
        assert not (layout1 == layout2)
    
    def test_hash_consistency(self):
        """Test hash consistency."""
        layout = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        hash1 = hash(layout)
        hash2 = hash(layout)
        
        assert hash1 == hash2
    
    def test_hash_equality_contract(self):
        """Test that equal objects have equal hashes."""
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout2 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        assert layout1 == layout2
        assert hash(layout1) == hash(layout2)
    
    def test_float_precision_normalization(self):
        """Test that float precision is normalized for hashing."""
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.123456789, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout2 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.1235, gap_cm=0.5, margin_cm=1.0, page_size='A4'  # Rounded
        )
        
        # Should be equal due to rounding in __post_init__
        assert layout1 == layout2
        assert hash(layout1) == hash(layout2)
    
    def test_immutability(self):
        """Test that dataclass is frozen (immutable)."""
        layout = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        with pytest.raises(AttributeError):
            layout.layout_rows = 3  # Should fail - frozen dataclass


class TestTypographyDataclass:
    """Test Typography dataclass behavior."""
    
    def test_creation_and_validation(self):
        """Test creation and validation."""
        typo = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )

        assert typo.hanzi_font_size_pt == 48
        assert typo.pinyin_font_size_pt == 18
        assert typo.english_font_size_pt == 14
        assert typo.hanzi_font_family == 'SimHei'
    
    def test_validation_errors(self):
        """Test validation errors."""
        # Negative font sizes should raise ValueError
        with pytest.raises(ValueError):
            Typography(
                hanzi_font_size_pt=-1, pinyin_font_size_pt=18, english_font_size_pt=14,
                hanzi_font_family='SimHei'
            )

        # Empty font family should raise ValueError
        with pytest.raises(ValueError):
            Typography(
                hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
                hanzi_font_family=''
            )
    
    def test_equality_and_hashing(self):
        """Test equality and hashing."""
        typo1 = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )
        typo2 = Typography(
            hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
            hanzi_font_family='SimHei'
        )

        assert typo1 == typo2
        assert hash(typo1) == hash(typo2)


class TestVisualOptionsDataclass:
    """Test VisualOptions dataclass behavior."""
    
    def test_creation_and_properties(self):
        """Test creation and property access."""
        visual = VisualOptions(
            background_color='#FFFFFF',
            preview_mode='📄 完整页面'
        )

        assert visual.background_color == '#FFFFFF'
        assert visual.preview_mode == '📄 完整页面'

    def test_equality_and_hashing(self):
        """Test equality and hashing."""
        visual1 = VisualOptions(
            background_color='#FFFFFF',
            preview_mode='📄 完整页面'
        )
        visual2 = VisualOptions(
            background_color='#FFFFFF',
            preview_mode='📄 完整页面'
        )

        assert visual1 == visual2
        assert hash(visual1) == hash(visual2)


class TestPaginateInfoDataclass:
    """Test PaginateInfo dataclass behavior."""
    
    def test_creation_and_properties(self):
        """Test creation and property access."""
        paginate = PaginateInfo(cards_per_page=6, total_pages=3)
        
        assert paginate.cards_per_page == 6
        assert paginate.total_pages == 3
    
    def test_equality_and_hashing(self):
        """Test equality and hashing."""
        paginate1 = PaginateInfo(cards_per_page=6, total_pages=3)
        paginate2 = PaginateInfo(cards_per_page=6, total_pages=3)
        
        assert paginate1 == paginate2
        assert hash(paginate1) == hash(paginate2)
    
    def test_immutability(self):
        """Test immutability."""
        paginate = PaginateInfo(cards_per_page=6, total_pages=3)
        
        with pytest.raises(AttributeError):
            paginate.cards_per_page = 9


class TestLayoutMetricsDataclass:
    """Test LayoutMetrics dataclass behavior."""
    
    def test_creation_with_defaults(self):
        """Test creation with default scale_factor."""
        metrics = LayoutMetrics(
            card_size_cm=5.0, grid_width_cm=20.0, grid_height_cm=28.0, fits_on_page=True
        )
        
        assert metrics.card_size_cm == 5.0
        assert metrics.grid_width_cm == 20.0
        assert metrics.grid_height_cm == 28.0
        assert metrics.fits_on_page is True
        assert metrics.scale_factor == 1.0  # Default value
    
    def test_creation_with_custom_scale(self):
        """Test creation with custom scale_factor."""
        metrics = LayoutMetrics(
            card_size_cm=5.0, grid_width_cm=20.0, grid_height_cm=28.0, 
            fits_on_page=False, scale_factor=0.8
        )
        
        assert metrics.scale_factor == 0.8
        assert metrics.fits_on_page is False


class TestCardPositionDataclass:
    """Test CardPosition dataclass behavior."""
    
    def test_creation_and_properties(self):
        """Test creation and property access."""
        position = CardPosition(row=1, col=2, x_cm=5.5, y_cm=8.3)
        
        assert position.row == 1
        assert position.col == 2
        assert position.x_cm == 5.5
        assert position.y_cm == 8.3
    
    def test_equality_and_hashing(self):
        """Test equality and hashing."""
        pos1 = CardPosition(row=1, col=2, x_cm=5.5, y_cm=8.3)
        pos2 = CardPosition(row=1, col=2, x_cm=5.5, y_cm=8.3)
        
        assert pos1 == pos2
        assert hash(pos1) == hash(pos2)


class TestUserSnapshotDataclass:
    """Test UserSnapshot dataclass behavior."""
    
    def test_creation_with_defaults(self):
        """Test creation with default values."""
        snapshot = UserSnapshot(
            version=3,
            created_at='2025-01-01T00:00:00Z',
            last_modified='2025-01-01T00:00:00Z',
            input_text="",
            cards=[],
            options={},
            layout={},
            typography={},
            visual={},
            preview={},
            export_history=[]
        )

        assert snapshot.version == 3
        assert snapshot.created_at == '2025-01-01T00:00:00Z'
        assert snapshot.cards == []
        assert snapshot.options == {}
        assert snapshot.layout == {}
        assert snapshot.export_history == []
        assert snapshot.total_cards_generated == 0  # Default

    def test_equality_behavior(self):
        """Test equality behavior (UserSnapshot is not hashable)."""
        # Use same session_id for both to ensure equality
        session_id = "test-session-id"

        snapshot1 = UserSnapshot(
            version=3,
            created_at='2025-01-01T00:00:00Z',
            last_modified='2025-01-01T00:00:00Z',
            input_text="test",
            cards=[{'hanzi': '你好'}],
            options={'auto_pinyin': True},
            layout={'layout_rows': 2},
            typography={'hanzi_font_size_pt': 48},
            visual={'background_color': '#ffffff'},
            preview={'preview_mode': '📄 完整页面'},
            export_history=[],
            session_id=session_id
        )
        snapshot2 = UserSnapshot(
            version=3,
            created_at='2025-01-01T00:00:00Z',
            last_modified='2025-01-01T00:00:00Z',
            input_text="test",
            cards=[{'hanzi': '你好'}],
            options={'auto_pinyin': True},
            layout={'layout_rows': 2},
            typography={'hanzi_font_size_pt': 48},
            visual={'background_color': '#ffffff'},
            preview={'preview_mode': '📄 完整页面'},
            export_history=[],
            session_id=session_id
        )

        # Test equality
        assert snapshot1 == snapshot2

        # UserSnapshot is not frozen, so it's not hashable
        with pytest.raises(TypeError):
            hash(snapshot1)


class TestExportRecordDataclass:
    """Test ExportRecord dataclass behavior."""
    
    def test_creation_and_properties(self):
        """Test creation and property access."""
        record = ExportRecord(
            timestamp='2025-01-01T00:00:00Z',
            format_type='pdf',
            card_count=10,
            filename='cards.pdf'
        )

        assert record.timestamp == '2025-01-01T00:00:00Z'
        assert record.format_type == 'pdf'
        assert record.card_count == 10
        assert record.filename == 'cards.pdf'

    def test_equality_behavior(self):
        """Test equality behavior (ExportRecord is not frozen)."""
        record1 = ExportRecord(
            timestamp='2025-01-01T00:00:00Z',
            format_type='pdf',
            card_count=10,
            filename='cards.pdf'
        )
        record2 = ExportRecord(
            timestamp='2025-01-01T00:00:00Z',
            format_type='pdf',
            card_count=10,
            filename='cards.pdf'
        )

        # Test equality
        assert record1 == record2

        # ExportRecord is not frozen, so it's not hashable
        with pytest.raises(TypeError):
            hash(record1)


class TestDataclassHashingInCollections:
    """Test dataclass behavior in collections (sets, dicts)."""
    
    def test_dataclass_as_dict_key(self):
        """Test using dataclass as dictionary key."""
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout2 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        cache = {layout1: 'cached_result'}
        
        # Should be able to retrieve using equivalent object
        assert cache[layout2] == 'cached_result'
    
    def test_dataclass_in_set(self):
        """Test dataclass behavior in sets."""
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout2 = LayoutOptions(
            layout_rows=2, layout_cols=3, layout_auto_fill=True,
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        layout3 = LayoutOptions(
            layout_rows=3, layout_cols=3, layout_auto_fill=True,  # Different
            card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
        )
        
        layout_set = {layout1, layout2, layout3}
        
        # Should only have 2 unique items (layout1 == layout2)
        assert len(layout_set) == 2
        assert layout1 in layout_set
        assert layout2 in layout_set
        assert layout3 in layout_set
    
    def test_hash_stability_across_instances(self):
        """Test that hash is stable across different instances."""
        # Create multiple instances with same values
        layouts = []
        for _ in range(5):
            layout = LayoutOptions(
                layout_rows=2, layout_cols=3, layout_auto_fill=True,
                card_size_cm=5.0, gap_cm=0.5, margin_cm=1.0, page_size='A4'
            )
            layouts.append(layout)
        
        # All should have the same hash
        hashes = [hash(layout) for layout in layouts]
        assert all(h == hashes[0] for h in hashes)
        
        # All should be equal
        for i in range(len(layouts)):
            for j in range(i + 1, len(layouts)):
                assert layouts[i] == layouts[j]


if __name__ == "__main__":
    pytest.main([__file__])
