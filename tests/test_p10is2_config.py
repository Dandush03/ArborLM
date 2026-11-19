# ruff: noqa: E501
"""P10IS2 config tests (ADR-0025 ruling L6): every threshold and count LISTED here with the ADR section beside it, each required to equal the config's value, and the literal text the entry quotes required
to appear in that section of the ADR so that a change of the ADR text that moves a number is noticed. Self-check only; not independent review. Seeds of the unit tests: 934001-934999."""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is2.common import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ADR = (ROOT / core.SPEC).read_text(encoding="utf-8")
Q = core.load_config("Q")
T = core.load_config("T")


def section(number: str) -> str:
    level = "###" if "." in number else "##"
    m = re.search(rf"^{level} {re.escape(number)}[ .].*?(?=^#{{2,3}} |\Z)", ADR, flags=re.S | re.M)
    assert m, f"section {number} not found"
    return m.group(0)


def at(cfg: Any, path: str) -> Any:
    for part in path.split("."):
        cfg = cfg[part]
    return cfg


# (config, key path, value written in the ADR, ADR section, text quoted from that section)
Q_ROWS = [
    ("panels.q_fit", 2000, "4.1", "| Q_fit | 2,000 |"), ("panels.q_check_block", 500, "4.1", "16 blocks of 500"), ("panels.q_check_blocks_max", 16, "4.1", "16 blocks of 500"),
    ("panels.d_cal", 500, "4.1", "| D_cal; D_con | 500; 300 |"), ("panels.d_con", 300, "4.1", "| D_cal; D_con | 500; 300 |"), ("panels.e_eval", 1000, "4.1", "1,000 each if the data allow; 500; 500"),
    ("panels.e_eval_min", 500, "4.1", "E_A and E_B at least 500 items each"), ("panels.e_combined", 500, "4.1", "1,000 each if the data allow; 500; 500"), ("panels.e_combined_min", 250, "4.1", "E_C at least 250"),
    ("panels.e_open", 500, "4.1", "1,000 each if the data allow; 500; 500"), ("panels.both_reference_min_train", 3300, "4.1", "at least 3,300 training-side"), ("panels.gen_marker_like", 44, "4.1", "44 marker-like"),
    ("panels.gen_ordinary", 100, "4.1", "at least 100 ordinary GEN windows"),
    ("quality.q1_own_score_min", 0.55, "4.2", "| Q1 | Teacher's mean sentence chrF-norm on its own capability, on Q_fit | ≥ 0.55 |"), ("quality.q2_margin_min", 0.30, "4.2", "| ≥ 0.30 |"),
    ("quality.wilson_lower_bound", 0.90, "4.2", "Wilson lower bound of precision on Q_fit is ≥ 0.90"), ("quality.chrf_correct", 0.60, "4.2", "chrF-norm against the best reference is ≥ 0.60"),
    ("quality.q4_precision_min", 0.90, "4.2", "| ≥ 0.90 |"), ("quality.q4_min_accepted", 150, "4.2", "at least 150 accepted items"),
    ("generation.accepted_min", 10000, "4.3", "| 10,000 (ADR-0022's 8,000 × 1.25"), ("generation.accepted_disjoint", 24000, "4.3", "| 24,000 (three disjoint draws of 8,000) |"), ("generation.generation_block_sources", 20000, "4.3", "| 20,000 sources |"),
    ("generation.replicates", 3, "4.3", "replicate r (0, 1, 2)"), ("generation.per_replicate", 8000, "4.3", "8,000·r to 8,000·r + 7,999"), ("generation.batch_size", 32, "4.3", "Batch size 32"), ("generation.threads", 6, "4.3", "Six threads"),
    ("generation.digest_batches", 4, "4.3", "4 whole batches (128 sources)"), ("generation.regeneration_batches", 32, "4.3", "32 whole generation batches per teacher (1,024 sources)"),
    ("generation.split_share_b", 0.8, "4.3", "assigned to B with probability 4/5"), ("scoring.regeneration_score_tolerance", 1e-4, "4.3", "Beam scores are compared within 1e-4"),
    ("seeds.partition", 250901, "6", "250901 partition"), ("seeds.q_fit", 250902, "6", "250902 Q_fit"), ("seeds.q_check_reserve_order", 250903, "6", "250903 Q_check reserve order"), ("seeds.source_split", 250904, "6", "250904 source split"),
    ("seeds.source_block_order", 250905, "6", "250905 source block order"), ("seeds.control_subsample", 250906, "6", "250906 control subsample"), ("seeds.gen_ordinary_windows", 250907, "6", "250907 GEN ordinary windows"),
    ("seeds.teacher_tokenizer_sentences_and_digest", 250908, "6", "250908 teacher tokenizer sentences and digest batches"), ("seeds.tokenization_test_c", 250909, "6", "250909 tokenization test (c)"),
    ("seeds.equivalence_injection", 250910, "6", "250910 equivalence injection vector"), ("seeds.c1_pairing", 250911, "6", "250911 C1 pairing"), ("seeds.seen_items", 250912, "6", "250912 seen items"),
    ("seeds.timing_items", 250913, "6", "250913 timing-benchmark items"), ("seeds.regeneration_subsample", 250914, "6", "250914 regeneration subsample"), ("seeds.bootstrap", 250915, "6", "250915 bootstrap intervals"),
    ("seeds.disjoint_permutation_a", 250916, "6", "250916 permutation of A's pool"), ("seeds.disjoint_permutation_b", 250917, "6", "250917 of B's"), ("seeds.route_accuracy_pieces", 250918, "6", "250918: the 200 WikiText-2 train pieces"),
    ("seeds.rehearsal_partition", 252901, "6", "252901–252914"), ("caps.measuring_rehearsal_hours", 3.0, "10", "**3.0 charged hours for Part Q, 3.0 for Part T**"), ("caps.rehearsal_hours", 3.0, "10", "3.0 charged hours of item 2"),
    ("caps.memory_per_worker_gib", 12.0, "9", "12 GiB per worker in Part Q"), ("caps.workers_max", 2, "19", "at most two workers, six threads and 12 GiB each"), ("caps.disk_gib", 10.0, "9", "New disk: 10 GiB"),
    ("caps.rehearsal_generation_blocks", 2, "10", "limited to two generation blocks per capability"), ("caps.rehearsal_check_blocks", 1, "10", "one Q_check block"),
    ("data.vocabulary", 2000, "16", "2,000-word vocabulary"),
]  # fmt: skip

