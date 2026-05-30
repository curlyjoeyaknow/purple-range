#!/usr/bin/env bash
# statusline.sh — statusLine command + proactive context monitor.
#
# Claude Code calls this to render the status line, passing session JSON on
# stdin. We piggyback on it to estimate context usage and, when it crosses the
# checkpoint threshold (default 60%), drop a flag file that the
# checkpoint-nudge UserPromptSubmit hook acts on.
#
# Wired in .claude/settings.json under the top-level "statusLine" key.
#
# IMPORTANT — heuristic note:
#   Claude Code's exact context-usage field in the statusline payload has
#   changed across versions. This script first tries known native fields, then
#   falls back to estimating from transcript size (bytes/4 ≈ tokens). The
#   estimate is deliberately conservative (tends to OVER-count), so it
#   checkpoints a little early — which is exactly what we want. Tune with:
#     CLAUDE_CHECKPOINT_PCT   (default 60)
#     CLAUDE_CONTEXT_TOKENS   (default 200000)
#   Confirm the native field against https://code.claude.com/docs/en/statusline
#   and replace the estimate block if your version exposes usage directly.

set -uo pipefail

THRESHOLD="${CLAUDE_CHECKPOINT_PCT:-60}"
WINDOW="${CLAUDE_CONTEXT_TOKENS:-200000}"
STATE_DIR=".claude/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true

INPUT="$(cat 2>/dev/null || true)"

# --- Try native fields first (names vary by version; harmless if absent) ---
PCT="$(printf '%s' "$INPUT" | jq -r '
  (.context.used_percent // .cost.context_used_percent // .context_used_percent // empty)
' 2>/dev/null || true)"

# --- Fallback: estimate from transcript size ---
if [[ -z "${PCT:-}" || "$PCT" == "null" ]]; then
  TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)"
  if [[ -n "${TRANSCRIPT:-}" && -f "$TRANSCRIPT" ]]; then
    BYTES="$(wc -c < "$TRANSCRIPT" 2>/dev/null || echo 0)"
    EST_TOKENS=$(( BYTES / 4 ))
    PCT=$(( EST_TOKENS * 100 / WINDOW ))
    [[ "$PCT" -gt 100 ]] && PCT=100
  else
    PCT=0
  fi
fi

PCT_INT="${PCT%.*}"; PCT_INT="${PCT_INT:-0}"

# --- Trip / clear the checkpoint flag ---
if [[ "$PCT_INT" -ge "$THRESHOLD" ]]; then
  echo "$PCT_INT" > "$STATE_DIR/checkpoint-needed" 2>/dev/null || true
  MARK="⚠ CHECKPOINT"
else
  rm -f "$STATE_DIR/checkpoint-needed" 2>/dev/null || true
  MARK="✓"
fi

# --- Render the status line ---
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')"
printf 'ctx %s%% %s | branch %s' "$PCT_INT" "$MARK" "$BRANCH"
exit 0
