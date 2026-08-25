import copy
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# src.core.init loads the config at import time; point it at the sanitized
# example config so tests never depend on a real config.yml.
os.environ.setdefault("CORTANA_CONFIG", os.path.join(REPO_ROOT, "config.example.yml"))


@pytest.fixture
def cfg():
    """The live in-memory cfg dict; any mutation is rolled back after the test."""
    from src.core.init import cfg as _cfg

    original = copy.deepcopy(_cfg)
    yield _cfg
    _cfg.clear()
    _cfg.update(original)