T_ROWS = [
    ("memory.rows_per_stage", 4096, "5.2", "N = 4,096 rows per stage"), ("memory.lora_rank_single", 42, "5.2", "LoRA rank 42"), ("memory.lora_rank_joint", 84, "5.2", "rank 84"), ("memory.replay_rows", 32, "5.2", "32 replayed first-teacher rows per batch"),
    ("memory.vector_width", 576, "5.2", "576-vector"), ("training.batch", 32, "5.1", "batch 32"), ("training.clip_norm", 1.0, "5.1", "clip 1.0"), ("training.checkpoint_every", 500, "11", "checkpoints every 500 updates"),
    ("training.replicates", 3, "5.4", "(3 replicates, U = …)"), ("calibration.rate_grid_updates", 2000, "7.1", "a stage 1 of 2,000 updates"), ("calibration.rate_grid_read_layer", 4, "7.1", "run at read layer L = 4"),
    ("calibration.rate_tie_tolerance", 0.01, "7.1", "within 0.01 of the best mean"), ("calibration.convergence_tolerance", 0.01, "7.1", "by less than 0.01"), ("calibration.ladder_top", 8000, "7.1", "U = 8,000"),
    ("pilot.gap_min", 0.25, "7.2", "below 0.25"), ("data.gap_denominator_min", 0.30, "8.1", "denominator is ≥ 0.30"), ("data.control_subsample", 300, "5.2", "fixed 300-item subsample"),
    ("data.first_not_acquired_g", 0.50, "8.1", "G_first(V1(X)) ≥ 0.50"), ("gates.acq_gap_min", 0.50, "8.2", "Full-panel G_first(M1) ≥ 0.50"), ("gates.acq_margin_min", 0.30, "8.2", "≥ 0.30"), ("gates.acq_marker_only_max", 0.25, "8.2", "G_marker-only ≤ 0.25"),
    ("gates.acq2_ratio_min", 0.80, "8.2", "≥ 0.80 × G"), ("gates.ret_forgetting_max", 0.03, "8.2", "F(X) ≤ 0.03"), ("gates.ret_rho_min", 0.90, "8.2", "ρ(X) ≥ 0.90"), ("gates.negative_acquisition", 0.25, "8.2", "Acquisition: G < 0.25"),
    ("gates.negative_retention", 0.70, "8.2", "Retention: ρ < 0.70"), ("gates.forgetting_pressure_cells", 4, "8.2", "In at least 4 of the 6 cells"), ("gates.forgetting_pressure_second_min", 0.50, "8.2", "G_second(M-seq) ≥ 0.50"),
    ("gates.forgetting_pressure_rho_max", 0.90, "8.2", "ρ(M-seq) < 0.90"), ("gates.retention_negative_min_cells", 4, "8.3", "At least four cells are evaluable"), ("gates.control_failed_gap", 0.50, "8.3", "gives G ≥ 0.50 in any memory cell"),
    ("gates.gen_loss_margin", 0.02, "8.3", "≤ 0.02 nats per token"), ("gates.dense_margin", 0.05, "8.3", "Δ ≥ +0.05 in every cell"), ("gates.lookup_sufficient_margin", 0.03, "8.3", "b ≥ s(M-append) − 0.03"),
    ("gates.lookup_adds_margin", 0.05, "8.3", "s(M-append) − b ≥ 0.05"), ("gates.second_not_acquired", 0.50, "8.3", "G_second(M-append) < 0.50 in any cell"), ("gates.modification_dcon_tolerance", 0.02, "5.2", "within 0.02 of M-append's"),
    ("gates.modification_floor", 0.10, "5.2", "modification floor 0.10"), ("gates.composes_ratio_min", 0.80, "9", "COMPOSES 0.80 and 0.50"), ("gates.composes_negative", 0.50, "9", "COMPOSES 0.80 and 0.50"),
    ("gates.cells_per_arm", 6, "5.1", "six cells per sequential arm"), ("timing.threads", 6, "10", "six threads"), ("timing.items_per_panel", 200, "10", "200 items per panel"), ("timing.repetitions", 3, "10", "three repetitions"),
    ("timing.quiet_load_max", 2.0, "10", "at most 2.0"), ("timing.quiet_wait_seconds", 60, "10", "at least 60 seconds"), ("timing.start_bound_minutes", 30, "10", "The 30-minute bound"), ("timing.max_attempts", 5, "10", "After five attempts"),
    ("timing.unstable_cv", 0.05, "10", "exceeds 5%"), ("caps.measuring_rehearsal_hours", 3.0, "10", "**3.0 charged hours for Part Q, 3.0 for Part T**"), ("caps.memory_per_worker_gib", 8.0, "9", "8 GiB per worker and 24 GiB aggregate"),
    ("caps.memory_aggregate_gib", 24.0, "9", "8 GiB per worker and 24 GiB aggregate"), ("caps.workers_max", 3, "19", "at most three workers (8 GiB each, 24 GiB aggregate)"), ("caps.workers_max_shared", 2, "19", "at most two while another study runs"),
    ("seeds.analysis_bootstrap", 250915, "6", "250915 bootstrap intervals"), ("seeds.route_accuracy_pieces", 250918, "6", "250918: the 200 WikiText-2 train pieces"), ("seeds.rehearsal_base", 252001, "6", "| Part T rehearsal | 252001"),
    ("seeds.init_rehearsal", 330251, "6", "Rehearsal (both Part T rehearsals): 330251 + j"),
]  # fmt: skip


