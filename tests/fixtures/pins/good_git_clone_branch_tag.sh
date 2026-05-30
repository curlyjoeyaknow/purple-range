#!/usr/bin/env bash
# Negative fixture for rule `bare-git-clone`.
# A clone pinned inline with `--branch vX.Y.Z` (a version tag). The gate MUST
# NOT flag it — the ref is pinned on the clone line itself.
set -euo pipefail

git clone --branch v3.0.0 --depth 1 https://github.com/Orange-Cyberdefense/GOAD.git /mnt/data/vendor/goad
echo "cloned at a pinned tag"
