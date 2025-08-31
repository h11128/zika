#!/usr/bin/env python3
"""
Comprehensive Compatibility Testing Script.
Runs all compatibility tests and generates detailed reports.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.compatibility.compatibility_matrix import (
    CompatibilityMatrix, CompatibilityTester, CompatibilityLevel,
    get_compatibility_matrix, get_compatibility_tester
)


def run_full_compatibility_suite(output_dir: str = "compatibility_reports") -> Dict[str, Any]:
    """Run full compatibility test suite and generate reports."""
    print("🔍 Starting Comprehensive Compatibility Testing...")
    start_time = time.time()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize testing components
    matrix = get_compatibility_matrix()
    tester = get_compatibility_tester()
    
    # Generate compatibility matrix report
    print("\n📊 Generating Compatibility Matrix Report...")
    matrix_report = matrix.generate_compatibility_report()
    
    # Run browser compatibility tests
    print("\n🌐 Running Browser Compatibility Tests...")
    browser_results = tester.run_browser_compatibility_tests()
    print(f"   Completed {len(browser_results)} browser tests")
    
    # Run Streamlit compatibility tests
    print("\n🚀 Running Streamlit Compatibility Tests...")
    streamlit_results = tester.run_streamlit_compatibility_tests()
    print(f"   Completed {len(streamlit_results)} Streamlit tests")
    
    # Run data format compatibility tests
    print("\n📁 Running Data Format Compatibility Tests...")
    data_format_results = tester.run_data_format_compatibility_tests()
    print(f"   Completed {len(data_format_results)} data format tests")
    
    # Generate comprehensive test report
    print("\n📋 Generating Test Report...")
    test_report = tester.generate_test_report()
    
    # Calculate overall statistics
    total_duration = time.time() - start_time
    
    # Compile comprehensive report
    comprehensive_report = {
        "test_execution": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": total_duration,
            "total_tests": test_report["summary"]["total_tests"],
            "success_rate": test_report["summary"]["success_rate"]
        },
        "compatibility_matrix": matrix_report,
        "test_results": test_report,
        "detailed_results": {
            "browser_tests": [result.__dict__ for result in browser_results],
            "streamlit_tests": [result.__dict__ for result in streamlit_results],
            "data_format_tests": [result.__dict__ for result in data_format_results]
        }
    }
    
    # Save reports
    save_reports(comprehensive_report, output_dir)
    
    # Print summary
    print_summary(comprehensive_report)
    
    return comprehensive_report


def save_reports(report: Dict[str, Any], output_dir: str):
    """Save compatibility reports to files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save comprehensive JSON report
    json_file = os.path.join(output_dir, f"compatibility_report_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"📄 Saved JSON report: {json_file}")
    
    # Save human-readable summary
    summary_file = os.path.join(output_dir, f"compatibility_summary_{timestamp}.md")
    with open(summary_file, 'w', encoding='utf-8') as f:
        write_markdown_summary(f, report)
    print(f"📄 Saved summary report: {summary_file}")
    
    # Save CSV for spreadsheet analysis
    csv_file = os.path.join(output_dir, f"compatibility_results_{timestamp}.csv")
    save_csv_results(report, csv_file)
    print(f"📄 Saved CSV results: {csv_file}")


def write_markdown_summary(f, report: Dict[str, Any]):
    """Write human-readable markdown summary."""
    f.write("# Compatibility Testing Report\n\n")
    
    # Test execution summary
    execution = report["test_execution"]
    f.write(f"**Test Date:** {execution['timestamp']}\n")
    f.write(f"**Duration:** {execution['duration_seconds']:.2f} seconds\n")
    f.write(f"**Total Tests:** {execution['total_tests']}\n")
    f.write(f"**Success Rate:** {execution['success_rate']:.1%}\n\n")
    
    # Browser support summary
    browser_support = report["compatibility_matrix"]["browser_support"]
    f.write("## Browser Support Summary\n\n")
    f.write(f"- **Total Browser Versions:** {browser_support['total_versions']}\n")
    f.write(f"- **Full Support:** {browser_support['full_support']}\n")
    f.write(f"- **Partial Support:** {browser_support['partial_support']}\n")
    f.write(f"- **Minimal Support:** {browser_support['minimal_support']}\n")
    f.write(f"- **Market Coverage:** {browser_support['market_coverage']:.1f}%\n\n")
    
    # Streamlit support summary
    streamlit_support = report["compatibility_matrix"]["streamlit_support"]
    f.write("## Streamlit Support Summary\n\n")
    f.write(f"- **Total Versions:** {streamlit_support['total_versions']}\n")
    f.write(f"- **Full Support:** {streamlit_support['full_support']}\n")
    f.write(f"- **Partial Support:** {streamlit_support['partial_support']}\n")
    f.write(f"- **Known Issues:** {streamlit_support['known_issues_count']}\n\n")
    
    # Data format support summary
    data_format_support = report["compatibility_matrix"]["data_format_support"]
    f.write("## Data Format Support Summary\n\n")
    f.write(f"- **Total Formats:** {data_format_support['total_formats']}\n")
    f.write(f"- **Migration Paths:** {data_format_support['migration_paths']}\n")
    f.write(f"- **Legacy Support:** {data_format_support['legacy_support']}\n\n")
    
    # Test results summary
    test_results = report["test_results"]
    f.write("## Test Results Summary\n\n")
    f.write(f"- **Browser Tests:** {test_results['by_category']['browser_tests']}\n")
    f.write(f"- **Streamlit Tests:** {test_results['by_category']['streamlit_tests']}\n")
    f.write(f"- **Data Format Tests:** {test_results['by_category']['data_format_tests']}\n\n")
    
    # Compatibility levels
    levels = test_results["compatibility_levels"]
    f.write("## Compatibility Levels\n\n")
    f.write(f"- **Full:** {levels['full']}\n")
    f.write(f"- **Partial:** {levels['partial']}\n")
    f.write(f"- **Minimal:** {levels['minimal']}\n")
    f.write(f"- **Unsupported:** {levels['unsupported']}\n\n")
    
    # Issues summary
    issues = test_results["issues"]
    f.write("## Issues Summary\n\n")
    f.write(f"- **Total Issues:** {issues['total_issues']}\n")
    f.write(f"- **Total Warnings:** {issues['total_warnings']}\n")
    f.write(f"- **Failed Tests:** {len(issues['failed_tests'])}\n\n")
    
    if issues['failed_tests']:
        f.write("### Failed Tests\n\n")
        for test_name in issues['failed_tests']:
            f.write(f"- {test_name}\n")
        f.write("\n")
    
    # Recommendations
    f.write("## Recommendations\n\n")
    success_rate = execution['success_rate']
    if success_rate >= 0.95:
        f.write("✅ **Excellent compatibility** - Ready for production deployment\n")
    elif success_rate >= 0.90:
        f.write("✅ **Good compatibility** - Minor issues should be addressed\n")
    elif success_rate >= 0.80:
        f.write("⚠️ **Acceptable compatibility** - Several issues need attention\n")
    else:
        f.write("❌ **Poor compatibility** - Significant issues must be resolved\n")


def save_csv_results(report: Dict[str, Any], csv_file: str):
    """Save test results in CSV format for analysis."""
    import csv
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Test Name', 'Category', 'Success', 'Compatibility Level',
            'Duration (ms)', 'Issues Count', 'Warnings Count', 'Details'
        ])
        
        # Write browser test results
        for result in report["detailed_results"]["browser_tests"]:
            browser_info = "N/A"
            if result.get('browser_version'):
                browser = result['browser_version']
                browser_type = getattr(browser, 'type', 'N/A')
                browser_version = getattr(browser, 'version', 'N/A')
                if hasattr(browser_type, 'value'):
                    browser_type = browser_type.value
                browser_info = f"Browser: {browser_type} {browser_version}"

            writer.writerow([
                result['test_name'], 'Browser', result['success'],
                result['compatibility_level'], result['test_duration_ms'],
                len(result['issues']), len(result['warnings']),
                browser_info
            ])

        # Write Streamlit test results
        for result in report["detailed_results"]["streamlit_tests"]:
            streamlit_info = "N/A"
            if result.get('streamlit_version'):
                streamlit = result['streamlit_version']
                version = getattr(streamlit, 'version', 'N/A')
                streamlit_info = f"Streamlit: {version}"

            writer.writerow([
                result['test_name'], 'Streamlit', result['success'],
                result['compatibility_level'], result['test_duration_ms'],
                len(result['issues']), len(result['warnings']),
                streamlit_info
            ])

        # Write data format test results
        for result in report["detailed_results"]["data_format_tests"]:
            format_info = "N/A"
            if result.get('data_format'):
                data_format = result['data_format']
                format_name = getattr(data_format, 'format_name', 'N/A')
                version = getattr(data_format, 'version', 'N/A')
                format_info = f"Format: {format_name} {version}"

            writer.writerow([
                result['test_name'], 'Data Format', result['success'],
                result['compatibility_level'], result['test_duration_ms'],
                len(result['issues']), len(result['warnings']),
                format_info
            ])


