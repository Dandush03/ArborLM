# ruff: noqa: E501
"""P10IS0 seed gate (ADR-0023 section 4.2; registry revision 3; ADR-0029 ruling 6's own-files exclusion).

Gate: (1) every planned value lies in the range the registry allocates to its role (config ``[seed_ranges]``); (2) the planned roles are pairwise disjoint and disjoint from the declared re-use (the identity gate's P10-S0 rehearsal set and
initialisation 2092, with their derived seeds), which is listed as re-used and not as new; (3) the config's ranges lie inside the registry checker's ALLOC rows for ADR-0023; (4) the cited checker (its SHA-256 in the config) is run as a copy
with the substitutions below (this study's and P10-I-R's own config and files excluded: both are P10-I allocations that would otherwise hit their own inventory), the copy's hash in the result.

The twelve spare values the ADR assigns to a repeated Stage R (draw sets 309401 to 309901 and initialisation 330061 to 330066) are listed by name in the result (``named_spare_values``) and checked to lie in the registry's spare and
initialisation rows. R2 images (init + 1000 k, k = 1..10) of every initialisation value are disjoint from every planned value.
"""

import hashlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256

from . import core

R2_OFFSETS = tuple(1000 * k for k in range(1, 11))
CHECKER_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})\nNAMED_SPARE_VALUES = {named!r}  # the twelve spare values of a repeated Stage R, named explicitly (ADR-0023 section 4.2)"),
    ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if q.name not in ("p10is0_overload.toml", "p10ir_routing.toml")]:'),
    ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if not any(x in q.name or x in q.parts for x in ("p10is0", "p10ir"))]:'),
)
ROW_PREFIX = {"registered": "data:", "auxiliary": "auxiliary", "calibration": "calibration", "rehearsal": "rehearsal draw", "check": "pipeline-check", "spare": "spare", "init": "init sub-row", "test": "test"}


def named_spare_values(cfg: Mapping[str, Any] | None = None) -> dict[str, list[int]]:
    """The twelve spare values of a repeated Stage R (repeats 1 to 3, both calibration draws): six draw-set bases and six initialisation seeds."""
    c = cfg or core.load_config()
    sets = [core.calibration_set(d, k, c).base for k in (1, 2, 3) for d in (1, 2)]
    inits = [core.init_seed("CAL", "A5-D", d, k, c) for k in (1, 2, 3) for d in (1, 2)]
    return {"draw_sets": sorted(sets), "initialisation": sorted(inits)}


def planned_seed_values(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    c = cfg or core.load_config()
    registered = frozenset().union(*(core.registered_set(d, c).values(c) for d in range(1, 11)), *(core.reserve_set(k, c).values(c) for k in range(1, 5)))
    calibration = frozenset().union(*(core.calibration_set(d, k, c).values(c) for k in range(0, 4) for d in (1, 2)))
    inits = {core.init_seed("REG", a, d, 0, c) for a in core.ARMS for d in (1, 2)} | {core.init_seed("CAL", "A5-D", d, k, c) for k in range(0, 4) for d in (1, 2)}
    inits |= {core.init_seed("REH", "A0", 1, 0, c), core.init_seed("CHK", "A0", 1, 0, c), *(int(x) for x in c["seeds"]["test_init"])}
    return {
        "registered_and_reserve_sets": registered, "calibration_sets": calibration, "rehearsal_set": core.rehearsal_set(c).values(c), "check_set": core.check_set(c).values(c), "initialisation": frozenset(inits),
        "derived_initialisation": frozenset(i + o for i in inits for o in R2_OFFSETS), "test_sets": frozenset().union(*(core.test_set(k, c).values(c) for k in range(9))),
    }  # fmt: skip


def declared_reuse(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    """The identity gate's re-use of P10-S0's rehearsal set and initialisation 2092 (registry section 4.6): read-only; it enters no class and no rehearsal measurement."""
    from studies.p10s0 import core as s0core

    c = cfg or core.load_config()
    init = int(c["seeds"]["identity_gate_init"])
    if int(c["seeds"]["identity_gate_data_base"]) != s0core.REHEARSAL_BASE or init != s0core.REHEARSAL_INIT:
        raise ValueError("the identity gate's declared re-use differs from P10-S0's rehearsal set")
    return {"p10s0_rehearsal_set_and_init": frozenset({*s0core.REHEARSAL_SET.values(), init, *(init + o for o in R2_OFFSETS)})}


def allocation_rows(checker_text: str) -> list[tuple[str, int, int]]:
    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(r'\("P10-I-S0 ADR-0023", "([^"]*)", (\d+), (\d+)\)', checker_text)]


def allocation_problems(cfg: Mapping[str, Any], rows: Sequence[tuple[str, int, int]]) -> list[str]:
    problems = []
    for key, prefix in ROW_PREFIX.items():
        lo, hi = (int(x) for x in cfg["seed_ranges"][key])
        if not any(r[0].startswith(prefix) and r[1] <= lo and hi <= r[2] for r in rows):
            problems.append(f"the config's {key} range {lo}-{hi} is not inside a registry allocation row '{prefix}...' of ADR-0023")
    return problems


def checker_copy(original: str, root: Path, named: Mapping[str, Sequence[int]] | None = None) -> str:
    named_values = {k: list(v) for k, v in (named or named_spare_values()).items()}
    out = original
    for old, new in CHECKER_SUBSTITUTIONS:
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to extend exactly once: {old!r}")
        out = out.replace(old, new.format(root=str(root), named=named_values))
    return out


def run_checker_copy(path: Path, root: Path, timeout: float) -> dict[str, Any]:
    text = checker_copy(path.read_text(encoding="utf-8"), root)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "seed_registry_check_r3_p10is0.py"
        copy.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(copy)], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    result = next((line for line in proc.stdout.splitlines() if line.startswith("RESULT:")), None)
    return {"returncode": proc.returncode, "result_line": result, "copy_sha256": hashlib.sha256(text.encode()).hexdigest(), "substitutions": [{"replaces": old, "with": new} for old, new in CHECKER_SUBSTITUTIONS], "named_values_in_copy": named_spare_values(), "own_files_excluded": ["p10is0", "p10ir"]}


