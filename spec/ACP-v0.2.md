# Anchored Collaboration Protocol (ACP)

**Version:** 0.2 (Draft Standard)
**Date:** 2026-10-17
**Editors:** Dana (大拿) and the ACP contributors
**Status of this memo:** Draft. Distribution unlimited.

---

## Abstract

This document specifies the Anchored Collaboration Protocol (ACP), an exchange layer for
human–agent collaboration on engineering artifacts. ACP defines three identity layers for
a versioned artifact (an immutable revision identity, a persistent feature identity, and a
revision-scoped geometric reference), a note format that carries a human's intent from a
selected region of the rendered artifact to the source that generates it, a
machine-checkable acceptance gate for the resulting change, and an append-only ledger
that gives both parties a shared memory of what was agreed and what was measured.

ACP is domain-neutral at its core and specialised by profiles. This document specifies
the core; `spec/profiles/` specifies CAD and simulation profiles.

---

## 1. Introduction

### 1.1 Motivation

Software engineering has a mature vocabulary for collaborative change: a commit identifies
a version, a path and line number identify a location, a diff describes a change, a test
suite decides whether the change is acceptable, and the log records who did what. Each of
these has a well-understood failure mode, and each failure is *detectable*.

Collaboration on engineering artifacts has the vocabulary of none of them. A parametric
model is a program whose output is geometry, but the geometry is what people see and talk
about, while the program is what must be edited. The two are related by a rebuild that is
neither identity-preserving nor invertible: face numbering changes when a feature is
added upstream, and a small parameter change can re-topologise an entire region.

In human–human collaboration this gap is bridged by pointing at a shared screen. In
human–agent collaboration there is no shared screen, so the gap becomes a stream of prose:
"the third hole from the left, the one near the chamfer, make it bigger". Agents are
remarkably good at working with such prose and remarkably bad at being *verifiably right*
about it, because nothing in the exchange is checkable.

The gap is not a modelling problem. It is an identity problem.

### 1.2 Scope

ACP specifies:

- the three-layer identity model for a versioned artifact (§3);
- six domain-neutral invariants that any conforming exchange must preserve (§4);
- wire formats for notes, revision manifests, and ledger events (§5);
- the operations anchor, reconnect, apply, verify, publish (§6);
- conformance classes so that partial implementations can be described honestly (§7);
- the profile mechanism and two profiles (§8);
- security and privacy considerations specific to agent-mediated editing (§9, §10).

### 1.3 Non-goals

ACP does **not** specify:

- a geometry kernel, a file format for geometry, or a modelling language. STEP, glTF, and
  the source language of the chosen engine remain the interchange formats.
- a transport. Notes may travel over HTTP, a message queue, a file drop, or an MCP tool;
  §5 defines payloads, not transport bindings.
- a permission model for agents beyond the minimum safety requirements in §9.3.
- how an agent decides *what* to change. ACP constrains what an agent may *claim*, and
  how that claim is checked. It says nothing about how the claim is generated.

---

## 2. Conventions and Terminology

### 2.1 Requirement levels

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED,
MAY, and OPTIONAL in this document are to be interpreted as described in RFC 2119 and
RFC 8174, when and only when they appear in bold capitals.

Each normative requirement carries an identifier of the form `ACP-<section>-<nn>` so that
conformance claims and test reports can cite it directly.

### 2.2 Terminology

**Artifact**
: The thing under discussion. A CAD part, an assembly, a simulation case, a PCB layout, a
  technical document. An artifact has at least one *cause* representation and at least
  one *effect* representation.

**Cause**
: The representation that generates the artifact: a parametric script, a feature tree, a
  configuration dictionary, a database row. Must be deterministically rebuildable
  (see §3.4).

**Effect**
: The rendered or exported result: a STEP file, a triangle mesh, a rendered image, a
  simulation result. This is what humans select and what agents inspect.

**Revision (L1)**
: An immutable snapshot of an artifact, identified by a content hash computed over the
  cause, the effect, and the reference table (§3.5).

**Feature (L2)**
: A named symbol in the cause representation that denotes a semantically stable unit
  (`hole_a`, `inlet`, `crank_pin`). Persists across revisions.

**Ref (L3)**
: A revision-scoped address of a selectable region in the effect representation, e.g.
  `#o1.2.f7`. Valid only within the revision it was minted in.