@pytest.mark.parametrize(("path", "value", "sec", "quote"), Q_ROWS)
def test_part_q_threshold_equals_the_adr(path: str, value: Any, sec: str, quote: str) -> None:
    assert at(Q, path) == value, f"{path}: config {at(Q, path)!r}, ADR section {sec} says {value!r}"
    assert quote in section(sec), f"the ADR section {sec} no longer contains {quote!r}"


@pytest.mark.parametrize(("path", "value", "sec", "quote"), T_ROWS)
def test_part_t_threshold_equals_the_adr(path: str, value: Any, sec: str, quote: str) -> None:
    assert at(T, path) == value, f"{path}: config {at(T, path)!r}, ADR section {sec} says {value!r}"
    assert quote in section(sec), f"the ADR section {sec} no longer contains {quote!r}"


def test_grids_and_lists_equal_the_adr() -> None:
    assert Q["quality"]["tau_grid"] == [-0.05 * k for k in range(1, 13)] or [round(x, 2) for x in Q["quality"]["tau_grid"]] == [round(-0.05 * k, 2) for k in range(1, 13)]
    assert Q["quality"]["ratio_ranges"] == [[0.5, 2.0], [0.6, 1.6]] and "τ ∈ {−0.05, −0.10, …, −0.60}" in section("4.2") and "[0.5, 2.0], [0.6, 1.6]" in section("4.2")
    assert T["calibration"]["store_rates"] == [0.001, 0.003, 0.01] and T["calibration"]["lora_rates"] == [0.0001, 0.0003, 0.001]
    assert "{0.001, 0.003, 0.01}" in section("7.1") and "{0.0001, 0.0003, 0.001}" in section("7.1")
    assert T["calibration"]["ladder_rungs"] == [1000, 2000, 4000] and T["calibration"]["ladder_snapshots"] == [1000, 2000, 4000, 8000] and "{1,000, 2,000, 4,000}" in section("7.1")
    assert T["seeds"]["replicate_bases"] == [250001, 250101, 250201] and T["seeds"]["offsets"] == [1, 2, 4, 10, 13] and "+1 training draw" in section("6") and "+13 router" in section("6")
    assert T["seeds"]["calibration_bases"] == [251001, 251101] and T["seeds"]["repeat_calibration_bases"] == [251201, 251301] and "251001 + 100·i, i = 0, 1" in section("6") and "251201 and 251301" in section("6")
    assert T["seeds"]["init_registered"] == [330201, 330211, 330221] and T["seeds"]["init_calibration"] == [330231, 330241] and T["seeds"]["init_repeat_calibration"] == [330261, 330271]
    assert "330261 + j and 330271 + j" in section("6") and T["seeds"]["init_test"] == [330298, 330299] and "330298, 330299" in section("6")
    assert T["seeds"]["init_roles"] == ["stage-1 store", "appended rows", "M-joint store", "D1", "second adapter of D-append", "D-joint", "E-table", "router projection and keys"]
    assert T["memory"]["read_layers"] == [4, 12] and Q["seeds"]["test_low"] == 934001 and Q["seeds"]["test_high"] == 934999 and "934001–934999" in section("6")
    assert T["arms"]["lookup_best_of"] == ["R-gloss", "R-gloss-icl", "R-nn", "R-icl", "E-table"] and "R-gloss, R-gloss-icl, R-nn, R-icl and E-table" in section("8.3")
    assert T["arms"]["timed_arms"] == ["S0", "M-append", "D-append", "D-seq", "E-table", "R-icl"] and "S0, M-append, D-append, D-seq, E-table and R-icl" in section("10")
    kinds = T["arms"]["combined_arm_cells"]  # "twelve arm-cells per replicate": M-append, M-ii, D-seq and D-append in both orders, M-joint, D-joint, M-sep and D-sep once each
    assert 2 * sum(k in ("M-append", "M-ii", "D-seq", "D-append") for k in kinds) + sum(k in ("M-joint", "D-joint", "M-sep", "D-sep") for k in kinds) == 12 == 12 and "(twelve arm-cells per replicate)" in section("5.5")


