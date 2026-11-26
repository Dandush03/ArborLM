# ruff: noqa: E501
"""Platform of record, gate G9 (seeds) and the rehearsal gate (ADR-0025 sections 6, 11 item 10, ruling L7).

Gate G9 runs a COPY of the registry's checker (``seed_registry_check_r3.py``, SHA-256 in the config) whose only changes exclude this study's own files: ``configs/p10is2_*.toml``, ``studies/p10is2/**`` and
the P10IS2 test files; the substitutions and the copy's SHA-256 are in the gate record. The unchanged checker reports FAIL once any P10-I study is implemented, because it counts a study's own config and tests
as collisions with its own allocation; the copy therefore still reports the OTHER implemented P10-I studies' own files (P10-I-R's seeds: its problem lines are listed, not hidden). The gate passes if the copy's
problem lines name no seed of this study. Separately it checks this study's named values against the registry's ALLOC rows.
"""

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

from . import core

ALLOC_STUDY = "P10-I-S2 ADR-0025"
CHECKER_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})"),
    ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if not q.name.startswith("p10is2_")]:'),
    ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if "p10is2" not in q.name and "p10is2" not in q.parts]:'),
    ("    for p_ in problems[:40]:", "    for p_ in problems:"),  # the checker prints only the first 40 problems: the copy prints ALL of them, so a problem naming this study cannot hide past line 40
)
OWN_MARKERS = ("P10IS2", "p10is2", "P10-I-S2 ADR-0025")


# --- platform --------------------------------------------------------------------------------------------------------------------------------
def platform_record() -> dict[str, Any]:
    return {
        "system": platform.system(), "machine": platform.machine(), "release": platform.release(), "platform": platform.platform(), "torch": torch.__version__,
        "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }  # fmt: skip


def platform_problems(cfg: Mapping[str, Any], record: Mapping[str, Any] | None = None) -> list[str]:
    """What differs from the platform of record: macOS arm64, torch 2.8.0, six threads, deterministic algorithms on (interop threads are recorded, not asserted)."""
    want = cfg["platform"]
    have = record or platform_record()
    out = []
    for key in ("system", "machine", "torch", "torch_num_threads", "deterministic_algorithms"):
        ok = have[key] == want[key] or (key == "torch" and str(have[key]).split("+")[0] == want[key])
        if not ok:
            out.append(f"{key}: {have[key]!r}, the platform of record has {want[key]!r}")
    return out


def apply_platform_settings(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """What every worker of the study sets first: six threads and deterministic algorithms (``studies/p10s2/stages.py`` sets them the same way). Returns the record to store with every score."""
    torch.set_num_threads(int(cfg["platform"]["torch_num_threads"]))
    torch.use_deterministic_algorithms(bool(cfg["platform"]["deterministic_algorithms"]))
    return platform_record()


# --- gate G9 ---------------------------------------------------------------------------------------------------------------------------------
def allocation_rows(checker_text: str) -> list[tuple[str, int, int]]:
    """The rows of this study in the checker's ALLOC table: (role, low, high)."""
    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(r'\("P10-I-S2 ADR-0025", "([^"]*)", (\d+), (\d+)\)', checker_text)]


ROW_OF_ROLE = {
    "partition side and analysis": "partition side, analysis, disjoint-draw permutations", "Part Q rehearsal partition side": "Part Q rehearsal partition side", "test": "test",
    "registered replicate sets": "data: registered replicate sets (3)", "analysis and route accuracy (inside the partition-side row)": "partition side, analysis, disjoint-draw permutations",
    "calibration": "calibration", "Part T rehearsal sets": "Part T rehearsal sets (i = 0..8)", "initialisation": "init sub-row",
}  # fmt: skip


def named_values(part: str, cfg: Mapping[str, Any]) -> dict[str, frozenset[int]]:
    """Every seed this part names, by role, each to be inside the registry row of ITS role (``ROW_OF_ROLE``)."""
    if part == "Q":
        reg = frozenset(core.partq_seeds(cfg, "registered").values())
        reh = frozenset(core.partq_seeds(cfg, "rehearsal").values())
        return {"partition side and analysis": reg, "Part Q rehearsal partition side": reh, "test": core.test_range(cfg)}
    seeds = cfg["seeds"]
    reg_data = {v for r in range(3) for v in core.partt_replicate_values(cfg, "registered", r)["data"].values()}
    cal_data = {v for i in range(4) for v in core.partt_replicate_values(cfg, "calibration", i)["data"].values()} | {int(core.partt_replicate_values(cfg, "calibration", i)["route_pieces"]) for i in range(4)}
    reh_data = set(core.partt_replicate_values(cfg, "rehearsal", 0)["data"].values()) | {int(core.partt_replicate_values(cfg, "rehearsal", 0)["route_pieces"])}
    # every derived initialisation value (base + j for every role in every mode, test mode included), never only the bases
    init = {v for mode, n in (("registered", 3), ("calibration", 4), ("rehearsal", 1), ("test", 2)) for i in range(n) for v in core.partt_replicate_values(cfg, mode, i)["init"].values()}
    return {
        "registered replicate sets": frozenset(reg_data), "analysis and route accuracy (inside the partition-side row)": frozenset({int(seeds["analysis_bootstrap"]), int(seeds["route_accuracy_pieces"]), int(seeds["g5_probe"])}),
        "calibration": frozenset(cal_data), "Part T rehearsal sets": frozenset(reh_data), "initialisation": frozenset(init), "test": core.test_range(cfg),
    }  # fmt: skip


def allocation_problems(part: str, cfg: Mapping[str, Any], rows: Sequence[tuple[str, int, int]]) -> list[str]:
    """The separate check of ruling 6: every named value lies inside the registry row of its own role. The registry's ALLOC rows of revision 3 cover 250918, 251201, 251301 and the sixteen extra
    initialisation values (the ADR notes the registry is extended with them as named values before any freeze; the rows already contain them)."""
    out: list[str] = []
    if not rows:
        return ["no P10-I-S2 rows in the checker's ALLOC table"]
    for role, vals in named_values(part, cfg).items():
        row = [(lo, hi) for name, lo, hi in rows if name == ROW_OF_ROLE[role]]
        if not row:
            out.append(f"{role}: the registry has no row named {ROW_OF_ROLE[role]!r}")
            continue
        bad = sorted(v for v in vals if not any(lo <= v <= hi for lo, hi in row))
        if bad:
            out.append(f"{role}: {len(bad)} value(s) outside the registry row {ROW_OF_ROLE[role]!r}: {bad[:5]}")
    return out


def checker_copy(original: str, root: Path) -> str:
    out = original
    for old, new in CHECKER_SUBSTITUTIONS:
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to replace exactly once: {old!r}")
        out = out.replace(old, new.format(root=str(root)))
    return out


def fail_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip().startswith("FAIL:")]


