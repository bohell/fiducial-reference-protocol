# FRP Profile: 2D Drawings

**Profile identifier:** `frp-drawing2d/0.2` · Core requirement: FRP v0.2 (§ references are to the core spec)

This profile maps the four FRP layers onto two-dimensional drawings: flat parts, plates,
gaskets, hole patterns, profiles, and drawing sheets. The cause is a text program that
emits drawing entities; the effect is a canonicalised DXF plus the entity table used for
picking.

**Implementation status.** This profile is design-level. Unlike the CAD profile it is
**not** backed by a reference implementation, so the thresholds in §5 are defaults derived
from geometry, not measured values from a working system. An implementation adopting this
profile **SHOULD** publish its measured margins so these defaults can be replaced with
evidence. Stating this explicitly is the point: a threshold with a measured number behind
it and a threshold with a plausible number behind it are not the same artifact.

---

## 1. Layer mapping

| Layer | In 2D drawings |
|---|---|
| **L1 revision** | SHA-256 over (cause source bytes ‖ canonical DXF bytes ‖ ref table), truncated to 12 hex for display |
| **L2 feature** | A layer name, a block name, or a named constant in the generating source (`plate_w`, `hole_d`, `PITCH`) |
| **L3 ref** | `#e<index>` — the entity's index in canonical order, minted per revision |
| **Cause** | The generating program (AutoLISP/`.scr` driven headlessly, or a script that emits DXF) |
| **Effect** | The canonical DXF plus the entity table used for picking |

**Profile rule D2-1-01** A ref **MUST NOT** be derived from a DXF handle, an object id, or
any other editor-assigned identifier. Handles are reassigned when a drawing is rewritten
and often change on a no-op save. Refs are positional within one revision and are not
durable (core I3).

**Profile rule D2-1-02** The ref table in the manifest **MUST** carry, per ref: L2 feature
name, entity type, `length_perimeter_mm` (mm), centroid (mm), and the bounding-box diagonal
used to normalise distances.

**Profile rule D2-1-03** Layer names and block names **MUST** survive canonicalisation
verbatim, because they are the L2 vocabulary humans actually use when discussing a drawing.

## 2. Cause admissibility in this profile

Beyond core §3.4:

**Profile rule D2-2-01** The cause **MUST** be re-runnable headlessly with a fixed parameter
set — either a script executed by a headless drawing engine, or a program that emits DXF
directly.

**Profile rule D2-2-02** Parameters a human is expected to discuss **MUST** be declared as
named constants, not computed inline, so an agent can rewrite them without parsing the
drawing logic.

**Profile rule D2-2-03** The cause **MUST NOT** depend on ambient state. This includes the
current layer, the active linetype and text-style tables, the user profile, and the locale.
Locale is not a formality: a decimal comma changes every coordinate in the effect.

**Profile rule D2-2-04** The cause **MUST** be self-contained. A drawing whose geometry
depends on external references is admissible only if those references are part of the cause
set and hashed together with it.

### 2.1 The hand-drawn case

A drawing that exists only as a hand-produced file has **no cause**. It cannot be rebuilt
from anything, so under **FRP-3.4-01** an implementation **MUST** refuse it for the Editor
class rather than pretending to reconstruct an edit history.

Such a drawing is still admissible as an *anchor target*: revisions can be snapshotted, refs
minted, notes collected, and reconnection attempted between snapshots. The honest ceiling is
**Anchor**, with the caveat that every snapshot is an independent leaf — there is no
derivation relation between them, so the ledger records "a new file appeared", not "a change
was applied". Implementations **MUST** state which of these two they are doing.

## 3. Effect canonicalisation

This section is the substantive requirement of the profile. Hashing a DXF or DWG container
byte-for-byte does **not** produce a stable revision identifier, because the container
carries state that has nothing to do with geometry:

| Class | Examples |
|---|---|
| Editor-assigned identity | entity handles, `$HANDSEED`, owner/pointer fields |
| Timestamps | `$TDUPDATE`, `$TDCREATE`, `$TDINDWG`, `$TDUSRTIMER` |
| Session identity | `$FINGERPRINTGUID`, `$VERSIONGUID`, user and machine names |
| Session state | current layer and tab, views, viewport, embedded thumbnails |
| Ordering | entity order reflects creation history, not geometry |
| Numeric noise | trailing digits from the emitter's float formatting |

