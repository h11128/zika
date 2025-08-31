"""
Security tests for dependency vulnerability scanning and validation.
Tests dependency security, version validation, and supply chain security.
"""

import pytest
import sys
import os
import json
import subprocess
import pkg_resources
from unittest.mock import MagicMock, patch, mock_open

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class DependencyScanner:
    """Scanner for dependency vulnerabilities."""
    
    def __init__(self):
        self.known_vulnerabilities = {
            # Example known vulnerabilities (would be loaded from security database)
            'requests': {
                '2.25.0': ['CVE-2021-33503'],
                '2.24.0': ['CVE-2021-33503'],
            },
            'pillow': {
                '8.1.0': ['CVE-2021-25287', 'CVE-2021-25288'],
                '8.0.0': ['CVE-2021-25287'],
            },
            'streamlit': {
                '1.0.0': ['CVE-2021-example'],  # Example
            }
        }
        
        self.security_policies = {
            'min_versions': {
                'requests': '2.26.0',
                'pillow': '8.2.0',
                'streamlit': '1.10.0',
                'pandas': '1.3.0',
            },
            'blocked_packages': {
                'insecure-package',
                'malicious-lib',
                'backdoor-module',
            },
            'required_packages': {
                'streamlit',
                'pandas',
                'requests',
            }
        }
    
    def scan_installed_packages(self):
        """Scan installed packages for vulnerabilities."""
        vulnerabilities = []
        warnings = []
        
        try:
            # Get installed packages
            installed_packages = {pkg.project_name.lower(): pkg.version 
                                for pkg in pkg_resources.working_set}
            
            # Check for vulnerabilities
            for package_name, version in installed_packages.items():
                if package_name in self.known_vulnerabilities:
                    package_vulns = self.known_vulnerabilities[package_name]
                    if version in package_vulns:
                        for vuln_id in package_vulns[version]:
                            vulnerabilities.append({
                                'package': package_name,
                                'version': version,
                                'vulnerability': vuln_id,
                                'severity': 'HIGH'
                            })
                
                # Check minimum version requirements
                if package_name in self.security_policies['min_versions']:
                    min_version = self.security_policies['min_versions'][package_name]
                    if self._compare_versions(version, min_version) < 0:
                        warnings.append({
                            'package': package_name,
                            'current_version': version,
                            'min_version': min_version,
                            'issue': 'Below minimum secure version'
                        })
                
                # Check for blocked packages
                if package_name in self.security_policies['blocked_packages']:
                    vulnerabilities.append({
                        'package': package_name,
                        'version': version,
                        'vulnerability': 'BLOCKED_PACKAGE',
                        'severity': 'CRITICAL'
                    })
            
            # Check for missing required packages
            for required_pkg in self.security_policies['required_packages']:
                if required_pkg not in installed_packages:
                    warnings.append({
                        'package': required_pkg,
                        'issue': 'Required package not installed'
                    })
            
        except Exception as e:
            vulnerabilities.append({
                'package': 'SCAN_ERROR',
                'vulnerability': str(e),
                'severity': 'ERROR'
            })
        
        return {
            'vulnerabilities': vulnerabilities,
            'warnings': warnings,
            'scanned_packages': len(installed_packages) if 'installed_packages' in locals() else 0
        }
    
    def _compare_versions(self, version1, version2):
        """Compare two version strings."""
        def version_tuple(v):
            return tuple(map(int, (v.split("."))))
        
        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)
        
        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    
    def validate_requirements_file(self, requirements_content):
        """Validate requirements.txt for security issues."""
        issues = []
        
        lines = requirements_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse package specification
            if '==' in line:
                package_name, version = line.split('==', 1)
                package_name = package_name.strip()
                version = version.strip()
                
                # Check for known vulnerabilities
                if package_name.lower() in self.known_vulnerabilities:
                    package_vulns = self.known_vulnerabilities[package_name.lower()]
                    if version in package_vulns:
                        issues.append({
                            'line': line_num,
                            'package': package_name,
                            'version': version,
                            'issue': f'Known vulnerabilities: {package_vulns[version]}',
                            'severity': 'HIGH'
                        })
                
                # Check minimum version
                if package_name.lower() in self.security_policies['min_versions']:
                    min_version = self.security_policies['min_versions'][package_name.lower()]
                    if self._compare_versions(version, min_version) < 0:
                        issues.append({
                            'line': line_num,
                            'package': package_name,
                            'version': version,
                            'issue': f'Below minimum secure version {min_version}',
                            'severity': 'MEDIUM'
                        })
                
                # Check for blocked packages
                if package_name.lower() in self.security_policies['blocked_packages']:
                    issues.append({
                        'line': line_num,
                        'package': package_name,
                        'version': version,
                        'issue': 'Package is blocked due to security concerns',
                        'severity': 'CRITICAL'
                    })
            
            elif '>=' in line or '>' in line or '<=' in line or '<' in line:
                # Version ranges - warn about potential security risks
                issues.append({
                    'line': line_num,
                    'package': line.split()[0],
                    'issue': 'Version range specified - consider pinning to specific secure version',
                    'severity': 'LOW'
                })
        
        return issues


