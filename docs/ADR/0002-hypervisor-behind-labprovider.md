# ADR-0002 — Hypervisor / provisioner behind a `LabProvider` port (VirtualBox-now, libvirt-deferred, Docker for containers)

> Status: accepted
> Date: 2026-05-31
> Deciders: owner (memeworldorder2024), architect
> Supersedes: —

## Context

Purple Range (codename Phalanx) stands up victim VMs and container targets on a
**single bare-metal host** and runs scripted attack→detect→mitigate loops
against them. The hypervisor / provisioner is therefore an external dependency
that the core orchestrator must drive. See the spine ADR
[`0001-manifest-oracle-event-sourced-scoring.md`](0001-manifest-oracle-event-sourced-scoring.md)
(which reserved this ADR), [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) (§Module
boundaries, §LabProvider) and [`docs/BRAINSTORM.md`](../BRAINSTORM.md)
(§Virtualization / Lab orchestration). This ADR **records an
already-settled decision** taken at brainstorm convergence and architecture
sign-off; it does not re-open it.

The forces in play:

- **Charter non-negotiable #3 (ports & adapters at every external boundary).**
  The hypervisor is exactly such a boundary. Business logic in `core/*` must
  **never** import a vendor SDK, shell out to `VBoxManage`, or call `vagrant`
  directly — otherwise the orchestrator can only be tested by booting a real
  hypervisor, which is impossible in CI (the <5-min, zero-VM tier; no nested
  virt on cloud runners) and slow/flaky on the host.
- **The host as it actually is (probed 2026-05-30).** A single AMD Ryzen 7
  9800X3D (8C/16T), 60 GiB RAM (~55 usable for guests), Ubuntu 24.04 / kernel
  6.17, bare metal with AMD-V and `/dev/kvm` usable. Installed: VirtualBox
  7.1.18, Vagrant 2.4.3, Docker 29.5.2, podman 4.9.3 — **and libvirt/KVM is
  also available.** So we have a genuine choice of hypervisor *today*.
- **The migration source.** The predecessor `cyber-range` is already built on
  Vagrant + VirtualBox. Reusing that path is the lowest-switching-cost way to
  get the first phases booting green; a libvirt rewrite would delay the
  critical path with no MVP-visible benefit.
- **Mixed target kinds.** Full VMs are required for Security Onion, GOAD
  (Active Directory forest) and SecGen victims; **containers** are the right
  shape for the Vulhub CVE fast-path and web targets. One port must front both,
  or the orchestrator learns the difference between a VM and a container —
  which would leak vendor concepts into core.
- **The base-snapshot training loop.** The MITIGATE pillar (ADR-0001) re-runs an
  attack from a known-clean state after the learner hardens the target. That
  requires snapshot/restore as first-class port operations, not an
  implementation detail of one adapter.

What we know: VirtualBox + Vagrant works on this host today and on the
predecessor. What we **don't** yet know (deferred, not papered over): whether
libvirt/KVM will eventually be worth the switch (better nested-virt and RAM
behaviour for GOAD-full), and the exact Vagrant box + version for the Linux
victims (selected at phase-web decomposition; pin-gate enforces it).

## Decision

> We will put the hypervisor / provisioner behind a single `LabProvider` port —
> `bring_up`, `tear_down`, `snapshot`, `restore`, `status` — wire **Vagrant +
> VirtualBox as the production adapter NOW**, **Docker Compose as the adapter
> for container / Vulhub-CVE targets**, defer **libvirt/KVM as a second adapter
> behind the same port**, and require every victim to boot from a known-clean
> **base snapshot** that is restored between scenarios.

The design:

**1. The port (exactly as in ARCHITECTURE.md §LabProvider).** `core/*` depends
only on this interface — never on `VBoxManage`, `vagrant`, the Docker SDK, or
`subprocess`:

- `bring_up(scenario: Scenario) -> LabHandle`
- `tear_down(handle) -> None`
- `snapshot(handle, name) -> SnapshotRef`
- `restore(handle, ref) -> None`
- `status(handle) -> list[ComponentStatus]`

