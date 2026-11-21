# ruff: noqa: E501
"""P10IS1 evaluate-cap extension (docs/decisions/ADR-0024-addendum-evaluate-cap-extension.md): the ledger credit with its offsetting debit, the identity checks a resumed registered command performs (read-only, on a
throw-away frozen repository: what a commit that touches only files outside the frozen roots does and does not change), and the reproduction of the known analysis defect on a tiny synthetic run. Self-check only: not an
independent review, not Astra validation, not human approval."""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import test_p10is1_quiet_rule as qr  # noqa: E402
import test_p10is1_rehearsal as TR  # noqa: E402
import test_p10is1_stages as TS  # noqa: E402

from arborlm.io import read_json  # noqa: E402
from studies.p10is1 import core, items, rehearsal, stages  # noqa: E402
from studies.p10is1 import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "results" / "p10is1-evaluate-cap-extension-20261121"


def load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, EXT / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _canon(monkeypatch: pytest.MonkeyPatch) -> None:
    qr.use_canon(monkeypatch)


def real_shaped_ledger(path: Path) -> list[dict[str, Any]]:
    """A ledger with the shape and the figures of the registered run's (read from its ledger file on 2026-11-21: evaluate spent its whole 1.0 h cap, baselines charged 0.0075 s)."""
    entries = [
        {"run": "H_c", "seconds": 28679.427646419073, "stage": "pre-freeze", "utc": "u"}, {"run": "r", "seconds": 36.62875300005544, "stage": "gates", "utc": "u"}, {"run": "r", "seconds": 198.5286589579191, "stage": "timing", "utc": "u"},
        {"run": "r", "seconds": 16534.440495874966, "stage": "train", "utc": "u"}, {"run": "r", "seconds": 7049.555819960078, "stage": "ladder", "utc": "u"}, {"run": "r", "seconds": 3600.028641999932, "stage": "evaluate", "utc": "u"},
        {"run": "r", "seconds": 0.007532167015597224, "stage": "baselines", "utc": "u"},
    ]  # fmt: skip
    from arborlm.io import write_json

    write_json(path, {"study": core.STUDY, "kind": "ledger", "schema": core.SCHEMA, "total_seconds": 187200.0, "entries": entries})
    return entries


def plan_file(tmp: Path) -> Path:
    pl = TS.plan_of()
    pl.data["stage_caps"] = {"train_hours": 31.0, "evaluate_hours": 1.0, "timing_hours": 1.0, "throughput_hours": 1.0, "analysis_hours": 1.0, "rehearsal_hours": 13.0, "total_hours": 52.0}
    p = tmp / "plan.json"
    p.write_text(json.dumps(core.jsonable(pl.data)))
    return p


