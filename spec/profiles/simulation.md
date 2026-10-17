# FRP Profile: Simulation Case

**Profile identifier:** `frp-sim/0.2` · Core requirement: FRP v0.2

This profile maps FRP onto a CFD/simulation case whose cause is a set of dictionaries and a
mesh recipe, and whose effect is a mesh plus a sequence of result fields.

The interesting problem here is that a simulation artifact has **two** effects with
different lifetimes: the mesh (a snapshot) and the solution (a trajectory). FRP treats the
mesh as the L1-bound effect and the solution as an append-only series of *derived* states,
each carrying the revision identity of the case that produced it.

---

## 1. Layer mapping

| Layer | In a simulation case |
|---|---|
| **L1 revision** | Hash over the case definition (dictionaries + geometry + mesh recipe + solver settings) |
| **L2 feature** | A boundary patch name (`inlet`, `wall`), a `fvSolution` solver key, a `fvSchemes` scheme entry, a named function object |
| **L3 ref** | A patch face index or a dictionary line address **valid in one mesh revision only** |
| **Cause** | `system/` + `constant/` dictionaries, the geometry (STEP/STL), the meshing recipe |
| **Effect** | The generated mesh, plus result fields per timestep |

**SIM-1-01** The L1 revision **MUST** include the meshing recipe and the geometry files. A
case whose mesh was produced by a recipe that is not part of the revision identity cannot
be reproduced, and its refs become meaningless.

**SIM-1-02** Result data **MUST NOT** be part of the L1 hash. Results are derived; including
them would make every solver run a new revision identity and destroy note anchoring across
a run.

**SIM-1-03** A result snapshot **MUST** reference the L1 revision it was computed from, so a
measurement cites both "which case" and "which run".

## 2. Cause admissibility

**SIM-2-01** The case **MUST** be reconstructible from its declared files alone: no
hand-edited mesh, no interactive GUI steps, no undocumented environment.

**SIM-2-02** Mesh generation **MUST** be re-runnable and **MUST** be verified by a quality
gate (§4) before any refs are minted.

**SIM-2-03** Nondeterministic parallel mesh/solver output is acceptable, provided the
revision identity is computed over inputs only (per SIM-1-02).

## 3. Ref minting

**SIM-3-01** Because patch face indices depend on the mesh, refs **MUST** be minted only
after a successful quality gate, and the ref table **MUST** record the mesh cell count and
per-patch face count.

**SIM-3-02** For a case whose geometry is swept from a parametric source, the profile
**RECOMMENDS** carrying the geometry revision as a *sub-revision* so that a geometry edit and
a solver-settings edit produce distinguishable history.

## 4. Reconnect

Fingerprint tuple for a patch ref: `(patch_name, face_count, total_area, centroid)`.

**SIM-4-01** Patch name alone is a **sufficient** reconnect key when the name persists —
this is the profile's main advantage over pure geometry matching, since patch names are
semantic (L2) and survive remeshing.

**SIM-4-02** When a patch is renamed, the manifest **MUST** record the rename mapping (core
§3.2-02) so that reconnect succeeds with an explicit record rather than by coincidence.

**SIM-4-03** Face-index-level refs **MUST** degrade to patch-level refs when the mesh
changes, rather than attempting index arithmetic. A face index is a location in a
particular mesh, not an identity.

## 5. Gate

A conforming simulation gate runs mesh quality checks *before* minting refs and, where the
case has a defined quantity of interest, records the measurement in the ledger.

```text
checkMesh:
  - max non-orthogonality     <= 70 deg    (profile default)
  - max skewness              <= 4         (profile default)
  - min volume                >  0
  - mesh OK verdict           == true
```

**SIM-5-01** The gate **MUST** fail closed: if `checkMesh` does not report a clean verdict,
no refs are minted and no note may be created against the mesh.

**SIM-5-02** Where a closed-form or conservation check exists for the quantity of interest,
it **SHOULD** be included as a kernel-independent check (core §6.4-02). Examples: mass flow
conservation between inlet and outlet; drag on a body in creeping flow versus an analytic
solution; total mass in a closed domain conserved to solver tolerance.

**SIM-5-03** Measured values used in a decision (a force coefficient, a pressure drop) **MUST**
be recorded in the ledger with the time window over which they were averaged, so that a
reported number is reproducible from the record.

> Reference implementation note: a force coefficient read from the wrong column of a
> coefficient file looks entirely plausible and will silently invalidate a long experiment.
> The gate should assert column semantics against a known anchor (for example, that the
> measured drag reproduces an independently computed value on a pinned case).

**SIM-5-04** Where a statistical quantity is reported from a transient run, the gate
**MUST** state the averaging window and **SHOULD** state the sampling uncertainty. A single
instantaneous value is not a converged statistic.

## 6. Permission surface

**SIM-6-01** An editing agent **MUST NOT** be able to modify the mesh directly, the gate
thresholds, or recorded results. It edits dictionaries and the geometry recipe only.

**SIM-6-02** An agent that starts a solver run **MUST** operate under a time and resource
budget declared in advance; an unbounded run is a denial-of-service vector (core §9.5).

## 7. Display binding

**SIM-7-01** A viewer **MUST** display the case revision alongside any field rendering, so
that an annotation made on a screenshot is anchored to a reproducible state.

**SIM-7-02** Where a rendering uses a colormap range, the range **MUST** be part of the
annotation context when the annotation refers to a visual feature. An automatic range on a
field with outliers renders the interesting structure invisible while remaining technically
correct.

> Reference implementation note: a vorticity slice with an auto range spanning ±535 mapped
> the physical range (±50) into a narrow band of mid-grey. Fixing the range to a symmetric
> ±250 with a diverging colormap restored the visible structure. The annotation "this
> recirculation zone" is meaningless if the zone cannot be seen.

## Appendix A — Where this profile is thin (informative)

- **Transient result annotation.** Annotating a feature that exists for only part of a
  transient (a shed vortex) needs a time-scoped ref. This profile currently handles it by
  binding the note to `(revision, timestep)` in the payload rather than minting a time-aware
  L3. A future revision of the profile may formalise time refs.
- **Ensemble runs.** A parameter sweep produces many runs from one case revision. The
  profile treats each run's snapshot as a derived state; a first-class "run set" object is
  not yet specified.
- **Mesh-independence studies.** Comparing quantities across refinement levels needs a
  declared refinement identity; the profile leaves this to a `x-` extension for now.
