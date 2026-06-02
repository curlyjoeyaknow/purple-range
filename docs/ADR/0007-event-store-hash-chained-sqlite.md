# ADR-0007 — EventStore: a hash-chained SQLite append-only log (tamper-EVIDENCE, not tamper-RESISTANCE)

> Status: accepted
> Date: 2026-05-31
> Deciders: owner (memeworldorder2024), architect
> Supersedes: —

## Context

Purple Range's whole scoring spine is a **fold over an append-only event log**
(ADR-0001 [`0001-manifest-oracle-event-sourced-scoring.md`](0001-manifest-oracle-event-sourced-scoring.md)).
The scoreboard, the rank signal, the audit trail, the replay/undo capability —
all of it is derived state computed by reducing that log. The store is therefore
the load-bearing persistence substrate for everything downstream: the Scorer
(T-111) folds it, the validation harness (T-801) folds it, and GATE A's second
reviewer exists specifically to attack its chain integrity and replay
determinism. T-110 implements it; **this ADR must land first** (charter #6:
non-obvious decisions become ADRs before the code).

ADR-0001 already settled the *spine shape*: six versioned event types, each row
carrying `seq`, `prev_hash`, `row_hash = H(prev_hash || canonical_json(event))`,
plus `correlation_id`/`causation_id` lineage; `verify_chain()` detects
tampering/reordering; the scoreboard is the fold. ADR-0001 also defaulted to
SQLite over the small-tier JSONL default and recorded the choice as Q-005 for
explicit sign-off. **This ADR is that sign-off**, and it pins the integrity
semantics precisely enough that T-110's tester can write
`test_verify_chain_detects_tampered_row` and
`test_fold_replay_reproduces_scoreboard` against a defined contract rather than
a vibe.

The forces in play:

