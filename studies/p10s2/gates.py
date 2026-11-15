# ruff: noqa: E501
"""Gates G1-G9 (ADR-0022 section 12.3). G1 (partitions) and G3 (qualification) are computed in ``data`` and ``filtering``; this module holds the gates that need a model, the frozen-bytes check, the
seed gate with its source check, and ``run_gates`` which the gates stage runs (at real size on rehearsal seeds before the freeze and again on registered seeds before training). A failed gate stops the
run; G1, G4-G9 failures are ENGINEERING-FAILURE at the label.

G2: the Stage 0 student and the stored teacher outputs score identically twice; every gap is defined on E_A and E_B (an undefined gap gives NOT_EVALUATED cells, not a stop).
G4: determinism of CPU evaluation (two scorings bit-identical; fixed batch composition; lowest-index tie rule); snapshot save and restore bit-identical; gradient reach (in M-append-frozen no first-stage
row, gate or student parameter receives a gradient; in every memory arm no student parameter does); 20 updates on CPU repeated bit-identically; the same 20 updates on MPS agree with CPU in loss within
1e-3 and in parameters within a relative norm difference of 1e-4; ``PYTORCH_ENABLE_MPS_FALLBACK`` unset; macOS, torch and MPS versions in the manifest.
G5: (a) on route "none" logits equal the frozen student's bit for bit on the general panel; (b) a new store with gate 0 on an empty base changes nothing; (c) gate isolation of appended rows.
G6: the address function and the router take the prompt only; permuting references changes no address and no route.
G7: frozen bytes: every model file equals its pinned SHA-256 (large files) or git-blob SHA-1 (small files); every other recorded file equals the SHA-256 recorded at first download or creation.
G8: student equivalence (``equivalence``). G9: seeds (``core.seed_gate``, the stricter checks and the source check below).

Revision after the audits (2026-11-15): G4 is never "not applicable" in a registered run (``require_mps``: a registered process whose world is not on MPS fails it); G7 reads the digests of a manifest
written at creation, never of one computed from the same files; G9 cannot pass on an empty record, reads each recorded use by its seed value and by the mode of the running stage (a mode label cannot
stand in), plans every replicate and the +10 code seed, lists 220901-220912 and allows 220906 in the analysis stage only. Before the freeze the gates run on rehearsal seeds with the rehearsal world
(``rehearsal.rehearsal_world``: D_cal in place of the evaluation panels, so no evaluation panel is scored and no gap on one is computed).
"""

import ast
import hashlib
import platform
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256

from . import cells, core, equivalence, evaluate, train
from .memory import MemoryArm, NullArm, SparseStore, new_lora_arm, run_student
from .tokenization import Example
from .world import World, load_arm, save_arm


# --- G2 -----------------------------------------------------------------------------------------------------------------------------------------
def g2(world: World) -> dict[str, Any]:
    a, b = cells.stage0_scores(world), cells.stage0_scores(world)
    undefined = []
    for name in world.ctx.panels:
        s0 = a["student"][name]["panel"]["mean"]
        t = a["teacher"].get(name, {}).get("mean")
        if t is None or not (t - s0 >= core.GAP_MIN):
            undefined.append(f"{name}: teacher minus Stage 0 below {core.GAP_MIN} or teacher outputs missing")
    return {"ok": core.digest(a) == core.digest(b), "scored_identically_twice": core.digest(a) == core.digest(b), "undefined_gaps": undefined}


# --- G4 -----------------------------------------------------------------------------------------------------------------------------------------
def tie_rule_check() -> dict[str, Any]:
    """The lowest-index tie rule: with identical keys every row ties and the selected rows are the lowest indices."""
    s = SparseStore(4)
    s.keys.append(torch.nn.Parameter(torch.ones(20, core.KEY_WIDTH)))
    s.values.append(torch.nn.Parameter(torch.zeros(20, 4)))
    s.gates.append(torch.nn.Parameter(torch.zeros(1)))
    s.stage_rows.append(20)
    q = torch.nn.functional.normalize(torch.ones(2, core.KEY_WIDTH), dim=-1)
    sel = s.selected_rows(q)
    return {"ok": bool((sel == torch.arange(core.TOP)).all()), "selected": sel[0].tolist()}


