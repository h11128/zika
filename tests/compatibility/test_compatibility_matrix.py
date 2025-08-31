"""
Unit tests for compatibility testing framework.
Tests compatibility matrix, browser support, Streamlit versions, and data format compatibility.
"""

import pytest
from unittest.mock import patch, MagicMock

from tests.compatibility.compatibility_matrix import (
    BrowserType, CompatibilityLevel, BrowserVersion, StreamlitVersion, DataFormatVersion,
    CompatibilityTestResult, CompatibilityMatrix, CompatibilityTester,
    get_compatibility_matrix, get_compatibility_tester
)


class TestBrowserVersion:
    """Test browser version functionality."""
    
    def test_browser_version_creation(self):
        """Test browser version creation."""
        browser = BrowserVersion(
            type=BrowserType.CHROME,
            version="120.0",
            release_date="2023-11-28",
            market_share=65.0,
            compatibility_level=CompatibilityLevel.FULL
        )
        
        assert browser.type == BrowserType.CHROME
        assert browser.version == "120.0"
        assert browser.market_share == 65.0
        assert browser.compatibility_level == CompatibilityLevel.FULL


class TestStreamlitVersion:
    """Test Streamlit version functionality."""
    
    def test_streamlit_version_creation(self):
        """Test Streamlit version creation."""
        streamlit = StreamlitVersion(
            version="1.29.0",
            release_date="2023-11-16",
            python_requirement=">=3.8",
            compatibility_level=CompatibilityLevel.FULL,
            known_issues=["Minor issue"]
        )
        
        assert streamlit.version == "1.29.0"
        assert streamlit.python_requirement == ">=3.8"
        assert streamlit.compatibility_level == CompatibilityLevel.FULL
        assert len(streamlit.known_issues) == 1


class TestDataFormatVersion:
    """Test data format version functionality."""
    
    def test_data_format_version_creation(self):
        """Test data format version creation."""
        data_format = DataFormatVersion(
            format_name="snapshot",
            version="3.0.0",
            schema_file="schemas/snapshot_v3.json",
            migration_path=["legacy", "1.0.0", "2.0.0"],
            compatibility_level=CompatibilityLevel.FULL
        )
        
        assert data_format.format_name == "snapshot"
        assert data_format.version == "3.0.0"
        assert len(data_format.migration_path) == 3
        assert data_format.compatibility_level == CompatibilityLevel.FULL


class TestCompatibilityTestResult:
    """Test compatibility test result functionality."""
    
    def test_test_result_creation(self):
        """Test test result creation."""
        browser = BrowserVersion(BrowserType.CHROME, "120.0", "2023-11-28")
        
        result = CompatibilityTestResult(
            test_name="test_chrome_120",
            browser_version=browser,
            success=True,
            compatibility_level=CompatibilityLevel.FULL,
            issues=[],
            warnings=["Minor warning"],
            test_duration_ms=150.5
        )
        
        assert result.test_name == "test_chrome_120"
        assert result.browser_version == browser
        assert result.success is True
        assert result.compatibility_level == CompatibilityLevel.FULL
        assert len(result.warnings) == 1
        assert result.test_duration_ms == 150.5


