# ruff: noqa: E501
"""P10IS6: the audit's required findings and the lead's rulings 1-13 of the addendum, one test each (ADR-0031 addendum; audit R1-R3, A1-A13), and the strengthened oracle (A5). Self-check only."""

import random
from typing import Any

import pytest
import torch

from studies.p10i_s6 import analysis, calibration, core, items, labels, model, synthetic, testing
from studies.p10i_s6.core import DENSE, FLAT, EngineeringStop
from studies.p10i_s6.synthetic import ArmSpec, Spec

CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
RT = synthetic.rate_table(4)
RT_SHARED = synthetic.rate_table(4, shared=True)


def gains(start: float, deltas: list[float]) -> dict[int, float]:
    g = {-1: start}
    for k, d in enumerate(deltas):
        g[k] = g[k - 1] + d
    return g


def spec(lead: float = 0.02, d_deltas: list[float] | None = None, **kw: Any) -> Spec:
    dd = d_deltas or [0.0005] * 5
    gd = gains(0.10, dd)
    gf = {k: v + lead for k, v in gd.items()}
    return Spec(ArmSpec(gf, {k: dd[k] for k in range(5)}), ArmSpec(gd, {k: dd[k] for k in range(5)}), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08, **kw)


def run(sp: Spec, *, shared: bool = False) -> dict[str, Any]:
    sp.shared = shared
    return analysis.analyse(synthetic.registry(CFG, sp), RT_SHARED if shared else RT, CFG, k_max=4, bitwise=True)


# ---- audit R1 + ruling 1
@pytest.mark.parametrize("kw,row,why", [({"failed": frozenset({(FLAT, 4, 0)})}, 2, "M-FLAT failed cell"), ({"failed": frozenset({(DENSE, 4, 0)})}, 1, "D-ADAPT failed cell (cause 3)"), ({"base_nonfinite": frozenset({1})}, 1, "cause 1"), ({"bad_disabled": frozenset({(FLAT, 2, 5)})}, 1, "cause 2")])
def test_r16_is_not_evaluable_beside_a_failure_label(kw: dict[str, Any], row: int, why: str) -> None:
    res = run(spec(**kw))
    assert res["line_p"]["row"] == row and res["r16"]["label"] == "NOT EVALUABLE", why  # the auditor's concrete inputs: lead +0.02, both arms converging, one failed cell
    assert "REPLICATED" not in res["r16"]["label"] and res["trend"]["tag"] == "TREND NOT DETERMINED"
    assert "REPLICATED AT 16,384" not in str(res["line_p"]["label"])


def test_r16_under_cause_4_alone_is_computed_by_its_own_rule() -> None:
    # the dense run still improves along its own curve at rung 4 (so R = 4) while its gain has fallen to 0.003 there (Cd(4) < 0.005: cause 4), but at rung 0 Cd(0) = 0.02 and Q(0) = 0.02
    gd = {-1: 0.0, 0: 0.02, 1: 0.015, 2: 0.01, 3: 0.006, 4: 0.003}
    gf = {k: v + 0.02 for k, v in gd.items()}
    sp = Spec(ArmSpec(gf, {k: 0.0005 for k in range(5)}), ArmSpec(gd, {0: 0.0005, 1: 0.0005, 2: 0.0005, 3: 0.0005, 4: 0.02}), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08)
    res = run(sp)
    assert res["line_p"]["cause_ids"] == [4] and res["line_p"]["row"] == 1 and res["reading_rung"] == 4
    assert res["r16"]["label"] == "REPLICATED AT 16,384"  # cause 4 is neither an integrity state nor a failed-cell state; R16 reads rung 0 only


