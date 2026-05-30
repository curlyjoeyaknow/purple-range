#!/usr/bin/env bash
# checkpoint-nudge.sh — UserPromptSubmit hook that acts on the context flag.
#
# The statusline monitor sets .claude/state/checkpoint-needed when context
# crosses the threshold (default 60%). On the next user turn, this hook injects
# a directive into Claude's context (stdout from UserPromptSubmit is visible to
# Claude) telling it to checkpoint NOW — write/refresh the handoff and compact —
# before continuing. This is what keeps the orchestrator from sliding toward a
# force-compact with stale state.
#
# Wired in .claude/settings.json under hooks.UserPromptSubmit.
# stdout on UserPromptSubmit is added as context Claude can see and act on.

set -uo pipefail

STATE_DIR=".claude/state"
FLAG="$STATE_DIR/checkpoint-needed"
LAST="$STATE_DIR/last-nudge"

[[ -f "$FLAG" ]] || exit 0   # nothing to do

# --- Debounce (review fix): don't nag every single turn. ---
# Back off if EITHER we nudged in the last 10 minutes OR a handoff/checkpoint
# commit landed since the last nudge (evidence the agent acted).
NOW=$(date +%s)
if [[ -f "$LAST" ]]; then
  PREV=$(cat "$LAST" 2>/dev/null || echo 0)
  if (( NOW - PREV < 600 )); then exit 0; fi
fi
# If the most recent commit is a handoff/checkpoint, the agent already acted —
# stay quiet until context actually climbs again.
LASTMSG=$(git log -1 --pretty=%s 2>/dev/null || echo "")
if printf '%s' "$LASTMSG" | grep -qiE '^(checkpoint|handoff)'; then
  echo "$NOW" > "$LAST" 2>/dev/null || true
  exit 0
fi
echo "$NOW" > "$LAST" 2>/dev/null || true

PCT="$(cat "$FLAG" 2>/dev/null || echo '60+')"

cat <<EOF
[CONTEXT GUARD] Estimated context usage is ${PCT}% — at or past the ${CLAUDE_CHECKPOINT_PCT:-60}% checkpoint threshold.

Run the /checkpoint workflow now, before continuing:
  1. /handoff — docs-keeper writes/refreshes docs/HANDOFF.md (reconcile TODO + DELIVERY-PLAN first).
  2. Commit and push the handoff.
  3. Compact: run /compact if you can; otherwise tell the user "ready to /compact".
     Because the handoff is now fresh and the PreCompact + SessionStart(compact)
     hooks are wired, even an auto-compact from here is lossless — the point of
     checkpointing now is to make the seam clean, not to depend on self-compaction.
Then resume from the handoff's "Next concrete step".

If you are the pm-orchestrator (the main session): also confirm any in-flight
subagent work is merged, WIP-committed, or noted in the handoff first.
EOF

# Leave the flag in place; statusline.sh clears it once usage drops after compaction.
exit 0
