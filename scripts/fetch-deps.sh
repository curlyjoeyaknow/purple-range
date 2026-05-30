#!/usr/bin/env bash
# Thin shim for the pinned dependency fetcher (T-002).
#
# The actual logic lives in lab/fetch_deps.py behind the Fetcher port (charter
# #3) so it is testable offline. This wrapper just hands off to the Python
# module; it holds NO clone command of its own (cloning happens in Python),
# so the pins-gate has nothing to flag here.
set -euo pipefail

exec python3 -m lab.fetch_deps "$@"