`Scenario(version:1){ id, components:[Component], net:"192.168.56.0/24" }` and
`Component{ name, kind:VM|CONTAINER, image, ram_mb, cpus, ip, promisc }` are the
only shapes that cross the seam (contracts are owned by `core/contracts`). The
`kind` field — not the adapter identity — tells the *orchestrator* nothing about
*how* a component is realised; the adapter decides VM vs container behind the
port. The port emits the lifecycle events `lab.brought_up | snapshotted |
restored | torn_down`, idempotency-keyed on `scenario.id + attempt`.

**2. Adapters.**

| Adapter | Binding | Realises |
|---|---|---|
| `VagrantVirtualBox` | **prod, now** | Linux/Windows full VMs (Security Onion, GOAD, SecGen victims) via Vagrant 2.4.3 + VirtualBox 7.1.18 |
| `DockerCompose` | **prod** | container / CVE targets (Vulhub), web targets, Kali-in-container attacker |
| `Libvirt` | **deferred** | the same five port methods over libvirt/KVM (`/dev/kvm` present), wired only when it earns the switch |
| `InMemoryLab` (fake) | **tests / CI** | returns canned `LabHandle`/`SnapshotRef`/`ComponentStatus`, so the orchestrator and `lab` harness are fully CI-testable with **no hypervisor present** |

**3. The base-snapshot rule (load-bearing).** Snapshots are taken **per target
VM, not per phase** (per-phase snapshots drift — BRAINSTORM §Virtualization).
After a victim is provisioned and *before its first attack*, the adapter takes a
mandatory `base` snapshot. The MITIGATE re-attack loop `restore`s to `base`
between scenarios so every run starts from a known-clean state. **No attack is
permitted against a VM lacking a `base` snapshot** — this is asserted in the
containment pre-flight (ADR-0006) and is the safety net behind the "untrusted
victim" trust boundary (ARCHITECTURE §Security & trust boundaries).

**4. Finalisation.** This ADR fixes the *shape and the now/deferred split*.
**T-201 lands the real `VagrantVirtualBox` adapter and FINALISES this ADR** —
any port-signature adjustment discovered while wiring the real VBoxManage/Vagrant
calls is folded back here (additively per charter #2; a method rename would
require its own migration note).

## Consequences

- **Positive:**
  - **CI-testability without a hypervisor.** `InMemoryLab` lets the orchestrator,
    the `lab up|down|reset|validate|status|panic` harness, and the snapshot/restore
    loop run in the <5-min zero-VM CI tier. If a clean fake were hard to write the
    interface would be wrong (charter heuristic) — five small methods over three
    plain contracts make the fake trivial, which validates the seam.
  - **Lowest switching cost now.** Reusing the predecessor's Vagrant+VirtualBox
    path gets phases booting green on the critical path without a hypervisor
    rewrite.
  - **Portability to libvirt later is free of core changes.** When/if libvirt
    earns the switch, it is a new adapter behind the same five methods; `core/*`
    does not move.
  - **One port spans VM and container kinds**, so the Vulhub fast-path (Docker)
    and the full-VM phases (GOAD, Security Onion, SecGen) share one orchestration
    contract.
  - **The MITIGATE loop is structural**, not adapter-specific: `restore(handle,
    base_ref)` is the same call whether the target is a VM or a container.

- **Negative:**
  - **The indirection has a cost.** Three adapters must each implement the same
    five methods honestly; snapshot/restore semantics differ between VirtualBox
    (real VM snapshots) and Docker Compose (image + volume reset), and the
    adapters must reconcile that behind the port. This is the price of charter #3
    and is paid once per adapter.
  - **Container "snapshots" are weaker than VM snapshots.** `DockerCompose`
    restore is a recreate-from-pinned-image-plus-clean-volume, not a
    point-in-time memory snapshot. Acceptable: Vulhub CVE images are
    `@sha256`-pinned and deterministic by construction (ADR-0001 / ARCHITECTURE
    §ScenarioGenerator), so recreate *is* restore-to-base for that plane.

