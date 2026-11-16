# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: the freeze takes the layer, the learning rates, the pilot result, the cap and the device from the records and never from typed values (audit B M11); a failed pilot, a
failed pre-freeze gates stage, a registered seed, a cap raise that is not the recomputed one and a device other than MPS stop it; refusals leave no file in the frozen folder; the run decision is a committed
file after the freeze commit with the exact line ``DECISION: RUN`` and the full freeze commit hash; ``--freeze-commit`` must be the commit that added the plan (m5). No test here fails once freeze files exist
in the repository (each asserts "both or neither"). Self-check only: not independent review, not Astra validation, not human approval."""

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_budget import hours, rates, scale_for  # noqa: E402

from studies.p10s2 import budget, core, freeze  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FROZEN_FILES = ("plan.json", "stage_caps.json", "rehearsal_outcome.json", "projection.json")


def git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a], capture_output=True, text=True, check=True)  # noqa: S603, S607
    return r.stdout.strip()


def calibration_record(*, pilot: bool = True, snapshot: bool = True, snap_pilot: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {"selection": {"read_layer": 4, "lora_lr": 0.001}, "pilot": {"ok": pilot, "outcome": None if pilot else "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"}}
    if snapshot:
        out["selection_at_snapshot"] = {"read_layer": 12, "lora_lr": 0.0003}
        out["pilot_at_snapshot"] = {"ok": snap_pilot, "outcome": None if snap_pilot else "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"}
    return out


class Setup:
    def __init__(self, tmp: Path, monkeypatch: pytest.MonkeyPatch, *, scale_hours: float = 10.0, n: int = 4, u: int = 2000, device: str = "mps", **cal: bool) -> None:
        core.reset_seed_record()
        self.tmp = tmp
        self.repo = tmp / "repo"
        (self.repo / "studies/p10s2").mkdir(parents=True, exist_ok=True)
        (self.repo / "studies/p10s2/x.py").write_text("x = 1\n")
        (self.repo / "studies/__init__.py").write_text("")
        (self.repo / core.DEFAULT_CONFIG).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / core.DEFAULT_CONFIG).write_text((ROOT / core.DEFAULT_CONFIG).read_text())
        self.led = Ledger(tmp / "ledger.jsonl")
        monkeypatch.setattr(freeze, "study_ledger_path", lambda: tmp / "ledger.jsonl")
        for kind, h in (("datagen", 1.0), ("calibration", 1.0), ("rehearsal", 1.5)):
            self.led.record(kind, h * 3600)
        self.rates = replace(rates(scale_for(scale_hours, n, u) if (n, u) != (4, 2000) else scale_hours / hours(1.0, 4, 2000)), train_device=device)
        data = self.repo / "data"
        data.mkdir(exist_ok=True)
        (data / "manifest.json").write_text('{"files": {}}')
        self.pre = tmp / "pre"
        self.pre.mkdir()
        from arborlm.io import file_sha256

        man, cfg_sha = file_sha256(data / "manifest.json"), file_sha256(self.repo / core.DEFAULT_CONFIG)
        c = core.CFG

        def ident(mode: str, **counts: int) -> dict[str, Any]:
            return {"bundle_manifest_sha256": man, "code_commit": "c0ffee", "config_sha256": cfg_sha, "seed_mode": mode, "update_counts": counts, "device": device}

        cal_rec = calibration_record(**cal)
        cal_rec["identity"] = ident("calibration", updates=int(c["calibration"]["updates"]))
        (self.pre / "calibration.json").write_text(json.dumps(cal_rec))
        (self.pre / "prefreeze.json").write_text(json.dumps({"teacher_only": True, "stop": None, "g1": {"ok": True}, "g3": {"ok": True}, "combined_whole_string": {"ok": True}, "tokenization": {"required_ok": True}, "bundle_manifest_sha256": man, "seed_mode": "registered-data"}))
        (self.pre / "prefreeze_gates.json").write_text(json.dumps({"ok": True, "seconds_scaled_to_registered_panels": 1.0, "identity": ident("rehearsal", updates=int(c["rehearsal"]["short_updates"]))}))
        reh: dict[str, Any] = {"raw": {"device": device}, "charged_hours_at_end_of_rehearsal": self.led.total_hours(), "identity": ident("rehearsal", updates=int(c["rehearsal"]["short_updates"]), full_updates=int(c["rehearsal"]["full_updates"]))}
        if device == "cpu":
            reh["mps_attempt"] = {"ok": False, "error": "RuntimeError: the rehearsal on MPS failed"}
        (self.pre / "rehearsal.json").write_text(json.dumps(reh))

    def freeze(self, run_dir: Path | None = None) -> dict[str, Any]:
        return freeze.write_freeze(self.repo, rates=self.rates, ledger=self.led, run_dir=run_dir or self.tmp / "registered-run", data_dir="data", calibration=self.pre / "calibration.json", prefreeze=self.pre / "prefreeze.json", prefreeze_gates=self.pre / "prefreeze_gates.json", rehearsal=self.pre / "rehearsal.json")

    def frozen_dir_files(self) -> set[str]:
        d = self.repo / core.FREEZE_DIR
        return {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()} if d.exists() else set()


def test_the_freeze_takes_layer_learning_rates_pilot_cap_and_device_from_the_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch)
    rec = s.freeze()
    plan = freeze.load_plan(s.repo)
    assert plan["design"] == {"replicates": 4, "updates": 2000, "layer": 4, "store_lr": 0.003, "lora_lr": 0.001, "rung": "rung 1", "device": "mps", "scoring_device": "cpu"}
    assert plan["cap_hours"] == 36.0 and plan["charged_hours_at_freeze"] == pytest.approx(3.5) and len(plan["planned_seeds"]) == 44
    assert {Path(x).name for x in rec["written"]} >= set(FROZEN_FILES) | {"calibration.json", "prefreeze_record.json", "prefreeze_gates.json", "rehearsal.json", "rates.json"}
    assert {k: v for k, v in json.loads((s.repo / plan["calibration"]["path"]).read_text()).items() if k != "identity"} == calibration_record()  # the record the numbers came from is in the freeze commit
    assert budget.Rates.from_json(json.loads((s.repo / plan["rates"]["path"]).read_text())) == s.rates
    run_dir = s.tmp / "registered-run"
    freeze.verify_plan(plan, s.repo, run_dir, ledger=s.led)
    assert not (s.repo / core.FREEZE_DIR / "prefreeze_caps.json").exists() and not (s.repo / core.FREEZE_DIR / "prefreeze_stop.json").exists()  # nothing but the plan's own files is written into the frozen folder


def test_for_u_1000_the_selection_and_the_pilot_come_from_the_1000_update_snapshots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch, scale_hours=40.0, n=3, u=2000)  # rung 1 does not fit even at the 72-hour ceiling, a U = 1,000 rung does
    d = budget.rehearsal_rule(s.led.total_hours(), s.rates, 72.0)
    assert d.updates == 1000, d.outcome
    s.freeze()  # the cap is the computed one (72: rung 1 needs more than the ceiling) and the freeze records it
    plan = freeze.load_plan(s.repo)
    assert plan["cap_hours"] == 72.0 and s.led.cap_hours() == 72.0
    assert plan["design"]["updates"] == 1000 and plan["design"]["layer"] == 12 and plan["design"]["lora_lr"] == 0.0003  # selection_at_snapshot, not the U = 2,000 selection (layer 4, 0.001)


def test_u_1000_refuses_without_the_snapshot_selection_or_with_a_failed_snapshot_pilot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for kw, why in (({"snapshot": False}, "no 'selection_at_snapshot'"), ({"snap_pilot": False}, "STUDENT CANNOT USE THE MEMORY")):
        s = Setup(tmp_path / why[:6], monkeypatch, scale_hours=40.0, n=3, u=2000, **kw)
        with pytest.raises(freeze.FreezeRefused, match=why):
            s.freeze()
        assert s.frozen_dir_files() == set() and not (s.repo / core.PLAN_FILE).exists()  # both or neither: no plan


def test_a_failed_pilot_stops_the_freeze_and_nothing_is_written_into_the_frozen_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch, pilot=False)
    with pytest.raises(freeze.FreezeRefused, match="STUDENT CANNOT USE THE MEMORY ON THIS TASK"):
        s.freeze()
    assert s.frozen_dir_files() == set()


def test_refusals_leave_no_file_in_the_frozen_folder_and_the_record_goes_outside_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch, scale_hours=200.0)
    with pytest.raises(freeze.FreezeRefused, match="NOT STARTED: BUDGET"):
        s.freeze()
    assert s.frozen_dir_files() == set()  # the next pre-freeze stage would otherwise refuse on an unclean tree
    out = json.loads((tmp_path / "refusals" / "rehearsal_outcome.json").read_text())
    assert out["outcome"] == "NOT STARTED: BUDGET" and out["decision"]["replicates"] is None
    s2 = Setup(tmp_path / "b", monkeypatch)
    (s2.pre / "prefreeze_gates.json").write_text(json.dumps({"ok": False}))
    with pytest.raises(freeze.FreezeRefused, match="gates stage on rehearsal seeds failed"):
        s2.freeze()
    assert s2.frozen_dir_files() == set()
    s3 = Setup(tmp_path / "c", monkeypatch)
    s3.led.path.write_text("")  # no measured pre-freeze stage: the caps are still provisional
    s3.led.record("datagen", 3600.0)
    with pytest.raises(freeze.FreezeRefused, match="still provisional"):
        s3.freeze()
    assert s3.frozen_dir_files() == set() and json.loads((tmp_path / "c" / "refusals" / "prefreeze_caps.json").read_text())["provisional"] is True


def test_the_study_stops_before_the_freeze_when_teachers_or_data_do_not_qualify_and_the_record_goes_outside_the_frozen_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch)
    from arborlm.io import file_sha256

    ok = {"g1": {"ok": True}, "combined_whole_string": {"ok": True}, "tokenization": {"required_ok": True}, "bundle_manifest_sha256": file_sha256(s.repo / "data" / "manifest.json"), "seed_mode": "registered-data", "qualification": {"ok": True, "outcome": None}, "sufficiency_pools": {"outcome": None}, "sufficiency_after_filter": {"outcome": None}}
    (s.pre / "prefreeze.json").write_text(json.dumps({**ok, "combined_whole_string": {"ok": False}}))
    with pytest.raises(freeze.FreezeRefused, match="whole-string check"):
        s.freeze()  # the same consequence as a prompt mismatch in test (a)
    (s.pre / "prefreeze.json").write_text(json.dumps({**ok, "qualification": {"ok": False, "outcome": "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"}}))
    with pytest.raises(freeze.FreezeRefused, match="TEACHERS-NOT-QUALIFIED"):
        s.freeze()
    assert json.loads((tmp_path / "refusals" / "prefreeze_stop.json").read_text())["label"] == "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"
    assert s.frozen_dir_files() == set() and not (s.repo / core.PLAN_FILE).exists()  # both or neither
    (s.pre / "prefreeze.json").write_text(json.dumps(ok))
    s.freeze()  # a record that qualifies freezes (after the refusals above left nothing behind)
    assert (s.repo / core.PLAN_FILE).exists() and (s.repo / core.CAPS_FILE).exists()


def test_the_freeze_refuses_a_device_other_than_mps_and_a_layer_that_is_not_the_calibrated_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch, device="cpu")
    with pytest.raises(freeze.FreezeRefused, match="frozen device is MPS"):
        s.freeze()
    assert s.frozen_dir_files() == set()
    s2 = Setup(tmp_path / "b", monkeypatch)
    s2.rates = replace(s2.rates, calibrated_layer=12)
    with pytest.raises(freeze.FreezeRefused, match="calibrated layer 12 differs"):
        s2.freeze()


def test_the_freeze_refuses_when_tokenization_test_a_is_absent_or_has_a_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for i, tok in enumerate((None, {"required_ok": False})):
        s = Setup(tmp_path / str(i), monkeypatch)
        rec = json.loads((s.pre / "prefreeze.json").read_text())
        rec.pop("tokenization")
        if tok is not None:
            rec["tokenization"] = tok
        (s.pre / "prefreeze.json").write_text(json.dumps(rec))
        with pytest.raises(freeze.FreezeRefused, match="test .a. of section 14.2 step 4"):
            s.freeze()
        assert s.frozen_dir_files() == set()


def test_the_freeze_may_record_cpu_only_with_the_rehearsals_reason_and_nothing_changes_after_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch, device="cpu")
    s.rates = replace(s.rates, train_device_reason="an MPS operation the update needs is unsupported (the rehearsal itself cannot run on MPS)")
    s.freeze()  # the lead's ruling: MPS unless the rehearsal cannot run on it; then CPU with every rate rehearsed on CPU
    plan = freeze.load_plan(s.repo)
    assert plan["design"]["device"] == "cpu" and plan["design"]["scoring_device"] == "cpu"
    s2 = Setup(tmp_path / "b", monkeypatch, device="cuda")
    s2.rates = replace(s2.rates, train_device_reason="because")
    with pytest.raises(freeze.FreezeRefused, match="without a recorded reason"):
        s2.freeze()  # only CPU is an allowed alternative


def test_the_freeze_records_the_computed_cap_itself_and_refuses_any_other(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fits = Setup(tmp_path / "a", monkeypatch)  # rung 1 fits 36 hours: the cap is 36 and nothing is raised
    fits.freeze()
    assert freeze.load_plan(fits.repo)["cap_hours"] == 36.0 and not (fits.repo / core.RAISE_FILE).exists()
    need = Setup(tmp_path / "b", monkeypatch, scale_hours=20.3)  # rung 1 needs more: the smallest whole number of hours that admits it, recorded by the freeze (never a 36-hour cap against the rule)
    need.freeze()
    plan = freeze.load_plan(need.repo)
    assert plan["cap_hours"] == need.led.cap_hours() == budget.effective_cap(need.repo / core.RAISE_FILE) > 36.0 and plan["cap_hours"] == float(int(plan["cap_hours"])) and plan["design"]["rung"] == "rung 1"
    assert need.led.cap_raise_entry() is not None
    over = Setup(tmp_path / "c", monkeypatch, scale_hours=200.0)  # no rung fits even at 72: NOT STARTED: BUDGET, and the raise is not recorded by a freeze that refuses
    with pytest.raises(freeze.FreezeRefused, match="NOT STARTED: BUDGET"):
        over.freeze()
    assert over.led.cap_raise_entry() is None and not (over.repo / core.RAISE_FILE).exists()


def test_the_freeze_refuses_after_a_registered_seed_and_checks_the_cap_raise_against_the_recomputation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch)
    with s.led.measure("train", registered=True):
        pass
    with pytest.raises(freeze.FreezeRefused, match="registered seed has been observed"):
        s.freeze()
    # a raise that was typed (a different cap) is refused: the freeze recomputes the proposal from P and the rates
    s2 = Setup(tmp_path / "b", monkeypatch, scale_hours=20.3)
    s2.led.append_cap_raise(60.0, {})
    (s2.repo / core.FREEZE_DIR).mkdir(parents=True, exist_ok=True)
    (s2.repo / core.RAISE_FILE).write_text(json.dumps({"new_cap_hours": 60.0}))
    with pytest.raises(freeze.FreezeRefused, match="computed by the rule"):
        s2.freeze()
    (s2.repo / core.RAISE_FILE).unlink()
    with pytest.raises(freeze.FreezeRefused, match="disagree"):
        s2.freeze()  # the ledger holds a raise the file does not
    # the recorded, recomputed raise is accepted and bound by hash
    s3 = Setup(tmp_path / "c", monkeypatch, scale_hours=20.3)
    budget.record_raise(s3.rates, s3.repo / core.RAISE_FILE, s3.led)
    s3.freeze()
    plan = freeze.load_plan(s3.repo)
    assert plan["cap_hours"] > 36.0 and plan["cap_raise_sha256"] and plan["design"]["rung"] == "rung 1"
    freeze.verify_plan(plan, s3.repo, s3.tmp / "registered-run", ledger=s3.led)
    s3.led.append_cap_raise(70.0, {})  # a raise after the freeze makes the ledger's cap differ from the plan's
    with pytest.raises(freeze.FreezeRefused, match="differs from the cap the freeze recorded"):
        freeze.verify_plan(plan, s3.repo, s3.tmp / "registered-run", ledger=s3.led)


def test_the_freeze_refuses_when_a_plan_is_already_committed_in_the_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch)
    git(s.repo, "init", "-q", "-b", "main")
    s.freeze()
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "freeze")
    shutil.rmtree(s.repo / core.FREEZE_DIR)  # even with the files removed again, the history holds a plan: registered stages may have run after it
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "remove")
    with pytest.raises(freeze.FreezeRefused, match="registered seed has been observed"):
        s.freeze()
    assert budget.plan_in_history(s.repo) and not budget.plan_in_history(None)


def test_verify_plan_checks_the_records_the_code_digest_and_every_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch)
    s.freeze()
    plan = freeze.load_plan(s.repo)
    run_dir = s.tmp / "registered-run"
    for rel in ("calibration", "prefreeze_record", "prefreeze_gates", "rehearsal", "rates", "projection"):
        target = s.repo / plan[rel]["path"]
        old = target.read_bytes()
        target.write_bytes(old + b" ")
        with pytest.raises(freeze.FreezeRefused, match="does not hash"):
            freeze.verify_plan(plan, s.repo, run_dir, ledger=s.led)
        target.write_bytes(old)
    (s.repo / "studies/p10s2/x.py").write_text("x = 2\n")
    with pytest.raises(freeze.FreezeRefused, match="code differs from the frozen digest.*x.py"):
        freeze.verify_plan(plan, s.repo, run_dir, ledger=s.led)  # plan["code"] is verified, not just recorded
    (s.repo / "studies/p10s2/x.py").write_text("x = 1\n")
    (s.repo / "studies/__init__.py").write_text("# changed\n")
    with pytest.raises(freeze.FreezeRefused, match="code differs"):
        freeze.verify_plan(plan, s.repo, run_dir, ledger=s.led)  # studies/__init__.py is inside the digest
    (s.repo / "studies/__init__.py").write_text("")
    freeze.verify_plan(plan, s.repo, run_dir, ledger=s.led)
    assert "studies/__init__.py" in freeze.FROZEN_PATHS and "studies/p10s2/freeze/plan.json" not in plan["code"] and not any("/records/" in k for k in plan["code"])


# --- the freeze commit, the run decision and the identity of the freeze commit ----------------------------------------------------------------
def committed_repo(tmp: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Setup, str]:
    s = Setup(tmp, monkeypatch)
    git(s.repo, "init", "-q", "-b", "main")
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "code")
    s.freeze()
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "freeze commit")
    return s, git(s.repo, "rev-parse", "HEAD")


def test_the_freeze_commit_must_be_the_commit_that_added_the_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s, fc = committed_repo(tmp_path, monkeypatch)
    freeze.check_freeze_identity(s.repo, fc)
    (s.repo / "results").mkdir()
    (s.repo / "results" / "note.md").write_text("later\n")
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "later commit with the same frozen paths")
    later = git(s.repo, "rev-parse", "HEAD")
    assert freeze.check_preconditions(s.repo, later)["commit"] == later  # the frozen paths equal HEAD's, so the precondition alone accepts it
    with pytest.raises(freeze.FreezeRefused, match="is not the freeze commit"):
        freeze.check_freeze_identity(s.repo, later)  # but it is not the commit that added the plan
    empty = tmp_path / "empty"
    empty.mkdir()
    git(empty, "init", "-q", "-b", "main")
    (empty / "a.txt").write_text("a")
    git(empty, "add", "-A")
    git(empty, "commit", "-q", "-m", "a")
    with pytest.raises(freeze.FreezeRefused, match="no commit in the history"):
        freeze.check_freeze_identity(empty, git(empty, "rev-parse", "HEAD"))


def test_the_run_decision_is_a_committed_file_after_the_freeze_commit_with_the_exact_line_and_the_full_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s, fc = committed_repo(tmp_path, monkeypatch)
    with pytest.raises(freeze.FreezeRefused, match="no committed run decision"):
        freeze.check_decision(s.repo, fc)
    d = s.repo / "results" / "p10s2-freeze-2026-11-16"
    d.mkdir(parents=True)
    (d / "DECISION.md").write_text(f"# decision\n\nDECISION: RUN\n\nfreeze commit {fc[:12]}\n")  # an abbreviated hash is not the full hash
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "decision (short hash)")
    with pytest.raises(freeze.FreezeRefused, match="no committed run decision"):
        freeze.check_decision(s.repo, fc)
    (d / "DECISION.md").write_text(f"# decision\n\nDECISION: RUN anyway\n\nfreeze commit {fc}\n")  # not the exact line
    git(s.repo, "commit", "-q", "-a", "-m", "decision (inexact line)")
    with pytest.raises(freeze.FreezeRefused, match="no committed run decision"):
        freeze.check_decision(s.repo, fc)
    (d / "DECISION.md").write_text(f"# decision\n\nDECISION: RUN\n\nfreeze commit {fc}\n")
    with pytest.raises(freeze.FreezeRefused, match="no committed run decision"):
        freeze.check_decision(s.repo, fc)  # edited but not committed: the committed blob is what counts
    git(s.repo, "commit", "-q", "-a", "-m", "decision")
    assert freeze.check_decision(s.repo, fc) == "results/p10s2-freeze-2026-11-16/DECISION.md"
    # the records after the freeze commit are outside every frozen path: the commits that add them do not disturb the preconditions
    assert freeze.check_preconditions(s.repo, fc)["commit"] == fc


def test_a_decision_inside_the_freeze_commit_itself_does_not_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = Setup(tmp_path, monkeypatch)
    git(s.repo, "init", "-q", "-b", "main")
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "code")
    s.freeze()
    (s.repo / "results" / "p10s2-freeze-x").mkdir(parents=True)
    (s.repo / "results" / "p10s2-freeze-x" / "DECISION.md").write_text("DECISION: RUN\n")
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "freeze commit with a decision file in it")
    fc = git(s.repo, "rev-parse", "HEAD")
    (s.repo / "results" / "p10s2-freeze-x" / "DECISION.md").write_text(f"DECISION: RUN\n{fc}\n")
    git(s.repo, "commit", "-q", "-a", "-m", "decision text added later")
    with pytest.raises(freeze.FreezeRefused, match="no committed run decision"):
        freeze.check_decision(s.repo, fc)  # the file was added by the freeze commit itself: a decision is made after it
