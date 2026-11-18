# ruff: noqa: E501
"""P10IS1 gates (ADR-0024 sections 6, 14, 16, 18): the platform of record, the gate result shape, gate G9 (seeds: the registry's checker, run as an extended copy, plus this study's own values checked separately against the
registry's allocation rows), the rehearsal gate and the identity gates. Bit-exact gates are made on the platform of record only (macOS arm64, torch 2.8.0, one thread, one interop thread, deterministic algorithms) and
are recorded as skipped elsewhere. A gate result is ``{"scope", "passed", "status", ...detail}``; ``passed`` None means skipped."""

import platform
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, sha256
from studies.p10s1 import core as s1core

from . import core

PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"


def platform_record() -> dict[str, Any]:
    return {
        "system": platform.system(), "machine": platform.machine(), "release": platform.release(), "platform": platform.platform(), "torch": torch.__version__, "torch_num_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }  # fmt: skip


def platform_problems(cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> list[str]:
    """What differs from the platform of record: macOS arm64, torch 2.8.0, one thread, one interop thread, deterministic algorithms on."""
    want = core.cfg_of(cfg)["platform"]
    have = record or platform_record()
    out = []
    for k in ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"):
        if have[k] != want[k] and not (k == "torch" and str(have[k]).split("+")[0] == want[k]):
            out.append(f"{k}: {have[k]!r}, the platform of record has {want[k]!r}")
    return out


def on_platform_of_record(cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> bool:
    return not platform_problems(cfg, record)


def gate(scope: str, passed: bool | None, **detail: Any) -> dict[str, Any]:
    return {"scope": scope, "passed": passed, "status": SKIPPED if passed is None else PASSED if passed else FAILED, **detail}


def configure_worker(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The settings every worker asserts (section 16): one torch thread, one interop thread, deterministic algorithms. Returns the record of what is in force."""
    c = core.cfg_of(cfg)["platform"]
    torch.set_num_threads(int(c["torch_num_threads"]))
    try:
        torch.set_num_interop_threads(int(c["torch_interop_threads"]))
    except RuntimeError:
        pass  # already set in this process; the assertion below catches a difference
    torch.use_deterministic_algorithms(bool(c["deterministic_algorithms"]))
    rec = platform_record()
    if rec["torch_num_threads"] != int(c["torch_num_threads"]) or rec["torch_interop_threads"] != int(c["torch_interop_threads"]) or not rec["deterministic_algorithms"]:
        raise RuntimeError(f"the worker's settings differ from the platform of record: {rec}")
    return rec


# --- gate G9: seeds ---------------------------------------------------------------------------------------------------------------------------------
def planned_seed_values(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    """Every integer this study uses, by role: block M's registered sets (with their H8, mask and index seeds), the calibration sets, the rehearsal set, the nine test sets, the initialisation seeds and their derived seeds (+ 1000 k)."""
    c = core.cfg_of(cfg)
    s = c["seeds"]
    reg = frozenset(v for d in range(1, int(s["registered_draws"]) + 1) for v in core.seed_set_values(core.registered_seeds(d, c)))
    cal = frozenset(v for k in (1, 2) for v in core.seed_set_values(core.calibration_seeds(k, c)))
    reh = frozenset(core.seed_set_values(core.rehearsal_seeds(c)))
    tests = frozenset(v for k in range(9) for v in core.seed_set_values(core.test_seeds(k, c)))
    inits = frozenset([*(core.init_seed_of(d, c) for d in range(1, int(s["registered_draws"]) + 1)), *(int(x) for x in s["calibration_init"]), int(s["rehearsal_init"]), *(int(x) for x in s["test_init"])])
    derived = frozenset(i + k for i in inits for k in s1core.DERIVED_INIT_OFFSETS)
    return {"registered_sets": reg, "calibration_sets": cal, "rehearsal_set": reh, "test_sets": tests, "initialisation": inits, "derived_initialisation": derived}


def declared_reuse(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    """The declared re-use (registry section 4.6; not an allocation): the adapter identity gate reproduces P10-S1's F-OQ and T-OQ at 8K/4K on its draw 1 (set 210001) with initialisation 2101 and its derived seeds."""
    s = core.cfg_of(cfg)["seeds"]
    init = int(s["identity_gate_init"])
    draw1 = s1core.registered_draw_seeds(int(s["identity_gate_draw"]))
    return {"adapter_identity_gate_p10s1_draw_1": frozenset([init, *(init + k for k in s1core.DERIVED_INIT_OFFSETS), *s1core.set_values(draw1)])}


CHECKER_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})"),
    ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if not q.name.startswith(("p10ir", "p10is"))]:'),
    ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if not any(part.startswith(("p10ir", "p10is")) or q.name.startswith(("test_p10ir", "test_p10is")) for part in q.parts)]:'),
)  # ruling 6 of ADR-0029 as ADR-0024 section 6 applies it: the files of every P10-I study's own package, config and tests are left out of the inventory; each study's own values are checked separately


def allocation_rows(checker_text: str, name: str) -> list[tuple[str, int, int]]:
    """The rows of this study in the cited checker's ``ALLOC`` table: (role, low, high)."""
    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(r'\("' + re.escape(name) + r'", "([^"]*)", (\d+), (\d+)\)', checker_text)]


