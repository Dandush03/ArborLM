# ruff: noqa: E501
"""P10S2 fix lane A: the seed registry after the rulings on the implementation audits (A-M4 core half, A-M8): 220906 drawn in the analysis stage only, 220912 the equivalence injection's own seed,
G9's list 220901-220912, the strict gate (non-empty, stage mode, planned set), the +10 code seed recorded, the seed table with every replicate's seeds. All seeds are listed seeds checked as values or test
seeds (229001-229999). Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import core, text  # noqa: E402


def test_the_twelve_listed_partition_side_seeds_and_where_each_is_drawn() -> None:
    assert core.listed_partition_seeds() == {
        "partition": 220901, "q_split": 220902, "source_sample": 220903, "ablation_subsample": 220904, "gen_windows": 220905, "bootstrap": 220906, "seen_items": 220907, "timing_items": 220908,
        "tokenizer_record": 220909, "random_id_sequences": 220910, "c1_pairing": 220911, "equivalence_injection": 220912,
    }  # fmt: skip
    assert set(core.PARTITION_USES) == set(core.listed_partition_seeds())  # every listed seed has its listed use
    data_step = core.partition_seeds("registered-data")
    assert len(data_step) == 11 and 220906 not in data_step.values() and data_step["equivalence_injection"] == 220912 != data_step["random_id_sequences"]
    assert core.partition_seeds("registered-analysis") == {"bootstrap": 220906} and core.ANALYSIS_STREAMS == ("bootstrap",)
    assert len(set(core.partition_seeds("test").values())) == 12 and all(229001 <= s <= 229999 for s in core.partition_seeds("test").values())
    assert core.listed_registered_seeds() >= set(range(220901, 220913))


def test_220906_is_drawn_in_the_analysis_stage_only() -> None:
    core.reset_seed_record()
    with pytest.raises(core.SeedRefused, match="not in the set"):
        core.seeded_generator(220906, "bootstrap in the data step", "registered-data")
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220906, "bootstrap in the run", "registered-run")
    with pytest.raises(core.SeedRefused, match="not drawn in mode"):
        core.partition_gen("registered-analysis", "q_split")  # no other partition-side stream in the analysis stage
    with pytest.raises(core.SeedRefused, match="not drawn in mode"):
        core.partition_gen("registered-data", "bootstrap")
    g1 = core.bootstrap_generator("registered-analysis", "A:ST1")
    g2 = core.bootstrap_generator("registered-analysis", "B:ST1")
    assert torch.equal(torch.randint(0, 100, (5,), generator=g1), torch.randint(0, 100, (5,), generator=g2))  # a fresh generator per printed interval
    assert [(u.seed, u.mode, u.purpose) for u in core.seed_record()] == [(220906, "registered-analysis", "bootstrap interval A:ST1"), (220906, "registered-analysis", "bootstrap interval B:ST1")]
    lo, hi = text.bootstrap_interval([0.1, 0.5, 0.9, 0.3], core.bootstrap_generator("test", "x"), resamples=50)
    assert 0.0 <= lo <= hi <= 1.0
    assert core.seed_gate(core.seed_record()[:2], [220906], planned_mode="registered-analysis", stage_mode="registered-analysis", allow_partial=False)["ok"]
    core.reset_seed_record()
    # the data step cannot use any of the listed seeds outside its mode: a run-mode use of a data-step seed is refused
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220912, "injection vector in the run", "registered-run")
    core.seeded_generator(220912, "injection vector", "registered-data")
    core.reset_seed_record()


def test_the_strict_gate_is_not_vacuous_and_checks_the_stage_mode_and_the_planned_set() -> None:
    plan = core.SeedPlan("test", 0)
    planned = core.planned_seeds("test", 1)
    assert planned == sorted(plan.planned()) and len(core.planned_seeds("registered-run")) == 44 and len(core.planned_seeds("registered-run", 2)) == 22  # all replicates, not replicate 0 only
    assert len(core.planned_seeds("registered-data")) == 11 and core.planned_seeds("registered-analysis") == [220906]
    # an empty record passes the old gate and fails the strict one
    assert core.seed_gate([], planned, planned_mode="test")["ok"]
    empty = core.seed_gate([], planned, planned_mode="test", stage_mode="test")
    assert not empty["ok"] and any("record is empty" in p for p in empty["problems"])
    # a test or rehearsal use inside a registered process
    reg_planned = core.planned_seeds("registered-run", 1)
    uses = [core.SeedUse(s, "use", "registered-run") for s in reg_planned]
    assert core.seed_gate(uses, reg_planned, planned_mode="registered-run", stage_mode="registered-run")["ok"]
    smuggled = [*uses, core.SeedUse(229001, "a test use next to a registered one", "test")]
    r = core.seed_gate(smuggled, reg_planned, planned_mode="registered-run", stage_mode="registered-run")
    assert not r["ok"] and any("carries mode 'test'" in p for p in r["problems"]) and any("not planned" in p for p in r["problems"])
    assert core.seed_gate(smuggled, reg_planned, planned_mode="registered-run")["ok"] is True  # the earlier, weaker call is what let it through
    rehearsal = [core.SeedUse(222001, "a rehearsal use", "rehearsal")]
    assert not core.seed_gate(rehearsal, [222001], planned_mode="rehearsal", stage_mode="registered-run")["ok"]
    # the planned set must equal the recorded set
    partial = core.seed_gate(uses[:5], reg_planned, planned_mode="registered-run", stage_mode="registered-run")
    assert not partial["ok"] and any("never recorded" in p for p in partial["problems"])
    assert core.seed_gate(uses[:5], reg_planned, planned_mode="registered-run", stage_mode="registered-run", allow_partial=True)["ok"]
    assert not core.seed_gate(uses, [], planned_mode="registered-run", stage_mode="registered-run")["ok"]  # no planned set given
    # a data-step seed that is drawn in the analysis stage only
    bad = core.seed_gate([core.SeedUse(220906, "bootstrap in the data step", "registered-data")], core.planned_seeds("registered-data"), planned_mode="registered-data", stage_mode="registered-data")
    assert not bad["ok"] and any("analysis stage only" in p for p in bad["problems"])
    ok = core.seed_gate([core.SeedUse(s, "d", "registered-data") for s in core.planned_seeds("registered-data")], core.planned_seeds("registered-data"), planned_mode="registered-data", stage_mode="registered-data")
    assert ok["ok"], ok["problems"]
    for s in (220001, 220101, 220201, 220301):  # replicate bases are not in the data step's set
        assert s not in core.planned_seeds("registered-data")


def test_the_code_seed_use_is_recorded_so_that_g9_sees_it() -> None:
    core.reset_seed_record()
    plan = core.SeedPlan("test", 1)
    seed = plan.code_seed()
    uses = core.seed_record()
    assert seed == plan.seed(10) and [(u.seed, u.kind, u.mode, u.purpose) for u in uses] == [(seed, "code-hash", "test", "oracle-code hash")]
    assert core.seed_gate(uses, [seed], planned_mode="test", stage_mode="test")["ok"]
    with pytest.raises(core.SeedRefused):
        core.record_code_seed_use(220001 + 10, "a registered code seed in test mode", "test")
    core.record_code_seed_use(220001 + 10, "registered code seed", "registered-run")
    assert core.seed_record()[-1].kind == "code-hash" and core.seed_gate(core.seed_record()[-1:], [220011], planned_mode="registered-run", stage_mode="registered-run")["ok"]
    core.reset_seed_record()


def test_the_seed_table_holds_every_replicates_seeds_the_code_seed_and_the_partition_side_seeds() -> None:
    rows = core.seed_table()
    assert len(rows) == 4 * 11 + 12
    seeds = [r["seed"] for r in rows]
    assert len(set(seeds)) == len(seeds) == 56
    for base in (220001, 220101, 220201, 220301):
        assert all(base + o in seeds for o in range(11))
    code = [r for r in rows if r["use"] == "oracle-code hash"]
    assert [r["seed"] for r in code] == [220011, 220111, 220211, 220311] and all(r["draws_generator"] is False for r in code)
    by = {r["name"]: r for r in rows}
    assert by["bootstrap"]["stage"] == "analysis (only)" and by["equivalence_injection"]["seed"] == 220912 and by["timing_items"]["stage"] == "data generation and partition"
    assert by["bootstrap"]["use"].startswith("the bootstrap resampling of every printed interval: drawn in the ANALYSIS STAGE ONLY")
    assert core.seed_gate([], [r["seed"] for r in rows], planned_mode="registered-run")["ok"]  # every table row is a listed registered seed, in range, and disjoint from the other studies


def test_a_listed_seed_serves_only_its_listed_use_in_the_data_step_sources() -> None:
    """The partition-side streams are looked up by name in the package; no module hard-codes a listed seed number or draws a stream under another name."""
    import ast

    root = Path(__file__).resolve().parents[1] / "studies" / "p10s2"
    drawn: dict[str, list[str]] = {}
    for path in sorted(root.glob("*.py")):
        for n in ast.walk(ast.parse(path.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "partition_gen" and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant):
                drawn.setdefault(str(n.args[1].value), []).append(path.name)
    assert set(drawn) <= set(core.listed_partition_seeds()) and "bootstrap" not in drawn  # 220906 is drawn through core.bootstrap_generator in the analysis stage, never in the data step
    assert drawn["equivalence_injection"] == ["datagen.py"] and drawn["random_id_sequences"] == ["datagen.py"] and drawn["timing_items"] == ["data.py"] and drawn["tokenizer_record"] == ["data.py"]
    src = (root / "datagen.py").read_text()
    assert src.count('partition_gen(mode, "equivalence_injection"') == 1 and src.count('partition_gen(mode, "random_id_sequences"') == 1  # each on its own seed, once
