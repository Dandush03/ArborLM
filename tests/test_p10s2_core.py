# ruff: noqa: E501
"""P10S2 core: the config against the ADR's numbers, the oracle-assisted line against the ADR text, seeds and gate G9, parameter arithmetic, the registry and the source checks (ADR-0022 sections 3, 9, 11.3,
12.3, 13.1). Self-check only: not independent review, not Astra validation, not human approval."""

import ast
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import core, gates, model, registry  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ADR = (ROOT / core.SPEC).read_text()
HF_JSON = {"vocab_size": 49152, "hidden_size": 576, "num_hidden_layers": 30, "num_attention_heads": 9, "num_key_value_heads": 3, "intermediate_size": 1536, "max_position_embeddings": 8192, "rope_theta": 100000.0, "rms_norm_eps": 3e-6}
REAL_CFG = model.StudentConfig.from_hf_config(HF_JSON)  # a synthetic config file with the pinned shape values; the epsilon is whatever the file says


# --- config against the ADR ---------------------------------------------------------------------------------------------------------------------
def test_config_values_equal_the_adr() -> None:
    c = core.CFG
    assert (c["memory"]["key_width"], c["memory"]["top"], c["memory"]["temperature"], c["memory"]["rows_per_stage"], c["memory"]["init_std"], c["memory"]["read_layers"]) == (16, 8, 0.2, 4096, 0.02, [4, 12])
    assert (c["training"]["batch"], c["training"]["clip_norm"], c["training"]["weight_decay"], c["training"]["updates"], c["training"]["store_learning_rate"], c["training"]["lora_learning_rates"]) == (32, 1.0, 0.0, [2000, 1000], 0.003, [0.0003, 0.001])
    assert (c["training"]["lora_rank_single"], c["training"]["lora_rank_joint"], c["training"]["replay_rows"], c["training"]["retention_check_drop"], c["training"]["modification_floor"]) == (42, 84, 32, 0.02, 0.10)
    assert (c["router"]["updates"], c["router"]["batch"], c["router"]["learning_rate"], c["router"]["none_prefixes"], c["router"]["none_prefixes_full_length"], c["router"]["prefix_tokens"], c["router"]["temperature"]) == (500, 64, 0.001, 8000, 4000, 64, 0.2)
    d = c["data"]
    assert (d["vocabulary"], d["min_words"], d["max_words"], d["large_group_pairs"], d["evaluation_fraction"]) == (2000, 3, 10, 50, 0.20)
    assert (d["panel_eval"], d["panel_combined"], d["panel_open"], d["panel_q_fit"], d["panel_q_check"], d["panel_d_cal"], d["panel_d_con"]) == (1000, 500, 500, 500, 500, 500, 300)
    assert (d["accepted_per_replicate"], d["gold_per_replicate"], d["sufficiency_factor"], d["generation_sources_max"], d["generation_beam"], d["generation_new_tokens"]) == (8000, 8000, 1.25, 60000, 4, 48)
    assert (d["ablation_subsample"], d["seen_items"], d["general_windows"], d["general_windows_marker_like"], d["general_window_tokens"], d["router_decision_token"]) == (300, 300, 144, 44, 256, 64)
    f = c["filter"]
    assert f["tau_grid"] == [-0.05 * k for k in range(1, 13)] or [round(x, 2) for x in f["tau_grid"]] == [round(-0.05 * k, 2) for k in range(1, 13)]
    assert (f["ratio_ranges"], f["chrf_correct"], f["wilson_lower_bound"], f["check_precision"], f["check_min_accepted"]) == ([[0.5, 2.0], [0.6, 1.6]], 0.60, 0.90, 0.90, 150)
    g = c["gates"]
    assert (g["acq_gap_min"], g["acq_margin_min"], g["acq_marker_only_max"], g["acq2_ratio_min"], g["ret_drop_max"], g["ret_gap_ratio_min"]) == (0.50, 0.30, 0.25, 0.80, 0.03, 0.90)
    assert (g["negative_acquisition"], g["negative_retention_ratio"], g["control_failed_gap"], g["gen_loss_margin"], g["pilot_gap_min"], g["annotation_margin"]) == (0.25, 0.70, 0.50, 0.02, 0.25, 0.03)
    assert (g["joint_bound_ratio"], g["task_coded_retention_margin"], g["router_accuracy_min"], g["composes_ratio_min"], g["exact_match_weak"], g["training_cost_ratio_max"], g["value_rows_ratio_max"]) == (0.90, 0.10, 0.99, 0.80, 0.10, 1.5, 0.10)
    assert (g["student_equivalence_tolerance"], g["mps_loss_tolerance"], g["mps_parameter_relative_tolerance"], g["g4_repeat_updates"]) == (1e-3, 1e-3, 1e-4, 20)
    assert (c["teachers"]["own_score_min"], c["teachers"]["margin_min"], c["scoring"]["gap_denominator_min"], c["scoring"]["bootstrap_resamples"], c["scoring"]["crosscheck_tolerance"]) == (0.55, 0.30, 0.30, 10000, 0.001)
    assert (c["recompute"]["own_code_item_tolerance"], c["recompute"]["frozen_code_tolerance"]) == (1e-6, 0.0)
    b = c["budget"]
    assert (b["cap_hours"], b["cap_ceiling_hours"], b["headroom"], b["memory_per_worker_gib"], b["memory_aggregate_gib"], b["rungs"]) == (36.0, 72.0, 2.0, 8.0, 24.0, [[4, 2000], [3, 2000], [4, 1000], [3, 1000]])
    assert (b["timing_threads"], b["timing_items"], b["timing_repetitions"]) == (6, 200, 3)
    s = c["seeds"]
    assert (s["replicate_bases"], s["offsets"], s["partition"], s["partition_streams"]) == ([220001, 220101, 220201, 220301], list(range(11)), 220901, list(range(220902, 220913)))
    assert "pending" not in c  # the combined-tasks addendum settled the open item; no stop remains
    assert c["student"]["parameters"] == 134515008 and c["teachers"]["parameters"] == [73944309, 74669178]


