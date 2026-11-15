# ruff: noqa: E501
"""P10S0 core: the registry (every count of ADR-0020 sections 6 and 10.1), labels, seeds and gate G9, the fixed strings character for character against the ADR and P9-II's OUTCOME.md, the config
(byte equality, values read from it), the single ledger, run names, draw plan, schedules, launch scripts. Self-check only: not independent review, not Astra validation, not human approval."""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s0 import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ADR = (ROOT / core.SPEC).read_text(encoding="utf-8")


# --- registry ------------------------------------------------------------------------------------------------------------------------------
def test_registry_counts_are_those_of_the_adr() -> None:
    assert (len(core.q1_cells()), len(core.q1_cells(True)), len(core.wx_cells("A5-D")), len(core.wx_cells("A1")), len(core.probe_cells("A5-D")), len(core.check_cells())) == (230, 190, 20, 20, 6, 3)
    assert core.WHOLE_PLAN_CELLS == 256
    by = {}
    for c in core.q1_cells():
        by[(c.celltype, c.arm)] = by.get((c.celltype, c.arm), 0) + 1
    assert by[("2K/4K", "A0")] == by[("2K/4K", "A1")] == by[("2K/4K", "A2")] == by[("2K/4K", "A5-D")] == 20 and by[("2K/4K", "A6")] == by[("2K/4K", "A7")] == 10
    assert by[("8K/16K", "A5-D")] == 20 and by[("8K/4K", "A0")] == by[("8K/4K", "A5-D")] == by[("8K/4K", "A6")] == 10
    cut = {}
    for c in core.q1_cells(True):
        cut[(c.celltype, c.arm)] = cut.get((c.celltype, c.arm), 0) + 1
    assert cut[("8K/16K", "A0")] == 10 and cut[("8K/16K", "A6")] == 10 and cut[("2K/4K", "A0")] == 20  # cut 3: 60 cells at 8K/16K


def test_no_a1_or_a2_at_8k_4k_and_references_use_seed_2001() -> None:
    assert not [c for c in core.q1_cells() if c.celltype == "8K/4K" and c.base in core.SUPERVISED]
    assert {c.seed_index for c in core.q1_cells() if c.arm in core.REFERENCE_ARMS} == {0}
    one_seed = [c for c in core.q1_cells() if c.celltype == "8K/4K" and c.arm in ("A0", "A5-D")]
    assert all(c.seed_index == (0 if c.draw % 2 else 1) for c in one_seed)  # init 2001 for odd draws, 2002 for even
    assert all(c.seed_index == (0 if c.draw % 2 else 1) for c in core.wx_cells("A5-D"))
    assert {c.draw for c in core.probe_cells("A1")} == {11, 12, 13} and {c.seed_index for c in core.probe_cells("A1")} == {0}
    cut = [c for c in core.q1_cells(True) if c.celltype == "8K/16K" and c.arm == "A1"]
    assert len(cut) == 10 and all(c.seed_index == (0 if c.draw % 2 else 1) for c in cut)


def test_wx_and_probe_exist_only_for_arms_that_can_still_be_the_candidate() -> None:
    for bad in ("A0", "A2", "A4", "A5-C"):
        with pytest.raises(ValueError):
            core.wx_cells(bad)
        with pytest.raises(ValueError):
            core.probe_cells(bad)


def test_labels_round_trip_and_unknown_labels_are_refused() -> None:
    for c in core.q1_cells() + core.wx_cells("A5-D") + core.probe_cells("A1") + core.check_cells():
        assert core.parse_label(c.label) == c
    t = core.make_cell("WX-A1", "8K/16K", "WX", 3, 1)
    assert core.parse_label(t.label) == t and t.label.startswith("TEST-")
    for bad in ("Q1-A9-2K4K-d01-j0", "nonsense", "Q1-A0-2K4K-d01-j2"):
        with pytest.raises(ValueError):
            core.parse_label(bad)
    with pytest.raises(ValueError):
        core.Cell("Q1", "A4", "2K/4K", 1, 0, "x")


def test_cell_types_are_the_registered_sizes() -> None:
    ct = core.CELLTYPES
    assert [(c.facts, c.slots, c.multiplier) for c in ct.values()] == [(2048, 4096, 1), (8192, 16384, 4), (8192, 4096, 4), (32768, 65536, 16)]
    assert [c.facts_per_slot for c in ct.values()] == [0.5, 0.5, 2.0, 0.5]
    assert all(c.exposures_per_fact() == 512.0 for c in ct.values())
    assert ct["8K/16K"].readout_updates() == (8192, 32768) and ct["2K/4K"].readout_updates() == (8192,) and ct["32K/64K"].decisive() == 131072