**Note**
: The minimal exchange unit: a human's intent plus the refs it applies to, bound to a
  revision.

**Gate**
: A machine-executable acceptance check. Not a human opinion and not an LLM's
  self-assessment.

**Ledger**
: An append-only, ordered record of events, shared by both parties.

---

## 3. Core Model

### 3.1 Cause and effect duality

**ACP-3.1-01** An implementation **MUST** distinguish, for every artifact, a cause
representation from an effect representation, and **MUST** be able to rebuild the effect
from the cause without human intervention.

**ACP-3.1-02** A note **MUST** address its selection in the effect representation and its
intended change in the cause representation.

The duality is not an implementation detail. It is the reason the protocol can be honest:
the user's selection is real but version-bound, while the change is expressible in a form
that survives rebuilds.

### 3.2 Three-layer identity

| Layer | Unit | Mutable? | Scope |
|---|---|---|---|
| L1 | revision | no | global |
| L2 | feature | yes (redeclared each revision) | artifact |
| L3 | ref | yes (recomputed each revision) | one revision |

**ACP-3.2-01** A ref **MUST NOT** be treated as valid outside the revision in which it
was minted. Implementations **MUST** reject or explicitly degrade a ref presented against
a different revision.

**ACP-3.2-02** A feature name **SHOULD** be stable across revisions of the same artifact.
When a feature is renamed or removed, the implementation **SHOULD** record the rename in
the revision manifest rather than silently dropping the name.

**ACP-3.2-03** An implementation **MUST NOT** silently reuse a ref for a different region
across revisions. If a region disappears, its ref disappears.

### 3.3 Selection at the effect, modification at the cause

**ACP-3.3-01** The result of *anchor* (resolving a ref) **MUST** include at least: the ref,
the revision it belongs to, and a measurable geometric signature (for CAD: area, centroid,
normal; for simulation: patch name and face count; profiles define the exact set).

**ACP-3.3-02** The anchor result **MUST** be sufficient for a modifying agent to locate
the corresponding feature **without** consulting the rendered artifact again. This is the
practical test of whether a profile is well designed.

### 3.4 Cause admissibility

An artifact's cause representation is admissible under ACP if and only if:

1. **Deterministic rebuild** — same inputs produce the same geometry; no dependence on
   time, randomness, or ambient environment.
2. **Nameable features** — the units a human would want to discuss have stable names.
3. **Machine-editable** — a plain-text (or structured, diffable) edit is possible and can
   be applied by a program without a GUI.

**ACP-3.4-01** An implementation **MUST** verify admissibility at registration time and
**MUST** refuse an artifact whose cause is not deterministically rebuildable.

> Rationale: a non-deterministic cause makes every gate meaningless, because the
> measured result cannot be attributed to the edit.

### 3.5 Revision composition

**ACP-3.5-01** A revision identifier **MUST** be a cryptographic hash over a canonical
serialisation of at least:

- the cause bytes (or a hash tree over them),
- the effect bytes (or a hash tree over them),
- the reference table mapping refs to L2 features and geometric signatures.

**ACP-3.5-02** The identifier **SHOULD** be rendered as the first 12 lowercase hex
characters for human display, and **MUST** be used in full where collision resistance
matters.

**ACP-3.5-03** Two revisions with the same identifier **MUST** be byte-identical in cause,
effect, and reference table. If a rebuild produces a different effect from an identical
cause, the implementation **MUST** treat this as an error, not as a new revision.

### 3.6 Effect canonicalisation

The effect of an artifact is usually stored in a container that carries information
unrelated to geometry: editor-assigned identity, timestamps, session GUIDs, view state,
creation ordering, and float formatting noise. Hashing such a container byte-for-byte
yields an identifier that changes when nothing geometric changed — and that an independent
party cannot reproduce.

**ACP-3.6-01** Where the effect container carries volatile state, the effect hash **MUST** be
computed over a canonical form that removes that state, not over the container bytes as
written.

**ACP-3.6-02** The canonicaliser **MUST** be identified by name and version in the revision
manifest (`effect.canonicalizer`). Otherwise a revision identifier that changed because the
canonicaliser was upgraded is indistinguishable from a geometry change.