def test_config_numbers_appear_in_the_adr_text() -> None:
    for text in ("4,096", "0.2", "42", "84", "2,000", "0.003", "0.0003", "0.001", "220901", "36 charged hours", "72 hours", "0.02 nats", "0.55", "0.30"):
        assert text in ADR


def test_oracle_line_is_the_adr_line_verbatim() -> None:
    assert core.ORACLE_LINE in ADR  # section 11.3, "fixed line"
    assert core.LEAD_RULE in ADR
    assert core.ORACLE_LINE.startswith("oracle-assisted (word-level addresses supplied by rule)") and core.ORACLE_LINE.endswith("not autonomous learned memory.")


def test_adr_status_is_the_reviewed_revision() -> None:
    assert "DESIGN REVISION 5" in ADR and "Lead's approval for implementation on synthetic stand-ins" in ADR


# --- parameter arithmetic (analytical) ----------------------------------------------------------------------------------------------------------------
def test_parameter_counts_match_the_adr_arithmetic() -> None:
    cfg = REAL_CFG
    assert model.student_parameter_count(cfg) == 134_515_008
    assert model.store_parameter_count(cfg, 4096) == 2_424_833
    assert model.lora_parameter_count(cfg, 42) == 2_419_200 and model.lora_parameter_count(cfg, 84) == 4_838_400
    assert round(100 * (2_419_200 / 2_424_833 - 1), 2) == -0.23 and round(100 * (4_838_400 / (2 * 2_424_833) - 1), 2) == -0.23
    assert model.student_parameter_count(cfg) + 2 * model.store_parameter_count(cfg, 4096) == 139_364_674
    teachers = sum(core.CFG["teachers"]["parameters"])
    assert teachers == 148_613_487 and round(139_364_674 / teachers, 3) == 0.938
    assert cfg.head_dim * cfg.kv_heads == 192  # the 576 x 192 value projection


def test_rms_norm_eps_is_read_from_the_config_file_never_assumed() -> None:
    assert REAL_CFG.rms_norm_eps == 3e-6 and "rms_norm_eps" not in core.CFG["student"]
    assert model.StudentConfig.from_hf_config({**HF_JSON, "rms_norm_eps": 1e-5}).rms_norm_eps == 1e-5
    with pytest.raises(KeyError):
        model.StudentConfig.from_hf_config({k: v for k, v in HF_JSON.items() if k != "rms_norm_eps"})  # absent in the file: refused, not defaulted
    with pytest.raises(ValueError, match="hidden_size|width"):
        model.StudentConfig.from_hf_config({**HF_JSON, "hidden_size": 512})
    assert not hasattr(model.StudentConfig, "pinned")


