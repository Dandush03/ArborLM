# ruff: noqa: E501
"""P10IR sealing rule and gates (ADR-0029 sections 4 and 11): the whitelist extractor on synthetic ``eval.json`` files (the sealed values are fake numbers typed here; nothing under the experiments directory
is opened), the source scan that keeps every other module away from ``eval.json``, the gates, the platform of record (bit-exact gates skipped elsewhere, tolerance gates still running) and the seed gate.
Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10ir import core, gates, reads, sealed  # noqa: E402
from studies.p10ir import testing as tiny  # noqa: E402

CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
ROOT = Path(__file__).resolve().parents[1]
FAKE_TREE_RECALL = 0.7316546321
FAKE_IVF_RECALL = 0.4412345678


def write_eval(run: Path, label: str, update: int, *, tree_recall: float | None = None, ivf: bool = True) -> Path:
    rec: dict[str, Any] = {
        "kind": "eval", "label": label, "update": update,
        "reads": {"main": {"panels": {p: {"n": 100, "correct": 80 + i, "useful": 70 + i, "disabled_correct": 3, "unseen_n": 9} for i, p in enumerate("AB")}, "deep": {"separability": {"nn_cosine_mean": 0.8}}}},
    }  # fmt: skip
    if tree_recall is not None:
        rec["reads"]["main"]["deep"]["separability"]["tree_recall_of_exhaustive_top8"] = tree_recall
    if ivf:
        rec["reads"]["ivf"] = {"panels": {p: {"n": 100, "correct": 60, "useful": 50 + i} for i, p in enumerate("AB")}, "ivf_measured": {"recall_of_exhaustive_top8": FAKE_IVF_RECALL, "candidates_mean": 512.0}, "index_sha256": "ab" * 32, "index_lists": 16}
    path = sealed.eval_path(run, label, update)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec), encoding="utf-8")
    return path


# --- the extractor -------------------------------------------------------------------------------------------------------------------------
def test_counts_return_only_the_whitelisted_keys(tmp_path: Path) -> None:
    write_eval(tmp_path, "cell", 8, tree_recall=FAKE_TREE_RECALL)
    got = sealed.counts(tmp_path, "cell", 8, "main")
    assert got == {"A": {"n": 100, "correct": 80, "useful": 70}, "B": {"n": 100, "correct": 81, "useful": 71}}
    assert sealed.counts(tmp_path, "cell", 8, "ivf") == {"A": {"n": 100, "correct": 60, "useful": 50}, "B": {"n": 100, "correct": 60, "useful": 51}}
    assert sealed.index_record(tmp_path, "cell", 8) == {"index_sha256": "ab" * 32, "index_lists": 16}
    assert str(FAKE_TREE_RECALL) not in json.dumps([got, sealed.index_record(tmp_path, "cell", 8)])
    assert str(FAKE_IVF_RECALL) not in json.dumps(sealed.counts(tmp_path, "cell", 8, "ivf"))


def test_sealed_equal_answers_equal_or_not_equal_and_prints_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_eval(tmp_path, "cell", 8, tree_recall=FAKE_TREE_RECALL)
    assert sealed.sealed_equal(tmp_path, "cell", 8, "tree_recall", FAKE_TREE_RECALL) is True
    assert sealed.sealed_equal(tmp_path, "cell", 8, "tree_recall", FAKE_TREE_RECALL + 1e-12) is False
    assert sealed.sealed_equal(tmp_path, "cell", 8, "ivf_recall", FAKE_IVF_RECALL) is True
    assert sealed.sealed_equal(tmp_path, "cell", 8, "ivf_recall", 0.0) is False
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    with pytest.raises(ValueError):
        sealed.sealed_equal(tmp_path, "cell", 8, "something_else", 0.0)


def test_a_missing_key_or_file_names_the_path_and_never_a_value(tmp_path: Path) -> None:
    write_eval(tmp_path, "cell", 8, tree_recall=None, ivf=False)
    with pytest.raises(sealed.SealedMissing) as exc:
        sealed.sealed_equal(tmp_path, "cell", 8, "tree_recall", 0.5)
    assert "0.5" not in str(exc.value) and "key path" in str(exc.value)
    with pytest.raises(sealed.SealedMissing):
        sealed.counts(tmp_path, "cell", 8, "ivf")
    with pytest.raises(sealed.SealedMissing):
        sealed.counts(tmp_path, "nope", 8, "main")


def test_information_series_and_available_updates_come_from_counts_and_directory_names(tmp_path: Path) -> None:
    for u in (4, 8, 16):
        write_eval(tmp_path, "cell", u)
    assert sealed.available_updates(tmp_path, "cell") == [4, 8, 16]
    from studies.p10s1 import core as s1

    series = sealed.information_series(tmp_path, "cell", [4, 8])
    assert series["A"][8] == s1.bits_per_fact(70, 100) and series["B"][4] == s1.bits_per_fact(71, 100)


def test_only_the_extractor_names_an_eval_json_or_reads_a_sealed_key() -> None:
    """Every access to an ``eval.json`` goes through ``sealed.py``: no other module under studies/p10ir names one or a sealed key path; the two places that handle P10-S1's index recall quantity (a number
    measured by P10-S1's own IVFMemory) are the read pass that drops it and the gate that consumes it."""
    allowed = {"eval.json": {"sealed.py"}, "tree_recall_of_exhaustive_top8": {"sealed.py"}, "recall_of_exhaustive_top8": {"sealed.py", "reads.py", "items.py"}, "ivf_measured": {"sealed.py"}}
    for path in sorted((ROOT / "studies" / "p10ir").glob("*.py")):
        src = path.read_text(encoding="utf-8")
        for key, ok in allowed.items():
            code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
            if key in code and path.name not in ok:
                # docstrings may describe the rule; a quoted string or an open() call is what is forbidden
                assert f'"{key}"' not in code and f"'{key}'" not in code and f"/ {key}" not in code, f"{path.name} names {key}"
    for path in sorted((ROOT / "studies" / "p10ir").glob("*.py")):
        if path.name != "sealed.py":
            assert "json.load(" not in path.read_text(encoding="utf-8") or "eval" not in path.read_text(encoding="utf-8").split("json.load(")[1][:60]


