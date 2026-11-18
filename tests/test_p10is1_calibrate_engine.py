# ruff: noqa: E501
"""P10IS1 real calibration engine, sealing and logit finiteness (ADR-0024 sections 7 and 14). The engine runs on a tiny config (every length shrunk, test-sized facts) through the adapter on the calibration seeds only;
the sealed directory is refused inside a git working tree, under the ArborLM checkout and through symlinks; a scan finds no sealed value in any public file. Self-check only."""

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import test_p10is1_calibrate as TC  # noqa: E402
import torch  # noqa: E402

from studies.p10is1 import calibrate, calibrate_engine, core, items, rehearsal, sealed  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACTS_MAP = {2048: 128, 8192: 128, 32768: 128}


def tiny_cfg_path(tmp: Path) -> Path:
    text = rehearsal.tiny_config_text()
    for old, new in (
        ('provisional_readout = { "2048" = 8192, "8192" = 8192, "32768" = 16384 }', 'provisional_readout = { "2048" = 16, "8192" = 16, "32768" = 32 }'), ("loaded_readout = 65536", "loaded_readout = 64"),
        ("u_p_candidates = [8192, 16384, 32768, 65536]", "u_p_candidates = [16, 32, 64, 128]"), ("u_p_ceiling = 65536", "u_p_ceiling = 128"),
        ('calibration_ceiling = { "8192/1024" = 1572864, "2048/256" = 1572864, "32768/4096" = 3145728 }', 'calibration_ceiling = { "8192/1024" = 192, "2048/256" = 192, "32768/4096" = 192 }'),
    ):  # fmt: skip
        assert old in text, old
        text = text.replace(old, new)
    p = tmp / "tiny.toml"
    p.write_text(text)
    return p


def make_engine(tmp: Path) -> tuple[calibrate_engine.RealEngine, items.Ctx]:
    cfgp = tiny_cfg_path(tmp)
    ctx = items.Ctx("calibration", tmp / "sealed", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfgp)
    return calibrate_engine.RealEngine(ctx, core.load_config(cfgp), FACTS_MAP), ctx


# --- sealing ---------------------------------------------------------------------------------------------------------------------------
def test_sealed_dir_is_refused_in_a_work_tree_under_the_checkout_and_through_symlinks(tmp_path: Path) -> None:
    ok = sealed.check_sealed_dir(tmp_path / "sealed" / "x")
    assert ok == (tmp_path / "sealed" / "x").resolve()
    for bad in (ROOT / "experiments" / "_scratch" / "s", Path("/Users/daniellaloush/dandush03/ArborLM/anything"), ROOT):
        with pytest.raises(sealed.SealedRefused, match="under"):
            sealed.check_sealed_dir(bad)
    link = tmp_path / "link"
    link.symlink_to(ROOT / "experiments")
    with pytest.raises(sealed.SealedRefused):
        sealed.check_sealed_dir(link / "sub")  # a symlink into the checkout resolves into it
    repo = tmp_path / "wt"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)  # noqa: S603, S607
    with pytest.raises(sealed.SealedRefused, match="inside a git working tree"):
        sealed.check_sealed_dir(repo / "deep" / "er")
    link2 = tmp_path / "link2"
    link2.symlink_to(repo)
    with pytest.raises(sealed.SealedRefused, match="git working tree"):
        sealed.check_sealed_dir(link2 / "x")


class Distinct(TC.TableEngine):
    """The table engine with values nobody could write by accident: every readout carries 0.0012345 noise."""

    def measure(self, unit: str, rate: float, readout: int) -> calibrate.RateRun:
        r = super().measure(unit, rate, readout)
        return calibrate.RateRun(r.readout_a_use - 0.0012345, r.min_all - 0.0012345, {u: v - 0.0012345 for u, v in r.walk.items()}, r.diverged)


def test_public_files_hold_no_sealed_value(tmp_path: Path) -> None:
    eng = Distinct({2048: 16384, 8192: 8192, 32768: 16384}, TC.LADDER_OK, h8_extra={"2K/4K": 0.8765432, "8K/16K": 0.9234567})
    sd, pd = tmp_path / "sealed", tmp_path / "public"
    pub = calibrate_engine.run_and_seal(eng, sd, pd)
    assert pub["complete"] and pub["row_u_p"] == {"2048": 16384, "8192": 8192, "32768": 16384} and pub["rates"]["F-OQ|1024"] == 0.01
    full = (sd / "calibration_full.json").read_text()
    sealed_values = ["0.8987655", "0.8887655", "0.8765432", "0.9234567", "0.7987655"]
    assert any(v in full for v in sealed_values[:2]) and "readout_a_use" in full and "u_p_detail" in full
    for f in pd.rglob("*"):
        if f.is_file():
            text = f.read_text()
            assert not any(v in text for v in sealed_values), f.name
            for key in sealed.SEALED_KEYS_FORBIDDEN_IN_PUBLIC:
                assert f'"{key}"' not in text, (f.name, key)
    wl = json.loads((pd / "calibration_public_whitelist.json").read_text())
    assert set(wl["public_keys"]) == set(sealed.PUBLIC_KEYS)
    rec = json.loads((pd / "calibration_public.json").read_text())
    assert set(rec) <= set(sealed.PUBLIC_KEYS) | {"kind", "schema", "study", "h8"}
    assert not any("0." in str(v) and len(str(v)) > 6 for k, v in rec["ladder"]["8K/1K"].items() if k not in ("note", "options"))  # lengths only
    # nothing public may hold a key outside the whitelist
    with pytest.raises(ValueError, match="outside the whitelist"):
        sealed.assert_public({**rec, "selections": {}})
    with pytest.raises(ValueError, match="sealed"):
        sealed.assert_public({**rec, "h8": {"results": 1}})


