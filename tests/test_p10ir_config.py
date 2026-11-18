# ruff: noqa: E501
"""P10IR config tests (ADR-0029 sections 4 to 6, 8 to 13). The threshold test LISTS every threshold in the test with the ADR section beside it (it does not parse numbers out of prose); for each
entry it also requires that the literal text the entry quotes appears in that section of the ADR, so that a change of the ADR text that moves a number is noticed. Self-check only: not independent
review, not Astra validation, not human approval. Seeds of the unit tests: 938001-938999 only; nothing here touches a registered seed or the experiments directory."""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10ir import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ADR = (ROOT / core.SPEC).read_text(encoding="utf-8")


def section(number: str) -> str:
    """The text of ADR section ``number`` (``8.1`` or ``11``): from its heading to the next heading of the same or a higher level."""
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
    ("thresholds.gap_bits", 0.5, "8.1", "i(Y) − i(X) ≥ 0.5 bits"),
    ("thresholds.restored_margin_bits", 0.25, "8.1", "i(Y) − i(X) ≤ 0.25 bits"),
    ("thresholds.restored_ratio", 0.90, "8.1", "i(X) ≥ 0.90 · i(Y)"),
    ("thresholds.floor_i_bits_printed", 0.473, "8.1", "0.473 bits"),
    ("thresholds.floor_a_use", 0.25, "8.1", "a_use ≥ 0.25"),
    ("thresholds.h_margin_bits", 0.25, "8.3", "i(T2) ≤ i(T0) − 0.25"),
    ("thresholds.closure", 0.5, "8.3", "g_P ≥ 0.5"),
    ("thresholds.recall_r", 0.90, "8.3", "CR8(T0) ≥ 0.90"),
    ("thresholds.plateau_gain_bits", 0.10, "9", "≤ 0.10 bits"),
    ("thresholds.still_learning_min_replicates", 2, "9", "at least 2 of 5 replicates"),
    ("thresholds.tree_candidates", 512, "8.4", "c\\* ≤ 512"),
    ("thresholds.replicates", 5, "8.2", "The denominator is always 5"),
    ("thresholds.label_min_replicates", 4, "8.2", "at least 4 of 5 replicates"),
    ("thresholds.not_evaluable_min_replicates", 2, "8.2", "at least 2 of its 5 replicates"),
    ("gates.tie_margin", 1e-5, "11", "differ by at most 1e-5"),
    ("gates.weight_tolerance", 1e-6, "11", "weights equal within 1e-6 absolute"),
    ("gates.tie_share_max", 0.001, "11", "more than 0.1% of facts fails the gate"),
    ("reads.visit_sweep", [1, 2, 4, 8], "6", "v ∈ {1, 2, 4, 8}"),
    ("reads.index_budgets", [128, 256, 512, 1024, 2048], "6", "c ∈ {128, 256, 512, 1,024, 2,048}"),
    ("reads.index_list_size", 64, "6", "k-means into N/64 lists"),
    ("reads.index_standard_budget", 512, "6", "I256@512"),
    ("reads.index_standard_list_size", 256, "6", "N/256 lists, at least 512 candidates"),
    ("reads.lloyd_iterations", 10, "12", "ten Lloyd iterations"),
    ("reads.branch_size", 256, "3", "N/256 branches"),
    ("reads.visit_registered", 2, "3", "The two best branches are visited"),
    ("reads.top", 8, "3", "The top 8 are selected"),
    ("reads.temperature", 0.2, "3", "/0.2"),
    ("a2.learning_rate", 0.003, "10", "Learning rate 0.003"),
    ("seeds.bridge_base", 290001, "5", "290001 + 100(d − 1)"),
    ("seeds.bridge_stride", 100, "5", "100(d − 1)"),
    ("seeds.bridge_draws", 5, "5", "d = 1..5"),
    ("seeds.bridge_index_offset", 60, "5", "index seed at base + 60"),
    ("seeds.bridge_init_base", 330600, "5", "330600 + d"),
    ("seeds.index_seeds", [298001, 298002, 298003], "5", "298001, 298002, 298003"),
    ("seeds.rehearsal_base", 299201, "5", "299201"),
    ("seeds.rehearsal_init", 330692, "5", "330692"),
    ("seeds.test_init", [330698, 330699], "5", "330698, 330699"),
    ("seeds.test_range", [938001, 938999], "5", "938001–938999"),
    ("seeds.p10s1_draw_base", 210001, "5", "bases 210001–210401"),
    ("seeds.identity_gate_updates", [512, 1024, 2048], "10", "512, 1,024, 2,048 updates"),
    ("seeds.identity_gate_cell", [8192, 4096], "10", "8K/4K, draw 1"),
    ("resources.rss_worker_bytes", 3 * 1024**3, "12", "3 GiB per worker"),
    ("resources.rss_aggregate_bytes", 18 * 1024**3, "12", "18 GiB aggregate"),
    ("resources.workers", 6, "13", "Six workers"),
    ("platform.torch", "2.8.0", "13", "torch 2.8.0"),
    ("platform.torch_num_threads", 1, "13", "torch.set_num_threads(1)"),
    ("platform.torch_interop_threads", 1, "13", "one interop thread"),
    ("platform.deterministic_algorithms", True, "13", "deterministic algorithms on"),
    ("seed_ranges.checker_sha256", "e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594", "5", "e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594"),
]


