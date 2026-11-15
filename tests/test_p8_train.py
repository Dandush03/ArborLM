"""P8 training worker, checkpoint contract, supervision, freeze binding and gates (synthetic).

Step counts are shortened by monkeypatching the registry constants in-process only; the registered
512-update run is exercised by the dry run and the rehearsal, not by CI."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import torch

from arborlm import p8_checkpoint as ckpt
from arborlm import p8_core as core
from arborlm import p8_train as train
from arborlm.io import read_json, sha256
from arborlm.p5_model import optimizer_for, state_digest


@pytest.fixture
def short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "STEPS", 8)
    monkeypatch.setattr(core, "CHECKPOINT_STEPS", (0, 4, 8))
    monkeypatch.setattr(core, "REACH_UPDATES", (1, 4, 8))
    monkeypatch.setattr(ckpt, "CHECKPOINT_STEPS", (0, 4, 8))


def inputs(case: str) -> tuple[core.Cell, Any, torch.Tensor]:
    cell = core.Cell(101, 301, 601, case)
    train_rows, order, _ = core.synthetic_training(cell)
    return cell, core.synthetic_backbone(cell), core.ordered_rows(train_rows, order)


def identity_for(cell: core.Cell, backbone: Any) -> dict[str, Any]:
    from arborlm.p4_model import backbone_digest

    return {
        **core.code_identity(),
        "cell": cell.fields(),
        "backbone_sha256": backbone_digest(backbone),
    }


# --- item 5: checkpoint restoration -----
@pytest.mark.parametrize("case", ["C07", "C01", "C02"])
def test_restore_from_midpoint_reaches_identical_final_state(
    short: None, case: str, tmp_path: Path
) -> None:
    cell, backbone, rows = inputs(case)
    model = core.build_model(cell, backbone)
    optimizer = optimizer_for(model)
    identity = identity_for(cell, backbone)
    saved: dict[int, str] = {}

    def checkpoint(step: int) -> None:
        saved[step] = ckpt.save(ckpt.step_path(tmp_path, step), model, optimizer, step, identity)

    checkpoint(0)
    train.advance(model, optimizer, rows, cell, cell.objective, 1, 8, on_checkpoint=checkpoint)
    final = state_digest(model)
    restored, optimizer2, meta = ckpt.restore(
        ckpt.step_path(tmp_path, 4), cell, backbone, expected_sha256=saved[4]
    )
    assert meta["step"] == 4 and optimizer2 is not None
    assert optimizer2.state_dict()["state"], "optimizer state is part of the checkpoint"
    train.advance(restored, optimizer2, rows, cell, cell.objective, 5, 8)
    assert state_digest(restored) == final
    again = ckpt.restore(ckpt.step_path(tmp_path, 8), cell, backbone)[2]
    assert again["state_digest"] == final


def test_checkpoint_refusals(short: None, tmp_path: Path) -> None:
    cell, backbone, rows = inputs("C03")
    model = core.build_model(cell, backbone)
    optimizer = optimizer_for(model)
    identity = identity_for(cell, backbone)
    path = ckpt.step_path(tmp_path, 0)
    digest = ckpt.save(path, model, optimizer, 0, identity)
    with pytest.raises(FileExistsError):
        ckpt.save(path, model, optimizer, 0, identity)  # never overwrites
    with pytest.raises(ValueError):
        ckpt.save(ckpt.step_path(tmp_path, 4), model, optimizer, 3, identity)  # unregistered step
    with pytest.raises(ValueError):
        ckpt.save(ckpt.step_path(tmp_path, 8), model, optimizer, 8, {**identity, "cell": {}})
    with pytest.raises(ValueError):
        ckpt.restore(path, cell, backbone, expected_sha256="0" * 64)
    other = core.Cell(101, 301, 602, "C03")
    with pytest.raises(ValueError):
        ckpt.restore(path, other, backbone)  # identity names another cell
    changed = core.synthetic_backbone(cell)
    with torch.no_grad():
        next(changed.parameters()).add_(1.0)
    with pytest.raises(ValueError):
        ckpt.restore(path, cell, changed)  # backbone digest differs
    assert ckpt.restore(path, cell, backbone, expected_sha256=digest)[2]["step"] == 0
    # a corrupted file does not load
    corrupt = tmp_path / "step-0004.pt"
    corrupt.write_bytes(path.read_bytes()[:-64])
    with pytest.raises(Exception):
        ckpt.restore(corrupt, cell, backbone)


# --- the worker (shortened) and the restore gate -----
@pytest.mark.parametrize("case", ["C07", "C10"])
def test_train_cell_and_restore_check_dry_run(short: None, case: str, tmp_path: Path) -> None:
    cell = core.Cell(102, 302, 602, case)
    run = tmp_path / "P8TD-test"
    run.mkdir()
    record = train.train_cell(cell, run, tmp_path, dry_run=True, data_dir=None)
    assert record["dry_run"] is True and record["status"] == "completed"
    assert record["backbone_sha256_before"] == record["backbone_sha256_after"]
    assert set(record["state_digests"]) == {"step-0000", "step-0004", "step-0008"}
    assert record["optimizer_parameter_names"][0] == "addition.keys"
    assert record["summary"]["updates"] == 8 and record["extra_backward_passes_per_update"] == len(
        cell.objective
    )
    assert set(record["summary"]["lambda"]) == set(cell.objective)
    assert [r["step"] for r in record["summary"]["reach"]] == [1, 4, 8]
    assert set(record["proxy_values"]) == {"0", "4", "8"}
    folder = run / "cells" / cell.label
    lines = [json.loads(x) for x in (folder / "steps.jsonl").read_text().splitlines()]
    assert len(lines) == 8 and all(x["dry_run"] is True for x in lines)
    args = argparse.Namespace(
        experiments_root=str(tmp_path), data_dir=str(tmp_path), run_dir=str(run), label=cell.label
    )
    assert train.cmd_restore_check(args) == 0
    result = next(tmp_path.glob("P8TRD-*/result.json"))
    assert read_json(result)["passed"] is True
    with pytest.raises(FileExistsError):
        train.train_cell(cell, run, tmp_path, dry_run=True, data_dir=None)  # no rerun in place


def test_repeated_cell_gives_identical_digests(short: None, tmp_path: Path) -> None:
    cell = core.Cell(101, 301, 601, "C09")
    records = []
    for name in ("a", "b"):
        run = tmp_path / name
        run.mkdir()
        records.append(train.train_cell(cell, run, tmp_path, dry_run=True, data_dir=None))
    assert records[0]["state_digests"] == records[1]["state_digests"]
    assert records[0]["checkpoint_file_sha256"] != {}


# --- supervision: failures are recorded, never rerun or skipped -----
LABELS = [core.cells()[i].label for i in (0, 1, 2)]
HEADER = {"code_identity": {"source_sha256": "x"}}


def fake_worker(behaviour: str) -> Any:
    script = (
        "import json,sys,os,time,pathlib\n"
        "label=sys.argv[1]; run=pathlib.Path(sys.argv[2]); mode=sys.argv[3]\n"
        "first=label.endswith('C01')\n"
        "if mode=='fail_first' and first: sys.exit(3)\n"
        "if mode=='sleep': time.sleep(30)\n"
        "if mode=='memory': b=bytearray(300*1024*1024); time.sleep(30)\n"
        "d=run/'cells'/label; d.mkdir(parents=True)\n"
        "(d/'train.json').write_text(json.dumps({'state_digests':{},'backbone_sha256_before':'b',"
        "'backbone_sha256_after':'b','checkpoint_file_sha256':{},'identity':{'source_sha256':'x'},"
        "'training_seconds':0.0,'peak_rss_bytes':1}))\n"
    )

    def command(label: str, run: Path) -> list[str]:
        return [sys.executable, "-c", script, label, str(run), behaviour]

    return command


def stage(tmp_path: Path, behaviour: str, **settings: Any) -> dict[str, Any]:
    run = tmp_path / "run"
    run.mkdir()
    return train.run_stage(
        run,
        LABELS,
        tmp_path,
        tmp_path,
        dry_run=True,
        settings=train.StageSettings(worker_command=fake_worker(behaviour), poll=0.05, **settings),
        header=HEADER,
    )


def test_stage_all_cells_complete(tmp_path: Path) -> None:
    manifest = stage(tmp_path, "ok", workers=2)
    assert manifest["status"] == "completed" and manifest["counts"]["completed"] == 3
    assert manifest["denominator"] == 3 and all(c["dry_run"] for c in manifest["cells"])


def test_stage_failure_is_recorded_and_stops_launching(tmp_path: Path) -> None:
    manifest = stage(tmp_path, "fail_first", workers=1)
    states = [c["status"] for c in manifest["cells"]]
    assert states == ["failed", "unexecuted", "unexecuted"]
    assert manifest["status"] == "INCOMPLETE" and manifest["denominator"] == 3
    assert read_json(tmp_path / "run" / "manifest.json")["status"] == "INCOMPLETE"


def test_stage_failure_continue_flag_keeps_denominator(tmp_path: Path) -> None:
    manifest = stage(tmp_path, "fail_first", workers=1, continue_after_failure=True)
    assert [c["status"] for c in manifest["cells"]] == ["failed", "completed", "completed"]
    assert manifest["status"] == "INCOMPLETE" and manifest["denominator"] == 3


def test_stage_cell_cap_kills_and_records(tmp_path: Path) -> None:
    manifest = stage(tmp_path, "sleep", workers=1, cell_cap=0.5)
    assert manifest["cells"][0]["status"] == "failed"
    assert "cell cap" in manifest["cells"][0]["reason"]
    assert manifest["status"] == "INCOMPLETE"


def test_stage_worker_rss_limit_kills_and_records(tmp_path: Path) -> None:
    manifest = stage(tmp_path, "memory", workers=1, rss_worker=150 * 1024 * 1024)
    assert manifest["cells"][0]["status"] == "failed"
    assert "RSS" in manifest["cells"][0]["reason"]


def test_stage_cap_kills_running_and_leaves_rest_unexecuted(tmp_path: Path) -> None:
    manifest = stage(tmp_path, "sleep", workers=1, stage_cap=0.4)
    assert manifest["cells"][0]["status"] == "failed"
    assert [c["status"] for c in manifest["cells"][1:]] == ["unexecuted", "unexecuted"]
    assert manifest["reason"].startswith("stage cap")


def test_project_makespan() -> None:
    assert train.project_makespan([10.0] * 8, 4) == 20.0
    assert train.project_makespan([30.0, 10.0, 10.0, 10.0, 10.0], 4) == 30.0


# --- freeze binding -----
def fake_git(files: dict[str, bytes]) -> Any:
    def git(*args: str) -> bytes:
        if args[0] == "rev-parse" and args[1] == "--verify":
            if args[2].startswith("nope"):
                raise subprocess.CalledProcessError(128, "git")
            return b"f" * 40 + b"\n"
        if args[0] == "rev-parse":
            return b"e" * 40 + b"\n"
        if args[0] == "ls-tree":
            return "\n".join(n for n in files if n.startswith("src/arborlm/")).encode()
        if args[0] == "show":
            name = args[1].split(":", 1)[1]
            if name not in files:
                raise subprocess.CalledProcessError(128, "git")
            return files[name]
        raise AssertionError(args)

    return git


def test_freeze_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = (core.repo_root() / core.SPEC).read_bytes()
    config = (core.repo_root() / core.DEFAULT_CONFIG).read_bytes()
    working = core.source_hashes()
    files: dict[str, bytes] = {core.SPEC: spec, str(core.DEFAULT_CONFIG): config}
    for extra_name in ("uv.lock", "pyproject.toml"):
        files[extra_name] = (core.repo_root() / extra_name).read_bytes()
    for name in working:
        files[name] = (core.repo_root() / name).read_bytes()
    monkeypatch.setattr(train, "_git", fake_git(files))
    info = train.verify_freeze("abc")
    assert info["freeze_commit"] == "f" * 40 and info["source_files"] == len(working)
    with pytest.raises(train.FreezeError, match="does not exist"):
        train.verify_freeze("nope")
    for missing in (core.SPEC, str(core.DEFAULT_CONFIG), "uv.lock", "pyproject.toml"):
        absent = {k: v for k, v in files.items() if k != missing}
        monkeypatch.setattr(train, "_git", fake_git(absent))
        with pytest.raises(train.FreezeError, match="missing at the freeze commit"):
            train.verify_freeze("abc")
    for tamper in (
        "src/arborlm/p8_core.py",
        core.SPEC,
        str(core.DEFAULT_CONFIG),
        "uv.lock",
        "pyproject.toml",
    ):
        changed = dict(files)
        changed[tamper] = changed[tamper] + b"x"
        monkeypatch.setattr(train, "_git", fake_git(changed))
        with pytest.raises(train.FreezeError):
            train.verify_freeze("abc")
    extra = dict(files)
    extra["src/arborlm/p8_extra.py"] = b"x"  # a file in the freeze commit absent from the tree
    monkeypatch.setattr(train, "_git", fake_git(extra))
    with pytest.raises(train.FreezeError):
        train.verify_freeze("abc")
    assert sha256(b"") != ""  # keep the import honest


def test_registered_stage_refuses_without_freeze_commit(tmp_path: Path) -> None:
    code = train.main(["stage", "--experiments-root", str(tmp_path), "--data-dir", str(tmp_path)])
    assert code == 2 and not list(tmp_path.iterdir())
    code = train.main(
        ["stage", "--experiments-root", str(tmp_path), "--data-dir", str(tmp_path),
         "--labels", LABELS[0]]
    )  # fmt: skip
    assert code == 2 and not list(tmp_path.iterdir())


def test_parser_has_every_registered_subcommand() -> None:
    parser = train.build_parser()
    for command in ("cell", "stage", "restore-check", "p5-invariance", "rehearsal"):
        args = parser.parse_args(
            [command, "--experiments-root", "/x", "--data-dir", "/y"]
            + (
                ["--run-dir", "/r", "--label", LABELS[0]]
                if command in ("cell", "restore-check")
                else []
            )
        )
        assert args.experiments_root == "/x" and args.data_dir == "/y"


def test_continue_after_failure_refused_for_registered_stage(tmp_path: Path) -> None:
    code = train.main(
        ["stage", "--experiments-root", str(tmp_path), "--data-dir", str(tmp_path),
         "--freeze-commit", "abc", "--continue-after-failure"]
    )  # fmt: skip
    assert code == 2 and not list(tmp_path.iterdir())


def test_restore_gate_reports_failure_and_refuses_rerun(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(train, "RESTORE_GATE_LABELS", ["b101-o301-s601-C01", "b101-o301-s601-C02"])
    run = tmp_path / "P8T-fake"
    run.mkdir()
    args = argparse.Namespace(
        experiments_root=str(tmp_path), data_dir=str(tmp_path), run_dir=str(run)
    )
    assert train.cmd_restore_gate(args) == 1  # no train.json: the worker fails, gate not passed
    report = read_json(run / "restore_gate.json")
    assert report["passed"] is False and set(report["cells"]) == set(train.RESTORE_GATE_LABELS)
    assert all(not c["passed"] for c in report["cells"].values())
    assert train.cmd_restore_gate(args) == 2  # never overwritten
    assert not (run / "cells").exists()


def test_restore_gate_passes_on_real_checkpoints_dry_run(
    short: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cell = core.Cell(101, 301, 601, "C06")
    run = tmp_path / "P8TD-gate"
    run.mkdir()
    train.train_cell(cell, run, tmp_path, dry_run=True, data_dir=None)
    result = train.restore_check(cell.label, run, tmp_path)
    assert result["passed"] is True and result["seconds"] > 0
    before = {p: p.read_bytes() for p in (run / "cells" / cell.label).glob("step-*.pt")}
    train.restore_check(cell.label, run, tmp_path)
    assert before == {p: p.read_bytes() for p in (run / "cells" / cell.label).glob("step-*.pt")}
