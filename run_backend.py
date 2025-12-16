import subprocess
import sys
import os

from pathlib import Path

repo_root = Path(__file__).resolve().parent
os.chdir(str(repo_root))

print("=" * 50)
print("Starting Backend Server on Port 8000")
print("=" * 50)
print("Press Ctrl+C to stop")
print()

proc = None
try:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", "8000", "--host", "0.0.0.0"],
        cwd=os.getcwd(),
    )
    proc.wait()
except KeyboardInterrupt:
    print("\nStopping backend...")
    if proc is not None:
        proc.terminate()
