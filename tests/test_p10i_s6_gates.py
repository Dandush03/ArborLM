# ruff: noqa: E501
"""P10IS6 gates (ADR-0031 sections 14, 16): the seed gate against an injected checker and own-value checks, read equality, BASE gate, the config equals the specification. Self-check only."""

import copy
import shutil
from typing import Any

from arborlm.io import file_sha256
from studies.p10i_s6 import core, gates, testing

CFG = core.load_config()


def test_every_threshold_in_the_config_equals_the_specification() -> None:
    t, c, r = CFG["thresholds"], CFG["convergence"], CFG["rates"]
    assert (t["effect"], t["min_cells"], t["min_parents"], t["cells"], t["parents"], t["half"], t["dense_share"], t["dense_floor"], t["dense_tolerance"], t["tolerance_neg_ref"], t["trend_delta"]) == (0.005, 22, 8, 27, 9, 0.5, 0.90, 0.005, -0.005, 1e-6, 0.005)
    assert c["epsilon"] == 0.001 and r["tie_tolerance"] == 0.0005
    assert r["grid"] == [0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1] and r["extension_down"] == [0.00003, 0.00001, 0.000003, 0.000001] and r["extension_up"] == [0.3, 1.0]
    assert (r["max_extensions_down"], r["max_extensions_up"]) == (4, 2)
    assert (CFG["ladder"]["base_updates"], CFG["ladder"]["rungs"], CFG["ladder"]["below_updates"], CFG["ladder"]["parent_updates"]) == (16384, 5, 8192, 1024)
    assert CFG["setting"]["panel_chunks"] == 512 and CFG["setting"]["val_targets"] == 32768 and CFG["controls"]["p_used_draws"] == 4 and CFG["data"]["pool_chunks_for_umax"] == 2097152
    assert (CFG["caps"]["d0_p0_hours"], CFG["caps"]["rehearsal_hours"], CFG["caps"]["registered_hours_bound"]) == (2.0, 16.0, 40.0)
    assert CFG["data"]["revision"] == "b08601e04326c79dfdd32d625aee71d232d685c3" and CFG["data"]["download_hard_stop_bytes"] == 10**9 and CFG["data"]["download_expected_bytes"] == 315466397


def test_seed_values_are_section_14_and_registry_r4() -> None:
    s = CFG["seeds"]
    reg, oa, cal, dry = (core.Seeds(p, CFG) for p in ("registered", "oa", "calibration", "dry"))
    assert [reg.stream(c) for c in (0, 26)] == [320001, 320027] and [oa.stream(c) for c in (0, 26)] == [320101, 320127]
    assert reg.p_used(0, 0) == 320201 and reg.p_used(26, 3) == 320308 and cal.p_used(2, 3) == 329042 and cal.stream(2) == 329003
    assert reg.init(26) == 330727 and oa.init(4) == 330732 and cal.init(2) == 330791 and dry.init(0) == 330792 and dry.stream(0) == 329201 and [dry.p_used(0, j) for j in range(4)] == [329231, 329232, 329233, 329234]
    assert s["init_planted_toy"] == 330793 and (s["held_dry_backbone"], s["held_dry_order"], s["held_dry_oa_stream"]) == (330794, 329211, 329202)
    assert s["order_registered"] == list(range(321001, 321010)) and s["order_calibration"] == [321091, 321092, 321093] and s["backbone_registered"] == list(range(330741, 330750)) and s["backbone_calibration"] == [330751, 330752, 330753]
    assert gates.seed_problems(CFG) == []


def test_no_data_seed_is_expanded_by_plus_1000k() -> None:
    p = gates.planned_seed_values(CFG)
    data = frozenset().union(*(p[k] for k in ("registered_streams", "oa_streams", "registered_p_used", "orders", "calibration_streams", "calibration_p_used", "dry", "held")))
    inits = p["init"] | p["oa_init"] | p["backbones"] | p["init_other"]
    assert not ({i + 1000 * k for i in inits for k in range(1, 11)} & data) and not ({d + 1000 * k for d in data for k in range(1, 11)} & inits)


def test_seed_problems_catch_each_planted_fault() -> None:
    def with_seeds(**kw: Any) -> dict[str, Any]:
        cfg = copy.deepcopy(dict(CFG))
        cfg["seeds"] = {**CFG["seeds"], **kw}
        return cfg

    assert any("outside" in x for x in gates.seed_problems(with_seeds(stream_base=330001)))
    assert any("share" in x for x in gates.seed_problems(with_seeds(oa_stream_base=320001)))  # overlaps the registered streams
    # an initialisation value 1,000 below a data seed: its component seed (+ 1000) lands on the data seed
    assert any("component seed" in x and "collides" in x for x in gates.seed_problems(with_seeds(init_calibration=329201 - 1000)))
    # a data seed 1,000 below an initialisation value: derivation by arithmetic
    assert any("derivation by arithmetic" in x for x in gates.seed_problems(with_seeds(dry_stream=330791 - 1000)))
    assert not any("derivation" in x or "component seed" in x for x in gates.seed_problems(CFG))


