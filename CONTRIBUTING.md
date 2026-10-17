# Contributing to ACP

The most valuable contribution right now is **not code**. It is disagreement, expressed
precisely.

## What we most want

### 1. A profile for a domain we have not covered

The core claims to be domain-neutral. That claim is only worth what a stranger can
demonstrate by filling in the four layers for their own domain. We have CAD and simulation.
We do not have:

- **ECAD / PCB** — where identity is usually *easier* (stable net and component ids), which
  makes it a good test of whether the L1/L2/L3 split is doing real work or just restating
  what ECAD already has.
- **Technical documentation** — clause numbers as L2, paragraph fingerprints as L3.
- **Data pipelines** — snapshot hash as L1, primary key as L2, cell coordinates as L3,
  generating query as cause.
- **Mesh/CAE without a parametric source** — the hard case: what is the *cause* when the
  artifact is a hand-built mesh? We suspect the answer is "the meshing recipe plus a
  registered provenance", but we have not proven it.

Write it as `spec/profiles/<domain>.md` following the shape of `cad.md`: layer mapping,
admissibility constraints, ref minting, reconnect fingerprint, gate, permission surface.
Include at least one **worked example with real numbers**. A profile without a number is a
wish.

### 2. A counterexample to one of the six invariants

If one of the invariants in §4 cannot be satisfied in your domain without making the
protocol useless, that is more interesting than a domain that fits. File an issue with the
concrete artifact and the concrete exchange that breaks. We would rather narrow an
invariant with a documented boundary than defend it with rhetoric.

### 3. A conformance test suite

The checklist in Appendix A is currently answered by humans reading their own code, which
is exactly the kind of self-assessment the protocol says not to trust. A test suite that
takes a candidate implementation and emits a conformance report would be the single most
useful piece of code in this project.

## What we will probably decline

- **A reference implementation in this repository.** The protocol should be implementable by
  anyone with any engine. Shipping our implementation here would quietly turn "ACP" into
  "our tool with a spec attached". Implementations live in their own repositories and link
  back.
- **A registry of artifacts or revisions.** A central authority contradicts the point.
- **Renaming the layers to something friendlier.** L1/L2/L3 are unglamorous on purpose;
  they resist being mistaken for product concepts.

## Process

1. Open an issue describing the problem before writing a large patch. Protocol changes that
   arrive as finished documents tend to be re-litigated from scratch.
2. For normative changes, state which requirement id (`ACP-<section>-<nn>`) you are
   changing and why the current text fails.
3. Prose style: RFC 2119 keywords in bold capitals only where they carry normative weight.
   No marketing adjectives. A claim about behaviour should be checkable by reading the
   implementation.
4. Numbers: any threshold you propose must come with the failure mode it catches and the
   measurement that set it. "2 % feels right" is not a rationale; "2 % catches wrong sweep
   direction (tens of percent) while admitting tessellation error (1e-4)" is.

## Versioning

Draft versions (0.x) may change wire formats between releases. Changes to a REQUIRED field
or to the meaning of an existing field require a major increment (currently: 0.x → 1.0).
Every change is recorded in `CHANGELOG.md` with the requirement ids affected.

## License

Contributions are accepted under Apache-2.0. By submitting a pull request you agree to
license your contribution under those terms.
