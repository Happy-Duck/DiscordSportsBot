# conftest.py
# Runs before any test module is imported.

import os
import sys
import tempfile
from pathlib import Path

# Make `import src.*` work no matter where pytest is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Point the whole test session at a throwaway database so tests never
# touch the real src/sportsbot.db. Must happen before src.db_skeleton import.
_tmpdir = tempfile.mkdtemp(prefix="sportsbot-tests-")
os.environ["SPORTSBOT_DB"] = os.path.join(_tmpdir, "test_sportsbot.db")
