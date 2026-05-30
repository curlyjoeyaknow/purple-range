"""Enable ``python -m lab`` to invoke the CLI."""

from __future__ import annotations

import sys

from lab.cli import main

if __name__ == "__main__":
    sys.exit(main())
