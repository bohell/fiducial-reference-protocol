# Changelog

All notable changes to the Fiducial Reference Protocol specification.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses
draft versioning: `0.x` releases may change wire formats.

---

## [Unreleased]

Renames the protocol and adds the 2D drawing domain; effect canonicalisation moves from a
CAD footnote to a core requirement. Wire formats gain optional fields only, so existing
documents remain valid and the schema `$id` version stays `0.2`. Nothing here removes a
required field or changes the meaning of an existing one (**FRP-11.2-01**) — except the
identifier prefix, which is called out under *Changed* rather than left implicit.

### Added

- **Core §3.6 — Effect canonicalisation** (**FRP-3.6-01** to **-04**). A container that
  carries editor-assigned identity, timestamps, session GUIDs, view state, or creation
  ordering cannot be hashed as written. The canonicaliser must be named and versioned in the
  manifest, the form must be reproducible by an independent implementation, and a text
  projection must exist so a reviewer can diff two revisions.
- **`spec/profiles/drawing2d.md`** — the 2D drawing profile (`frp-drawing2d/0.2`): L2 is a
  layer or block name, L3 is a canonical entity index, and refs must not be derived from
  DXF handles. Includes two 2D-specific gate checks: **contour closure** (an unclosed
  contour renders correctly and cannot be machined) and **exact entity count** (deleting a
  hole changes area by a small, tolerant margin).
- **`effect.canonicalizer`** and **`effect.entities`** in the revision manifest schema.
- **Appendix A.1/A.2 of the drawing2d profile** — how the profile maps onto AutoCAD
  (`accoreconsole` gives headless execution; hand-drawn DWG has no cause) and SolidWorks
  (no vendor headless mode, so the cause is the design table, not the part file).

### Changed

- **Rename: ACP → FRP.** The protocol was published briefly as *ACP / Anchored
  Collaboration Protocol*. That abbreviation collides with *Agent Communication Protocol*,
  so it was renamed while no external implementation existed. The new name is **FRP /
  Fiducial Reference Protocol**, Chinese 基准指称协议.

  A *fiducial* is a mark placed on a part so a machine can re-establish its coordinate
  system against a part that has shifted, stretched, or distorted — standard vocabulary in
  PCB assembly, photolithography, and metrology. That is what this protocol does for
  annotations, and it is why the name was chosen over the other available `-RP` options:
  `ARP`, `SRP`, `CRP`, and `CAP` are all taken by things a reader is likely to have heard of.

  Effect on identifiers: requirement ids move from `ACP-<sec>-<nn>` to `FRP-<sec>-<nn>`,
  schema `$id` from `urn:acp:schema:*` to `urn:frp:schema:*`, and profile identifiers from
  `acp-*` to `frp-*`. Strictly, **FRP-11.2-01** governs fields, not identifiers, so this is
  not a version-breaking change; but it does break citation stability, and renaming after
  external citation existed would have been much worse.

- **Core §1.4 — Why the CAD profile is the ceiling.** States the direction in which
  conformance transfers, and corrects a widespread intuition: anchors in contracts, code,
  and PCBs are *not* stable. Re-annotation, function extraction, and clause renumbering
  destroy anchors exactly as a CAD rebuild does. What differs is frequency, visibility, and
  candidate density — and those differences mean an implementation that assumes stable
  anchors works until the first refactor and then fails wholesale. Reconnect is required in
  every domain (I4); only its trigger differs.

- **CAD-2-01** now cites core §3.6 instead of carrying its own STEP-specific exception. The
  rule did not change; its scope did. What was written as a CAD concession is now the general
  case, which is what it always was.
- Core §8 lists three profiles rather than two.

### Clarified

- The drawing2d profile states its own evidence level: it is **design-level**, with no
  reference implementation, and its thresholds are derived geometrically rather than
  measured. A threshold with a measured number behind it and one with a plausible number
  behind it are not the same artifact, and the document says which it is.

---

## [0.2] — 2026-10-17

First public draft. Substantial rewrite of the internal 0.1 draft, which existed only as a
single unstructured document.

### Added

- **Normative requirement ids** (`FRP-<section>-<nn>`) so conformance reports can cite text
  directly instead of quoting prose.
- **Conformance classes** (Viewer / Anchor / Editor / Full, §7) with a checklist in
  Appendix A. Previously an implementation could only claim to be "compliant", which said
  nothing about what it could actually do.
- **JSON Schemas** for note, revision manifest, and ledger event (`schema/`), with
  `additionalProperties: false` and namespaced extension keys (§11).
- **Reconnect as a first-class operation** (§6.2) with mandatory recording of the fingerprint,
  the metric value, the candidate count, and the method. The rule that ambiguity must be
  reported rather than resolved silently is new.
- **Permission surface requirements** for editing agents (§9.3, and per-profile sections):
  no write access to the revision store, the ledger, or the gate definition.
- **Ledger chaining** (`prev_hash`) as a SHOULD (§9.4) for truncation detection.
- **Privacy section** (§10): disclosure when `intent` text is sent to a third-party model,
  and retention limits that do not rewrite history.
- **Appendix B — Design rationale** (non-normative), including why per-face UUIDs are
  rejected and why refs must be revision-scoped. Both were argued internally; writing them
  down makes them falsifiable.
- Two profiles with worked numbers: `frp-cad/0.2` and `frp-sim/0.2`.
- Profile appendices listing **implementation hazards**: build caches keyed by source path,
  daemon workers not inheriting per-call environment, buffered output hiding success flags,
  overlay elements swallowing pointer events, reload-versus-redeployment, and mixed
  local/remote absolute paths in destructive commands.

### Changed

- The core invariant set is now stated as **six numbered invariants** (§4) rather than
  embedded in prose. Profiles are explicitly forbidden from weakening them.
- `Verify` now **requires at least one kernel-independent check** (§6.4-02). A gate computed
  by the same kernel that produced the change tests self-consistency, not correctness.
- Requirement that a gate report **all** checks rather than stopping at the first failure
  (CAD-5-04), so a single ledger entry explains the whole state.
- Revision identity explicitly excludes derived results in the simulation profile
  (SIM-1-02), so that solver runs do not each become a new revision.

### Removed

- All organisation-specific references from the 0.1 draft: internal hostnames, private IP
  addresses, internal product names, and internal deployment paths. The protocol now
  describes shapes, not our infrastructure.
- The claim that any single implementation "validates" the protocol. Reference
  implementations are cited as evidence that a profile is implementable, not as proof that
  the core is right.

### Known issues

- **Name collision.** "FRP" is also used by the Agent Communication Protocol. A rename is
  likely before 1.0.
- **Time-scoped refs** are not specified. Annotating a feature that exists during only part
  of a transient is handled by a payload field, not by a first-class L3 (see
  `simulation.md` Appendix A).
- **Ensemble/sweep objects** are unspecified.
- **Conformance testing is manual.** Appendix A is answered by reading one's own code, which
  contradicts I5. A test suite is the top code contribution sought.
- **Fingerprint thresholds** in the CAD profile (1e-3 area, 1° normal) are calibrated on a
  small set of parts. They may need widening for parts with many near-identical faces.

---

## [0.1] — internal draft, 2026-10

Not publicly released. Established the three-layer identity model (revision / feature /
ref), the note format, the edit-verify-publish loop, and the append-only ledger, based on a
working human-picks-a-face → agent-edits-source → machine-verifies prototype.