- **The port is already locked.** [`ports/__init__.py`](../../ports/__init__.py)
  pins the `EventStore` Protocol surface — `append(events) -> list`,
  `fold(reducer, init) -> Any`, `replay_from(seq) -> Iterator`,
  `verify_chain() -> bool` — finalised at T-101 (PR #9, merged). This ADR must
  be **consistent with that surface and must not invent a new port** (charter
  #3). The design space is the *adapter behind* those four methods, not the
  method signatures. Everything pinned below (the authoritative `append`, the
  `list[dict]` return, the first-bad-`seq` log line) lives **inside** those
  four signatures and requires **no port change** — confirmed against the
  locked Protocol.

- **The contracts are already locked.** [`contracts/schemas.py`](../../contracts/schemas.py)
  pins the 13 persisted shapes. The six chained event types
  (`scenario_generated`, `attack_executed`, `scenario_aborted`, `submission`,
  `verification_result`, `score_awarded`) each carry `version:int` first,
  then `seq:int` and `prev_hash:str` as first-class declared fields — **but
  not `row_hash`**. Two specifics this ADR must design around:
  - `seq`/`prev_hash` are **REQUIRED, non-defaulted** fields on every event
    dataclass (lines 212–213 and the parallel blocks), so a caller cannot omit
    them — it must pass *placeholder* values the store then overwrites (see B2
    / §1a below).
  - the dataclasses are `@dataclass(frozen=True)` — attribute rebinding raises
    — so the store cannot mutate a caller's instance to stamp the assigned
    `seq`/`prev_hash`. It reconstructs via `dump(event)`, which returns an
    independent **deep-copied plain dict** ([`schemas.py`](../../contracts/schemas.py)
    line 689), and patches *that dict* (see §1a).

  [`contracts/__init__.py`](../../contracts/__init__.py)
  pins `canonical_json` (`json.dumps(obj, sort_keys=True,
  separators=(",", ":"))`, lines 53–60) as the exact bytes the chain hashes
  over. **A caveat the chain inherits and must pin:** that call leaves
  `allow_nan` and `ensure_ascii` at the `json` module DEFAULTS
  (`allow_nan=True`, `ensure_ascii=True`), and the `submission` /
  `attack_executed` events carry **learner-supplied `evidence: dict` declared
  free-form** as `{"type": "object"}` (lines 185/255/493/604). So absent an
  explicit constraint, a `NaN`/`Infinity` float or a non-string key inside
  `evidence` could enter the hashed bytes — and `json.dumps`' default
  `NaN`/`Infinity` tokens are not valid JSON, so any re-parse-then-re-serialize
  path would diverge. The `sha256` function and the canonicalizer are settled;
  **what this ADR pins is the value-domain and flag discipline the store
  enforces when it calls them** (§0 below) so the hashed input is provably
  stable. Our job is to define *how the store computes and persists the chain
  over those bytes*.

- **Charter non-negotiables.** Append-only events with derived state (#4);
  `version:int` on everything persisted (#2, additive evolution); ports &
  adapters with a clean fake at the boundary (#3); stdlib-only posture (no
  third-party dependency). These constrain the adapter choice hard: a store
  that needs `psycopg`/`SQLAlchemy`/a server process is off the table.

- **The status quo this generalizes.** [`lab/ledger.py`](../../lab/ledger.py)
  (T-004) is the existing append-only skeleton: a `ValidationEvent`, a `Ledger`
  Protocol with `append` only, a `JsonlLedger` production adapter (one
  `json.dumps` line per event, append-mode), and an `InMemoryLedger` fake. It
  has **no `seq`, no chain, no fold, no replay, no transaction boundary across
  rows**. It proved the append-only *pattern* at commit-1 scale; the scoring
  EventStore is the grown-up generalization that the rank signal depends on.

- **The scope is sequential and single-writer (ADR-0005).** At
  sequential/scenario-scoped scope there is exactly **one logical scoring
  writer** — the orchestrator. ADR-0001 explicitly *dropped* "concurrent
  writers" as a justification for SQLite. So the design must NOT lean on
  multi-writer concurrency to justify itself; the real justifications are
  transactional multi-row append and indexed seek.

The genuine tradeoff: **how much integrity machinery is worth it for a solo
lab?** Too little (plain JSONL) and a partial multi-row write can leave a broken
chain with no transaction boundary, and a full-file scan backs every replay.
Too much (signing, external anchoring, WORM media) and we spend the MVP budget
defending against a threat model — a privileged attacker on the owner's own
host — that does not exist for a single-user training tool. The honest answer
sits in the middle and must be *named honestly*, because the easy lie ("the log
is tamper-proof") is exactly the kind of false assurance the product promise
(trustworthy rank) cannot afford.

What we know: the port and contracts are locked; stdlib `sqlite3` ships with
CPython; canonical-JSON discipline is already in `contracts`. What we **don't**
fully know yet (deferred, not papered over): the exact on-disk DDL/index names
and the precise fold-reducer signature shape — those are T-110/T-111
implementation details that finalise additively against this ADR, the same way
ADR-0002's port is finalised by its implementing task.

## Decision

> We will implement the locked `EventStore` port as a **`SqliteEventStore`
> production adapter over one stdlib-`sqlite3` `events` table** whose every row
> carries a monotonic `seq` and a `row_hash` over a **framed** input
> `sha256(prev_hash_bytes + b"\x00" + canonical_bytes)` forming a forward
> hash-chain; `append` is **authoritative** over `seq`/`prev_hash` and returns
> the fully-populated persisted rows; the store **hashes the exact bytes it
> persists and verifies by re-reading those same bytes**; `verify_chain()`
> means "recompute the chain from genesis and assert every stored `row_hash`
> and `prev_hash` matches"; and `InMemoryEventStore` is the list-backed fake
> with byte-identical chain math — accepting explicitly that this chain is
> **tamper-EVIDENCE, not tamper-RESISTANCE**.

The design:

**0. Hashed-input stability — the preconditions the store enforces (B1).**
The chain is only meaningful if the bytes it hashes are *provably* the same
bytes every time the same logical event is encountered. Four invariants pin
that, all enforced by the store/loader, none requiring a contract edit *today*
(but see Open questions):

- **Serializer flags are explicit, and the chain requires `allow_nan=False`.**
  When the store canonicalizes an event for hashing it MUST use a no-NaN
  serialization: a `NaN`, `Infinity`, or `-Infinity` float anywhere in the
  event (overwhelmingly via free-form `evidence`) MUST **raise at `append`
  time** and **never enter the chain**. Rationale: `json.dumps`' default
  `allow_nan=True` emits the bare tokens `NaN`/`Infinity`, which are *not legal
  JSON*; any consumer that re-parses (a future export/import, a re-derivation)
  would either reject them or round-trip them differently, silently diverging
  the hash. The store therefore treats non-finite floats as a precondition
  violation, not as data. **Implementation note for T-110:** because the locked
  `canonical_json` (lines 53–60) passes neither flag, the store must obtain the
  no-NaN guarantee at its own call site — e.g. validate finiteness on the
  patched event dict before canonicalizing, or canonicalize through a local
  `json.dumps(..., sort_keys=True, separators=(",",":"), allow_nan=False)` that
  produces *byte-identical* output to `canonical_json` for all finite,
  in-domain inputs (the two differ only on the inputs we are forbidding). See
  Open questions: pinning `allow_nan=False` *inside* `contracts.canonical_json`
  is the cleaner long-term home and is recorded there as a required follow-up;
  this ADR does **not** edit `contracts`.
- **`evidence` value domain is JSON-primitive-only.** The loader/store treats
  `evidence` (and any free-form dict) as constrained to JSON primitives:
  objects, arrays, strings, finite numbers, booleans, and null, with
  **string-only keys**. No `NaN`/`Inf`, no non-string keys, no non-JSON
  Python objects (sets, bytes, datetimes, etc.). This is a precondition the
  loader/store enforces on ingest; an out-of-domain `evidence` is rejected
  before it can reach the hash. (`ensure_ascii` is left at default `True`: it
  changes the *encoding* of non-ASCII strings but is deterministic and stable,
  so it does not threaten chain stability — the conformance fixtures in M2
  include a non-ASCII string to lock exactly that.)
- **The concatenation is framed, not bare.** `row_hash` is computed over a
  **framed** input rather than the ambiguous string concatenation
  `prev_hash + canonical_json(event)`:

  ```
  row_hash = sha256(prev_hash.encode("ascii") + b"\x00" + canonical_bytes).hexdigest()
  ```

  where `canonical_bytes = canonical_json(patched_event_dict).encode("utf-8")`
  and `prev_hash` is the stored 64-hex token. Reasoning for choosing framed
  over a documented invariant: `prev_hash` *is* a fixed-width 64-hex token, so
  bare concatenation is in fact unambiguous **today** — but that unambiguity is
  a load-bearing property that lives only in prose, and a single future change
  to the hash encoding (a different digest, a base64 form, a length change)
  would silently make `prev_hash + payload` parseable two ways and corrupt the
  chain semantics with no test failure at the framing layer. A one-byte `\x00`
  separator that **cannot occur** in either a hex token or in
  `separators=(",",":")` canonical JSON costs nothing, makes the input
  self-delimiting independent of the token width, and converts "encoding change
  is silently chain-corrupting" into "encoding change is loudly different
  bytes." The tradeoff is the one downside: the framed bytes are **not** the
  literal concatenation a reader might assume from ADR-0001's
  `H(prev_hash || canonical_json(event))` shorthand — so `||` is hereby pinned
  to mean *this* framing, and **any change to the framing or hash encoding is a
  chain-breaking migration** (re-fold + re-chain under a migration ADR), called
  out alongside the breaking-schema-change cost in Consequences.
- **Hash the bytes you persist; verify by re-reading those bytes.** The SQLite
  adapter stores the canonical-JSON event string in `payload TEXT` and computes
  `row_hash` over **that exact string's bytes** (framed as above). `verify_chain`
  re-reads the stored `payload` bytes and re-hashes *them* — it does **not**
  re-parse `payload` into a dict and re-`dump`/re-canonicalize it. This kills
  the entire round-trip-divergence class (any subtle re-encode, float
  re-formatting, key-order or escaping difference between write-time and
  read-time serialization): verification compares stored-`row_hash` against a
  hash of the stored bytes, so the only thing that can fail the check is an
  *actual mutation of the persisted bytes* — which is exactly the tamper signal
  we want. The InMemory fake holds the same canonical string per row and
  follows the identical rule.

**1. The chain, defined precisely.** "The chain" is the totally-ordered
sequence of stored rows, ordered by `seq` ascending. Concretely:

- **Genesis.** `seq` is a monotonic integer assigned by `append`, starting at
  `1` for the first row ever appended (the table is otherwise empty). The
  genesis `prev_hash` is a **chosen fixed 64-hex sentinel** `"0" * 64`,
  distinct from any real predecessor `row_hash` and used only to mean "no
  predecessor." It is **not** "the all-zero sha256 digest" (sha256 of no input
  is `e3b0c4…`, not 64 zeros) — it is an arbitrary reserved constant picked
  because it is an obvious, fixed-width, never-naturally-produced token, chosen
  so an empty-store `verify_chain()` is trivially true and the first row chains
  off a constant, not off "nothing."
- **Per-row hash.** For each row, `row_hash` is the framed `sha256` of §0:
  `sha256(prev_hash.encode("ascii") + b"\x00" + canonical_bytes)`, where
  `canonical_bytes` is the UTF-8 encoding of `canonical_json(patched_event_dict)`
  and `patched_event_dict` is `dump(event)` with its `seq`/`prev_hash` replaced
  by the store-assigned values (see §1a). `canonical_json` is the contracts
  module's sorted-keys / no-whitespace serializer — the *exact* same function
  used for `manifest_hash`, so there is one and only one canonicalization
  discipline in the codebase (with the no-NaN precondition of §0 layered on at
  the store's call site).
- **The link.** Row *n*'s `prev_hash` MUST equal row *(n-1)*'s `row_hash`
  (genesis's `prev_hash` is the sentinel). This is what makes the chain a
  chain: each link binds to the cumulative history before it, so any change to
  an earlier row's bytes breaks every `prev_hash`/`row_hash` equality from that
  point forward.

**1a. `append` is AUTHORITATIVE over `seq`/`prev_hash`, and its return shape is
pinned (B2).** This is the integrity boundary; it is pinned here, not left to
T-110:

- **Authority.** `append(events)` **ignores and overwrites** any caller-supplied
  `seq` and `prev_hash`. For the batch it reads the current chain tip
  (`tip = ` the max-`seq` row, or the genesis sentinel for an empty store),
  then for each event in batch order assigns `seq = previous_seq + 1` and
  `prev_hash = previous_row_hash` (the first event's `prev_hash` is the tip's
  `row_hash`, or the genesis sentinel), computes `row_hash` per §0/§1, and
  chains the next event off it. A **wrong caller-supplied `prev_hash` MUST be
  overwritten, not trusted** — trusting it would let a caller forge linkage and
  defeat the chain. The store's authority over exactly these two fields *is* the
  integrity boundary.
- **Placeholders.** Because `seq`/`prev_hash` are required non-defaulted fields,
  callers construct events with **placeholders** — by convention `seq = 0` and
  `prev_hash = "0" * 64` — purely to satisfy the dataclass. These values carry
  no meaning and are discarded by `append`. (Using the genesis sentinel as the
  placeholder `prev_hash` is harmless: it is overwritten before hashing for
  every non-first batch and is the correct value for a genesis append anyway.)
- **Frozen-instance mechanism.** Since the dataclasses are `frozen=True`, the
  store does **not** mutate the caller's instance. It calls `dump(event)` →
  obtains an independent deep-copied plain dict → patches `dict["seq"]` and
  `dict["prev_hash"]` to the assigned values → canonicalizes/hashes *that dict*
  → persists the canonical string and the `row_hash`. No frozen-attribute
  rebinding occurs.
- **Return shape.** `append` **returns `list[dict]`**: one fully-populated
  persisted row per input event, in `seq` order, each dict being the patched
  event dict **plus** its assigned `row_hash` (i.e. the exact persisted shape,
  a superset of the dataclass fields). This is consistent with the locked
  Protocol's `append(events) -> list` (a `list[dict]` *is* a `list`), so **no
  port change is needed**. Downstream relies on this: the Scorer (T-111) and the
  validation harness consume the returned rows' assigned `seq`/`prev_hash`/
  `row_hash` rather than re-reading; §2 `verify_chain` and T-111's fold both
  depend on `append` having been authoritative and on this populated return.
- **`fold`/`replay_from` yield the SAME persisted-dict shape `append` returns**
  (added during T-110, which pinned it in tests). The store reconstructs each
  item from the stored `payload` (`json.loads`) plus the row's `seq`/`prev_hash`/
  `row_hash` columns — it does **not** re-hydrate typed dataclasses (that would
  couple the store to the contract catalog and the per-shape loaders). Consumers
  that want a typed view call `contracts.load_<shape>()` on the yielded dict. So
  the store's whole I/O surface is *dataclasses in, persisted dicts out*.

**2. `verify_chain()` semantics — exact pass/fail.** Returns `True` iff,
reading all rows ordered by `seq` and re-hashing the **stored `payload`
bytes** (§0 "verify by re-reading"):

- `seq` is a gap-free monotonic run `1, 2, 3, …, N` (no gap ⇒ no silent
  deletion; no duplicate ⇒ no silent insertion-by-overwrite);
- the first row's `prev_hash` is the genesis sentinel;
- for every row, `row_hash == sha256(prev_hash_bytes + b"\x00" +
  stored_payload_bytes)` (no row's persisted bytes were edited — its stored
  `row_hash` no longer matches them);
- for every non-genesis row, `prev_hash == previous_row.row_hash` (no row was
  reordered or its predecessor altered).

It returns `False` (never raises for a tamper case) on **any** row edit,
reorder, deletion, or insertion. An empty store returns `True`. This is the
falsifiable contract `test_verify_chain_detects_tampered_row` pins. **Operator
diagnosis:** on a `False` verdict the adapter's internal verify logs a single
line naming the **first bad `seq`** (the lowest `seq` at which an equality
fails), so the operator can locate the break; the **public port signature stays
`-> bool`** (no diagnostic surface added to the port — no port change). See M3.

**3. SQLite production adapter, behind the existing port.** One `events`
table, columns at minimum `seq INTEGER PRIMARY KEY` (monotonic, indexed by
construction), `event_type TEXT`, `payload TEXT` (the canonical-JSON event
bytes — the exact bytes hashed, per §0), `prev_hash TEXT`, `row_hash TEXT`.
`append(events)` writes the whole batch in **one transaction**
(`BEGIN … COMMIT`), assigning consecutive `seq` values and chaining
`prev_hash`/`row_hash` across the batch *and* off the current chain tip (§1a) —
so a multi-row step (e.g. `verification_result` + `score_awarded`) either lands
wholly-chained or not at all; a crash mid-batch rolls back and never leaves a
broken chain. `replay_from(seq)` is an indexed `WHERE seq >= ? ORDER BY seq`
seek (O(log N) to the start row), yielding events in `seq` order.
`fold(reducer, init)` replays from genesis applying `reducer` left-to-right.
`verify_chain()` streams rows in `seq` order and applies §2. All via stdlib
`sqlite3` — **no third-party dependency**, consistent with the stdlib-only
posture and with `contracts`/`ports` importing nothing vendored.

**3a. Durability PRAGMAs are PINNED here, not deferred (M4).** The #1 reason
SQLite beats JSONL is the atomic, durable multi-row transaction (§"No broken
chains" in Consequences). That claim is **only true under a durable sync
mode**. This ADR therefore **pins** the connection PRAGMA floor:
`synchronous = FULL` (the default rollback-journal durable mode), **or**
`synchronous = NORMAL` with `journal_mode = WAL` — and *only* the WAL variant,
with its documented risk recorded. T-110 **may not** weaken this below the
NORMAL+WAL floor (e.g. `synchronous = OFF`, or `journal_mode = MEMORY`/`OFF`)
to chase the append-latency NFR without a **follow-up ADR**; the durability
claim is load-bearing for the integrity story and is not a free latency knob.
The documented risk of the NORMAL+WAL variant: a power loss / OS crash can lose
the most recent committed transaction(s) (the WAL frames not yet checkpointed)
even though the *database file* stays internally consistent and `verify_chain`
still passes on what survived — i.e. you can lose the tail, but you cannot get a
*broken* chain. The exact choice between FULL and NORMAL+WAL (and the
checkpoint cadence) is the one PRAGMA decision T-110 finalises, *within* this
pinned floor.

**4. JSONL stays the conceptual model and the fake stays the boundary.**
JSONL-append remains the *mental model* of "append-only log, one record per
line" and remains the shape of `lab/ledger.py`'s `JsonlLedger` for the
lighter-weight `ValidationEvent` stream (T-801). `InMemoryEventStore` (locked
as the T-101 fake) is the **test boundary**: a list-backed adapter implementing
the identical `append`/`fold`/`replay_from`/`verify_chain` semantics — same
genesis sentinel, same `canonical_json`, same framing, same authoritative
`append`, same "hash the bytes you keep" rule — so core tests (Scorer T-111,
every parallel S1/S2/S3 stream) run against the fake with **no SQLite file
touched**. If the fake and the SQLite adapter ever disagree on a fold or a
`verify_chain` verdict, the port surface is wrong, not the fake (charter
heuristic). A shared conformance test runs both through the same property
assertions (M2).

**4a. Conformance fixture set is PINNED (M2).** The shared InMemory/SQLite
conformance suite MUST include, at minimum, these `evidence`/value shapes,
appended through both adapters and asserted to produce **byte-identical
`row_hash`** per row and an **identical `verify_chain` verdict**:

- a **finite float** in `evidence` (e.g. `{"score": 0.5}`) — locks float
  serialization stability across adapters and across close-reopen;
- a **non-ASCII string** in `evidence` (e.g. `{"note": "café — δ"}`) — locks
  that the default `ensure_ascii=True` encoding is deterministic and identical
  on both sides;
- a **nested-dict `evidence`** (e.g. `{"a": {"b": [1, 2, {"c": true}]}}`) —
  locks that `sort_keys` canonicalization is recursive and stable;
- a **close-reopen / persistence round-trip** for the SQLite adapter: append
  rows, close the connection, reopen the file, and assert `verify_chain` is
  still `True` and the stored `row_hash` values are byte-identical to those
  returned by the original `append`.

These fixtures are tied directly to §0's "hash the bytes you persist, verify by
re-reading those bytes" rule: the round-trip case is precisely what proves the
write-time and read-time byte streams agree. (A `NaN`/`Inf` fixture is the
*negative* case: it MUST raise at `append` and never produce a row — see §0 and
the corresponding negative conformance test.)

**5. Determinism and additive evolution.** `fold` and `replay_from` are
**deterministic and order-stable** — always ordered by `seq`, which `append`
assigns monotonically — so the same log always reduces to the same scoreboard
(the replay-reproduces-rank property GATE A reviewer-2 checks). **One
distinction to keep honest (N2):** `correlation_id`/`causation_id` are
**Rng-minted** ([`contracts.mint_correlation_id`](../../contracts/__init__.py),
F-006) and **ARE part of the hashed bytes**. So "deterministic fold" means
*folding an existing log reproduces the same scoreboard* — it does **not** mean
two independent runs produce the same log. Reproducible *regeneration* of an
identical log (and thus identical `correlation_id`s and `row_hash`es) depends
on the `Rng` **seed**; a different seed yields different ids, different bytes,
and a different (but internally valid) chain. Replay-determinism over a fixed
log and seeded-reproducibility of a fresh log are two separate properties and
GATE A should test them as such. Schema evolution is **additive via
`version:int`** (charter #2): a new optional field on, say,
`score_awarded(version:2 → 3)` changes the canonical-JSON bytes only for *new*
rows; old rows keep their original bytes and original `row_hash`, so the chain
stays intact and the fold reducer dispatches on `(event_type, version)` to
handle both shapes. A *removal* or field rename is NOT additive: it changes the
canonical bytes of historical rows, invalidating every downstream `row_hash`,
and therefore requires a migration ADR plus a re-fold/re-chain (see
Consequences). The §0 **framing/hash-encoding** is on the same footing: changing
it is a chain-breaking migration, not an additive change.

This ADR fixes the integrity semantics and the adapter choice. The exact DDL,
index names, and reducer signature are finalised additively by **T-110** against
this contract.

## Consequences

- **Positive:**
  - **Trustworthy rank from a log whose *recorded verdicts* are
    tamper-evident.** The fold is deterministic and replayable; `verify_chain()`
    is a precise, falsifiable tripwire for accidental corruption, out-of-band
    edits, and reordering *of what was written*. This is a necessary pillar of
    honest rank — but note the threat-model paragraph below: the chain certifies
    the *integrity of the recorded log*, not the *honesty of the oracle inputs*
    that produced each verdict. Both must hold for rank to be trustworthy; this
    store owns the first, not the second.
  - **No broken chains from partial writes.** The single-transaction multi-row
    `append` (under the §3a durable-PRAGMA floor) means a crash between
    `verification_result` and `score_awarded` rolls back wholly — there is no
    half-chained state for the fold to trip on. This is the #1 concrete reason
    SQLite beats bare JSONL here (it is a transaction boundary JSONL
    structurally lacks) **and it is exactly why §3a pins `synchronous`/
    `journal_mode`: weaken them and this benefit evaporates.**
  - **O(log N) seek-replay and verify.** The indexed monotonic `seq` makes
    `replay_from(seq)` and chain verification seek to a row rather than scan the
    whole file, which keeps the NFR budget (append < 5 ms/event, full rebuild
    < 1 s at personal volume) comfortable.
  - **Zero third-party dependency.** stdlib `sqlite3` keeps the stdlib-only
    posture intact — one fewer supply-chain surface, one fewer pin to chase
    (charter #10), consistent with `ports`/`contracts` importing nothing
    vendored.
  - **Clean test boundary.** `InMemoryEventStore` makes the entire scoring core
    CI-testable with no file I/O and no SQLite, and the shared conformance test
    (§4a) proves the fake and the real adapter agree byte-for-byte.

- **Negative:**
  - **Tamper-EVIDENCE, not tamper-RESISTANCE — this is a first-class
    limitation, not a footnote.** A holder of the DB file (the owner, or anyone
    with write access to it) can rewrite any event and recompute the entire
    forward chain from that row onward, producing a perfectly valid-looking log
    that `verify_chain()` passes. The chain detects *accidental* corruption,
    *out-of-band* edits by a process that doesn't know to re-chain, *reordering*,
    and *truncation/insertion* — it does **not** prevent a privileged,
    chain-aware attacker. **Threat model, stated explicitly — and the honest
    split between two integrity properties (M1):**
    - *Log integrity* (what the chain provides): evidence that the **recorded
      verdicts have not been tampered with after the fact**. If a row's bytes
      change, or rows are reordered/deleted/inserted out-of-band, `verify_chain`
      fails. This is a property *of this store*.
    - *Scoring integrity* (what the chain does **not** provide): the **honesty
      of the oracle inputs at scoring time** — the scenario manifest, the
      ground-truth JSONL, the `service_probe`, and anything else the Scorer
      reads to decide pass/fail. In a CTF-style lab **the player has HOST
      ACCESS** (ADR-0005: single-user, single-host), so the player can in
      principle influence those inputs *before* a verdict is computed and
      appended. The chain will then faithfully and tamper-evidently record a
      verdict derived from manipulated inputs — a *correctly chained lie*. This
      store **cannot** detect that; it is **not** a property of the EventStore.
      Where it is handled: input honesty is a **single-owner-trust** assumption
      (the owner does not cheat their own training rank — same self-defeating
      logic as the tamper-resistance accept below) plus whatever validation the
      oracle/manifest layer (ADR-0001, ADR-0006 containment) applies at read
      time; it is **explicitly accepted as out of scope for this store** and
      pointed at the Scorer/oracle layer, not papered over here.

    The earlier "trustworthy rank from a trustworthy log" framing is
    deliberately **softened**: the log is *tamper-evident over recorded
    verdicts*, which is necessary but not sufficient for trustworthy rank;
    scoring integrity rests on single-owner trust, not on this chain.

    What tamper-*resistance* would require — and why it is out of scope for the
    MVP: (a) **cryptographic signing** of each `row_hash` with a key held off
    the box (forging then needs the key, not just file access); (b) **external
    anchoring** of periodic chain checkpoints to an append-only third party (a
    public ledger, a notarization service, a remote witness) so local rewrites
    are externally contradictable; (c) an **append-only / WORM medium** the
    owner cannot rewrite. All three add operational machinery, key management,
    and (for anchoring) a network dependency that fights the fail-closed
    containment invariant (ADR-0006) — defending a threat that does not exist
    for a solo, single-owner training lab. Honest property, named so no one
    later mistakes the chain for proof against the owner *or* for proof that the
    inputs behind a verdict were honest.
  - **Corruption recovery is manual restore-from-backup — no automatic
    re-chain (M3).** For the MVP, the recovery posture on a failed
    `verify_chain` is explicitly: the adapter's internal verify **logs the first
    bad `seq`** (the public port stays `-> bool`, §2), the operator is alerted
    that the log is compromised, and **recovery is a manual restore from a known
    -good backup** — there is **no automatic re-chain, no quarantine-and-replay,
    no self-heal**. This is a conscious MVP scope cut: auto-re-chaining a
    corrupted log is precisely the capability a chain-aware attacker would
    abuse, and building it for a single-owner lab inverts the tamper-evidence
    value. For the **truncation** sub-case (a clean tail loss, e.g. the
    NORMAL+WAL tail-loss risk of §3a), `scenario_aborted.last_good_seq` (a
    declared field, [`schemas.py`](../../contracts/schemas.py) line 243) gives a
    recorded high-water mark a future recovery procedure could fold to the last
    intact scenario boundary; for the MVP this is **noted, not automated** —
    restore-from-backup remains the recovery path. Revisit if log size or
    operational reality makes manual restore impractical.
  - **Re-fold / re-chain cost on a breaking migration.** Because every
    `row_hash` is computed over the event's canonical bytes (and the §0
    framing), any *non-additive* schema change (field removal/rename) to a
    historical event type, **or any change to the §0 hash framing/encoding**,
    invalidates every subsequent `row_hash` and forces a full re-fold + re-chain
    of the log under a migration ADR. Additive `version` bumps are free (old
    rows untouched); breaking changes are expensive *by design*, which is the
    intended pressure toward additive-only evolution (charter #2).
  - **SQLite single-writer concurrency.** SQLite serializes writers (one write
    transaction at a time; a second writer blocks or hits `SQLITE_BUSY`). At
    ADR-0005's sequential/scenario-scoped scope this is a **non-issue** — there
    is exactly one logical scoring writer (the orchestrator) — but it is recorded
    as a real property: if the re-tier trigger fires (a larger host, concurrent
    scenarios), the single-writer assumption must be revisited, not silently
    relied upon. We explicitly do NOT claim concurrency as a benefit (ADR-0001
    dropped that rationale).
  - **`fold` is an O(N) full-scan per scoreboard read — no snapshot/incremental
    story (N5).** Every scoreboard read folds the entire log from genesis; there
    is **no materialized read-model, no snapshot, no incremental fold** in the
    MVP. At personal volume (the <1 s full-rebuild NFR) this is comfortable, but
    it is a **named scaling trigger** alongside SQLite single-writer: the first
    of the two to bite — a log large enough that per-read O(N) folds blow the
    rebuild budget, or a workload that needs a second writer — is the signal to
    add a snapshot/projection layer (small→medium tier transition). `replay_from`
    is O(log N) to the start row but still O(N) over the rows it yields; the
    full-genesis fold is the cost being flagged. Recorded so it is a conscious
    accepted limit, not a latent surprise.
  - **Canonical-JSON discipline is now load-bearing.** The chain is only stable
    because `canonical_json` produces identical bytes for identical content, and
    because the store enforces the §0 value-domain/flag preconditions on top.
    Any drift in that serializer (a Python `json` behavior change, a stray
    re-encode), or any erosion of the no-NaN / JSON-primitive-only precondition,
    would break `verify_chain()` across the board. Mitigated by it being one
    pinned stdlib function in `contracts`, exercised by the conformance (§4a),
    negative-NaN, and golden-bytes tests.

- **Neutral / deferred:** the exact DDL, index names, the **specific** PRAGMA
  pair *within the §3a pinned floor* (FULL vs NORMAL+WAL and checkpoint
  cadence), and the fold-reducer signature are deferred to T-110, finalised
  additively against this ADR. Signing/anchoring/WORM are deferred as the named
  upgrade path *if* the threat model ever changes (e.g. the lab becomes
  multi-user or rank becomes externally consequential).

- **Reversibility:** **hours-to-days for the adapter, months for the chain
  property.** Swapping the SQLite backend for another store behind the same four
  port methods is exactly the change the port exists to absorb (hours-to-days).
  Removing or restructuring the hash-chain *after the scoring log is live* is
  months — it is the audit substrate every score references — which is why the
  semantics are pinned now, deliberately, before T-110.

This decision **honours** the charter: it implements #2 (versioned, additive),
#3 (the locked port + clean fake, **no port change**), #4 (append-only,
fold-derived state), and #10 (stdlib-only, no unpinned dependency). The one
deviation from the small-tier JSONL default — choosing SQLite — is the Q-005
sign-off ADR-0001 deferred, and it is justified above (transactional multi-row
append + indexed seek; NOT concurrency), recorded here for the record rather
than papered over.

## Alternatives considered

### Alternative 1 — Plain JSONL ledger (the T-004 status quo, generalized)

- **What it would look like:** extend `lab/ledger.py`'s `JsonlLedger` pattern —
  one `json.dumps(event)` line appended per row, the chain fields written into
  each line, `fold`/`replay_from`/`verify_chain` implemented as file scans. No
  database, no DDL, maximally simple, and it matches the small-tier default the
  charter nominates.
- **Why not:** **no transaction boundary across rows.** A single scoring step
  emits multiple chained rows (`verification_result` + `score_awarded`); a crash
  or a partial flush between two appends leaves a half-written final line or a
  row whose `prev_hash` chains off a tip that was never durably written — a
  broken chain with no atomic rollback. Bare file-append has no multi-row
  transaction. Secondly, every `replay_from(seq)` and `verify_chain()` becomes a
  **full-file scan** (O(N)) rather than an indexed seek (O(log N)), eroding the
  rebuild NFR as the log grows. JSONL is kept as the *conceptual model* and for
  the lighter `ValidationEvent` stream (T-801), but it is the wrong substrate for
  the integrity-critical, multi-row scoring log. Rejected for the scoring spine.

### Alternative 2 — SQLite, but WITHOUT a hash-chain (just an indexed append-only table)

- **What it would look like:** the same `events` table with monotonic `seq` and
  the same transactional multi-row `append`, but drop `prev_hash`/`row_hash`
  entirely. `verify_chain()` would degrade to "checking `seq` is gap-free", or
  be removed. Less code (ADR-0001 estimates the chain at ~250–350 LOC), simpler
  rows, and we'd keep the two genuine SQLite wins (transaction + index).
- **Why not:** it **discards the tamper-evidence property the spine promises**
  and the port already declares (`verify_chain()` is a locked method on the
  `EventStore` Protocol — dropping the chain would make it a lie or force a port
  change the charter forbids gratuitously). A bare append-only table detects a
  *deleted* row only by a `seq` gap and an *edited* row not at all: a stray
  editor or a corruption that changes a `payload` in place would pass unnoticed,
  silently corrupting every score that folds over it. The whole reason the
  scoreboard is event-sourced rather than a mutable `scores` table (ADR-0001
  Alternative 3) is auditability and tamper-evidence; keeping the table but
  dropping the chain throws away half of exactly that. The chain's cost is
  modest and stdlib-only; its value (a falsifiable corruption tripwire) is the
  point. Rejected.

### Alternative 3 — Full tamper-RESISTANCE via signing and/or external anchoring

- **What it would look like:** sign each `row_hash` with an asymmetric key held
  off the host, and/or periodically anchor a chain checkpoint to an external
  append-only witness (a public transparency log, a notary, a second machine),
  so that a local rewrite of history is cryptographically detectable or
  impossible without the off-box key. This is genuine tamper-*resistance*, not
  merely evidence.
- **Why not:** it defends a **threat model that does not exist for this
  product.** Purple Range is an explicitly single-user, single-owner,
  single-host training lab (ADR-0005; BRAINSTORM §Locked decisions). The only
  party with file access is the owner, and the owner forging their own training
  rank is a self-defeating act with no adversary to fool. (Note: signing the
  *log* still would not certify *scoring integrity* — the input-honesty problem
  of M1 — because the player has host access at scoring time regardless; so even
  this heavier option does not buy the property a naive reading might expect.)
  Signing adds key management and a key-custody story; external anchoring adds a
  **network dependency that directly fights the fail-closed egress-containment
  invariant** (ADR-0006) and an availability coupling to a third party. All of
  that buys protection against an attacker the deployment context rules out. It
  is the textbook over-engineering the charter's "simplest design that satisfies
  the charter" heuristic rejects. **Recorded as the explicit upgrade path** for
  the day the threat model changes (multi-user lab, externally consequential
  rank), but rejected for the MVP. Honest evidence beats dishonest "proof"
  theater.

## Accepted risks

🟡 Things to carry forward and revisit on the named trigger (hand to `critic`
before T-110 depends on this):

- **Tamper-evidence ≠ tamper-resistance, and log-integrity ≠ scoring-integrity**
  — accepted because the deployment is single-owner and the owner has no
  adversary to forge against, and because oracle-input honesty at scoring time
  is a single-owner-trust assumption owned by the Scorer/oracle layer, not this
  store (M1). Revisit if the lab becomes multi-user, or if rank ever becomes
  externally consequential (shared scoreboard, credential, anything an outsider
  would gain from forging). The upgrade path (sign / anchor / WORM) is named in
  Alternative 3 — with the caveat that it addresses *log* integrity, not input
  honesty.
- **`occurred_at` wall-clock ordering is NOT chain-protected (N3).** The "no
  reordering" guarantee is **`seq`-ordering only** — the chain binds each row to
  its `seq` position, and `verify_chain` asserts the `seq` run and the
  `prev_hash` links. It says **nothing** about `occurred_at`: a row's wall-clock
  timestamp can be earlier than its predecessor's (clock skew, `Clock` port
  offset math, backdating) and the chain will still pass. Anything that needs
  temporal ordering must order by `seq`, not by `occurred_at`. Accepted because
  `seq` is the canonical order for fold/replay and `occurred_at` is descriptive
  metadata, not an ordering key.
- **Breaking-migration re-fold/re-chain cost** — accepted because additive
  `version` evolution is the default and breaking changes *should* be expensive
  (it pressures additive-only design, charter #2). The §0 framing/hash-encoding
  is on the same footing (changing it is a breaking migration). Revisit only if
  a forced breaking migration on a large live log makes re-chaining a real
  operational burden.
- **SQLite single-writer + O(N) full-scan fold** — accepted because ADR-0005's
  sequential scope has exactly one logical scoring writer and personal volume
  keeps the full-genesis fold under the <1 s NFR. Revisit at the ADR-0005
  re-tier trigger (a larger host / concurrent scenarios) **or** when log size
  makes the per-read O(N) fold blow the rebuild budget — whichever bites first
  is the signal to add a snapshot/projection read-model (N5). Never claim
  concurrency as a SQLite benefit (ADR-0001 dropped that rationale).
- **Canonical-JSON + value-domain preconditions are load-bearing for chain
  stability** — accepted because `canonical_json` is one pinned stdlib function
  in `contracts`, shared with `manifest_hash`, and the store layers the §0
  no-NaN / JSON-primitive-only preconditions on top. Revisit (and add a
  dedicated golden-bytes test) if the serializer ever needs to change, and carry
  the Open-question below to land `allow_nan=False` in `contracts` itself.

## Open questions

- **Should `allow_nan=False` move into `contracts.canonical_json`?** This ADR
  pins the **store** to enforce a no-NaN, JSON-primitive-only hashed input (§0),
  obtaining the guarantee at its own call site without editing `contracts`. But
  the cleaner long-term home for "the canonical serialization the chain hashes
  over never emits non-JSON `NaN`/`Inf` tokens" is **inside**
  `contracts.canonical_json` (lines 53–60), so *every* caller — `manifest_hash`
  included — inherits it. That is a **required follow-up to contracts** with its
  own change (and likely a one-line ADR note or amendment), explicitly **out of
  scope for this ADR**, which edits ADR markdown only. Until then, T-110 owns
  the precondition at the store boundary, and the §4a negative-NaN conformance
  test is the tripwire that proves it holds.
- **Idempotency vs position-dependent `row_hash`.** Because `dump(event)`
  includes `seq` and `prev_hash`, the `row_hash` binds each event *to its
  position* — re-appending "the same" logical event at a different `seq` is a
  different `row_hash`. That is intended (reordering breaks the chain). De-dup is
  keyed on `(scenario_id, challenge_id, pillar, manifest_hash)` at the *Scorer*
  layer (ADR-0001 M5,
  [`contracts.idempotency_key`](../../contracts/__init__.py)) — **before**
  append — NOT on `row_hash`. The two layers' responsibilities (Scorer de-dups;
  store chains) should be stated explicitly when T-111 lands.

## Open tensions surfaced for the critic

These were genuine seams between this design and the already-locked surface;
they are now resolved above and recorded here for traceability:

- **`row_hash` is NOT a field on the event dataclasses — RESOLVED.** The
  contract shapes carry `version`, `seq`, `prev_hash` as declared fields, but
  `row_hash` is computed and stored by the adapter (it cannot be inside the
  bytes it hashes over, on pain of a fixpoint). §1a pins that `append` is
  authoritative over `seq`/`prev_hash`, reconstructs via `dump` (frozen-safe),
  patches the dict, hashes the §0 framed bytes, and **returns `list[dict]`**
  (the persisted superset rows incl. `row_hash`) — consistent with the
  Protocol's `-> list`, **no port change**.
- **The fold treats `seq`/`prev_hash` as part of the hashed bytes — RESOLVED as
  intended.** `row_hash` binds the event to its position (reordering breaks the
  chain); idempotency is a *Scorer*-layer concern on a different key (see Open
  questions). Confirmed consistent: de-dup happens before append, so the store
  never sees a logical duplicate it would need to position-dedup.
- **`verify_chain() -> bool` cannot say *where* it broke — RESOLVED.** §2 pins
  that the adapter's **internal** verify logs the **first bad `seq`** while the
  **public port stays `-> bool`** (no diagnostic method added — no port change);
  M3's recovery posture (manual restore-from-backup, no auto re-chain) makes the
  log line operationally sufficient for the MVP.

## Links

- PRD: [`docs/PRD.md`](../PRD.md)
- Spine ADR (this builds on it; settles its Q-005): [`0001-manifest-oracle-event-sourced-scoring.md`](0001-manifest-oracle-event-sourced-scoring.md)
- Ports & adapters reference style: [`0002-hypervisor-behind-labprovider.md`](0002-hypervisor-behind-labprovider.md)
- Scope / single-writer context: [`0005-sequential-scenario-scoped-scope.md`](0005-sequential-scenario-scoped-scope.md)
- Locked port: [`ports/__init__.py`](../../ports/__init__.py) — `EventStore` Protocol (unchanged by this ADR)
- Locked contracts: [`contracts/__init__.py`](../../contracts/__init__.py) (`canonical_json` lines 53–60, `manifest_hash`, `mint_correlation_id`), [`contracts/schemas.py`](../../contracts/schemas.py) (the six chained event shapes; `dump` line 689; free-form `evidence` at lines 185/255/493/604)
- Status-quo skeleton generalized: [`lab/ledger.py`](../../lab/ledger.py) (T-004 append-only `Ledger`)
- Architecture sections affected: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §EventStore port + adapters, §event shapes, §state model
- Implemented & finalised by: **T-110** (`SqliteEventStore`); folded by **T-111** (Scorer); gated at **GATE A** (2× fresh clean-room, reviewer-2 owns chain/replay)

---

## Addendum 1 (2026-06-02) — `event_type` is authenticated by framing (Q-020)

> Status: accepted
> Date: 2026-06-02
> Deciders: owner (memeworldorder2024), architect
> Resolves: [`docs/OPEN-QUESTIONS.md`](../OPEN-QUESTIONS.md) **Q-020** (blocks T-111)
> Engages: [`docs/RED-TEAM.md`](../RED-TEAM.md) 2026-05-31 internal review (🔴) + 2026-06-02 external review (🔴 + the Option-D proposal)
> Scope: amends §0, §1, §1a, §2, §4a; supersedes nothing — additive to the chain math, chain-breaking to stored `row_hash` (no persisted data exists yet)

### Context (the gap)

The body of this ADR pins the chain over **`payload` bytes only**. But §5 pins the
Scorer reducer to dispatch on `(event_type, version)`, and `event_type` is **not a
dataclass attribute** — it is derived from the class name by
[`_chain._event_type_of`](../../adapters/_chain.py) and stored in its **own
`events.event_type TEXT NOT NULL` column** (DDL,
[`event_store.py`](../../adapters/event_store.py)). That column is:

- **not part of the hashed `payload`** (`chain_batch` hashes `canonical_payload(dump(event) + seq + prev_hash)`; `event_type` is computed *separately* and carried only as the private `_event_type` bookkeeping key);
- **not re-read by `verify_chain`** (its SELECT is `seq, prev_hash, payload, row_hash`; `verify_rows` unpacks exactly that 4-tuple);
- **not on the read surface** (`_iter_rows` reconstructs the yielded dict from `payload` + `row_hash`, so `fold`/`replay_from` never yield `event_type`).

Two consequences, both confirmed against source by two independent reviewers:

1. `UPDATE events SET event_type='LIE' WHERE seq=…` leaves `verify_chain()` **`True`** — a tamper blind-spot in **the exact field the reducer dispatches on**. The store's "tamper-EVIDENCE" promise (§0/§2) is therefore **false for `event_type`**: it is unverified denormalization.
2. T-111 **cannot** dispatch on `(event_type, version)` as §5 specifies, because the discriminator is absent from the yielded dict.

The current T-110 suite has **no test that tampers a non-`payload` column** — which
is precisely how this slipped past GATE-A prep. That regression guard is mandated
below.

### Decision

> **Adopt Option D: fold `event_type` into the framed row hash alongside
> `payload` — the same way `prev_hash` already is — WITHOUT injecting it into the
> canonical `payload` dict, AND promote `event_type` to a first-class key on the
> persisted/yielded row so the reducer can read `row["event_type"]`.**

The framed input grows by one NUL-delimited field, inserted **between** the
`prev_hash` frame and the `canonical_bytes` frame:

```
row_hash = sha256(
    prev_hash.encode("ascii") + b"\x00"
    + event_type.encode("utf-8") + b"\x00"   # utf-8, NOT ascii — see critic 🟡-1
    + canonical_bytes
).hexdigest()
```

where `canonical_bytes` and the genesis sentinel handling are **exactly as today**
(the genesis row still frames off `prev_hash = GENESIS_SENTINEL = "0"*64`; only the
hash *input* grew, never the sentinel). `event_type` is snake_case from
`_event_type_of` (`scenario_generated`, `attack_executed`, …) — no NUL byte can
occur in it (it is derived from a Python identifier, which cannot contain NUL),
so the input stays self-delimiting, preserving the §0 framing rationale.
**Encoded with `utf-8`, not `ascii`** (critic 🟡-1): Python 3 permits non-ASCII
identifiers, so a future event class like `class Café` would make
`"café".encode("ascii")` raise `UnicodeEncodeError` inside `framed_row_hash` and
crash the whole store — `utf-8` (the same encoding `canonical_bytes` already uses)
removes that latent footgun for free while staying NUL-free. `verify_chain` re-reads the **stored `event_type` column bytes** and
re-frames them, so "hash the bytes you persist; verify by re-reading them" (§0)
now holds for **both** `payload` and `event_type`.

This keeps `payload` **byte-for-byte** `canonical_json(dump(event))` — the
denormalized column is now *authenticated*, not *smuggled into the event*.

### Why D over A and C (the Q-020 alternatives)

**Option A — inject an `event_type` key into the hashed payload dict** (whether via
a new `event_type:str` contract field or a stray key patched in before
canonicalizing). Rejected:

- It **changes the canonical bytes of every event**, which forces editing the
  **independent** conformance oracle
  [`conftest_t110.canonical_bytes_of`](../../tests/conftest_t110.py) (it computes
  `canonical_json(dump(event))`). That oracle's whole value is that it defines the
  hashed bytes *at the contracts level, outside the store* — edit it to match the
  store and `test_row_hash_is_framed_input` stops being an independent check and
  becomes a tautology that re-asserts the store against itself.
- It makes `payload` **no longer a faithful `canonical_json(dump(event))`**, which
  breaks the §4a *oracle-independence* invariant: the conformance oracle
  `conftest_t110.canonical_bytes_of` computes the hashed bytes at the **contracts
  level, outside the store**; edit it to match A's payload and
  `test_row_hash_is_framed_input` collapses into a tautology re-asserting the store
  against itself. **This — not stray-key pollution — is the true discriminator** (critic
  🟡-2). (A stray key would NOT actually break re-hydration: `contracts._load`
  validates only against the schema's own `properties`/`required` — no
  `additionalProperties:false` (Q-017, verified in `schemas.py`) — then filters
  `kwargs` to dataclass `field_names`, so extras are *silently dropped*. The yielded
  dict already carries the non-field key `row_hash` through exactly this path. So the
  read path tolerates extras; A's real cost is the lost oracle-independence above.)
- The contract-field variant additionally ripples to T-101 field-set assertions
  and needs a `version` bump on all six shapes — a larger blast radius for the
  same property.

**Option C — reducer cross-checks the `event_type` column against a
payload-derived shape**. Rejected:

- It leaves the column **unauthenticated at the store layer**. `verify_chain()`
  still returns `True` on a tampered `event_type`; integrity is only "restored" if
  *every* consumer remembers to run the cross-check. That **pushes integrity out of
  the store and into every reducer** — the opposite of the §3/§4a "one chain
  discipline, both adapters route through `_chain`" posture. A second consumer
  (the T-801 validation harness folds the same log) would have to re-implement the
  same guard or silently trust the column.
- It is O(shapes) per row (structural re-derivation) and reintroduces exactly the
  "distinguish shapes structurally" fragility the internal reviewer flagged.

**Why D wins:** it makes the column tamper-evident **at the store boundary**, where
the property belongs, so `verify_chain()` becomes the single falsifiable tripwire
for `event_type` too; it keeps the independent test oracle and the
`payload == canonical_json(dump(event))` invariant intact; and it is localized to
the four `_chain`/store seams below. Honesty about **D's downsides**:

- **D is chain-breaking** (every `row_hash` changes) — identical migration cost to
  A; see Migration below. Accepted because no persisted data exists.
- **D widens the §0 framing contract** from a 2-field frame to a 3-field frame.
  The "any change to the framing is a chain-breaking migration" rule (§0/§5) now
  covers the `event_type` frame too. This is recorded as the new framing of record.
- **D adds a second positional coupling** between a SELECT column list (in
  `event_store.py`) and a tuple unpack (in `_chain.verify_rows`, a *different
  module*). The external reviewer flagged the existing 4-tuple coupling as a
  readability risk; growing it to a 5-tuple sharpens that risk. Mitigation is
  mandated below (named-tuple or an inline comment pinning column↔position).

### Code deltas (names + signatures; tester/implementer TDD from here)

1. **`_chain.framed_row_hash`** — add an `event_type` parameter (extend the existing
   function; do **not** fork a second function — one framing discipline, one
   place):
   ```python
   def framed_row_hash(prev_hash: str, event_type: str, canonical_bytes: bytes) -> str:
       return hashlib.sha256(
           prev_hash.encode("ascii") + b"\x00"
           + event_type.encode("utf-8") + b"\x00"   # utf-8, NOT ascii — see critic 🟡-1
           + canonical_bytes
       ).hexdigest()
   ```
   Genesis/sentinel behaviour is unchanged (callers still pass
   `prev_hash=GENESIS_SENTINEL` for the first row).

2. **`_chain.chain_batch`** — pass each event's `event_type` into the hash, and
   **promote `event_type` to a first-class (non-underscore) key** on the persisted
   row so it survives `public_row` and lands on the yielded dict:
   - compute `event_type = _event_type_of(event)` **before** hashing (it already
     does, just later — move it up);
   - `row["event_type"] = event_type` on the patched dict (now a real key, hashed
     *adjacent to* but not *inside* `payload`);
   - `row_hash = framed_row_hash(prev_hash, event_type, payload.encode("utf-8"))`;
   - **retire the private `_event_type` key** — `event_type` is now public and
     first-class. Keep the private `_payload` (it stays an internal carry of the
     canonical string the persistence layer needs and must NOT leak to callers —
     it is redundant with the dict's content but not a declared field). The
     persisted-row dict §1a returns is now the patched event dict **+ `row_hash`
     + `event_type`** (a superset that now carries the discriminator). Reducers
     read `row["event_type"]`.

3. **`_chain.verify_rows`** — receive and re-frame `event_type`. New row tuple
   shape (ordered to mirror the SELECT):
   ```python
   def verify_rows(rows: list[tuple[int, str, str, str, str]]) -> bool:
       # each row: (seq, prev_hash, event_type, payload, row_hash)
       ...
       recomputed = framed_row_hash(row_prev_hash, event_type, payload.encode("utf-8"))
   ```
   Re-hashes the **stored `event_type` and `payload` bytes** (never re-derives
   `event_type` from a reparsed object — that would re-open the blind-spot). On a
   `False` verdict the existing first-bad-`seq` log line stands.

4. **`SqliteEventStore.verify_chain`** — SELECT must now include `event_type`, in
   the position `verify_rows` unpacks:
   ```sql
   SELECT seq, prev_hash, event_type, payload, row_hash FROM events ORDER BY seq
   ```
   **Positional-coupling note (reviewer-flagged; mitigation hardened per critic 🟡):**
   this SELECT column order and the `verify_rows` unpack live in different modules;
   reorder one without the other and verification silently hashes the wrong field.
   A comment is **not** an acceptable mitigation — it does not fail a test on reorder.
   The implementer MUST make the cross-module contract **key-based, not positional**:
   either (a) `verify_chain` passes `verify_rows` a `list[dict]` (column→value) and
   `verify_rows` reads `r["event_type"]`/`r["payload"]`/… by name, or (b) build a
   `collections.namedtuple` at the SELECT and have `verify_rows` access fields by
   name (`row.event_type`, never `row[2]`). Option (a) preferred (kills the footgun
   structurally and matches the dict shape `_iter_rows` already yields). Non-negotiable.

5. **`SqliteEventStore._iter_rows`** — must surface `event_type` on the yielded
   dict so `fold`/`replay_from` carry the discriminator (today it SELECTs only
   `payload, row_hash`):
   ```sql
   SELECT payload, row_hash, event_type FROM events {where} ORDER BY seq
   ```
   then `row["event_type"] = event_type` on the reconstructed dict. (The §1a
   invariant "`fold`/`replay_from` yield the SAME shape `append` returns" forces
   this — `append` now returns `event_type`, so the read path must too.)

6. **`SqliteEventStore.append`** — no structural change: `_event_type` is gone, so
   the INSERT reads `event_type` from the now-public key
   (`r["event_type"]` instead of `r["_event_type"]`). The INSERT column list is
   unchanged (the table already has `event_type`).

7. **`InMemoryEventStore`** (the §4a byte-identity fake) — confirmed it routes
   **entirely** through `_chain`: `append`→`chain_batch`, `verify_chain`→`verify_rows`,
   `public_row` for reads. The only edits are the `verify_chain` tuple it builds —
   it must now assemble `(r["seq"], r["prev_hash"], r["event_type"], r["_payload"], r["row_hash"])`
   to match the new `verify_rows` arity — and dropping the `_event_type` reference.
   Because both adapters call the same `_chain.framed_row_hash`, byte-identity (§4a)
   holds **by construction** — no separate fake framing to keep in sync.

8. **`public_row` underscore-strip — LOAD-BEARING for this change, not a nit**
   (critic 🟡): D moves `event_type` from the stripped `_event_type` to the kept
   `event_type`, so the §1a yielded **key-set** is now a real contract
   (`{dataclass fields} ∪ {row_hash, event_type}`). The `startswith("_")` strip
   means any *event field* ever named with a leading underscore would be silently
   dropped from what reducers see — the exact bug-class this addendum fixes for
   `event_type`. The implementer MUST pin the yielded key-set with
   `test_yielded_row_keyset` (see Mandated tests below) so the strip can't silently
   drop a real field. **Genuine nits to fold in while these lines are open** (cheap,
   same lines, non-blocking): rewrite the garbled `_event_type_of` docstring; default
   `fold`'s `where` to `""` instead of `"WHERE 1=1"`; soften the `close()` "Idempotent"
   docstring.

### Conformance oracle & fixtures — what changes, what does NOT

- **`conftest_t110.canonical_bytes_of` — UNCHANGED.** Under D, `payload`/canonical
  bytes are identical to today (`event_type` never enters the dict). The oracle
  stays a faithful, store-independent definition of the hashed `payload` bytes.
  This is the central reason D beats A.
- **`conftest_t110.framed_row_hash` (the independent test helper) — CHANGES**, in
  lockstep with the production signature: it gains the `event_type` param so
  `test_row_hash_is_framed_input` re-frames `(prev_hash, event_type, canonical_bytes)`
  and still checks the store against an independent definition.
- **`CONFORMANCE_FIXTURES` — UNCHANGED set.** The three evidence shapes (finite
  float, non-ASCII, nested dict) all ride `submission`, so they all carry the same
  `event_type="submission"`. The fixtures still assert **byte-identical `row_hash`**
  across InMemory/SQLite — that assertion's *expected values* are re-baselined
  (every `row_hash` grew different bytes) but the fixture **definitions** do not
  change. **MANDATED (was "recommended"; promoted per critic 🟠):** add at least one
  fixture whose `event_type` **differs** from the rest, so the conformance suite
  actually proves the `event_type` frame moves the hash across adapters — without it,
  every fixture shares `event_type="submission"` and the suite would pass even if
  `event_type` were dropped from the frame entirely.
- **§4a conformance assertion — WIDEN (critic 🟠).** Today it compares `row_hash` +
  `verify_chain` verdict across InMemory/SQLite. It must now also compare the **full
  yielded dict** (including `event_type`) across the two adapters — because under D,
  SQLite re-sources `event_type` from its **column** while InMemory keeps it in the
  in-dict value; `row_hash` byte-identity holds "by construction" but does NOT pin
  that the *yielded* `event_type` values agree. Comparing the full dict pins the
  convergence the addendum is otherwise only asserting.
- **Re-baseline scope for the tester:** any test that pins a **literal** `row_hash`
  or compares against `framed_row_hash(...)` must be recomputed. Tests that assert
  *relationships* (`verify_chain() is True/False`, reorder/delete/insert, returned
  `row_hash` == persisted `row_hash`, fold reproduces scoreboard) are
  framing-agnostic and need no value edit.

### Migration

This is a **chain-breaking change**: every `row_hash` is recomputed over a larger
input, so every stored `row_hash` changes. Per §0/§5 a framing change is a
chain-breaking migration. **Posture: no migration — re-create.** The store is
**pre-MVP with zero persisted production data** (T-110 just landed; T-111 has not
run; no scoring log exists). There is nothing to re-fold/re-chain: existing dev/test
SQLite files are disposable and recreated by the test harness.

**`version` bumps required: NONE.** D adds **no field to any contract dataclass**
(`event_type` was never a contract field — it is store-derived), so none of the six
event `version:int` values change, and `contracts/schemas.py` is untouched. `payload`
bytes are identical, so historical canonical serialization is unchanged. The change
is confined to the chain-math/store layer. (Contrast: Option A's contract-field
variant *would* have forced a `version` bump on all six shapes.) The framing of
record in §0 is hereby updated to the 3-field frame for all future rows.

### Mandated negative test (the regression guard)

```python
def test_verify_chain_detects_tampered_event_type(sqlite_path):
    """Tampering ONLY the event_type column out-of-band -> verify_chain() False."""
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True
    conn = sqlite3.connect(str(sqlite_path))
    try:
        seq = conn.execute("SELECT seq FROM events ORDER BY seq LIMIT 1").fetchone()[0]
        # change ONLY event_type; leave payload/prev_hash/row_hash untouched
        conn.execute("UPDATE events SET event_type='LIE' WHERE seq=?", (seq,))
        conn.commit()
    finally:
        conn.close()
    assert store.verify_chain() is False, \
        "tampering event_type alone must now break the chain (Q-020)"
```

This is the test whose **absence** let Q-020 slip — it tampers a **non-`payload`
column** and asserts the chain catches it. It MUST be written first (failing
against the current `event_type`-unframed code), then made to pass by the deltas
above. It belongs in the SQLite-specific tamper block alongside
`test_verify_chain_detects_tampered_row`.

**But the verdict-only assertion can pass for the wrong reason** (critic 🟠: any
unrelated always-on mismatch — e.g. a tuple-arity bug, or the `seq`/`prev_hash`
check tripping first — also yields `False`, so `is False` does not prove
`event_type` is the byte that matters). It MUST be paired with a **positive
discrimination** test that pins causation:

```python
def test_row_hash_frames_event_type(sqlite_path, fx):
    """The stored event_type is provably an input to the row hash."""
    store = make_sqlite(sqlite_path); store.append(fx.a_few_events())
    seq, etype, payload, rh = read_row(sqlite_path, seq=1)  # by-name read
    # re-framing with the STORED event_type reproduces the STORED row_hash...
    assert _chain.framed_row_hash(GENESIS_SENTINEL, etype, payload.encode()) == rh
    # ...and a DIFFERENT event_type yields a DIFFERENT hash (control).
    assert _chain.framed_row_hash(GENESIS_SENTINEL, "other_type", payload.encode()) != rh
```

And the §1a **read-contract** is now materially wider (`event_type` is a first-class
yielded key), so pin the key-set too (critic 🟡; this is the charter-#2 "version
surface" for a non-dataclass persisted shape):

```python
def test_yielded_row_keyset(store, fx):
    """fold/replay yield exactly {dataclass fields} ∪ {row_hash, event_type} — both adapters."""
    store.append(fx.a_few_events())
    row = next(store.replay_from(1))
    expected = dataclass_field_names(fx.scenario_generated()) | {"row_hash", "event_type"}
    assert set(row.keys()) == expected
```

All three (negative + positive-discrimination + key-set) are **mandated**, RED-first.

### Interaction with Q-021 (tip-read race) — recommendation: **split (default), don't ride along** (revised per critic 🟡)

The implementer *does* touch the `append` read→write path Q-021 concerns, so the
moment is cheap. **But the default is now SPLIT, not ride-along**: Q-020 is an
**integrity** change on the T-111 critical path; Q-021 is a **concurrency** change
that is explicitly **non-blocking** (single-writer scope; a duplicate `seq` raises
`IntegrityError` → rollback, so integrity is never at risk — only spurious failures
under a hypothetical second writer). Bundling them makes GATE-A's clean-room reviewer
assess two distinct risk surfaces in one diff, and a flaw in the *non-blocking*
concurrency hardening could stall the *blocking* integrity fix that actually unblocks
T-111. **Default: land Q-020 alone; Q-021 (`BEGIN IMMEDIATE` + tip-read-inside-txn)
is a separate follow-up** — pick it up only if it falls out trivially and does not
enlarge the Q-020 review surface. This addendum does **not** decide Q-021; it records
that coupling a blocking change to a non-blocking one is the wrong default.

### Consequences

- **Becomes easy:** `verify_chain()` now trips on any **isolated** out-of-band edit
  of `event_type` (as it already does for `payload`); the reducer dispatches on a
  discriminator that is on the read surface; the conformance oracle and the
  `payload == canonical_json(dump(event))` invariant survive untouched.
- **Scope of the guarantee (precise — critic 🟠, do not overstate):** D authenticates
  the **immutability** of the stored `event_type`, **not** its **correspondence to the
  payload it labels.** `event_type` is derived once at write time by `_event_type_of`
  and trusted thereafter; the chain never cross-checks that the stored `event_type`
  matches the *shape* of its `payload`. A privileged attacker who rewrites **both** the
  `event_type` column **and** re-derives a consistent `row_hash` (the frame is public —
  this is tamper-EVIDENCE, not tamper-RESISTANCE, per the ADR title) produces a row
  whose `event_type` lies about a differently-shaped `payload`, and `verify_chain()`
  returns True. This is **within the declared threat model** (privileged host attacker
  is out of scope, §0/title) — but T-111's `(event_type, version)` dispatch may trust
  only "`event_type` was not edited in isolation," **not** "`event_type` provably
  matches the payload." If T-111 needs the latter, that is Option-C territory (a reducer
  cross-check of column vs payload-derived shape) and is hereby recorded as a **residual,
  NOT solved by D.**
- **Becomes hard:** the §0 framing is now a 3-field contract — one more thing a
  future hash-encoding change breaks (and must break loudly); the SELECT↔`verify_rows`
  coupling grew by one column and must be made **key-based** (not positional).
- **We owe later:** the key-based guard on the SELECT↔`verify_rows` coupling (mandated
  above, not optional); a Q-021 disposition (now **split-by-default**, follow-up); and
  the `event_type`↔`payload` correspondence residual above if T-111's dispatch needs it.

### Critic pass — DONE (2026-06-02), all concerns addressed above

The `critic` ran against this addendum (full review in [`docs/RED-TEAM.md`](../RED-TEAM.md)
2026-06-02). **Verdict: the core decision (D over A/C) is sound** — the critic tried the
three nominated objections and they FAILED on the evidence:

1. **Collision/framing soundness — sound.** The NUL-delimited 3-field frame is
   self-delimiting and *strictly stronger* than the old 2-field frame; `event_type`
   (identifier-derived) and `canonical_bytes` (`json.dumps` escapes NUL as ` `)
   are both provably NUL-free. The one residual — `.encode("ascii")` could raise on a
   future non-ASCII class name — is **fixed above** (→ `utf-8`).
2. **"D moves A's stray-key defect onto the yielded dict" — FAILS.** Verified in
   `schemas.py`: `_validate` checks only the schema's own `properties`/`required` (no
   `additionalProperties:false`, Q-017) and `_load` filters `kwargs` to dataclass
   `field_names` — extras are silently dropped. The yielded dict already carries the
   non-field key `row_hash` through this exact path. So the read path is safe; A's real
   cost is lost oracle-independence (rationale **corrected above**).
3. **"No version bump" — airtight for schemas**, with the honest caveat (now pinned by
   `test_yielded_row_keyset`) that the §1a yielded-dict read-contract widens.

The critic's **8 fixable findings (🟠×3, 🟡×5)** are each addressed inline above:
ascii→utf-8 encode; A-rationale corrected to oracle-independence; key-based (not
positional, not comment) SELECT↔`verify_rows` coupling; `public_row` underscore-strip
elevated to load-bearing + `test_yielded_row_keyset`; distinct-`event_type` conformance
fixture promoted to mandated + §4a widened to compare full yielded dicts;
negative-test paired with positive-discrimination (`test_row_hash_frames_event_type`);
Q-021 ride-along flipped to split-by-default; Consequences corrected to scope the
guarantee (immutability, **not** `event_type`↔`payload` correspondence — recorded as a
residual). **This addendum is the binding T-111 spec; the tester/implementer work from
the Code-deltas + Mandated-tests sections above.**