**ACP-3.6-03** The canonical form **MUST** be reproducible by an independent implementation
from the same cause. Where the canonical form is not human-readable text, a text projection
**MUST** be published alongside it so two revisions can be diffed by a reviewer.

**ACP-3.6-04** Two runs of the same cause with the same canonicaliser version **MUST** produce
byte-identical canonical output. A difference **MUST** be treated as an error and **MUST NOT**
be absorbed by widening a gate threshold.

> Rationale: without this rule, an artifact whose exporter writes a timestamp cannot
> participate in ACP at all, and one whose exporter emits entities in creation order
> produces a new “revision” on every save. Both failures present as protocol instability
> when the defect is in the exporter. The rule also makes review possible: a reviewer can
> only diff what is stable.

---

## 4. Invariants

The core of ACP is six invariants. A profile may specialise their vocabulary; a profile
**MUST NOT** weaken them.

**I1 — Version anchoring.**
Every statement about an artifact binds to an immutable revision. No note, measurement, or
ledger entry exists without a revision identity.

**I2 — Cause/effect duality.**
Selection is expressed in the effect layer; modification is expressed in the cause layer;
the protocol carries the translation between them and never conflates the two.

**I3 — Persistent logical identity, ephemeral presentation index.**
L2 names persist; L3 refs do not. Implementations must never quietly promote a ref into a
durable identifier.

**I4 — Reconnection by fingerprint, with explicit degradation.**
When a ref does not survive a rebuild, the implementation attempts to re-establish the
correspondence by geometric/structural fingerprint matching, and **records what it matched
and with what confidence**. If matching fails, it degrades explicitly to "please select
again". It **MUST NOT** guess silently.

**I5 — Machine-checkable acceptance.**
A change is accepted only if a gate passes. The gate is executable code with a numeric
threshold, not a narrative. An agent's own claim of success is not evidence.

**I6 — Append-only shared memory.**
The ledger is ordered, append-only, and readable by both parties. Corrections are new
entries, never rewrites.

---

## 5. Wire Formats

All formats are JSON (RFC 8259), UTF-8, with `additionalProperties: false` for
interoperability. JSON Schemas are normative and are published under `schema/`.

### 5.1 Note

A note is the minimal unit a human creates by pointing at an artifact and stating an
intent.

**ACP-5.1-01** A note **MUST** contain: `id`, `artifact`, `rev`, `refs`, `intent`,
`created`, `status`.

**ACP-5.1-02** `refs` **MUST** be non-empty, and every ref **MUST** resolve in `rev` at
the moment the note is accepted. If any ref fails to resolve, the note **MUST** be
rejected with a machine-readable reason.

**ACP-5.1-03** `intent` **MUST** be the human's own words. Implementations **MUST NOT**
rewrite `intent`; a machine interpretation, if any, belongs in a separate field
(`op`/`params`), and the original text is preserved verbatim.

**ACP-5.1-04** `status` **MUST** be one of `new`, `acked`, `done`, `failed`. States other
than these (e.g. `in_review`) are profile-level extensions and **MUST** be namespaced.

```json
{
  "id": "20261017-115119",
  "artifact": "s-duct",
  "rev": "f1ad97db35cf",
  "created": "2026-10-17T11:51:19",
  "intent": "这个管子再搞弯一些",
  "op": "set_param",
  "params": { "A_mm": 90 },
  "refs": ["#o1.1.f1"],
  "status": "new"
}
```

Rendered form (human-facing, Quick-Edit style), with the file prefix being the canonical
cause/effect path the agent will open:

```
意图: 这个管子再搞弯一些
操作: set_param {"A_mm": 90}
File: /models/s-duct/STEP/s_duct.step
References:
/models/s-duct/STEP/s_duct.step#o1.1.f1
(revision: f1ad97db35cf, note id: 20261017-115119)
```

**ACP-5.1-05** The rendered form **MUST** carry the revision and the note id, so that a
note pasted into a chat window remains anchored.

### 5.2 Revision manifest

**ACP-5.2-01** A manifest **MUST** contain: `rev`, `artifact`, `created`, `cause`,
`effect`, `features`, `refs`, `gate`.

**ACP-5.2-02** `refs` **MUST** map every minted ref to an L2 feature name and the
geometric signature used for reconnection.

