# ruff: noqa: E501
"""P10IS3 gates (ADR-0026 sections 8, 10, 11). Each gate returns ``{"name", "passed", "status", ...}``; ``passed`` is None where a bit-exact gate was skipped because the machine is not the platform of record.
Bitwise assertions are made on macOS arm64, torch 2.8.0, one thread, one interop thread, deterministic algorithms only; elsewhere the same checks use a 1e-6 tolerance. An environment error inside a gate propagates
and is never recorded as a failed gate.
"""

import copy
import platform
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F

from arborlm.io import file_sha256, sha256
from arborlm.pilot_model import EPS, TEMP, TOP, Memory, stable_top, tree_candidates

from . import core, model

PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"


def configure_process() -> None:
    """B1: the process (supervisor and workers alike) is configured BEFORE any platform check: one intra-op thread, one interop thread, deterministic algorithms (``engine.configure_cpu``). The interop thread count can be
    set only before parallel work has started; if the process already ran parallel work the call is tolerated only when the count is already 1, otherwise it is an engineering stop."""
    from arborlm import engine

    try:
        engine.configure_cpu()
    except RuntimeError:  # set_num_interop_threads after parallel work started
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)
        if torch.get_num_interop_threads() != 1:
            raise core.EngineeringStop("ENGINEERING STOP — the interop thread count cannot be set to 1 in this process") from None