**Profile rule D2-3-01** The effect hash **MUST** be computed over a canonical form that
removes at least every class in the table above.

**Profile rule D2-3-02** Canonicalisation **MUST**:

1. sort entities by a geometric key — layer name, entity type, then rounded bounding-box
   minimum, then rounded centroid;
2. re-serialise every coordinate at a fixed decimal precision;
3. emit a fixed header containing only a whitelisted set of variables, with all volatile
   variables dropped rather than zeroed;
4. emit layer, block, and style tables in sorted order;
5. normalise line endings and encoding.

**Profile rule D2-3-03** The canonicaliser **MUST** be identified in the manifest by name
and version (`effect.canonicalizer`). Without this, a revision identifier that changes
purely because the canonicaliser was upgraded is indistinguishable from a geometry change —
and the first such upgrade silently invalidates every historical ref.

**Profile rule D2-3-04** Two runs of the same cause **MUST** produce byte-identical
canonical output. A difference **MUST** be reported as an error, not absorbed by widening a
gate threshold (core FRP-3.5-03).

**Profile rule D2-3-05** The canonical form **MUST** be human-readable text. A binary
effect format is admissible only together with its canonical text projection, and the hash
**MUST** be taken over the projection. A reviewer must be able to diff two revisions.

## 4. Ref minting

**Profile rule D2-4-01** Refs **MUST** be minted from the canonical entity order, so that two
mints of the same revision assign the same ref to the same entity.

**Profile rule D2-4-02** The minting step **MUST** verify in a fresh process that every ref
resolves and that the resolved geometry matches the values recorded in the table. A ref table
that cannot be re-resolved **MUST NOT** be published.

**Profile rule D2-4-03** Entity count and per-entity length are the primary evidence of
correspondence between the displayed drawing and the exported DXF.

## 5. Gate

A conforming gate includes at least one kernel-independent check (**FRP-6.4-02**). In 2D
almost every quantity has a closed form, so this is cheaper than in 3D — there is no excuse
for a gate that only re-measures what the drawing engine just produced.

| Check | Metric | Default threshold | Catches |
|---|---|---|---|
| area | relative difference vs analytic | **1e-4** | wrong hole diameter, missing hole, wrong notch depth |
| perimeter | relative difference vs analytic | **1e-4** | wrong radius, wrong chamfer, wrong fillet |
| bounding box | absolute, mm per axis | **0.05 mm** | wrong overall size, displaced origin |
| contour closure | maximum endpoint gap | **1e-6 mm** | an unclosed contour that breaks machining |
| entity count | exact equality | **0** | a feature silently dropped by the emitter |

These are defaults, not measurements — see the note at the top of this document.

**Profile rule D2-5-01** Area and perimeter **MUST** be compared against values derived
outside the drawing engine, from the parametric definition.

**Profile rule D2-5-02** The closure check **MUST** be present. An unclosed contour is
geometrically valid, renders correctly, and is unusable: it is the single most expensive
failure to discover after the part is cut.

**Profile rule D2-5-03** The entity-count check **MUST** be present. It is the only check
that reliably catches a dropped feature, because removing a hole from a plate changes area by
a small and easily-tolerated percentage.

**Profile rule D2-5-04** A gate **MUST** report all checks, not stop at the first failure
(core **FRP-6.4-03** requires blocking publication; it does not require early exit).

## 6. Reconnect

Fingerprint tuple: `(entity_type, length_perimeter_mm, centroid, bbox_diag)` with these
default thresholds. A profile **MAY** tighten them; it **MUST** state the values used.

| Property | Metric | Threshold |
|---|---|---|
| entity type | exact match | — |
| length / perimeter | relative difference | ≤ 1e-3 |
| centroid | Euclidean distance | ≤ 1e-3 · diagonal(bbox) |
| bbox diagonal | relative difference | ≤ 1e-2 |

**Profile rule D2-6-01** Matching **MUST** be attempted over the whole entity set and
**MUST** report the number of candidates within threshold. More than one candidate is
`ambiguous` and degrades to re-selection (core **FRP-6.2-03**).

**Profile rule D2-6-02** A match that lands on a *different* L2 feature name **MUST** be
treated as a failed reconnect even if the geometry is within threshold.

