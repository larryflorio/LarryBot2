#!/usr/bin/env python3
"""
Test runner for LarryBot2
"""
import sys
import subprocess
import os


def run_tests():
    """Run all tests with pytest from the project root."""
    # Get the project root (parent of the script directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, os.pardir))

    # Change to the project root directory
    os.chdir(project_root)

    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=larrybot",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=80"
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code) 