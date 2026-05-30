---
name: ship
description: >-
  Pre-PR checklist + open PR + wait for CI. Runs the local equivalent of the
  CI checks first, opens a PR with a properly-filled description against the
  default branch, and tracks CI status. Disable model-invocation — call this
  explicitly when a task is complete. Direct pushes to main are blocked by
  branch protection; this is the path.
disable-model-invocation: true
---

# /ship — Open a PR

This skill has `disable-model-invocation: true` — Claude won't run it
autonomously. Invoke explicitly when a task is genuinely ready.

## Pre-flight (run locally before opening the PR)

```bash
# Tests must be green.
<your project's test command>

# Lint clean.
<your project's lint command>

# Type check clean.
<your project's typecheck command>

# Diff against main is small and atomic.
git diff --stat origin/main...HEAD

# Commit history is clean — squash WIP commits if needed.
git log --oneline origin/main...HEAD
```

If any of these fail, stop and fix. Don't open a PR with red CI locally —
it'll be red in CI too, and that's noise for everyone.

## Step 1 — Confirm reviewer signed off

The `reviewer` agent must have signed off on this change. If they said
"hand off to external-reviewer", `/external-check` must have run and any
findings addressed.

## Step 2 — Confirm docs are current

`docs-keeper` should have updated:

- `docs/CHANGELOG.md` — one-line entry in `[Unreleased]`.
- `docs/TODO.md` — task marked done; any new TODOs added.
- `docs/ARCHITECTURE.md` — if anything structural changed.
- The relevant ADR — if a non-obvious choice was made.

If any of these are stale, fix before shipping.

## Step 3 — Open the PR

```bash
gh pr create \
  --base main \
  --head "$(git branch --show-current)" \
  --title "<type>: <one-line summary>" \
  --body-file <(cat <<'EOF'
## What
<one paragraph: user-visible behaviour change>

## Why
<one paragraph: spec/PRD/issue this satisfies; link to it>

## How
<bullets: the implementation approach>

## Tests
<bullets: what's covered, what isn't, what was tested manually>

## Docs
<bullets: which docs were updated>

## Risk
<one paragraph: what could go wrong; rollback plan>

## Reviewer checklist
- [ ] Reviewer agent: APPROVED
- [ ] External-reviewer: ran (non-trivial change) / not needed (trivial)
- [ ] Critic findings: addressed / accepted in ADR
- [ ] ADR added/updated: yes / no — N/A
EOF
)
```

PR title convention: `<type>: <summary>` where type is one of `feat`, `fix`,
`refactor`, `docs`, `test`, `chore`, `infra`. Lowercase. No period at end.

## Step 4 — Watch CI

```bash
gh pr checks --watch
```

CI runs `.github/workflows/ci.yml` (tests + lint + types) and triggers
`.github/workflows/external-review.yml` (the LLM-powered fresh-context
review). If CI fails, fix and push to the same branch — the PR will
re-trigger.

## Step 5 — Merge

Only after:

- All CI checks green.
- Required approvals satisfied (set by `scripts/setup-branch-protection.sh`).
- All review threads resolved.

Merge strategy: squash + merge (one logical change = one commit on main).
Edit the squash commit message to the PR title + a clean summary.

## Step 6 — Clean up

```bash
git checkout main
git pull
git branch -d <feature-branch>
git push origin --delete <feature-branch>
```

If the branch lived in a worktree:

```bash
git worktree remove ../<worktree-dir>
```

Update `docs/TODO.md` and `docs/HANDOFF.md` to reflect the merge.

## Notes

- Direct pushes to `main` are blocked. If you find you can push to main,
  branch protection isn't set up — run `scripts/setup-branch-protection.sh`.
- For genuinely tiny changes (typo fixes in docs), a PR is still required.
  The friction is the feature.