def run_checker_copy(path: Path, root: Path, timeout: float) -> dict[str, Any]:
    text = checker_copy(path.read_text(encoding="utf-8"), root)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "seed_registry_check_r3_p10is2.py"
        copy.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, "-I", str(copy)], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    fails = fail_lines(proc.stdout)
    reported = [int(m[1]) for m in re.finditer(r"problems: (\d+)", proc.stdout)]
    own = [f for f in fails if any(m in f for m in OWN_MARKERS)]
    result = next((line for line in proc.stdout.splitlines() if line.startswith("RESULT:")), None)
    return {
        "returncode": proc.returncode, "result_line": result, "copy_sha256": sha256(text.encode()), "substitutions": [old for old, _ in CHECKER_SUBSTITUTIONS], "problems": len(fails), "problems_naming_this_study": own,
        "problems_of_other_studies": len(fails) - len(own), "reported_problem_count": reported[0] if reported else None, "all_problems_printed": bool(reported) and reported[0] == len(fails),
    }  # fmt: skip


def run_checker_unedited(path: Path, root: Path, timeout: float) -> dict[str, Any]:
    """Revision 5 of the registry's checker, UNEDITED (P10-I-S2 is a built-in owner of its own files: the own-file globs are the checker's, recorded here). It must print ``RESULT: PASS``."""
    proc = subprocess.run([sys.executable, str(path), "--root", str(root)], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    result = next((line for line in proc.stdout.splitlines() if line.startswith("RESULT:")), None)
    return {"returncode": proc.returncode, "result_line": result, "problems": len(fail_lines(proc.stdout)), "fail_lines": fail_lines(proc.stdout)[:20], "unedited": True}


def seed_gate_r5(part: str, cfg: Mapping[str, Any], *, root: Path | None = None, run_checker: bool = True, timeout: float = 600.0) -> dict[str, Any]:
    """Gate G9 against registry revision 5: the checker and the addendum are cited by SHA-256, the checker runs unedited and prints ``RESULT: PASS``, and every named value (every derived value of every mode)
    lies inside the registry row of its role."""
    base = root or core.ROOT
    s = cfg["seeds"]
    problems: list[str] = []
    checker: dict[str, Any] = {"path": s["registry_checker"], "expected_sha256": s["registry_checker_sha256"], "addendum": s["registry_addendum"], "addendum_expected_sha256": s["registry_addendum_sha256"], "own_file_globs": list(s["own_file_globs"])}
    cp, ap = base / s["registry_checker"], base / s["registry_addendum"]
    rows: list[tuple[str, int, int]] = []
    for label, p, want in (("checker", cp, s["registry_checker_sha256"]), ("addendum", ap, s["registry_addendum_sha256"])):
        if not p.is_file():
            problems.append(f"the registry {label} is not at {p.relative_to(base)}")
        elif file_sha256(p) != want:
            problems.append(f"the registry {label} differs from the SHA-256 the config cites")
    if not problems:
        rows = allocation_rows(cp.read_text(encoding="utf-8"))
        checker["allocation_rows"] = len(rows)
        problems += allocation_problems(part, cfg, rows)
        if run_checker:
            checker.update(run_checker_unedited(cp, base, timeout))
            if checker["returncode"] != 0 or checker["result_line"] != "RESULT: PASS":
                problems.append(f"the registry checker ({Path(str(cp)).name}, the revision the config cites, unedited) did not print RESULT: PASS: {checker['result_line']!r}")
    named = named_values(part, cfg)
    return {"passed": not problems, "problems": problems, "roles": {k: len(v) for k, v in named.items()}, "checker": checker}


def seed_gate(part: str, cfg: Mapping[str, Any], *, root: Path | None = None, run_checker: bool = True, timeout: float = 300.0) -> dict[str, Any]:
    """Gate G9: (1) the registry checker's SHA-256 equals the config's; (2) this part's named values lie inside the registry's rows; (3) the extended copy reports no problem naming this study (problems of other
    implemented studies are counted and listed, not hidden)."""
    if "registry_addendum" in cfg["seeds"]:
        return seed_gate_r5(part, cfg, root=root, run_checker=run_checker, timeout=max(timeout, 600.0))
    base = root or core.ROOT
    s = cfg["seeds"]
    checker_path = base / s["registry_checker"]
    problems: list[str] = []
    checker: dict[str, Any] = {"path": s["registry_checker"], "expected_sha256": s["registry_checker_sha256"]}
    rows: list[tuple[str, int, int]] = []
    if not checker_path.is_file():
        problems.append(f"the registry checker is not at {s['registry_checker']}")
    else:
        checker["sha256"] = file_sha256(checker_path)
        if checker["sha256"] != s["registry_checker_sha256"]:
            problems.append("the registry checker file differs from the SHA-256 the ADR cites")
        else:
            rows = allocation_rows(checker_path.read_text(encoding="utf-8"))
            checker["allocation_rows"] = len(rows)
            problems += allocation_problems(part, cfg, rows)
            if run_checker:
                checker.update(run_checker_copy(checker_path, base, timeout))
                if not checker["all_problems_printed"]:
                    problems.append(f"the checker printed {checker['problems']} problem lines but reports {checker['reported_problem_count']}: the gate would be blind to some")
                if checker["problems_naming_this_study"]:
                    problems.append(f"the extended registry checker reports {len(checker['problems_naming_this_study'])} problem(s) naming this study")
    named = named_values(part, cfg)
    roles = {k: len(v) for k, v in named.items()}
    flat = [v for vals in named.values() for v in vals if vals is not named["test"]]
    return {"passed": not problems, "problems": problems, "roles": roles, "checker": checker, "distinct_named_values": len(set(flat))}


def rehearsal_gate(record: Mapping[str, Any] | None, required: Sequence[str], *, plan_file_sha256: str | None = None) -> dict[str, Any]:
    """The rehearsal record says every required stage ran against the rehearsal's plan with status COMPLETE; the counting rehearsal names the SHA-256 of the plan file now in ``freeze/`` and was made on caps
    that are not provisional; the measuring rehearsal is never enough."""
    if record is None:
        return {"passed": False, "missing": list(required), "reason": "no rehearsal record"}
    done = {s for s, v in (record.get("stages") or {}).items() if v.get("status") == "COMPLETE"}
    missing = [s for s in required if s not in done]
    out: dict[str, Any] = {"missing": missing}
    ok = not missing and record.get("kind_of_rehearsal") == "counting" and record.get("caps_provisional") is False
    if record.get("kind_of_rehearsal") != "counting":
        out["reason"] = "only a counting rehearsal against the candidate plan can be frozen on"
    if plan_file_sha256 is not None:
        ok_plan = record.get("plan_file_sha256") == plan_file_sha256
        out["plan_file_hash_matches"] = ok_plan
        ok = ok and ok_plan
    forced = record.get("forced") or {}
    out["forced_pause_and_resume"] = bool(forced.get("pause_resume"))
    out["forced_paused_identity_and_restore"] = bool(forced.get("paused_identity_restore"))
    ok = ok and out["forced_pause_and_resume"] and out["forced_paused_identity_and_restore"]
    out["passed"] = ok
    return out
