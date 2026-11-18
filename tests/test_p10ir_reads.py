# ruff: noqa: E501
"""P10IR read tests (ADR-0029 sections 6 and 7, gate 2 and gate 4): every read against a brute-force reference on tiny tensors; T0 against P10-S1's ``S1Memory._top_tree`` on random small trees (bit
for bit on the platform of record, within 1e-6 elsewhere); the I64 reads against a loop that collects lists; the new measures against loops; the end-task counts of T0, F0 and I256@512 against P10-S1's own
``_read_record`` on a tiny model. Seeds: the unit-test range 938001-938999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from studies.p10ir import core, gates, reads  # noqa: E402
from studies.p10ir import testing as tiny  # noqa: E402
from studies.p10s1 import core as s1core  # noqa: E402
from studies.p10s1 import evaluate as s1eval  # noqa: E402
from studies.p10s1 import index as s1index  # noqa: E402
from studies.p10s1.model import S1Memory  # noqa: E402

CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
CHUNK = int(CFG["resources"]["eval_chunk_elements"])
EPS = 1e-12


def on_record() -> bool:
    """Evaluated when a test runs (the session fixture sets one thread and deterministic algorithms after import)."""
    return gates.on_platform_of_record(CFG)


def same(a: torch.Tensor, b: torch.Tensor) -> bool:
    """Bit-exact on the platform of record (macOS arm64); elsewhere the tolerance version (the bit-exact assertion is made there only)."""
    return torch.equal(a, b) if on_record() else (a.shape == b.shape and bool(torch.allclose(a.double(), b.double(), atol=1e-6, rtol=0.0)) if a.is_floating_point() else torch.equal(a, b))


# --- brute force ---------------------------------------------------------------------------------------------------------------------------
def brute_tree(mem: S1Memory, q: torch.Tensor, v: int, prior_select: bool, prior_weight: bool) -> tuple[list[list[int]], list[list[float]], list[list[int]]]:
    keys = F.normalize(mem.keys.double(), dim=-1)
    router = F.normalize(mem.router.double(), dim=-1)
    per, branches = mem.spec.per_branch, mem.spec.branches
    ids_out, w_out, br_out = [], [], []
    for row in q.double():
        routes = (router @ row) / 0.2
        order = sorted(range(branches), key=lambda b: (-float(routes[b]), b))[:v]
        prior = routes.log_softmax(-1)
        cands = []
        for b in order:
            for s in range(b * per, (b + 1) * per):
                cos = float(keys[s] @ row) / 0.2
                pr = float(prior[b])
                cands.append((cos + (pr if prior_select else 0.0), s, cos + (pr if prior_weight else 0.0)))
        cands.sort(key=lambda t: (-t[0], t[1]))
        top = cands[:8]
        weights = torch.tensor([t[2] for t in top]).softmax(-1).tolist()
        ids_out.append([t[1] for t in top])
        w_out.append(weights)
        br_out.append(order)
    return ids_out, w_out, br_out


def path_weights(out: reads.TreeOut) -> list[list[float]]:
    return reads._weights(out.values).double().tolist()


# --- T0 equals P10-S1's read ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("branches", [2, 3, 4, 6])
@pytest.mark.parametrize("chunk", [CHUNK, 1 << 14])
def test_t0_equals_the_top_of_s1_top_tree_on_random_trees(branches: int, chunk: int) -> None:
    """Property (gate 2, R3-1): the common path at v = 2 with both priors on gives P10-S1's slot ids and scores, for every query, on random small trees and for two chunkings."""
    for k in range(3):
        seed = 938001 + 10 * branches + k
        mem = tiny.tree_memory(branches, seed)
        mem.chunk_elements = chunk
        q = tiny.unit_queries(37, seed + 5)
        ref_values, ref_ids, ref_branches, ref_routes = mem._top_tree(q)
        out = reads.tree_path(mem.keys, mem.router, q, 2, True, True, per=256, chunk_elements=chunk)
        assert same(ref_values[:, :8], out.values[:, :8]) and torch.equal(ref_ids[:, :8], out.ids[:, :8])
        assert torch.equal(ref_branches, out.branch_ids) and same(ref_routes, out.routes)
        assert same(ref_values, out.values) and torch.equal(ref_ids, out.ids)  # all 64 columns, not only the top 8


