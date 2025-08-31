"""
Compatibility Testing Matrix and Framework.
Tests compatibility across browser versions, Streamlit versions, and data formats.
"""

import pytest
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

from services.migration import migrate_user_data, detect_data_version
from core.feature_flags import get_feature_flag


class BrowserType(Enum):
    """Supported browser types."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


class CompatibilityLevel(Enum):
    """Compatibility support levels."""
    FULL = "full"          # Full feature support
    PARTIAL = "partial"    # Limited feature support
    MINIMAL = "minimal"    # Basic functionality only
    UNSUPPORTED = "unsupported"  # Not supported


@dataclass
class BrowserVersion:
    """Browser version specification."""
    type: BrowserType
    version: str
    release_date: str
    market_share: float = 0.0
    compatibility_level: CompatibilityLevel = CompatibilityLevel.FULL


@dataclass
class StreamlitVersion:
    """Streamlit version specification."""
    version: str
    release_date: str
    python_requirement: str
    compatibility_level: CompatibilityLevel = CompatibilityLevel.FULL
    known_issues: List[str] = field(default_factory=list)


@dataclass
class DataFormatVersion:
    """Data format version specification."""
    format_name: str
    version: str
    schema_file: Optional[str] = None
    migration_path: List[str] = field(default_factory=list)
    compatibility_level: CompatibilityLevel = CompatibilityLevel.FULL


@dataclass
class CompatibilityTestResult:
    """Result of compatibility test."""
    test_name: str
    browser_version: Optional[BrowserVersion] = None
    streamlit_version: Optional[StreamlitVersion] = None
    data_format: Optional[DataFormatVersion] = None
    success: bool = False
    compatibility_level: CompatibilityLevel = CompatibilityLevel.UNSUPPORTED
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    test_duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompatibilityMatrix:
    """Compatibility matrix for browser, Streamlit, and data format versions."""
    
    def __init__(self):
        self.browser_versions = self._define_browser_versions()
        self.streamlit_versions = self._define_streamlit_versions()
        self.data_formats = self._define_data_formats()
        
    def _define_browser_versions(self) -> List[BrowserVersion]:
        """Define supported browser versions."""
        return [
            # Chrome versions
            BrowserVersion(BrowserType.CHROME, "120.0", "2023-11-28", 65.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.CHROME, "119.0", "2023-10-31", 15.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.CHROME, "118.0", "2023-10-10", 10.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.CHROME, "110.0", "2023-02-07", 5.0, CompatibilityLevel.PARTIAL),
            BrowserVersion(BrowserType.CHROME, "100.0", "2022-03-29", 2.0, CompatibilityLevel.MINIMAL),
            
            # Firefox versions
            BrowserVersion(BrowserType.FIREFOX, "121.0", "2023-12-19", 8.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.FIREFOX, "120.0", "2023-11-21", 5.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.FIREFOX, "115.0", "2023-07-04", 3.0, CompatibilityLevel.PARTIAL),
            BrowserVersion(BrowserType.FIREFOX, "102.0", "2022-06-28", 1.0, CompatibilityLevel.MINIMAL),
            
            # Safari versions
            BrowserVersion(BrowserType.SAFARI, "17.0", "2023-09-18", 10.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.SAFARI, "16.0", "2022-09-12", 5.0, CompatibilityLevel.PARTIAL),
            BrowserVersion(BrowserType.SAFARI, "15.0", "2021-09-20", 2.0, CompatibilityLevel.MINIMAL),
            
            # Edge versions
            BrowserVersion(BrowserType.EDGE, "120.0", "2023-11-30", 5.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.EDGE, "119.0", "2023-11-02", 3.0, CompatibilityLevel.FULL),
            BrowserVersion(BrowserType.EDGE, "110.0", "2023-02-09", 2.0, CompatibilityLevel.PARTIAL),
        ]
    
    def _define_streamlit_versions(self) -> List[StreamlitVersion]:
        """Define supported Streamlit versions."""
        return [
            StreamlitVersion("1.29.0", "2023-11-16", ">=3.8", CompatibilityLevel.FULL),
            StreamlitVersion("1.28.0", "2023-10-26", ">=3.8", CompatibilityLevel.FULL),
            StreamlitVersion("1.27.0", "2023-09-21", ">=3.8", CompatibilityLevel.FULL),
            StreamlitVersion("1.26.0", "2023-08-24", ">=3.8", CompatibilityLevel.PARTIAL, 
                           ["Session state issues", "Component rendering delays"]),
            StreamlitVersion("1.25.0", "2023-07-13", ">=3.8", CompatibilityLevel.PARTIAL,
                           ["Cache invalidation bugs", "Memory leaks"]),
            StreamlitVersion("1.20.0", "2023-03-09", ">=3.7", CompatibilityLevel.MINIMAL,
                           ["Limited component support", "Performance issues"]),
            StreamlitVersion("1.15.0", "2022-10-27", ">=3.7", CompatibilityLevel.MINIMAL,
                           ["No session state", "Limited caching"]),
        ]
    
    def _define_data_formats(self) -> List[DataFormatVersion]:
        """Define supported data formats."""
        return [
            DataFormatVersion("snapshot", "3.0.0", "schemas/snapshot_v3.json", 
                            ["legacy", "1.0.0", "2.0.0"], CompatibilityLevel.FULL),
            DataFormatVersion("snapshot", "2.0.0", "schemas/snapshot_v2.json",
                            ["legacy", "1.0.0"], CompatibilityLevel.FULL),
            DataFormatVersion("snapshot", "1.0.0", "schemas/snapshot_v1.json",
                            ["legacy"], CompatibilityLevel.FULL),
            DataFormatVersion("legacy", "legacy", None, [], CompatibilityLevel.PARTIAL),
            DataFormatVersion("export", "pdf_v1", None, [], CompatibilityLevel.FULL),
            DataFormatVersion("export", "pptx_v1", None, [], CompatibilityLevel.FULL),
            DataFormatVersion("export", "csv_v1", None, [], CompatibilityLevel.FULL),
        ]
    
    def get_supported_browsers(self, min_compatibility: CompatibilityLevel = CompatibilityLevel.PARTIAL) -> List[BrowserVersion]:
        """Get browsers with minimum compatibility level."""
        return [
            browser for browser in self.browser_versions
            if self._compatibility_level_value(browser.compatibility_level) >= self._compatibility_level_value(min_compatibility)
        ]
    
    def get_supported_streamlit_versions(self, min_compatibility: CompatibilityLevel = CompatibilityLevel.PARTIAL) -> List[StreamlitVersion]:
        """Get Streamlit versions with minimum compatibility level."""
        return [
            version for version in self.streamlit_versions
            if self._compatibility_level_value(version.compatibility_level) >= self._compatibility_level_value(min_compatibility)
        ]
    
    def get_supported_data_formats(self, min_compatibility: CompatibilityLevel = CompatibilityLevel.PARTIAL) -> List[DataFormatVersion]:
        """Get data formats with minimum compatibility level."""
        return [
            format_ver for format_ver in self.data_formats
            if self._compatibility_level_value(format_ver.compatibility_level) >= self._compatibility_level_value(min_compatibility)
        ]
    
    def _compatibility_level_value(self, level: CompatibilityLevel) -> int:
        """Convert compatibility level to numeric value for comparison."""
        return {
            CompatibilityLevel.UNSUPPORTED: 0,
            CompatibilityLevel.MINIMAL: 1,
            CompatibilityLevel.PARTIAL: 2,
            CompatibilityLevel.FULL: 3
        }[level]
    
    def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate comprehensive compatibility report."""
        return {
            "browser_support": {
                "total_versions": len(self.browser_versions),
                "full_support": len([b for b in self.browser_versions if b.compatibility_level == CompatibilityLevel.FULL]),
                "partial_support": len([b for b in self.browser_versions if b.compatibility_level == CompatibilityLevel.PARTIAL]),
                "minimal_support": len([b for b in self.browser_versions if b.compatibility_level == CompatibilityLevel.MINIMAL]),
                "market_coverage": sum(b.market_share for b in self.browser_versions if b.compatibility_level != CompatibilityLevel.UNSUPPORTED)
            },
            "streamlit_support": {
                "total_versions": len(self.streamlit_versions),
                "full_support": len([s for s in self.streamlit_versions if s.compatibility_level == CompatibilityLevel.FULL]),
                "partial_support": len([s for s in self.streamlit_versions if s.compatibility_level == CompatibilityLevel.PARTIAL]),
                "minimal_support": len([s for s in self.streamlit_versions if s.compatibility_level == CompatibilityLevel.MINIMAL]),
                "known_issues_count": sum(len(s.known_issues) for s in self.streamlit_versions)
            },
            "data_format_support": {
                "total_formats": len(self.data_formats),
                "migration_paths": len([f for f in self.data_formats if f.migration_path]),
                "legacy_support": len([f for f in self.data_formats if "legacy" in f.version])
            }
        }