def allocation_problems(cfg: Mapping[str, Any], rows: Sequence[tuple[str, int, int]]) -> list[str]:
    """The separate check: every range the config assigns to a role of this study lies inside the registry's allocation row of that role."""
    want = {"registered": "data: block M registered draw sets", "calibration": "calibration draw sets", "rehearsal": "rehearsal draw set", "init": "init sub-row", "test": "test"}
    out = []
    for key, prefix in want.items():
        lo, hi = (int(x) for x in cfg["seed_ranges"][key])
        if not any(r[0].startswith(prefix) and r[1] <= lo and hi <= r[2] for r in rows):
            out.append(f"the config's {key} range {lo}-{hi} is not inside a registry allocation row '{prefix}...' of {cfg['seed_ranges']['checker_allocation_name']}")
    return out


def checker_copy(original: str, root: Path) -> str:
    out = original
    for old, new in CHECKER_SUBSTITUTIONS:
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to extend exactly once: {old!r}")
        out = out.replace(old, new.format(root=str(root)))
    return out


def run_checker_copy(path: Path, root: Path, timeout: float) -> dict[str, Any]:
    text = checker_copy(path.read_text(encoding="utf-8"), root)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "seed_registry_check_r3_p10is1.py"
        copy.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(copy)], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    result = next((line for line in proc.stdout.splitlines() if line.startswith("RESULT:")), None)
    return {"returncode": proc.returncode, "result_line": result, "copy_sha256": sha256(text.encode()), "substitutions": [old for old, _ in CHECKER_SUBSTITUTIONS], "missing_empty": "MISSING" not in proc.stdout or not re.search(r"MISSING:\s*\[?[^\s\]]", proc.stdout)}


def seed_gate(cfg: Mapping[str, Any] | None = None, *, root: Path | None = None, run_checker: bool = True, timeout: float = 300.0) -> dict[str, Any]:
    """G9. (1) every planned value lies in the range the registry allocates to its role; (2) the planned roles are pairwise disjoint and disjoint from the declared re-use (listed as re-used, not new); (3) the registry's
    checker (revision 3; its SHA-256 is in the config) is run as the extended copy and must print RESULT: PASS with an empty MISSING list. The copy's hash and its exclusions are recorded. Required before each freeze."""
    c = core.cfg_of(cfg)
    base = root or core.repo_root()
    ranges = c["seed_ranges"]
    planned = planned_seed_values(c)
    allowed = {"registered_sets": [ranges["registered"]], "calibration_sets": [ranges["calibration"]], "rehearsal_set": [ranges["rehearsal"]], "test_sets": [ranges["test"]], "initialisation": [ranges["init"]], "derived_initialisation": []}
    problems: list[str] = []
    for role, values in planned.items():
        if role == "derived_initialisation":
            continue
        bad = sorted(v for v in values if not any(int(lo) <= v <= int(hi) for lo, hi in allowed[role]))
        if bad:
            problems.append(f"{role}: values outside the registry's range: {bad[:5]}")
    names = sorted(planned)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = planned[a] & planned[b]
            if common:
                problems.append(f"{a} and {b} share {sorted(common)[:5]}")
    reuse = declared_reuse(c)
    flat = frozenset().union(*planned.values())
    for name, vals in reuse.items():
        common = flat & vals
        if common:
            problems.append(f"a planned value is also a declared re-use ({name}): {sorted(common)[:5]}")
    path = base / ranges["checker"]
    checker: dict[str, Any] = {"path": ranges["checker"], "expected_sha256": ranges["checker_sha256"]}
    if path.is_file():
        checker["sha256"] = file_sha256(path)
        if checker["sha256"] != ranges["checker_sha256"]:
            problems.append("the registry checker file differs from the SHA-256 the ADR cites")
        else:
            rows = allocation_rows(path.read_text(encoding="utf-8"), ranges["checker_allocation_name"])
            checker["allocation_rows"] = len(rows)
            problems += allocation_problems(c, rows) if rows else [f"no {ranges['checker_allocation_name']} rows in the checker's ALLOC table"]
            if run_checker:
                checker.update(run_checker_copy(path, base, timeout))
                if checker["returncode"] != 0 or checker["result_line"] != "RESULT: PASS" or not checker["missing_empty"]:
                    problems.append(f"the extended registry checker did not print RESULT: PASS with an empty MISSING list (returncode {checker['returncode']}, {checker['result_line']})")
    else:
        problems.append(f"the registry checker is not at {ranges['checker']}")
    return gate("seeds", not problems, name="G9", problems=problems, roles={k: len(v) for k, v in planned.items()}, declared_reuse_not_new={k: len(v) for k, v in reuse.items()}, checker=checker)


def rehearsal_gate(record: Mapping[str, Any] | None, required: Sequence[str], *, plan_file_sha256: str | None = None) -> dict[str, Any]:
    """The rehearsal gate: the counting rehearsal's record says every required stage ran end to end with status COMPLETE, on caps that are not provisional, against the candidate plan whose SHA-256 is the committed plan's."""
    if record is None:
        return gate("rehearsal", False, name="rehearsal", missing=list(required), reason="no rehearsal record")
    done = {s for s, v in (record.get("stages") or {}).items() if v.get("status") == "COMPLETE"}
    missing = [s for s in required if s not in done]
    ok = not missing and record.get("caps_provisional") is False
    detail: dict[str, Any] = {"missing": missing, "caps_provisional": record.get("caps_provisional")}
    if plan_file_sha256 is not None:
        cand = record.get("candidate") or {}
        same = cand.get("status") == "COMPLETE" and cand.get("plan_file_sha256") == plan_file_sha256
        detail["counting_rehearsal_of_this_plan_file"] = same
        ok = ok and same
    return gate("rehearsal", ok, name="rehearsal", **detail)
