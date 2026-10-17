# FRP Profile: Parametric CAD

**Profile identifier:** `frp-cad/0.2` · Core requirement: FRP v0.2 (§ references are to the core spec)

This profile maps the four FRP layers onto parametric CAD whose cause is a text program
and whose effect is an exported B-rep (STEP) plus a triangle tessellation for display.

It is backed by a working end-to-end implementation: a human picks a face in a browser,
a note is created, an agent edits the parametric source, an independent analytic gate runs,
a new revision is published, and the viewer reloads — with the ledger recording each step.

---

## 1. Layer mapping

| Layer | In CAD |
|---|---|
| **L1 revision** | SHA-256 over (cause source bytes ‖ effect STEP bytes ‖ ref table), truncated to 12 hex for display |
| **L2 feature** | A named symbol in the source: a parameter (`A_mm`), a sketch variable (`hole_d`), a named solid or face group (`wall`, `inlet`) |
| **L3 ref** | `#o<solid>.<occurrence>.f<face>` — minted per revision from the tessellation |
| **Cause** | The parametric script (build123d, OpenSCAD, FreeCAD `Document.xml`, CadQuery) |
| **Effect** | The exported STEP plus the per-face tessellation used for picking |

**Profile rule CAD-1-01** A ref **MUST** encode the solid and occurrence index it was
minted from, so that imports of multiple instances do not collide.

**Profile rule CAD-1-02** The ref table in the manifest **MUST** carry, per ref: L2 feature
name, area (mm²), centroid (mm), and outward normal. These four are the reconnect
fingerprint.

## 2. Cause admissibility in this profile

Beyond core §3.4:

**CAD-2-01** The script **MUST** be runnable headlessly with a fixed parameter set and
**MUST** produce byte-identical STEP output on repeated runs. Floating-point non-determinism
in the kernel exporter is admissible only under core §3.6: the effect hash is then computed
over a canonicalised STEP (re-serialised with sorted entity ordering), and the canonicaliser
is recorded in the manifest per **FRP-3.6-02**. What was a CAD-specific exception in v0.1 is
now an application of the core rule.

**CAD-2-02** Parameters that a human is expected to discuss **MUST** be declared as named
module-level constants, not computed inline, so that an agent can rewrite them without
parsing the modelling logic.

> Reference implementation note: parameters are declared with a machine-visible marker on
> the same line:

```python
D = 120.0  # GEN:D
A =  50.0  # GEN:A
L = 700.0  # GEN:L
```

An agent rewrites the value and keeps the marker. The marker doubles as a guard: if the
rewrite cannot be verified, the build aborts rather than silently using a stale value.

**CAD-2-03** The script **MUST NOT** read the ambient environment to determine geometry.
Parameters come from the script's own literals. (A daemon that caches builds by source
path will otherwise hand back geometry from a previous parameter set — see Appendix A.)

## 3. Ref minting

**CAD-3-01** Refs **MUST** be minted deterministically from the tessellation in a fixed
order (e.g. by solid, then occurrence, then face index in kernel iteration order). Two
mints of the same revision **MUST** produce the same ref for the same face.

**CAD-3-02** The minting step **MUST** verify, in a fresh process, that every ref resolves
and that the resolved area matches the value recorded in the table. A ref table that
cannot be re-resolved **MUST NOT** be published.

**CAD-3-03** Face count and per-face area are recorded as the primary evidence of
correspondence between the display artifact and the exported STEP.

## 4. Reconnect

Fingerprint tuple: `(area_mm2, centroid, outward_normal)` with the following default
thresholds (a profile MAY tighten them; it MUST state the values used):

| Property | Metric | Threshold |
|---|---|---|
| area | relative difference | ≤ 1e-3 |
| centroid | Euclidean distance | ≤ 1e-3 · diagonal(bbox) |
| normal | angle | ≤ 1° |

**CAD-4-01** Matching **MUST** be attempted over the whole face set, and **MUST** report
the number of candidates within threshold. More than one candidate is `ambiguous` and
degrades to re-selection (core §6.2-03).

**CAD-4-02** A reconnect that matches a face to a *different* L2 feature name **MUST** be
treated as a failed reconnect even if the geometry is within threshold. This catches
re-topologisation that happens to land on a geometrically similar but semantically
different face.

**CAD-4-03** Reconnect results **MUST** be appended to the ledger with the metric value
and the candidate count.

## 5. Gate

A conforming CAD gate includes at least one kernel-independent check. The reference
implementation uses three, all derived from closed-form expressions evaluated before the
model is built:

