# ruff: noqa: E501
"""P9I core: the 57-cell registry (section I.7 row counts), seeds, the update rule of section I.6, config,
identity, run names and the charged-time ledger. Self-check only: not independent review, not Astra
validation, not human approval."""

import ast
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9i import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_registry_rows_and_totals() -> None:
    cells = core.cells()
    assert len(cells) == 57
    by_group: dict[str, int] = {}
    for c in cells:
        by_group[c.group] = by_group.get(c.group, 0) + 1
    assert by_group == {"core-16384": 22, "core-65536": 10, "core-4096": 8, "bb-wide": 13, "bb-4096": 4}
    assert sum(1 for c in cells if c.block == "core") == 40
    assert sum(1 for c in cells if c.block == "BB") == 17
    assert len({c.label for c in cells}) == 57


def test_registry_arms_per_size_and_replicates() -> None:
    def arms(group: str, parent: tuple[int, int]) -> list[str]:
        return sorted({c.arm for c in core.cells_of_group(group) if c.parent == parent})

    assert arms("core-16384", core.PRIMARY_PARENT) == sorted(["N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7"])
    assert arms("core-65536", core.PRIMARY_PARENT) == sorted(["N", "W7", "A4", "R1", "D7"])
    assert arms("core-4096", core.PRIMARY_PARENT) == sorted(["N", "W7", "A4", "R1"])
    replicates = [c for c in core.cells() if c.replicate]
    assert sorted(c.arm for c in replicates) == sorted(["W7", "A4", "R1", "D7", "BB"])
    assert all(c.slots == 16384 and c.seed == 1801 and c.parent == (102, 302) for c in replicates)
    bb4 = {c.arm for c in core.cells_of_group("bb-4096")}
    assert bb4 == {"BB", "BB-0"}
    wide = {c.arm for c in core.cells_of_group("bb-wide")}
    assert wide == {"BB", "BB-D", "BB-0"}
    assert {c.seed for c in core.cells() if not c.replicate} == {1801, 1802}


def test_registry_is_asserted_at_import() -> None:
    with pytest.raises(ImportError):
        core._assert_registry(core.cells()[:-1])


def test_cell_rejects_unregistered_combinations() -> None:
    with pytest.raises(ValueError):
        core.Cell("core", "x", "BB", 4096, (101, 301), 1801, "x")  # a BB arm outside block BB
    with pytest.raises(ValueError):
        core.Cell("core", "x", "N", 4096, (101, 301), 7, "x")  # not an init seed
    with pytest.raises(ValueError):
        core.Cell("CAL", "x", "N", 4096, (101, 301), 1791, "x")  # calibration cells are R1/R2 only
    with pytest.raises(ValueError):
        core.parse_label("N-n1-b1-o1-s1")


def test_calibration_cells_are_eighteen_runs() -> None:
    cal = core.calibration_cells()
    assert len(cal) == 18
    assert {c.arm for c in cal} == {"R1", "R2"}
    assert sorted({c.seed for c in cal}) == [1791, 1792]
    per = [c for c in cal if c.arm == "R1" and c.slots == 4096]
    assert [(c.parent, c.seed) for c in per] == [((101, 301), 1791), ((101, 301), 1792), ((102, 302), 1791)]
    assert core.parse_label(cal[0].label) == cal[0]


def test_parse_label_roundtrip_for_test_cells() -> None:
    for arm in core.ARMS:
        c = core.make_cell(arm, 16384, (102, 302), 1801)
        assert core.parse_label(c.label) == c


def test_d7_widths_and_parameter_formulas() -> None:
    assert [core.d7_hidden_width(s) for s in core.SLOTS_BY_SIZE] == [786, 3090, 12306]
    for s in core.SLOTS_BY_SIZE:
        h = core.d7_hidden_width(s)
        assert abs(core.d7_parameters(h) - core.w7_parameters(s)) / core.w7_parameters(s) <= 0.001
    assert core.W_EXTRA == 3072 and core.A_EXTRA == 3072 and core.BB_PARAMETERS == 4224
    assert core.memory_parameters(4096) == 198145


