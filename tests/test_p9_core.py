# ruff: noqa: E501
"""P9 package I0: registry, schedules, coefficients, G2 interval, config, identities, record IO, stubs.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import hashlib
import importlib
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm import p8_core  # noqa: E402
from arborlm.io import file_sha256  # noqa: E402
from studies.p9 import core  # noqa: E402

ROOT = core.repo_root()
STUBS = (
    "data",
    "controls",
    "model",
    "objective",
    "train",
    "evaluate",
    "layout",
    "sim",
    "incremental",
    "store",
    "pool",
    "analysis_a",
    "analysis_b",
    "analysis_c",
    "analysis_d",
    "report",
)
LABELS_SHA256 = "63a0723cac111bcee0664b7a4c5c199e3776350b925f45cda1b7f6dd4084206e"


# --- registry ---------------------------------------------------------------------------------------
def test_registry_counts_per_block_and_total() -> None:
    cs = core.cells()
    assert len(cs) == core.TOTAL_CELLS == 100
    expected = {
        "A1": 9,
        "A2": 9,
        "A3": 2,
        "A4": 4,
        "A5": 12,
        "A5b": 4,
        "A6": 4,
        "A7": 8,
        "A8": 6,
        "A10": 6,
        "B1": 8,
        "C1": 8,
        "D1": 6,
        "D2": 14,
    }
    assert core.BLOCK_COUNTS == expected
    assert tuple(expected) == core.BLOCKS
    for block, count in expected.items():
        assert len(core.cells_of_block(block)) == count
    assert [c.index for c in cs] == list(range(100))
    # blocks appear contiguously in ADR order
    order = [c.block for c in cs]
    assert [b for i, b in enumerate(order) if i == 0 or order[i - 1] != b] == list(core.BLOCKS)


def test_replicate_parent_only_in_a1_and_a2() -> None:
    for c in core.cells():
        assert (c.parent == core.REPLICATE_PARENT) == (
            c.parent == (102, 302) and c.block in ("A1", "A2")
        )
    for block in ("A1", "A2"):
        group = core.cells_of_block(block)
        assert sum(c.parent == core.REPLICATE_PARENT for c in group) == 3
        assert all(c.seed == 1701 for c in group if c.parent == core.REPLICATE_PARENT)
    assert {c.seed for c in core.cells()} == {1701, 1702}


def test_labels_unique_stable_and_round_trip() -> None:
    cs = core.cells()
    labels = [c.label for c in cs]
    assert len(set(labels)) == 100
    assert labels == core.all_labels()
    for c in cs:
        assert core.parse_label(c.label) is c or core.parse_label(c.label) == c
    assert labels[0] == "A1-flat-R0-n4096-b101-o301-s1701"
    assert labels[2] == "A1-flat-R0-n4096-b102-o302-s1701"
    assert labels[-1] == "D2-flat-R0-n16384-joint-b101-o301-s1702"
    assert "A7-flat-R1-n65536-k32-b101-o301-s1702" in labels
    assert "C1-tree-R0-n16384-au0p25-ac0p05-b101-o301-s1701" in labels
    assert "A10-flat-R0-n16384-lazy-b101-o301-s1702" in labels
    assert "A4-flat-R0-n65536-fixed-b101-o301-s1701" in labels
    assert hashlib.sha256("\n".join(labels).encode()).hexdigest() == LABELS_SHA256
    with pytest.raises(ValueError):
        core.parse_label("A1-flat-R0-n4096-b101-o301-s9999")
    # a fresh call returns a copy: the registry cannot be mutated through it
    core.cells().pop()
    assert len(core.cells()) == 100


def test_cell_field_ranges_and_configurations() -> None:
    by = {c.label: c for c in core.cells()}
    assert {c.slots for c in core.cells()} == {4096, 16384, 65536}
    a5 = core.cells_of_block("A5")
    assert {(c.rung, c.slots) for c in a5} == {
        (r, s) for r in ("R1", "R2") for s in (4096, 16384, 65536)
    }
    assert {c.slots for c in core.cells_of_block("A5b")} == {16384, 65536}
    assert {c.rung for c in core.cells_of_block("A5b")} == {"R0a"}
    assert {(c.arch, c.rung) for c in core.cells_of_block("A6")} == {
        ("learned_tree", "R1"),
        ("learned_tree", "OB"),
    }
    assert {(c.rung, c.slots, c.key_width) for c in core.cells_of_block("A7")} == {
        (r, s, 32) for r in ("R0", "R1") for s in (16384, 65536)
    }
    assert all(c.optimizer == "lazy" for c in core.cells_of_block("A10"))
    assert all(c.track == "fixed" and c.facts == 2048 for c in core.cells_of_block("A4"))
    assert all(c.arch == "fixed_tree" and c.slots == 16384 for c in core.cells_of_block("A3"))
    assert all(c.arch == "dense" for c in core.cells_of_block("A8"))
    b1 = core.cells_of_block("B1")
    assert {(c.arch, c.alpha_u, c.alpha_c) for c in b1} == {
        (a, u, 0.0) for a in ("flat", "learned_tree") for u in (0.25, 1.0)
    }
    c1 = core.cells_of_block("C1")
    assert {(c.arch, c.alpha_u, c.alpha_c) for c in c1} == {
        (a, 0.25, k) for a in ("flat", "learned_tree") for k in (0.05, 0.25)
    }
    assert all(c.slots == 16384 for c in (*b1, *c1))
    assert {c.lane_d_arm for c in core.cells_of_block("D1")} == {"phaseA"}
    d2 = {(c.arch, c.lane_d_arm) for c in core.cells_of_block("D2")}
    assert d2 == {
        ("flat", "sequential"),
        ("flat", "memory_only"),
        ("learned_tree", "sequential"),
        ("flat", "replay"),
        ("dense", "sequential"),
        ("dense", "replay"),
        ("flat", "joint"),
    }
    assert by["D2-flat-R0-n16384-joint-b101-o301-s1701"].facts == 8192
    assert all(c.facts == 4096 for c in core.cells() if c.lane_d_arm not in (None, "joint"))
    assert all(c.is_lane_d for c in core.cells() if c.block in ("D1", "D2"))
    assert all(c.lane == core.BLOCK_LANE[c.block] for c in core.cells())
    with pytest.raises(ValueError):
        core.Cell(**{**core.cells()[0].fields(), "slots": 1000, "parent": (101, 301)})


def test_fact_counts_per_size_and_track() -> None:
    assert [core.facts_for(s) for s in core.SLOTS_BY_SIZE] == [2048, 8192, 32768]
    assert [core.facts_for(s, "fixed") for s in core.SLOTS_BY_SIZE] == [2048] * 3
    for c in core.cells_of_block("A1"):
        assert c.facts == {4096: 2048, 16384: 8192, 65536: 32768}[c.slots]
    assert core.UNSEEN_FACTS == 2048


def test_dependencies() -> None:
    by = {c.label: c for c in core.cells()}
    for c in core.cells():
        if c.block == "D2" and c.lane_d_arm != "joint":
            assert len(c.depends_on) == 1
            parent = by[c.depends_on[0]]
            assert (parent.block, parent.arch, parent.parent, parent.seed) == (
                "D1",
                c.arch,
                c.parent,
                c.seed,
            )
            assert parent.index < c.index
        else:
            assert c.depends_on == ()
    n_dep = sum(bool(c.depends_on) for c in core.cells())
    assert n_dep == 12  # six non-joint D2 configurations x two seeds
    for blocks in core.ANALYSIS_DEPENDENCIES.values():
        assert set(blocks) <= set(core.BLOCKS)
    assert core.ANALYSIS_DEPENDENCIES["capacity_flat"] == ("A1", "A8")
    assert core.ANALYSIS_DEPENDENCIES["lane_c_gate"] == ("A1", "A2", "B1")


# --- schedules ----------------------------------------------------------------------------------------
def _cell(label: str) -> core.Cell:
    return core.parse_label(label)


def test_updates_for_matched_exposure() -> None:
    sizes = {4096: 512, 16384: 2048, 65536: 8192}
    for slots, u in sizes.items():
        c = _cell(f"A1-flat-R0-n{slots}-b101-o301-s1701")
        assert core.updates(c, 32) == u
        assert core.updates(c, 64) == 2 * u
        assert core.updates(c, 128) == 4 * u
    assert core.updates(_cell("A4-flat-R0-n65536-fixed-b101-o301-s1701"), 32) == 512
    assert core.updates(_cell("D1-flat-R0-n16384-phaseA-b101-o301-s1701"), 32) == 1024
    assert core.updates(_cell("D2-flat-R0-n16384-joint-b101-o301-s1701"), 32) == 2048
    assert core.fixed_compute_updates(32) == 2048
    with pytest.raises(ValueError):
        core.updates(core.cells()[0], 48)
    with pytest.raises(ValueError):
        core.matched_updates(101, 32)


def test_snapshot_and_run_schedule() -> None:
    a1 = {s: _cell(f"A1-flat-R0-n{s}-b101-o301-s1701") for s in core.SLOTS_BY_SIZE}
    assert core.snapshots(a1[4096], 32) == (256, 512, 1024, 2048)
    assert core.snapshots(a1[16384], 32) == (1024, 2048)
    assert core.snapshots(a1[65536], 32) == (1024, 2048, 4096, 8192)
    assert core.snapshots(a1[65536], 64) == (2048, 4096, 8192, 16384)
    assert core.snapshots(a1[4096], 128) == (1024, 2048, 4096, 8192)
    # the 4,096-slot cells run to U_16K
    assert [core.run_updates(a1[s], 32) for s in core.SLOTS_BY_SIZE] == [2048, 2048, 8192]
    fixed = _cell("A4-flat-R0-n16384-fixed-b101-o301-s1701")
    assert core.snapshots(fixed, 32) == (256, 512, 1024, 2048)
    assert core.run_updates(fixed, 32) == 2048
    d1 = _cell("D1-flat-R0-n16384-phaseA-b101-o301-s1701")
    assert core.snapshots(d1, 32) == (512, 1024) and core.run_updates(d1, 32) == 1024
    joint = _cell("D2-flat-R0-n16384-joint-b101-o301-s1701")
    assert core.snapshots(joint, 32) == (1024, 2048)
    for c in core.cells():
        for e in core.EXPOSURE_MENU:
            snaps = core.snapshots(c, e)
            assert list(snaps) == sorted(set(snaps))
            assert max(snaps) == core.run_updates(c, e)
            assert core.updates(c, e) in snaps


def test_contexts_and_batch_arithmetic() -> None:
    assert core.ANSWER_SITES_PER_BATCH == 128 == core.BATCH_CONTEXTS * 8
    replay = _cell("D2-flat-R0-n16384-replay-b101-o301-s1701")
    other = _cell("D2-flat-R0-n16384-sequential-b101-o301-s1701")
    assert core.contexts_per_update(replay) == 32 and core.contexts_per_update(other) == 16
    assert core.answer_exposures_per_update(replay) == 256


def test_position_convention() -> None:
    assert core.CONTEXT_BYTES == 64 and core.INPUT_LENGTH == 63 == core.TARGETS_PER_CONTEXT
    assert [core.answer_site_position(r) for r in range(8)] == [6, 14, 22, 30, 38, 46, 54, 62]
    assert core.answer_target_position(3) == 31
    assert core.ANSWER_SITE_POSITIONS == (6, 14, 22, 30, 38, 46, 54, 62)
    assert core.record_input_positions(0) == (0, 1, 2, 3, 4, 5, 6)
    assert core.record_input_positions(7) == (56, 57, 58, 59, 60, 61, 62)
    assert all(max(core.record_input_positions(r)) <= 62 for r in range(8))
    with pytest.raises(ValueError):
        core.answer_site_position(8)


# --- sizes and coefficients ---------------------------------------------------------------------------
def test_parameter_counts_and_dense_width() -> None:
    assert core.memory_parameters("flat", 4096) == 198145
    assert core.memory_parameters("fixed_tree", 4096) == 198145
    assert core.memory_parameters("learned_tree", 4096) == 198401
    assert (
        core.memory_parameters("learned_tree", 16384)
        == core.memory_parameters("flat", 16384) + 64 * 16
    )
    assert [core.dense_hidden_width(s) for s in core.SLOTS_BY_SIZE] == [3096, 12312, 49176]
    for s in core.SLOTS_BY_SIZE:
        assert 64 * core.dense_hidden_width(s) + 1 == core.memory_parameters("flat", s)
    assert [core.logical_key_products("flat", s) for s in core.SLOTS_BY_SIZE] == [
        4096,
        16384,
        65536,
    ]
    assert [core.logical_key_products("learned_tree", s) for s in core.SLOTS_BY_SIZE] == [
        528,
        576,
        768,
    ]


def test_coefficients() -> None:
    ln32 = math.log(32)
    assert core.usage_floor_support(4096, 2048) == 2048
    assert core.usage_floor_support(16384, 8192) == 8192
    assert core.usage_floor_support(65536, 32768) == 32768
    assert core.usage_ema_rate(8192) == 1 / 64
    # ln M / ln N is 11/12, 13/14, 15/16 at the three sizes
    assert core.lambda_u(1.0, 4096, 2048) == pytest.approx(ln32 * 12 / 11)
    assert core.lambda_u(0.25, 16384, 8192) == pytest.approx(0.25 * ln32 * 14 / 13)
    assert core.lambda_u(1.0, 65536, 32768) == pytest.approx(ln32 * 16 / 15)
    assert core.lambda_u(0.0, 16384, 8192) == 0.0
    assert core.lambda_u(0.25, 16384, 8192) == pytest.approx(0.93308, abs=1e-5)
    assert core.lambda_c(0.0) == 0.0
    assert core.lambda_c(0.25) == pytest.approx(0.25 * ln32 / 0.875)
    assert core.lambda_c(0.05) == pytest.approx(0.05 * ln32 * 8 / 7)
    b1 = _cell("B1-flat-R0-n16384-au1-b101-o301-s1701")
    assert core.lambda_u_for(b1) == pytest.approx(ln32 * 14 / 13)
    assert core.lambda_c_for(b1) == 0.0
    c1 = _cell("C1-tree-R0-n16384-au0p25-ac0p25-b101-o301-s1702")
    assert core.lambda_c_for(c1) == pytest.approx(core.lambda_c(0.25))
    assert core.lambda_u_for(c1) == pytest.approx(core.lambda_u(0.25, 16384, 8192))
    # a fully collapsed memory costs alpha_u times the chance-level answer loss
    assert core.lambda_u(0.25, 16384, 8192) * (math.log(8192) / math.log(16384)) == pytest.approx(
        0.25 * ln32
    )
    assert core.ALPHA_U_DOSES == (0.0, 0.25, 1.0) and core.ALPHA_C_DOSES == (0.0, 0.05, 0.25)


# --- G2 interval and information ----------------------------------------------------------------------
def _exact_mass(n: int, lo: int, hi: int) -> Fraction:
    total = Fraction(0)
    for k in range(lo, hi + 1):
        total += Fraction(math.comb(n, k) * 31 ** (n - k), 32**n)
    return total


def test_g2_level() -> None:
    assert core.g2_level() == pytest.approx(1 - 0.001 / 8)
    assert core.g2_level(core.G2_TESTS_LANE_D) == pytest.approx(1 - 0.001 / 4)


def test_g2_interval_is_exact_central_and_tight_at_2048() -> None:
    n = 2048
    iv = core.chance_interval(n)
    assert iv.n == n and iv.level == pytest.approx(0.999875)
    assert iv.low < 64 < iv.high
    tail = Fraction(1, 1000 * 8 * 2)
    assert _exact_mass(n, 0, iv.low - 1) <= tail < _exact_mass(n, 0, iv.low)
    assert _exact_mass(n, iv.high + 1, n) <= tail < _exact_mass(n, iv.high, n)
    assert _exact_mass(n, iv.low, iv.high) >= Fraction(core.g2_level()).limit_denominator(10**9)
    # roughly mean +/- 3.8 sd, sd = 7.88
    assert 28 <= iv.high - 64 <= 34 and 27 <= 64 - iv.low <= 36
    assert iv.low_accuracy == iv.low / n and iv.high_accuracy == iv.high / n


def test_g2_interval_other_sizes() -> None:
    previous = None
    for n in (2048, 8192, 32768):
        iv = core.chance_interval(n)
        mean = n / 32
        assert iv.low < mean < iv.high
        half = (iv.high - iv.low) / 2
        assert 3.5 * math.sqrt(n * 31 / 1024) < half < 4.3 * math.sqrt(n * 31 / 1024)
        if previous is not None:
            assert iv.high_accuracy < previous  # the accuracy interval tightens with n
        previous = iv.high_accuracy
    lane_d = core.chance_interval(4096, core.G2_TESTS_LANE_D)
    primary = core.chance_interval(4096)
    assert lane_d.high <= primary.high and lane_d.level < primary.level
    with pytest.raises(ValueError):
        core.chance_interval(0)


def test_information_bits() -> None:
    assert core.fano_bits_per_fact(1.0) == pytest.approx(5.0)
    assert core.fano_bits_per_fact(0.5) == pytest.approx(5 - 1 - 0.5 * math.log2(31))
    assert core.fano_bits_per_fact(0.5) == pytest.approx(1.5226, abs=1e-3)
    assert core.fano_bits_per_fact(0.0) == pytest.approx(0.0455, abs=1e-3)  # positive below chance
    assert core.fano_bits_per_fact(1 / 32) == pytest.approx(0.0, abs=1e-12)
    iv = core.chance_interval(2048)
    assert core.at_or_below_chance(iv.high, 2048) and not core.at_or_below_chance(iv.high + 1, 2048)
    assert core.information_bits(iv.high, 2048) == 0.0  # set to 0 at or below the upper end
    assert core.information_bits(0, 2048) == 0.0
    assert core.information_bits(iv.high + 1, 2048) > 0.0
    assert core.information_bits(2048, 2048) == pytest.approx(2048 * 5.0)
    assert core.information_bits(1024, 2048) == pytest.approx(2048 * core.fano_bits_per_fact(0.5))
    with pytest.raises(ValueError):
        core.information_bits(3000, 2048)


def test_score_answer_sites_counts_ties_wrong() -> None:
    import torch

    logits = torch.zeros(3, 256)
    sigma = list(core.ALPHABET)
    logits[0, sigma[5]] = 4.0  # correct (answer 5)
    logits[1, sigma[2]] = 3.0
    logits[1, sigma[7]] = 3.0  # tie between answer 2 and symbol 7 -> wrong
    logits[2, sigma[9]] = 5.0  # wrong
    logits[2, 0] = 50.0  # mass outside the alphabet
    scores = core.score_answer_sites(logits, torch.tensor([5, 2, 1]))
    assert scores.correct.tolist() == [True, False, False]
    assert scores.logp_sigma.exp().sum(-1).tolist() == pytest.approx([1.0, 1.0, 1.0])
    assert scores.mass_sigma[2] < 1e-6 < scores.mass_sigma[0]
    assert scores.p_correct[0] > 0.5
    with pytest.raises(ValueError):
        core.score_answer_sites(logits[:, :10], torch.tensor([0, 0, 0]))


def test_select_exposure_rule() -> None:
    ok = {4096: {32: 0.99, 64: 1.0, 128: 1.0}}
    assert core.select_exposure({**ok, 16384: {32: 0.97, 64: 1.0, 128: 1.0}}) == (32, [])
    assert core.select_exposure(
        {4096: {32: 0.99, 64: 1.0, 128: 1.0}, 16384: {32: 0.5, 64: 0.96, 128: 1.0}}
    ) == (
        64,
        [],
    )
    assert core.select_exposure({4096: {32: 0.5, 64: 0.9, 128: 0.96}}) == (128, [])
    result = core.select_exposure(
        {4096: {32: 0.99, 64: 1.0, 128: 1.0}, 65536: {32: 0.2, 64: 0.5, 128: 0.9}}
    )
    assert result == (32, [65536])
    assert core.select_exposure({65536: {32: 0.2, 64: 0.5, 128: 0.9}}) == (None, [65536])


# --- seeds ------------------------------------------------------------------------------------------------
def test_seeds_as_in_the_adr() -> None:
    assert core.DATA_SEEDS == {
        "facts": 170001,
        "templates": 170011,
        "clusters": 170031,
        "training_order": 170041,
        "calibration_stream": 170051,
        "panel_a": 170061,
        "panel_b": 170071,
        "held_out": 170081,
        "mixed_cluster": 170082,
        "lane_d_a": 170091,
        "lane_d_b": 170092,
        "r1_codes": 170101,
        "branch_hash": 170102,
        "permutation_tests": 170111,
    }
    assert core.NULL_SEEDS_A == (171331, 171332, 171333)
    assert core.NULL_SEEDS_B == (171341, 171342, 171343)
    assert core.INIT_SEEDS == (1701, 1702)
    assert core.PRIMARY_PARENT == (101, 301) and core.REPLICATE_PARENT == (102, 302)
    reg = core.registered_seeds()
    assert reg.panel_a == 170061 and reg.null_seeds_b == core.NULL_SEEDS_B
    assert len(set(reg.data_values())) == 14


def test_rehearsal_seeds_are_disjoint_from_registered() -> None:
    registered = core.registered_seed_values()
    seen: set[int] = set()
    for draw in range(4):
        rs = core.rehearsal_seeds(draw)
        values = [*rs.data_values(), *rs.null_seeds_a, *rs.null_seeds_b]
        assert min(values) >= 179001
        assert not set(values) & registered
        assert not set(values) & seen
        seen |= set(values)
        for v in values:
            core.assert_not_registered_seed(v)
    assert core.rehearsal_seeds(0).facts == 179001
    for bad in (170001, 171331, 1701, 100):
        with pytest.raises(ValueError):
            core.assert_not_registered_seed(bad)
    with pytest.raises(ValueError):
        core.rehearsal_seeds(-1)


# --- config ---------------------------------------------------------------------------------------------
def test_config_matches_constants() -> None:
    cfg = core.load_config()
    assert cfg == core.registered_config()
    assert (ROOT / core.DEFAULT_CONFIG).read_text() == core.render_config_toml()
    assert (
        cfg["spec_reference"] == core.SPEC
        and cfg["frozen_source_sha256"] == core.FROZEN_SOURCE_DIGEST
    )
    assert cfg["alphabet"]["bytes"] == list(range(0x40, 0x60))
    assert (
        cfg["templates"]["pool"] == list(core.TEMPLATE_POOL) and len(cfg["templates"]["pool"]) == 48
    )
    assert cfg["objective"]["alpha_u_doses"] == [0.0, 0.25, 1.0]
    assert cfg["objective"]["alpha_c_doses"] == [0.0, 0.05, 0.25]
    assert (
        cfg["training"]["lazy_learning_rate"] == 0.012 and cfg["training"]["learning_rate"] == 0.003
    )
    assert cfg["training"]["exposure_menu"] == [32, 64, 128]
    assert cfg["capacity"]["step_accuracy_min"] == 0.25
    assert cfg["capacity"]["step_ratio_b101"] == 3.0 and cfg["capacity"]["step_ratio_b102"] == 2.5
    assert cfg["utilization"]["regularizer_movement_ratio"] == 1.5
    assert cfg["locality"]["cache_rows_primary"] == [8, 32]
    assert cfg["limits"]["rss_aggregate_bytes"] == 24 * 1024**3
    assert cfg["limits"]["rss_worker_bytes"] == 3 * 1024**3
    assert cfg["seeds"]["data"] == core.DATA_SEEDS and cfg["seeds"]["rehearsal_base"] == 179001
    assert cfg["matrix"]["total"] == 100 and cfg["matrix"]["block_counts"]["D2"] == 14
    assert cfg["gates"]["g2_tests_primary"] == 8 and cfg["gates"]["g1_tests_per_stream"] == 8
    assert set(cfg["choices"]) == set(core.OPEN_CHOICES)


def test_config_validation_refuses_changes(tmp_path: Path) -> None:
    text = (ROOT / core.DEFAULT_CONFIG).read_text()
    assert core.validate_config(core.load_config()) is not None
    for old, new in (
        ("lazy_learning_rate = 0.012", "lazy_learning_rate = 0.013"),
        ("step_accuracy_min = 0.25", "step_accuracy_min = 0.2"),
        ("alpha_u_doses = [0.0, 0.25, 1.0]", "alpha_u_doses = [0.0, 0.25, 2.0]"),
        ("default_exposure = 32", "default_exposure = 32.0"),  # wrong type
        ("total = 100", "total = 99"),
    ):
        assert old in text
        path = tmp_path / "changed.toml"
        path.write_text(text.replace(old, new))
        with pytest.raises(ValueError):
            core.load_config(path)
    path.write_text(text + "\nextra = 1\n")
    with pytest.raises(ValueError):
        core.load_config(path)


# --- identities ------------------------------------------------------------------------------------------
def test_frozen_source_digest_unchanged() -> None:
    assert p8_core.source_digest() == core.FROZEN_SOURCE_DIGEST
    assert (
        core.FROZEN_SOURCE_DIGEST
        == "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507"
    )
    assert not any("p9" in p.name for p in (ROOT / "src" / "arborlm").rglob("*.py"))


def test_p9_source_digest_covers_exactly_studies_p9() -> None:
    hashes = core.p9_source_hashes()
    assert "studies/p9/core.py" in hashes and "studies/p9/__init__.py" in hashes
    assert all(k.startswith("studies/p9/") and k.endswith(".py") for k in hashes)
    for name in STUBS:
        assert f"studies/p9/{name}.py" in hashes
    assert core.p9_source_digest() == core.p9_source_digest()
    assert len(core.p9_source_digest()) == 64


def test_p9_source_digest_changes_with_content(tmp_path: Path) -> None:
    pkg = tmp_path / "studies" / "p9"
    pkg.mkdir(parents=True)
    (pkg / "a.py").write_text("x = 1\n")
    first = core.p9_source_digest(tmp_path)
    (pkg / "a.py").write_text("x = 2\n")
    second = core.p9_source_digest(tmp_path)
    (pkg / "b.py").write_text("")
    assert len({first, second, core.p9_source_digest(tmp_path)}) == 3


def test_spec_and_config_hashes() -> None:
    assert core.spec_sha256() == file_sha256(ROOT / core.SPEC)
    assert core.config_sha256() == core.config_sha256(ROOT / core.DEFAULT_CONFIG)
    ident = core.code_identity()
    assert ident["frozen_source_sha256"] == core.FROZEN_SOURCE_DIGEST
    assert set(ident) == {"source_sha256", "spec_sha256", "config_sha256", "frozen_source_sha256"}


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    done = subprocess.run(
        ["git", "-C", str(repo), *args], input=stdin, capture_output=True, check=True, env=env
    )
    return done.stdout.decode().strip()


def test_frozen_input_check_against_head() -> None:
    out = core.frozen_input_check(ROOT, "HEAD")
    assert out["ok"], out["problems"]
    assert out["files_compared"] == 85 + 2
    assert out["source_digest"] == core.FROZEN_SOURCE_DIGEST


def test_frozen_input_check_detects_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src" / "arborlm").mkdir(parents=True)
    (repo / "src" / "arborlm" / "a.py").write_text("a = 1\n")
    (repo / "uv.lock").write_text("lock\n")
    (repo / "pyproject.toml").write_text("[project]\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    tree = _git(repo, "write-tree")
    commit = _git(repo, "commit-tree", tree, "-m", "frozen")  # plumbing: no hooks, no signing
    assert core.frozen_input_check(repo, commit, check_p8_digest=False)["ok"]
    (repo / "src" / "arborlm" / "a.py").write_text("a = 2\n")
    changed = core.frozen_input_check(repo, commit, check_p8_digest=False)
    assert not changed["ok"] and "src/arborlm/a.py" in changed["problems"][0]
    (repo / "src" / "arborlm" / "a.py").write_text("a = 1\n")
    (repo / "src" / "arborlm" / "new.py").write_text("")
    assert any(
        "not in the commit" in p
        for p in core.frozen_input_check(repo, commit, check_p8_digest=False)["problems"]
    )
    (repo / "src" / "arborlm" / "new.py").unlink()
    (repo / "uv.lock").write_text("other\n")
    assert any(
        "uv.lock" in p
        for p in core.frozen_input_check(repo, commit, check_p8_digest=False)["problems"]
    )
    (repo / "uv.lock").write_text("lock\n")
    (repo / "pyproject.toml").unlink()
    assert any(
        "pyproject.toml" in p
        for p in core.frozen_input_check(repo, commit, check_p8_digest=False)["problems"]
    )
    with pytest.raises(RuntimeError):
        core.frozen_input_check(repo, "no-such-commit", check_p8_digest=False)


def test_git_blob_sha1_matches_git(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    data = b"hello\nworld\n"
    assert core.git_blob_sha1(data) == _git(repo, "hash-object", "--stdin", stdin=data)


# --- run names and record IO -----------------------------------------------------------------------------
def test_run_names() -> None:
    now = datetime(2026, 11, 14, 4, 37, 53, 8527, tzinfo=UTC)
    name = core.run_name("train", now, "ab" * 16)
    assert name == "P9T-20261114T043753008527Z-" + "ab" * 16
    assert core.parse_run_name(name) == ("train", "20261114T043753008527Z", "ab" * 16)
    assert len(set(core.RUN_STAGE_CODES.values())) == len(core.RUN_STAGE_CODES)
    for stage in core.RUN_STAGE_CODES:
        assert core.parse_run_name(core.run_name(stage))[0] == stage
    assert core.run_name("train") != core.run_name("train")
    with pytest.raises(ValueError):
        core.run_name("nonsense")
    for bad in ("P8T-20261114T043753008527Z-ab", "P9Z-x-y", "P9T-notaz-y", "P9T"):
        with pytest.raises(ValueError):
            core.parse_run_name(bad)


def test_record_io_round_trip_and_refusals(tmp_path: Path) -> None:
    record = {**core.envelope("train"), "label": "x", "value": 1.5, "nested": {"a": [1, 2]}}
    path = tmp_path / "deep" / "train.json"
    core.write_record(path, record)
    assert core.read_record(path) == record
    assert core.read_record(path, "train") == record
    with pytest.raises(ValueError):
        core.read_record(path, "eval")
    with pytest.raises(ValueError):
        core.write_record(tmp_path / "a.json", {"kind": "train", "schema": 1, "study": "P8"})
    with pytest.raises(ValueError):
        core.write_record(tmp_path / "b.json", {"kind": "mystery", "schema": 1, "study": "P9"})
    with pytest.raises(ValueError):  # canonical JSON refuses NaN
        core.write_record(tmp_path / "c.json", {**core.envelope("eval"), "x": float("nan")})
    with pytest.raises(ValueError):
        core.envelope("mystery")
    (tmp_path / "plain.json").write_text('{"a": 1}')
    with pytest.raises(ValueError):
        core.read_record(tmp_path / "plain.json")


def test_cell_directory_layout() -> None:
    run = Path("/runs/P9T-x")
    label = core.cells()[0].label
    assert core.cell_dir(run, label) == run / "cells" / label
    assert core.snapshot_dir(run, label, 512) == run / "cells" / label / "snapshots" / "u0000512"
    assert core.eval_path(run, label, 512, "panel_a").name == "panel_a.json"
    assert core.trace_path(run, label, 512, "calibration", "answer").name == "calibration.answer.pt"
    assert core.sim_path(run, label, 512, "panel_b").parent.name == "u0000512"
    with pytest.raises(ValueError):
        core.cell_dir(run, "not-a-cell")


def test_rehearsal_whitelist_has_no_loss_or_accuracy_key() -> None:
    assert core.REHEARSAL_RECORD_KEYS
    assert not any(
        ("loss" in k and k != "loss_finite") or "accuracy" in k for k in core.REHEARSAL_RECORD_KEYS
    )
    assert {"wall_seconds", "peak_rss_bytes", "shapes", "loss_finite"} <= core.REHEARSAL_RECORD_KEYS


def test_trace_round_trip(tmp_path: Path) -> None:
    import torch

    q = 5
    trace = core.Trace(
        label=core.cells()[0].label,
        update=512,
        stream="panel_a",
        kind="answer",
        slots=4096,
        selected=torch.arange(q * 8).reshape(q, 8) % 4096,
        branches=torch.zeros(q, 2, dtype=torch.int64),
        context=torch.arange(q),
        position=torch.full((q,), 6),
        fact=torch.arange(q),
        cluster=torch.full((q,), -1),
    )
    path = tmp_path / "t" / "panel_a.answer.pt"
    digest = core.write_trace(path, trace)
    assert digest == file_sha256(path)
    back = core.read_trace(path, digest)
    assert back.label == trace.label and back.kind == "answer" and back.slots == 4096
    assert torch.equal(back.selected, trace.selected) and back.branches is not None
    assert torch.equal(back.cluster, trace.cluster)
    with pytest.raises(ValueError):
        core.read_trace(path, "0" * 64)
    trace.kind = "nonsense"
    with pytest.raises(ValueError):
        core.write_trace(tmp_path / "bad.pt", trace)


# --- template pool from the training bytes ---------------------------------------------------------------
def test_template_pool_derivation_on_a_synthetic_corpus() -> None:
    corpus = bytearray()
    for byte in range(256):
        if byte not in core.ALPHABET:
            corpus += bytes([byte]) * (1 + byte % 7)  # many ties; ties broken by byte value
    corpus += bytes(core.ALPHABET) * 100  # alphabet bytes never enter the pool
    pool = core.derive_template_pool(bytes(corpus))
    assert len(pool) == 48 == len(set(pool)) and not set(pool) & set(core.ALPHABET)
    counts = {b: corpus.count(b) for b in pool}
    keys = [(-counts[b], b) for b in pool]
    assert keys == sorted(keys)
    assert core.derive_template_pool(bytes(corpus)) == pool
    with pytest.raises(ValueError):
        core.derive_template_pool(b"abc")


def test_template_pool_literal_equals_the_derivation_from_the_frozen_corpus() -> None:
    root = core.default_experiments_root(ROOT)
    if not core.corpus_path(root).is_file():
        pytest.skip("frozen train.bytes not present in this checkout's experiments/")
    corpus = core.load_trained_corpus(root)
    assert len(corpus) == 2048 * 65
    assert core.derive_template_pool(corpus) == core.TEMPLATE_POOL
    assert len(set(core.TEMPLATE_POOL)) == 48 and not set(core.TEMPLATE_POOL) & set(core.ALPHABET)


# --- stubs -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", STUBS)
def test_stub_modules_import(name: str) -> None:
    module = importlib.import_module(f"studies.p9.{name}")
    assert module.__doc__ and "ADR-0017" in module.__doc__
    assert getattr(module, "__file__", "").endswith(f"{name}.py")


def test_stub_bodies_raise_not_implemented() -> None:
    from studies.p9 import analysis_a, controls, data, model, pool, report, sim, store

    with pytest.raises(NotImplementedError):
        data.build_study_data(core.rehearsal_seeds(0), b"")
    with pytest.raises(NotImplementedError):
        controls.g2_report({}, 8)
    with pytest.raises(NotImplementedError):
        model.build_model(core.cells()[0], None, fact_lut=None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        analysis_a.information_ratio(1.0, 2.0)
    with pytest.raises(NotImplementedError):
        sim.cache_pages(10, 8, 0.25)
    with pytest.raises(NotImplementedError):
        pool.skipped_for_dependency([], [])
    with pytest.raises(NotImplementedError):
        report.study_status([], [])
    with pytest.raises(NotImplementedError):
        store.consistency_test(Path("."), {}, {})


def test_no_stub_module_defines_a_class_that_shadows_core() -> None:
    from studies.p9 import data, evaluate, model

    assert data.FactTable.__module__ == "studies.p9.data"
    assert evaluate.ReadCache.__module__ == "studies.p9.evaluate"
    assert model.Selection.__module__ == "studies.p9.model"
    assert not hasattr(model, "Cell") or model.Cell is core.Cell


def test_no_existing_frozen_file_is_touched_by_p9() -> None:
    # everything P9 adds lives under studies/, configs/p9_*, tests/test_p9_*
    for path in (ROOT / "studies").rglob("*.py"):
        assert "src/arborlm" not in path.as_posix()