def environment_record() -> dict[str, Any]:
    mps = getattr(torch.backends, "mps", None)
    return {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(), "torch": torch.__version__, "mps_built": bool(mps and mps.is_built()), "mps_available": bool(mps and mps.is_available()), "mac_ver": platform.mac_ver()[0], "mps_fallback_env": bool(__import__("os").environ.get("PYTORCH_ENABLE_MPS_FALLBACK")), "threads": torch.get_num_threads()}


def g4(world: World, plan: core.SeedPlan, updates: int | None = None, *, require_mps: bool = False) -> dict[str, Any]:
    """Determinism, snapshot restoration, gradient reach, repeated updates, and the MPS comparison when training runs on MPS. ``require_mps`` (every registered process) makes the comparison mandatory:
    a world not on MPS fails G4, it is never "not applicable"."""
    ctx = world.ctx
    ctx.seed_plan = plan
    hashes_before = world.student.tensor_hashes()
    n = updates if updates is not None else core.CFG["gates"]["g4_repeat_updates"]
    res: dict[str, Any] = {"tie_rule": tie_rule_check(), "environment": environment_record()}
    ex = world.train_examples(0, "A")
    first_panel = next(iter(ctx.panels.values()))
    codes = world.codes(0)

    # (1) two scorings bit-identical
    arm = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, codes)
    s1 = evaluate.score_panel(ctx, arm, first_panel, route="oracle").to_json()
    s2 = evaluate.score_panel(ctx, arm, first_panel, route="oracle").to_json()
    res["two_scorings_bit_identical"] = s1 == s2

    # (2) snapshot save and restore bit-identical
    with tempfile.TemporaryDirectory() as d:
        save_arm(arm, Path(d), "g4")
        back = load_arm(world, 0, Path(d), "g4")
        same_hash = back.state_hash() == arm.state_hash()
        same_out = evaluate.score_panel(ctx, back, first_panel).to_json() == s1
    res["snapshot_restore_bit_identical"] = bool(same_hash and same_out)

    # (3) gradient reach
    plain = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, codes)
    reach_plain = train.gradient_reach(world.student, plain, ex[: world.batch], world.marker_index)
    maf_store = plain.store.clone()
    maf_store.append_stage(world.rows_per_stage, plan.gen(6, "stage-2 appended rows (gates)"))
    maf_store.freeze_stage(0)
    maf_store.set_trainable([1])
    maf = MemoryArm(maf_store, world.layer, codes)
    reach_maf = train.gradient_reach(world.student, maf, ex[: world.batch], world.marker_index)
    stage0_clean = all(p.grad is None and not p.requires_grad for p in maf_store.stage_parameters(0))
    lora = new_lora_arm(world.cfg, world.rank_single, plan.gen(8, "LoRA initialization (gates)"))
    reach_lora = train.gradient_reach(world.student, lora, ex[: world.batch], world.marker_index)
    res["gradient_reach"] = {
        "memory": reach_plain, "maf": reach_maf, "lora": reach_lora, "maf_first_stage_has_no_gradient": stage0_clean,
        "ok": bool(reach_plain["arm_with_gradient"] == reach_plain["arm_parameters"] and reach_maf["arm_with_gradient"] == reach_maf["arm_parameters"] and stage0_clean and reach_lora["arm_with_gradient"] == reach_lora["arm_parameters"] and reach_plain["student_with_gradient"] == 0 and reach_maf["student_with_gradient"] == 0 and reach_lora["student_with_gradient"] == 0),
    }  # fmt: skip

    # (4) the same updates on CPU repeated bit-identically
    def run() -> tuple[list[float], str]:
        a = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, codes)
        rec = train.train_arm(world.student, a, ex, n, world.batch, world.store_lr, plan.gen(2, "batch order (gates)"), world.marker_index, device=torch.device("cpu"))
        return rec.losses, a.state_hash()

    la, ha = run()
    lb, hb = run()
    res["repeated_updates_bit_identical"] = bool(la == lb and ha == hb and len(la) == n and len(lb) == n)
    res["repeated_updates"] = n

    # (5) MPS against CPU
    if world.device.type == "mps":
        a_cpu = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, codes)
        a_mps = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, codes)
        rc = train.train_arm(world.student, a_cpu, ex, n, world.batch, world.store_lr, plan.gen(2, "batch order (gates)"), world.marker_index, device=torch.device("cpu"))
        rm = train.train_arm(world.student, a_mps, ex, n, world.batch, world.store_lr, plan.gen(2, "batch order (gates)"), world.marker_index, device=torch.device("mps"))
        if rc.status != "completed" or rm.status != "completed" or len(rc.losses) != len(rm.losses):
            res["mps_agreement"] = {"ok": False, "status": f"an update failed: cpu {rc.error!r}, mps {rm.error!r}"}
        else:
            res["mps_agreement"] = train.update_agreement(rc.losses, rm.losses, a_cpu.trainable(), a_mps.trainable())
    elif require_mps:
        res["mps_agreement"] = {"ok": False, "status": f"the MPS comparison is mandatory in a registered run and this process is on {world.device.type}: no silent fallback"}
    else:
        res["mps_agreement"] = {"ok": True, "status": "not applicable: not a registered run and the training device is not MPS (dry stage and tests only)"}
    res["mps_fallback_unset"] = not res["environment"]["mps_fallback_env"]
    res["student_hashes_unchanged"] = world.student.tensor_hashes() == hashes_before
    res["ok"] = bool(res["tie_rule"]["ok"] and res["two_scorings_bit_identical"] and res["snapshot_restore_bit_identical"] and res["gradient_reach"]["ok"] and res["repeated_updates_bit_identical"] and res["mps_agreement"]["ok"] and res["mps_fallback_unset"] and res["student_hashes_unchanged"])
    return res


