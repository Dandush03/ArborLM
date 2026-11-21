# ruff: noqa: E501
"""P10IS0 sealing (ADR-0023 section 5.2) and accounting (sections 9, 10): the whitelist validator, the access log, disk pauses, the quiet condition read before the workers start, and the attempts rule."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is0 import accounting, core, ladder, sealed  # noqa: E402

CFG = core.load_config()


def test_whitelist_accepts_durations_and_rehearsal_figures_only() -> None:
    entries = {"8K/4K": {"e_star": 512, "t_exposures": 1024, "convergence": "SHOWN", "flat_below_floor": False, "reference_flags": {"cond4": False, "other": []}, "extension": "none", "labels": []}}
    sealed.validate_public(ladder.durations_record(entries))
    sealed.validate_public({"kind": "timing", "label": "x", "wall_seconds": 12.5, "peak_rss_bytes": 1000, "load_average": [0.5, 0.4, 0.3], "shapes": {"addition.keys": [4096, 16]}})
    for bad in ({"accuracy": 0.9}, {"m_p": 0.9}, {"label": "x", "wall_seconds": 1.0, "note": "hi"}, {"counts": {"correct": 5}}):
        with pytest.raises(sealed.PublicOutputError):
            sealed.validate_public(bad)
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({"status": "ok", "decision": {"wall_seconds": 1.0, "score": 0.93}})
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({"e_star": 512, "round": 1, "path": "x", "labels": [], "workers": 6, "ok": True, "count": 3, "tasks": {"a": 0.93}})


def test_sealed_files_are_hashed_logged_and_read_only_by_the_auditor(tmp_path: Path) -> None:
    p = sealed.write_sealed(tmp_path, "cal1.json", {"m_p": [0.5, 0.6]})
    assert p.parent.name == "sealed" and sealed.sealed_hashes(tmp_path)["cal1.json"]
    with pytest.raises(FileExistsError):
        sealed.write_sealed(tmp_path, "cal1.json", {"m_p": []})
    with pytest.raises(ValueError):
        sealed.write_sealed(tmp_path, "../out.json", {})
    with pytest.raises(sealed.SealedRefused):
        sealed.read_sealed(tmp_path, "cal1.json", reader="lead", why="curiosity")
    assert not (tmp_path / sealed.ACCESS_LOG).exists()  # a refused read is not a read
    rec = sealed.read_sealed(tmp_path, "cal1.json", reader="auditor-recomputation", why="recompute durations")
    assert rec["m_p"] == [0.5, 0.6] and (tmp_path / sealed.ACCESS_LOG).read_text().count("auditor-recomputation") == 1
    assert sealed.disclosure_labels(["8K/4K"]) == {"8K/4K": "CALIBRATION VALUES SEEN BY THE LEAD"}


def test_emit_prints_only_validated_output(capsys: pytest.CaptureFixture[str]) -> None:
    sealed.emit({"stage": "R", "cell_type": "8K/4K", "wall_seconds": 3.5})
    assert '"cell_type": "8K/4K"' in capsys.readouterr().out
    with pytest.raises(sealed.PublicOutputError):
        sealed.emit({"stage": "R", "accuracy": 0.5})


def test_disk_rule(tmp_path: Path) -> None:
    gib = 2**30
    assert accounting.check_disk(tmp_path, CFG, used=10 * gib, free=60 * gib) == {"run_dir_bytes": 10 * gib, "free_bytes": 60 * gib}
    with pytest.raises(accounting.DiskPause):
        accounting.check_disk(tmp_path, CFG, used=110 * gib, free=900 * gib)
    with pytest.raises(accounting.DiskPause):
        accounting.check_disk(tmp_path, CFG, used=1, free=50 * gib - 1)
    assert accounting.disk_projection_bytes(524288, CFG) == 524288 * 609
    assert accounting.memory_projection_bytes(524288, CFG) / 2**30 == pytest.approx(0.558, abs=0.001)  # the ADR's 0.56 GiB
    assert accounting.memory_projection_bytes(1048576, CFG) / 2**30 == pytest.approx(1.117, abs=0.001)


def test_quiet_check_is_bounded_and_reads_before_the_workers() -> None:
    slept: list[float] = []
    loads = iter([0.5, 0.6, 0.7, 1.9, 2.0, 1.0, 0.9])
    r = accounting.quiet_check(CFG, sampler=lambda: next(loads), sleep=slept.append, others=lambda: [])
    assert r["quiet"] and len(r["samples"]) == 7 and slept == [10.0] * 6  # seven samples, ten seconds apart, over 60 s
    loud = iter([0.5, 0.6, 0.7, 2.01, 1.0, 1.0, 1.0])
    r = accounting.quiet_check(CFG, sampler=lambda: next(loud), sleep=lambda s: None, others=lambda: [])
    assert not r["quiet"] and r["reasons"] == ["a load-average sample above 2.0"]
    r = accounting.quiet_check(CFG, sampler=lambda: 0.1, sleep=lambda s: None, others=lambda: [{"pid": 1, "command": "python -m studies.p10s1"}])
    assert not r["quiet"] and "another study's process is alive" in r["reasons"]


def test_attempts_rule() -> None:
    t0 = datetime(2026, 11, 20, tzinfo=UTC)
    q, n = {"quiet": True}, {"quiet": False}
    assert accounting.attempt_decision([], t0, t0, CFG)["decision"] == "RETRY"
    assert accounting.attempt_decision([n], t0, t0 + timedelta(hours=1), CFG)["decision"] == "RETRY"
    assert accounting.attempt_decision([n, q], t0, t0, CFG) == {"decision": "READY", "use_attempt": 1}  # the first attempt that met the condition; a failed one is never used
    assert accounting.attempt_decision([q, n, n], t0, t0, CFG)["use_attempt"] == 0
    assert accounting.attempt_decision([n, n, n], t0, t0, CFG)["decision"] == accounting.PAUSED_NOT_QUIET
    assert accounting.attempt_decision([n], t0, t0 + timedelta(hours=25), CFG)["decision"] == accounting.PAUSED_NOT_QUIET


def test_stage3_rates_need_enough_updates() -> None:
    ok = [{"arm": "A0", "slots": 512, "updates": 8192, "wall_seconds": 81.92}]
    assert accounting.stage3_rates(ok, CFG) == {("A0", 512): pytest.approx(0.01)}
    with pytest.raises(ValueError):
        accounting.stage3_rates([{"arm": "A0", "slots": 512, "updates": 100, "wall_seconds": 1.0}], CFG)
