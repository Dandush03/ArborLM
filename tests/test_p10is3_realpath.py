# ruff: noqa: E501
"""P10IS3 tests of the paths that read real inputs, on tiny fixtures written by the tests (no real corpus, no real parents): the parquet loader, ``prepare_data``, ``real_resources``, R2, a successful freeze in a
temporary repository, the registered cap rule and the seed files. The parquet tests need the optional ``pilot`` extra (pyarrow) and are skipped without it: run them with ``uv run --locked --extra pilot pytest``. Self-check only."""

import argparse
import copy
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10i_s3 import core, data, gates, plan, rehearsal, stages, synthetic  # noqa: E402
from studies.p10i_s3 import window_spans as ws  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config()


def small_cfg() -> dict[str, Any]:
    cfg = copy.deepcopy(dict(CFG))
    cfg["data"].update({"rep_ranks": [0, 8], "rep_u_ranks": [8, 16], "fresh_start": 16, "panel_walk_start": 8, "eligible_train": 480, "eligible_validation": 160})
    cfg["setting"]["panel_chunks"] = 4
    return cfg


def texts(rows: int, seed: int, per_row: int = 8) -> list[str]:
    rng = random.Random(seed)
    return ["".join(rng.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(65 * per_row)) for _ in range(rows)]


def _prepare(tmp: Path, state: str = "ABSENT-DECLARED", shared: Path | None = None) -> tuple[dict[str, Any], Path, data.ChunkSet, list[str]]:
    cfg = small_cfg()
    tr, va = texts(60, 935201), texts(20, 935202)
    cs = data.corpus_from_texts(tr, va, 480, 160)
    lay = ws.RowLayout(va)
    win = [{"source": "P10-S2 GEN and ADR-0025 marker-like", "stratum": "marker", "start": 100, "end": 400, "first_row": lay.row_of(100), "last_row": lay.row_of(399)}]
    doc = ws.build_excluded(va, {"windows": win}, ledger_path=None, ledger_absent=True) if state == "ABSENT-DECLARED" else {**ws.build_excluded(va, {"windows": win}, ledger_path=None, ledger_absent=True), "ledger": {"state": "read", "path": "x", "windows": 0}}
    out = tmp / "data"
    consumed = {f"b{101 + p // 3}-o{301 + p % 3}": list(range(8)) for p in range(9)}
    m = rehearsal.prepare_data(cs, va, cfg, ROOT, consumed, {"b101-o301": "d" * 64}, doc, out, shared, expected_hashes={})
    return m, out, cs, va


def test_prepare_data_with_the_ledger_absent_writes_this_studys_spans_first(tmp_path: Path) -> None:
    shared = tmp_path / "shared" / "ledger.json"
    m, out, cs, va = _prepare(tmp_path, "ABSENT-DECLARED", shared)
    assert all(g["passed"] for g in m["gates"].values()) and m["adr0025_ledger"]["state"] == "ABSENT-DECLARED"
    lay = ws.RowLayout(va)
    led = ws.read_ledger(shared, lay)  # this study's own panels, in concatenated bytes, exclusive end
    assert len(led) == 8 and all(w["source"].startswith("P10-I-S3 panel") for w in led) and m["shared_ledger_written"] == str(shared)
    panels = m["panels"]
    assert len(panels["registered"]) == len(panels["calibration"]) == 4 and not set(panels["registered"]) & set(panels["calibration"]) and min(panels["registered"]) >= 8
    # the marker-like window (bytes 100..399) is avoided by every panel chunk
    avoided = ws.excluded_spans(lay, [{"start": 100, "end": 400}])
    chosen = [cs.val_spans[r] for r in panels["registered"] + panels["calibration"]]
    assert data.count_overlaps(chosen, avoided) == 0
    # files and hashes
    mf = json.loads((out / "data_manifest.json").read_text())
    assert {"train_all.bytes", "validation_all.bytes", "panel_ledger.json", "excluded_spans.json"} <= set(mf["files"])
    assert all(file_sha256(out / n) == h for n, h in mf["files"].items())
    # prepare-data refuses to overwrite and refuses an existing shared ledger
    with pytest.raises(plan.StageRefused):
        _prepare(tmp_path, "ABSENT-DECLARED", tmp_path / "other.json")  # the manifest exists


