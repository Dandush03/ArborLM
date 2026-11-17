# ruff: noqa: E501
"""P10S2 re-check A, R2/R3/R16: the data-generation step's installation and stop records, on fakes (no network, no real file, no real ledger). Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import ledger  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_r2_requirements_are_checked_before_any_install_and_installed_versions_must_equal_the_pins(tmp_path: Path) -> None:
    from studies.p10s2 import datagen
    from studies.p10s2 import install_datagen as ins

    h = " \\\n    --hash=sha256:" + "0" * 64
    good = "".join(f"{n}=={v}{h}\n" for n, v in ins.EXPECTED_PINS.items())
    req = tmp_path / "req.txt"
    req.write_text(good)
    assert ins.check_requirements(req) == ins.EXPECTED_PINS
    for bad in ("-e ./x\n", "-r other.txt\n", "--extra-index-url http://example.org/simple\n", "--index-url https://x\n"):
        req.write_text(good + bad)
        with pytest.raises(ins.InstallRefused, match="option lines"):
            ins.check_requirements(req)
        with pytest.raises(datagen.DatagenStop, match="option lines"):
            datagen.check_requirements_hashed(req)
    req.write_text(good.replace("numpy==2.3.3", "numpy==2.3.4"))
    with pytest.raises(ins.InstallRefused, match="numpy"):
        ins.check_requirements(req)
    req.write_text(good.replace(h, "", 1))
    with pytest.raises(datagen.DatagenStop):
        ins.check_requirements(req)
    req.write_text(good)
    # run with a fake installer and fake ledgers: a row before and after, the install charged, the versions asserted, the directory removed on a refusal
    from studies.p10s2 import fetch_guard

    dl = tmp_path / "DOWNLOAD_LEDGER.md"
    head, _rows, tail = fetch_guard._read_ledger(ROOT / fetch_guard.DOWNLOAD_LEDGER)  # the real table format, none of its rows
    fetch_guard._write_ledger(dl, head, [], tail)
    calls: list[str] = []
    led = Ledger(tmp_path / "ledger.jsonl")

    def installer_ok(requirements: Path, target: Path) -> None:
        calls.append("install")
        for n, v in ins.EXPECTED_PINS.items():
            d = target / f"{n.replace('-', '_')}-{v}.dist-info"
            d.mkdir(parents=True)
            (d / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {n}\nVersion: {v}\n")

    got = ins.run(req, tmp_path / "pkgs", led=led, download_ledger=dl, installer=installer_ok)
    assert got == ins.EXPECTED_PINS and calls == ["install"] and [e["kind"] for e in led.entries()] == ["install", "install"]
    assert "data-generation packages" in dl.read_text() and "completed" in dl.read_text()  # a row before the install, completed after it
    with pytest.raises(ins.InstallRefused, match="exists"):
        ins.run(req, tmp_path / "pkgs", led=led, download_ledger=dl, installer=installer_ok)
    wrong = tmp_path / "pkgs2"

    def installer_wrong(requirements: Path, target: Path) -> None:
        installer_ok(requirements, target)
        (target / "torch").mkdir()  # shadows the locked torch

    with pytest.raises(ins.InstallRefused, match="shadow"):
        ins.run(req, wrong, led=led, download_ledger=dl, installer=installer_wrong)
    assert not wrong.exists()  # nothing stays on the path
    src = (ROOT / "studies/p10s2/launch/datagen.sh").read_text()
    assert "--with-requirements" not in src and "install_datagen" in src and 'PYTHONPATH="$PWD/data/datagen-packages"' in src
    with pytest.raises(datagen.DatagenStop, match="eight pins"):
        datagen.check_installed_pins({**ins.EXPECTED_PINS, "numpy": "1.0"})
    datagen.check_installed_pins(dict(ins.EXPECTED_PINS))


def test_r3_r16_every_exception_after_the_start_leaves_a_stop_record_each_attempt_is_kept_and_a_registered_test_returns_to_the_lead(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10s2 import datagen

    class Fake:
        def __init__(self) -> None:
            self.led = Ledger(tmp_path / "ledger.jsonl")

        def remaining(self) -> float:
            return 10.0

        def charge(self, stage: str, seconds: float) -> None:
            self.led.record(stage if stage in ledger.STAGE_KINDS else "datagen", seconds)

    def boom(exc: BaseException):  # type: ignore[no-untyped-def]
        def f(*a: Any, **k: Any) -> Any:
            raise exc

        return f

    out = tmp_path / "out"
    monkeypatch.setattr(datagen, "package_versions", lambda: {})
    for i, exc in enumerate((ValueError("a newline in a prompt"), datagen.StageCapExceeded("cap"), KeyboardInterrupt())):
        monkeypatch.setattr(datagen, "_run", boom(exc))
        with pytest.raises(type(exc)):
            datagen.run(tmp_path / "dl", out, led=Fake(), stage_cap_seconds=3600.0)
        rec = json.loads((out / "datagen_attempts" / f"attempt-{i + 1:03d}.json").read_text())
        assert rec["stop_kind"] == "engineering" and rec["attempt"] == i + 1 and type(exc).__name__ in rec["stopped"]
    assert len(list((out / "datagen_attempts").glob("attempt-*.json"))) == 3  # every attempt's record is kept; a re-run after an engineering stop is allowed
    monkeypatch.setattr(datagen, "_run", boom(datagen.ScoreMismatch("score differs")))
    with pytest.raises(datagen.ScoreMismatch):
        datagen.run(tmp_path / "dl", out, led=Fake(), stage_cap_seconds=3600.0)
    assert json.loads((out / "datagen_attempts" / "attempt-004.json").read_text())["stop_kind"] == "registered-test"
    with pytest.raises(datagen.DatagenStop, match="returns to the lead"):
        datagen.run(tmp_path / "dl", out, led=Fake(), stage_cap_seconds=3600.0)  # a stop on a registered test is not re-run
    (out / "datagen_attempts" / "lead_release.json").write_text(json.dumps({"releases_attempt": 4, "cause": "the score comparison was read by the lead", "released_by": "lead"}))
    assert datagen.datagen_rerun_gate(out) is None
    assert datagen.stop_kind(datagen.RegisteredTestStop("x")) == "registered-test" and datagen.stop_kind(RuntimeError("x")) == "engineering"
    assert all(e["status"] in ("started", "completed", "failed") for e in Fake().led.entries())