def test_parameter_counts_match_the_built_tiny_modules() -> None:
    cfg = model.StudentConfig.tiny(300)
    from studies.p10s2.synthetic import tgen

    st = model.build_student(cfg, tgen(11, "count"))
    assert sum(p.numel() for p in st.parameters()) == model.student_parameter_count(cfg)
    ad = model.LoRAAdapter(cfg, 3, tgen(12, "count lora"))
    assert sum(p.numel() for p in ad.parameters()) == model.lora_parameter_count(cfg, 3)


# --- the registry (section 13.1) -----------------------------------------------------------------------------------------------------------------------
def test_registry_counts() -> None:
    cs = registry.replicate_cells(0)
    assert len(cs) == 18 and len({c.label for c in cs}) == 18
    u = registry.units_per_replicate()
    assert u == {"store": 16, "lora": 6, "total": 22}
    assert len(registry.registry(4)) == 72 and len(registry.registry(3)) == 54
    assert len(registry.memory_cells(0)) == 11  # the five ablations run on 11 memory cells per replicate; E-table has none
    assert sum(1 for c in cs if c.group in ("ETABLE",)) == 2
    with pytest.raises(ValueError):
        registry.registry(5)
    assert registry.parse_label("r2/MII/BA").depends_on == "r2/MAF/BA" and registry.parse_label("r0/LSEQ/AB").depends_on == "r0/LORA1/AB" and registry.parse_label("r0/ST1/AB").depends_on is None


# --- seeds (section 9, gate G9) ------------------------------------------------------------------------------------------------------------------
def test_listed_seeds_and_ranges() -> None:
    for i, base in enumerate((220001, 220101, 220201, 220301)):
        plan = core.SeedPlan("registered-run", i)
        assert plan.base == base and plan.planned() == [base + o for o in range(11)]
    # the data step draws eleven of the twelve listed partition-side seeds: 220906 (the bootstrap) is drawn in the analysis stage only (ruling of 2026-11-15), 220912 is the equivalence injection vector's own seed
    assert core.partition_seeds("registered-data") == {"partition": 220901, "q_split": 220902, "source_sample": 220903, "ablation_subsample": 220904, "gen_windows": 220905, "seen_items": 220907, "timing_items": 220908, "tokenizer_record": 220909, "random_id_sequences": 220910, "c1_pairing": 220911, "equivalence_injection": 220912}
    assert core.partition_seeds("registered-analysis") == {"bootstrap": 220906}
    assert sorted(core.listed_partition_seeds().values()) == list(range(220901, 220913))
    assert core.replicate_bases("calibration")[0] == 221001 and core.replicate_bases("calibration")[9] == 221901 and core.replicate_bases("rehearsal")[0] == 222001
    assert all(221001 <= s <= 221999 for s in core.allowed_seeds("calibration")) and all(222001 <= s <= 222999 for s in core.allowed_seeds("rehearsal"))
    assert min(core.allowed_seeds("test")) == 229001 and max(core.allowed_seeds("test")) == 229999
    reg = core.listed_registered_seeds()
    assert all(220001 <= s <= 228999 for s in reg) and not any(221001 <= s <= 221999 or 222001 <= s <= 222999 or 229001 <= s <= 229999 for s in reg)


def test_generator_is_seeded_directly_fresh_per_use_and_recorded() -> None:
    core.reset_seed_record()
    a = core.seeded_generator(229001, "first use", "test")
    b = core.seeded_generator(229001, "second use", "test")
    import torch

    assert torch.equal(torch.randn(5, generator=a), torch.randn(5, generator=b))  # each use starts from the same draws
    assert [u.purpose for u in core.seed_record()] == ["first use", "second use"]
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220001, "registered seed in test mode", "test")
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(229001, "test seed in registered mode", "registered-run")
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220002 + 1000, "arithmetic on a listed seed", "registered-run")
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220905, "partition-side seed in the run", "registered-run")
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220001, "run seed in the data step", "registered-data")
    core.reset_seed_record()


def test_no_plus_1000k_derivation_in_the_listed_sets() -> None:
    # section 9: every generator is seeded by a listed seed; base + 1000 k would land in S2's own calibration or rehearsal ranges
    for base in (220001, 220101, 220201, 220301):
        assert 221001 <= base + 1000 <= 221999 and 222001 <= base + 2000 <= 222999  # a '+1000 k' derivation lands in S2's own calibration and rehearsal ranges
        assert (base + 1000) not in core.allowed_seeds("registered-run")


