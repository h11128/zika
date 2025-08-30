"""
Unit tests for core.version module.
Tests code version generation and environment detection.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from core.version import (
    get_code_version, 
    get_version_info,
    clear_version_cache,
    _detect_environment,
    _get_git_sha,
    _is_git_dirty,
    _get_production_version,
    _get_ci_version,
    _get_development_version
)


class TestEnvironmentDetection:
    """Test environment detection logic."""
    
    def test_detect_ci_environment(self):
        """Test CI environment detection."""
        with patch.dict(os.environ, {'CI': 'true'}, clear=True):
            assert _detect_environment() == 'ci'
        
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}, clear=True):
            assert _detect_environment() == 'ci'
        
        with patch.dict(os.environ, {'BUILD_NUMBER': '123'}, clear=True):
            assert _detect_environment() == 'ci'
    
    def test_detect_production_environment(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            assert _detect_environment() == 'production'
        
        with patch.dict(os.environ, {'NODE_ENV': 'production'}, clear=True):
            assert _detect_environment() == 'production'
    
    def test_detect_development_environment(self):
        """Test development environment detection (default)."""
        with patch.dict(os.environ, {}, clear=True):
            assert _detect_environment() == 'development'


class TestVersionGeneration:
    """Test version generation for different environments."""
    
    def setup_method(self):
        """Clear version cache before each test."""
        clear_version_cache()
    
    def test_override_version(self):
        """Test version override via environment variable."""
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'test-override'}, clear=True):
            clear_version_cache()
            assert get_code_version() == 'test-override'
    
    def test_production_version_with_semver(self):
        """Test production version with semantic version."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'RELEASE_VERSION': 'v2.1.0'
        }, clear=True):
            clear_version_cache()
            version = get_code_version()
            assert version == 'v2.1.0'
    
    def test_production_version_with_build_number(self):
        """Test production version with build number."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'VERSION': '2.1.0',
            'BUILD_NUMBER': '456'
        }, clear=True):
            clear_version_cache()
            version = get_code_version()
            assert version == 'v2.1.0+build.456'
    
    def test_ci_version_with_build_number(self):
        """Test CI version with build number."""
        with patch.dict(os.environ, {
            'CI': 'true',
            'BUILD_NUMBER': '123'
        }, clear=True):
            with patch('core.version._get_git_sha', return_value='abc1234'):
                clear_version_cache()
                version = get_code_version()
                assert version == 'ci-123-abc1234'
    
    def test_ci_version_fallback_to_sha(self):
        """Test CI version fallback to SHA when no build number."""
        with patch.dict(os.environ, {'CI': 'true'}, clear=True):
            with patch('core.version._get_git_sha', return_value='abc1234'):
                clear_version_cache()
                version = get_code_version()
                assert version == 'abc1234'
    
    @patch('core.version.datetime')
    def test_development_version_clean(self, mock_datetime):
        """Test development version with clean git tree."""
        mock_datetime.now.return_value.strftime.return_value = '20250830120000'
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.version._get_git_sha', return_value='abc1234'):
                with patch('core.version._is_git_dirty', return_value=False):
                    clear_version_cache()
                    version = get_code_version()
                    assert version == 'dev-abc1234-20250830120000'
    
    @patch('core.version.datetime')
    def test_development_version_dirty(self, mock_datetime):
        """Test development version with dirty git tree."""
        mock_datetime.now.return_value.strftime.return_value = '20250830120000'
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.version._get_git_sha', return_value='abc1234'):
                with patch('core.version._is_git_dirty', return_value=True):
                    clear_version_cache()
                    version = get_code_version()
                    assert version == 'dev-abc1234-20250830120000-dirty'
    
    @patch('core.version.datetime')
    def test_development_version_no_git(self, mock_datetime):
        """Test development version without git."""
        mock_datetime.now.return_value.strftime.return_value = '20250830120000'
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.version._get_git_sha', return_value=None):
                clear_version_cache()
                version = get_code_version()
                assert version == 'dev-nogit-20250830120000'


class TestGitIntegration:
    """Test git integration functions."""
    
    @patch('core.version.subprocess.run')
    def test_get_git_sha_success(self, mock_run):
        """Test successful git SHA retrieval."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'abc1234\n'
        
        result = _get_git_sha()
        assert result == 'abc1234'
        
        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'git' in args
        assert 'rev-parse' in args
        assert '--short' in args
        assert 'HEAD' in args
    
    @patch('core.version.subprocess.run')
    def test_get_git_sha_failure(self, mock_run):
        """Test git SHA retrieval failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = 'not a git repository'
        
        result = _get_git_sha()
        assert result is None
    
    @patch('core.version.subprocess.run')
    def test_is_git_dirty_clean(self, mock_run):
        """Test git dirty check with clean tree."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ''
        
        result = _is_git_dirty()
        assert result is False
    
    @patch('core.version.subprocess.run')
    def test_is_git_dirty_dirty(self, mock_run):
        """Test git dirty check with dirty tree."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ' M file.py\n?? new_file.py\n'
        
        result = _is_git_dirty()
        assert result is True


class TestVersionInfo:
    """Test version info function."""
    
    def test_get_version_info_structure(self):
        """Test version info returns expected structure."""
        with patch('core.version.get_code_version', return_value='test-version'):
            info = get_version_info()
            
            expected_keys = {
                'code_version', 'environment', 'git_sha', 'git_sha_short',
                'git_dirty', 'git_version', 'build_number', 'timestamp'
            }
            
            assert set(info.keys()) == expected_keys
            assert info['code_version'] == 'test-version'
            assert isinstance(info['timestamp'], str)


class TestVersionCaching:
    """Test version caching behavior."""
    
    def test_version_is_cached(self):
        """Test that version is cached and consistent."""
        clear_version_cache()
        
        with patch('core.version._detect_environment', return_value='development') as mock_detect:
            with patch('core.version._get_development_version', return_value='test-dev-version') as mock_dev:
                # First call
                version1 = get_code_version()
                # Second call
                version2 = get_code_version()
                
                # Should be the same
                assert version1 == version2
                assert version1 == 'test-dev-version'
                
                # Environment detection should only be called once due to caching
                assert mock_detect.call_count == 1
                assert mock_dev.call_count == 1
    
    def test_cache_clear(self):
        """Test cache clearing functionality."""
        clear_version_cache()
        
        with patch('core.version._get_development_version', side_effect=['version1', 'version2']):
            # First call
            version1 = get_code_version()
            assert version1 == 'version1'
            
            # Clear cache
            clear_version_cache()
            
            # Second call should get new version
            version2 = get_code_version()
            assert version2 == 'version2'