@pytest.mark.parametrize("branches", [4, 6])
def test_t0_memory_verifies_every_query_it_serves(branches: int) -> None:
    seed = 938101 + branches
    src = tiny.tree_memory(branches, seed)
    mem = reads.TreeReadMemory(src, reads.TreeReadSpec("T0", 2, True, True), verify=True)
    q = tiny.unit_queries(50, seed + 1)
    mem._top_tree(q)
    assert (mem.checked, mem.mismatched) == (50, 0)
    # the counters count the read, not the check: K = N/256 + 2 x 256 per query
    assert mem.counters.key_scores == 50 * (branches + 2 * 256)
    # a read that differs from T0 is caught as a mismatch (the check is not vacuous)
    wrong = reads.TreeReadMemory(src, reads.TreeReadSpec("T1", 2, False, False), verify=True)
    wrong._top_tree(q)
    assert wrong.mismatched > 0


# --- every read against brute force --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("branches", [4, 6, 16])
def test_every_tree_read_against_brute_force(branches: int) -> None:
    seed = 938201 + branches
    mem = tiny.tree_memory(branches, seed)
    q = tiny.unit_queries(5 if branches == 16 else 9, seed + 1)  # 16 branches = 4,096 slots: the sweep reads Tv1, Tv4 and Tv8 exist there
    specs = {s.name: s for s in reads.tree_read_specs(256 * branches, CFG)}
    assert {"T0", "T1", "T1w", "T3", "T2"} <= set(specs)
    for name, spec in specs.items():
        v = spec.v(branches)
        out = reads.tree_path(mem.keys, mem.router, q, v, spec.prior_select, spec.prior_weight, per=256, chunk_elements=CHUNK)
        ids, weights, order = brute_tree(mem, q, v, spec.prior_select, spec.prior_weight)
        assert out.ids[:, :8].tolist() == ids, name
        assert out.branch_ids.tolist() == order, name
        assert torch.allclose(torch.tensor(path_weights(out)), torch.tensor(weights), atol=1e-5), name