**ACP-5.2-03** `gate` **MUST** record the executed check(s), the numeric threshold, the
measured value, and the pass/fail outcome. A manifest whose gate has no measured value
**MUST NOT** be published.

```json
{
  "rev": "f1ad97db35cf",
  "artifact": "s-duct",
  "created": "2026-10-17T11:45:02",
  "cause": { "path": "src/gen_sduct.py", "hash": "sha256:...", "params": { "D_mm": 120, "A_mm": 50, "L_mm": 700 } },
  "effect": { "path": "STEP/s_duct.step", "hash": "sha256:9c1f...", "faces": 3 },
  "features": ["inlet", "outlet", "wall"],
  "refs": {
    "#o1.1.f1": { "feature": "wall",   "area_mm2": 276718.258, "centroid": [350.006, 40.0, 0.0], "normal": [0, -1, 0] },
    "#o1.1.f2": { "feature": "inlet",  "area_mm2": 11309.734,  "centroid": [0.0, 0.0, 0.0],    "normal": [-1, 0, 0] },
    "#o1.1.f3": { "feature": "outlet", "area_mm2": 11309.734,  "centroid": [700.0, 0.0, 0.0],  "normal": [1, 0, 0] }
  },
  "gate": [
    { "check": "volume_vs_analytic", "limit": 0.02, "measured": 0.00004, "unit": "relative", "ok": true },
    { "check": "bbox_vs_analytic",   "limit": 1.0,  "measured": 0.0,     "unit": "mm",       "ok": true },
    { "check": "area_vs_analytic",   "limit": 0.02, "measured": 0.004,   "unit": "relative", "ok": true }
  ]
}
```

### 5.3 Ledger event

**ACP-5.3-01** A ledger event **MUST** contain: `seq`, `at`, `type`, `actor`, `rev`,
`payload`.

**ACP-5.3-02** `seq` **MUST** be strictly increasing within a ledger. Implementations
**MUST NOT** rewrite or delete a committed event; a correction is a new event with
`type: "correction"` referring to the corrected `seq`.

**ACP-5.3-03** `actor` **MUST** identify a human, an agent, or a service, and **MUST** be
stable across events.

**ACP-5.3-04** Events describing a measurement **MUST** include the measured values
before and after, so that a decision can be replayed without re-running the system.

```json
{"seq": 41, "at": "2026-10-17T12:10:04", "type": "change_applied", "actor": "agent:dana",
 "rev": "f1ad97db35cf", "payload": {"note": "20261017-115119", "feature": "wall",
 "op": "set_param", "params": {"A_mm": 50}, "measured_before": {"A_mm": 50},
 "measured_after": {"A_mm": 90}, "result_rev": "a91f02c7e1d4", "verified": true}}
```

---

## 6. Operations

### 6.1 Anchor

Resolve a ref against a revision.

**ACP-6.1-01** Anchor **MUST** fail closed: unknown ref, ref from another revision, or
artifact mismatch all produce an error, never a best-effort guess.

### 6.2 Reconnect

Establish the correspondence between a previous revision's selection and a new revision.

**ACP-6.2-01** Reconnect **MUST** use a declared fingerprint (a named tuple of measurable
properties) and **MUST** apply a declared matching threshold.

**ACP-6.2-02** Reconnect **MUST** emit a record containing the matched candidates, the
chosen candidate, the distance metric value, and the method. This record is written to the
ledger.

**ACP-6.2-03** If no candidate satisfies the threshold, reconnect **MUST** report
`degraded: re-select` and **MUST NOT** return a best-effort match. Ambiguity (two
candidates within the threshold) **MUST** also be reported rather than resolved silently.

> Rationale: a silent wrong match is worse than asking the human to click again, because
> the wrong match is invisible while the re-click costs two seconds.

### 6.3 Apply

Modify the cause.

**ACP-6.3-01** Apply **MUST** be expressed as a change to the cause representation, never
to the effect representation.

**ACP-6.3-02** An agent performing Apply **MUST** operate within a permission surface that
excludes: network access, process spawning outside the declared build command, credential
access, and any write outside the artifact's cause directory. Profiles specify the exact
surface.

### 6.4 Verify

Run the gate.

**ACP-6.4-01** Verify **MUST** be executed by code, against numerically stated thresholds,
and **MUST** record measured values.