# ---- audit R2 + ruling 7
def test_calibration_not_interior_is_raised_by_the_rate_table() -> None:
    import math

    u = [core.rung_updates(CFG, k) for k in range(-1, 3)]
    grid = [float(x) for x in CFG["rates"]["grid"]] + [float(x) for x in CFG["rates"]["extension_up"]]  # extended to the maximum, minimiser still at the top
    curves = {a: {r: {c: {d: 3.0 - 0.01 * math.log10(r) for d in u} for c in range(3)} for r in grid} for a in core.ARMS}
    with pytest.raises(EngineeringStop, match="CALIBRATION NOT INTERIOR"):
        calibration.rate_table(curves, CFG, 2)


# ---- audit R3 + ruling 8
def test_integrity_equalities_are_exact_on_every_platform() -> None:
    reg = synthetic.registry(CFG, spec())
    key = core.nll_key(FLAT, synthetic.RATES_FLAT[2], 4, core.rung_updates(CFG, 2), core.READ_REPLAY)
    reg[key] = reg[key] + 1e-9  # far below 1e-6
    for bitwise in (True, False):
        res = analysis.analyse(reg, RT, CFG, k_max=4, bitwise=bitwise)
        assert res["line_p"]["row"] == 1 and 2 in res["line_p"]["cause_ids"]
    import inspect

    from studies.p10i_s6 import stages

    assert "1e-6" not in inspect.getsource(analysis._eq) and "bitwise = True" in inspect.getsource(stages.run_analysis)


# ---- ruling 2 (L2)
def test_one_undefined_intervention_fails_the_whole_condition() -> None:
    col = spec(used_slots=lambda k, c: 1 if c == 4 else 300)
    r = run(col)
    f2 = r["d_flat"]["conditions"]["F2"]
    assert f2["mean"] is None and f2["ok"] is False and r["d_flat"]["collapsed"] == [4]  # no mean over fewer cells
    nf = spec(nonfinite_xmean=frozenset({(0, 7)}))
    f3 = run(nf)["d_flat"]["conditions"]["F3"]
    assert f3["mean"] is None and f3["ok"] is False and run(nf)["d_flat"]["label"] == "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE"
    nd = spec(nonfinite_draw=frozenset({(0, 3)}))
    assert run(nd)["d_flat"]["conditions"]["F2"]["mean"] is None


# ---- ruling 3 (L3, audit A1)
def test_missing_base_and_missing_used_slots_are_incomplete_registry() -> None:
    with pytest.raises(EngineeringStop, match="INCOMPLETE REGISTRY: no BASE record"):
        run(spec(base_missing=frozenset({2})))
    with pytest.raises(EngineeringStop, match="INCOMPLETE REGISTRY: no used_slots"):
        run(spec(slots_missing=frozenset({(0, 3)})))
    res = run(spec(base_nonfinite=frozenset({2})))
    assert res["line_p"]["row"] == 1 and res["line_p"]["cause_ids"][0] == 1  # present but not finite: NOT EVALUABLE, cause 1


# ---- ruling 10 (A2, A3)
def test_non_finite_replay_is_not_evaluable_not_a_failed_cell_for_both_arms() -> None:
    for arm in (FLAT, DENSE):
        res = run(spec(nonfinite_replay=frozenset({(arm, 1, 3)})))
        assert res["line_p"]["row"] == 1 and res["line_p"]["cause_ids"] == [2] and res["flat_failed"] is False and res["dense_failed"] is False


def test_non_finite_enabled_makes_l_not_determined_at_every_rung_the_run_serves() -> None:
    sp = spec(nonfinite_enabled=frozenset({(FLAT, 2, 5)}))
    shared = run(sp, shared=True)  # one run serves rungs -1..4
    for k in range(5):
        assert shared["per_rung"][str(k)]["L"][FLAT] is None and shared["per_rung"][str(k)]["convergence"][FLAT] == "NOT DETERMINED"
    assert shared["rung_minus_one"][FLAT]["L"] is None and shared["line_p"]["row"] == 2 and shared["d_flat"]["label"] == "NOT EVALUABLE"
    distinct = run(sp)  # a distinct rate per rung: only the run of rung 2 is affected (plus the deltas that read its L)
    assert [distinct["per_rung"][str(k)]["L"][FLAT] is None for k in range(5)] == [False, False, True, False, False]
    text = __import__("studies.p10i_s6.printing.report", fromlist=["render"]).render(shared, "test")
    assert "n/a" in text and "PERSISTS" not in text.split("## Per rung")[0].split("Line P (registered)")[1][:200]