# --- G5 -----------------------------------------------------------------------------------------------------------------------------------------
def g5(world: World, plan: core.SeedPlan) -> dict[str, Any]:
    ctx = world.ctx
    ctx.seed_plan = plan
    arm = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, world.codes(0))
    with torch.no_grad():  # a store with non-trivial values and gate, so that "no read" is a real test of the route
        arm.store.values[0].copy_(torch.randn(arm.store.values[0].shape, generator=plan.gen(0, "store values (G5a)")))
        arm.store.gates[0].fill_(1.0)
    a = evaluate.general_by_construction(ctx, arm)
    # (b) a new store with gate 0 on an empty base changes nothing
    fresh = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, world.codes(0))
    ex = world.train_examples(0, "A")[0]
    ids = torch.tensor([list(ex.ids)])
    from .train import reads_of

    reads = [reads_of(ex, ["A"], world.marker_index)]
    with torch.no_grad():
        base = run_student(world.student, NullArm(), ids, reads)
        with_store = run_student(world.student, fresh, ids, reads)
    b = bool(torch.equal(base, with_store))
    # (c) gate isolation of appended rows: with g2 = 0 the read is unchanged when the appended values are replaced by arbitrary finite values
    st = fresh.store.clone()
    st.append_stage(world.rows_per_stage, plan.gen(6, "stage-2 appended rows (gates)"))
    q = torch.stack([world.codes(0).get("A", j) for _p, j in ex.reads] or [world.codes(0).get("A", 0)])
    with torch.no_grad():
        r_zero_vals = SparseStore.from_state(st.snapshot_state())
        r_zero_vals.values[1].zero_()
        r0 = r_zero_vals.read(q)
        r_arb = SparseStore.from_state(st.snapshot_state())
        r_arb.values[1].copy_(1e3 * torch.randn(r_arb.values[1].shape, generator=plan.gen(4, "arbitrary finite values (G5c)")))
        r1 = r_arb.read(q)
        r_init = st.read(q)
    c = bool(torch.equal(r0, r1) and torch.equal(r0, r_init))
    from .memory import row_shares

    shares = row_shares(st, q, fresh.store.rows)
    return {"a_route_none_bit_identical": a, "b_empty_base_changes_nothing": b, "c_gate_isolation": c, "append_cost_interference_not_gated": shares, "ok": bool(a["bit_identical_to_student"] and b and c)}