def test_seed_namespaces_are_disjoint() -> None:
    ns = core.seed_namespaces()
    for a, b in itertools.combinations(ns, 2):
        assert not (ns[a] & ns[b]), (a, b)
    assert min(ns["registered_data"]) == 182001
    assert min(ns["calibration_data"]) == 179101
    assert min(ns["test"]) >= 900001
    assert all(179001 <= v < 180001 for v in ns["rehearsal_data"] | ns["calibration_data"])
    assert ns["registered_init"] == {1801, 1802} and ns["calibration_init"] == {1791, 1792}
    # the auditor's probe constants and ADR-0017's registered seeds stay unused
    assert not any(180101 <= v <= 181900 for v in ns["registered_data"])
    assert not (ns["registered_data"] & ns["p9_registered"])


def test_rehearsal_draws_are_limited_and_exclude_the_calibration_draw_from_seed_checks() -> None:
    with pytest.raises(ValueError):
        core.rehearsal_draw_seeds(10)
    assert core.calibration_seeds().facts == 179101
    assert core.registered_seeds().facts == 182001
    core.check_seed_set("registered", "p9i-registered")
    core.check_seed_set("calibration", "rehearsal-1")
    core.check_seed_set("rehearsal", "rehearsal-2")
    core.check_seed_set("calibration", "p9i-test-0")
    for mode, name in (("registered", "rehearsal-1"), ("registered", "p9i-test-0"), ("calibration", "p9i-registered"), ("calibration", "rehearsal-2"), ("rehearsal", "rehearsal-1"), ("rehearsal", "p9i-registered")):
        with pytest.raises(ValueError):
            core.check_seed_set(mode, name)


def _curves(**values: dict[int, float]) -> dict[int, dict[int, float]]:
    return {int(k[1:]): v for k, v in values.items()}


GOOD = {2048: 0.97, 4096: 0.99, 8192: 0.99, 16384: 0.99}


def test_select_updates_picks_the_smallest_u_that_qualifies_everywhere() -> None:
    r2 = _curves(s4096=GOOD, s16384={2048: 0.5, 4096: 0.96, 8192: 0.99, 16384: 0.99}, s65536={2048: 0.2, 4096: 0.4, 8192: 0.97, 16384: 0.99})
    r1 = _curves(s4096=GOOD, s16384={2048: 0.95, 4096: 0.95, 8192: 0.95, 16384: 0.95}, s65536={2048: 0.1, 4096: 0.5, 8192: 0.91, 16384: 0.99})
    out = core.select_updates(r2, r1)
    assert out.updates == 8192 and out.failed == {} and out.live == [4096, 16384, 65536]


def test_select_updates_requires_both_rungs_at_the_same_u() -> None:
    r2 = _curves(s4096=GOOD, s16384={2048: 0.99, 4096: 0.5, 8192: 0.5, 16384: 0.5})
    r1 = _curves(s4096=GOOD, s16384={2048: 0.1, 4096: 0.95, 8192: 0.95, 16384: 0.95})
    out = core.select_updates(r2, r1)
    assert out.failed == {16384: [core.NOT_JOINT]} and out.updates == 2048  # each rung is reached, never both at once


def test_select_updates_with_a_failed_size() -> None:
    r2 = _curves(s4096=GOOD, s16384=GOOD, s65536={2048: 0.2, 4096: 0.5, 8192: 0.9, 16384: 0.94})
    r1 = _curves(s4096=GOOD, s16384=GOOD, s65536=GOOD)
    out = core.select_updates(r2, r1)
    assert out.failed == {65536: [core.TASK_CEILING_FAIL]}
    assert out.updates == 2048 and out.live == [4096, 16384]  # U is the smallest value at the remaining sizes
    r1_bad = _curves(s4096=GOOD, s16384={2048: 0.2, 4096: 0.3, 8192: 0.6, 16384: 0.89}, s65536=GOOD)
    both = core.select_updates(_curves(s4096=GOOD, s16384={2048: 0.2, 4096: 0.3, 8192: 0.6, 16384: 0.9}, s65536=GOOD), r1_bad)
    assert both.failed == {16384: [core.TASK_CEILING_FAIL, core.ORACLE_QUERY_FAIL]}
    oracle = core.select_updates(_curves(s4096=GOOD), _curves(s4096={2048: 0.5, 4096: 0.5, 8192: 0.5, 16384: 0.5}))
    assert oracle.failed == {4096: [core.ORACLE_QUERY_FAIL]} and oracle.updates is None and oracle.live == []


