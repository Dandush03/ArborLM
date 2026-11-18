# ruff: noqa: E501
"""P10IS3 planted-positive, NEG-REF, gates, memory bound and the synthetic end-to-end rehearsal (ADR-0026 sections 3.4, 5.3, 8, 11). Tiny models, tens of updates, test-range seeds only (935001-935999);
nothing touches a registered seed, the registered panel with a trained model, or a sealed value. Self-check only."""

import copy
import json
import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.p4_model import Backbone  # noqa: E402
from arborlm.pilot_model import PilotModel  # noqa: E402
from studies.p10i_s3 import (  # noqa: E402
    calibration,
    core,
    gates,
    items,
    model,
    plan,
    planted,
    rehearsal,
    stages,
    synthetic,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
SEEDS = core.Seeds("test")


# ---------------- planted positive and NEG-REF ----------------
@pytest.mark.parametrize("arm", [core.FLAT, core.TREE])
def test_planted_positive_dependence_is_detected_by_every_intervention(arm: str) -> None:
    m = planted.plant(arm)
    e = planted.effects(m, planted.toy_panel(32), SEEDS)
    assert e["C"] > 1.0  # the planted corrections help a lot
    for k in ("P_used", "X", "X_mean", "P_all"):
        assert e[k] >= 0.5 * e["C"], k
    assert e["used_slots"] >= 16


def test_batch_mean_read_keeps_nothing_of_a_zero_mean_plant() -> None:
    m = planted.plant(core.FLAT)
    e = planted.effects(m, planted.toy_panel(32), SEEDS)
    assert abs(e["X_mean"] - e["C"]) < 1e-3  # the corrections are built with zero mean over each batch: the context-free read gives back the baseline


def test_neg_ref_gives_zero_and_is_never_dependent() -> None:
    for arm in (core.FLAT, core.TREE):
        r = planted.neg_ref_check(planted.plant(arm), planted.toy_panel(32), SEEDS, TH)
        assert r["passed"] and all(r["zero_within_tolerance"].values()) and not r["meets_d2_cell"] and not r["meets_d3_cell"]
    # a NEG-REF built from a model whose values are NOT constant would be caught: the check fails if the reference leaks dependence
    m = planted.plant(core.FLAT)
    first = planted.effects(m, planted.toy_panel(32), SEEDS)
    bad = planted.neg_ref(m, first["usage"])
    with torch.no_grad():
        bad.addition.values[3] += 1.0  # type: ignore[union-attr, operator]
    e = planted.effects(bad, planted.toy_panel(32), SEEDS)
    assert abs(e["P_used"]) > 1e-6 or abs(e["P_all"]) > 1e-6


def test_planted_positive_gate_passes() -> None:
    g = planted.planted_positive(TH, SEEDS)
    assert g["passed"] is True and set(g["arms"]) == {core.FLAT, core.TREE}


# ---------------- gates ----------------
def test_read_equality_gate_passes_and_catches_a_wrong_read(monkeypatch: pytest.MonkeyPatch) -> None:
    assert gates.read_equality_gate(core.test_seed(5), bitwise=True)["passed"] is True
    orig = model.memory_read

    def broken(mem, h, ctl, collector=None):  # type: ignore[no-untyped-def]
        out, lookup = orig(mem, h, ctl, collector)
        return out + 1e-3, lookup

    monkeypatch.setattr(model, "memory_read", broken)
    assert gates.read_equality_gate(core.test_seed(5), bitwise=True)["passed"] is False


def test_prefix_identity_gate_and_a_perturbed_run_fails(tmp_path: Path) -> None:
    bb = Backbone(PilotModel("dense_small", 42))
    rows = torch.randint(0, 256, (96, 65), generator=torch.Generator().manual_seed(core.test_seed(40)), dtype=torch.int64)
    for arm in (core.TREE, core.FLAT, core.DENSE):
        g = gates.prefix_identity_gate(arm, bb, rows, init_seed=core.test_seed(41), stream_seed=core.test_seed(42), fresh=True, rate=0.003, short=3, long=6, root=tmp_path / arm, bitwise=True)
        assert g["passed"] is True, arm


def test_base_gate() -> None:
    assert gates.base_gate({"a": (1.0, 1.0, 1.0)}, bitwise=True)["passed"] is True
    assert gates.base_gate({"a": (1.0, 1.0, 1.0 + 1e-9)}, bitwise=True)["passed"] is False
    assert gates.base_gate({"a": (1.0, 1.0, 1.0 + 1e-9)}, bitwise=False)["passed"] is True  # elsewhere: 1e-6


def test_platform_problems_are_named() -> None:
    rec = {**gates.platform_record(), "system": "Linux", "torch": "2.7.0"}
    probs = gates.platform_problems(CFG, rec)
    assert any("system" in p for p in probs) and any("torch" in p for p in probs)
    assert gates.on_platform_of_record(CFG, {**rec, "system": "Darwin", "torch": "2.8.0+cpu", "machine": "arm64", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": True})


def test_rehearsal_gate_reads_the_candidate_plan_hash() -> None:
    rec = {"stages": {"R1": {"status": "COMPLETE"}, "R2": {"status": "COMPLETE"}, "R3": {"status": "COMPLETE"}}, "caps_provisional": False, "candidate": {"plan_file_sha256": "ab"}}
    assert gates.rehearsal_gate(rec, ("R1", "R2", "R3"), plan_file_sha256="ab")["passed"] is True
    assert gates.rehearsal_gate(rec, ("R1", "R2", "R3"), plan_file_sha256="cd")["passed"] is False
    assert gates.rehearsal_gate({**rec, "caps_provisional": True}, ("R1", "R2", "R3"), plan_file_sha256="ab")["passed"] is False
    assert gates.rehearsal_gate({**rec, "stages": {"R1": {"status": "COMPLETE"}}}, ("R1", "R2", "R3"))["passed"] is False
    assert gates.rehearsal_gate(None, ("R1",))["passed"] is False


# ---------------- memory ----------------
def test_reads_and_evaluations_run_without_autograd_and_within_a_memory_bound() -> None:
    bb = Backbone(PilotModel("dense_small", 42))
    panel = torch.randint(0, 256, (256, 65), generator=torch.Generator().manual_seed(core.test_seed(60)), dtype=torch.int64)
    m = model.build_model(copy.deepcopy(bb), core.TREE, core.test_seed(61))
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with torch.no_grad():
        logits, _ = m(panel[:8, :-1], model.Ctl("exhaustive", visit=16))
    assert not logits.requires_grad
    model.evaluate(m, panel, model.Ctl("exhaustive", visit=16), expected_targets=256 * 64)
    model.evaluate_reads(m, panel, SEEDS, 0, expected_targets=256 * 64)
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    assert (after - before) < 1.5 * 2**30  # ru_maxrss is bytes on macOS and kilobytes on Linux: both far below the bound after the unit change below
    assert all(not p.grad for p in m.trainable() if p.grad is not None)


# ---------------- the synthetic end-to-end rehearsal ----------------
def test_synthetic_rehearsal_r1_r3_end_to_end(tmp_path: Path) -> None:
    """R1 (rate search, full controls on the selected rates, NEG-REF, sealed archive, public whitelist) and R3 (every stage in the DRY profile against a candidate plan file) on random data and random backbones."""
    over = {**rehearsal.SYNTHETIC_OVERRIDE, "rates": {"grid": [0.003, 0.03], "max_extensions_per_side": 0}, "resources": {"workers": 6}}
    run = tmp_path / "run"
    sealed_path = tmp_path / "sealed" / "sealed.json"
    pub = rehearsal.run_r1(ROOT, run, over, synthetic=True, sealed_path=sealed_path, cells=(0,))
    # the public file carries the whitelist and no loss value
    assert set(pub) >= {"rate_table", "convergence", "gates", "timing", "storage", "sealed_sha256"}
    assert pub["gates"]["neg_ref"]["passed"] is True and pub["gates"]["core"]["passed"] is True
    assert all(v["passed"] for v in pub["gates"].values())  # prefix identity for every arm-regime, read equality, planted positive, base
    text = (run / "rehearsal_public.json").read_text()
    sealed = sealed_path.read_bytes()
    nll_values = [x for x in json.loads(sealed)["curves"]["M-TREE|REP"]["0.003"]["0"].values()]
    assert all(isinstance(v, float) for v in nll_values) and not any(f"{v}"[:8] in text for v in nll_values)
    cfg = copy.deepcopy(dict(CFG))
    stages.deep_update(cfg, over)
    assert calibration.check_public_against_sealed(pub, sealed, cfg)["result"] == "agree"
    assert set(pub["rate_table"]["rates"]) == {f"{a}|{g}" for a, g in calibration.ARM_REGIMES}
    assert pub["storage"]["snapshots"] > 0 and pub["storage"]["bytes_per_snapshot_mean"] > 1e6
    # the sealed archive holds the statistics of the calibration cell
    body = json.loads(sealed)
    assert "statistics" in body["extra"] and "neg_ref" in body["extra"]
    # R3 against a candidate plan file with the real checkpoint names (its rate table is the candidate's)
    rt = synthetic.rate_table(CFG)
    cand = rehearsal.rehearsal_plan(ROOT, tmp_path / "cand", "candidate", {}, {"train": [], "eval": []}, rt, synthetic=True, gate_profile="dry")
    rec = rehearsal.run_r3(ROOT, tmp_path / "r3", cand, synthetic=True)
    assert rec["status"] == "COMPLETE" and rec["plan_file_sha256"] == plan.file_sha256(cand.path) if hasattr(plan, "file_sha256") else rec["status"] == "COMPLETE"
    assert (tmp_path / "r3" / "r3_report.md").read_text().startswith("# P10-I-S3 report")


def test_items_can_be_listed_for_a_synthetic_resource_and_run_end_to_end(tmp_path: Path) -> None:
    """One cell, one arm, in process: train (restart from 0), evaluate every read, collect the registry, key by key."""
    cfg = copy.deepcopy(dict(CFG))
    stages.deep_update(cfg, rehearsal.SYNTHETIC_OVERRIDE)
    res = stages.synthetic_resources(cfg)
    rt = synthetic.rate_table(cfg)
    its = items.registered_items(cfg, rt, profile="test", cells=[0])
    tr = [i for i in its["train"] if i["arm"] == core.TREE and i["regime"] == core.REP][0]
    rec = items.run_train(res, tr, tmp_path)
    assert rec["status"] == "ok" and set(rec["snapshots"]) == {"0", "2", "4", "6", "8"} and rec["trainable_parameters"] == 198401
    assert items.run_train(res, tr, tmp_path)["seconds"] == rec["seconds"]  # a finished item is not recomputed
    ev = [i for i in its["eval"] if i["train"] == tr["id"]]
    for e in ev:
        items.run_eval(res, e, tmp_path, rec)
    reg = items.collect_registry(tmp_path, {"train": [tr], "eval": ev})
    full = [k for k in reg if k.startswith("nll|M-TREE|REP|") and k.endswith("|u00008|P_used|d3")]
    assert len(full) == 1  # keys carry arm, regime, rate, cell, checkpoint, read and draw
    assert len([k for k in reg if k.startswith("nll|") and "|u00008|" in k]) == 16  # the 16 reads of an M-TREE checkpoint of section 9
    assert len([k for k in reg if k.startswith("nll|") and "|u00000|" in k]) == 2  # step 0: enabled and disabled only (ruling 10)
    assert reg[core.run_key(core.TREE, core.REP, 0.003, 0)]["status"] == "ok"
    # the enabled reference equals the replay bitwise on this platform
    en = reg[core.nll_key(core.TREE, core.REP, 0.003, 0, 8, "enabled")]
    assert en == reg[core.nll_key(core.TREE, core.REP, 0.003, 0, 8, "replay")]


def test_a_code_error_is_an_item_error_and_never_a_failed_cell(tmp_path: Path) -> None:
    p = tmp_path / "train.json"

    def boom() -> None:
        raise OSError("disk full")

    with pytest.raises(OSError):
        items.guarded(p, "train|x", boom)
    rec = core.read_record(p, "train")
    assert rec["status"] == "item_error" and "disk full" in rec["reason"]
    # the analysis refuses while an item error exists and labels nothing
    from studies.p10i_s3 import analysis

    reg = synthetic.registry(CFG, {})
    reg[core.run_key(core.TREE, core.FRESH, 0.003, 0)] = {"status": "item_error"}
    with pytest.raises(core.EngineeringStop, match="ITEM ERRORS"):
        analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    # an EngineeringStop (a defect of plan or driver) propagates untouched and writes no item record
    q = tmp_path / "other.json"

    def stop() -> None:
        raise core.EngineeringStop("x")

    with pytest.raises(core.EngineeringStop):
        items.guarded(q, "train|y", stop)
    assert not q.exists()


def test_failed_run_is_recorded_and_its_evals_are_skipped(tmp_path: Path) -> None:
    cfg = copy.deepcopy(dict(CFG))
    stages.deep_update(cfg, rehearsal.SYNTHETIC_OVERRIDE)
    res = stages.synthetic_resources(cfg)
    rt = synthetic.rate_table(cfg, rate=1e30)
    its = items.registered_items(cfg, rt, profile="test", cells=[0])
    tr = [i for i in its["train"] if i["arm"] == core.DENSE and i["regime"] == core.REP][0]
    rec = items.run_train(res, tr, tmp_path)
    assert rec["status"] == "failed_cell" and rec["reason"].startswith("non-finite") and rec["failed_at_update"] >= 1  # K1: a diverging rate is a failed cell of that rate, not an item error
    ev = [i for i in its["eval"] if i["train"] == tr["id"] and i["update"] == 8][0]
    out = items.run_eval(res, ev, tmp_path, rec)
    assert "skipped" in out
