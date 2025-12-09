import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Conda prefix: {os.environ.get('CONDA_PREFIX', 'Not set')}")
