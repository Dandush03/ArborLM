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


def checker_substitutions() -> tuple[tuple[str, str], ...]:
    """ADR-0029 ruling 6's own-files exclusion, for this study: the cited checker copy differs by exactly these three substitutions, each listed in the gate result with the copy's SHA-256."""
    return (
        ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})"),
        ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if not q.name.startswith(("p10i_s", "p10ir_"))]:'),
        ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if not (set(q.parts) & {"p10i_s0", "p10i_s1", "p10i_s2", "p10i_s3", "p10i_s4", "p10i_s5", "p10ir"} or q.name.startswith(("test_p10is", "test_p10ir_")))]:'),
    )


def checker_copy(original: str, root: Path) -> str:
    out = original
    for old, new in checker_substitutions():
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to extend exactly once: {old!r}")
        out = out.replace(old, new.replace("{root!r}", repr(str(root))))
    return out


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
                copy_text = checker_copy(text, base)
                with tempfile.TemporaryDirectory() as tmp:
                    p = Path(tmp) / "seed_registry_check_r3_p10is3.py"
                    p.write_text(copy_text, encoding="utf-8")
                    proc = subprocess.run([sys.executable, str(p)], cwd=base, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
                line = next((x for x in proc.stdout.splitlines() if x.startswith("RESULT:")), None)
                checker.update({"returncode": proc.returncode, "result_line": line, "copy_sha256": sha256(copy_text.encode()), "substitutions": [o for o, _ in checker_substitutions()]})
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