def make_root(d: Any, *, pass_checker: bool = True, rows: bool = True) -> Any:
    """A throw-away copy of the two registry files and an injected checker: no dependence on the repository's planning state or on sibling studies' files."""
    rel = "docs/reviews/p10-i-direction-2026-11-17"
    (d / rel).mkdir(parents=True)
    shutil.copy(core.repo_root() / rel / "SEED_REGISTRY_R4.md", d / rel / "SEED_REGISTRY_R4.md")
    row_text = "".join(f'    ("P10-I-S6 ADR-0031", "r{i}", {lo}, {hi}),\n' for i, (lo, hi) in enumerate([(320001, 329299), (330701, 330799), (952001, 952999)])) if rows else ""
    other = '    ("P10-I-S3 ADR-0026", "registered", 260001, 266999),\n'
    script = f'ALLOC = [\n{other}{row_text}]\nimport sys\nprint("args", sys.argv[1:])\nprint("RESULT: {"PASS" if pass_checker else "FAIL"}")\nraise SystemExit({0 if pass_checker else 1})\n'
    path = d / "checker.py"
    path.write_text(script, encoding="utf-8")
    return path


def test_seed_gate_with_an_injected_checker() -> None:
    root = core.repo_root()
    cfg = copy.deepcopy(dict(CFG))
    with testing.scratch("seedgate") as d:
        ck = make_root(d)
        ok = gates.seed_gate(cfg, root=d, checker_path=ck)
        assert ok["passed"] is True and ok["checker"]["result_line"] == "RESULT: PASS" and ok["checker"]["own_allocation_rows"] == 3 and ok["checker"]["own_globs"] == CFG["seed_ranges"]["own_globs"]
    with testing.scratch("seedgate2") as d:
        ck = make_root(d, pass_checker=False)
        bad = gates.seed_gate(cfg, root=d, checker_path=ck)
        assert bad["passed"] is False and any("RESULT: PASS" in p for p in bad["problems"])  # a hit on this study's allocation (the checker decides) fails
    with testing.scratch("seedgate3") as d:
        ck = make_root(d, rows=False)
        assert any("no allocation row" in p for p in gates.seed_gate(cfg, root=d, checker_path=ck)["problems"])
    with testing.scratch("seedgate4") as d:
        ck = make_root(d)
        (d / CFG["seed_ranges"]["addendum"]).write_text("changed", encoding="utf-8")
        assert any("addendum" in p for p in gates.seed_gate(cfg, root=d, checker_path=ck)["problems"])
    assert file_sha256(root / CFG["seed_ranges"]["checker"]) == CFG["seed_ranges"]["checker_sha256"]  # the cited checker is the one in the tree


def test_read_equality_and_base_gate() -> None:
    g = gates.read_equality_gate(core.Seeds("dry", CFG).init(0), CFG)
    assert g["passed"] is True and set(g["items"]) == {"flat_no_intervention", "dense_no_intervention"}
    assert gates.base_gate({"a": (1.0, 1.0, 1.0)}, bitwise=True)["passed"] is True
    assert gates.base_gate({"a": (1.0, 1.0, 1.0 + 1e-9)}, bitwise=True)["passed"] is False  # bitwise on the platform of record
    assert gates.base_gate({"a": (1.0, 1.0, 1.0 + 1e-9)}, bitwise=False)["passed"] is True


def test_rehearsal_gate() -> None:
    rec = {"caps_provisional": False, "stages": {"R1": {"status": "COMPLETE"}, "R2": {"status": "COMPLETE"}, "R3": {"status": "COMPLETE"}}, "candidate": {"plan_file_sha256": "ab"}}
    assert gates.rehearsal_gate(rec, ("R1", "R2", "R3"), plan_file_sha256="ab")["passed"] is True
    assert gates.rehearsal_gate(rec, ("R1", "R2", "R3"), plan_file_sha256="cd")["passed"] is False
    assert gates.rehearsal_gate({**rec, "caps_provisional": True}, ("R1",))["passed"] is False
    assert gates.rehearsal_gate(None, ("R1",))["passed"] is False