def platform_record() -> dict[str, Any]:
    return {"system": platform.system(), "machine": platform.machine(), "release": platform.release(), "platform": platform.platform(), "torch": torch.__version__, "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled())}  # fmt: skip


def platform_problems(cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> list[str]:
    want = (cfg or core.load_config())["platform"]
    have = record or platform_record()
    problems = []
    for k in ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"):
        if have[k] != want[k] and not (k == "torch" and str(have[k]).split("+")[0] == want[k]):
            problems.append(f"{k}: {have[k]!r}, the platform of record has {want[k]!r}")
    return problems


def on_platform_of_record(cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> bool:
    return not platform_problems(cfg, record)


def gate(name: str, passed: bool | None, **detail: Any) -> dict[str, Any]:
    return {"name": name, "passed": passed, "status": SKIPPED if passed is None else PASSED if passed else FAILED, **detail}


def _same(a: Tensor, b: Tensor, bitwise: bool, tol: float = 1e-6) -> bool:
    return bool(torch.equal(a, b)) if bitwise else bool(torch.allclose(a, b, atol=tol, rtol=0))


# --- read equality (section 11) -------------------------------------------------------------------------------------------
@torch.no_grad()
def read_equality_gate(seed: int, *, bitwise: bool | None = None, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """With no intervention the study's read equals ``Memory.forward`` for both variants; the exhaustive read equals ``tree_candidates(visit=16)`` (the path P6 used) computed here independently."""
    bitwise = on_platform_of_record(cfg) if bitwise is None else bitwise
    g = torch.Generator().manual_seed(seed)
    results: dict[str, bool] = {}
    for variant in ("learned_tree", "flat"):
        mem = Memory(variant, seed)
        h = torch.randn(8, 64, 32, generator=g)
        ref, _ = mem(h)
        mine, _ = model.memory_read(mem, h, None)
        results[f"{variant}_no_intervention"] = _same(ref, mine, bitwise)
        if variant == "learned_tree":
            q = F.normalize(F.linear(h, mem.wq), dim=-1, eps=EPS).reshape(-1, 16)
            routes = (q @ F.normalize(mem.router, dim=-1, eps=EPS).T) / TEMP
            w, sel, _, _ = tree_candidates(q, mem.keys, routes, visit=16)
            comb = (w.softmax(-1)[..., None] * mem.values[sel]).sum(-2)
            expect = h + mem.gate.sigmoid() * F.linear(comb.reshape(h.shape), mem.wo)
            got, _ = model.memory_read(mem, h, model.Ctl("exhaustive", visit=16))
            results["exhaustive_equals_tree_candidates_visit16"] = _same(expect, got, bitwise)
            flat = (q @ F.normalize(mem.keys, dim=-1, eps=EPS).T) / TEMP + routes.log_softmax(-1).repeat_interleave(256, dim=-1)
            _, ids = stable_top(flat, TOP)
            results["exhaustive_selection_equals_flat_scan"] = bool(torch.equal(sel, ids))
    return gate("read_equality", all(results.values()), bitwise=bitwise, items=results)


# --- prefix identity (section 11) -----------------------------------------------------------------------------------------
def prefix_identity_gate(arm: str, backbone: Any, rows: Tensor, *, init_seed: int, stream_seed: int, fresh: bool, rate: float, short: int, long: int, root: Path, bitwise: bool | None = None, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """On the platform of record, a separate ``short``-update run is bitwise equal to the ``short`` checkpoint of the ``long``-update run (the registered gate: 512 and 16,384, one calibration cell, each arm and regime)."""
    bitwise = on_platform_of_record(cfg) if bitwise is None else bitwise
    ident = {"gate": "prefix_identity", "arm": arm}
    a = model.build_model(copy.deepcopy(backbone), arm, init_seed)
    ra = model.train_run(a, model.Stream(rows, stream_seed, fresh=fresh), rate, root / "long", [short, long], long, ident)
    b = model.build_model(copy.deepcopy(backbone), arm, init_seed)
    rb = model.train_run(b, model.Stream(rows, stream_seed, fresh=fresh), rate, root / "short", [short], short, ident)
    if ra["status"] != "ok" or rb["status"] != "ok":
        return gate("prefix_identity", False, arm=arm, reason="a run failed", long=ra["status"], short=rb["status"])
    s1 = torch.load(model.snapshot_dir(root / "long", short) / "state.pt", weights_only=True)
    s2 = torch.load(model.snapshot_dir(root / "short", short) / "state.pt", weights_only=True)
    same = all(_same(s1["addition"][k], s2["addition"][k], bitwise) for k in s1["addition"]) and ra["snapshots"][str(short)]["sha256"] is not None
    opt_same = bitwise is False or (ra["snapshots"][str(short)]["sha256"] == rb["snapshots"][str(short)]["sha256"])
    return gate("prefix_identity", bool(same and opt_same), arm=arm, bitwise=bitwise, short=short, long=long)


def base_gate(values: Mapping[str, tuple[float, float, float]], *, bitwise: bool) -> dict[str, Any]:
    """BASE and disabled = BASE on every parent: ``values[parent] = (base, replay, disabled)``; equal bitwise on the platform of record, within 1e-6 elsewhere."""
    bad = [p for p, (b, r, d) in values.items() if not ((b == r == d) if bitwise else (abs(b - r) <= 1e-6 and abs(b - d) <= 1e-6))]
    return gate("base_and_disabled", not bad, parents=len(values), failing=bad, bitwise=bitwise)


# --- seeds (gate 6) ------------------------------------------------------------------------------------------------------
def planned_seed_values(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    """Every integer by role (registered, calibration, dry). Initialisation seeds also expand to the five component seeds (seed + 1000 ... + 5000)."""
    c = cfg or core.load_config()
    roles: dict[str, set[int]] = {k: set() for k in ("registered_streams", "registered_p_all", "registered_joint", "registered_p_used", "registered_x", "calibration", "dry", "init", "init_components", "test_init")}
    reg, cal, dry = core.Seeds("registered", c), core.Seeds("calibration", c), core.Seeds("dry", c)
    for ci in range(27):
        roles["registered_streams"] |= {reg.stream(ci, g) for g in range(3)}
        roles["registered_p_all"].add(reg.p_all(ci))
        roles["registered_joint"].add(reg.joint(ci))
        roles["registered_p_used"] |= {reg.p_used(ci, j) for j in range(4)}
        roles["registered_x"] |= {reg.x(ci, j) for j in range(4)}
    for ci in range(3):
        roles["calibration"] |= {cal.stream(ci, g) for g in range(3)} | {cal.p_all(ci), cal.joint(ci)} | {cal.p_used(ci, j) for j in range(4)} | {cal.x(ci, j) for j in range(4)}
    roles["dry"] |= {dry.stream(0, g) for g in range(3)} | {dry.p_all(0), dry.joint(0)} | {dry.p_used(0, j) for j in range(4)} | {dry.x(0, j) for j in range(4)}
    inits = {int(x) for x in c["seeds"]["init_registered"]} | {int(c["seeds"]["init_calibration"]), int(c["seeds"]["init_dry"])}
    roles["init"] = inits
    roles["init_components"] = {i + k for i in inits | {int(x) for x in c["seeds"]["init_test"]} for k in (1000, 2000, 3000, 4000, 5000)}
    roles["test_init"] = {int(x) for x in c["seeds"]["init_test"]}
    return {k: frozenset(v) for k, v in roles.items()}


def seed_problems(cfg: Mapping[str, Any] | None = None) -> list[str]:
    """The study's own values against the registry's allocation rows (config ``[seed_ranges]``), pairwise disjointness of roles, and no initialisation seed derived by arithmetic from a data seed."""
    c = cfg or core.load_config()
    r = c["seed_ranges"]
    planned = planned_seed_values(c)
    inside = {"registered_streams": "stream", "registered_p_all": "stream", "registered_joint": "stream", "registered_p_used": "stream", "registered_x": "stream", "calibration": "calibration", "dry": "dry", "init": "init", "test_init": "init"}
    problems = []
    for role, rng in inside.items():
        lo, hi = r[rng]
        bad = sorted(v for v in planned[role] if not lo <= v <= hi)
        if bad:
            problems.append(f"{role}: {bad[:3]} outside the registry's range {lo}-{hi}")
    names = sorted(planned)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if planned[a] & planned[b]:
                problems.append(f"{a} and {b} share {sorted(planned[a] & planned[b])[:3]}")
    data = frozenset().union(*(planned[k] for k in ("registered_streams", "registered_p_all", "registered_joint", "registered_p_used", "registered_x", "calibration", "dry")))
    if planned["init_components"] & data:
        problems.append("an initialisation component seed (seed + 1000 .. 5000) collides with a stream or permutation seed")
    expect = {"registered_streams": 81, "registered_p_all": 27, "registered_joint": 27, "registered_p_used": 108, "registered_x": 108}
    problems += [f"{k}: {len(planned[k])} values, the registry has {n}" for k, n in expect.items() if len(planned[k]) != n]
    return problems


OWN_FILES_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    # Only this study's own files and P10-I-R's (the checker's known self-collision) leave the scan; no other study's code is dropped.
    ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if not q.name.startswith(("p10i_s3_", "p10ir_"))]:'),
    ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if not (set(q.parts) & {"p10i_s3", "p10ir"} or q.name.startswith(("test_p10is3_", "test_p10ir_")))]:'),
)
ROOT_SUBSTITUTION = ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})")
CHECKER_FILE = core.FREEZE_DIR / "seed_registry_check.py"
SEED_PLAN_FILE = core.FREEZE_DIR / "seed_plan.json"
NOTES = {
    "clip_grad_norm": "torch's clip_grad_norm_ raises a RuntimeError, not a ValueError, with error_if_nonfinite=True. This study calls it with error_if_nonfinite=False and tests the norm in its own code (model.train_step raises FailedCell); the arithmetic is the same when the norm is finite.",
    "bitwise_equality_test": "tests/test_p10is3_model.py::test_train_step_matches_p4_train_step_bitwise (M-TREE and D-ADAPT against p4_model.train_step)",
}


def checker_substitutions(with_root: bool = False) -> tuple[tuple[str, str], ...]:
    """ADR-0029 ruling 6's own-files exclusion, for this study: the cited checker differs from the frozen copy by exactly these two substitutions (the copy lives in ``freeze/`` three directories below the root, as the cited
    file does, so ``ROOT`` needs none). A temporary copy used before the frozen file exists adds the ``ROOT`` substitution. The substitutions and the copy's SHA-256 are recorded in the gate result."""
    return (ROOT_SUBSTITUTION, *OWN_FILES_SUBSTITUTIONS) if with_root else OWN_FILES_SUBSTITUTIONS


def checker_copy(original: str, root: Path | None = None) -> str:
    out = original
    for old, new in checker_substitutions(root is not None):
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to extend exactly once: {old!r}")
        out = out.replace(old, new.replace("{root!r}", repr(str(root))) if root is not None else new)
    return out


def seed_plan_content(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"study": core.STUDY, "roles": {k: sorted(v) for k, v in sorted(planned_seed_values(cfg).items())}, "note": "every planned seed by role; the registry's allocation rows are in the checker copy"}


def write_seed_files(repo: Path, cfg: Mapping[str, Any]) -> dict[str, str]:
    """Written at candidate-plan time as real files (frozen inputs, hashed with the rest of ``studies/p10i_s3``): the seed plan and the extended checker copy. Refuses to overwrite."""
    import json

    src = repo / cfg["seed_ranges"]["checker"]
    if file_sha256(src) != cfg["seed_ranges"]["checker_sha256"]:
        raise ValueError("the registry checker differs from the SHA-256 the config cites")
    out = {}
    for rel, payload in ((SEED_PLAN_FILE, json.dumps(seed_plan_content(cfg), sort_keys=True, indent=1) + "\n"), (CHECKER_FILE, checker_copy(src.read_text(encoding="utf-8")))):
        path = repo / rel
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        out[str(rel)] = file_sha256(path)
    return out


def seed_files_problems(repo: Path, cfg: Mapping[str, Any]) -> list[str]:
    """The files on disk equal a regeneration from the cited checker and the config (the freeze refuses a difference)."""
    import json

    problems = []
    for rel, want in ((SEED_PLAN_FILE, json.dumps(seed_plan_content(cfg), sort_keys=True, indent=1) + "\n"), (CHECKER_FILE, checker_copy((repo / cfg["seed_ranges"]["checker"]).read_text(encoding="utf-8")))):
        p = repo / rel
        if not p.is_file() or p.read_text(encoding="utf-8") != want:
            problems.append(f"{rel} is missing or differs from a regeneration")
    return problems


def allocation_rows(checker_text: str) -> list[tuple[str, int, int]]:
    import re

    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(r'\("P10-I-S3 ADR-0026", "([^"]*)", (\d+), (\d+)\)', checker_text)]


