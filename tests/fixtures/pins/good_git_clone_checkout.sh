#!/usr/bin/env bash
# Negative fixture for rule `bare-git-clone`.
# A clone immediately followed (within the "near" window) by a
# `git checkout <40-hex-sha>` — the pin. The gate MUST NOT flag it.
set -euo pipefail

git clone https://github.com/vulhub/vulhub.git /mnt/data/vendor/vulhub
cd /mnt/data/vendor/vulhub
git checkout d277a8693e588684e951dddb0733809e53881a3c
echo "cloned and pinned to a commit"
