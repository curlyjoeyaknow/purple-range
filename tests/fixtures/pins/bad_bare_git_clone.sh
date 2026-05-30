#!/usr/bin/env bash
# Positive fixture for the bare-clone rule. See test docstring for the rule.
# The clone below is followed by no pinning ref within the near window.
set -euo pipefail

git clone https://github.com/vulhub/vulhub.git /mnt/data/vendor/vulhub
cd /mnt/data/vendor/vulhub
echo "cloned at no pinned ref"