# ---- ruling 11 (A4)
def test_snapshot_comparison_is_bytewise() -> None:
    z, nz = torch.tensor([0.0]), torch.tensor([-0.0])
    assert torch.equal(z, nz) and not model.bytes_equal(z, nz)
    assert model.bytes_equal(z.clone(), z) and not model.bytes_equal(z, torch.tensor([0.0], dtype=torch.float64))
    nan = torch.tensor([float("nan")])
    assert model.bytes_equal(nan, nan.clone()) and not model.bytes_equal(torch.zeros(2), torch.zeros(3))
    base = testing.synthetic_backbone()
    m = model.build_model(base, FLAT, core.Seeds("test", CFG).init(0))
    with testing.scratch("bytes") as d:
        model.save_snapshot(d / "a", m, None, 1, {"i": 1})
        with torch.no_grad():
            m.addition.wo.view(-1)[0] = 0.0  # type: ignore[union-attr]
            m.addition.wo.view(-1)[1] = 0.0  # type: ignore[union-attr]
        model.save_snapshot(d / "b", m, None, 1, {"i": 1})
        with torch.no_grad():
            m.addition.wo.view(-1)[1] = -0.0  # type: ignore[union-attr]
        model.save_snapshot(d / "c", m, None, 1, {"i": 1})
        assert model.snapshots_equal(d / "b", 1, d / "b", 1) and not model.snapshots_equal(d / "b", 1, d / "c", 1)  # a value comparison would call these equal


# ---- ruling 12
def test_test_seeds_the_planted_toy_value_and_no_control_memory() -> None:
    lo, hi = CFG["seeds"]["test_range"]
    for k in range(3):
        assert lo <= core.test_seed(700 + k, CFG) <= hi
    import inspect

    assert "init_planted_toy" in inspect.getsource(model.planted_positive)
    from studies.p10i_s6 import parents

    bb = parents.untrained_backbone(core.test_seed(701, CFG))
    assert sum(p.numel() for p in bb.parameters()) == 27392


# ---- ruling 13
def test_descriptive_output_of_section_12_5_is_complete_and_a_partial_directory_is_kept_aside() -> None:
    cs = {a: {str(k): {"delta": 0.5, "delta_run": 0.5, "state": "NOT CONVERGED"} for k in range(5)} for a in core.ARMS}
    res = analysis.analyse(synthetic.registry(CFG, spec()), RT, CFG, k_max=4, bitwise=True, calibration_states=cs)
    pr = res["per_rung"]["2"]
    assert len(pr["delta_envelope_per_parent"][FLAT]) == 9 and pr["X_mean_dense"]["n"] == 27 and pr["delta_per_parent"][FLAT]
    m1 = res["rung_minus_one"][FLAT]
    assert m1["stats"]["n"] == 27 and len(m1["parent_means"]) == 9 and len(m1["cells"]) == 27
    assert res["calibration_vs_registered_states_that_differ"][f"{FLAT}|0"] == {"calibration": "NOT CONVERGED", "registered": "CONVERGED"}
    assert res["step0"] and res["harm"]["0"]["H_used"] is not None
    # a partial item directory is kept aside on restart and the attempt is logged
    cfg = {**dict(CFG), "ladder": {**CFG["ladder"], "base_updates": 2, "below_updates": 1}}
    table = testing.patterned_rows(300, core.test_seed(20, CFG)).to(torch.uint8)
    panel = testing.patterned_rows(4, core.test_seed(21, CFG))
    res_ = items.Resources(cfg, table, {"registered": (0, 200), "calibration": (200, 100)}, {"registered": panel, "calibration": panel}, lambda g, p: testing.synthetic_backbone(p), expected_targets=256, resume_ok=False)
    t = items.registered_items(cfg, synthetic.rate_table(2, shared=True), 2, cells=[0], with_oa=False)["train"][0]
    with testing.scratch("aside") as d, testing.scratch("pub") as pub:
        (pub / core.PAUSE_FILE).write_text("x")
        assert items.run_train(res_, t, d, pub)["status"] == "paused"
        before = sorted(p.name for p in items.item_dir(d, t["id"]).iterdir())
        (pub / core.PAUSE_FILE).unlink()
        out = items.run_train(res_, t, d, pub)
        kept = list((items.item_dir(d, t["id"]).parent / "_kept_aside").iterdir())
        assert out["status"] == "ok" and len(kept) == 1 and sorted(p.name for p in kept[0].iterdir()) == before and list((pub / "attempts").glob("*.json"))