**ACP-6.4-02** Verify **MUST** include at least one check whose expected value is derived
independently of the modelling kernel used in Apply (e.g. an analytic formula, a
conservation law, or a pinned reference dataset).

> Rationale: a gate computed from the same kernel that produced the change tests
> self-consistency, not correctness. In the CAD profile, volume, bounding box, and boundary
> areas are compared against closed-form expressions.

**ACP-6.4-03** A gate that fails **MUST** block publication of the revision and **MUST**
produce a ledger event with `type: "gate_failed"`.

### 6.5 Publish

Make the new revision visible.

**ACP-6.5-01** Publish **MUST** be atomic with respect to readers: a reader sees either the
previous revision or the new one, never a mixture.

**ACP-6.5-02** Publish **MUST** emit the manifest before the revision becomes addressable.

---

## 7. Conformance Classes

The word "compliant" alone is uninformative. Implementations state a class.

| Class | Requires | Meaning |
|---|---|---|
| **Viewer** | I1, I3 (+ note creation per §5.1) | Can show a revision, mint refs, and collect notes. Cannot change anything. |
| **Anchor** | Viewer + I2, I4 | Can resolve refs and reconnect across revisions with a recorded fingerprint match. |
| **Editor** | Anchor + I5 | Can apply cause-layer edits and enforce a gate before publishing. |
| **Full** | Editor + I6 | Maintains a shared append-only ledger and can replay decisions. |

**ACP-7-01** An implementation claiming a class **MUST** pass the conformance checklist in
Appendix A for that class.

**ACP-7-02** An implementation **MUST** declare its class and its profile(s) in its
documentation, in the form `ACP v0.2 / Editor / CAD`, so that a counterpart knows what to
expect before exchanging anything.

---

## 8. Profiles

A profile maps the four layers onto a concrete domain and fixes the fingerprint and gate
vocabularies.

**ACP-8-01** A profile **MUST** define: L1 source, L2 vocabulary, L3 minting rule, cause
admissibility constraints, fingerprint tuple, and at least one gate check with its
threshold.

**ACP-8-02** A profile **MUST NOT** weaken any of the six invariants. It MAY add
domain-specific invariants.

`spec/profiles/cad.md` defines the parametric CAD profile with a working implementation.
`spec/profiles/simulation.md` defines the simulation profile, where L2 is a boundary-patch
or dictionary key and L1 includes the case definition plus the result timestep.
`spec/profiles/drawing2d.md` defines the 2D drawing profile (DXF/DWG), where L2 is a layer
or block name and effect canonicalisation is the profile's central requirement (§3.6). It is
design-level: unlike the CAD profile it has no reference implementation, and its thresholds
are derived geometrically rather than measured.

---

## 9. Security Considerations

### 9.1 Ref poisoning

A ref supplied by an untrusted party may point at a different region than intended, or at
a region chosen to cause an expensive rebuild.

**ACP-9.1-01** Anchor **MUST** return the geometric signature alongside the ref, so the
handling party can compare it against the revision manifest before acting.

### 9.2 Gate circumvention

**ACP-9.2-01** Publication **MUST** require a successful gate for the revision being
published; an implementation **MUST NOT** allow an override that is not itself recorded as
a ledger event with an explicit actor.

### 9.3 Agent permission surface

**ACP-9.3-01** The editing agent **MUST NOT** have write access to the revision store, the
ledger, or the gate definition. It writes only the cause.

**ACP-9.3-02** The gate **MUST** be evaluated in a separate context from the agent's
edit — either a separate process or a separate trust domain.

### 9.4 Replay and forgery

**ACP-9.4-01** Ledger entries **SHOULD** be chained (each entry including the hash of its
predecessor) so that truncation or reordering is detectable.

### 9.5 Denial of service via expensive rebuilds

**ACP-9.5-01** Implementations **SHOULD** bound the cost of a single apply+verify cycle and
**SHOULD** rate-limit notes from unauthenticated sources.

---

## 10. Privacy Considerations

**ACP-10.1-01** `intent` contains human natural language and **MAY** contain sensitive
information. Implementations that transmit notes to a third-party model **MUST** disclose
this in their documentation.

**ACP-10.2-01** The ledger is append-only by design; implementations **MUST** provide a
documented mechanism for retention limits that does not silently rewrite history (e.g.
segment-level expiry with a recorded tombstone).

