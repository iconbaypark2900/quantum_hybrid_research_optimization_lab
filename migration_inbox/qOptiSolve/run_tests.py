#!/usr/bin/env python3
"""
Test runner for QOptiSolve.

This script provides a simple way to run the test suite
and can be used as an alternative to pytest directly.
"""

import sys
import subprocess
import os


def run_tests():
    """Run the test suite."""
    print("🧪 Running QOptiSolve Test Suite")
    print("=" * 50)
    
    # Check if pytest is available
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} found")
    except ImportError:
        print("❌ pytest not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
            print("✅ pytest installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install pytest")
            return False
    
    # Run tests
    print("\n--- Running Tests ---")
    try:
        # Change to the project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_dir)
        
        # Run pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/",
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "--color=yes"  # Colored output
        ], capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            return True
        else:
            print(f"\n❌ Some tests failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def run_specific_test(test_file):
    """Run a specific test file."""
    print(f"🧪 Running specific test: {test_file}")
    print("=" * 50)
    
    try:
        # Change to the project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_dir)
        
        # Run specific test
        result = subprocess.run([
            sys.executable, "-m", "pytest", f"tests/{test_file}",
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "--color=yes"  # Colored output
        ], capture_output=False)
        
        if result.returncode == 0:
            print(f"\n✅ Test {test_file} passed!")
            return True
        else:
            print(f"\n❌ Test {test_file} failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running test {test_file}: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Run specific test
        test_file = sys.argv[1]
        success = run_specific_test(test_file)
    else:
        # Run all tests
        success = run_tests()
    
    if success:
        print("\n🎉 Test execution completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Test execution failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