def test_calibrate_command_refuses_a_sealed_dir_inside_the_checkout(tmp_path: Path) -> None:
    from studies.p10is1.calibrate_engine import cmd_calibrate

    args = argparse.Namespace(sealed_dir=str(ROOT / "experiments" / "_scratch" / "sealed_x"), run_dir=str(tmp_path / "run"))
    with pytest.raises(core.StageRefused):
        cmd_calibrate(args, make_engine=lambda ctx: Distinct({2048: 8192, 8192: 8192, 32768: 16384}, TC.LADDER_OK))
    assert not (tmp_path / "run").exists() and not (ROOT / "experiments" / "_scratch" / "sealed_x").exists()
    ok = argparse.Namespace(sealed_dir=str(tmp_path / "sealed"), run_dir=str(tmp_path / "run"))
    assert cmd_calibrate(ok, make_engine=lambda ctx: Distinct({2048: 8192, 8192: 8192, 32768: 16384}, TC.LADDER_OK)) == 0
    assert (tmp_path / "run" / "calibration_public.json").is_file()


# --- the real engine, tiny --------------------------------------------------------------------------------------------------------------
def test_engine_measures_on_calibration_seeds_continues_runs_and_seals_records(tmp_path: Path) -> None:
    eng, ctx = make_engine(tmp_path)
    r = eng.measure("F-OQ|1024", 0.003, 16)
    assert isinstance(r.readout_a_use, float) and set(r.walk) == {8, 4, 2, 1} and isinstance(r.diverged, bool)
    sd = ctx.run_dir
    cells = list((sd / "train" / "cells").iterdir())
    assert len(cells) == 2 and all("_CAL_" in c.name or c.name.startswith("P_") or "CAL" in c.name for c in cells) and not any(c.name.startswith("TEST_") for c in cells)
    # the same (cell, rate, draw) at a later readout CONTINUES the run (a segment from the optimizer snapshot), it is not restarted
    eng.measure("F-OQ|1024", 0.003, 32)
    rec = json.loads(next(iter((sd / "train" / "cells").iterdir())).joinpath("cell_train.json").read_text())
    assert [(s["from"], s["to"]) for s in rec["segments"]] == [(0, 16), (16, 32)]
    # the draw's seed set is the calibration set, never a registered one
    assert {json.loads((c / "cell_train.json").read_text())["seed_name"] for c in (sd / "train" / "cells").iterdir()} == {"p10is1-cal-1", "p10is1-cal-2"}
    with pytest.raises(ValueError, match="refused"):
        spec = eng.spec("F-OQ", 2048, 1024, 1, 0.003)
        adapter_spec = {**spec, "seed_name": core.registered_seeds(1).name, "seed_base": core.registered_seeds(1).facts}
        from studies.p10is1 import adapter

        adapter.assert_seed_allowed("calibration", adapter_spec)
    views_f, views_r = eng.row_up(2048, 0.003, 0.003)
    assert set(views_f) == {16, 32, 64, 128} and set(views_r) == {16, 32, 64, 128} and all(len(v) in (0, 4) for v in views_f.values())
    h8 = eng.h8_extra({"H8|4096": 0.003, "H8|16384": 0.003, **{u: 0.003 for u in core.units(eng.cfg)}}, {2048: 16, 8192: 16})
    assert set(h8) == {"2K/4K", "8K/16K"} and all(0.0 <= v <= 1.0 for v in h8.values())


def test_engine_ladder_views_continue_the_loaded_runs_up_the_ladder(tmp_path: Path) -> None:
    eng, ctx = make_engine(tmp_path)
    eng.measure("F-OQ|8K/1K", 0.003, 64)  # the loaded-cell unit at its readout (64 in the tiny config)
    v = eng.ladder_views("8K/1K", "F-OQ", 0.003, 192)
    assert set(v) == {(1, "A"), (1, "B"), (2, "A"), (2, "B")} and all(32 in s or 64 in s for s in v.values())
    rec = json.loads(next(iter((ctx.run_dir / "train" / "cells").iterdir())).joinpath("cell_train.json").read_text())
    assert rec["segments"][0]["from"] == 0 and rec["segments"][1]["from"] == 64  # no new run: the 64-update checkpoint continues


def test_logit_watch_covers_every_logit_and_stops_on_a_non_finite_one(tmp_path: Path) -> None:
    eng, ctx = make_engine(tmp_path)
    spec = eng.spec("F-OQ", 2048, 1024, 1, 0.003)
    data, seeds = eng.data_for(spec)
    from studies.p10s1.model import build_model

    model = build_model("F-OQ", 1024, spec["init_seed"], items.backbone_of(ctx), r1_seed=seeds.r1_codes, hash_seed=0, seed_rng=False)
    with torch.no_grad(), items.LogitWatch(model) as w:
        from studies.p10s1 import evaluate as ev

        ev._read_record(model, data, spec["facts"], seeds, deep=False, robustness=False)
    assert w.seen >= 5 and w.bad == 0  # many forward passes: main, memory off, swap, shuffle, secondary streams
    with pytest.raises(ValueError, match="engineering stop"):
        with torch.no_grad(), items.LogitWatch(model):
            model.backbone.final_norm.weight.data[0] = float("nan")
            ev._read_record(model, data, spec["facts"], seeds, deep=False, robustness=False)
    with pytest.raises(ValueError, match="no logits"):
        with items.LogitWatch(model):
            pass


def _unused(_: Mapping[str, Any]) -> None:
    return None