class TestCompatibilityMatrix:
    """Test compatibility matrix functionality."""
    
    def test_matrix_creation(self):
        """Test compatibility matrix creation."""
        matrix = CompatibilityMatrix()
        
        assert len(matrix.browser_versions) > 0
        assert len(matrix.streamlit_versions) > 0
        assert len(matrix.data_formats) > 0
    
    def test_get_supported_browsers(self):
        """Test getting supported browsers."""
        matrix = CompatibilityMatrix()
        
        # Get browsers with full support
        full_support = matrix.get_supported_browsers(CompatibilityLevel.FULL)
        assert all(b.compatibility_level == CompatibilityLevel.FULL for b in full_support)
        
        # Get browsers with partial or better support
        partial_plus = matrix.get_supported_browsers(CompatibilityLevel.PARTIAL)
        assert all(b.compatibility_level in [CompatibilityLevel.FULL, CompatibilityLevel.PARTIAL] for b in partial_plus)
        assert len(partial_plus) >= len(full_support)
    
    def test_get_supported_streamlit_versions(self):
        """Test getting supported Streamlit versions."""
        matrix = CompatibilityMatrix()
        
        # Get versions with full support
        full_support = matrix.get_supported_streamlit_versions(CompatibilityLevel.FULL)
        assert all(s.compatibility_level == CompatibilityLevel.FULL for s in full_support)
        
        # Get versions with minimal or better support
        minimal_plus = matrix.get_supported_streamlit_versions(CompatibilityLevel.MINIMAL)
        assert len(minimal_plus) >= len(full_support)
    
    def test_get_supported_data_formats(self):
        """Test getting supported data formats."""
        matrix = CompatibilityMatrix()
        
        # Get formats with full support
        full_support = matrix.get_supported_data_formats(CompatibilityLevel.FULL)
        assert all(f.compatibility_level == CompatibilityLevel.FULL for f in full_support)
        
        # Get formats with partial or better support
        partial_plus = matrix.get_supported_data_formats(CompatibilityLevel.PARTIAL)
        assert len(partial_plus) >= len(full_support)
    
    def test_compatibility_level_value(self):
        """Test compatibility level value conversion."""
        matrix = CompatibilityMatrix()
        
        assert matrix._compatibility_level_value(CompatibilityLevel.UNSUPPORTED) == 0
        assert matrix._compatibility_level_value(CompatibilityLevel.MINIMAL) == 1
        assert matrix._compatibility_level_value(CompatibilityLevel.PARTIAL) == 2
        assert matrix._compatibility_level_value(CompatibilityLevel.FULL) == 3
    
    def test_generate_compatibility_report(self):
        """Test compatibility report generation."""
        matrix = CompatibilityMatrix()
        report = matrix.generate_compatibility_report()
        
        assert "browser_support" in report
        assert "streamlit_support" in report
        assert "data_format_support" in report
        
        # Verify browser support metrics
        browser_support = report["browser_support"]
        assert "total_versions" in browser_support
        assert "full_support" in browser_support
        assert "market_coverage" in browser_support
        assert browser_support["total_versions"] > 0
        
        # Verify Streamlit support metrics
        streamlit_support = report["streamlit_support"]
        assert "total_versions" in streamlit_support
        assert "known_issues_count" in streamlit_support
        assert streamlit_support["total_versions"] > 0
        
        # Verify data format support metrics
        data_format_support = report["data_format_support"]
        assert "total_formats" in data_format_support
        assert "migration_paths" in data_format_support
        assert data_format_support["total_formats"] > 0