class TestDependencyVulnerabilityScanning:
    """Test dependency vulnerability scanning."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = DependencyScanner()
    
    def test_vulnerability_detection(self):
        """Test detection of known vulnerabilities."""
        # Mock installed packages with known vulnerabilities
        mock_packages = [
            MagicMock(project_name='requests', version='2.25.0'),
            MagicMock(project_name='pillow', version='8.1.0'),
            MagicMock(project_name='streamlit', version='1.15.0'),
        ]
        
        with patch('pkg_resources.working_set', mock_packages):
            results = self.scanner.scan_installed_packages()
        
        # Should detect vulnerabilities in requests and pillow
        vulnerabilities = results['vulnerabilities']
        vuln_packages = [v['package'] for v in vulnerabilities]
        
        assert 'requests' in vuln_packages, "Should detect requests vulnerability"
        assert 'pillow' in vuln_packages, "Should detect pillow vulnerabilities"
        
        # Check vulnerability details
        requests_vulns = [v for v in vulnerabilities if v['package'] == 'requests']
        assert len(requests_vulns) > 0
        assert 'CVE-2021-33503' in requests_vulns[0]['vulnerability']
    
    def test_minimum_version_checking(self):
        """Test minimum version requirement checking."""
        # Mock packages with versions below minimum
        mock_packages = [
            MagicMock(project_name='requests', version='2.20.0'),  # Below min 2.26.0
            MagicMock(project_name='pandas', version='1.2.0'),     # Below min 1.3.0
            MagicMock(project_name='streamlit', version='1.15.0'), # Above min 1.10.0
        ]
        
        with patch('pkg_resources.working_set', mock_packages):
            results = self.scanner.scan_installed_packages()
        
        warnings = results['warnings']
        warning_packages = [w['package'] for w in warnings]
        
        assert 'requests' in warning_packages, "Should warn about requests version"
        assert 'pandas' in warning_packages, "Should warn about pandas version"
        assert 'streamlit' not in [w['package'] for w in warnings if 'min_version' in w], \
            "Should not warn about streamlit version"
    
    def test_blocked_package_detection(self):
        """Test detection of blocked packages."""
        # Mock packages including blocked ones
        mock_packages = [
            MagicMock(project_name='streamlit', version='1.15.0'),
            MagicMock(project_name='insecure-package', version='1.0.0'),
            MagicMock(project_name='malicious-lib', version='2.0.0'),
        ]
        
        with patch('pkg_resources.working_set', mock_packages):
            results = self.scanner.scan_installed_packages()
        
        vulnerabilities = results['vulnerabilities']
        blocked_packages = [v['package'] for v in vulnerabilities if v['vulnerability'] == 'BLOCKED_PACKAGE']
        
        assert 'insecure-package' in blocked_packages
        assert 'malicious-lib' in blocked_packages
        
        # Check severity
        blocked_vulns = [v for v in vulnerabilities if v['vulnerability'] == 'BLOCKED_PACKAGE']
        for vuln in blocked_vulns:
            assert vuln['severity'] == 'CRITICAL'
    
    def test_missing_required_packages(self):
        """Test detection of missing required packages."""
        # Mock minimal package set missing required packages
        mock_packages = [
            MagicMock(project_name='requests', version='2.26.0'),
            # Missing streamlit and pandas
        ]
        
        with patch('pkg_resources.working_set', mock_packages):
            results = self.scanner.scan_installed_packages()
        
        warnings = results['warnings']
        missing_packages = [w['package'] for w in warnings if 'not installed' in w['issue']]
        
        assert 'streamlit' in missing_packages
        assert 'pandas' in missing_packages


class TestRequirementsFileValidation:
    """Test requirements.txt file validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = DependencyScanner()
    
    def test_vulnerable_requirements_detection(self):
        """Test detection of vulnerable packages in requirements.txt."""
        requirements_content = """
# Core dependencies
streamlit==1.15.0
pandas==1.5.0
requests==2.25.0
pillow==8.1.0

# Development dependencies
pytest==7.0.0
"""
        
        issues = self.scanner.validate_requirements_file(requirements_content)
        
        # Should detect vulnerabilities in requests and pillow
        vuln_packages = [issue['package'] for issue in issues if issue['severity'] == 'HIGH']
        assert 'requests' in vuln_packages
        assert 'pillow' in vuln_packages
    
    def test_minimum_version_requirements_validation(self):
        """Test validation of minimum version requirements."""
        requirements_content = """
streamlit==1.5.0
pandas==1.2.0
requests==2.26.0
"""
        
        issues = self.scanner.validate_requirements_file(requirements_content)
        
        # Should warn about versions below minimum
        below_min_packages = [issue['package'] for issue in issues if 'Below minimum' in issue['issue']]
        assert 'streamlit' in below_min_packages  # 1.5.0 < 1.10.0
        assert 'pandas' in below_min_packages     # 1.2.0 < 1.3.0
        assert 'requests' not in below_min_packages  # 2.26.0 >= 2.26.0
    
    def test_blocked_packages_in_requirements(self):
        """Test detection of blocked packages in requirements."""
        requirements_content = """
streamlit==1.15.0
insecure-package==1.0.0
malicious-lib==2.0.0
"""
        
        issues = self.scanner.validate_requirements_file(requirements_content)
        
        # Should detect blocked packages
        blocked_packages = [issue['package'] for issue in issues if issue['severity'] == 'CRITICAL']
        assert 'insecure-package' in blocked_packages
        assert 'malicious-lib' in blocked_packages
    
    def test_version_range_warnings(self):
        """Test warnings for version ranges."""
        requirements_content = """
streamlit>=1.10.0
pandas>1.3.0,<2.0.0
requests~=2.26.0
"""
        
        issues = self.scanner.validate_requirements_file(requirements_content)
        
        # Should warn about version ranges
        range_warnings = [issue for issue in issues if 'range specified' in issue['issue']]
        assert len(range_warnings) >= 2  # At least streamlit and pandas
    
    def test_comments_and_empty_lines_ignored(self):
        """Test that comments and empty lines are ignored."""
        requirements_content = """
# This is a comment
streamlit==1.15.0

# Another comment
pandas==1.5.0

"""
        
        issues = self.scanner.validate_requirements_file(requirements_content)
        
        # Should not have issues with comments or empty lines
        comment_issues = [issue for issue in issues if issue.get('line', 0) in [1, 3, 5, 7]]
        assert len(comment_issues) == 0