def test_the_stored_read_records_never_hold_the_recall_quantity_of_p10s1() -> None:
    rec = reads.read_record("A1", "c", 8, "I256@512", {"panels": {}, "work": {}, "measured": {"recall_of_exhaustive_top8": 0.5, "candidates_mean": 600.0, "candidates_p99": 700.0}})
    assert "recall" not in json.dumps(rec) and rec["candidates"] == {"mean": 600.0, "p99": 700.0}


def test_recall_gates_report_equal_or_not_equal_and_nothing_else(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_eval(tmp_path, "T", 8, tree_recall=FAKE_TREE_RECALL)
    write_eval(tmp_path, "F", 8)
    ok = gates.recall_gates(tmp_path, "T", "F", 8, tree_recall_value=FAKE_TREE_RECALL, ivf_recall_value=FAKE_IVF_RECALL, cfg=CFG)
    assert ok["tree_recall_reproduction"]["scope"] == "tree" and ok["ivf_recall_reproduction"]["scope"] == "index"
    bad = gates.recall_gates(tmp_path, "T", "F", 8, tree_recall_value=0.1, ivf_recall_value=0.2, cfg=CFG)
    for g in (*ok.values(), *bad.values()):
        assert set(g) <= {"scope", "passed", "status", "equal", "reason"}  # no value of the recorded quantity, no value of the recomputed one
        assert str(FAKE_TREE_RECALL) not in json.dumps(g) and str(FAKE_IVF_RECALL) not in json.dumps(g)
    if gates.on_platform_of_record(CFG):
        assert all(g["passed"] is True for g in ok.values()) and all(g["passed"] is False for g in bad.values())
    assert capsys.readouterr().out == ""
    assert gates.recall_gates(tmp_path, None, None, 8, tree_recall_value=None, ivf_recall_value=None, cfg=CFG) == {}


# --- the platform of record ----------------------------------------------------------------------------------------------------------------
LINUX = {"system": "Linux", "machine": "x86_64", "torch": "2.8.0+cpu", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": True}
MAC = {"system": "Darwin", "machine": "arm64", "torch": "2.8.0", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": True}


def test_platform_problems_name_every_difference() -> None:
    assert gates.platform_problems(CFG, MAC) == [] and gates.on_platform_of_record(CFG, MAC)
    assert any("system" in p for p in gates.platform_problems(CFG, LINUX))
    assert any("torch_num_threads" in p for p in gates.platform_problems(CFG, {**MAC, "torch_num_threads": 6}))
    assert any("deterministic" in p for p in gates.platform_problems(CFG, {**MAC, "deterministic_algorithms": False}))
    assert any("torch:" in p for p in gates.platform_problems(CFG, {**MAC, "torch": "2.7.0"}))
    assert gates.platform_problems(CFG, {**MAC, "torch": "2.8.0+cpu"}) == []  # a local-version suffix of the same torch is the same torch


def test_bit_exact_gates_are_skipped_elsewhere_and_the_tolerance_gates_still_run() -> None:
    mem = tiny.tree_memory(4, 938501)
    codes = tiny.unit_queries(60, 938502)
    keys = mem.keys.detach()
    assert gates.exact("tree", lambda: (True, {}), CFG, LINUX) == {"scope": "tree", "passed": None, "status": "skipped", "reason": gates.exact("tree", lambda: (True, {}), CFG, LINUX)["reason"]}
    assert gates.index_rebuild_gate(keys, 938901, 16, CFG, LINUX)["status"] == "skipped"
    assert gates.path_gate(10, 0, CFG, LINUX)["status"] == "skipped" and gates.counts_gate("tree", {"A": {}}, {"A": {}}, source="x", cfg=CFG, record=LINUX)["status"] == "skipped"
    # gate 4 is a tolerance gate: it runs and passes on any platform
    res = gates.exactness_gates(mem, codes, TH, chunk_elements=1 << 20)
    assert all(g["passed"] is True for g in res.values())
    # a skipped gate is not a failure when the analysis reads the item, a failed or malformed one is
    from studies.p10ir.registry import scope_ok

    item = {"complete": True, "gates": {"a": {"scope": "tree", "passed": None, "status": "skipped"}}}
    assert scope_ok(item, "tree")[0] is True
    item["gates"]["b"] = {"scope": "tree", "passed": False, "status": "failed"}
    assert scope_ok(item, "tree") == (False, "gate(s) failed: b")
    assert scope_ok({"complete": True, "gates": {"c": {"scope": "tree", "passed": None}}}, "tree")[0] is False  # no 'skipped' status: not trusted


def test_gate_2_helpers_on_the_platform_of_record() -> None:
    same = {p: {"n": 10, "correct": 7, "useful": 6} for p in "AB"}
    other = {p: {"n": 10, "correct": 7, "useful": 5} for p in "AB"}
    if not gates.on_platform_of_record(CFG):
        pytest.skip("bit-exact gates run on macOS arm64 only (they are recorded as skipped elsewhere: tested above)")
    assert gates.counts_gate("tree", same, same, source="s", cfg=CFG)["passed"] is True
    assert gates.counts_gate("tree", same, other, source="s", cfg=CFG)["passed"] is False
    assert gates.counts_gate("index", same, same, source="s", cfg=CFG, extra_equal={"index_hash_equal": False})["passed"] is False
    assert gates.path_gate(10, 0, CFG)["passed"] is True and gates.path_gate(10, 1, CFG)["passed"] is False and gates.path_gate(0, 0, CFG)["passed"] is False  # no query checked is not a pass


# --- gate 6: seeds --------------------------------------------------------------------------------------------------------------------------------
def test_seed_gate_passes_with_the_registry_values_and_lists_the_declared_reuse() -> None:
    res = gates.seed_gate(CFG, run_checker=False)
    assert res["passed"], res["problems"]
    assert res["declared_reuse_not_new"] == {"p10s1_registered_draws_160_values": 160, "adapter_identity_gate_draw_1": 38}  # registry section 4.6: 2101, its R2 images 3101-7101 and the 32 values of set 210001
    assert res["roles"]["i64_index_seeds"] == 3 and res["roles"]["initialisation"] == 8 and res["roles"]["rehearsal_set"] == 32
    planned = gates.planned_seed_values(CFG)
    lo, hi = CFG["seed_ranges"]["bridge"]
    assert all(lo <= v <= hi for v in planned["bridge_sets"])
    assert min(planned["bridge_sets"]) == 290001 and 290061 in planned["bridge_sets"] and 290461 in planned["bridge_sets"]  # base + 60 is the index seed
    assert planned["initialisation"] == {330601, 330602, 330603, 330604, 330605, 330692, 330698, 330699}
    assert not (planned["bridge_sets"] & gates.declared_reuse(CFG)["p10s1_registered_draws_160_values"])


def test_seed_gate_detects_a_value_outside_its_range_and_a_collision_with_a_declared_reuse() -> None:
    bad = copy.deepcopy(dict(CFG))
    bad["seeds"] = {**CFG["seeds"], "bridge_base": 210001}  # inside P10-S1's registered draws
    res = gates.seed_gate(bad, run_checker=False)
    assert not res["passed"] and any("outside the registry's range" in p for p in res["problems"]) and any("declared re-use" in p for p in res["problems"])
    bad2 = copy.deepcopy(dict(CFG))
    bad2["seeds"] = {**CFG["seeds"], "index_seeds": [298001, 298002, 290001]}
    assert any("index" in p for p in gates.seed_gate(bad2, run_checker=False)["problems"])


def test_seed_gate_refuses_a_checker_file_that_is_not_the_cited_one(tmp_path: Path) -> None:
    (tmp_path / "docs" / "reviews" / "p10-i-direction-2026-11-17").mkdir(parents=True)
    fake = tmp_path / CFG["seed_ranges"]["checker"]
    fake.write_text("print('RESULT: PASS')\n", encoding="utf-8")
    res = gates.seed_gate(CFG, root=tmp_path, run_checker=True)
    assert not res["passed"] and any("differs from the SHA-256 the ADR cites" in p for p in res["problems"])
    assert gates.seed_gate(CFG, root=tmp_path / "nowhere", run_checker=True)["passed"] is False


def test_the_extended_checker_copy_differs_from_the_cited_file_by_exactly_three_substitutions() -> None:
    cited = (ROOT / CFG["seed_ranges"]["checker"]).read_text(encoding="utf-8")
    copy_text = gates.checker_copy(cited, ROOT)
    assert len(gates.CHECKER_SUBSTITUTIONS) == 3 and copy_text != cited
    old_lines, new_lines = cited.splitlines(), copy_text.splitlines()
    assert len(old_lines) == len(new_lines) and sum(1 for a, b in zip(old_lines, new_lines, strict=True) if a != b) == 3
    with pytest.raises(ValueError):
        gates.checker_copy(cited.replace("ROOT = Path(__file__).resolve().parents[3]", "ROOT = x"), ROOT)


def test_the_extended_registry_checker_prints_result_pass() -> None:
    res = gates.seed_gate(CFG, run_checker=True)
    assert res["passed"], res["problems"]
    assert res["checker"]["result_line"] == "RESULT: PASS" and res["checker"]["returncode"] == 0


# --- gate 5 ----------------------------------------------------------------------------------------------------------------------------------------
def test_rehearsal_gate_needs_every_stage_complete_and_gates_1_and_2_on_the_registered_checkpoints() -> None:
    stages = ("gates-a1", "a1")
    done = {"stages": {s: {"status": "COMPLETE"} for s in stages}, "registered_checkpoint_gates": {"gate1_passed": True, "gate2_passed": True, "gate3_run": False}}
    assert gates.rehearsal_gate(done, stages)["passed"] is True
    assert gates.rehearsal_gate(None, stages)["passed"] is False
    partial = {**done, "stages": {"gates-a1": {"status": "COMPLETE"}, "a1": {"status": "PAUSED"}}}
    assert gates.rehearsal_gate(partial, stages)["missing"] == ["a1"]
    ran_gate3 = {**done, "registered_checkpoint_gates": {"gate1_passed": True, "gate2_passed": True, "gate3_run": True}}
    assert gates.rehearsal_gate(ran_gate3, stages)["passed"] is False  # gate 3 is never run before the freeze
    assert gates.rehearsal_gate({**done, "registered_checkpoint_gates": {"gate1_passed": True, "gate2_passed": False, "gate3_run": False}}, stages)["passed"] is False


def test_the_declared_reuse_of_the_identity_gate_is_the_registrys_38_values() -> None:
    vals = gates.declared_reuse(CFG)["adapter_identity_gate_draw_1"]
    assert len(vals) == 38 and {2101, 3101, 4101, 5101, 6101, 7101} <= vals and 210001 in vals and 210061 in vals


def test_the_studys_own_ranges_lie_inside_the_registrys_allocation_rows_of_adr_0029() -> None:
    """Ruling 6, the separate check: the rows are parsed from the cited checker's ALLOC table and compared with the config's ranges."""
    text = (ROOT / CFG["seed_ranges"]["checker"]).read_text(encoding="utf-8")
    rows = gates.allocation_rows(text)
    assert ("data: bridge draw sets (5)", 290001, 296999) in rows and ("I64 index seeds (3)", 298001, 298999) in rows and ("rehearsal draw set (1)", 299201, 299299) in rows
    assert ("init sub-row", 330601, 330699) in rows and ("test", 938001, 938999) in rows and len(rows) == 8
    assert gates.allocation_problems(CFG, rows) == []
    bad = copy.deepcopy(dict(CFG))
    bad["seed_ranges"] = {**CFG["seed_ranges"], "bridge": [290001, 299999]}
    assert any("bridge" in p for p in gates.allocation_problems(bad, rows))
    # the test index seeds the rehearsal and the tests use are in the test range, and are not the registered index seeds
    t = core.i64_seeds(CFG, test=True)
    assert all(938001 <= v <= 938999 for v in t) and not set(t) & set(core.i64_seeds(CFG))
    assert set(t) <= gates.planned_seed_values(CFG)["test_index_seeds"]


def test_gate_4_and_the_fact_passes_run_without_autograd() -> None:
    """Audit B1: the checkpoint's keys and router are Parameters; nothing a read or a gate returns may carry a graph."""
    mem = tiny.tree_memory(4, 938601)
    mem.keys.requires_grad_(True)
    mem.router.requires_grad_(True)
    q = tiny.unit_queries(40, 938602)
    out = reads.tree_path(mem.keys, mem.router, q, 2, True, True, per=256, chunk_elements=1 << 20)
    for t in (out.values, out.ids, out.branch_ids, out.routes, reads.exhaustive_top(mem.keys, q, 8, 1 << 20)[0], reads.independent_flat(mem.keys, mem.router, q, True, per=256, chunk_elements=1 << 20)[0]):
        assert t.grad_fn is None and not t.requires_grad
    res = reads.tree_fact_pass(mem, q, reads.tree_read_specs(1024, CFG), chunk_elements=1 << 20)
    assert all(isinstance(v, float) for e in res.values() for v in e["facts"].values())
    ids, vals = gates._collect(lambda x: (lambda o: (o.values, o.ids))(reads.tree_path(mem.keys, mem.router, x, 4, True, True, per=256, chunk_elements=1 << 20)), q, 16)
    assert ids.grad_fn is None and vals.grad_fn is None and not vals.requires_grad
    assert all(g["passed"] is True for g in gates.exactness_gates(mem, q, TH, chunk_elements=1 << 20).values())


def test_fact_pass_memory_does_not_grow_with_the_number_of_facts() -> None:
    """Audit B1, memory bound: 16,384 slots, 256 facts, keys that are Parameters: the peak RSS must grow by well under 100 MiB (with autograd on it grew by 841.6 MiB). A fresh process, so that the peak is this pass's."""
    code = f"""
import resource, sys
sys.path.insert(0, {str(ROOT)!r})
import torch
from torch.nn import functional as F
from studies.p9.model import AdditionSpec
from studies.p10ir import core, reads
from studies.p10s1.model import S1Memory
torch.set_num_threads(1)
mem = S1Memory(AdditionSpec("learned_tree", 16384, 16, "R1", 64, 0), 938801)
assert mem.keys.requires_grad and mem.router.requires_grad
g = torch.Generator().manual_seed(938802)
q = F.normalize(torch.randn(256, 16, generator=g), dim=-1)
specs = [s for s in reads.tree_read_specs(16384) if s.name in ("T0", "T1", "T1w", "T3", "T2")]
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
reads.tree_fact_pass(mem, q, specs, chunk_elements=1 << 20)
after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print((after - before) / 2**20)
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=600, check=False)
    assert out.returncode == 0, out.stderr[-800:]
    growth = float(out.stdout.strip().splitlines()[-1])
    assert growth < 100.0, f"peak RSS grew by {growth:.1f} MiB"
