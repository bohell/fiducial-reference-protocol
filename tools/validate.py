#!/usr/bin/env python3
"""Repository checks for the FRP specification.

Runs the same checks locally and in CI. Exits non-zero on any failure.

  1. every *.json parses
  2. every *.jsonl line parses
  3. examples/ instances conform to schema/ (full JSON Schema when jsonschema
     is installed, structural fallback otherwise)
  4. every relative Markdown link resolves
  5. no internal identifiers or credentials leaked into tracked text files
  6. every normative requirement id (FRP-<sec>-<nn>) cited in a profile exists
     in the core specification

Usage:  python3 tools/validate.py [--root .] [--no-jsonschema]

`--no-jsonschema` forces the structural fallback, so CI can prove that both
engines reach the same verdict (a divergence means one of them is wrong).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TEXT_EXT = {".md", ".json", ".jsonl", ".txt", ".yml", ".yaml"}

# Identifiers that must never appear in a public spec repository.
# Kept as fragments so this file does not match itself.
FORBIDDEN = [
    "10.126.126.",
    "zhao" + "chu",
    "/tank/",
    "gzs-" + "nas",
    "/home/" + "ctyun",
    "/home/" + "node",
    "ShV8" + "!eJ!",
    "claw" + "box",
    "ghp" + "_",
]


def fail(msg: str) -> None:
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        )
        rels = [r for r in out.stdout.splitlines() if r.strip()]
        if rels:
            return [root / r for r in rels]
    except Exception:
        pass
    return sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)


# ----------------------------------------------------------------- 1 & 2
def check_json(files: list[Path]) -> int:
    bad = 0
    for f in files:
        if f.suffix == ".json":
            try:
                json.loads(f.read_text(encoding="utf-8"))
                ok(f"json {f.name}")
            except Exception as e:
                fail(f"json {f}: {e}")
                bad += 1
        elif f.suffix == ".jsonl":
            n = 0
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    if line.strip():
                        json.loads(line)
                        n += 1
                ok(f"jsonl {f.name} ({n} lines)")
            except Exception as e:
                fail(f"jsonl {f}: {e}")
                bad += 1
    return bad


# ----------------------------------------------------------------- 3
# Keywords the structural fallback understands. If a schema starts using a
# construct outside this set, the fallback must fail loudly instead of passing:
# a silent pass is indistinguishable from a passing check, which would make the
# CI assertion "both engines agree" meaningless.
#
# `format` is accepted but not enforced, matching JSON Schema's default (format
# is an annotation unless a format checker is supplied). The real engine used in
# CI behaves the same way, so the two stay comparable.
_FALLBACK_SUPPORTED = {
    "$schema", "$id", "title", "description", "examples", "format",
    "type", "properties", "required", "additionalProperties", "items",
    "enum", "minItems", "maxItems", "minimum", "maximum",
    "minLength", "maxLength", "pattern", "minProperties", "maxProperties",
}


def _structural(instance, schema, path="$"):
    """Validator used when jsonschema is unavailable.

    Fails closed on unrecognised schema constructs. Covers the constraints the
    reference schemas actually use: type, required, additionalProperties (both
    boolean and schema form), items, enum, string length and pattern, numeric
    bounds, and array/object cardinality.
    """
    errs = []

    unknown = sorted(set(schema) - _FALLBACK_SUPPORTED)
    if unknown:
        return [f"{path}: unsupported schema keyword(s) {unknown}; fallback refuses to pass"]

    t = schema.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    if types:
        py = {
            "object": dict, "array": list, "string": str, "boolean": bool,
            "number": (int, float), "integer": int, "null": type(None),
        }
        good = False
        for tt in types:
            p = py.get(tt)
            if p is None:
                good = True
            elif isinstance(instance, p) and not (tt in ("number", "integer") and isinstance(instance, bool)):
                good = True
        if not good:
            return [f"{path}: expected {types}"]
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: {instance} above maximum {schema['maximum']}")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for r in schema.get("required", []):
            if r not in instance:
                errs.append(f"{path}: missing required '{r}'")
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errs.append(f"{path}: fewer than minProperties {schema['minProperties']}")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errs.append(f"{path}: more than maxProperties {schema['maxProperties']}")
        addl = schema.get("additionalProperties")
        for k, v in instance.items():
            if k in props:
                errs += _structural(v, props[k], f"{path}.{k}")
            elif addl is False:
                errs.append(f"{path}: unexpected '{k}'")
            elif isinstance(addl, dict):
                # Schema-valued additionalProperties: this is how the ref table
                # is validated at all. Ignoring it would skip the protocol core.
                errs += _structural(v, addl, f"{path}.{k}")
    elif isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: more than maxItems {schema['maxItems']}")
        for i, v in enumerate(instance):
            errs += _structural(v, schema.get("items", {}), f"{path}[{i}]")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum")
    return errs


def _schema_pairs(root: Path) -> list[tuple[str, str]]:
    """Bind every example to a schema by longest name-prefix match.

    examples/note-cad.json            -> schema/note.schema.json
    examples/revision-manifest.json   -> schema/revision-manifest.schema.json
    examples/revision-manifest-2d.json-> schema/revision-manifest.schema.json

    Discovery, not a hardcoded list: an example that is added but never bound
    would otherwise report success by being skipped.
    """
    ex_dir, sch_dir = root / "examples", root / "schema"
    schemas = sorted(sch_dir.glob("*.schema.json"))
    pairs: list[tuple[str, str]] = []
    for inst in sorted(ex_dir.glob("*.json")):
        best_stem, best_sch = "", None
        for sch in schemas:
            stem = sch.name[: -len(".schema.json")]
            if inst.stem == stem or inst.stem.startswith(stem + "-"):
                if len(stem) > len(best_stem):
                    best_stem, best_sch = stem, sch
        rel_i = inst.relative_to(root).as_posix()
        if best_sch is None:
            fail(f"{rel_i}: no schema bound to this example")
            continue
        pairs.append((rel_i, best_sch.relative_to(root).as_posix()))
    return pairs


def check_schemas(root: Path, force_structural: bool = False) -> int:
    pairs = _schema_pairs(root)
    have = False
    if not force_structural:
        try:
            import jsonschema  # type: ignore

            have = True
        except Exception:
            have = False
    print(f"      schema engine: {'jsonschema' if have else 'structural fallback'}")

    bad = 0
    for inst_p, sch_p in pairs:
        inst_f, sch_f = root / inst_p, root / sch_p
        if not inst_f.is_file() or not sch_f.is_file():
            fail(f"missing {inst_p} or {sch_p}")
            bad += 1
            continue
        inst = json.loads(inst_f.read_text(encoding="utf-8"))
        sch = json.loads(sch_f.read_text(encoding="utf-8"))
        if have:
            try:
                jsonschema.validate(inst, sch)
                ok(f"schema {inst_p}")
            except Exception as e:
                fail(f"schema {inst_p}: {str(e).splitlines()[0][:160]}")
                bad += 1
        else:
            errs = _structural(inst, sch)
            if errs:
                for e in errs[:5]:
                    fail(f"schema {inst_p}: {e}")
                bad += 1
            else:
                ok(f"schema {inst_p}")

    # ledger: every line against the event schema
    led_f, led_s = root / "examples/ledger.jsonl", root / "schema/ledger-event.schema.json"
    if led_f.is_file() and led_s.is_file():
        sch = json.loads(led_s.read_text(encoding="utf-8"))
        bad_lines = 0
        for i, line in enumerate(led_f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            ev = json.loads(line)
            if have:
                try:
                    jsonschema.validate(ev, sch)
                except Exception as e:
                    fail(f"ledger line {i}: {str(e).splitlines()[0][:120]}")
                    bad_lines += 1
            else:
                errs = _structural(ev, sch)
                if errs:
                    fail(f"ledger line {i}: {errs[0]}")
                    bad_lines += 1
        bad += 1 if bad_lines else 0
        if not bad_lines:
            ok("schema examples/ledger.jsonl")
    return bad


# ----------------------------------------------------------------- 4
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)")


def check_links(files: list[Path]) -> int:
    bad = 0
    for f in files:
        if f.suffix != ".md":
            continue
        for link in LINK_RE.findall(f.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (f.parent / link.split("#")[0]).resolve()
            if not target.exists():
                fail(f"link {f.relative_to(f.parent.parent.parent) if f.parent.parent.parent else f}: {link}")
                bad += 1
    if not bad:
        ok("markdown relative links")
    return bad


# ----------------------------------------------------------------- 5
def check_forbidden(files: list[Path], root: Path) -> int:
    bad = 0
    me = Path(__file__).resolve()
    for f in files:
        if f.resolve() == me or f.suffix not in TEXT_EXT:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in FORBIDDEN:
            if pat in text:
                fail(f"forbidden identifier in {f.relative_to(root)}: {pat!r}")
                bad += 1
    if not bad:
        ok("no internal identifiers")
    return bad


# ----------------------------------------------------------------- 6
REQ_DEF = re.compile(r"^\*\*(FRP-[0-9A-Za-z.\-]+)\*\*", re.M)
REQ_CITE = re.compile(r"\b(FRP-[0-9A-Za-z.\-]+)")


def check_requirement_ids(root: Path) -> int:
    core = root / "spec" / "FRP-v0.2.md"
    if not core.is_file():
        fail("core spec missing")
        return 1
    text = core.read_text(encoding="utf-8")
    defined = set(REQ_DEF.findall(text))
    # ids may also be defined inline as "**FRP-3.1-01** An implementation ..."
    if not defined:
        fail("no requirement ids defined in core spec")
        return 1
    bad = 0
    for prof in sorted((root / "spec" / "profiles").glob("*.md")):
        pt = prof.read_text(encoding="utf-8")
        for cid in set(REQ_CITE.findall(pt)):
            if re.match(r"^FRP-[0-9]+\.[0-9]+-[0-9]+$", cid) and cid not in defined:
                fail(f"{prof.name} cites {cid} which the core does not define")
                bad += 1
    ok(f"requirement ids ({len(defined)} defined)")
    return bad


def main() -> int:
    root = Path(sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else ".").resolve()
    force_structural = "--no-jsonschema" in sys.argv
    os.chdir(root)
    files = tracked_files(root)
    print(f"== FRP validation ({len(files)} tracked files) ==")
    bad = 0
    bad += check_json(files)
    bad += check_schemas(root, force_structural)
    bad += check_links(files)
    bad += check_forbidden(files, root)
    bad += check_requirement_ids(root)
    print(f"== {'PASS' if not bad else f'{bad} FAILURE(S)'} ==")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
