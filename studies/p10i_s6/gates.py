# ruff: noqa: E501
"""P10IS6 gates (ADR-0031 sections 6.4, 11, 16): process configuration, platform of record, seeds, BASE and disabled = BASE, read equality, the synthetic-registry gate, the rehearsal gate.

Each gate returns ``{"name", "passed", "status", ...}``; ``passed`` is None where a bit-exact gate was skipped because the machine is not the platform of record. Bitwise assertions are made on macOS arm64, torch 2.8.0, one thread, one
interop thread, deterministic algorithms only. An environment error inside a gate propagates and is never recorded as a failed gate. Self-check only.
"""

import platform
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from arborlm.io import file_sha256

from . import core

PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"
ST = "P10-I-S6 ADR-0031"


def configure_process() -> None:
    """The process (supervisor and workers alike) is configured BEFORE any platform check: ``engine.configure_cpu``; if the interop threads were already used the call is tolerated only when the count is already 1."""
    from arborlm import engine

    try:
        engine.configure_cpu()
    except RuntimeError:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)
        if torch.get_num_interop_threads() != 1:
            raise core.EngineeringStop("ENGINEERING STOP — the interop thread count cannot be set to 1 in this process") from None


def platform_record() -> dict[str, Any]:
    return {"system": platform.system(), "machine": platform.machine(), "release": platform.release(), "torch": torch.__version__, "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled())}  # fmt: skip


def platform_problems(cfg: Mapping[str, Any], record: Mapping[str, Any] | None = None) -> list[str]:
    want, have = cfg["platform"], record or platform_record()
    return [f"{k}: {have[k]!r}, the platform of record has {want[k]!r}" for k in ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms") if have[k] != want[k] and not (k == "torch" and str(have[k]).split("+")[0] == want[k])]


def on_platform_of_record(cfg: Mapping[str, Any], record: Mapping[str, Any] | None = None) -> bool:
    return not platform_problems(cfg, record)


def gate(name: str, passed: bool | None, **detail: Any) -> dict[str, Any]:
    return {"name": name, "passed": passed, "status": SKIPPED if passed is None else PASSED if passed else FAILED, **detail}


def _same(a: Tensor, b: Tensor, bitwise: bool) -> bool:
    return bool(torch.equal(a, b)) if bitwise else bool(torch.allclose(a, b, atol=1e-6, rtol=0))


@torch.no_grad()
def read_equality_gate(seed: int, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """With no intervention this study's read (``studies.p10i_s3.model.memory_read``) equals ``Memory.forward`` for the flat memory, and the dense read equals ``DenseAdapter.forward``."""
    from arborlm.p4_model import DenseAdapter
    from arborlm.pilot_model import Memory
    from studies.p10i_s3.model import dense_read, memory_read

    bitwise = on_platform_of_record(cfg)
    g = torch.Generator().manual_seed(seed)
    h = torch.randn(8, 64, 32, generator=g)
    mem = Memory("flat", seed)
    ad = DenseAdapter(seed)
    ref, _ = mem(h)
    mine, _ = memory_read(mem, h, None)
    items = {"flat_no_intervention": _same(ref, mine, bitwise), "dense_no_intervention": _same(ad(h)[0], dense_read(ad, h, None), bitwise)}
    return gate("read_equality", all(items.values()), bitwise=bitwise, items=items)


def base_gate(values: Mapping[str, tuple[float, float, float]], *, bitwise: bool) -> dict[str, Any]:
    """BASE and disabled = BASE on every parent: ``values[parent] = (base, replay, disabled)``; equal bitwise on the platform of record."""
    bad = [p for p, (b, r, d) in values.items() if not ((b == r == d) if bitwise else (abs(b - r) <= 1e-6 and abs(b - d) <= 1e-6))]
    return gate("base_and_disabled", not bad, parents=len(values), failing=bad, bitwise=bitwise)


# --- seeds --------------------------------------------------------------------------------------------------------------------------------------------
def planned_seed_values(cfg: Mapping[str, Any]) -> dict[str, frozenset[int]]:
    """Every integer of this study by role (section 14 and registry revision 4). Initialisation seeds also expand to the component seeds (+ 1000 ... + 5000)."""
    s = cfg["seeds"]
    reg, oa, cal, dry = (core.Seeds(p, cfg) for p in ("registered", "oa", "calibration", "dry"))
    roles: dict[str, set[int]] = {k: set() for k in ("registered_streams", "oa_streams", "registered_p_used", "orders", "calibration_streams", "calibration_p_used", "dry", "init", "oa_init", "backbones", "init_other", "held")}
    for c in range(27):
        roles["registered_streams"].add(reg.stream(c))
        roles["oa_streams"].add(oa.stream(c))
        roles["registered_p_used"] |= {reg.p_used(c, j) for j in range(4)}
        roles["init"].add(reg.init(c))
    roles["oa_init"] = {int(x) for x in s["init_oa"]}
    roles["orders"] = {int(x) for x in s["order_registered"]} | {int(x) for x in s["order_calibration"]}
    for q in range(3):
        roles["calibration_streams"].add(cal.stream(q))
        roles["calibration_p_used"] |= {cal.p_used(q, j) for j in range(4)}
    roles["dry"] = {dry.stream(0)} | {dry.p_used(0, j) for j in range(4)}
    roles["backbones"] = {int(x) for x in s["backbone_registered"]} | {int(x) for x in s["backbone_calibration"]}
    roles["init_other"] = {int(s["init_calibration"]), int(s["init_dry"]), int(s["init_planted_toy"]), *(int(x) for x in s["init_test"])}
    roles["held"] = {int(s["held_dry_backbone"]), int(s["held_dry_order"]), int(s["held_dry_oa_stream"])}
    return {k: frozenset(v) for k, v in roles.items()}


def seed_problems(cfg: Mapping[str, Any]) -> list[str]:
    """This study's own values against its config ranges (the registry's allocation rows), pairwise disjointness of roles, counts, and no initialisation or backbone seed derived by arithmetic (+ 1000 k) from a data seed."""
    r = cfg["seed_ranges"]
    planned = planned_seed_values(cfg)
    inside = {"registered_streams": "stream", "oa_streams": "stream", "registered_p_used": "stream", "orders": "order", "calibration_streams": "calibration", "calibration_p_used": "calibration", "dry": "calibration", "held": None, "init": "init", "oa_init": "init", "backbones": "init", "init_other": "init"}
    problems: list[str] = []
    for role, rng in inside.items():
        if rng is None:
            continue
        lo, hi = r[rng]
        bad = sorted(v for v in planned[role] if not lo <= v <= hi)
        if bad:
            problems.append(f"{role}: {bad[:3]} outside the registry's range {lo}-{hi}")
    names = sorted(planned)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if planned[a] & planned[b]:
                problems.append(f"{a} and {b} share {sorted(planned[a] & planned[b])[:3]}")
    data = frozenset().union(*(planned[k] for k in ("registered_streams", "oa_streams", "registered_p_used", "orders", "calibration_streams", "calibration_p_used", "dry", "held")))
    inits = planned["init"] | planned["oa_init"] | planned["backbones"] | planned["init_other"]
    if {i + 1000 * k for i in inits for k in range(1, 11)} & data:
        problems.append("an initialisation or backbone component seed (seed + 1000 k) collides with a data seed")
    if {d + 1000 * k for d in data for k in range(1, 11)} & inits:
        problems.append("an initialisation value equals a data seed plus 1000 k: derivation by arithmetic is not allowed")
    expect = {"registered_streams": 27, "oa_streams": 27, "registered_p_used": 108, "orders": 12, "calibration_streams": 3, "calibration_p_used": 12, "init": 27, "oa_init": 3, "backbones": 12}
    problems += [f"{k}: {len(planned[k])} values, section 14 has {n}" for k, n in expect.items() if len(planned[k]) != n]
    return problems


def allocation_rows(checker_text: str, label: str) -> list[tuple[str, int, int]]:
    """The rows of ``label`` in the checker's allocation table."""
    import re

    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(rf'\("{re.escape(label)}", "([^"]*)", (\d+), (\d+)\)', checker_text)]


def other_rows_hit(checker_text: str, label: str, values: Sequence[int]) -> list[str]:
    import re

    hits = []
    for m in re.finditer(r'\("(P10-I[^"]*)", "([^"]*)", (\d+), (\d+)\)', checker_text):
        if m[1] != label:
            lo, hi = int(m[3]), int(m[4])
            h = [v for v in values if lo <= v <= hi]
            if h:
                hits.append(f"{m[1]} / {m[2]}: {h[:3]}")
    return hits


def seed_gate(cfg: Mapping[str, Any], *, root: Path, run_checker: bool = True, timeout: float = 300.0, checker_path: Path | None = None) -> dict[str, Any]:
    """Cites the revision-4 checker and addendum by SHA-256 (config), runs the checker UNEDITED with this study's own file globs (``--own``), requires ``RESULT: PASS``, records the checker's hash, the own globs and the output's result line,
    and separately checks this study's own values against the registry's allocation rows for ``allocation_label`` and against every other study's rows. Other studies' own allocations hitting their own files are the checker's known own-files
    case and do not fail; a hit on THIS study's allocation fails (the checker decides; nothing here parses its failure lines)."""
    r = cfg["seed_ranges"]
    problems = seed_problems(cfg)
    checker: dict[str, Any] = {"path": r["checker"], "expected_sha256": r["checker_sha256"], "own_globs": r["own_globs"]}
    path = checker_path or (root / r["checker"])
    add = root / r["addendum"]
    if not add.is_file() or file_sha256(add) != r["addendum_sha256"]:
        problems.append("the revision-4 addendum is missing or differs from the SHA-256 the config cites")
    if not path.is_file():
        problems.append(f"the registry checker is not at {path}")
        return gate("seeds", False, problems=problems, checker=checker)
    checker["sha256"] = file_sha256(path)
    if checker_path is None and checker["sha256"] != r["checker_sha256"]:
        problems.append("the registry checker differs from the SHA-256 the config cites")
        return gate("seeds", False, problems=problems, checker=checker)
    text = path.read_text(encoding="utf-8")
    label = str(r["allocation_label"])
    rows = allocation_rows(text, label)
    checker["own_allocation_rows"] = len(rows)
    if not rows:
        problems.append(f"the checker has no allocation row for {label}")
    planned = planned_seed_values(cfg)
    every = sorted(set().union(*planned.values()))
    outside = [v for v in every if not any(lo <= v <= hi for _, lo, hi in rows)] if rows else []
    if outside:
        problems.append(f"values outside every {label} allocation row: {outside[:5]}")
    others = other_rows_hit(text, label, every)
    if others:
        problems.append(f"values inside another study's allocation row: {others[:3]}")
    if run_checker:
        proc = subprocess.run([sys.executable, str(path), "--own", f"{label}={r['own_globs']}", "--root", str(root)], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
        line = next((x for x in proc.stdout.splitlines() if x.startswith("RESULT:")), None)
        checker.update({"returncode": proc.returncode, "result_line": line})
        if proc.returncode != 0 or line != "RESULT: PASS":
            problems.append(f"the checker did not print RESULT: PASS ({proc.returncode}, {line})")
    return gate("seeds", not problems, problems=problems, checker=checker, roles={k: len(v) for k, v in planned.items()})


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


def file_hash(path: Path) -> str:
    return file_sha256(path)