def test_prepare_data_refuses_without_a_ledger_state_or_a_shared_path(tmp_path: Path) -> None:
    cfg = small_cfg()
    cs = data.corpus_from_texts(texts(60, 935201), texts(20, 935202), 480, 160)
    va = texts(20, 935202)
    consumed = {"b": list(range(8))}
    for doc in ({"spans": []}, {"format": "p10i-s3-excluded-spans-v1", "spans": [], "ledger": {"state": "weird"}}):
        with pytest.raises(plan.StageRefused, match="excluded-spans file"):
            rehearsal.prepare_data(cs, va, cfg, ROOT, consumed, {}, doc, tmp_path / "o1", None, expected_hashes={})
    absent = ws.build_excluded(va, {"windows": []}, ledger_path=None, ledger_absent=True)
    with pytest.raises(plan.StageRefused, match="writes its own spans"):
        rehearsal.prepare_data(cs, va, cfg, ROOT, consumed, {}, absent, tmp_path / "o2", None, expected_hashes={})
    existing = tmp_path / "exists.json"
    existing.write_text("{}")
    with pytest.raises(plan.StageRefused, match="writes its own spans"):
        rehearsal.prepare_data(cs, va, cfg, ROOT, consumed, {}, absent, tmp_path / "o3", existing, expected_hashes={})
    assert not (tmp_path / "o1").exists() and not (tmp_path / "o2").exists() and not (tmp_path / "o3").exists()  # nothing written


def test_prepare_data_with_a_ledger_read_does_not_touch_the_shared_ledger(tmp_path: Path) -> None:
    m, out, _, _ = _prepare(tmp_path, "read", None)
    assert m["shared_ledger_written"] is None and m["adr0025_ledger"]["state"] == "read"


def test_real_resources_load_the_manifest_files_and_refuse_a_changed_file(tmp_path: Path) -> None:
    m, out, cs, _ = _prepare(tmp_path, "read", None)
    cfg = small_cfg()
    p = plan.Plan({**core.envelope("freeze_plan"), "mode": "rehearsal", "data": {}, "data_manifest": {"path": str(out / "data_manifest.json")}, "data_dir": str(out), "parent_suite": str(tmp_path / "suite")})
    p.data["synthetic"] = False
    res = stages.real_resources(p, ROOT, cfg)
    assert res.rows["REP"].shape == (8, 65) and res.rows["REP-U"].shape == (8, 65) and res.rows["FRESH"].shape == (480 - 16, 65)
    assert res.rows["REP-U"].tolist() == cs.train_rows[8:16].tolist() and res.rows["FRESH"].tolist() == cs.train_rows[16:].tolist()
    reg = [cs.val_rows[r].tolist() for r in m["panels"]["registered"]]
    assert res.panels["registered"].tolist() == reg and res.panels["calibration"].shape == (4, 65)
    assert res.expected_targets == 32768  # the registered count (a tiny panel is a test device only)
    with (out / "train_all.bytes").open("r+b") as f:
        f.write(b"\x00")
    with pytest.raises(plan.StageRefused, match="PAUSED — IDENTITY"):
        stages.real_resources(p, ROOT, cfg)