def test_read_definitions_t3_is_all_keys_with_the_prior_t2_is_exact_search() -> None:
    mem = tiny.tree_memory(4, 938301)
    q = tiny.unit_queries(20, 938302)
    t3 = reads.tree_path(mem.keys, mem.router, q, 4, True, True, per=256, chunk_elements=CHUNK)
    t2 = reads.tree_path(mem.keys, mem.router, q, 4, False, False, per=256, chunk_elements=CHUNK)
    exact_vals, exact_ids = reads.exhaustive_top(mem.keys, q, 64, CHUNK)
    assert torch.equal(t2.ids, exact_ids)  # T2 is exact search over the tree's keys read as a flat memory
    assert torch.allclose(t2.values, exact_vals, atol=1e-5)
    ind_vals, ind_ids = reads.independent_flat(mem.keys, mem.router, q, True, per=256, chunk_elements=CHUNK)
    assert torch.equal(t3.ids[:, :8], ind_ids[:, :8]) and torch.allclose(t3.values, ind_vals, atol=1e-5)
    # the prior is one constant per branch: within one branch the order of any two slots is the same with or without it
    t1 = reads.tree_path(mem.keys, mem.router, q, 2, False, False, per=256, chunk_elements=CHUNK)
    t0 = reads.tree_path(mem.keys, mem.router, q, 2, True, True, per=256, chunk_elements=CHUNK)
    for r in range(q.shape[0]):
        for b in t0.branch_ids[r].tolist():
            a = [s for s in t0.ids[r, :64].tolist() if s // 256 == b]
            c = [s for s in t1.ids[r, :64].tolist() if s // 256 == b]
            common = [s for s in a if s in c]
            assert [s for s in a if s in common] == [s for s in c if s in common]


def test_t1w_keeps_the_t0_selection_and_removes_the_prior_from_the_weights() -> None:
    mem = tiny.tree_memory(4, 938311)
    q = tiny.unit_queries(15, 938312)
    t0 = reads.tree_path(mem.keys, mem.router, q, 2, True, True, per=256, chunk_elements=CHUNK)
    t1w = reads.tree_path(mem.keys, mem.router, q, 2, True, False, per=256, chunk_elements=CHUNK)
    assert torch.equal(t0.ids, t1w.ids)  # the selection of T0
    keys = F.normalize(mem.keys, dim=-1)
    cos = (q @ keys.T) / 0.2
    assert torch.allclose(t1w.values[:, :8], cos.gather(1, t1w.ids[:, :8]), atol=1e-5)  # weights are the softmax of cos / 0.2 over the slots T0 selected


def test_tv1_priors_on_against_off_pass_the_exactness_identity_and_a_real_difference_fails_it() -> None:
    mem = tiny.tree_memory(6, 938321)
    codes = tiny.unit_queries(300, 938322)
    res = gates.exactness_gates(mem, codes, TH, chunk_elements=CHUNK)
    assert set(res) == {"tv1_priors_on_against_off", "t3_against_independent_flat", "t2_against_independent_flat"}
    assert all(g["passed"] is True and g["scope"] == "tree" for g in res.values()), res
    on = reads.tree_path(mem.keys, mem.router, codes, 2, True, True, per=256, chunk_elements=CHUNK)
    off = reads.tree_path(mem.keys, mem.router, codes, 2, False, False, per=256, chunk_elements=CHUNK)
    diff = gates.compare_selection(on.ids, on.values, off.ids, off.values, TH)
    assert diff["passed"] is False and diff["not_float_ties"] > 0  # v = 2: the prior is a real effect, so the identity does not hold


# --- the gate-4 comparison: float ties and tolerances (R3-6) ------------------------------------------------------------------------------------
def test_compare_selection_float_tie_definition_and_tolerances() -> None:
    base = [3.0, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3, 2.3 - 5e-6]
    va = torch.tensor([base + [0.0] * 3])[:, :12]
    ids_a = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]])
    # identical sets, identical scores: passes
    r = gates.compare_selection(ids_a, va, ids_a, va, TH)
    assert r["passed"] and r["sets_differ"] == 0 and r["max_weight_difference"] == 0.0
    # the 8th and 9th scores differ by 5e-6 (at most 1e-5): the swapped 8th/9th slot is a float tie, counted; one tie in one fact is 100% of facts, above 0.1%, so the gate fails on the share
    ids_b = ids_a.clone()
    ids_b[0, 7], ids_b[0, 8] = ids_a[0, 8], ids_a[0, 7]
    r = gates.compare_selection(ids_a, va, ids_b, va, TH)
    assert r["sets_differ"] == 1 and r["float_ties"] == 1 and r["not_float_ties"] == 0 and r["passed"] is False and r["float_tie_share"] == 1.0
    # with enough identical facts the same single tie is within 0.1%
    many_a, many_v = ids_a.repeat(2000, 1), va.repeat(2000, 1)
    many_b = many_a.clone()
    many_b[0, 7], many_b[0, 8] = many_a[0, 8], many_a[0, 7]
    r = gates.compare_selection(many_a, many_v, many_b, many_v, TH)
    assert r["float_ties"] == 1 and r["float_tie_share"] == 1 / 2000 and r["passed"] is True
    # a gap of 1e-4 at the boundary is not rounding: a different set there is not a float tie and fails
    wide = torch.tensor([[3.0, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3, 2.3 - 1e-4, 0.0, 0.0, 0.0]])
    r = gates.compare_selection(ids_a, wide, ids_b, wide, TH)
    assert r["not_float_ties"] == 1 and r["passed"] is False
    # either computation's tie counts ("in either computation")
    r = gates.compare_selection(ids_a, wide, ids_b, va, TH)
    assert r["float_ties"] == 1 and r["not_float_ties"] == 0
    # weights: a difference above 1e-6 slot by slot fails
    shifted = va.clone()
    shifted[0, 0] += 1e-4
    r = gates.compare_selection(ids_a, va, ids_a, shifted, TH)
    assert r["passed"] is False and r["max_weight_difference"] > 1e-6
    tiny_shift = va.clone()
    tiny_shift[0, 0] += 1e-8
    assert gates.compare_selection(ids_a, va, ids_a, tiny_shift, TH)["passed"] is True
    # weights are aligned by slot id, so two orders of the same set compare equal
    perm = torch.tensor([[7, 6, 5, 4, 3, 2, 1, 0, 8, 9, 10, 11]])
    assert gates.compare_selection(ids_a, va, ids_a.gather(1, perm), va.gather(1, perm), TH)["max_weight_difference"] == 0.0