# --- G6 -----------------------------------------------------------------------------------------------------------------------------------------
def g6(world: World, plan: core.SeedPlan) -> dict[str, Any]:
    """The address function and the router take the prompt only: the reads and the router decision of an example do not change with its target or its references, and the generated sequences of a panel
    do not change when the references are permuted."""
    ctx = world.ctx
    ctx.seed_plan = plan
    problems: list[str] = []
    for r in range(len(world.streams)):
        for c in core.TASKS:
            for x in world.streams[r].t[c][:20]:
                p, t = world.bank.prompt(c, x.en), world.bank.train(c, x)
                if p.reads != t.reads or p.marker != t.marker or p.prompt_ids != t.prompt_ids:
                    problems.append(f"{c}: reads, marker or prompt differ between the prompt and the training example of {x.key!r}")
    arm = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (gates)")), world.layer, world.codes(0))
    with torch.no_grad():
        arm.store.values[0].copy_(torch.randn(arm.store.values[0].shape, generator=plan.gen(0, "store values (G6)")))
        arm.store.gates[0].fill_(1.0)
    panel = next(iter(ctx.panels.values()))
    a = evaluate.score_panel(ctx, arm, panel).sequences
    shuffled = evaluate.PanelData(panel.name, panel.task, panel.examples, [list(reversed(rs)) + ["permuted reference"] for rs in reversed(panel.refs)])
    b = evaluate.score_panel(ctx, arm, shuffled).sequences
    if a != b:
        problems.append("generated sequences changed when the references were permuted")
    return {"ok": not problems, "problems": problems}


# --- G7 -----------------------------------------------------------------------------------------------------------------------------------------
def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()  # noqa: S324 (git object id, not a security use)


def g7(manifest: Mapping[str, Mapping[str, str]], root: Path) -> dict[str, Any]:
    """Every listed file equals its recorded digest: ``{"path": {"algo": "sha256" | "git-sha1", "digest": ...}}``. A missing file or a different digest is a problem; the check is made at every load."""
    problems: list[str] = []
    for rel, spec in sorted(manifest.items()):
        p = root / rel
        if not p.is_file():
            problems.append(f"{rel}: missing")
            continue
        got = file_sha256(p) if spec["algo"] == "sha256" else git_blob_sha1(p)
        if got != spec["digest"]:
            problems.append(f"{rel}: {spec['algo']} {got} differs from the recorded {spec['digest']}")
    return {"ok": not problems, "problems": problems, "checked": len(manifest)}


# --- G8 -----------------------------------------------------------------------------------------------------------------------------------------
def g8(world: World, record: dict[str, Any] | None) -> dict[str, Any]:
    if record is None:
        return {"ok": False, "problems": ["the result recorded by the data-generation step is absent"]}
    created = record.get("at_creation", {})
    if not (created.get("logits", {}).get("ok") and created.get("injection", {}).get("ok")):
        return {"ok": False, "problems": ["the data-generation step's own comparison was not within tolerance"], "at_creation": created}
    v = equivalence.verify_record(world.student, record)
    return {**v, "problems": [] if v["ok"] else ["the registered path's student does not reproduce the stored reference"]}


# --- G9 -----------------------------------------------------------------------------------------------------------------------------------------
FORBIDDEN_CALLS = {"default_generator", "initial_seed", "get_rng_state", "set_rng_state"}
RNG_FUNCS = {"rand", "randn", "randint", "randperm", "normal", "multinomial", "bernoulli", "rand_like", "randn_like", "randint_like", "poisson"}
RNG_METHODS = {"normal_", "uniform_", "random_", "bernoulli_", "exponential_", "geometric_", "cauchy_", "log_normal_"}
DEFAULT_INIT = {"Linear", "Embedding", "Conv1d", "Conv2d", "LayerNorm", "Dropout", "MultiheadAttention", "LSTM", "GRU"}


