"""
Simple launcher script for arXiv search tests
Run this with: python run_arxiv_tests.py
"""
import subprocess
import sys
import os

# Change to the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

print("=" * 80)
print("Running arXiv Search Method Comparison Tests")
print("=" * 80)
print()

# Run the test module
try:
    result = subprocess.run(
        [sys.executable, "-m", "testing.arxiv_search_test.test_runner"],
        cwd=backend_dir,
        capture_output=False,
        text=True
    )
    
    if result.returncode == 0:
        print("\n" + "=" * 80)
        print("Tests completed successfully!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print(f"Tests completed with return code: {result.returncode}")
        print("=" * 80)
        
except KeyboardInterrupt:
    print("\n\nTests interrupted by user.")
    sys.exit(1)
except Exception as e:
    print(f"\nError running tests: {e}")
    sys.exit(1)