def test_no_test_depends_on_the_directory_being_a_git_work_tree() -> None:
    """The ignored-path check is exercised against a throw-away repository, and outside any repository it passes by definition."""
    import subprocess
    import sys

    from studies.p10i_s6 import plan as planmod

    with testing.scratch("nogit") as d:
        planmod.require_ignored_path(d, d / "out" / "ledger.json")  # a directory that is not a repository: nothing to dirty
        r = d / "r"
        r.mkdir()
        for a in (["init", "-q"], ["config", "user.email", "t@e.invalid"]):
            subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)  # noqa: S603, S607
        (r / ".gitignore").write_text("/ign/\n")
        planmod.require_ignored_path(r, r / "ign" / "ledger.json")
        with pytest.raises(planmod.StageRefused, match="not git-ignored"):
            planmod.require_ignored_path(r, r / "src" / "ledger.json")
        planmod.require_ignored_path(r, __import__("pathlib").Path(sys.prefix) / "elsewhere")


# ---- audit A5: the strengthened oracle (all twelve rows, run sharing, builtin sum, its own key strings)
def okey(arm: str, rate: float, c: int, u: int, read: str, draw: int = 0) -> str:
    return f"nll|{arm}|r{rate:.6g}|c{c:02d}|u{u:06d}|{read}|d{draw}"