def test_the_ledger_credit_opens_the_evaluate_and_baselines_cap_and_leaves_everything_else_as_it_was(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ext = load_script("apply_extension")
    led_path, plan = tmp_path / "P10IS1-ledger.json", plan_file(tmp_path)
    old = real_shaped_ledger(led_path)
    old_text = led_path.read_text()
    led = core.Ledger(led_path, 187200.0)
    pl = planmod.Plan.load(plan)
    assert stages.stage_cap_seconds(pl, "evaluate", led) == 0.0 and stages.stage_cap_seconds(pl, "baselines", led) == 0.0  # the shared cap key is spent: baselines was PAUSED with the cap at zero
    # the dry run writes nothing
    assert ext.main(["--ledger", str(led_path), "--plan", str(plan)]) == 0 and led_path.read_text() == old_text and not list(tmp_path.glob("*.before-*"))
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    total_before = led.charged()
    assert ext.main(["--ledger", str(led_path), "--plan", str(plan), "--apply"]) == 0
    led2 = core.Ledger(led_path, 187200.0)
    entries = led2.entries()
    assert entries[: len(old)] == old and len(entries) == len(old) + 2  # no existing entry changed; two appended
    assert [(e["stage"], e["seconds"]) for e in entries[-2:]] == [("evaluate", -3600.0), (ext.OFFSET_STAGE, 3600.0)] and ext.OFFSET_STAGE not in stages.CAP_KEY
    assert all("approval-sha256=" + __import__("hashlib").sha256((EXT / "APPROVAL.md").read_bytes()).hexdigest() in e["run"] for e in entries[-2:])
    assert abs(led2.charged() - total_before) < 1e-6 and led2.total_seconds == 187200.0  # the TOTAL charged and the total cap are as before
    cap = stages.stage_cap_seconds(pl, "evaluate", led2)
    assert cap == pytest.approx(3600.0 - 0.036174, abs=1e-3) and stages.stage_cap_seconds(pl, "baselines", led2) == pytest.approx(cap)  # the effective evaluate-and-baselines cap is the 2.0 h
    led2.require_room("evaluate")
    for stage in ("train", "ladder", "timing", "throughput", "analysis"):  # the other caps are exactly what they were
        assert stages.stage_cap_seconds(pl, stage, led2) == stages.stage_cap_seconds(pl, stage, led)
    assert (tmp_path / "P10IS1-ledger.json.before-evaluate-cap-extension").read_text() == old_text  # the pre-image, a new file
    with pytest.raises(SystemExit, match="already been applied"):
        ext.main(["--ledger", str(led_path), "--plan", str(plan), "--apply"])
    assert read_json(plan)["stage_caps"]["evaluate_hours"] == 1.0  # the plan's frozen cap is not touched


def test_the_extension_refuses_an_approval_without_the_lead_words_or_the_machine_lines(tmp_path: Path) -> None:
    ext = load_script("apply_extension")
    led_path, plan = tmp_path / "L.json", plan_file(tmp_path)
    real_shaped_ledger(led_path)
    good = (EXT / "APPROVAL.md").read_text()
    for name, text in (("no_quote", good.replace("Approve 1 h", "Maybe")), ("two_hours", good.replace("evaluate_hours +1.0", "evaluate_hours +2.0")), ("other_commit", good.replace("46bf55a5", "00000000")), ("total", good.replace("TOTAL_CAP: unchanged", "TOTAL_CAP: raised"))):
        bad = tmp_path / f"{name}.md"
        bad.write_text(text)
        with pytest.raises(SystemExit, match="refused"):
            ext.main(["--ledger", str(led_path), "--plan", str(plan), "--approval", str(bad), "--apply"])
    assert not list(tmp_path.glob("*.before-*"))
    assert "Approve 1 h" in good and "Do you approve extending S1's evaluate cap by 1 hour" in good and "`Astra review: NOT_PERFORMED`" in good


def test_the_new_files_are_outside_every_frozen_root_and_do_not_match_the_decision_2_glob() -> None:
    for f in (EXT / "APPROVAL.md", EXT / "apply_extension.py", EXT / "verify_resume_identity.py", ROOT / "docs" / "decisions" / "ADR-0024-addendum-evaluate-cap-extension.md", Path(__file__)):
        rel = f.relative_to(ROOT)
        assert not str(rel).startswith(tuple(("studies/p10is1", *planmod.IMPORTED_ROOTS, "configs/", "uv.lock"))), rel
        assert not rel.match(planmod.DECISION_2_GLOB), rel
    assert not any(k.startswith(("results/", "docs/", "tests/")) for k in planmod.frozen_file_hashes(ROOT))
    plan_path = ROOT / core.PLAN
    if plan_path.is_file():  # this worktree holds the freeze: the frozen hashes at the freeze are what they are now
        frozen = read_json(plan_path)
        if frozen.get("mode") == "registered":
            assert frozen["frozen_files"] == planmod.frozen_file_hashes(ROOT)


@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record is macOS arm64")
def test_the_resume_identity_checks_pass_after_a_commit_outside_the_frozen_roots_and_refuse_one_inside_them(tmp_path: Path) -> None:
    """On a throw-away frozen repository (a copy of this tree, a plan, a freeze record and a Decision 2): the registered pre-checks pass; after a commit that adds only the approval folder, a document and a test they still pass
    (the freeze commit is an ancestor of the new HEAD, the frozen files are equal); after a commit that edits a file of studies/p10is1 they REFUSE (PAUSED — IDENTITY). Each is a read-only run of the checks: no stage."""
    repo, commit, run = TR.frozen_repo(tmp_path)
    script = EXT / "verify_resume_identity.py"

    def verify() -> tuple[int, dict[str, Any]]:
        out = subprocess.run([sys.executable, str(script), "--repo", str(repo), "--run-dir", str(run), "--freeze-commit", commit], cwd=repo, env=TR.env_for(repo), capture_output=True, text=True, timeout=600, check=False)  # noqa: S603
        return out.returncode, json.loads(out.stdout) if out.stdout.strip().startswith("{") else {"stderr": out.stderr[-800:]}

    rc, res = verify()
    assert rc == 0 and set(res["results"].values()) == {"PASS"} and len(res["results"]) == 5, res
    (repo / "results" / "p10is1-evaluate-cap-extension-20261121").mkdir(parents=True)
    (repo / "results" / "p10is1-evaluate-cap-extension-20261121" / "APPROVAL.md").write_text("approval\n")
    (repo / "docs" / "decisions" / "ADR-0024-addendum-evaluate-cap-extension.md").write_text("addendum\n")
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_x.py").write_text("x = 1\n")
    TR.git(repo, "add", "-A")
    TR.git(repo, "commit", "-q", "-m", "approval record and addendum")
    head_after = TR.git(repo, "rev-parse", "HEAD").strip()
    assert head_after != commit
    rc2, res2 = verify()
    assert rc2 == 0 and res2["head"] == head_after and set(res2["results"].values()) == {"PASS"}, res2  # nothing a commit outside the frozen roots changes is checked
    (repo / "studies" / "p10is1" / "README_RUN.md").write_text((repo / "studies" / "p10is1" / "README_RUN.md").read_text() + "\nedited\n")
    TR.git(repo, "add", "-A")
    TR.git(repo, "commit", "-q", "-m", "a change inside the frozen root")
    rc3, res3 = verify()
    assert rc3 == 1 and any("differs from the freeze" in v or "frozen file" in v for v in res3["results"].values()), res3
    (repo / "dirty.txt").write_text("x")  # and an uncommitted file refuses too
    rc4, res4 = verify()
    assert rc4 == 1 and any("not clean" in v for v in res4["results"].values())


def test_known_defect_the_analysis_registry_refuses_the_baselines_stage_manifest(tmp_path: Path) -> None:
    """NOT FIXED here (addendum section 6). On a tiny synthetic test-mode run, after the baselines stage is COMPLETE, ``build_registry`` raises because run_dir/baselines/manifest.json (a stage_manifest) matches the glob over
    baseline records. A PAUSED baselines stage writes the same file, so the crash is not specific to a pause: it recurs after baselines completes. When the defect is fixed (under a new freeze) this test must be inverted."""
    root = tmp_path / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    run = root / "run"
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    args = argparse.Namespace(freeze_commit=None, synthetic=True)
    always = {"quiet": True, "load_average": 0.1, "other_study_processes": []}
    for st in ("gates", "baselines"):
        rec = stages.execute_stage(st, pl, ctx, run, pl.path, args, repo=ROOT, inline=True, quiet_reading=lambda: always, end_fn=lambda s: {"ok": True, "other_study_processes": []}, sleep=lambda s: None)
        assert rec["status"] == "COMPLETE"
    assert sorted(p.name for p in (run / "baselines").glob("*.json")) == ["d1_f128.json", "d2_f128.json", "manifest.json"]
    with pytest.raises(ValueError, match="expected a 'baseline' record, got 'stage_manifest'"):
        stages.build_registry(ctx, pl, run)
