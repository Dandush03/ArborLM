# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: the ONE study ledger of charged hours (ADR-0022 section 13.2; the lead's ruling of 2026-11-15, audit B B3 and M3): every stage charges it and reads it, P is never
ignored, a killed process is not free, the cap raise lives in it. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import core, ledger  # noqa: E402
from studies.p10s2.ledger import Ledger, LedgerRefused  # noqa: E402


def test_the_study_ledger_is_one_file_outside_every_run_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert ledger.STUDY_LEDGER == Path("experiments/P10S2/ledger.jsonl")
    monkeypatch.setattr(core, "ROOT", tmp_path)
    a, b = Ledger(), Ledger()
    assert a.path == b.path == tmp_path / "experiments" / "P10S2" / "ledger.jsonl"
    a.charge("datagen", 3600.0, process="data generation")
    assert b.total_hours() == pytest.approx(1.0)  # what one stage charged, every other stage reads: P is never ignored
    b.charge("calibration", 1800.0)
    assert a.total_hours() == pytest.approx(1.5) and a.remaining() == pytest.approx(36.0 - 1.5) and a.remaining(72.0) == pytest.approx(72 - 1.5)


def test_charge_with_seconds_records_and_without_seconds_measures(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.jsonl")
    e = led.charge("fetch", 7200.0, workers=2, process="two parallel workers")
    assert e["charged_hours"] == pytest.approx(4.0)  # k workers for t hours charge k t
    with led.charge("datagen", process="block form"):
        pass
    assert [x["status"] for x in led.entries() if x["kind"] == "datagen"] == ["started", "completed"]
    with pytest.raises(ValueError):
        led.charge("unknown", 1.0)
    with pytest.raises(ValueError):
        led.charge("train", -1.0)


def test_every_stage_kind_of_the_study_has_a_charge() -> None:
    assert {"fetch", "datagen", "calibration", "gates-rehearsal", "rehearsal", "gates-registered", "train", "evaluate", "timing", "recompute", "analysis", "report"} <= set(ledger.STAGE_KINDS)


def test_a_killed_process_is_not_free(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.jsonl")
    led.record("train", 0.0, status="started", run_id="killed", registered=True, t_start=time.time() - 7200.0)  # a start marker with no end entry: SIGKILL
    assert led.unfinished() and led.total_hours() == pytest.approx(2.0, abs=0.01)  # charged the wall time elapsed since its start
    assert led.total_hours(exclude_run="killed") == 0.0  # the running stage does not count itself twice
    assert led.registered_observed()  # and the seeds it drew count as observed
    led.record("train", 7000.0, run_id="killed", registered=True)  # an end entry resolves it
    assert not led.unfinished() and led.total_hours() == pytest.approx(7000.0 / 3600.0)


def test_the_cap_raise_is_an_entry_of_the_ledger_and_refuse_if_over_reads_everything(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.jsonl")
    led.record("rehearsal", 35 * 3600.0)
    led.refuse_if_over(0.5, None, "ok")
    with pytest.raises(LedgerRefused, match="over the cap of 36.0 h"):
        led.refuse_if_over(1.5, None, "stage evaluate")  # P is part of the room check: 35 h are already charged
    led.append_cap_raise(50.0, {"x": 1})
    assert led.cap_hours() == 50.0 and led.cap_raise_entry()["new_cap_hours"] == 50.0
    led.refuse_if_over(1.5, None, "under the raised cap")
    assert led.summary()["cap_hours"] == 50.0 and led.summary()["by_kind"] == {"rehearsal": 35.0}
    led.append_cap_raise(80.0, {})
    with pytest.raises(LedgerRefused, match="above the ceiling"):
        led.cap_hours()


def test_the_start_marker_precedes_the_stage_and_an_end_entry_follows_a_failure(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.jsonl")
    seen: list[int] = []
    with pytest.raises(RuntimeError):
        with led.measure("gates-registered", registered=True, process="x"):
            seen.append(len(led.entries()))  # the marker is already written when the block starts
            assert led.registered_observed()
            raise RuntimeError("boom")
    assert seen == [1] and [e["status"] for e in led.entries()] == ["started", "failed"]
    lines = (tmp_path / "l.jsonl").read_text().splitlines()
    assert all(json.loads(ln)["kind"] == "gates-registered" for ln in lines)