```python
# Swept circular duct: volume = πR² × arc length of the centre-line
v_expect = math.pi * R**2 * arclen_mm
rel_vol  = abs(solid.volume - v_expect) / v_expect
assert rel_vol < 0.02                       # CAD-5-01

# Bounding box from the parametric definition
assert abs(bbox.X - L) < 1.0                # mm tolerance
assert abs(bbox.Y - (2*A + D)) < 1.0
assert abs(bbox.Z - D) < 1.0

# Boundary areas: ends = πR², lateral = 2πR × arclen
assert abs(area_inlet  - math.pi * R**2) / (math.pi * R**2) < 0.02
assert abs(area_wall   - 2*math.pi*R*arclen_mm) / (2*math.pi*R*arclen_mm) < 0.02
```

**CAD-5-01** Volume relative error limit: **2 %**. Rationale: a swept solid with a
non-trivial guide curve is tessellated before the kernel computes volume; 2 % admits
tessellation error while catching wrong radius, wrong length, and wrong sweep direction
(each of which produces errors of tens of percent).

**CAD-5-02** Bounding box limit: **1 mm** per axis. Catches a swept profile oriented on the
wrong plane — a failure mode that leaves volume unchanged.

**CAD-5-03** Boundary area limits: **2 %** relative. Catches a closed solid whose ends are
capped when they should be open (area 0 instead of πR²) and a lateral surface with the
wrong perimeter.

**CAD-5-04** A gate **MUST** report all checks, not stop at the first failure, so that a
single ledger entry explains the whole state.

Measured reference values for `D=120, A=50, L=700` (mm):

| Check | Expected | Measured | Relative error |
|---|---|---|---|
| volume | 5 147 525.7 mm³ | 5 147 751.9 mm³ | 4.4e-05 |
| bbox | 700 × 220 × 120 | 700 × 220 × 120 | 0 |
| inlet area | 0.011310 m² | 0.011310 m² | < 1e-6 |
| wall area | 0.205901 m² | 0.205909 m² | 4e-05 |

## 6. Permission surface for the editing agent

**CAD-6-01** The agent's write surface **MUST** be the cause script (and nothing else).
It **MUST NOT** write the STEP, the ref table, the manifest, or the ledger.

**CAD-6-02** The gate **MUST** run outside the agent's editing context — separate process
or separate trust domain — and the agent **MUST NOT** be able to alter the thresholds.

**CAD-6-03** The agent **MUST** be restricted from network access and from spawning
processes other than the declared build command.

## 7. Display binding

**CAD-7-01** The viewer **MUST** display the revision identifier alongside the model, and
**MUST** reload when the revision changes rather than showing a stale model.

**CAD-7-02** The viewer **MUST** treat missing optional fields in the ref table as
non-fatal: a face lacking `normal` renders without the normal line and **MUST NOT** block
note creation (core §5.1-02 requires ref resolution, not field completeness).

> Reference implementation note: this rule exists because an early ref table omitted
> `normal` and the viewer threw on `undefined.join`, leaving the submit button permanently
> disabled. One missing optional field silently disabled the primary action.

## 8. Related profiles

This profile covers artifacts whose cause is a text program and whose effect is a B-rep.
Two adjacent cases have their own profile or mapping:

- **2D drawings** (DXF/DWG, flat parts, hole patterns): see `drawing2d.md`. The decisive
difference is that a 2D container carries far more volatile state relative to its geometry,
so canonicalisation is the profile's central requirement rather than a footnote.
- **Feature-tree CAD** (a binary part edited through a vendor API): the cause is the
external input set the model is built from — a design table and equation file — not the
part file. See `drawing2d.md` Appendix A.2.

## Appendix A — Implementation hazards (informative)

These are real failures encountered while building the reference implementation. They are
listed because each one produced *plausible but wrong* behaviour rather than an error.

**A.1 Build caches keyed by source path.**
A CAD build daemon that records "this source path is up to date" will skip a rebuild when
the same path is reused with new parameters. Always build in a fresh directory per
invocation, or key the cache on a content hash.

**A.2 Daemon workers do not inherit per-call environment.**
Passing parameters via environment variables to a daemon is unreliable: the worker sees the
environment at daemon start. The symptom is the worst possible one — the build succeeds,
the geometry is from the *previous* parameter set, and the gate passes because it verified
that geometry. Parameters **must** live in the source content.

**A.3 Buffered output hides success flags.**
Redirecting a build's output to a log file and then searching the process pipe for a
success marker always fails. Parse the log, and use the exit status as a second signal.

**A.4 Overlay elements swallow pointer events.**
A translucent hint panel over a 3D canvas intercepts clicks in the region it covers.
`pointer-events: none` on purely presentational overlays is not cosmetic.

**A.5 Reload is not redeployment.**
When the protocol server is a long-lived child process, reloading configuration does not
replace the running process. The reliable check is *process start time versus file
modification time* — not the reload command's exit message.

**A.6 Absolute paths from one host in a command aimed at another.**
A destructive command that mixes a local shell with a remote absolute path is a latent
disaster. Verify the working directory before any recursive delete.