class TestCompatibilityTester:
    """Test compatibility tester functionality."""
    
    def test_tester_creation(self):
        """Test compatibility tester creation."""
        tester = CompatibilityTester()
        
        assert tester.matrix is not None
        assert isinstance(tester.test_results, list)
        assert len(tester.test_results) == 0
    
    def test_browser_compatibility_tests(self):
        """Test browser compatibility testing."""
        tester = CompatibilityTester()
        results = tester.run_browser_compatibility_tests()
        
        assert len(results) > 0
        assert all(isinstance(r, CompatibilityTestResult) for r in results)
        assert all(r.browser_version is not None for r in results)
        assert all(r.test_duration_ms >= 0 for r in results)
        
        # Verify test results are stored
        assert len(tester.test_results) == len(results)
    
    def test_streamlit_compatibility_tests(self):
        """Test Streamlit compatibility testing."""
        tester = CompatibilityTester()
        results = tester.run_streamlit_compatibility_tests()
        
        assert len(results) > 0
        assert all(isinstance(r, CompatibilityTestResult) for r in results)
        assert all(r.streamlit_version is not None for r in results)
        assert all(r.test_duration_ms >= 0 for r in results)
    
    def test_data_format_compatibility_tests(self):
        """Test data format compatibility testing."""
        tester = CompatibilityTester()
        results = tester.run_data_format_compatibility_tests()
        
        assert len(results) > 0
        assert all(isinstance(r, CompatibilityTestResult) for r in results)
        assert all(r.data_format is not None for r in results)
        assert all(r.test_duration_ms >= 0 for r in results)
    
    def test_browser_feature_tests(self):
        """Test individual browser feature tests."""
        tester = CompatibilityTester()
        
        # Test with modern browser
        modern_browser = BrowserVersion(BrowserType.CHROME, "120.0", "2023-11-28", 
                                      compatibility_level=CompatibilityLevel.FULL)
        
        assert tester._test_local_storage_support(modern_browser) is True
        assert tester._test_css_grid_support(modern_browser) is True
        assert tester._test_es6_support(modern_browser) is True
        assert tester._test_web_components_support(modern_browser) is True
        
        # Test with older browser
        old_browser = BrowserVersion(BrowserType.CHROME, "100.0", "2022-03-29",
                                   compatibility_level=CompatibilityLevel.MINIMAL)
        
        assert tester._test_local_storage_support(old_browser) is False
        assert tester._test_css_grid_support(old_browser) is False
        assert tester._test_es6_support(old_browser) is False
        assert tester._test_web_components_support(old_browser) is False
    
    def test_streamlit_feature_tests(self):
        """Test individual Streamlit feature tests."""
        tester = CompatibilityTester()
        
        # Test with modern Streamlit
        modern_streamlit = StreamlitVersion("1.29.0", "2023-11-16", ">=3.8", 
                                          CompatibilityLevel.FULL)
        
        assert tester._test_session_state_support(modern_streamlit) is True
        assert tester._test_caching_support(modern_streamlit) is True
        assert tester._test_component_rendering(modern_streamlit) is True
        
        # Test with older Streamlit
        old_streamlit = StreamlitVersion("1.15.0", "2022-10-27", ">=3.7",
                                       CompatibilityLevel.MINIMAL,
                                       ["Component rendering delays"])
        
        assert tester._test_session_state_support(old_streamlit) is False
        assert tester._test_caching_support(old_streamlit) is True
        assert tester._test_component_rendering(old_streamlit) is False
    
    @patch('tests.compatibility.compatibility_matrix.migrate_user_data')
    def test_data_format_migration_tests(self, mock_migrate):
        """Test data format migration testing."""
        tester = CompatibilityTester()
        
        # Mock successful migration
        mock_result = MagicMock()
        mock_result.success = True
        mock_migrate.return_value = mock_result
        
        assert tester._test_migration_from_version("legacy", "3.0.0") is True
        mock_migrate.assert_called()
        
        # Mock failed migration
        mock_result.success = False
        mock_migrate.return_value = mock_result
        
        assert tester._test_migration_from_version("legacy", "3.0.0") is False
    
    @patch('tests.compatibility.compatibility_matrix.detect_data_version')
    def test_data_format_validation_tests(self, mock_detect):
        """Test data format validation testing."""
        tester = CompatibilityTester()
        
        # Mock successful detection
        mock_detect.return_value = (None, "3.0.0")
        
        data_format = DataFormatVersion("snapshot", "3.0.0")
        assert tester._test_data_format_validation(data_format) is True
        
        # Mock failed detection
        mock_detect.return_value = (None, "2.0.0")
        assert tester._test_data_format_validation(data_format) is False
    
    def test_sample_data_creation(self):
        """Test sample data creation for different versions."""
        tester = CompatibilityTester()
        
        # Test legacy data
        legacy_data = tester._create_sample_data("legacy")
        assert "cards" in legacy_data
        assert "format_version" not in legacy_data
        
        # Test v1 data
        v1_data = tester._create_sample_data("1.0.0")
        assert v1_data["format_version"] == "1.0.0"
        assert "cards" in v1_data
        
        # Test v2 data
        v2_data = tester._create_sample_data("2.0.0")
        assert v2_data["format_version"] == "2.0.0"
        assert "metadata" in v2_data
        
        # Test v3 data
        v3_data = tester._create_sample_data("3.0.0")
        assert v3_data["format_version"] == "3.0.0"
        assert "export_history" in v3_data
        assert "id" in v3_data["cards"][0]
    
    def test_generate_test_report(self):
        """Test test report generation."""
        tester = CompatibilityTester()
        
        # Add some mock test results
        tester.test_results = [
            CompatibilityTestResult("test1", success=True, test_duration_ms=100.0,
                                  compatibility_level=CompatibilityLevel.FULL),
            CompatibilityTestResult("test2", success=False, test_duration_ms=200.0,
                                  compatibility_level=CompatibilityLevel.PARTIAL,
                                  issues=["Test issue"]),
            CompatibilityTestResult("test3", success=True, test_duration_ms=150.0,
                                  compatibility_level=CompatibilityLevel.MINIMAL,
                                  warnings=["Test warning"])
        ]
        
        report = tester.generate_test_report()
        
        assert "summary" in report
        assert "by_category" in report
        assert "compatibility_levels" in report
        assert "issues" in report
        
        # Verify summary metrics
        summary = report["summary"]
        assert summary["total_tests"] == 3
        assert summary["successful_tests"] == 2
        assert summary["success_rate"] == 2/3
        assert summary["average_duration_ms"] == 150.0
        
        # Verify compatibility levels
        levels = report["compatibility_levels"]
        assert levels["full"] == 1
        assert levels["partial"] == 1
        assert levels["minimal"] == 1
        
        # Verify issues
        issues = report["issues"]
        assert issues["total_issues"] == 1
        assert issues["total_warnings"] == 1
        assert len(issues["failed_tests"]) == 1


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_compatibility_matrix(self):
        """Test get compatibility matrix function."""
        matrix1 = get_compatibility_matrix()
        matrix2 = get_compatibility_matrix()
        
        assert matrix1 is matrix2  # Should return same instance
        assert isinstance(matrix1, CompatibilityMatrix)
    
    def test_get_compatibility_tester(self):
        """Test get compatibility tester function."""
        tester1 = get_compatibility_tester()
        tester2 = get_compatibility_tester()
        
        assert tester1 is tester2  # Should return same instance
        assert isinstance(tester1, CompatibilityTester)


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_compatibility_test_suite(self):
        """Test running full compatibility test suite."""
        tester = CompatibilityTester()
        
        # Run all test categories
        browser_results = tester.run_browser_compatibility_tests()
        streamlit_results = tester.run_streamlit_compatibility_tests()
        data_format_results = tester.run_data_format_compatibility_tests()
        
        # Verify all tests ran
        assert len(browser_results) > 0
        assert len(streamlit_results) > 0
        assert len(data_format_results) > 0
        
        # Verify test results are accumulated
        total_expected = len(browser_results) + len(streamlit_results) + len(data_format_results)
        assert len(tester.test_results) == total_expected
        
        # Generate comprehensive report
        report = tester.generate_test_report()
        
        assert report["summary"]["total_tests"] == total_expected
        assert report["by_category"]["browser_tests"] == len(browser_results)
        assert report["by_category"]["streamlit_tests"] == len(streamlit_results)
        assert report["by_category"]["data_format_tests"] == len(data_format_results)
    
    def test_compatibility_matrix_integration(self):
        """Test compatibility matrix integration."""
        matrix = CompatibilityMatrix()
        tester = CompatibilityTester()
        
        # Verify tester uses matrix
        assert tester.matrix is not None
        
        # Verify matrix provides data for tests
        browsers = matrix.get_supported_browsers()
        streamlit_versions = matrix.get_supported_streamlit_versions()
        data_formats = matrix.get_supported_data_formats()
        
        assert len(browsers) > 0
        assert len(streamlit_versions) > 0
        assert len(data_formats) > 0
        
        # Generate matrix report
        matrix_report = matrix.generate_compatibility_report()
        
        # Run tests and generate test report
        tester.run_browser_compatibility_tests()
        test_report = tester.generate_test_report()
        
        # Verify reports are consistent
        assert matrix_report["browser_support"]["total_versions"] == test_report["by_category"]["browser_tests"]


if __name__ == "__main__":
    pytest.main([__file__])
