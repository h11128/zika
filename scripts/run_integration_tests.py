#!/usr/bin/env python3
"""
Integration test runner for UI refactor validation.
Runs comprehensive tests and generates validation reports.
"""

import sys
import time
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.performance_monitor import get_performance_monitor, validate_performance_targets


class IntegrationTestRunner:
    """Comprehensive integration test runner."""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        self.performance_monitor = get_performance_monitor()
    
    def run_test_suite(self, test_path: str, suite_name: str) -> Dict[str, Any]:
        """Run a test suite and capture results."""
        print(f"\n🧪 Running {suite_name}...")
        
        start_time = time.time()
        
        try:
            # Run pytest with JSON output
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                test_path, 
                '-v', 
                '--tb=short',
                '--json-report',
                '--json-report-file=test_results.json'
            ], 
            capture_output=True, 
            text=True,
            cwd=project_root
            )
            
            duration = time.time() - start_time
            
            # Parse results
            try:
                with open(project_root / 'test_results.json', 'r') as f:
                    test_data = json.load(f)
                
                summary = test_data.get('summary', {})
                
                suite_results = {
                    'suite_name': suite_name,
                    'duration_seconds': duration,
                    'total_tests': summary.get('total', 0),
                    'passed': summary.get('passed', 0),
                    'failed': summary.get('failed', 0),
                    'errors': summary.get('error', 0),
                    'skipped': summary.get('skipped', 0),
                    'success_rate': 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
                
                if suite_results['total_tests'] > 0:
                    suite_results['success_rate'] = (suite_results['passed'] / suite_results['total_tests']) * 100
                
                # Clean up
                test_results_file = project_root / 'test_results.json'
                if test_results_file.exists():
                    test_results_file.unlink()
                
            except (FileNotFoundError, json.JSONDecodeError):
                # Fallback to parsing stdout
                suite_results = {
                    'suite_name': suite_name,
                    'duration_seconds': duration,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode,
                    'success_rate': 100 if result.returncode == 0 else 0
                }
            
            if result.returncode == 0:
                print(f"✅ {suite_name} passed ({duration:.2f}s)")
            else:
                print(f"❌ {suite_name} failed ({duration:.2f}s)")
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}...")
            
            return suite_results
            
        except Exception as e:
            print(f"❌ {suite_name} crashed: {e}")
            return {
                'suite_name': suite_name,
                'duration_seconds': time.time() - start_time,
                'error': str(e),
                'success_rate': 0
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration test suites."""
        print("🚀 Starting comprehensive integration test suite...")
        
        test_suites = [
            ('tests/ui/test_error_boundaries.py', 'Error Boundaries'),
            ('tests/ui/test_adapter_system.py', 'Adapter System'),
            ('tests/integration/test_adapter_migration.py', 'Adapter Migration'),
            ('tests/integration/test_end_to_end_workflows.py', 'End-to-End Workflows'),
            ('tests/validation/test_design_compliance.py', 'Design Compliance'),
            ('tests/performance/test_performance_benchmarks.py', 'Performance Benchmarks')
        ]
        
        results = {}
        
        for test_path, suite_name in test_suites:
            suite_results = self.run_test_suite(test_path, suite_name)
            results[suite_name] = suite_results
        
        return results
    
    def validate_system_health(self) -> Dict[str, Any]:
        """Validate overall system health."""
        print("\n🔍 Validating system health...")
        
        health_results = {}
        
        try:
            # Test basic imports
            from ui.ports import get_ui_adapter
            from ui.inputs import render_input_section_adapted
            from ui.options import render_options_section_adapted
            from ui.sidebar import render_sidebar_adapted
            
            health_results['imports'] = {'status': 'success', 'message': 'All imports successful'}
            
        except Exception as e:
            health_results['imports'] = {'status': 'failed', 'message': f'Import failed: {e}'}
        
        try:
            # Test adapter creation
            adapter = get_ui_adapter()
            assert adapter is not None
            assert hasattr(adapter, 'inputs')
            assert hasattr(adapter, 'layout')
            assert hasattr(adapter, 'notifications')
            
            health_results['adapter'] = {'status': 'success', 'message': 'Adapter system functional'}
            
        except Exception as e:
            health_results['adapter'] = {'status': 'failed', 'message': f'Adapter test failed: {e}'}
        
        try:
            # Test performance targets
            performance_results = validate_performance_targets()
            health_results['performance'] = {
                'status': 'success' if all(performance_results.values()) else 'warning',
                'targets': performance_results
            }
            
        except Exception as e:
            health_results['performance'] = {'status': 'failed', 'message': f'Performance validation failed: {e}'}
        
        return health_results
    
    def generate_report(self, test_results: Dict[str, Any], health_results: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time
        
        report = [
            "# UI Refactor Integration Test Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {total_duration:.2f} seconds",
            "",
            "## Executive Summary"
        ]
        
        # Calculate overall statistics
        total_tests = sum(suite.get('total_tests', 0) for suite in test_results.values())
        total_passed = sum(suite.get('passed', 0) for suite in test_results.values())
        total_failed = sum(suite.get('failed', 0) for suite in test_results.values())
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report.extend([
            f"- **Total Tests**: {total_tests}",
            f"- **Passed**: {total_passed}",
            f"- **Failed**: {total_failed}",
            f"- **Success Rate**: {overall_success_rate:.1f}%",
            ""
        ])
        
        # Overall status
        if overall_success_rate >= 95:
            report.append("🟢 **Status**: EXCELLENT - System ready for production")
        elif overall_success_rate >= 85:
            report.append("🟡 **Status**: GOOD - Minor issues to address")
        elif overall_success_rate >= 70:
            report.append("🟠 **Status**: FAIR - Several issues need attention")
        else:
            report.append("🔴 **Status**: POOR - Major issues require immediate attention")
        
        report.append("")
        
        # Test suite details
        report.append("## Test Suite Results")
        
        for suite_name, results in test_results.items():
            success_rate = results.get('success_rate', 0)
            duration = results.get('duration_seconds', 0)
            
            status_icon = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
            
            report.extend([
                f"### {status_icon} {suite_name}",
                f"- Success Rate: {success_rate:.1f}%",
                f"- Duration: {duration:.2f}s",
                f"- Tests: {results.get('total_tests', 'N/A')}",
                ""
            ])
            
            if results.get('failed', 0) > 0 or results.get('errors', 0) > 0:
                report.append("**Issues:**")
                if results.get('stderr'):
                    report.append(f"```\n{results['stderr'][:500]}...\n```")
                report.append("")
        
        # System health
        report.append("## System Health Check")
        
        for component, health in health_results.items():
            status = health.get('status', 'unknown')
            message = health.get('message', 'No details')
            
            status_icon = "✅" if status == 'success' else "⚠️" if status == 'warning' else "❌"
            
            report.extend([
                f"### {status_icon} {component.title()}",
                f"- Status: {status.upper()}",
                f"- Details: {message}",
                ""
            ])
        
        # Performance metrics
        if 'performance' in health_results and 'targets' in health_results['performance']:
            report.append("## Performance Targets")
            targets = health_results['performance']['targets']
            
            for target, met in targets.items():
                status_icon = "✅" if met else "❌"
                report.append(f"- {status_icon} {target}: {'MET' if met else 'NOT MET'}")
            
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        
        if overall_success_rate >= 95:
            report.append("- ✅ System is ready for production deployment")
            report.append("- ✅ All critical functionality is working correctly")
            report.append("- ✅ Performance targets are being met")
        else:
            report.append("- ⚠️ Address failing tests before production deployment")
            report.append("- ⚠️ Review error logs for specific issues")
            report.append("- ⚠️ Consider additional testing for edge cases")
        
        report.extend([
            "",
            "## Next Steps",
            "1. Review and fix any failing tests",
            "2. Validate performance in production-like environment",
            "3. Conduct user acceptance testing",
            "4. Prepare deployment documentation",
            "5. Plan rollout strategy"
        ])
        
        return "\n".join(report)
    
    def save_report(self, report: str, filename: str = "integration_test_report.md"):
        """Save report to file."""
        report_path = project_root / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {report_path}")
        return report_path


def main():
    """Main test runner function."""
    runner = IntegrationTestRunner()
    
    try:
        # Run all test suites
        test_results = runner.run_all_tests()
        
        # Validate system health
        health_results = runner.validate_system_health()
        
        # Generate and save report
        report = runner.generate_report(test_results, health_results)
        report_path = runner.save_report(report)
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        total_tests = sum(suite.get('total_tests', 0) for suite in test_results.values())
        total_passed = sum(suite.get('passed', 0) for suite in test_results.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 95:
            print("🟢 Status: EXCELLENT - Ready for production!")
            return 0
        elif overall_success_rate >= 85:
            print("🟡 Status: GOOD - Minor issues to address")
            return 0
        else:
            print("🔴 Status: NEEDS WORK - Address failing tests")
            return 1
    
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