def oracle_row(reg: dict[str, Any], rt: dict[str, Any], k_max: int, n: int) -> tuple[int, str | None]:
    """Rows 1-12 of section 12.3 from the raw registry with this file's OWN key strings (independent of ``core``'s key functions), ``sum`` as ruling G5 says."""
    U = {k: 16384 * 2**k for k in range(0, k_max + 1)} | {-1: 8192}
    rate = {a: {int(k): float(v) for k, v in rt["rates"][a].items()} for a in (FLAT, DENSE)}
    rk = lambda a, k, c: f"run|{a}|r{rate[a][k]:.6g}|c{c:02d}"  # noqa: E731

    def val(a: str, k: int, c: int, u: int, read: str = "enabled", d: int = 0) -> float | None:
        v = reg[okey(a, rate[a][k], c, u, read, d)]
        return None if v is None else float(v)

    def mean(x: list[float]) -> float:
        return sum(x) / len(x)

    base = {p: (reg.get(f"base|p{p:02d}|enabled"), reg.get(f"base|p{p:02d}|replay")) for p in range(n // 3)}
    if any(k not in reg for p in range(n // 3) for k in (f"base|p{p:02d}|enabled", f"base|p{p:02d}|replay")):
        raise EngineeringStop("INCOMPLETE")
    cause1 = any(e is None or r is None or e != r for e, r in base.values())
    cause2 = cause3 = flat_failed = False
    bad_run: dict[tuple[str, int], bool] = {}
    L: dict[tuple[str, int], float | None] = {}
    prevm: dict[tuple[str, int], float | None] = {}
    for a in (FLAT, DENSE):
        for k in range(-1, k_max + 1):
            vals, prevs, bad = [], [], False
            for c in range(n):
                run_failed = reg[rk(a, k, c)]["status"] == "failed_cell"
                served = [j for j in range(-1, k_max + 1) if rate[a][j] == rate[a][k]]
                cell_bad = run_failed or any(val(a, j, c, U[j]) is None or (j >= 0 and val(a, j, c, U[j - 1]) is None) for j in served)
                bad = bad or cell_bad
                if run_failed or cell_bad:
                    continue
                vals.append(val(a, k, c, U[k]))
                prevs.append(val(a, k, c, U[k - 1]) if k >= 0 else None)
                b = base[c // 3][0]
                rep, dis = val(a, k, c, U[k], "replay"), val(a, k, c, U[k], "disabled")
                if rep is None or dis is None or b is None or rep != vals[-1] or dis != b:
                    cause2 = True
            bad_run[(a, k)] = bad
            L[(a, k)] = None if bad else mean(vals)  # type: ignore[arg-type]
            prevm[(a, k)] = None if bad or k < 0 else mean(prevs)  # type: ignore[arg-type]
    flat_failed = any(bad_run[(FLAT, k)] for k in range(-1, k_max + 1))
    cause3 = any(bad_run[(DENSE, k)] for k in range(-1, k_max + 1))
    eps = 0.001

    def conv(a: str, k: int) -> bool:
        if L[(a, k - 1)] is None or L[(a, k)] is None or prevm[(a, k)] is None:
            return False
        return (L[(a, k - 1)] - L[(a, k)] < eps) and (prevm[(a, k)] - L[(a, k)] < eps)  # type: ignore[operator]

    kstar = next((k for k in range(0, k_max + 1) if all(conv(a, j) for a in (FLAT, DENSE) for j in range(k, k_max + 1))), None)
    R = kstar if kstar is not None else k_max
    cause4 = False
    if not (cause1 or cause2 or cause3):
        cd = mean([base[c // 3][0] - val(DENSE, R, c, U[R]) for c in range(n)])  # type: ignore[operator]
        cause4 = cd < 0.005
    if cause1 or cause2 or cause3 or cause4:
        return 1, None
    if flat_failed:
        return 2, None
    lds = [L[(DENSE, k)] for k in range(0, k_max + 1)]
    jd = min(range(0, k_max + 1), key=lambda k: (lds[k], -k))  # type: ignore[arg-type,return-value]

    def cls(k: int) -> str:
        q = [val(DENSE, k, c, U[k]) - val(FLAT, k, c, U[k]) for c in range(n)]  # type: ignore[operator]
        qd = [val(DENSE, jd, c, U[jd]) - val(FLAT, k, c, U[k]) for c in range(n)]  # type: ignore[operator]

        def pm(x: list[float]) -> list[float]:
            return [mean(x[i : i + 3]) for i in range(0, n, 3)]

        def ahead(x: list[float]) -> bool:
            return mean(x) >= 0.005 and sum(1 for y in x if y > 0) >= 22 and sum(1 for y in pm(x) if y > 0) >= 8

        if ahead(q) and ahead(qd):
            return "M"
        if mean(q) <= -0.005 and sum(1 for y in q if y < 0) >= 22 and sum(1 for y in pm(q) if y < 0) >= 8:
            return "D"
        if -0.005 < mean(q) < 0.005:
            return "L"
        return "U"

    classes = {k: cls(k) for k in range(0, k_max + 1)}
    if kstar is not None:
        cs = [classes[k] for k in range(kstar, k_max + 1)]
        return (3, None) if len(set(cs)) > 1 else ({"M": 4, "L": 5, "D": 6, "U": 7}[cs[0]], None)
    cdn, cmm = conv(DENSE, k_max), conv(FLAT, k_max)
    if cdn and not cmm and classes[k_max] == "M":
        return 8, None
    if cmm and not cdn and classes[k_max] == "D":
        return 9, None
    if not cdn and cmm:
        return 10, None
    if cdn and not cmm:
        return 11, None
    return 12, None


def random_world(rng: random.Random, n: int = 27) -> tuple[Spec, bool]:
    """A random world: each arm converges (tiny deltas) from a random rung or never; the lead takes one of several shapes; faults are injected with small probabilities; half of the worlds share one run across rungs."""
    shared = rng.random() < 0.5

    def deltas(conv_from: int | None) -> list[float]:
        return [0.02 if (conv_from is None or k < conv_from) else rng.choice([0.0004, 0.0009, -0.003]) for k in range(5)]

    dd = deltas(rng.choice([None, 0, 1, 2, 3, 4]))
    fd = deltas(rng.choice([None, 0, 1, 2, 3, 4]))
    gd = gains(rng.choice([0.0, 0.03, 0.10]), dd)
    gf = gains(rng.choice([0.0, 0.03, 0.10]) + rng.choice([-0.03, 0.0, 0.02, 0.05]), fd)
    cell = {k: [rng.choice([0.0, 0.0, 0.0, 0.004, 0.012]) for _ in range(n)] for k in range(-1, 5)} if rng.random() < 0.3 else {}
    if rng.random() < 0.15:  # the UNDECIDED shape: mean lead 0.0056 >= 0.005 but only 21 of 27 cells positive (six cells, one in each of six parents, are at -0.001)
        dd = deltas(rng.choice([0, 1, 2]))
        gd = gains(0.10, dd)
        gf = {k: v + 0.0075 for k, v in gd.items()}
        cell = {k: [0.0085 if c in (0, 3, 6, 9, 12, 15) else 0.0 for c in range(n)] for k in range(-1, 5)}
    if shared:
        drd, drf = {k: gd[k] - gd[k - 1] for k in range(5)}, {k: gf[k] - gf[k - 1] for k in range(5)}
    else:
        drd, drf = {k: rng.choice([dd[k], 0.02, 0.0004]) for k in range(5)}, {k: rng.choice([fd[k], 0.02]) for k in range(5)}
    sp = Spec(ArmSpec(gf, drf, cell), ArmSpec(gd, drd), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08, shared=shared)
    if rng.random() < 0.08:
        sp.base_nonfinite = frozenset({rng.randrange(9)})
    if rng.random() < 0.06:
        sp.bad_disabled = frozenset({(rng.choice([FLAT, DENSE]), rng.randrange(-1, 5), rng.randrange(n))})
    if rng.random() < 0.06:
        sp.nonfinite_replay = frozenset({(rng.choice([FLAT, DENSE]), rng.randrange(-1, 5), rng.randrange(n))})
    if rng.random() < 0.06:
        sp.failed = frozenset({(DENSE, rng.randrange(-1, 5), rng.randrange(n))})
    if rng.random() < 0.08:
        sp.failed = sp.failed | frozenset({(FLAT, rng.randrange(-1, 5), rng.randrange(n))})
    if rng.random() < 0.05:
        sp.nonfinite_enabled = frozenset({(rng.choice([FLAT, DENSE]), rng.randrange(-1, 5), rng.randrange(n))})
    return sp, shared


def test_the_analysis_agrees_with_the_oracle_on_random_worlds_that_reach_every_row() -> None:
    rng = random.Random(core.test_seed(40, CFG))
    reached: set[int] = set()
    shared_seen = distinct_seen = 0
    for _ in range(400):
        sp, shared = random_world(rng)
        reg = synthetic.registry(CFG, sp)
        rt = RT_SHARED if shared else RT
        res = analysis.analyse(reg, rt, CFG, k_max=4, bitwise=True)
        row, _ = oracle_row(reg, rt, 4, 27)
        assert res["line_p"]["row"] == row, (res["line_p"]["label"], row)
        reached.add(row)
        shared_seen += shared
        distinct_seen += not shared
    assert reached == set(range(1, 13)), f"rows not reached: {sorted(set(range(1, 13)) - reached)}"
    assert shared_seen > 100 and distinct_seen > 100  # run sharing is exercised as often as distinct rates


def test_labels_module_is_importable_for_the_probe() -> None:
    assert labels.PERSISTS == "PERSISTS AT CONVERGENCE"
