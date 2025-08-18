#!/usr/bin/env python3
"""
Test runner script for the Chinese Character Learning Cards application.
Provides convenient commands for running different types of tests.
"""

import sys
import subprocess
import argparse


def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout:
                print(result.stdout)
        else:
            print("❌ FAILED")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    return run_command(
        "python -m pytest tests/ -v",
        "Running All Tests"
    )


def run_new_tests():
    """Run only new tests."""
    new_test_files = [
        "tests/test_config_objects.py",
        "tests/test_app_controller.py", 
        "tests/test_refactored_preview.py",
        "tests/test_error_handling.py"
    ]
    
    cmd = f"python -m pytest {' '.join(new_test_files)} -v"
    return run_command(cmd, "Running New Tests Only")


def run_coverage():
    """Run tests with coverage report."""
    return run_command(
        "python -m pytest tests/ --cov=core --cov=ui --cov=services --cov=src --cov-report=term-missing",
        "Running Tests with Coverage Report"
    )


def run_integration_tests():
    """Run integration tests only."""
    integration_files = [
        "tests/test_integration_end_to_end.py",
        "tests/test_integration_cross_module.py",
        "tests/test_integration_file_io.py",
        "tests/test_integration_error_handling.py",
        "tests/test_integration_performance.py",
        "tests/test_integration_configuration.py"
    ]
    cmd = f"python -m pytest {' '.join(integration_files)} -v"
    return run_command(cmd, "Running Integration Tests")


def run_unit_tests():
    """Run unit tests only (excluding integration tests)."""
    return run_command(
        "python -m pytest tests/ -v -k 'not integration'",
        "Running Unit Tests Only"
    )


def run_performance_tests():
    """Run performance and caching tests."""
    return run_command(
        "python -m pytest tests/test_integration_performance.py -v --tb=short",
        "Running Performance Tests"
    )


def run_fast_tests():
    """Run fast tests suitable for pre-commit hooks."""
    return run_command(
        "python -m pytest tests/test_integration_cross_module.py tests/test_integration_configuration.py -q",
        "Running Fast Integration Tests"
    )


def run_ci_tests():
    """Run tests suitable for CI/CD (excluding slow performance tests)."""
    return run_command(
        "python -m pytest tests/ -k 'not (performance and slow)' --maxfail=5",
        "Running CI/CD Test Suite"
    )


def run_specific_test(test_file):
    """Run a specific test file."""
    return run_command(
        f"python -m pytest tests/{test_file} -v",
        f"Running {test_file}"
    )


def run_quick_check():
    """Run a quick smoke test."""
    return run_command(
        "python -m pytest tests/test_config_objects.py tests/test_app_controller.py -v",
        "Quick Smoke Test"
    )


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test runner for Chinese Character Learning Cards")
    parser.add_argument("command", nargs="?", default="all",
                       choices=["all", "unit", "integration", "performance", "coverage", "fast", "ci",
                               "new", "quick", "config", "controller", "preview", "error"],
                       help="Test command to run")

    args = parser.parse_args()

    print("🀄 Chinese Character Learning Cards - Test Runner")
    print("=" * 60)

    success = True

    if args.command == "all":
        success = run_all_tests()
    elif args.command == "unit":
        success = run_unit_tests()
    elif args.command == "integration":
        success = run_integration_tests()
    elif args.command == "performance":
        success = run_performance_tests()
    elif args.command == "coverage":
        success = run_coverage()
    elif args.command == "fast":
        success = run_fast_tests()
    elif args.command == "ci":
        success = run_ci_tests()
    elif args.command == "new":
        success = run_new_tests()
    elif args.command == "quick":
        success = run_quick_check()
    elif args.command == "config":
        success = run_specific_test("test_config_objects.py")
    elif args.command == "controller":
        success = run_specific_test("test_app_controller.py")
    elif args.command == "preview":
        success = run_specific_test("test_refactored_preview.py")
    elif args.command == "error":
        success = run_specific_test("test_error_handling.py")
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ Code is ready for deployment")
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Please fix the issues before deployment")
    print(f"{'='*60}")

    # Print help information
    if args.command == "all" and success:
        print("\n📚 Available Test Categories:")
        print("  unit         - Unit tests only (fast)")
        print("  integration  - Integration tests only")
        print("  performance  - Performance and caching tests (slow)")
        print("  coverage     - All tests with coverage report")
        print("  fast         - Fast tests for pre-commit hooks")
        print("  ci           - CI/CD test suite (excludes slow tests)")
        print("\n🔧 Development Commands:")
        print("  quick        - Quick smoke test")
        print("  new          - Recently added tests")
        print("  config       - Configuration tests")
        print("  controller   - App controller tests")
        print("  preview      - Preview functionality tests")
        print("  error        - Error handling tests")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