---

## 11. Versioning and Extensibility

**ACP-11.1-01** Unknown fields **MUST** be rejected in the core formats
(`additionalProperties: false`). Extensions use namespaced keys (`x-<vendor>-<field>`) and
MUST be ignorable.

**ACP-11.2-01** A change that removes a REQUIRED field or changes the meaning of an
existing field requires a major version increment.

---

## 12. References

- RFC 2119 — Key words for use in RFCs to Indicate Requirement Levels
- RFC 8174 — Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words
- RFC 8259 — The JavaScript Object Notation (JSON) Data Interchange Format
- JSON Schema 2020-12
- ISO 10303 (STEP) — industrial automation systems and integration: product data
  representation and exchange
- W3C Web Annotation Data Model — selector vocabulary relevant to L3
- W3C PROV-DM — provenance model relevant to §5.3

---

## Appendix A — Conformance checklist

Answer yes/no; any "no" means the class is not claimed.

**Viewer**
- [ ] A1. Revision identifier is a hash over cause + effect + ref table (§3.5).
- [ ] A2. Refs are rejected when presented against a different revision (§3.2-01).
- [ ] A3. Notes preserve `intent` verbatim (§5.1-03).
- [ ] A4. Note creation fails when any ref does not resolve (§5.1-02).

**Anchor**
- [ ] B1. Anchor returns ref + revision + geometric signature (§6.1, §3.3-01).
- [ ] B2. Reconnect uses a declared fingerprint and threshold (§6.2-01).
- [ ] B3. Reconnect records the match, its metric, and its method (§6.2-02).
- [ ] B4. Failed reconnect degrades explicitly instead of guessing (§6.2-03).

**Editor**
- [ ] C1. Edits are applied to the cause, not the effect (§6.3-01).
- [ ] C2. Gate is code with numeric thresholds and measured values (§6.4-01).
- [ ] C3. At least one gate check is kernel-independent (§6.4-02).
- [ ] C4. A failed gate blocks publication (§6.4-03).

**Full**
- [ ] D1. Ledger is append-only with strictly increasing `seq` (§5.3-02).
- [ ] D2. Corrections are new events, not rewrites (§5.3-02).
- [ ] D3. Measurements before/after are recorded (§5.3-04).
- [ ] D4. Ledger entries are chained by hash (§9.4-01).

---

## Appendix B — Design rationale (non-normative)

**Why not just use git?**
git already gives L1 and a durable L2 for text. What it does not give is the *translation*
between a selected region of the rendered effect and a named cause. A commit tells you
that `hole_a` changed; it cannot tell you which surface the human clicked. ACP is the
missing middle: it takes the click, resolves it to a feature, and then hands the actual
editing to ordinary source control practice.

**Why not assign a UUID to every face?**
Because face identity is not stable under rebuild in any kernel that supports real
modelling operations. A persistent UUID per face would have to be maintained by the
kernel across re-topologisation, which is exactly the problem kernel vendors have worked
on for decades without a universal answer. ACP takes the opposite position: refs are
*disposable*, and durability is obtained by re-deriving the mapping and recording the
evidence.

**Why insist on refs being revision-scoped?**
Because the alternative is worse in a way that is invisible. If refs are assumed stable,
the first upstream change that renumbers faces silently redirects every existing note to
the wrong region. A protocol that fails loudly at that moment is more useful than one that
succeeds incorrectly.

**Why is the gate required to include a kernel-independent check?**
A change verified only by the kernel that produced it is tested for self-consistency. The
interesting failures — wrong parameter mapped to the wrong feature, stale cache, a
modelling operation that silently no-ops — are precisely the ones the kernel will not
catch. Analytic or conservation checks catch them because they were computed before the
change existed.

**Why a ledger rather than a database of current state?**
Because the question people actually ask is "why is it like this?" A current-state table
answers "what", a ledger answers "why", and an agent-mediated workflow needs the latter
to be reviewable. Append-only also makes the record resistant to well-intentioned
tidying.

**Why does the protocol not require a specific agent architecture?**
Because the failure modes it prevents — wrong-region edits, unverified claims, lost
provenance — exist regardless of how the editing is organised. Binding the protocol to one
architecture would date it within a year.