@pytest.mark.parametrize(("path", "expected", "sec", "literal"), THRESHOLDS, ids=[t[0] for t in THRESHOLDS])
def test_every_threshold_in_the_adr_equals_the_configs_value(path: str, expected: Any, sec: str, literal: str) -> None:
    cfg = core.load_config()
    assert at(cfg, path) == expected, f"{path}: config {at(cfg, path)!r} differs from the ADR section {sec} value {expected!r}"
    assert literal in section(sec), f"the ADR section {sec} no longer contains {literal!r}"


def test_cells_are_the_seven_of_section_4() -> None:
    cfg = core.load_config()
    got = {(c.facts, c.slots): (c.role, c.u_p, c.run, tuple(sorted(c.trajectory))) for c in core.cell_specs(cfg)}
    want = {
        (2048, 1024): ("printed", 8192, 49152, (16384, 32768)), (2048, 4096): ("printed", 8192, 49152, (16384, 32768)), (8192, 4096): ("primary", 8192, 49152, (16384, 32768)),
        (8192, 16384): ("printed", 8192, 49152, (16384, 32768)), (32768, 16384): ("primary", 16384, 98304, (32768, 65536)), (8192, 1024): ("loaded", 8192, 393216, (49152, 196608)),
        (32768, 4096): ("loaded", 16384, 786432, (98304, 393216)),
    }
    assert got == want
    s4 = section("4")
    for facts, slots in want:
        assert core.cell_name(facts, slots) in s4 or core.cell_name(facts, slots) in ADR
    assert [c.name for c in core.primary_cells(cfg)] == ["8K/4K", "32K/16K"]  # section 9


def test_a2_cells_are_the_two_primary_cells() -> None:
    cfg = core.load_config()
    assert [list(c) for c in cfg["a2"]["cells"]] == [[8192, 4096], [32768, 16384]]
    assert cfg["a2"]["arms"] == ["F-OQ", "T-OQ"]


def test_the_floor_is_fano_of_a_use_025_and_prints_as_0_473() -> None:
    from studies.p10s1 import core as s1

    cfg = core.load_config()
    th = core.Thresholds.from_config(cfg)
    assert th.floor_i_bits == s1.PLATEAU_FLOOR_I
    assert round(th.floor_i_bits, 3) == cfg["thresholds"]["floor_i_bits_printed"]


def test_thresholds_object_carries_exactly_the_config_values() -> None:
    cfg = core.load_config()
    th = core.Thresholds.from_config(cfg)
    assert (th.gap_bits, th.restored_margin_bits, th.h_margin_bits, th.restored_ratio, th.closure, th.recall_r, th.plateau_gain_bits) == (0.5, 0.25, 0.25, 0.90, 0.5, 0.90, 0.10)
    assert (th.tree_candidates, th.replicates, th.label_min_replicates, th.not_evaluable_min_replicates, th.still_learning_min_replicates) == (512, 5, 4, 2, 2)
    assert (th.tie_margin, th.weight_tolerance, th.tie_share_max) == (1e-5, 1e-6, 0.001)


def test_no_threshold_literal_is_hard_coded_in_the_label_and_analysis_code() -> None:
    """The labels take every threshold from ``core.Thresholds``; a threshold typed into the code could drift from the config. The only numeric literals allowed are 0/1/2-type structure and EPS."""
    for name in ("labels.py", "analysis.py"):
        src = (ROOT / "studies" / "p10ir" / name).read_text(encoding="utf-8")
        code = "\n".join(line.split("#")[0] for line in src.splitlines())
        code = re.sub(r'""".*?"""', "", code, flags=re.S)
        code = re.sub(r'"[^"\n]*"', '""', code)
        for bad in ("0.473", "0.90", "0.25", "0.5", "512", "0.10"):
            assert not re.search(rf"(?<![\w.]){re.escape(bad)}(?![\w.])", code), f"{bad} appears as a literal in {name}"


def test_spec_hash_is_provenance_only_and_the_adr_is_not_a_frozen_input() -> None:
    assert core.SPEC not in str(core.CONFIG)
    assert len(core.spec_sha256()) == 64


def test_config_validation_refuses_a_missing_key(tmp_path: Path) -> None:
    text = (ROOT / core.CONFIG).read_text(encoding="utf-8").replace("closure = 0.5", "closure_x = 0.5", 1)
    p = tmp_path / "bad.toml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="lacks"):
        core.load_config(p)


def test_caps_are_provisional_until_the_human_lead_sets_them() -> None:
    cfg = core.load_config()
    assert core.caps_provisional(cfg) is True
    assert core.cap_hours("rehearsal", cfg) == 1.0 and core.cap_hours("a1", cfg) == 5.0 and core.cap_hours("a2", cfg) == 1.5
    assert core.propose_cap_hours(1.0, 2.0) == 5.0  # section 12: charged + 2 x projected remaining