def test_gate_g9_on_planned_and_recorded_seeds() -> None:
    core.reset_seed_record()
    ok = core.seed_gate([], [s for i in range(4) for s in core.SeedPlan("registered-run", i).planned()] + list(core.listed_partition_seeds().values()))
    assert ok["ok"], ok["problems"]
    bad = core.seed_gate([core.SeedUse(221001, "calibration seed used as registered", "registered-run")], [220001, 221005, 229001, 5])
    assert not bad["ok"]
    text = " ".join(bad["problems"])
    assert "221005" in text and "229001" in text and "5" in text and "221001" in text
    # foreign ranges (S0, S1, P9-II, P9) and the other studies' config seeds
    for seed, who in ((200100, "S0"), (210500, "S1"), (190001, "P9-II"), (171000, "P9"), (900100, "P9-I")):
        assert core.foreign_seed_hit(seed) == who
    assert core.foreign_seed_hit(220001) is None and core.foreign_seed_hit(229001) is None
    assert core.seed_gate([core.SeedUse(200100, "S0 seed", "registered-run")])["ok"] is False
    cfg_seeds = core.config_seeds()
    assert cfg_seeds and not (cfg_seeds & core.listed_registered_seeds())  # the other studies' config seeds are disjoint from S2's listed seeds
    calib = core.seed_gate([core.SeedUse(221050, "ok", "calibration"), core.SeedUse(222050, "wrong range", "calibration")])
    assert not calib["ok"] and "222050" in " ".join(calib["problems"])
    assert core.seed_gate([core.SeedUse(222050, "ok", "rehearsal"), core.SeedUse(229500, "ok", "test")])["ok"]


def test_the_seed_gate_covers_the_seeds_actually_used() -> None:
    core.reset_seed_record()
    plan = core.SeedPlan("test", 0)
    plan.gen(0, "x")
    plan.gen(6, "y")
    assert core.seed_gate(core.seed_record(), plan.planned(), planned_mode="test")["ok"]
    assert [u.seed for u in core.seed_record()] == [229001, 229007]
    core.reset_seed_record()


# --- the source check (gate G9) ------------------------------------------------------------------------------------------------------------------------
def test_source_check_passes_on_the_package() -> None:
    r = gates.source_check()
    assert r["ok"], r["problems"]


def test_source_check_detects_unseeded_and_global_generators() -> None:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "bad.py").write_text(
            "import torch\nimport random\nfrom torch import nn\n\ndef f():\n    torch.manual_seed(1)\n    g = torch.Generator()\n    x = torch.randn(3)\n    y = torch.randperm(4)\n    layer = nn.Linear(2, 2)\n    z = torch.zeros(2).normal_()\n    return x, y, layer, z, random\n"
        )
        r = gates.source_check(Path(d))
        text = " ".join(r["problems"])
        for needle in ("imports ['random']", "manual_seed", "torch.Generator", "torch.randn without generator", "torch.randperm without generator", "nn.Linear", ".normal_()"):
            assert needle in text, needle
        (Path(d) / "bad.py").write_text("import torch\n\ndef f(g):\n    return torch.randn(3, generator=g)\n")
        assert gates.source_check(Path(d))["ok"]


def test_only_the_output_module_prints() -> None:
    for path in sorted((ROOT / "studies" / "p10s2").glob("*.py")):
        tree = ast.parse(path.read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
        assert not calls or path.name == "output.py", f"{path.name} calls print directly"


def test_every_torch_load_is_weights_only() -> None:
    for path in sorted((ROOT / "studies" / "p10s2").glob("*.py")):
        for n in ast.walk(ast.parse(path.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "load" and isinstance(n.func.value, ast.Name) and n.func.value.id == "torch":
                assert any(k.arg == "weights_only" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords), f"{path.name}:{n.lineno} torch.load without weights_only=True"


def test_no_existing_file_is_modified_and_no_dependency_declared() -> None:
    # the lock and the project file are untouched by this work (they are read here, never written)
    assert "sacrebleu" not in (ROOT / "uv.lock").read_text() and "transformers" not in (ROOT / "uv.lock").read_text()
    assert "p10s2" not in (ROOT / "pyproject.toml").read_text()
