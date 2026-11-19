# ruff: noqa: E501
"""P10IS5 config tests (ADR-0028 sections 4 to 10, 12, 13). The threshold test LISTS every threshold in the test with the ADR section beside it (it does not parse numbers out of prose); for each entry it also
requires that the literal text the entry quotes appears in that section of the ADR, so that a change of the ADR text that moves a number is noticed. Two values are NOT in the ADR and are asserted as the implementer's
departures: the per-pass process timeout (a deadline on a wait) and the extra process marker ``studies.``. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import math
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ADR = (ROOT / core.SPEC).read_text(encoding="utf-8")
CFG = core.load_config()


def section(number: str) -> str:
    level = "###" if "." in number else "##"
    m = re.search(rf"^{level} {re.escape(number)}[ .].*?(?=^#{{2,3}} |\Z)", ADR, flags=re.S | re.M)
    assert m, f"section {number} not found"
    return m.group(0)


def at(cfg: Any, path: str) -> Any:
    for part in path.split("."):
        cfg = cfg[part]
    return cfg


# (config path, expected value, ADR section, a literal that section must contain)
THRESHOLDS: list[tuple[str, Any, str, str]] = [
    ("device.page_bytes", 16384, "4.1", "16,384 B"),
    ("device.tile_pages", 64, "4.1", "64 pages = 1,048,576 B (1 MiB)"),
    ("device.store_tiles", 4096, "4.1", "4,096 tiles = 262,144 pages"),
    ("device.rehearsal_tiles", 1024, "4.1", "1,024 tiles = 1,073,741,824 B (1 GiB)"),
    ("device.control_tiles", 64, "5.4", "its own file of 64 tiles"),
    ("device.rehearsal_usable_tiles", 896, "8", "840 of tiles 0 to 895"),
    ("device.band_start_tile", 896, "13", "tiles 896 to 951"),
    ("device.f_rdahead", 45, "13", "`F_RDAHEAD` 45"),
    ("device.f_nocache", 48, "13", "`F_NOCACHE` 48"),
    ("device.f_fullfsync", 51, "13", "`F_FULLFSYNC` 51"),
    ("device.write_unit_bytes", 1048576, "7", "1 MiB `os.pwrite` calls"),
    ("device.build_chunk_bytes", 1073741824, "13", "Chunks of 1 GiB"),
    ("device.directory_suffix", ".noindex", "6", "ends in `.noindex`"),
    ("cells.sizes", [1, 3, 8, 64], "4.2", "**Request sizes s (pages):** 1, 3, 8, 64"),
    ("cells.depths", [1, 2, 4, 8, 16, 32], "4.2", "**Depths k:** 1, 2, 4, 8, 16, 32"),
    ("cells.requests_per_pass", [400, 400, 160, 64], "4.2", "400, 400, 160, 64 for s = 1, 3, 8, 64"),
    ("cells.tiles_per_pass", [7, 20, 20, 64], "4.3", "Tiles per pass: 7, 20, 20, 64"),
    ("cells.rehearsal_requests_per_pass", [100, 100, 40, 16], "8", "n(s) = 100, 100, 40, 16"),
    ("cells.rehearsal_tiles_per_pass", [2, 5, 5, 16], "13", "the counts are 2, 5, 5, 16"),
    ("cells.repeats", 5, "4.3", "Repeats are 1 to 5 and the spare, 6"),
    ("cells.spare_repeat", 6, "4.3", "Repeats are 1 to 5 and the spare, 6"),
    ("cells.r1_depths", [1, 32], "13", "at k = 1 and k = 32"),
    ("cells.r1_reread_working_set_tiles", [32, 64, 128], "7", "working sets of 32, 64 and 128 MiB"),
    ("thresholds.m_floor", 0.10, "5.4", "max(0.10, 2 × CV_R)"),
    ("thresholds.m_ceiling", 0.30, "5.4", "If m_t would exceed 0.30"),
    ("thresholds.m_cv_multiple", 2.0, "5.4", "max(0.10, 2 × CV_R)"),
    ("thresholds.label_min_repeats", 4, "5.3", "in at least 4 of 5 repeats"),
    ("thresholds.valid_min_repeats", 4, "5.3", "at least 4 of the 5 repeats are valid"),
    ("thresholds.harness_limited_fraction", 0.25, "5.4", "above a quarter of the cell's median latency"),
    ("thresholds.harness_requests", 400, "5.4", "400 single-page requests"),
    ("thresholds.harness_tiles", 7, "5.4", "its tiles 0 to 6"),
    ("thresholds.harness_depths", [1, 2, 4, 8, 16, 32], "5.4", "at each depth"),
    ("budget.cap_bytes", 10_000_000_000, "6", "10,000,000,000 B (10 GB)"),
    ("budget.probe_bytes", 67_108_864, "6", "at most 67,108,864 (64 MiB)"),
    ("budget.control_file_bytes", 67_108_864, "6", "Control file (positive control, harness figure) | R1 | 67,108,864"),
    ("budget.rehearsal_file_bytes", 1_073_741_824, "6", "Rehearsal file (R1, M and K) | R1 | 1,073,741,824"),
    ("budget.store_file_bytes", 4_294_967_296, "6", "The file | E1 | 4,294,967,296"),
    ("budget.free_space_min_bytes", 500_000_000_000, "6", "at least 500 GB at all times"),
    ("budget.max_builds_per_file", 2, "6", "No file is built a third time"),
    ("quiet.load_margin", 0.5, "8", "plus 0.5"),
    ("quiet.idle_window_seconds", 600, "7", "10-minute idle window"),
    ("quiet.idle_interval_seconds", 10, "7", "sampled every 10 s"),
    ("quiet.idle_samples", 60, "8", "sixty samples"),
    ("quiet.retry_interval_seconds", 600, "8", "retried every 10 minutes"),
    ("quiet.retry_deadline_seconds", 21600, "8", "at most 6 hours"),
    ("quiet.settle_seconds", 120, "8", "120 s have passed"),
    ("quiet.activity_window_seconds", 30, "8", "over a 30 s window"),
    ("quiet.percentile", 0.95, "8", "95th percentile"),
    ("quiet.hid_idle_min_seconds", 600, "8", "`HIDIdleTime` at least 600 s"),
    ("quiet.cold_wait_seconds", 600, "7", "after the build and a 10-minute wait"),
    ("quiet.extra_sessions", 3, "8", "in up to three further sessions"),
    ("resources.memory_guard_bytes", 4 * 1024**3, "9", "Memory guard: 4 GiB of `ri_phys_footprint` per process"),
    ("platform.system", "Darwin", "12", "macOS arm64"),
    ("platform.machine", "arm64", "12", "macOS arm64"),
    ("platform.torch", "2.8.0", "12", "torch 2.8.0"),
    ("platform.python_prefix", "3.12", "12", "CPython 3.12.14"),
    ("seeds.store_contents", 280101, "10", "280101 (280102, 280103 unused)"),
    ("seeds.r1_rehearsal_file_contents", 289001, "10", "289001 (rehearsal file)"),
    ("seeds.r1_control_file_contents", 289013, "10", "289013 (control file)"),
    ("seeds.request_order", [280001, 280002, 280003, 280004, 280005], "10", "280001–280005"),
    ("seeds.spare_request_order", 280006, "10", "spare 280006"),
    ("seeds.r1_request_order", 289011, "10", "289011"),
    ("seeds.m_request_order", [289211, 289212, 289213, 289214, 289215], "10", "289211–289215"),
    ("seeds.k_request_order", [289216, 289217, 289218, 289219, 289220], "10", "289216–289220"),
    ("seeds.pass_order", [280201, 280202, 280203, 280204, 280205], "10", "280201–280205"),
    ("seeds.spare_pass_order", 280206, "10", "**280206**"),
    ("seeds.r1_pass_order", 289021, "10", "289021"),
    ("seeds.m_pass_order", [289221, 289222, 289223, 289224, 289225], "10", "289221–289225"),
    ("seeds.k_pass_order", [289226, 289227, 289228, 289229, 289230], "10", "289226–289230"),
    ("seeds.tile_assignment", 287001, "10", "**287001**"),
    ("seeds.m_tile_assignment", 289241, "10", "**289241**"),
    ("seeds.k_tile_assignment", 289242, "10", "**289242**"),
    ("seeds.r1_reread_offsets", 289051, "10", "**289051**"),
]


@pytest.mark.parametrize(("path", "expected", "sec", "literal"), THRESHOLDS, ids=[t[0] for t in THRESHOLDS])
def test_threshold_equals_the_adr(path: str, expected: Any, sec: str, literal: str) -> None:
    assert at(CFG, path) == expected, path
    assert literal in section(sec), f"section {sec} of the ADR does not contain {literal!r}"


def test_total_cap_is_the_provisional_figure_or_the_rule_value_below_it() -> None:
    # Independent of the planning state: 5 hours while the caps are provisional (section 10); after M the lead sets them by the rule, and the rule's value never exceeds the provisional figure here.
    assert "the provisional figure is 5 hours" in section("10")
    total = float(at(CFG, "caps.total_hours"))
    assert total == 5.0 if CFG["caps"]["provisional"] else 0.0 < total <= 5.0


def test_registry_ranges() -> None:
    registry = (ROOT / "docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md").read_text(encoding="utf-8")
    assert CFG["seeds"]["test_range"] == [937001, 937999] and "| | test | 937001–937999 |" in registry  # the registry's row of P10-I-S5
    assert [list(CFG["seed_ranges"][k]) for k in ("registered", "auxiliary", "r1", "rehearsal", "test")] == [[280001, 286999], [287001, 288999], [289001, 289199], [289201, 289299], [937001, 937999]]
    assert CFG["seed_ranges"]["checker_sha256"] == "e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594"


def test_departures_from_the_adr_are_listed_here() -> None:
    assert CFG["quiet"]["pass_timeout_seconds"] == 900  # an implementer's deadline on a worker process (the brief: no unbounded wait); not a threshold of any label
    assert {"studies/", "arborlm", "pytest"} <= set(CFG["quiet"]["process_markers"]) and "studies." in CFG["quiet"]["process_markers"]


def test_derived_arithmetic_of_the_adr() -> None:
    reg, reh = core.registered_geometry(CFG), core.rehearsal_geometry(CFG)
    assert reg.tiles_per_repeat_depth == 111 and reg.tiles_needed() == 3996 and len(reg.cells()) == 24 and reg.all_repeats == (1, 2, 3, 4, 5, 6)
    assert reh.tiles_per_repeat_depth == 28 and reh.tiles_needed() == 840 and reh.all_repeats == (1, 2, 3, 4, 5)
    assert CFG["device"]["store_tiles"] * 1_048_576 == CFG["budget"]["store_file_bytes"] and CFG["device"]["rehearsal_tiles"] * 1_048_576 == CFG["budget"]["rehearsal_file_bytes"]
    assert CFG["device"]["control_tiles"] * 1_048_576 == CFG["budget"]["control_file_bytes"]
    planned = CFG["budget"]["probe_bytes"] + CFG["budget"]["control_file_bytes"] + CFG["budget"]["rehearsal_file_bytes"] + CFG["budget"]["store_file_bytes"]
    assert planned == 5_502_926_848 and planned + CFG["budget"]["store_file_bytes"] == 9_797_894_144 < CFG["budget"]["cap_bytes"]  # section 6's table
    assert CFG["quiet"]["idle_window_seconds"] == CFG["quiet"]["idle_interval_seconds"] * CFG["quiet"]["idle_samples"]


def test_fixed_figures_are_provisional_until_the_lead_writes_them() -> None:
    f = CFG["fixed_after_r1_and_m"]
    if f["provisional"]:
        assert f["m_t"] == 0.0 and f["load_p95"] == 0.0 and not f["timing_spread"]
    else:
        assert f["m_t"] >= CFG["thresholds"]["m_floor"] and f["load_p95"] > 0
    assert core.caps_provisional(CFG) in (True, False) and core.provisional_figures(CFG) in (True, False)


def test_validation_refuses_a_missing_key_a_nonfinite_number_and_a_wrong_grid() -> None:
    import tomllib

    raw = tomllib.loads((ROOT / core.CONFIG).read_text(encoding="utf-8"))
    core.validate_config(raw)
    broken = copy.deepcopy(raw)
    del broken["quiet"]["settle_seconds"]
    with pytest.raises(ValueError, match="lacks"):
        core.validate_config(broken)
    broken = copy.deepcopy(raw)
    broken["thresholds"]["m_floor"] = math.inf
    with pytest.raises(ValueError, match="non-finite"):
        core.validate_config(broken)
    broken = copy.deepcopy(raw)
    broken["cells"]["requests_per_pass"] = [400, 400, 160]
    with pytest.raises(ValueError, match="one value per size"):
        core.validate_config(broken)
    broken = copy.deepcopy(raw)
    broken["experiment_family"] = "OTHER"
    with pytest.raises(ValueError, match="differ"):
        core.validate_config(broken)


def test_nearest_rank_statistics_by_hand() -> None:
    v = [5, 1, 4, 2, 3]
    assert core.median(v) == 3 and core.nearest_rank(v, 0.9) == 5 and core.nearest_rank(v, 0.2) == 1 and core.nearest_rank(v, 0.21) == 2
    assert core.median([1, 2, 3, 4]) == 2  # rank ceil(4 / 2) = 2: the lower middle
    hundred = list(range(1, 101))
    assert core.nearest_rank(hundred, 0.9) == 90 and core.nearest_rank(hundred, 0.99) == 99
    assert core.cv([2.0, 4.0]) == pytest.approx(math.sqrt(2) / 3)  # sample sd sqrt(2), mean 3
    assert core.cv([1.0]) is None and core.cv([0.0, 0.0]) is None
    with pytest.raises(ValueError):
        core.nearest_rank([], 0.5)


def test_keys_carry_every_distinguishing_name() -> None:
    assert core.pass_key("E2", 3, 8, 64, 2) == "E2|r3|k8|s64|a2" and core.parse_pass_key("E2|r3|k8|s64|a2") == ("E2", 3, 8, 64, 2)
    keys = {core.pass_key(st, r, k, s, a) for st in ("E2", "M", "K") for r in (1, 2) for k in (1, 2) for s in (1, 3) for a in (1, 2)}
    assert len(keys) == 3 * 2 * 2 * 2 * 2
    with pytest.raises(ValueError):
        core.pass_key("X", 1, 1, 1)
    with pytest.raises(ValueError):
        core.parse_pass_key("E2|r1|k1")
    assert core.block_key("E2", 6) == "E2|r6|a1"


def test_records_refuse_overwrite_and_nonfinite(tmp_path: Path = Path()) -> None:
    from studies.p10is5 import testing as T

    with T.scratch("config_records") as d:
        p = d / "x.json"
        core.write_record(p, {**core.envelope("pass"), "v": float("nan"), "t": (1, 2)})
        assert core.read_record(p, "pass")["v"] is None and core.read_record(p)["t"] == [1, 2]
        with pytest.raises(FileExistsError):
            core.write_record(p, core.envelope("pass"))
        with pytest.raises(ValueError):
            core.read_record(p, "block")
        with pytest.raises(ValueError):
            core.envelope("nope")


def test_hours_ledger_charges_and_refuses_when_spent() -> None:
    from studies.p10is5 import testing as T

    with T.scratch("config_hours") as d:
        led = core.HoursLedger(d / "h.json", 100.0)
        led.require_room()
        led.charge("E2", "b1", 60.0)
        led.charge("E2", "b2", 40.0)
        assert led.charged() == 100.0
        with pytest.raises(core.LedgerRefused):
            led.require_room()
    assert core.propose_cap_hours(2.0, 1.5) == 5.0
    with pytest.raises(ValueError):
        core.HoursLedger(Path("x"), 0)
