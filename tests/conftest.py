import os
import sys
import shutil
import pytest

# Ensure project root on sys.path for imports like `from src...`/`from services...`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Prefer the project's local 'components' package over any third-party package named 'components'
import importlib

def _prefer_local_components():
    try:
        mod = sys.modules.get('components')
        local_pkg_dir = os.path.join(ROOT, 'components').replace('\\', '/').rstrip('/')
        if mod is None or not getattr(mod, '__file__', '') or not mod.__file__.replace('\\', '/').startswith(local_pkg_dir):
            if 'components' in sys.modules:
                # Remove non-local module to avoid name collisions
                del sys.modules['components']
            importlib.invalidate_caches()
            mod = importlib.import_module('components')
        # Ensure submodule attribute exists for patchers that dot-resolve
        try:
            getattr(mod, 'browser_storage')
        except AttributeError:
            importlib.import_module('components.browser_storage')
    except Exception:
        # Best-effort: don't block tests if this fails
        pass

_prefer_local_components()


@pytest.fixture(scope="session", autouse=True)
def cleanup_out_dir_session():
    """Clean up the repository-level 'out' directory before and after the test session.

    - Removes files/subdirectories under ./out (but keeps the folder)
    - Ensures 'out' exists for tests that want to write debug artifacts
    """
    out_dir = os.path.join(ROOT, 'out')
    os.makedirs(out_dir, exist_ok=True)

    def _clean():
        try:
            for entry in os.listdir(out_dir):
                path = os.path.join(out_dir, entry)
                try:
                    if os.path.islink(path) or os.path.isfile(path):
                        os.unlink(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                except Exception:
                    # best-effort cleanup; ignore failures to avoid breaking tests
                    pass
        except FileNotFoundError:
            # If 'out' was removed by someone else, recreate later
            os.makedirs(out_dir, exist_ok=True)

    # Clean before tests
    _clean()
    yield
    # Clean after tests
    _clean()

def pytest_collection_modifyitems(config, items):
    """Auto-assign markers based on filename patterns to organize the suite.

    - integration: tests under tests/integration/ or files named test_integration_*.py
    - e2e: tests whose nodeid contains 'end_to_end'
    - performance: tests whose nodeid contains 'performance'; also mark as slow
    - slow: added for performance tests (and any future slow selectors)
    - ui: tests under tests/ui/
    """
    for item in items:
        # Normalize for Windows paths
        path = str(getattr(item, 'fspath', '')).replace('\\', '/').lower()
        nodeid = item.nodeid.lower()

        if '/tests/integration/' in path or '/tests/test_integration_' in path:
            item.add_marker(pytest.mark.integration)

        if '/tests/ui/' in path:
            item.add_marker(pytest.mark.ui)

        if 'end_to_end' in nodeid:
            item.add_marker(pytest.mark.e2e)

        if 'performance' in nodeid:
            item.add_marker(pytest.mark.performance)
            # Only mark as slow if it's specifically a slow performance test
            if 'slow' in nodeid or 'benchmark' in nodeid:
                item.add_marker(pytest.mark.slow)
