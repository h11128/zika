"""
Project components package.

This package contains modules used by tests (e.g., components.browser_storage).
An explicit __init__.py ensures standard import/patch semantics for submodules.
"""

# Eagerly import submodules so that unittest.mock.patch('components.browser_storage.*')
# can dot‑resolve attributes reliably in all collection orders.
from . import browser_storage  # noqa: F401