**Profile rule D2-6-03** When an edit changes the entity decomposition — exploding a
polyline, joining two lines, trimming a contour — reconnect **MAY** degrade from entity level
to contour level, but it **MUST** record the degradation and the resulting coarser ref. It
**MUST NOT** silently map a ref to a contour while claiming entity-level precision.

## 7. Permission surface for the editing agent

**Profile rule D2-7-01** The agent's write surface **MUST** be the cause script. It **MUST
NOT** write the DXF, the entity table, the manifest, or the ledger (core **FRP-9.3-01**).

**Profile rule D2-7-02** The gate **MUST** run outside the agent's editing context, and the
agent **MUST NOT** be able to alter thresholds.

**Profile rule D2-7-03** The agent **MUST NOT** be given control of an interactive drawing
session. Session edits are exactly the non-reproducible path: they produce an effect with no
cause, which cannot be rebuilt, gated, or replayed. This is a permission rule precisely
because it is convenient to break.

## 8. Display binding

**Profile rule D2-8-01** The viewer **MUST** display the revision identifier alongside the
drawing and **MUST** reload when the revision changes.

**Profile rule D2-8-02** Picking **MUST** resolve to the canonical entity index, not to a
renderer object id. A ref that means "the third mesh the browser created" is not an FRP ref.

**Profile rule D2-8-03** The viewer **MUST** treat missing optional fields in the ref table
as non-fatal, consistent with core **FRP-5.1-02**: a ref must resolve, but the presence of
every optional descriptor is not a precondition for note creation.

---

## Appendix A — Applicability to AutoCAD and SolidWorks (informative)

This appendix records how the profile maps onto the two systems it is most often asked
about. It is informative: an implementation still has to satisfy the normative rules above.

### A.1 AutoCAD

AutoCAD ships a headless command-line engine (`accoreconsole.exe`) with the desktop product
(2013 and later). It runs the same drawing engine without a user interface, accepts
AutoLISP and .NET, and is suitable for batch work. This satisfies the headless requirement
of **D2-2-01** without a separate licence.

Two constraints follow:

1. **Hand-drawn DWG is not an admissible cause.** See §2.1. This is the profile's own rule
   refusing the case, not a limitation of AutoCAD.
2. **The native container is not hashable as-is.** DWG and DXF both carry handles,
   timestamps, GUIDs, and session state. **D2-3-01** through **D2-3-05** exist because of
   this. The practical route is to hash a canonical ASCII DXF export, which is also what
   makes review possible: a reviewer can diff two revisions.

Layers and blocks map directly onto L2, which is the strongest part of the fit.

### A.2 SolidWorks

A SolidWorks part is a feature tree in a binary container, edited and rebuilt by a COM
automation interface that drives a running application process. There is no
vendor-supported headless mode analogous to `accoreconsole`. That is an engineering
constraint the protocol cannot remove.

The workable mapping is therefore **not** this profile but the CAD profile, with the cause
being the external inputs the model is built from:

- a **design table** (CSV) that drives dimensions and configurations,
- an **equation file** for derived quantities,
- the model file itself as the effect generator.

Under that mapping the cause is text, diffable, and editable without a GUI — which is what
core §3.4 actually asks for. SolidWorks is stronger than AutoCAD on L2, because a feature
tree with named dimensions and named features is already the vocabulary humans use.

For a **drawing** produced from a SolidWorks model (`.SLDDRW`), the causal chain has two
links: drawing ← model ← parameters. This profile requires the cause to be the thing that
determines geometry, so for such a drawing the cause is the *model*, not the drawing file.
Exporting the drawing to DXF does not transfer admissibility to the drawing itself.

---

## Appendix B — Conformance ceiling by target (informative)

| Target | Viewer | Anchor | Editor | Full |
|---|---|---|---|---|
| Script-generated DXF | ✓ | ✓ | ✓ | ✓ |
| AutoCAD, script-generated DWG | ✓ | ✓ | ✓ with canonical DXF | ✓ with canonical DXF |
| AutoCAD, hand-drawn DWG | ✓ | ✓ | ✗ no cause (§2.1) | ✗ |
| SolidWorks part | ✓ | ✓ | via design table, CAD profile | via design table, CAD profile |
| SolidWorks drawing | ✓ | ✓ | cause is the model, not the drawing | same |

An implementation **MUST** declare the ceiling it actually reaches rather than the one its
tooling suggests (**FRP-7-02**).