# --- the parquet loader (needs pyarrow) ----------------------------------------------------------------------------------------------------
def test_corpus_from_parquet_fixture_matches_corpus_from_texts_and_checks_the_pins(tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow")
    from pyarrow import parquet

    from arborlm.fetch_wikitext import DOWNLOAD_FILES
    from arborlm.pilot_data import select

    tr, va = texts(60, 935203), texts(20, 935204)
    for name, rows in zip(DOWNLOAD_FILES, (tr, va), strict=True):
        parquet.write_table(pa.table({"text": rows}), tmp_path / name)
    pins = {n: {"bytes": (tmp_path / n).stat().st_size, "sha256": file_sha256(tmp_path / n)} for n in DOWNLOAD_FILES}
    n_tr = select(tr, "train", 0)[2]["eligible_unique_chunks"]
    _, full, _ = select(tr, "train", 0)
    n_va = select(va, "validation", 0, excluded=full)[2]["eligible_unique_chunks"]
    cfg = small_cfg()
    cfg["data"].update({"eligible_train": n_tr, "eligible_validation": n_va})
    cs = data.corpus_from_parquet(tmp_path, cfg, pins)
    ref = data.corpus_from_texts(tr, va, n_tr, n_va)
    assert cs.train_rows.tolist() == ref.train_rows.tolist() and cs.val_spans == ref.val_spans and cs.train_spans == ref.train_spans
    assert data.validation_rows(tmp_path) == va
    bad = {**pins, DOWNLOAD_FILES[0]: {**pins[DOWNLOAD_FILES[0]], "sha256": "0" * 64}}
    with pytest.raises(core.EngineeringStop, match="pinned acquisition file mismatch"):
        data.corpus_from_parquet(tmp_path, cfg, bad)
    cfg["data"]["eligible_train"] = n_tr + 1
    with pytest.raises(Exception, match="insufficient|differs"):
        data.corpus_from_parquet(tmp_path, cfg, pins)


# --- R2 --------------------------------------------------------------------------------------------------------------------------------------
def test_run_r2_on_a_tiny_synthetic_resource_set(tmp_path: Path) -> None:
    rec = rehearsal.run_r2(ROOT, tmp_path / "r2", rehearsal.SYNTHETIC_OVERRIDE, synthetic=True, updates=3) if (tmp_path / "r2").mkdir() is None else {}
    t = rec["timing"]
    for arm in core.ARMS:
        assert t[f"seconds_per_update_{arm}"] > 0 and t[f"seconds_per_evaluation_{arm}"] > 0 and t[f"bytes_per_snapshot_{arm}"] > 1e6
    assert t["seconds_per_exhaustive_evaluation_M-TREE"] > 0 and isinstance(t["LOADED"], bool) and "load_average_1min" in t
    assert (tmp_path / "r2" / "r2.json").is_file() and "not an efficiency result" in rec["note"]


# --- a successful freeze in a temporary repository -----------------------------------------------------------------------------------------
def _skeleton(tmp: Path) -> Path:
    """A temporary repository: a copy of the tree (the seed checker reads files of earlier studies), with this study's freeze directory emptied and the config's ``provisional`` cleared as the human lead does after the rehearsal."""
    for rel in ("studies", "src", "configs", "tests", "docs/decisions", "docs/reviews/p10-i-direction-2026-11-17"):
        shutil.copytree(ROOT / rel, tmp / rel, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", "superseded"))
    freeze = tmp / "studies/p10i_s3/freeze"
    shutil.rmtree(freeze)
    freeze.mkdir(parents=True)
    cfg_path = tmp / core.CONFIG
    cfg_path.write_text(cfg_path.read_text().replace("provisional = true", "provisional = false"))
    for f in ("uv.lock", "pyproject.toml"):
        shutil.copy(ROOT / f, tmp / f)
    (tmp / core.RATE_TABLE).write_text(json.dumps(synthetic.rate_table(CFG)))
    return tmp


def _candidate(repo: Path, run: Path, projected: float | None = 10.0) -> argparse.Namespace:
    a = argparse.Namespace(repo=str(repo), run_dir=str(run), data_manifest=None, parent_suite=None, projected_remaining_hours=projected, over_cap_approved=False, supersede=False)
    assert stages.cmd_candidate_plan(a) == 0
    return a


def _record(path: Path, plan_sha: str, provisional: bool = False, stages_done: tuple[str, ...] = ("R1", "R2", "R3")) -> Path:
    core.write_record(path, {**core.envelope("rehearsal_public"), "stages": {s: {"status": "COMPLETE"} for s in stages_done}, "caps_provisional": provisional, "candidate": {"status": "COMPLETE", "plan_file_sha256": plan_sha}})
    return path


def test_candidate_plan_writes_the_seed_files_and_the_freeze_succeeds(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    _candidate(repo, tmp_path / "run")
    # K3 and item 2: the seed plan and the checker copy are real, hashed frozen inputs, regenerated identically
    sp, chk = repo / gates.SEED_PLAN_FILE, repo / gates.CHECKER_FILE
    assert sp.is_file() and chk.is_file()
    p = plan.Plan.load(repo / core.PLAN)
    assert p.data["frozen_files"][str(gates.SEED_PLAN_FILE)] == file_sha256(sp) and p.data["frozen_files"][str(gates.CHECKER_FILE)] == file_sha256(chk)
    assert p.data["seed_files"] == {str(gates.SEED_PLAN_FILE): file_sha256(sp), str(gates.CHECKER_FILE): file_sha256(chk)}
    assert gates.seed_files_problems(repo, core.load_config(repo / core.CONFIG)) == []
    assert "parents[3]" in chk.read_text() and "p10i_s3" in chk.read_text()  # the cited file with exactly the two own-files exclusions (ROOT needs none three levels down)
    plan_sha = file_sha256(repo / core.PLAN)
    rec = _record(tmp_path / "rehearsal_public.json", plan_sha)
    assert stages.cmd_freeze(argparse.Namespace(repo=str(repo), rehearsal=str(rec))) == 0
    fr = json.loads((repo / core.FREEZE_RECORD).read_text())
    assert fr["plan_file_sha256"] == plan_sha and fr["seed_gate"]["passed"] is True and fr["seed_gate"]["checker"]["source"].startswith("frozen file")
    assert fr["seed_gate"]["checker"]["result_line"] == "RESULT: PASS" and len(fr["seed_gate"]["checker"]["copy_sha256"]) == 64 and len(fr["seed_gate"]["checker"]["substitutions"]) == 2
    assert fr["rehearsal_gate"]["passed"] is True
    # the freeze record makes the registered plan verify; a written-once freeze is not rewritten
    plan.verify_plan(p, repo, tmp_path / "run")
    with pytest.raises(plan.StageRefused, match="exists"):
        stages.cmd_freeze(argparse.Namespace(repo=str(repo), rehearsal=str(rec)))


def test_freeze_refusals(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    _candidate(repo, tmp_path / "run")
    plan_sha = file_sha256(repo / core.PLAN)
    ns = lambda rec: argparse.Namespace(repo=str(repo), rehearsal=str(rec))  # noqa: E731
    with pytest.raises(plan.StageRefused, match="provisional"):
        stages.cmd_freeze(ns(_record(tmp_path / "a.json", plan_sha, provisional=True)))  # a measuring rehearsal cannot be frozen on
    with pytest.raises(plan.StageRefused, match="SHA-256"):
        stages.cmd_freeze(ns(_record(tmp_path / "b.json", "0" * 64)))  # the rehearsal rehearsed another plan file
    with pytest.raises(plan.StageRefused, match="SHA-256"):
        stages.cmd_freeze(ns(_record(tmp_path / "c.json", plan_sha, stages_done=("R1", "R2"))))  # R3 is missing
    # a changed seed file, then a changed source file: refused, nothing written
    chk = repo / gates.CHECKER_FILE
    chk.write_text(chk.read_text() + "\n# changed\n")
    with pytest.raises(plan.StageRefused, match="regeneration"):
        stages.cmd_freeze(ns(_record(tmp_path / "d.json", plan_sha)))
    assert not (repo / core.FREEZE_RECORD).exists()


def test_freeze_refuses_when_code_changed_after_the_plan(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    _candidate(repo, tmp_path / "run")
    plan_sha = file_sha256(repo / core.PLAN)
    core_py = repo / "studies/p10i_s3/core.py"
    core_py.write_text(core_py.read_text() + "\n# changed after the plan\n")
    with pytest.raises(plan.StageRefused, match="differs from a re-derivation"):
        stages.cmd_freeze(argparse.Namespace(repo=str(repo), rehearsal=str(_record(tmp_path / "r.json", plan_sha))))


def test_supersede_moves_the_seed_files_aside_too(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    a = _candidate(repo, tmp_path / "run")
    with pytest.raises(plan.StageRefused, match="--supersede"):
        stages.cmd_candidate_plan(a)
    a.supersede = True
    assert stages.cmd_candidate_plan(a) == 0
    sup = repo / "studies/p10i_s3/freeze/superseded"
    assert len(list(sup.glob("seed_plan-*.json"))) == 1 and len(list(sup.glob("seed_registry_check-*.py"))) == 1 and len(list(sup.glob("plan-*.json"))) == 1


# --- the registered cap rule (section 7) ---------------------------------------------------------------------------------------------------
def test_registered_cap_is_charged_plus_two_times_projected_remaining(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _skeleton(tmp_path / "repo")
    cfg = core.load_config(repo / core.CONFIG)
    none = plan.build_plan(mode=plan.REGISTERED, cfg=cfg, repo=repo, run_dir=tmp_path / "run", rate_table=synthetic.rate_table(CFG))
    assert none["caps"]["registered_hours"] == 48.0 and none["caps_provisional"] is True  # 48 h until the rule is applied
    for projected in (0.5, 10.0, 24.0):
        rec = plan.build_plan(mode=plan.REGISTERED, cfg=cfg, repo=repo, run_dir=tmp_path / "run", rate_table=synthetic.rate_table(CFG), projected_remaining_hours=projected)
        assert rec["caps"]["registered_hours"] == 2.0 * projected and rec["caps_provisional"] is False  # charged so far is 0 at candidate time
        assert plan.Plan(rec).cap_seconds("train") == 2.0 * projected * 3600.0
    assert stages.main(["caps-proposal", "--charged-hours", "3", "--projected-remaining-hours", "10"]) == 0
    assert json.loads(capsys.readouterr().out)["proposed_registered_cap_hours"] == 23.0
    # a cap above 48 charged hours goes back to the human lead: the candidate plan refuses unless that extension is declared
    with pytest.raises(plan.StageRefused, match="exceeds 48"):
        stages.cmd_candidate_plan(argparse.Namespace(repo=str(repo), run_dir=str(tmp_path / "run"), data_manifest=None, parent_suite=None, projected_remaining_hours=24.5, over_cap_approved=False, supersede=False))
    assert not (repo / core.PLAN).exists()
    assert stages.cmd_candidate_plan(argparse.Namespace(repo=str(repo), run_dir=str(tmp_path / "run"), data_manifest=None, parent_suite=None, projected_remaining_hours=24.5, over_cap_approved=True, supersede=False)) == 0
    assert plan.Plan.load(repo / core.PLAN).data["caps"]["registered_hours"] == 49.0


def test_synthetic_registry_gate_passes_and_fails_when_the_analysis_is_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    g = gates.synthetic_registry_gate(CFG)
    assert g["passed"] is True and len(g["cases"]) == 10
    from studies.p10i_s3 import labels

    orig = labels.line1
    monkeypatch.setattr(labels, "line1", lambda *a, **k: {**orig(*a, **k), "label": "DEPENDENT"} if not k.get("integrity_stop") else orig(*a, **k))
    bad = gates.synthetic_registry_gate(CFG)
    assert bad["passed"] is False and bad["cases"]["NO CAPACITY"] is False
