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
        "python -m pytest tests/ --cov=core --cov=ui --cov=services --cov-report=term-missing",
        "Running Tests with Coverage Report"
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
                       choices=["all", "new", "coverage", "quick", "config", "controller", "preview", "error"],
                       help="Test command to run")
    
    args = parser.parse_args()
    
    print("🀄 Chinese Character Learning Cards - Test Runner")
    print("=" * 60)
    
    success = True
    
    if args.command == "all":
        success = run_all_tests()
    elif args.command == "new":
        success = run_new_tests()
    elif args.command == "coverage":
        success = run_coverage()
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
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
