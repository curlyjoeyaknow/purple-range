#!/usr/bin/env bash
# precompact-handoff.sh — PreCompact hook (the deterministic backstop).
#
# Fires immediately before Claude Code compacts the conversation (auto OR
# manual). A shell hook can't author the *narrative* HANDOFF — only Claude can
# do that, and the framework has it do so at the <60% checkpoint, well before
# this fires. THIS hook guarantees the *minimum* is never lost: a mechanical
# state snapshot + a transcript backup. SessionStart(compact) re-injects both.
#
# Wired in .claude/settings.json under hooks.PreCompact.
# Receives JSON on stdin: { transcript_path, trigger ("manual"|"auto"), ... }

set -uo pipefail

STATE_DIR=".claude/state"
BACKUP_DIR=".claude/backups"
mkdir -p "$STATE_DIR" "$BACKUP_DIR" 2>/dev/null || true

INPUT="$(cat 2>/dev/null || true)"
TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)"
TRIGGER="$(printf '%s' "$INPUT" | jq -r '.trigger // "unknown"' 2>/dev/null || true)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. Back up the transcript so nothing is unrecoverable.
if [[ -n "${TRANSCRIPT:-}" && -f "$TRANSCRIPT" ]]; then
  cp "$TRANSCRIPT" "$BACKUP_DIR/transcript-precompact-$(date -u +%Y%m%d-%H%M%S).jsonl" 2>/dev/null || true
fi

# 2. Write a mechanical snapshot of where the repo is right now.
{
  echo "# Pre-compaction snapshot — $TS  (trigger: $TRIGGER)"
  echo
  echo "> Auto-written by the PreCompact hook. The rich, reasoned handoff is in"
  echo "> docs/HANDOFF.md (refreshed by the orchestrator at the <60% checkpoint)."
  echo "> This file is the mechanical backstop in case that one is stale."
  echo
  echo "## Branch & status"
  echo '```'
  git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(no git)"
  git status --short 2>/dev/null || true
  echo '```'
  echo
  echo "## Recent commits"
  echo '```'
  git log --oneline -n 15 2>/dev/null || true
  echo '```'
  echo
  echo "## Worktrees (parallel streams in flight)"
  echo '```'
  git worktree list 2>/dev/null || true
  echo '```'
  echo
  echo "## In-progress tasks (from docs/TODO.md)"
  echo '```'
  grep -nE 'in-progress|in_progress|\[ \].*CRITICAL|blocked' docs/TODO.md 2>/dev/null | head -n 30 || echo "(no docs/TODO.md or no matches)"
  echo '```'
  echo
  echo "## Active gate (from docs/DELIVERY-PLAN.md)"
  echo '```'
  grep -nE 'adversarial|hard|loop budget|escalat' docs/DELIVERY-PLAN.md 2>/dev/null | head -n 20 || echo "(no docs/DELIVERY-PLAN.md or no matches)"
  echo '```'
} > "$STATE_DIR/last-snapshot.md" 2>/dev/null || true

# 3. Flag that a restore is warranted on the next (post-compact) session start.
echo "$TS $TRIGGER" > "$STATE_DIR/restore-pending" 2>/dev/null || true

# Non-blocking: never fail compaction because of this hook.
exit 0