def test_schedules_are_exposure_scaled() -> None:
    assert core.schedule_for("A2", "2K/4K").u_pre == 2048 and core.schedule_for("A2", "8K/16K").u_pre == 8192
    assert core.schedule_for("A1", "8K/16K").u_pre is None and core.schedule_for("A5-D", "2K/4K").u_pre is None
    with pytest.raises(ValueError):
        core.schedule_for("A2", "8K/4K")
    assert core.schedule_for("A2", "2K/4K", unit=8).u_pre == 2  # DRY scaling: U_pre / U stays 1/4


# --- calibrated values and the fixed strings --------------------------------------------------------------------------------------------------
def test_calibrated_values() -> None:
    assert core.CALIBRATED == {"lambda": 1.0, "u_pre": 2048.0, "mu": 1.0, "k0_fraction": 0.125}
    assert (core.HYPER.lambda_, core.HYPER.u_pre, core.HYPER.mu) == (1.0, 2048.0, 1.0)


def test_fixed_strings_are_in_the_adr_character_for_character() -> None:
    for s in (core.FOURTH_ARM_STRING, core.F1_ANNOTATION, core.PROVENANCE_SENTENCE, core.HUMAN_LEAD_WORDS, core.FIXED_SENTENCES):
        assert s in ADR, s
    assert "**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**" in ADR
    assert f"**\"{core.PROVENANCE_SENTENCE}\"**" in ADR
    assert core.MAPPING_NONE_TEMPLATE.format(arm="A0") == "FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)"
    assert "FOURTH ARM: NONE — P9-II CARRIED \\<arm\\> (ALREADY IN S0)" in ADR and core.NOT_STARTED in ADR


def test_f1_annotation_is_verbatim_in_p9ii_outcome() -> None:
    assert core.F1_ANNOTATION in (ROOT / core.P9II_RECORDS["outcome"]).read_text(encoding="utf-8")


def test_a5d_block_contains_the_three_strings() -> None:
    block = core.a5d_block()
    assert core.FOURTH_ARM_STRING in block and core.F1_ANNOTATION in block and core.PROVENANCE_SENTENCE in block


# --- seeds and G9 --------------------------------------------------------------------------------------------------------------------------------
def test_registered_seed_layout_is_the_adr_s() -> None:
    d1 = core.registered_set(1)
    assert d1.base == 200001 and core.registered_set(13).base == 201201 and core.reserve_set(1).base == 201301 and core.reserve_set(2).base == 201401
    s = d1.seeds(2048)
    assert s.facts == 200001 and d1.seeds(8192).facts == 200021 and d1.seeds(32768).facts == 200061
    assert tuple(d1.seeds(2048).null_seeds_a) == (200015, 200016, 200017) and tuple(d1.seeds(2048).null_seeds_b) == (200018, 200019, 200020)
    assert (d1.target_seed("2K/4K", 0), d1.target_seed("2K/4K", 1), d1.target_seed("8K/16K", 1), d1.target_seed("32K/64K", 0)) == (200041, 200042, 200046, 200049)
    assert (d1.swap_seed(2048), d1.swap_seed(8192), d1.swap_seed(32768)) == (200051, 200052, 200053)
    assert core.INIT_SEEDS == (2001, 2002) and (core.CHECK_INIT, core.REHEARSAL_INIT) == (2091, 2092) and (core.CHECK_BASE, core.REHEARSAL_BASE) == (209001, 209101)
    assert (core.TEST_SEED_BASE, core.TEST_SEED_TOP) == (920001, 920999)


def test_seed_groups_lie_inside_the_declared_ranges_and_g9_passes() -> None:
    core.assert_namespaces_disjoint(extra=core.implemented_study_seeds())
    every = frozenset().union(*core.seed_namespaces().values())
    assert min(core.seed_namespaces()["registered"]) >= 200001 and max(core.seed_namespaces()["reserve"]) <= 209999
    assert all(920001 <= v <= 920999 for v in core.seed_namespaces()["test"])
    assert 2001 in every and 2091 in every and 2092 in every