- **Neutral / deferred:** the libvirt adapter is deferred (not rejected); the
  exact Linux victim box + `box_version` is selected at phase-web decomposition
  and enforced by the pins gate. SecGen's containerised toolchain is a
  `ScenarioGenerator` concern (ADR-0003), not a `LabProvider` one.

- **Reversibility:** **hours-to-days.** Swapping or adding a hypervisor adapter
  is exactly the change this port was built to absorb. The port *signature*
  itself is harder to change once T-201 and downstream phases depend on it
  (days-to-weeks), which is why it is fixed and finalised deliberately at T-201.

This decision **honours** the charter — it implements #3 directly and introduces
no deviation.

## Alternatives considered

### Alternative 1 — Direct `VBoxManage` / `vagrant` calls from the orchestrator

- **What it would look like:** the orchestrator (and the `lab` harness) shell out
  to `VBoxManage`, `vagrant up/halt/snapshot`, and `docker compose` directly,
  with no port in between. Fewer files, no adapter indirection.
- **Why not:** it **violates charter #3** and makes `core/*` untestable without a
  real hypervisor — the orchestrator could only be exercised by booting VMs,
  which is impossible in the zero-VM CI tier and slow/flaky on the host. It also
  hard-binds the whole project to VirtualBox forever (vendor lock-in), killing
  the cheap path to libvirt. Rejected — this is the fake-grading-equivalent
  mistake for orchestration.

### Alternative 2 — libvirt/KVM as the production adapter NOW (skip VirtualBox)

- **What it would look like:** go straight to libvirt/KVM (it is available on the
  host, `/dev/kvm` present, arguably better nested-virt and memory behaviour for
  GOAD-full) and never write the VirtualBox adapter.
- **Why not:** **deferred, not rejected on merit.** VirtualBox + Vagrant already
  works on this host and is the predecessor's proven path, so the switching cost
  *now* is lower and the critical path is shorter. The benefit of libvirt is real
  but not MVP-visible, and the whole point of the `LabProvider` port is that we
  can adopt libvirt later as a drop-in adapter without core changes — so there is
  no penalty for deferring. Recorded here as the first follow-on adapter to write
  when it earns the switch.

### Alternative 3 — Containers only (Docker Compose for everything)

- **What it would look like:** drop full VMs entirely; run every target as a
  container. Lowest RAM, fastest boot, simplest single adapter.
- **Why not:** it **cannot deliver the VM / Active-Directory / GOAD phases** that
  are core to the product — a Windows AD forest, Security Onion's full sensor
  stack, and randomised SecGen victims are not container workloads. Containers
  are the right shape for the Vulhub CVE fast-path and web targets, so we keep
  Docker Compose as *an* adapter — but not the *only* one. Rejected as the sole
  strategy.

## Accepted risks

🟡 Accepted, with the trigger to revisit:

- **Snapshot-semantics divergence across adapters** — accepted because the
  base-snapshot *contract* (clean state before first attack; restore between
  scenarios) is uniform even though VirtualBox and Docker realise it differently.
  Revisit if a phase needs guarantees Docker recreate cannot meet (e.g.
  in-container stateful corruption that an image reset misses).
- **VirtualBox-first technical debt vs libvirt** — accepted because the port
  makes the migration cheap. Revisit when GOAD-full RAM/nested-virt behaviour on
  VirtualBox proves limiting, or when a bigger host (the re-tier trigger in
  ADR-0005) appears.

## Links

- PRD: [`docs/PRD.md`](../PRD.md)
- Spine ADR (reserved this one): [`0001-manifest-oracle-event-sourced-scoring.md`](0001-manifest-oracle-event-sourced-scoring.md)
- Related ADRs: ADR-0003 (SecGen containerised toolchain), ADR-0005 (sequential / scenario-scoped scope), ADR-0006 (containment authority)
- Brainstorm: [`docs/BRAINSTORM.md`](../BRAINSTORM.md) §Virtualization / Lab orchestration
- Architecture sections affected: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §Module boundaries, §Ports & adapters → LabProvider
- Finalised by: **T-201** (real `VagrantVirtualBox` adapter)