def source_check(package_dir: Path | None = None) -> dict[str, Any]:
    """A source check that no generator is seeded anywhere but ``core.seeded_generator`` and that the global default generator is not used: no ``manual_seed``/``seed`` call, no ``random`` or ``numpy``
    import, no ``torch.Generator(...)`` outside ``core.py``, no ``torch.nn.init`` or default-initialized ``torch.nn`` layer, and every call of a torch random function carries ``generator=``."""
    root = package_dir if package_dir is not None else core.ROOT / "studies" / "p10s2"
    problems: list[str] = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            where = f"{path.name}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.Import | ast.ImportFrom):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any(m.split(".")[0] in ("random", "numpy") for m in mods):
                    problems.append(f"{where}: imports {mods}")
                if any("nn.init" in m or m.endswith("nn.init") for m in mods) or (isinstance(node, ast.ImportFrom) and node.module == "torch.nn" and any(a.name == "init" for a in node.names)):
                    problems.append(f"{where}: imports torch.nn.init")
            if isinstance(node, ast.Call):
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
                base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
                has_gen = any(k.arg == "generator" for k in node.keywords)
                if name in FORBIDDEN_CALLS or (name == "manual_seed" and path.name != "core.py") or (name == "seed" and base in ("torch", "random")):
                    problems.append(f"{where}: calls {name}")
                if name == "Generator" and path.name != "core.py":
                    problems.append(f"{where}: torch.Generator constructed outside core.py")
                if name in RNG_FUNCS and base in ("torch", "") and not has_gen:
                    problems.append(f"{where}: torch.{name} without generator=")
                if isinstance(f, ast.Attribute) and name in RNG_METHODS:
                    problems.append(f"{where}: .{name}() draws from a generator not passed explicitly")
                if base == "nn" and name in DEFAULT_INIT:
                    problems.append(f"{where}: torch.nn.{name} initializes from the global generator")
    return {"ok": not problems, "problems": problems}


LISTED_PARTITION_SEEDS = tuple(range(220901, 220913))  # 220901-220912 (the lead's ruling: the equivalence injection vector has its own listed seed 220912)
BOOTSTRAP_SEED = 220906  # drawn in the analysis stage and nowhere else (the lead's ruling on the bootstrap seed)
ANALYSIS_STAGE = "analysis"


def record_code_seeds(replicates: int, mode: str) -> None:
    """The +10 oracle-code seed seeds no generator (the hash takes it as an input), so nothing records its use by itself: the gates stage records it for every replicate, so that G9 sees it."""
    for r in range(replicates):
        core.seeded_generator(core.SeedPlan(mode, r).code_seed(), "oracle-code hash seed (recorded for G9; no generator is drawn from it)", mode)


