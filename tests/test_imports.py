"""Smoke test: every module imports cleanly against config.example.yml.

run.py is excluded because it starts the bot at import time.
"""

import importlib

import pytest

MODULES = [
    "src.core.init",
    "src.core.tools",
    "src.core.cortana",
    "src.core.db",
    "src.core.models",
    "src.core.mediacrypto",
    "src.core.archiver",
    "src.core.listeners",
    "src.func.commands",
    "src.func.functions",
    "src.web.server",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)
