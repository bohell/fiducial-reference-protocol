# Fiducial Reference Protocol (FRP)

**Version 0.2 (Draft Standard)** · 2026-10-17

> A protocol for humans and AI agents to talk about *parts of an engineering artifact* —
> and to agree, verifiably, on what changed.

---

## The problem in one paragraph

Text has git: a commit hash pins the version, line numbers address a location, `diff`
describes the change, and CI checks it. Engineering artifacts have none of that.
A CAD feature tree lives inside one application's memory; STEP export loses it; a PDF
loses everything. When a human and an agent discuss "this hole", the human points with a
mouse and the agent has nothing to point back at. The result is a conversation about
geometry conducted entirely in prose, with no identity, no version, and no proof.

FRP supplies the missing pieces: **a version identity, an address inside that version,
a persistent name for the thing you actually want to change, a machine-checkable
acceptance gate, and an append-only memory both sides share.**

---

## The core idea

```
Selection happens at the geometry layer  (the effect).
Modification happens at the feature layer (the cause).
The protocol maintains the two-way translation,
and recomputes the translation table after every rebuild.
```

A user clicks a face. That face is an *effect* — a surface in one particular build.
What they actually want is a change to a *cause* — a parameter, a sketch dimension, a
named feature, a configuration line. FRP is the layer that carries the click to the
right cause without pretending the click survives the rebuild.

Three identity layers do the work:

| Layer | Name | Lifetime | Analogue |
|---|---|---|---|
| **L1** | `revision` — content hash | immutable, permanent | git commit SHA |
| **L2** | `feature` — named symbol | persists across revisions | file path |
| **L3** | `ref` — e.g. `#o1.2.f7` | **valid inside one revision only** | line number |

The single most important rule in this document: **a ref is never assumed to survive a
rebuild.** Refs are cheap, local, and disposable. What survives is the L2 name, and the
translation from L2 back to refs, which is recomputed and re-verified on every revision.

---

## What is in this repository

```
spec/
  FRP-v0.2.md              normative specification (this is the standard)
  profiles/
    cad.md                 parametric CAD profile (reference implementation)
    simulation.md          CFD/simulation case profile
    drawing2d.md           2D drawing profile (DXF/DWG; design-level, no reference impl)
schema/
  note.schema.json         machine-readable note (JSON Schema 2020-12)
  revision-manifest.schema.json
  ledger-event.schema.json
examples/
  note-cad.json  note-cad.md  revision-manifest.json  ledger.jsonl
README.zh-CN.md            中文导读
```

## Status

Draft. The wire formats in `schema/` are stabilising; the conformance classes in §7 are
new in v0.2 and expected to change. Implementations are invited to state which
conformance class they meet rather than claiming "FRP compliant".

A worked end-to-end implementation (human picks a face in a browser → agent edits the
parametric source → machine verification → new revision published → ledger entry
appended) exists and is described in `spec/profiles/cad.md`. Implementation code is
intentionally **not** part of this repository: the protocol should be implementable by
anyone with any engine.

## Design position

FRP does not replace STEP, does not replace git, and does not require a particular
kernel. It is a *sidecar*: STEP remains the interchange format for the effect, a source
file or feature tree remains the cause, and FRP adds the identity and memory that both
of them lack. See Appendix B for why the obvious alternatives (git alone, UUIDs per face,
W3C Web Annotation selectors) do not close this gap.

## Naming history

This protocol was published briefly as **ACP / Anchored Collaboration Protocol**. That
abbreviation collides with *Agent Communication Protocol*, so it was renamed before any
external implementation existed. The name **FRP / Fiducial Reference Protocol** was adopted
in its place.

*Fiducial* is the operative word. In PCB assembly, photolithography, and metrology, a
fiducial is a mark deliberately placed so that a machine can re-establish its coordinate
system against a part that has shifted, stretched, or distorted. That is the job this
protocol does for annotations: the artifact keeps changing, and the correspondence is
re-derived from a small set of stable references rather than assumed.

`FRP` is also used for *Functional Reactive Programming* and for fibre-reinforced polymer.
Both are distant enough not to be confused in context, but implementations **SHOULD** write
the full name on first use.

## Contributing

See `CONTRIBUTING.md`. The most useful contribution right now is **a profile for a
domain we have not covered** (mesh/CAE, ECAD, technical documentation, data pipelines)
plus a note on which of the six invariants fails to map.

## License

Apache License 2.0 — see `LICENSE`. The patent grant is deliberate: a protocol meant to
be implemented should not require a legal review to implement.
