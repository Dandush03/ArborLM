# ruff: noqa: E501
"""P10-I-S2-D0, lead decision 1: finalize_only refusals, code-difference policy, hash-before-read ordering, and the post-pass steps over a tiny synthetic run. Synthetic values only; nothing here is a result."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from p10is2_engine_fixtures import CFG_T  # noqa: E402
from test_p10is2d0_finalize_fix import _stats_record  # noqa: E402
from test_p10is2d0_pipeline import _run, tiny  # noqa: E402, F401

from studies.p10is2d0 import finalize_only as fo  # noqa: E402
from studies.p10is2d0 import passes, run  # noqa: E402


def _skeleton(out: Path, with_hash_bytes: bytes = b"{}") -> None:
    """A run directory in the state the driver leaves after its last pass, with placeholder bytes."""
    exp = fo.expected_record_paths(out)
    for paths in exp.values():
        for p in paths:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(with_hash_bytes)
    (out / "gates").mkdir(exist_ok=True)
    for g in fo.GATE_FILES:
        (out / "gates" / g).write_bytes(b"{}")
    (out / "launch.json").write_text(json.dumps({"commit": "aaaa"}))


def test_a_complete_skeleton_passes_the_directory_check(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    fo.check_run_directory(tmp_path)
    assert sum(len(v) for v in fo.expected_record_paths(tmp_path).values()) == 96 + 6 + 24


@pytest.mark.parametrize("mutation", ["no_launch", "run_complete", "report", "records_dir", "missing_pass", "extra_pass", "missing_stats", "missing_gate_pass", "missing_gate_file"])
def test_the_directory_check_refuses(tmp_path: Path, mutation: str) -> None:
    _skeleton(tmp_path)
    exp = fo.expected_record_paths(tmp_path)
    if mutation == "no_launch":
        (tmp_path / "launch.json").unlink()
    elif mutation == "run_complete":
        (tmp_path / "run_complete.json").write_text("{}")
    elif mutation == "report":
        (tmp_path / "report.txt").write_text("x")
    elif mutation == "records_dir":
        (tmp_path / "records").mkdir()
    elif mutation == "missing_pass":
        exp["passes"][0].unlink()
    elif mutation == "extra_pass":
        (tmp_path / "passes" / "P__9__ZZ__x__y__first.json").write_text("{}")
    elif mutation == "missing_stats":
        exp["stats"][0].unlink()
    elif mutation == "missing_gate_pass":
        exp["gate_passes"][0].unlink()
    else:
        (tmp_path / "gates" / "repro.json").unlink()
    with pytest.raises(run.D0Refused):
        fo.check_run_directory(tmp_path)


def test_the_code_difference_policy() -> None:
    ok = ["studies/p10is2d0/finalize.py", "studies/p10is2d0/finalize_only.py", "tests/test_p10is2d0_finalize_only.py", "docs/reviews/x/LEAD_DECISION_1.md"]
    assert fo.check_code_difference(ok) == ok
    for bad in ("studies/p10is2d0/driver.py", "studies/p10is2d0/passes.py", "studies/p10is2d0/reads.py", "src/arborlm/io.py", "results/x/RECORD.md", "configs/p10is2_partt.toml"):
        with pytest.raises(run.D0Refused):
            fo.check_code_difference([*ok, bad])


def test_hash_records_hashes_bytes_without_parsing_json(tmp_path: Path) -> None:
    _skeleton(tmp_path, with_hash_bytes=b"this is not json")  # parsing would raise
    h = fo.hash_records(tmp_path)
    assert len(h) == 96 + 6 + 24 + 4
    assert all(len(v) == 64 for v in h.values())


def test_hashes_are_written_before_any_record_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _skeleton(tmp_path)
    (tmp_path / "launch.json").write_text(json.dumps({"commit": "aaaa"}))
    pt = tmp_path / "partt"
    pt.mkdir()
    (pt / "registry.json").write_text("{}")
    seen: dict[str, Any] = {}

    def fake_git(repo: Path, *argv: str) -> str:
        return {"status": "", "rev-parse": "bbbb", "diff": "studies/p10is2d0/finalize.py\ntests/x.py"}[argv[0]]

    class Done(Exception):
        pass

    def fake_post(out: Path, *a: Any, **k: Any) -> int:
        seen["hashes_exist"] = (out / "inputs" / "record_hashes_before_finalize.json").is_file()
        seen["resumes"] = json.loads((out / "resumes.json").read_text())
        seen["diff"] = json.loads((out / "inputs" / "finalize_code_difference.json").read_text())
        return 0

    monkeypatch.setattr(fo, "git", fake_git)
    monkeypatch.setattr(fo.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(fo, "PART_T_RUN", pt)
    monkeypatch.setattr(fo, "post_pass", fake_post)
    assert fo.finalize_run(tmp_path, Path(__file__).resolve().parents[1], "unit test cause") == 0
    assert seen["hashes_exist"]
    assert seen["resumes"][-1]["cause"] == "unit test cause" and seen["resumes"][-1]["kind"] == "finalize_only"
    assert seen["diff"] == {"launch_commit": "aaaa", "finalize_commit": "bbbb", "changed_files": ["studies/p10is2d0/finalize.py", "tests/x.py"]}


def test_a_dirty_tree_and_a_forbidden_difference_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _skeleton(tmp_path)
    monkeypatch.setattr(fo, "git", lambda repo, *argv: " M studies/p10is2d0/driver.py")
    with pytest.raises(run.D0Refused, match="not clean"):
        fo.finalize_run(tmp_path, tmp_path, "c")
    monkeypatch.setattr(fo, "git", lambda repo, *argv: {"status": "", "rev-parse": "bbbb", "diff": "studies/p10is2d0/passes.py"}[argv[0]])
    monkeypatch.setattr(fo.subprocess, "run", lambda *a, **k: None)
    with pytest.raises(run.D0Refused, match="differ from the launch commit"):
        fo.finalize_run(tmp_path, tmp_path, "c")
    assert not (tmp_path / "report.txt").exists() and not (tmp_path / "resumes.json").exists()


def test_post_pass_writes_report_records_and_run_complete_over_a_tiny_run(tiny, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    w, arms, tmp = tiny
    out = tmp / "out_final"
    recs: dict[str, dict[str, object]] = {}
    for t in passes.main_tasks():
        if t["kind"] == "pass" and (t["rep"], t["order"]) == (0, "AB"):
            recs[t["id"]] = _run(w, arms, out, t)
    for t in passes.main_tasks():
        if t["kind"] == "pass" and (t["rep"], t["order"]) != (0, "AB"):
            src = recs[t["id"].replace(f"P|{t['rep']}|{t['order']}", "P|0|AB")]
            p = passes.record_path(out, t["id"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({**src, "id": t["id"]}))
    for t in passes.main_tasks():
        if t["kind"] == "stats":
            p = passes.record_path(out, t["id"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(_stats_record()))
    (out / "gates").mkdir()
    (out / "gates" / "gate_record.json").write_text(json.dumps({"identity": {"pass": True}, "reproduction": {"pass": True}, "no_write": True}))
    pt = tmp / "partt_dir"
    pt.mkdir()
    (pt / "f.txt").write_text("frozen")
    (out / "inputs").mkdir()
    (out / "inputs" / "partt_run_dir.before.json").write_text(json.dumps(run.fs_manifest(pt)))
    reg: dict[str, float] = {}
    for cap in "AB":
        reg[f"S0|-|-|s:E_{cap}"] = 0.1
        reg[f"TEACHER|-|-|s:E_{cap}"] = 0.9
    for r, o in passes.cells():
        for pan in ("E_A", "E_B"):
            for arm in ("M1", "M-append"):
                reg[f"{arm}|{o}|{r}|s:{pan}"] = 0.5
    led = passes.Ledger(out, "finalize_test")
    assert fo.post_pass(out, reg, CFG_T, pt, "launchsha", "finalizesha", led, 0.0) == 0
    text = (out / "report.txt").read_text()
    assert "launchsha (launch); finalize commit finalizesha; report step re-run after a rendering defect; lead decision 1" in text
    assert "READ STATISTICS (section 5.2) cell r0/AB" in text
    done = json.loads((out / "run_complete.json").read_text())
    assert done["launch_commit"] == "launchsha" and done["finalize_commit"] == "finalizesha" and done["note"] == fo.NOTE and done["part_t_run_dir_changed"] is False
    assert json.loads((out / "records" / "partt_run_dir_diff.json").read_text()) == {"added": [], "removed": [], "changed": []}
    # a changed Part T file is an engineering stop
    (pt / "f.txt").write_text("changed")
    assert fo.post_pass(out, reg, CFG_T, pt, "l", "f", led, 0.0) == fo.EXIT_ENGINEERING