def seed_gate(cfg: Mapping[str, Any] | None = None, *, root: Path | None = None, run_checker: bool = True, timeout: float = 600.0) -> dict[str, Any]:
    c = cfg or core.load_config()
    base = root or core.repo_root()
    r = c["seed_ranges"]
    planned = planned_seed_values(c)
    allowed = {
        "registered_and_reserve_sets": [r["registered"]], "calibration_sets": [r["calibration"], r["spare"]], "rehearsal_set": [r["rehearsal"]], "check_set": [r["check"]], "initialisation": [r["init"]],
        "derived_initialisation": [], "test_sets": [r["test"]],
    }  # fmt: skip
    problems: list[str] = []
    for role, values in planned.items():
        if role == "derived_initialisation":
            continue
        out = sorted(v for v in values if not any(lo <= v <= hi for lo, hi in allowed[role]))
        if out:
            problems.append(f"{role}: values outside the registry's range: {out[:5]}")
    names = sorted(planned)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = planned[a] & planned[b]
            if common:
                problems.append(f"{a} and {b} share {sorted(common)[:5]}")
    flat = frozenset().union(*planned.values())
    for name, vals in declared_reuse(c).items():
        common = flat & vals
        if common:
            problems.append(f"a planned value is also a declared re-use ({name}): {sorted(common)[:5]}")
    named = named_spare_values(c)
    spare, init_row = r["spare"], r["init"]
    if not all(spare[0] <= v <= spare[1] for v in named["draw_sets"]) or not all(init_row[0] <= v <= init_row[1] for v in named["initialisation"]):
        problems.append("a named spare value lies outside the registry's spare or initialisation row")
    if len(named["draw_sets"]) + len(named["initialisation"]) != 12:
        problems.append("the repeated Stage R does not have exactly twelve named spare values")
    checker_path = base / r["checker"]
    checker: dict[str, Any] = {"path": r["checker"], "expected_sha256": r["checker_sha256"]}
    if checker_path.is_file():
        checker["sha256"] = file_sha256(checker_path)
        if checker["sha256"] != r["checker_sha256"]:
            problems.append("the registry checker file differs from the SHA-256 the ADR cites")
        else:
            rows = allocation_rows(checker_path.read_text(encoding="utf-8"))
            checker["allocation_rows"] = len(rows)
            problems += allocation_problems(c, rows) if rows else ["no ADR-0023 rows in the checker's ALLOC table"]
            if run_checker:
                checker.update(run_checker_copy(checker_path, base, timeout))
                if checker["returncode"] != 0 or checker["result_line"] != "RESULT: PASS":
                    problems.append(f"the extended registry checker did not print RESULT: PASS (returncode {checker['returncode']}, {checker['result_line']})")
    else:
        problems.append(f"the registry checker is not at {r['checker']}")
    return {"passed": not problems, "problems": problems, "roles": {k: len(v) for k, v in planned.items()}, "declared_reuse_not_new": {k: len(v) for k, v in declared_reuse(c).items()}, "named_spare_values": named, "checker": checker}