def test_select_updates_boundaries_are_inclusive() -> None:
    edge = {2048: 0.95, 4096: 0.95, 8192: 0.95, 16384: 0.95}
    r1 = {2048: 0.90, 4096: 0.90, 8192: 0.90, 16384: 0.90}
    assert core.select_updates({4096: edge}, {4096: r1}).updates == 2048
    below = {2048: 0.9499999, 4096: 0.9499999, 8192: 0.9499999, 16384: 0.9499999}
    assert core.select_updates({4096: below}, {4096: r1}).failed == {4096: [core.TASK_CEILING_FAIL]}
    assert core.select_updates({4096: edge}, {4096: {u: 0.8999999 for u in edge}}).failed == {4096: [core.ORACLE_QUERY_FAIL]}


def test_config_file_matches_constants_and_loads() -> None:
    text = (ROOT / "configs" / "p9i_interface.toml").read_text(encoding="utf-8")
    assert text == core.render_config_toml()
    cfg = core.load_config()
    assert cfg["matrix"]["total"] == 57 and cfg["interfaces"]["bb_parameters"] == 4224
    assert core.config_sha256() == core.config_sha256()
    changed = core.load_config()
    changed["thresholds"]["works_eta"] = 0.8
    with pytest.raises(ValueError):
        core.validate_config(changed)


def test_identity_hashes_and_imported_p9_modules_are_all_listed() -> None:
    hashes = core.source_hashes()
    assert "studies/p9i/core.py" in hashes and "studies/p9/model.py" in hashes
    assert core.source_digest() == core.source_digest()
    imported: set[str] = set()
    for path in (ROOT / "studies" / "p9i").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("studies.p9"):
                if node.module == "studies.p9":
                    imported |= {a.name for a in node.names}
                elif not node.module.startswith("studies.p9i"):
                    imported.add(node.module.split(".")[2])
    assert imported <= set(core.IMPORTED_P9_MODULES), imported - set(core.IMPORTED_P9_MODULES)
    ident = core.code_identity()
    assert set(ident) == {"source_sha256", "spec_sha256", "config_sha256", "frozen_source_sha256"}


def test_run_names_roundtrip_and_records_carry_the_study_code(tmp_path: Path) -> None:
    for stage in core.STAGE_CODES:
        name = core.run_name(stage)
        assert name.startswith("P9I") and core.parse_run_name(name)[0] == stage
    with pytest.raises(ValueError):
        core.parse_run_name("P9T-2026Z-abc")
    record = {**core.envelope("train"), "x": 1}
    assert record["study"] == "P9I"
    core.write_record(tmp_path / "r.json", record)
    assert core.read_record(tmp_path / "r.json", "train")["x"] == 1
    with pytest.raises(ValueError):
        core.write_record(tmp_path / "bad.json", {"kind": "train", "schema": 1, "study": "P9"})


def test_ledger_charges_and_refuses(tmp_path: Path) -> None:
    ledger = core.Ledger(tmp_path / "ledger.json", cap_seconds=1000.0)
    assert ledger.remaining() == 1000.0
    ledger.require_room("calibrate", 1000.0)
    ledger.charge("calibrate", "run-a", 400.0)
    ledger.charge("rehearse", "run-b", 350.0)
    assert ledger.charged() == 750.0 and ledger.remaining() == 250.0
    assert [e["stage"] for e in ledger.entries()] == ["calibrate", "rehearse"]
    ledger.require_room("train", 250.0)
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("train", 251.0)
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("train", 0.0)
    assert core.CAP_SECONDS == 4 * 3600
