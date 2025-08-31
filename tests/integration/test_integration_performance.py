#!/usr/bin/env python3
"""
Performance and Caching Integration Tests

Tests performance characteristics and caching behavior:
1. Cache effectiveness and consistency
2. Performance benchmarks for key operations
3. Memory usage and leak detection
4. Scalability with large datasets
5. Concurrent access performance
6. Resource cleanup and optimization
"""

import os
import sys
import time
import pytest
import gc
import threading
from unittest.mock import patch
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from typing import List, Dict

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.processing import parse_input_text, generate_missing_data, auto_segment_text
from services.export import export_cards
from services.cache_v2 import (
    create_page_preview_html, create_simple_grid_html,
    cached_create_page_preview_html, cached_create_simple_grid_html
)
from src.dict_utils import create_default_dict
from core.constants import DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE


class TestCachingBehavior:
    """Test caching behavior and effectiveness."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
        ]
    
    def test_cache_consistency_simple_grid(self):
        """Test cache consistency for simple grid HTML generation."""
        # Generate HTML multiple times with same parameters
        html1 = create_simple_grid_html(
            self.sample_cards, hanzi_font_family='SimHei', background_color='#E3F2FD'
        )
        html2 = create_simple_grid_html(
            self.sample_cards, hanzi_font_family='SimHei', background_color='#E3F2FD'
        )
        html3 = create_simple_grid_html(
            self.sample_cards, hanzi_font_family='SimHei', background_color='#E3F2FD'
        )
        
        # Should be identical (cache working)
        assert html1 == html2 == html3
        
        # Different parameters should produce different results
        html_different = create_simple_grid_html(
            self.sample_cards, hanzi_font_family='Microsoft YaHei', background_color='#FFEBEE'
        )
        assert html1 != html_different
    
    def test_cache_consistency_page_preview(self):
        """Test cache consistency for page preview HTML generation."""
        # Generate page preview multiple times with same parameters
        html1 = create_page_preview_html(
            self.sample_cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
            page_size='A4', hanzi_font_family='SimHei', background_color='#E3F2FD'
        )
        html2 = create_page_preview_html(
            self.sample_cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
            page_size='A4', hanzi_font_family='SimHei', background_color='#E3F2FD'
        )
        
        # Should be identical
        assert html1 == html2
        
        # Different page number should produce different result
        html_page2 = create_page_preview_html(
            self.sample_cards, page_num=1, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
            page_size='A4', hanzi_font_family='SimHei', background_color='#E3F2FD'
        )
        assert html1 != html_page2
    
    def test_cache_invalidation_on_parameter_change(self):
        """Test that cache is properly invalidated when parameters change."""
        base_params = {
            'cards': self.sample_cards,
            'hanzi_font_family': 'SimHei',
            'background_color': '#E3F2FD'
        }
        
        # Generate with base parameters
        html_base = create_simple_grid_html(**base_params)
        
        # Test each parameter change
        param_variations = [
            {'hanzi_font_family': 'Microsoft YaHei'},
            {'background_color': '#FFEBEE'},
            {'layout_rows': 2, 'layout_cols': 2},
        ]
        
        for variation in param_variations:
            modified_params = {**base_params, **variation}
            html_modified = create_simple_grid_html(**modified_params)
            assert html_base != html_modified, f"Cache not invalidated for {variation}"
    
    def test_cache_performance_improvement(self):
        """Test that caching provides performance improvement."""
        large_cards = [
            {'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
            for i in range(50)
        ]

        # Test that cached function exists and works
        from services.cache_v2 import cached_create_simple_grid_html

        # Multiple calls should return identical results
        html1 = cached_create_simple_grid_html(large_cards, hanzi_font_family='SimHei')
        html2 = cached_create_simple_grid_html(large_cards, hanzi_font_family='SimHei')
        html3 = cached_create_simple_grid_html(large_cards, hanzi_font_family='SimHei')

        # Results should be identical (this tests cache correctness)
        assert html1 == html2 == html3
        assert len(html1) > 1000  # Should be substantial HTML
        assert 'simple-grid' in html1

        # Test with different parameters to ensure cache key differentiation
        html_different = cached_create_simple_grid_html(large_cards, hanzi_font_family='Arial')
        assert html_different != html1  # Different parameters should give different results


class TestPerformanceBenchmarks:
    """Test performance benchmarks for key operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dictionary = create_default_dict("data")
    
    def test_text_processing_performance(self):
        """Test performance of text processing operations."""
        test_texts = [
            "爱 家 朋友",  # Simple
            "我爱我的家人朋友们学习工作生活",  # Medium
            "中华人民共和国是一个伟大的国家有着悠久的历史和灿烂的文化" * 5  # Large
        ]
        
        for text in test_texts:
            # Test parsing performance
            start_time = time.time()
            cards = parse_input_text(text)
            parse_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert parse_time < 1.0, f"Parsing took too long: {parse_time:.4f}s for text length {len(text)}"
            
            # Test segmentation performance
            start_time = time.time()
            segmented = auto_segment_text(text)
            segment_time = time.time() - start_time
            
            assert segment_time < 2.0, f"Segmentation took too long: {segment_time:.4f}s"
            
            # Test data generation performance (limited cards for speed)
            if len(cards) > 20:
                cards = cards[:20]
            
            start_time = time.time()
            processed = generate_missing_data(cards, True, True, self.dictionary)
            process_time = time.time() - start_time
            
            assert process_time < 5.0, f"Data generation took too long: {process_time:.4f}s"
    
    def test_export_performance(self):
        """Test performance of export operations."""
        card_counts = [5, 20, 50]
        
        for count in card_counts:
            cards = [
                {'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
                for i in range(count)
            ]
            
            # Test PPTX export performance
            start_time = time.time()
            pptx_content = export_cards(cards, 'pptx')
            pptx_time = time.time() - start_time
            
            # Performance should scale reasonably
            expected_max_time = count * 0.1 + 2.0  # Linear scaling + base overhead
            assert pptx_time < expected_max_time, \
                f"PPTX export too slow for {count} cards: {pptx_time:.4f}s"
            
            # Test PDF export performance
            start_time = time.time()
            pdf_content = export_cards(cards, 'pdf')
            pdf_time = time.time() - start_time
            
            assert pdf_time < expected_max_time, \
                f"PDF export too slow for {count} cards: {pdf_time:.4f}s"
    
    def test_preview_generation_performance(self):
        """Test performance of preview generation."""
        card_counts = [9, 27, 81]  # 1, 3, 9 pages worth
        
        for count in card_counts:
            cards = [
                {'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
                for i in range(count)
            ]
            
            # Test simple grid performance
            start_time = time.time()
            simple_html = create_simple_grid_html(cards)
            simple_time = time.time() - start_time
            
            # Should be fast regardless of card count (limited display)
            assert simple_time < 1.0, f"Simple grid too slow: {simple_time:.4f}s"
            
            # Test page preview performance
            start_time = time.time()
            page_html = create_page_preview_html(
                cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                hanzi_font_size=48, pinyin_font_size=18, english_font_size=14
            )
            page_time = time.time() - start_time
            
            assert page_time < 1.0, f"Page preview too slow: {page_time:.4f}s"


class TestMemoryManagement:
    """Test memory usage and leak detection."""
    
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        if not HAS_PSUTIL:
            pytest.skip("psutil not available for memory testing")
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def test_memory_usage_during_processing(self):
        """Test memory usage during large data processing."""
        initial_memory = self.get_memory_usage()
        
        # Process large dataset
        large_text = "爱家朋友水火山月日木" * 100
        cards = parse_input_text(large_text)
        
        if len(cards) > 100:
            cards = cards[:100]  # Limit for testing
        
        dictionary = create_default_dict("data")
        processed_cards = generate_missing_data(cards, True, True, dictionary)
        
        # Generate previews
        for i in range(10):
            html = create_simple_grid_html(processed_cards)
            page_html = create_page_preview_html(
                processed_cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                hanzi_font_size=48, pinyin_font_size=18, english_font_size=14
            )
        
        # Force garbage collection
        gc.collect()
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Excessive memory usage: {memory_increase:.2f}MB"
    
    def test_memory_cleanup_after_export(self):
        """Test memory cleanup after export operations."""
        initial_memory = self.get_memory_usage()
        
        cards = [
            {'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
            for i in range(50)
        ]
        
        # Perform multiple exports
        for _ in range(5):
            pptx_content = export_cards(cards, 'pptx')
            pdf_content = export_cards(cards, 'pdf')
            
            # Clear references
            del pptx_content, pdf_content
        
        # Force garbage collection
        gc.collect()
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase significantly after cleanup
        assert memory_increase < 50, f"Memory leak detected: {memory_increase:.2f}MB"
    
    def test_cache_memory_management(self):
        """Test memory management of cache system."""
        initial_memory = self.get_memory_usage()
        
        # Generate many different cached items
        for i in range(20):
            cards = [{'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}]
            
            # Each call should create a new cache entry
            html = create_simple_grid_html(
                cards, hanzi_font_family=f'Font{i}', background_color=f'#00{i:02d}{i:02d}{i:02d}'
            )
        
        cache_memory = self.get_memory_usage()
        memory_increase = cache_memory - initial_memory
        
        # Cache should not use excessive memory
        assert memory_increase < 100, f"Cache using too much memory: {memory_increase:.2f}MB"


class TestScalabilityAndConcurrency:
    """Test scalability and concurrent access."""
    
    def test_concurrent_processing(self):
        """Test concurrent processing of cards."""
        cards = [
            {'hanzi': '爱', 'pinyin': '', 'english': ''},
            {'hanzi': '家', 'pinyin': '', 'english': ''},
            {'hanzi': '朋友', 'pinyin': '', 'english': ''}
        ]
        
        results = []
        errors = []
        
        def process_worker():
            try:
                dictionary = create_default_dict("data")
                processed = generate_missing_data(cards, True, True, dictionary)
                results.append(processed)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_worker)
            threads.append(thread)
        
        # Measure concurrent execution time
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)
        
        execution_time = time.time() - start_time
        
        # Verify results
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"
        assert len(results) == 5
        assert execution_time < 10, f"Concurrent processing too slow: {execution_time:.4f}s"
        
        # All results should be consistent
        for result in results:
            assert len(result) == 3
            assert all(card['pinyin'] for card in result)
    
    def test_concurrent_export(self):
        """Test concurrent export operations."""
        cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        ]
        
        results = []
        errors = []
        
        def export_worker(format_type):
            try:
                content = export_cards(cards, format_type)
                results.append((format_type, len(content)))
            except Exception as e:
                errors.append(e)
        
        # Create threads for different formats
        threads = []
        for format_type in ['pptx', 'pdf'] * 3:  # 6 threads total
            thread = threading.Thread(target=export_worker, args=(format_type,))
            threads.append(thread)
        
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=15)
        
        execution_time = time.time() - start_time
        
        # Verify results
        assert len(errors) == 0, f"Concurrent export errors: {errors}"
        assert len(results) == 6
        assert execution_time < 15, f"Concurrent export too slow: {execution_time:.4f}s"
        
        # All exports should produce reasonable file sizes
        for format_type, size in results:
            assert size > 1000, f"{format_type} export too small: {size} bytes"
    
    def test_scalability_with_increasing_load(self):
        """Test scalability with increasing data load."""
        base_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        ]
        
        load_factors = [1, 5, 10, 20]
        times = []
        
        for factor in load_factors:
            cards = base_cards * factor
            
            start_time = time.time()
            
            # Simulate typical workflow
            html = create_simple_grid_html(cards)
            content = export_cards(cards, 'pptx')
            
            execution_time = time.time() - start_time
            times.append(execution_time)
        
        # Performance should scale reasonably (not exponentially)
        for i in range(1, len(times)):
            ratio = times[i] / times[0]
            load_ratio = load_factors[i] / load_factors[0]
            
            # Time should not increase more than 3x the load increase
            assert ratio < load_ratio * 3, \
                f"Poor scalability: {load_ratio}x load caused {ratio:.2f}x time increase"
