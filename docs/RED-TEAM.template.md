# RED-TEAM

Risk reviews from `/critique` and `/phase-review`. Maintained by the
`docs-keeper` agent. This is where the `critic`'s findings live so future-you
can see what was considered and how it was resolved.

Findings use the critic's severity scale:

- 🔴 **Fatal** — proposal cannot ship as-is.
- 🟠 **Serious** — likely to bite within 6 months.
- 🟡 **Smell** — might be fine, but worth a sentence in the ADR.

---

## YYYY-MM-DD — `/critique` on <target>

> Target: `<doc path / commit / PR>`
> Invoked by: <user / pm-orchestrator>
> Critic: `claude-opus-4-7` (or whichever model)

### What the critic understood the proposal to be

<1–3 sentences — verbatim from critic output>

### Resolved

- 🔴 **<finding name>**
  - Violated assumption: …
  - Failure mode: …
  - Falsifiable test: …
  - **Addressed by:** <commit / PR / ADR link> on YYYY-MM-DD

### Open followups

- 🟠 **<finding name>** → TODO **F-NNN**
  - Violated assumption: …
  - Failure mode: …
  - Falsifiable test: …
  - Trigger to address: <when this becomes blocking>

### Accepted risks

- 🟡 **<finding name>**
  - Why accepted: <reason>
  - Noted in: ADR-NNNN section "Accepted risks"
  - Revisit when: <trigger condition>

### Three forcing questions — and our answers

1. **Q:** <critic's question>
   **A:** <our answer; or link to ADR / PRD section where answered>
2. …
3. …

---

## YYYY-MM-DD — Phase review: `<phase-name>`

> Range: `<from-ref>..<to-ref>`
> Files changed: <N>  Commits: <N>
> Triggered by: workflow_dispatch / pm-orchestrator

### What this phase delivered

<one paragraph against the spec>

### Reviewer findings (full-context)

<reviewer's structured output>

### External-reviewer findings (fresh-context)

<external-reviewer's structured output>

### Critic findings (state-of-system red-team)

<critic's structured output, focused on the system as it now exists, not the
diff>

### Spec / doc audit

- [ ] `docs/PRD.md` claims match phase's actual behaviour: yes | no — <note>
- [ ] `docs/ARCHITECTURE.md` reflects what was built: yes | no — <note>
- [ ] All ADRs honoured (no silent violations): yes | no — <note>
- [ ] `docs/CHANGELOG.md` covers every meaningful change: yes | no — <note>
- [ ] `docs/OPEN-QUESTIONS.md` current: yes | no — <note>
- [ ] `docs/TODO.md` reflects reality: yes | no — <note>

### Decision

**GO** | **NO-GO** | **GO-WITH-FOLLOWUPS**

### Followups (if go-with-followups)

- TODO **F-NNN**: <followup, with owner and deadline>

### Milestone tag

`phase-N-end` — created YYYY-MM-DD, pointing at `<commit-sha>`.
