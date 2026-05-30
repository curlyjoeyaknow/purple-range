#!/usr/bin/env bash
# session-restore.sh — SessionStart hook (matcher: compact|resume).
#
# After a compaction (or a resume), re-inject the critical state so the
# post-compact session re-grounds immediately instead of waking up amnesiac.
# stdout from SessionStart is added to Claude's context.
#
# Wired in .claude/settings.json under hooks.SessionStart with matcher
# "compact|resume". Pairs with precompact-handoff.sh (which wrote the snapshot)
# and the orchestrator's docs/HANDOFF.md (the rich version).

set -uo pipefail

STATE_DIR=".claude/state"

echo "## Session re-grounding (post-compact/resume)"
echo

if [[ -f "docs/HANDOFF.md" ]]; then
  echo "### docs/HANDOFF.md (authored handoff — trust this first)"
  echo '```markdown'
  sed -n '1,80p' docs/HANDOFF.md 2>/dev/null || true
  echo '```'
  echo
fi

if [[ -f "$STATE_DIR/last-snapshot.md" ]]; then
  echo "### Mechanical pre-compaction snapshot (backstop)"
  echo '```markdown'
  sed -n '1,60p' "$STATE_DIR/last-snapshot.md" 2>/dev/null || true
  echo '```'
  echo
fi

if [[ -f "docs/DELIVERY-PLAN.md" ]]; then
  echo "### Where we are in the delivery plan"
  echo '```'
  grep -nE 'critical path|Stream|Milestone|adversarial|hard|loop budget' docs/DELIVERY-PLAN.md 2>/dev/null | head -n 25 || true
  echo '```'
  echo
fi

echo "Resume from the handoff's \"Next concrete step\". If you are the"
echo "pm-orchestrator, reload docs/DELIVERY-PLAN.md and continue executing the"
echo "critical path; you remain bound by it."

# Clear the restore flag now that we've restored.
rm -f "$STATE_DIR/restore-pending" 2>/dev/null || true
exit 0