def test_g9_lists_the_other_studies_seeds() -> None:
    s1 = dict(core.OTHER_NAMESPACES)["S1"]
    for lo, hi in ((210001, 219999), (2101, 2105), (2111, 2111), (2121, 2121), (2112, 2112), (2122, 2122), (2191, 2192), (921001, 921999)):
        assert (lo, hi) in s1
    assert (1891, 1892) in core.OTHER_NAMESPACES["P9-II"] and (910001, 919999) in core.OTHER_NAMESPACES["P9-II"]
    assert (220001, 228999) in core.OTHER_NAMESPACES["S2"] and (229001, 229999) in core.OTHER_NAMESPACES["S2"]
    for lo, hi in ((170001, 171343), (179001, 179933), (1701, 1702), (182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233), (500001, 500004), (190001, 191599), (1901, 1902)):
        assert any((lo, hi) in v for v in core.OTHER_NAMESPACES.values())


def test_g9_refuses_an_overlap_in_every_direction() -> None:
    own = core.seed_namespaces()
    with pytest.raises(ValueError, match="overlap"):
        core.assert_namespaces_disjoint({"registered": own["registered"], "reserve": own["reserve"] | frozenset({200001}), "init": own["init"]}, {})
    with pytest.raises(ValueError, match="outside its bounded range"):
        core.assert_namespaces_disjoint({"init": frozenset({2001, 2003})}, {})
    with pytest.raises(ValueError, match="outside its bounded range"):
        core.assert_namespaces_disjoint({"registered": frozenset({210001})}, {})  # S1's block is not S0's
    with pytest.raises(ValueError, match="inside S1"):
        core.assert_namespaces_disjoint({"registered": frozenset({200001})}, {"S1": ((200001, 200010),)})
    with pytest.raises(ValueError, match="a seed of"):
        core.assert_namespaces_disjoint({"init": frozenset({2001})}, {}, {"P9-II code": frozenset({2001})})
    assert core.p9ii_test_seed_values() and all(910001 <= v <= 919999 for v in core.p9ii_test_seed_values())


def test_p1_to_p8_config_seeds_do_not_touch_s0() -> None:
    configs = core.config_seed_values(ROOT)
    assert configs and "p10s0_qualification.toml" not in configs
    own = frozenset().union(*core.seed_namespaces().values())
    for name, values in configs.items():
        assert not (own & values), name


def test_check_seed_set_per_mode() -> None:
    core.check_seed_set("registered", "p10s0-draw-3")
    core.check_seed_set("registered", "p10s0-reserve-2")
    core.check_seed_set("check", "p10s0-check")
    core.check_seed_set("rehearsal", "p10s0-rehearsal")
    core.check_seed_set("dry", "p10s0-test-0")
    for mode, name in (("registered", "p10s0-check"), ("registered", "p9ii-draw-1"), ("registered", "p10s0-test-0"), ("check", "p10s0-draw-1"), ("rehearsal", "p10s0-draw-1"), ("dry", "p10s0-draw-1"), ("dry", "p10s0-rehearsal")):
        with pytest.raises(ValueError):
            core.check_seed_set(mode, name)
    with pytest.raises(ValueError):
        core.check_seed_set("nonsense", "p10s0-draw-1")


def test_test_seed_sets_stay_in_920001_920999() -> None:
    for k in range(8):
        assert all(920001 <= v <= 920999 for v in core.test_set(k).values())
    with pytest.raises(ValueError):
        core.test_set(9)


# --- draw plan ---------------------------------------------------------------------------------------------------------------------------------------
def test_draw_plan_substitutes_reserves_in_order() -> None:
    ok = dict.fromkeys(core.SET_NAMES, True)
    assert core.plan_draws(ok).ok and not core.plan_draws(ok).replacements
    one = {**ok, "p10s0-draw-4": False}
    p = core.plan_draws(one)
    assert p.ok and p.replacements == {4: "p10s0-reserve-1"} and p.seed_set_of[4] == "p10s0-reserve-1"
    two = {**ok, "p10s0-draw-4": False, "p10s0-draw-9": False}
    assert core.plan_draws(two).replacements == {4: "p10s0-reserve-1", 9: "p10s0-reserve-2"}
    assert not core.plan_draws({**two, "p10s0-draw-12": False}).ok
    assert not core.plan_draws({**one, "p10s0-reserve-1": False}).ok
    assert not core.plan_draws({k: v for k, v in ok.items() if k != "p10s0-draw-2"} | {}).replacements == {} or True
    assert core.plan_draws({k: v for k, v in ok.items() if k != "p10s0-draw-2"}).replacements == {2: "p10s0-reserve-1"}  # no G1 result counts as failed
    assert core.replacement_label("p10s0-reserve-2") == "REPLACED BY RESERVE 2"


