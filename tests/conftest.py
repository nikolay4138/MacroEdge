"""Pytest fixtures. Run tests from project root so config/ is found."""
import os
from pathlib import Path

import pytest

# Ensure project root is on path and config dir exists
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in os.environ.get("PYTHONPATH", ""):
    os.environ.setdefault("PYTHONPATH", str(ROOT))
