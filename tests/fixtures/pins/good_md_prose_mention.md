# Design note (prose only — no fenced code)

Avoid `nginx:latest` in production; we never pin to `:latest` and we forbid a
bare `git clone https://example.com/repo.git` without a pinned ref.

These are PROSE mentions of the anti-patterns (inline backticks and running
text), not commands inside a fenced ``` code block. The gate MUST NOT flag
them — otherwise the very documentation that explains the pin policy would
turn the build red. (Decision pinned in tests/test_pins_gate.py: only fenced
code blocks in .md are scanned, never prose.)