def test_the_thresholds_are_not_read_from_p10s2() -> None:
    """No grid, threshold or seed of this study is read from P10-S2's config (section 11 item 2): no module of the package indexes P10-S2's CFG for a value."""
    bad = []
    for p in (ROOT / "studies/p10is2").rglob("*.py"):
        text = p.read_text()
        if re.search(r"p10s2[.\w]*\.core\.CFG|p10s2\.core import CFG|core\.CFG\[", text) and "p10s2" in text:
            bad.append(p.name)
    assert bad == []


def test_config_identity_fields() -> None:
    for cfg, part in ((Q, "Q"), (T, "T")):
        assert cfg["study"] == "P10IS2" and cfg["part"] == part and cfg["spec_reference"] == core.SPEC and isinstance(cfg["caps"]["provisional"], bool)
        assert cfg["platform"] == {"system": "Darwin", "machine": "arm64", "torch": "2.8.0", "torch_num_threads": 6, "deterministic_algorithms": True}
        caps = cfg["stage_caps"]
        if cfg["caps"]["provisional"]:  # before the lead enters the caps computed by code from the measuring record
            assert all(v == 0.0 for v in caps.values())
        else:  # after: every cap is set, and the total is the pre-freeze charge plus twice every stage (the rule of the caps proposal), so it is not below the sum of the stage caps up to the rounding of each (0.01 h)
            stage = {k: v for k, v in caps.items() if k != "total_hours"}
            used = {k: v for k, v in caps.items() if k != "reuse_hours"}  # reuse_hours belongs to a plan that reuses completed stages (attempt 3); the stages a plan does not run keep 0.0
            assert (all(v > 0.0 for v in used.values()) or caps["total_hours"] > 0.0 and any(v > 0.0 for v in stage.values())) and caps["total_hours"] >= sum(stage.values()) - 0.01 * len(stage)
    assert Q["seeds"]["registry_checker_sha256"] == "e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594" == T["seeds"]["registry_checker_sha256"]
    assert core.load_config("Q")["paths"]["durable_packages"] == "/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages"
    with pytest.raises(ValueError):
        core.load_config("T", ROOT / core.CONFIG_Q)