# --- the flat reads and the index ------------------------------------------------------------------------------------------------------------
def test_exhaustive_top_against_brute_force_and_p10s1_top_flat() -> None:
    mem = tiny.flat_memory(1024, 938401)
    q = tiny.unit_queries(11, 938402)
    vals, ids = reads.exhaustive_top(mem.keys, q, 64, CHUNK)
    keys = F.normalize(mem.keys.double(), dim=-1)
    for r, row in enumerate(q.double()):
        scores = (keys @ row) / 0.2
        want = sorted(range(1024), key=lambda s: (-float(scores[s]), s))[:8]
        assert ids[r, :8].tolist() == want
    ref_vals, ref_ids = mem._top_flat(q)
    assert torch.equal(ids, ref_ids) and same(vals, ref_vals)


@pytest.mark.parametrize("slots", [1024, 4096])
def test_i64_budget_memory_with_512_equals_p10s1_ivf_memory_and_collects_at_least_c(slots: int) -> None:
    mem = tiny.flat_memory(slots, 938410 + slots // 1024)
    q = tiny.unit_queries(25, 938411)
    idx256 = s1index.build_index(mem.keys.detach(), 938901)
    theirs = s1index.IVFMemory(mem, idx256)
    mine = reads.IVFBudgetMemory(mem, idx256, 512)
    tv, ti = theirs._top_flat(q)
    mv, mi = mine._top_flat(q)
    assert torch.equal(ti, mi) and same(tv, mv)  # the registered read, called through the new class
    idx64 = s1index.build_index(mem.keys.detach(), 938902, slots // 64)
    assert idx64.lists == slots // 64
    for c in core.feasible_budgets(slots, CFG):
        mask, counts = s1index.candidate_mask(idx64, q, c)
        assert bool((counts >= c).all()) and mask.sum(1).tolist() == counts.tolist()
        # a loop: lists in descending centroid score (stable) until at least c keys are collected
        scores = q.double() @ idx64.unit.double().T
        for r in range(q.shape[0]):
            order = sorted(range(idx64.lists), key=lambda j: (-float(scores[r, j]), j))
            total, take = 0, []
            for j in order:
                take.append(j)
                total += int(idx64.sizes[j])
                if total >= c:
                    break
            expect = torch.isin(idx64.assign, torch.tensor(take))
            assert torch.equal(mask[r], expect) or int((mask[r] != expect).sum()) <= 2  # near-ties of centroid scores between float32 and float64 may reorder
        # more budget never collects fewer keys
    sizes = [int(s1index.candidate_mask(idx64, q, c)[1].float().mean()) for c in core.feasible_budgets(slots, CFG)]
    assert sizes == sorted(sizes)


def test_the_index_is_bit_identical_on_rebuild_and_the_gate_reports_it() -> None:
    mem = tiny.flat_memory(1024, 938421)
    res = gates.index_rebuild_gate(mem.keys.detach(), 298003, 16, CFG)
    if on_record():
        assert res["passed"] is True and res["scope"] == "index" and res["lists"] == 16
    else:
        assert res["passed"] is None and res["status"] == "skipped"


# --- the new measures against loops ------------------------------------------------------------------------------------------------------------
def test_tree_fact_measures_against_loops() -> None:
    mem = tiny.tree_memory(4, 938431)
    codes = tiny.unit_queries(64, 938432)
    specs = reads.tree_read_specs(1024, CFG)
    res = reads.tree_fact_pass(mem, codes, specs, chunk_elements=CHUNK, chunk=16)
    keys = F.normalize(mem.keys.double(), dim=-1)
    byname = {s.name: s for s in specs}
    for name in ("T0", "T1", "T1w", "T3", "T2", "Tv1_on"):
        spec = byname[name]
        v = spec.v(4)
        ids, _, branches = brute_tree(mem, codes, v, spec.prior_select, spec.prior_weight)
        cr8, cr1, sr8, am_c, am_s = [], [], [], [], []
        for r, row in enumerate(codes.double()):
            scores = (keys @ row) / 0.2
            e8 = sorted(range(1024), key=lambda s: (-float(scores[s]), s))[:8]
            w_e = torch.tensor([float(scores[s]) for s in e8]).softmax(-1).tolist()
            in_c = [s // 256 in branches[r] for s in e8]
            cr8.append(sum(in_c) / 8)
            cr1.append(float(in_c[0]))
            sr8.append(len(set(ids[r]) & set(e8)) / 8)
            am_c.append(sum(w for w, c in zip(w_e, in_c, strict=True) if c))
            am_s.append(sum(w for w, s in zip(w_e, e8, strict=True) if s in ids[r]))
        got = res[name]["facts"]
        for key, want in (("cr8", cr8), ("cr1", cr1), ("sr8", sr8), ("am_c", am_c), ("am_s", am_s)):
            assert got[key] == pytest.approx(sum(want) / len(want), abs=1e-5), (name, key)
    # T2 is exact search: it selects exactly E8 (no prior), so SR8 = AM_S = 1; T3 and T2 score every key: CR8 = CR1 = AM_C = 1
    assert res["T2"]["facts"]["sr8"] == pytest.approx(1.0) and res["T2"]["facts"]["am_s"] == pytest.approx(1.0)
    assert res["T3"]["facts"]["cr8"] == 1.0 and res["T3"]["facts"]["cr1"] == 1.0 and res["T3"]["facts"]["am_c"] == pytest.approx(1.0)
    assert 0.0 <= res["T0"]["facts"]["share_span_both"] <= 1.0


def test_pair_statistics_and_testability_against_loops() -> None:
    mem = tiny.tree_memory(4, 938441)
    codes = tiny.unit_queries(40, 938442)
    res = reads.tree_fact_pass(mem, codes, reads.tree_read_specs(1024, CFG), chunk_elements=CHUNK, chunk=16)
    t0 = reads.tree_path(mem.keys, mem.router, codes, 2, True, True, per=256, chunk_elements=CHUNK)
    t1 = reads.tree_path(mem.keys, mem.router, codes, 2, False, False, per=256, chunk_elements=CHUNK)
    changed, tvs = [], []
    for r in range(codes.shape[0]):
        a, b = t0.ids[r, :8].tolist(), t1.ids[r, :8].tolist()
        wa = dict(zip(a, t0.values[r, :8].softmax(-1).tolist(), strict=True))
        wb = dict(zip(b, t1.values[r, :8].softmax(-1).tolist(), strict=True))
        changed.append(float(set(a) != set(b)))
        tvs.append(0.5 * sum(abs(wa.get(s, 0.0) - wb.get(s, 0.0)) for s in set(a) | set(b)))
    assert res["T1"]["pair"]["against"] == "T0"
    assert res["T1"]["pair"]["share_selected_changed"] == pytest.approx(sum(changed) / len(changed))
    assert res["T1"]["pair"]["tv_mean"] == pytest.approx(sum(tvs) / len(tvs), abs=1e-5)
    assert res["T2"]["pair"]["against"] == "T3" and res["T3"]["pair"]["against"] == "T0"
    assert "pair" not in res["T0"]
    # at 1,024 slots the router visits two of four branches: T3 sees more keys, so T3's selection differs from T0's wherever a visited-less key wins


def test_index_fact_measures_against_loops_and_f0_is_exact() -> None:
    mem = tiny.flat_memory(1024, 938451)
    codes = tiny.unit_queries(48, 938452)
    idx = s1index.build_index(mem.keys.detach(), 938901, 16)
    res = reads.flat_fact_pass(mem, codes, {"I64@128/s938901": (idx, 128)}, chunk=16)
    f0 = res["F0"]["facts"]
    assert f0["cr8"] == f0["cr1"] == f0["sr8"] == 1.0 and f0["am_c"] == pytest.approx(1.0) and f0["am_s"] == pytest.approx(1.0)
    keys = F.normalize(mem.keys.double(), dim=-1)
    mask, counts = s1index.candidate_mask(idx, codes, 128)
    cr8, am = [], []
    for r, row in enumerate(codes.double()):
        scores = (keys @ row) / 0.2
        e8 = sorted(range(1024), key=lambda s: (-float(scores[s]), s))[:8]
        w_e = torch.tensor([float(scores[s]) for s in e8]).softmax(-1).tolist()
        cr8.append(sum(bool(mask[r, s]) for s in e8) / 8)
        am.append(sum(w for w, s in zip(w_e, e8, strict=True) if bool(mask[r, s])))
    got = res["I64@128/s938901"]
    assert got["facts"]["cr8"] == pytest.approx(sum(cr8) / len(cr8), abs=1e-5) and got["facts"]["am_c"] == pytest.approx(sum(am) / len(am), abs=1e-5)
    # for an index read of the flat memory there is no prior: SR8 = CR8 and AM_S = AM_C (the selection is the top 8 of the candidates)
    assert got["facts"]["sr8"] == pytest.approx(got["facts"]["cr8"], abs=1e-6) and got["facts"]["am_s"] == pytest.approx(got["facts"]["am_c"], abs=1e-6)
    assert got["candidates_facts"]["mean"] == pytest.approx(float(counts.float().mean()))
    assert got["candidates_facts"]["p99"] == pytest.approx(float(torch.quantile(counts.float(), 0.99)))
    assert got["candidates_facts"]["mean"] >= 128


# --- the end-task counts through P10-S1's own functions -------------------------------------------------------------------------------------------
def test_read_counts_reproduce_p10s1_read_record_for_t0_f0_and_i256_and_t0_path_is_verified() -> None:
    """The in-test analogue of gate 2 on a tiny model: T0 through the common path, F0 and I256@512 give the counts of P10-S1's ``_read_record`` for the same model, and every query of T0's Panel A and B
    passes (main and address-swap reads) was checked against ``S1Memory._top_tree``."""
    seeds = core.test_seeds(0)
    data = tiny.data(0)
    facts = tiny.FACTS
    tree = tiny.model("T-OQ", 1024)
    flat = tiny.model("F-OQ", 1024)
    for model in (tree, flat):
        with torch.no_grad():  # make the memory read-sensitive: random unit keys (an untrained init is N(0, 0.02) and works too, this only spreads the scores)
            model.addition.keys.copy_(F.normalize(torch.randn(model.addition.keys.shape, generator=torch.Generator().manual_seed(938461)), dim=-1))
    ref_tree = s1eval._read_record(tree, data, facts, seeds, deep=False, robustness=False)
    t0 = reads.TreeReadMemory(tree.addition, reads.TreeReadSpec("T0", 2, True, True), verify=True)
    with reads.swapped_addition(tree, t0):
        mine = reads.read_counts(tree, data, facts, seeds)
    assert t0.checked > 0 and t0.mismatched == 0
    for p in "AB":
        for k in ("n", "correct", "useful"):
            assert mine["panels"][p][k] == ref_tree["panels"][p][k], (p, k)
    assert mine["work"]["K"] == ref_tree["work"]["K"]
    assert isinstance(tree.addition, S1Memory) and tree.addition is not t0  # the checkpoint's own memory is restored
    ref_flat = s1eval._read_record(flat, data, facts, seeds, deep=False, robustness=False)
    got_flat = reads.read_counts(flat, data, facts, seeds)
    assert all(got_flat["panels"][p][k] == ref_flat["panels"][p][k] for p in "AB" for k in ("n", "correct", "useful"))
    ivf, idx = s1eval.ivf_model(flat, seeds)
    ref_ivf = s1eval._read_record(ivf, data, facts, seeds, deep=False, robustness=False)
    got_ivf = reads.read_counts(ivf, data, facts, seeds)
    assert all(got_ivf["panels"][p][k] == ref_ivf["panels"][p][k] for p in "AB" for k in ("n", "correct", "useful"))
    # the recall quantity of P10-S1's index read is the one measured in the Panel A pass; the gate consumes it, the record drops it
    assert got_ivf["measured"]["recall_of_exhaustive_top8"] == ref_ivf["ivf_measured"]["recall_of_exhaustive_top8"]
    rec = reads.read_record("A1", "cell", 8192, "I256@512", got_ivf)
    assert "recall_of_exhaustive_top8" not in str(rec) and set(rec["candidates"]) == {"mean", "p99"}
    assert idx.sha256() == s1eval.ivf_model(flat, seeds)[1].sha256()
    assert s1core.bits_per_fact(got_flat["panels"]["A"]["useful"], got_flat["panels"]["A"]["n"]) == got_flat["panels"]["A"]["i"]


def test_the_i_of_every_read_is_p10s1s_bits_per_fact_of_the_useful_count() -> None:
    seeds = core.test_seeds(0)
    model = tiny.model("T-OQ", 1024)
    t3 = reads.TreeReadMemory(model.addition, reads.TreeReadSpec("T3", None, True, True))
    with reads.swapped_addition(model, t3):
        c = reads.read_counts(model, tiny.data(0), tiny.FACTS, seeds)
    for p in "AB":
        assert c["panels"][p]["i"] == s1core.bits_per_fact(c["panels"][p]["useful"], c["panels"][p]["n"])
        assert c["panels"][p]["a_use"] == c["panels"][p]["useful"] / c["panels"][p]["n"]
    assert c["work"]["K"] == 4 + 4 * 256  # N/256 router scores plus every key of every branch


def test_read_sets_per_slot_count() -> None:
    names_1024 = [s.name for s in reads.tree_read_specs(1024, CFG)]
    assert names_1024 == ["T0", "T1", "T1w", "T3", "T2", "Tv1_on", "Tv1_off"]  # 4 branches: v = 1, 2 (= T0 / T1), 4 (= T3 / T2); v = 8 does not exist
    names_4096 = [s.name for s in reads.tree_read_specs(4096, CFG)]
    assert names_4096 == ["T0", "T1", "T1w", "T3", "T2", "Tv1_on", "Tv1_off", "Tv4_on", "Tv4_off", "Tv8_on", "Tv8_off"]
    assert [s.name for s in reads.tree_read_specs(16384, CFG)] == names_4096
    assert all(core.is_read_name(n) for n in names_4096)
    assert core.feasible_budgets(1024, CFG) == [128, 256, 512] and core.feasible_budgets(4096, CFG) == [128, 256, 512, 1024, 2048] and core.feasible_visits(1024, CFG) == [1, 2, 4]
