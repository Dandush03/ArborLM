# ruff: noqa: E501
"""P10IS5 stage R0 test (ADR-0028 section 8): the record, the three probes (shrunk to 1 MiB each: 3 MiB really written under experiments/_scratch, deleted), the ledger, Spotlight blocking. Fake machine and reads."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import blocks, core, device, r0  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402

CFG = core.load_config()


def test_r0_record_and_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    for n in ("PROBE_A_BYTES", "PROBE_B_BYTES", "PROBE_C_BYTES"):
        monkeypatch.setattr(r0, n, 1 << 20)
    assert 32 * 2**20 + 16 * 2**20 + 8 * 2**20 <= CFG["budget"]["probe_bytes"]  # the real probes total 56 MiB, inside the 64 MiB
    cfg = copy.deepcopy(dict(CFG))
    cfg["budget"] = {**cfg["budget"], "probe_bytes": 3 << 20, "free_space_min_bytes": 1}
    with T.scratch("r0") as d:
        clk = T.Clock()
        fs = T.FakeSystem(clk)
        io = T.FakeIO(1)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=fs.run, run_b=fs.run_b, sleep=clk.sleep, clock=clk, pread=io.pread, opener=io.opener)
        led = device.WriteLedger(d / "run" / "w.json", 10**9)
        rec = r0.run_r0(cfg, d / "data.noindex", d / "run", deps, led, [])
        assert set(rec["probes"]) == {"probe_1", "probe_2", "probe_3"} and led.total() == 3 << 20 and rec["ec3_before"]["lifetime_bytes_written"] == "NOT READABLE"
        assert rec["counters"]["process"]["readable"] and not list((d / "data.noindex").glob("probe_*"))
        assert rec["hygiene"]["blocks_e1"] is False and rec["probes"]["probe_1"]["delete"]["absent"]
