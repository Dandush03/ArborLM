# ruff: noqa: E501
"""P10IS0: E2 (rehearsal cell records are sealed; the public rehearsal record is whitelisted) and E1 (the wave limit names duration)."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from studies.p10is0 import core, rehearsal, sealed  # noqa: E402
from studies.p10is0.profile import MARKER  # noqa: E402

FORBIDDEN_KEYS = ("task_loss", "diversity_loss", "accuracy", "correct", "distinct_top1", "address_stability", "a_use", '"obs"', "readouts")


def test_the_real_phase_seals_its_cell_records_and_the_public_record_is_whitelisted(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / MARKER).write_text("test profile: the real phase's code path on tiny synthetic data\n")
    store = tmp_path / "store"
    rec = rehearsal.real(REPO, run, "2K/512", 16, store, allow_test_profile=True)
    assert set(rec["stages"]) == {"A5-D", "A6"} and all(v["status"] == "COMPLETE" for v in rec["stages"].values())
    sealed_results = sorted((sealed.sealed_dir(store) / "rehearsal" / "cells").glob("*/result.json"))
    assert len(sealed_results) == 2 and list((sealed.sealed_dir(store) / "rehearsal" / "cells").glob("*/updates_*.jsonl"))
    secrets = set()
    for f in sealed_results:
        for ro in json.loads(f.read_text())["readouts"].values():
            secrets.add(json.dumps(ro["a"]))  # the accuracy counts, e.g. [correct, n]
            secrets.add(json.dumps(ro["h1"]))
    secrets = {s for s in secrets if s not in ("[0, 128]",)}
    public = [f for f in run.rglob("*") if f.is_file() and f.suffix in (".json", ".jsonl", ".log", ".md") and "draws" not in f.relative_to(run).parts]  # the draws' own G1 data checks (a dictionary-lookup check of the data) hold no model value
    assert any(f.name == "rehearsal_real.json" for f in public) and not (run / "cells").exists()  # the old code wrote <run>/cells/REH-*/result.json
    for f in public:
        text = f.read_text(errors="ignore")
        for k in FORBIDDEN_KEYS:
            assert k not in text, (f.name, k)
        for s in secrets:
            assert s not in text, (f.name, s)  # no value equal to a sealed one


def test_the_whitelist_refuses_other_keys() -> None:
    ok = {**core.envelope("rehearsal"), "phase": "real", "stages": {"A6": {"status": "COMPLETE", "seconds_per_update": 0.01, "peak_rss_bytes": 5}}, "items": 2, "platform": {"system": "Darwin"}}
    assert rehearsal.public_rehearsal_record(ok) is ok
    with pytest.raises(rehearsal.RehearsalRecordError, match="whitelist"):
        rehearsal.public_rehearsal_record({**ok, "accuracy": 0.9})
    with pytest.raises(rehearsal.RehearsalRecordError, match="stage"):
        rehearsal.public_rehearsal_record({**ok, "stages": {"A6": {"status": "COMPLETE", "task_loss": 3.1}}})
    with pytest.raises(rehearsal.RehearsalRecordError, match="platform"):
        rehearsal.public_rehearsal_record({**ok, "platform": {"system": "Darwin", "probe": 1}})


def test_the_wave_limit_names_task_count_and_duration() -> None:
    s = sealed.WAVE_LIMIT_SENTENCE
    assert "task count" in s and "duration" in s and "not which" in s