class CompatibilityTester:
    """Automated compatibility testing framework."""
    
    def __init__(self):
        self.matrix = CompatibilityMatrix()
        self.test_results: List[CompatibilityTestResult] = []
    
    def run_browser_compatibility_tests(self) -> List[CompatibilityTestResult]:
        """Run browser compatibility tests."""
        results = []
        
        for browser in self.matrix.browser_versions:
            result = self._test_browser_features(browser)
            results.append(result)
            self.test_results.append(result)
        
        return results
    
    def run_streamlit_compatibility_tests(self) -> List[CompatibilityTestResult]:
        """Run Streamlit version compatibility tests."""
        results = []
        
        for streamlit_version in self.matrix.streamlit_versions:
            result = self._test_streamlit_features(streamlit_version)
            results.append(result)
            self.test_results.append(result)
        
        return results
    
    def run_data_format_compatibility_tests(self) -> List[CompatibilityTestResult]:
        """Run data format compatibility tests."""
        results = []
        
        for data_format in self.matrix.data_formats:
            result = self._test_data_format_migration(data_format)
            results.append(result)
            self.test_results.append(result)
        
        return results
    
    def _test_browser_features(self, browser: BrowserVersion) -> CompatibilityTestResult:
        """Test browser-specific features."""
        import time
        start_time = time.time()
        
        issues = []
        warnings = []
        success = True
        
        try:
            # Test localStorage support
            if not self._test_local_storage_support(browser):
                issues.append("localStorage not supported")
                success = False
            
            # Test CSS Grid support
            if not self._test_css_grid_support(browser):
                warnings.append("CSS Grid support limited")
            
            # Test ES6 features
            if not self._test_es6_support(browser):
                if browser.compatibility_level == CompatibilityLevel.FULL:
                    issues.append("ES6 features not supported")
                    success = False
                else:
                    warnings.append("Limited ES6 support")
            
            # Test WebComponents support
            if not self._test_web_components_support(browser):
                warnings.append("WebComponents support limited")
            
        except Exception as e:
            issues.append(f"Browser test error: {e}")
            success = False
        
        duration_ms = (time.time() - start_time) * 1000
        
        return CompatibilityTestResult(
            test_name=f"browser_{browser.type.value}_{browser.version}",
            browser_version=browser,
            success=success,
            compatibility_level=browser.compatibility_level,
            issues=issues,
            warnings=warnings,
            test_duration_ms=duration_ms,
            metadata={
                "market_share": browser.market_share,
                "release_date": browser.release_date
            }
        )
    
    def _test_streamlit_features(self, streamlit_version: StreamlitVersion) -> CompatibilityTestResult:
        """Test Streamlit version-specific features."""
        import time
        start_time = time.time()
        
        issues = []
        warnings = []
        success = True
        
        try:
            # Test session state support
            if not self._test_session_state_support(streamlit_version):
                if streamlit_version.version >= "1.18.0":
                    issues.append("Session state not working properly")
                    success = False
                else:
                    warnings.append("Session state not available")
            
            # Test caching support
            if not self._test_caching_support(streamlit_version):
                issues.append("Caching not working properly")
                success = False
            
            # Test component rendering
            if not self._test_component_rendering(streamlit_version):
                warnings.append("Component rendering issues detected")
            
            # Add known issues
            if streamlit_version.known_issues:
                warnings.extend(streamlit_version.known_issues)
            
        except Exception as e:
            issues.append(f"Streamlit test error: {e}")
            success = False
        
        duration_ms = (time.time() - start_time) * 1000
        
        return CompatibilityTestResult(
            test_name=f"streamlit_{streamlit_version.version}",
            streamlit_version=streamlit_version,
            success=success,
            compatibility_level=streamlit_version.compatibility_level,
            issues=issues,
            warnings=warnings,
            test_duration_ms=duration_ms,
            metadata={
                "python_requirement": streamlit_version.python_requirement,
                "release_date": streamlit_version.release_date
            }
        )
    
    def _test_data_format_migration(self, data_format: DataFormatVersion) -> CompatibilityTestResult:
        """Test data format migration capabilities."""
        import time
        start_time = time.time()
        
        issues = []
        warnings = []
        success = True
        
        try:
            # Test migration path
            if data_format.migration_path:
                for source_version in data_format.migration_path:
                    if not self._test_migration_from_version(source_version, data_format.version):
                        issues.append(f"Migration from {source_version} to {data_format.version} failed")
                        success = False
            
            # Test data validation
            if not self._test_data_format_validation(data_format):
                issues.append("Data format validation failed")
                success = False
            
            # Test schema compliance
            if data_format.schema_file and not self._test_schema_compliance(data_format):
                warnings.append("Schema compliance issues detected")
            
        except Exception as e:
            issues.append(f"Data format test error: {e}")
            success = False
        
        duration_ms = (time.time() - start_time) * 1000
        
        return CompatibilityTestResult(
            test_name=f"data_format_{data_format.format_name}_{data_format.version}",
            data_format=data_format,
            success=success,
            compatibility_level=data_format.compatibility_level,
            issues=issues,
            warnings=warnings,
            test_duration_ms=duration_ms,
            metadata={
                "migration_path_length": len(data_format.migration_path),
                "has_schema": data_format.schema_file is not None
            }
        )
    
    # Browser feature test methods (simplified for demonstration)
    def _test_local_storage_support(self, browser: BrowserVersion) -> bool:
        """Test localStorage support."""
        # Simplified test - in real implementation would use browser automation
        unsupported_versions = [
            (BrowserType.CHROME, "100.0"),
            (BrowserType.FIREFOX, "102.0"),
            (BrowserType.SAFARI, "15.0")
        ]
        return (browser.type, browser.version) not in unsupported_versions
    
    def _test_css_grid_support(self, browser: BrowserVersion) -> bool:
        """Test CSS Grid support."""
        # Most modern browsers support CSS Grid
        return browser.compatibility_level != CompatibilityLevel.MINIMAL
    
    def _test_es6_support(self, browser: BrowserVersion) -> bool:
        """Test ES6 features support."""
        # ES6 support varies by browser version
        return browser.compatibility_level in [CompatibilityLevel.FULL, CompatibilityLevel.PARTIAL]
    
    def _test_web_components_support(self, browser: BrowserVersion) -> bool:
        """Test WebComponents support."""
        # WebComponents support is newer
        return browser.compatibility_level == CompatibilityLevel.FULL
    
    # Streamlit feature test methods
    def _test_session_state_support(self, streamlit_version: StreamlitVersion) -> bool:
        """Test session state support."""
        # Session state was added in Streamlit 0.84.0
        version_parts = streamlit_version.version.split('.')
        major, minor = int(version_parts[0]), int(version_parts[1])
        return major > 1 or (major == 1 and minor >= 18)
    
    def _test_caching_support(self, streamlit_version: StreamlitVersion) -> bool:
        """Test caching support."""
        # All tested versions should support some form of caching
        return streamlit_version.compatibility_level != CompatibilityLevel.UNSUPPORTED
    
    def _test_component_rendering(self, streamlit_version: StreamlitVersion) -> bool:
        """Test component rendering."""
        # Component rendering improved over time
        return "Component rendering" not in ' '.join(streamlit_version.known_issues)
    
    # Data format test methods
    def _test_migration_from_version(self, source_version: str, target_version: str) -> bool:
        """Test migration between versions."""
        try:
            # Create sample data for source version
            sample_data = self._create_sample_data(source_version)
            
            # Attempt migration
            result = migrate_user_data(sample_data, target_version)
            
            return result.success
        except Exception:
            return False
    
    def _test_data_format_validation(self, data_format: DataFormatVersion) -> bool:
        """Test data format validation."""
        try:
            # Create sample data
            sample_data = self._create_sample_data(data_format.version)
            
            # Test detection
            detected_format, detected_version = detect_data_version(sample_data)
            
            return detected_version == data_format.version
        except Exception:
            return False
    
    def _test_schema_compliance(self, data_format: DataFormatVersion) -> bool:
        """Test schema compliance."""
        # Simplified - would validate against actual schema files
        return data_format.schema_file is not None
    
    def _create_sample_data(self, version: str) -> Dict[str, Any]:
        """Create sample data for testing."""
        if version == "legacy":
            return {
                'cards': [
                    {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
                ]
            }
        elif version == "1.0.0":
            return {
                'format_version': '1.0.0',
                'cards': [
                    {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
                ]
            }
        elif version == "2.0.0":
            return {
                'format_version': '2.0.0',
                'metadata': {
                    'created_at': '2024-01-15T10:30:00Z',
                    'last_modified': '2024-01-15T10:30:00Z'
                },
                'cards': [
                    {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
                ]
            }
        elif version == "3.0.0":
            return {
                'format_version': '3.0.0',
                'metadata': {
                    'created_at': '2024-01-15T10:30:00Z',
                    'last_modified': '2024-01-15T10:30:00Z'
                },
                'cards': [
                    {
                        'id': 'test-uuid-123',
                        'version': 1,
                        'hanzi': '测试',
                        'pinyin': 'cè shì',
                        'english': 'test',
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                ],
                'export_history': []
            }
        else:
            return {}
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r.success])
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "average_duration_ms": sum(r.test_duration_ms for r in self.test_results) / total_tests if total_tests > 0 else 0
            },
            "by_category": {
                "browser_tests": len([r for r in self.test_results if r.browser_version]),
                "streamlit_tests": len([r for r in self.test_results if r.streamlit_version]),
                "data_format_tests": len([r for r in self.test_results if r.data_format])
            },
            "compatibility_levels": {
                "full": len([r for r in self.test_results if r.compatibility_level == CompatibilityLevel.FULL]),
                "partial": len([r for r in self.test_results if r.compatibility_level == CompatibilityLevel.PARTIAL]),
                "minimal": len([r for r in self.test_results if r.compatibility_level == CompatibilityLevel.MINIMAL]),
                "unsupported": len([r for r in self.test_results if r.compatibility_level == CompatibilityLevel.UNSUPPORTED])
            },
            "issues": {
                "total_issues": sum(len(r.issues) for r in self.test_results),
                "total_warnings": sum(len(r.warnings) for r in self.test_results),
                "failed_tests": [r.test_name for r in self.test_results if not r.success]
            }
        }


# Global instances
_compatibility_matrix: Optional[CompatibilityMatrix] = None
_compatibility_tester: Optional[CompatibilityTester] = None


def get_compatibility_matrix() -> CompatibilityMatrix:
    """Get global compatibility matrix instance."""
    global _compatibility_matrix
    if _compatibility_matrix is None:
        _compatibility_matrix = CompatibilityMatrix()
    return _compatibility_matrix


def get_compatibility_tester() -> CompatibilityTester:
    """Get global compatibility tester instance."""
    global _compatibility_tester
    if _compatibility_tester is None:
        _compatibility_tester = CompatibilityTester()
    return _compatibility_tester