def print_summary(report: Dict[str, Any]):
    """Print test summary to console."""
    print("\n" + "="*60)
    print("🎯 COMPATIBILITY TESTING SUMMARY")
    print("="*60)
    
    execution = report["test_execution"]
    test_results = report["test_results"]
    
    print(f"⏱️  Duration: {execution['duration_seconds']:.2f} seconds")
    print(f"📊 Total Tests: {execution['total_tests']}")
    print(f"✅ Success Rate: {execution['success_rate']:.1%}")
    print(f"🌐 Browser Tests: {test_results['by_category']['browser_tests']}")
    print(f"🚀 Streamlit Tests: {test_results['by_category']['streamlit_tests']}")
    print(f"📁 Data Format Tests: {test_results['by_category']['data_format_tests']}")
    
    # Compatibility breakdown
    levels = test_results["compatibility_levels"]
    print(f"\n📈 Compatibility Levels:")
    print(f"   Full: {levels['full']}")
    print(f"   Partial: {levels['partial']}")
    print(f"   Minimal: {levels['minimal']}")
    print(f"   Unsupported: {levels['unsupported']}")
    
    # Issues summary
    issues = test_results["issues"]
    print(f"\n⚠️  Issues:")
    print(f"   Total Issues: {issues['total_issues']}")
    print(f"   Total Warnings: {issues['total_warnings']}")
    print(f"   Failed Tests: {len(issues['failed_tests'])}")
    
    # Overall assessment
    success_rate = execution['success_rate']
    print(f"\n🎯 Overall Assessment:")
    if success_rate >= 0.95:
        print("   ✅ EXCELLENT - Ready for production")
    elif success_rate >= 0.90:
        print("   ✅ GOOD - Minor issues to address")
    elif success_rate >= 0.80:
        print("   ⚠️  ACCEPTABLE - Several issues need attention")
    else:
        print("   ❌ POOR - Significant issues must be resolved")
    
    print("="*60)


def main():
    """Main entry point for compatibility testing script."""
    parser = argparse.ArgumentParser(description="Run comprehensive compatibility tests")
    parser.add_argument("--output-dir", default="compatibility_reports",
                       help="Output directory for reports (default: compatibility_reports)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick compatibility check (subset of tests)")
    
    args = parser.parse_args()
    
    try:
        if args.quick:
            print("🚀 Running Quick Compatibility Check...")
            # For quick mode, we could run a subset of tests
            # For now, run the full suite but could be optimized
        
        report = run_full_compatibility_suite(args.output_dir)
        
        # Exit with appropriate code
        success_rate = report["test_execution"]["success_rate"]
        if success_rate >= 0.90:
            sys.exit(0)  # Success
        elif success_rate >= 0.80:
            sys.exit(1)  # Warning - some issues
        else:
            sys.exit(2)  # Error - significant issues
            
    except Exception as e:
        print(f"❌ Error running compatibility tests: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
