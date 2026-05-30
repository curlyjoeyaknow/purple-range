"""Make the repo root importable for the whole test suite.

The bare ``pytest`` console script (what CI's ``unit`` stage runs) does NOT add
the current working directory to ``sys.path`` — only ``python -m pytest`` does.
Without this, ``import lab`` (and any repo-root package) resolves locally under
``python -m pytest`` but fails in CI with ``ModuleNotFoundError: No module named
'lab'`` at collection time. Placing this conftest at the repo root makes pytest
treat the root as the rootdir and load this file before collecting any test, so
the path is set up uniformly regardless of how pytest is invoked. This replaces
the previous reliance on each test file inserting ``REPO_ROOT`` itself (which was
order-dependent: only the alphabetically-first ``lab``-importing module's insert
saved the rest).
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