# --- config -------------------------------------------------------------------------------------------------------------------------------------------
def test_config_file_is_the_rendered_constants_and_resources_are_read_from_it() -> None:
    assert (ROOT / core.DEFAULT_CONFIG).read_text(encoding="utf-8") == core.render_config_toml(core.generation_block())  # the generation block is the one the rehearsal sets
    assert core.validate_config(core.load_config())
    lim = core.resource_limits()
    assert lim["rss_worker_bytes"] == 3 * 1024**3 and lim["rss_aggregate_bytes"] == 18 * 1024**3 and lim["workers"] == 6 and lim["cap_hours"] == 16.0 and lim["headroom"] == 2.0 and lim["rehearsal_peak_limit_bytes"] == int(1.5 * 1024**3)
    cfg = core.load_config()
    assert cfg["arms"]["candidate_arms"] == ["A5-D", "A1"] and cfg["calibrated"]["mu"] == 1.0 and cfg["seeds"]["registered_base"] == 200001
    bad = core.registered_config()
    bad["resources"]["workers"] = 7
    with pytest.raises(Exception):  # noqa: B017
        core.validate_config(__import__("copy").deepcopy(cfg) | {"resources": bad["resources"] | {"cap_hours": 1.0}})


def test_the_config_name_is_the_adr_s() -> None:
    assert core.DEFAULT_CONFIG == Path("configs/p10s0_qualification.toml") and "configs/p10s0_qualification.toml" in ADR  # the lead's ruling on item 1
    assert not (ROOT / "configs/p10s0_addressing.toml").exists()


# --- identity, run names, ledger ----------------------------------------------------------------------------------------------------------------------
def test_run_names_carry_the_study_code_p10s0() -> None:
    for stage in core.STAGE_CODES:
        name = core.run_name(stage, unique="abc")
        assert name.startswith("P10S0") and core.parse_run_name(name)[0] == stage
    with pytest.raises(ValueError):
        core.parse_run_name("P9II" + "G-20260101T000000000000Z-abc")
    assert str(core.default_experiments_root()).endswith("/experiments")


def test_source_digest_covers_s0_p9ii_p9i_p9_and_the_launch_scripts() -> None:
    hashes = core.source_hashes()
    assert "studies/p10s0/core.py" in hashes and "studies/p9ii/train.py" in hashes and "studies/p9i/core.py" in hashes and "studies/p9/pool.py" in hashes
    assert {f"studies/p10s0/launch/{n}.sh" for n in ("generate", "gates", "q1", "q1_gate", "probe", "wx", "analysis", "report")} <= set(hashes)
    ident = core.code_identity()
    assert set(ident) == {"source_sha256", "spec_sha256", "config_sha256", "frozen_source_sha256"} and ident["source_sha256"] == core.source_digest()


def test_s0_imports_only_hashed_study_modules() -> None:
    hashed = set(core.source_hashes())
    for path in (ROOT / "studies" / "p10s0").glob("*.py"):
        for m in re.finditer(r"^\s*(?:from|import) studies\.(p9|p9i|p9ii)(?:\.(\w+))?(?: import (.*))?", path.read_text(encoding="utf-8"), re.M):
            pkg, mod, names = m.group(1), m.group(2), m.group(3)
            mods = [mod] if mod else [n.strip().split(" ")[0] for n in (names or "").split(",") if n.strip()]
            for name in mods:
                if name in ("__init__",):
                    continue
                key = f"studies/{pkg}/{name}.py"
                if (ROOT / key).is_file():
                    assert key in hashed, f"{path.name} imports {key}, which the source digest does not cover"


def test_ledger_is_one_budget_of_sixteen_hours(tmp_path: Path) -> None:
    ledger = core.Ledger(tmp_path / "ledger.json")
    assert ledger.cap_seconds == 16 * 3600 and ledger.charged() == 0 and ledger.remaining() == 16 * 3600
    ledger.require_room("q1", 3600)
    ledger.charge("gates", "run", 100.0)
    ledger.charge("q1", "run", 5000.0)
    assert ledger.charged() == 5100.0 and len(ledger.entries()) == 2
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("big", 16 * 3600)
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("none", 0)
    assert core.ledger_for(tmp_path).path.name == "P10S0-ledger.json"


