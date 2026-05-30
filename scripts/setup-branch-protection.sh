#!/usr/bin/env bash
# setup-branch-protection.sh — Apply branch protection to the default branch
# via the GitHub CLI. Idempotent.
#
# Two modes (resolves the solo-dev self-merge deadlock from the red-team):
#   team mode (default): requires 1 approving review. Works when >1 human/bot
#       can approve. An autonomous agent CANNOT approve its own PR, so under
#       /deliver a human closes the merge gate.
#   solo mode (--solo):  requires 0 approving reviews but KEEPS the real gates —
#       green CI, linear history, conversation resolution, no force-push. The
#       agent can then merge its own green PR. The gate is "CI + review
#       discipline", not "a second human".
#
# Required status checks are configurable; until you wire ci.yml to your stack
# its `test` job FAILS BY DESIGN and will (correctly) block merges. Pass
# --checks "" to start with no required checks, then add them once CI is real.
#
# Usage:
#   ./scripts/setup-branch-protection.sh                 # team mode, main
#   ./scripts/setup-branch-protection.sh --solo          # solo mode, main
#   ./scripts/setup-branch-protection.sh --solo master
#   ./scripts/setup-branch-protection.sh --checks "test,markdown"

set -euo pipefail

BRANCH="main"
SOLO=0
CHECKS='test,docs-discipline,markdown'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --solo) SOLO=1; shift ;;
    --checks) CHECKS="$2"; shift 2 ;;
    *) BRANCH="$1"; shift ;;
  esac
done

command -v gh >/dev/null || { echo "gh CLI not found. Install from https://cli.github.com/"; exit 1; }
command -v jq >/dev/null || { echo "jq not found. Install jq (apt install jq)."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh not authenticated. Run: gh auth login"; exit 1; }

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
REVIEW_COUNT=$([[ $SOLO -eq 1 ]] && echo 0 || echo 1)

# Build the required-status-checks contexts array from CHECKS (may be empty).
if [[ -n "$CHECKS" ]]; then
  CONTEXTS=$(echo "$CHECKS" | jq -R 'split(",") | map(select(length>0))')
else
  CONTEXTS='[]'
fi

echo "Applying branch protection to ${REPO}@${BRANCH}  (mode: $([[ $SOLO -eq 1 ]] && echo solo || echo team), required reviews: ${REVIEW_COUNT})"
[[ "$CONTEXTS" == '[]' ]] && echo "  note: no required status checks set (use --checks once CI is wired)."

gh api -X PUT \
  -H "Accept: application/vnd.github+json" \
  "repos/${REPO}/branches/${BRANCH}/protection" \
  --input <(jq -n --argjson checks "$CONTEXTS" --argjson reviews "$REVIEW_COUNT" '
    {
      required_status_checks: { strict: true, contexts: $checks },
      enforce_admins: true,
      required_pull_request_reviews: {
        dismiss_stale_reviews: true,
        require_code_owner_reviews: false,
        required_approving_review_count: $reviews,
        require_last_push_approval: ($reviews > 0)
      },
      restrictions: null,
      required_linear_history: true,
      allow_force_pushes: false,
      allow_deletions: false,
      required_conversation_resolution: true
    }
  ') > /dev/null

echo "Done. ${BRANCH} now requires:"
[[ "$CONTEXTS" != '[]' ]] && echo "  • green CI for: ${CHECKS}"
echo "  • $([[ $SOLO -eq 1 ]] && echo '0 approvals (solo) — agent may merge its own green PR' || echo '1 approving review — a human closes the merge gate')"
echo "  • linear history, conversation resolution, no force-push, no deletion"