class TestSupplyChainSecurity:
    """Test supply chain security measures."""
    
    def test_package_integrity_validation(self):
        """Test package integrity validation."""
        def validate_package_integrity(package_name, expected_hash):
            """Mock package integrity validation."""
            # In real implementation, this would verify package hashes
            known_hashes = {
                'streamlit': 'abc123def456',
                'pandas': 'def456ghi789',
                'requests': 'ghi789jkl012',
            }
            
            if package_name not in known_hashes:
                return False, "Package not in trusted registry"
            
            if known_hashes[package_name] != expected_hash:
                return False, "Hash mismatch - potential tampering"
            
            return True, "Package integrity verified"
        
        # Test valid packages
        valid_packages = [
            ('streamlit', 'abc123def456'),
            ('pandas', 'def456ghi789'),
        ]
        
        for package, hash_value in valid_packages:
            is_valid, message = validate_package_integrity(package, hash_value)
            assert is_valid, f"Valid package {package} failed integrity check: {message}"
        
        # Test tampered packages
        tampered_packages = [
            ('streamlit', 'wrong_hash'),
            ('pandas', 'malicious_hash'),
        ]
        
        for package, hash_value in tampered_packages:
            is_valid, message = validate_package_integrity(package, hash_value)
            assert not is_valid, f"Tampered package {package} passed integrity check"
    
    def test_trusted_source_validation(self):
        """Test validation of package sources."""
        def validate_package_source(package_url):
            """Validate package source URL."""
            trusted_sources = [
                'https://pypi.org/',
                'https://files.pythonhosted.org/',
            ]
            
            untrusted_sources = [
                'http://suspicious-mirror.com/',
                'https://malicious-pypi.evil/',
            ]
            
            for trusted in trusted_sources:
                if package_url.startswith(trusted):
                    return True, "Trusted source"
            
            for untrusted in untrusted_sources:
                if package_url.startswith(untrusted):
                    return False, "Untrusted source"
            
            return False, "Unknown source"
        
        # Test trusted sources
        trusted_urls = [
            'https://pypi.org/simple/streamlit/',
            'https://files.pythonhosted.org/packages/streamlit-1.15.0.tar.gz',
        ]
        
        for url in trusted_urls:
            is_trusted, message = validate_package_source(url)
            assert is_trusted, f"Trusted URL {url} rejected: {message}"
        
        # Test untrusted sources
        untrusted_urls = [
            'http://suspicious-mirror.com/streamlit-1.15.0.tar.gz',
            'https://malicious-pypi.evil/packages/streamlit/',
        ]
        
        for url in untrusted_urls:
            is_trusted, message = validate_package_source(url)
            assert not is_trusted, f"Untrusted URL {url} accepted"
    
    def test_dependency_confusion_protection(self):
        """Test protection against dependency confusion attacks."""
        def check_dependency_confusion(package_name, internal_packages):
            """Check for potential dependency confusion."""
            # Internal packages should have priority
            if package_name in internal_packages:
                return True, "Internal package - safe"
            
            # Check for suspicious package names
            suspicious_patterns = [
                'company-internal-',
                'private-',
                'internal-',
            ]
            
            for pattern in suspicious_patterns:
                if pattern in package_name.lower():
                    return False, f"Suspicious package name pattern: {pattern}"
            
            return True, "External package - validated"
        
        internal_packages = {'company-internal-utils', 'private-config'}
        
        # Test internal packages
        for package in internal_packages:
            is_safe, message = check_dependency_confusion(package, internal_packages)
            assert is_safe, f"Internal package {package} flagged as unsafe: {message}"
        
        # Test suspicious external packages
        suspicious_packages = ['company-internal-fake', 'private-malicious']
        
        for package in suspicious_packages:
            is_safe, message = check_dependency_confusion(package, internal_packages)
            assert not is_safe, f"Suspicious package {package} not detected"


if __name__ == "__main__":
    pytest.main([__file__])
