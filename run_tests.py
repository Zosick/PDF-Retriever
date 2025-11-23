import subprocess
import sys

try:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
except Exception as e:
    print(f"Error: {e}")
