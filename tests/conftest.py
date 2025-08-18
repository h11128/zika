import os
import sys
import shutil
import pytest

# Ensure project root on sys.path for imports like `from src...`/`from services...`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


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