def seed_gate(cfg: Mapping[str, Any] | None = None, *, root: Path | None = None, run_checker: bool = True, timeout: float = 300.0) -> dict[str, Any]:
    c = cfg or core.load_config()
    base = root or core.repo_root()
    problems = seed_problems(c)
    r = c["seed_ranges"]
    path = base / r["checker"]
    checker: dict[str, Any] = {"path": r["checker"], "expected_sha256": r["checker_sha256"]}
    if not path.is_file():
        problems.append(f"the registry checker is not at {r['checker']}")
    else:
        checker["sha256"] = file_sha256(path)
        if checker["sha256"] != r["checker_sha256"]:
            problems.append("the registry checker differs from the SHA-256 the config cites")
        else:
            text = path.read_text(encoding="utf-8")
            rows = allocation_rows(text)
            checker["allocation_rows"] = len(rows)
            want = {"stream": "registered streams", "calibration": "calibration streams", "dry": "dry-rehearsal", "init": "init sub-row", "test": "test"}
            for key, prefix in want.items():
                lo, hi = r[key]
                if not any(x[0].startswith(prefix) and x[1] <= lo and hi <= x[2] for x in rows):
                    problems.append(f"the config's {key} range {lo}-{hi} is not inside a registry allocation row '{prefix}...' of ADR-0026")
            if run_checker:
                frozen = base / CHECKER_FILE
                if frozen.is_file():  # the frozen file written at candidate-plan time, run as it is
                    problems += seed_files_problems(base, c)
                    copy_text = frozen.read_text(encoding="utf-8")
                    proc = subprocess.run([sys.executable, str(frozen)], cwd=base, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
                    checker["source"] = "frozen file " + str(CHECKER_FILE)
                    subs = checker_substitutions(False)
                else:  # before the candidate plan: a temporary copy (the gate result says so)
                    copy_text = checker_copy(text, base)
                    with tempfile.TemporaryDirectory() as tmp:
                        p = Path(tmp) / "seed_registry_check_r3_p10is3.py"
                        p.write_text(copy_text, encoding="utf-8")
                        proc = subprocess.run([sys.executable, str(p)], cwd=base, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
                    checker["source"] = "temporary copy (no frozen file yet)"
                    subs = checker_substitutions(True)
                line = next((x for x in proc.stdout.splitlines() if x.startswith("RESULT:")), None)
                checker.update({"returncode": proc.returncode, "result_line": line, "copy_sha256": sha256(copy_text.encode()), "substitutions": [o for o, _ in subs]})
                if proc.returncode != 0 or line != "RESULT: PASS":
                    problems.append(f"the extended registry checker did not print RESULT: PASS ({proc.returncode}, {line})")
    return gate("seeds", not problems, problems=problems, checker=checker, roles={k: len(v) for k, v in planned_seed_values(c).items()})


def rehearsal_gate(record: Mapping[str, Any] | None, required: Sequence[str], *, plan_file_sha256: str | None = None) -> dict[str, Any]:
    """The freeze's reading of the counting rehearsal's record: every required stage COMPLETE, the caps not provisional, and (given) the candidate plan file's SHA-256 equal to the committed file's."""
    if record is None:
        return {"passed": False, "reason": "no rehearsal record"}
    done = {s for s, v in (record.get("stages") or {}).items() if v.get("status") == "COMPLETE"}
    missing = [s for s in required if s not in done]
    ok = not missing and record.get("caps_provisional") is False
    out: dict[str, Any] = {"missing": missing, "caps_provisional": record.get("caps_provisional")}
    if plan_file_sha256 is not None:
        same = (record.get("candidate") or {}).get("plan_file_sha256") == plan_file_sha256
        out["candidate_plan_rehearsed_with_this_file"] = same
        ok = ok and same
    out["passed"] = ok
    return out


# --- the synthetic-registry gate (public whitelist, section 5.3) ----------------------------------------------------------------------------
def synthetic_registry_gate(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The analysis on a synthetic registry whose labels are worked out by hand (the same cases the unit tests hold, a representative subset): pass or fail, and which case failed. A pure check: no model, no data."""
    from . import analysis, synthetic

    c = cfg or core.load_config()
    S = synthetic.Spec
    tree, dense = core.TREE, core.DENSE

    def run(t: Any, d: Any = None) -> dict[str, Any]:
        reg = synthetic.registry(c, {(tree, core.FRESH): t, (dense, core.FRESH): d or S(gain=0.03)})
        return analysis.analyse(reg, synthetic.rate_table(c), c)["regimes"][core.FRESH]

    cases: dict[str, bool] = {}
    cases["DEPENDENT"] = run(S(gain=0.02, p=0.015, xm=0.012))["line1"]["label"] == "DEPENDENT"
    cases["CAPACITY WITHOUT DEMONSTRATED DEPENDENCE (D2)"] = run(S(gain=0.02, p=0.004, xm=0.012))["line1"]["detail"]["failing"] == ["D2"]
    cases["NO CAPACITY"] = run(S(gain=0.004))["line1"]["label"] == "NO CAPACITY"
    cases["failed cell is never averaged away"] = run(S(gain=0.2, p=0.15, xm=0.15, failed=[4]))["line1"]["label"] == "NO CAPACITY"
    cases["COMPETITIVE"] = run(S(gain=0.02), S(gain=0.022))["line2_tree"]["base_label"] == "COMPETITIVE"
    cases["NOT COMPETITIVE (K2)"] = run(S(gain=0.018), S(gain=0.022))["line2_tree"]["base_label"] == "NOT COMPETITIVE"
    cases["MEMORY AHEAD"] = run(S(gain=0.03), S(gain=0.02))["line2_tree"]["base_label"] == "MEMORY AHEAD"
    cases["dense adds nothing: NOT EVALUABLE"] = run(S(gain=0.0045), S(gain=0.003))["line2_tree"]["base_label"] == "NOT EVALUABLE"
    cases["integrity: disabled != BASE"] = run(S(gain=0.02, bad_disabled=[2]))["line1"]["label"] == "NOT EVALUABLE"
    # B3: COMPETITIVE before the tags with D-ADAPT's U* rate at the edge is INCONCLUSIVE, and an INCONCLUSIVE label is never positive
    reg = synthetic.registry(c, {(tree, core.FRESH): S(gain=0.02), (dense, core.FRESH): S(gain=0.022)})
    edge = analysis.analyse(reg, synthetic.rate_table(c, edge=[(dense, core.FRESH)]), c)
    cases["INCONCLUSIVE (DENSE RATE AT EDGE) is never positive"] = edge["line2_tree"]["label"] == "INCONCLUSIVE (DENSE RATE AT EDGE)" and edge["registered_positive"]["line2"] is False
    try:
        reg = synthetic.registry(c, {})
        reg[core.run_key(tree, core.FRESH, 0.003, 0)] = {"status": "item_error"}
        analysis.analyse(reg, synthetic.rate_table(c), c)
        cases["item error refuses"] = False
    except core.EngineeringStop:
        cases["item error refuses"] = True
    return gate("synthetic_registry", all(cases.values()), cases=cases)