def g9(planned: Sequence[int] = (), planned_mode: str = "registered-run", *, stage: str = "gates", records: Sequence[core.SeedUse] | None = None, replicates: int | None = None) -> dict[str, Any]:
    """Gate G9, strict. ``planned`` are the seeds planned for the registry (every replicate's base + 0..10); ``records`` the seeds actually recorded in this process. Refused: an empty record or no planned
    seeds; any recorded use whose mode label is not the running stage's mode (a label cannot stand in for the mode); a recorded seed outside the planned set of the stage's mode; a replicate whose training
    draw (+1), gold draw (+5) or +10 code seed is not recorded; any partition-side seed 220901-220912 in a registered-run process. 220906 is allowed in the analysis stage only (``analysis_seed_check``)."""
    recs = core.seed_record() if records is None else list(records)
    gate = core.seed_gate(recs, planned, planned_mode=planned_mode, extra_foreign=core.config_seeds())
    problems = list(gate["problems"])
    planned_set = set(planned)
    if not planned_set:
        problems.append("no seed was planned: G9 cannot pass without a planned registry")
    if not recs:
        problems.append("no seed was recorded: G9 cannot pass on an empty seed record")
    for use in recs:
        if use.mode != planned_mode:
            problems.append(f"recorded use of {use.seed} ({use.purpose}) carries mode {use.mode!r}, but this stage runs in mode {planned_mode!r}")
        if planned_set and use.seed not in planned_set and planned_mode == "registered-run":
            problems.append(f"recorded seed {use.seed} ({use.purpose}) is not among the seeds planned for the registry")
        if planned_mode == "registered-run" and use.seed in LISTED_PARTITION_SEEDS:
            problems.append(f"recorded seed {use.seed} ({use.purpose}) is a partition-side seed used in a registered-run process (220906 is drawn in the analysis stage only)")
    if replicates is not None:
        have = {u.seed for u in recs}
        base = [core.SeedPlan(planned_mode, r) for r in range(replicates)]
        for r, p in enumerate(base):
            for off, what in ((1, "training draw"), (5, "gold draw"), (10, "code seed")):
                if p.seed(off) not in have:
                    problems.append(f"replicate {r}: the +{off} seed {p.seed(off)} ({what}) is not recorded")
    src = source_check()
    return {"ok": bool(not problems and src["ok"]), "seeds": {"ok": not problems, "problems": problems, "recorded": gate["recorded"], "planned": sorted(planned_set)}, "source": src, "listed_partition_seeds": list(LISTED_PARTITION_SEEDS), "bootstrap_seed": {"seed": BOOTSTRAP_SEED, "allowed_in_stage": ANALYSIS_STAGE}, "stage": stage}


def analysis_seed_check(records: Sequence[core.SeedUse]) -> dict[str, Any]:
    """The analysis stage draws 220906 and no other seed (a fresh generator per printed interval, in the registry's order). Any other recorded seed is refused; an empty record is allowed (no interval printed)."""
    problems = [f"analysis stage drew seed {u.seed} ({u.purpose}); only {BOOTSTRAP_SEED} may be drawn in it" for u in records if u.seed != BOOTSTRAP_SEED]
    return {"ok": not problems, "problems": problems, "recorded": [{"seed": u.seed, "purpose": u.purpose, "mode": u.mode} for u in records], "stage": ANALYSIS_STAGE}


# --- the gates stage -----------------------------------------------------------------------------------------------------------------------------
def planned_all(mode: str, replicates: int) -> list[int]:
    """Every replicate's base + 0..10."""
    return sorted(s for r in range(replicates) for s in core.SeedPlan(mode, r).planned())


def run_gates(world: World, plan: core.SeedPlan, *, g1: Mapping[str, Any], g3: Mapping[str, Any], equivalence_record: dict[str, Any] | None, file_manifest: Mapping[str, Mapping[str, str]] | None = None, root: Path | None = None, updates: int | None = None, planned: Sequence[int] = (), require_mps: bool = False) -> dict[str, Any]:
    """All gates for one stage run. ``g1`` and ``g3`` come from the data and qualification steps; ``file_manifest`` must be a manifest written at creation (never one computed from the files it is compared
    with). G9 plans every replicate of the world and requires the +10 code seeds to be recorded."""
    record_code_seeds(world.replicates, plan.mode)
    out: dict[str, Any] = {"G1": dict(g1), "G2": g2(world), "G3": dict(g3), "G4": g4(world, plan, updates, require_mps=require_mps), "G5": g5(world, plan), "G6": g6(world, plan), "G7": g7(file_manifest or {}, root or Path(".")), "G8": g8(world, equivalence_record)}
    out["G9"] = g9(planned or planned_all(plan.mode, world.replicates), plan.mode, replicates=world.replicates)
    out["G7"]["manifest_empty"] = not file_manifest
    if not file_manifest:
        out["G7"] = {**out["G7"], "ok": False, "problems": [*out["G7"].get("problems", []), "no file manifest: G7 compares files with digests recorded at creation and cannot pass on none"]}
    out["ok"] = all(bool(out[k].get("ok")) for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"))
    return out


def example_reads_equal(a: Example, b: Example) -> bool:
    return a.reads == b.reads and a.marker == b.marker
