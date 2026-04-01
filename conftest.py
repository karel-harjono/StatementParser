"""
pytest configuration: add the project root to sys.path so that
`import app.*` works without a package install.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