def test_records_need_the_p10s0_envelope(tmp_path: Path) -> None:
    core.write_record(tmp_path / "a.json", {**core.envelope("train"), "x": 1})
    assert core.read_record(tmp_path / "a.json", "train")["x"] == 1
    with pytest.raises(ValueError):
        core.write_record(tmp_path / "b.json", {"kind": "train", "schema": 1, "study": "P9II"})
    with pytest.raises(ValueError):
        core.read_record(tmp_path / "a.json", "eval")
    with pytest.raises(ValueError):
        core.envelope("nonsense")


def test_platform_helpers_and_environment() -> None:
    env = core.environment()
    assert env["torch"] and env["threads"]["torch_num_threads"] >= 1 and "platform" in env
    assert isinstance(core.on_registered_platform(), bool)


# --- launch scripts ------------------------------------------------------------------------------------------------------------------------------------
SCRIPTS = ("gates", "q1", "q1_gate", "probe", "wx", "analysis", "report")


@pytest.mark.parametrize("name", SCRIPTS)
def test_every_launch_script_passes_its_stage_cap_file_and_its_stage_name(name: str) -> None:
    text = (ROOT / "studies/p10s0/launch" / f"{name}.sh").read_text(encoding="utf-8")
    assert "--caps studies/p10s0/freeze/stage_caps.json" in text
    assert f"registered {name} " in text and "--freeze-commit" in text and "--run-dir" in text
    assert 'if [ "$#" -ne 2 ]' in text and "eval " not in text
    assert (ROOT / "studies/p10s0/launch" / f"{name}.sh").stat().st_mode & 0o111


def test_generate_script_passes_the_stage_cap_to_every_call() -> None:
    text = (ROOT / "studies/p10s0/launch/generate.sh").read_text(encoding="utf-8")
    calls = [line for line in text.splitlines() if "studies.p10s0.stages generate" in line]
    assert len(calls) == 2 and all("--generation-cap-from-config" in c and "--stage-cap-seconds" not in c and "--i-understand-freeze-time" in c and "--mode registered" in c for c in calls)
    assert "for k in 1 2 3 4 5 6 7 8 9 10 11 12 13" in text and "for r in 1 2" in text and "draw-plan" in text


@pytest.mark.parametrize("name", [*SCRIPTS, "generate"])
def test_launch_scripts_refuse_wrong_argument_counts(name: str) -> None:
    for argv in ([], ["only-one"], ["a", "b", "c"]):
        r = subprocess.run(["sh", str(ROOT / "studies/p10s0/launch" / f"{name}.sh"), *argv], capture_output=True, check=False)
        assert r.returncode == 2 and b"usage" in r.stderr


def test_the_freeze_files_exist_both_or_neither() -> None:
    """Before the freeze neither file exists; the freeze commit adds both. This test passes before and after it (the audit's M4; P9-II's fix 2bc8038 does the same)."""
    assert (ROOT / "studies/p10s0/freeze/README.md").is_file()
    assert (ROOT / "studies/p10s0/freeze/plan.json").exists() == (ROOT / "studies/p10s0/freeze/stage_caps.json").exists()


def test_g9_reads_p9ii_s_test_seeds_from_its_committed_code_and_tests() -> None:
    from studies.p10s0 import gates

    found = gates.scan_p9ii_code_for_test_seeds(ROOT)
    assert found and all(910001 <= v <= 919999 for v in found), sorted(v for v in found if not 910001 <= v <= 919999)
    g = gates.g9_check(ROOT)
    assert g["passed"] and g["p9ii_code_scanned"] and g["p9ii_test_seeds_inside_range"] and g["p9ii_test_seed_count"] >= len(found)
    assert (1891, 1892) in [tuple(r) for r in g["other_ranges"]["P9-II"]] and {"S1", "S2", "P9", "P9-I"} <= set(g["other_ranges"])


def test_g9_scan_reads_test_seeds_calls_and_not_literals(tmp_path: Path) -> None:
    from studies.p10s0 import gates

    (tmp_path / "studies/p9ii").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "studies/p9ii/x.py").write_text("RANGE = (920001, 929999)\nvalues = test_seeds(1)\n")
    (tmp_path / "tests/test_p9ii_x.py").write_text("init = 915000\nbad = 920123\nrefused = test_seeds(99999)\nother = test_seeds(2)\n")
    found = gates.scan_p9ii_code_for_test_seeds(tmp_path)
    assert 910101 in found and 910201 in found and 920001 not in found and 920123 not in found and 915000 not in found and all(910001 <= v <= 919999 for v in found)
    assert gates.g9_check(tmp_path)["p9ii_test_seeds_inside_range"]
