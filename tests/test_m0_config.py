# ruff: noqa: E501
"""M0 stage I0-a: the config holds every number of ADR-0033 as a PROPOSAL, and code defaults agree with it."""

from __future__ import annotations

import re

from studies.m0 import config as cfgmod
from studies.m0 import ggen
from studies.m0.power import LADDER

CFG = cfgmod.load()
TEXT = cfgmod.CONFIG_PATH.read_text()

ADR = {  # numbers as the ADR (revision 4) states them
    ("sizes", "tuning_items_per_level_and_part"): 100,
    ("sizes", "development_pool_per_part"): 4000,
    ("sizes", "m0_draw_per_part"): 1500,
    ("sizes", "sealed_pool_per_part"): 20000,
    ("sizes", "k0_development"): 500,
    ("sizes", "nuisance_items"): 150,
    ("sizes", "min_clusters_per_part"): 300,
    ("sizes", "min_families"): 12,
    ("stats", "bootstrap_resamples"): 10000,
    ("stats", "simulation_samples"): 20000,
    ("stats", "confirmation_samples"): 2000,
    ("stats", "alpha"): 0.05,
    ("stats", "power"): 0.8,
    ("stats", "cap_fraction"): 0.5,
    ("stats", "margin_grid"): [0.02, 0.03, 0.05],
    ("stats", "planning_worst_case_tau"): 0.10,
    ("bands", "floor_ceiling_low"): 0.10,
    ("bands", "floor_ceiling_high"): 0.90,
    ("limits", "projection_hours"): 336,
    ("limits", "per_reference_hours"): 72,
    ("limits", "whole_measurement_hours"): 168,
    ("limits", "rehearsal_hours"): 48,
    ("limits", "memory_peak_gib"): 34,
    ("limits", "active_compute_bound"): 1.25,
    ("limits", "download_limit_bytes"): 50_000_000_000,
    ("limits", "prompt_token_limit"): 2048,
    ("limits", "direct_token_limit"): 32,
    ("limits", "worked_token_limits"): [384, 512, 768, 1024],
    ("knowntruth", "tolerance"): 0.03,
    ("knowntruth", "max_monte_carlo_se"): 0.01,
    ("generators", "capacity_factor"): 10,
}
EXEMPT = {"download_limit_bytes", "ngram_length", "salt_bytes", "size_ladder", "min_clusters_for_bootstrap", "n_tier1_systems", "n_taught_single_teacher_systems", "clusters", "n_items", "seed"}


def test_adr_numbers_equal_config_values() -> None:
    for (sec, key), val in ADR.items():
        assert CFG[sec][key] == val, (sec, key)
    assert list(LADDER) == CFG["stats"]["size_ladder"]


def test_every_numeric_value_is_marked_proposed_or_exempt() -> None:
    section = ""
    for line in TEXT.splitlines():
        m = re.match(r"\[(\w+)\]", line)
        if m:
            section = m.group(1)
            continue
        kv = re.match(r"(\w+)\s*=\s*(.+?)(\s+#.*)?$", line)
        if not kv or section == "knowntruth" and kv.group(1).startswith("scenario_"):
            continue
        key, val = kv.group(1), kv.group(2)
        if re.match(r"^[\d\[\-.]", val) and section not in ("meta", "levels", "seeds") and key not in EXEMPT:
            assert "PROPOSED" in line, line
    assert "the human lead's to confirm before the freeze" in TEXT and "nothing confirmed" in TEXT


def test_seeds_are_inside_the_proposed_block_and_code_defaults_agree() -> None:
    s = CFG["seeds"]
    data = [v for k, v in s.items() if isinstance(v, int) and not k.startswith("test_")]
    data += s["sampling_nuisance"]
    assert all(400001 <= v <= 409999 for v in data)
    assert 953001 <= CFG["knowntruth"]["seed"] <= 953999 and s["test_first"] == 953001 and s["test_last"] == 953999
    assert (s["tuning_draw"], s["development_pool"], s["sealed_pool"], s["family_partition"], s["scorer_hand_label_sample"]) == (400001, 400002, 400003, 400004, 400013)
    sz = ggen.Sizes.from_config(CFG)
    assert (sz.development, sz.sealed, sz.m0_draw, sz.tuning_per_level) == (4000, 20000, 1500, 100)
    assert ggen.Sizes() == sz
