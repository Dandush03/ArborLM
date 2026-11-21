# ruff: noqa: E501
"""P10IS5 device-layer tests (ADR-0028 sections 5.1, 6, 7; rulings 2, 13): the write ledger and its refusal at the cap, the uncached build with its chunk verification and resume, the counter rule, the cold check, the
hold-cold rule (PAUSED — STORE NOT COLD, one rebuild, STORE CANNOT BE HELD COLD), free space, the data-mismatch stop. Real files of a few MiB under ``experiments/_scratch/`` (deleted when each test ends: the total these
tests write is tallied in ``experiments/_scratch/p10is5_test_bytes_written.log``); the physical counter is a fake over real reads, so no test depends on the machine's cache. One optional smoke test uses the real counter
and is skipped unless P10IS5_REAL_DEVICE=1. Self-check only: not independent review, not Astra validation, not human approval."""

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import core, device, harness, layout  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402

MIB = 1 << 20
SEED = T.TEST_SEED_CONTENTS


def test_scratch_is_inside_the_worktree_scratch_directory() -> None:
    with T.scratch("device_guard") as d:
        assert str(d).startswith(str(core.repo_root() / "experiments" / "_scratch"))


def test_counter_rule_by_hand() -> None:
    assert device.counter_rule(16384 * 10, 10) == "OK"
    assert device.counter_rule(16384 * 10 - 1, 10) == "STORE PAGES CACHED" and device.counter_rule(0, 10) == "STORE PAGES CACHED"
    assert device.counter_rule(16384 * 10 + 1, 10) == "COUNTER CONTAMINATED"
    assert device.counter_rule(16384 * 10, 10, written_bytes=1) == "COUNTER CONTAMINATED"  # the bytes written during a read pass must be 0


def test_write_ledger_refuses_at_the_cap_before_any_write_is_made() -> None:
    with T.scratch("device_ledger") as d:
        led = device.WriteLedger(d / "ledger.json", 10_000)
        f = d / "f.bin"
        fd = device.open_uncached_write(f)
        try:
            led.begin("a", 4_000)
            assert led.write(fd, b"x" * 4_000, 0) == 4_000 and led.total() == 4_000
            with pytest.raises(core.WriteBudgetExceeded, match="exceeds"):
                led.write(fd, b"y", 4_000)  # nothing is reserved any more
            assert f.stat().st_size == 4_000  # the refused write was not made
            assert led.end() == 0
            with pytest.raises(core.WriteBudgetExceeded, match="would pass the cap"):
                led.begin("b", 6_001)  # 4,000 + 6,001 > 10,000
            assert led.total() == 4_000  # a refused reservation charges nothing
            led.begin("b", 6_000)
            led.write(fd, b"z" * 6_000, 4_000)
            led.end()
            assert led.total() == 10_000 and led.remaining() == 0
            with pytest.raises(core.WriteBudgetExceeded):
                led.begin("c", 1)
        finally:
            os.close(fd)
        assert device.WriteLedger(d / "ledger.json", 10_000).total() == 10_000  # persisted across instances: every stage and attempt counts
        assert isinstance(core.WriteBudgetExceeded("x"), core.Paused)  # PAUSED, resumable
        led2 = device.WriteLedger(d / "l2.json", 10_000)
        led2.begin("one", 100)
        with pytest.raises(RuntimeError, match="still open"):
            led2.begin("two", 1)
        assert led2.end() == 100  # unwritten reserved bytes stay charged
        assert led2.total() == 100


def test_ledger_charges_the_larger_of_logical_and_observed() -> None:
    with T.scratch("device_settle") as d:
        led = device.WriteLedger(d / "l.json", 1_000_000)
        led.begin("x", 1000)
        led.end()
        assert led.settle("x", 1000, 900) == 0 and led.total() == 1000  # observed below logical: the logical bytes stand
        assert led.settle("x", 1000, 1500) == 500 and led.total() == 1500  # observed above: the larger is charged
        with pytest.raises(ValueError):
            device.WriteLedger(d / "bad.json", 0)


def test_free_space_below_the_minimum_is_paused() -> None:
    with T.scratch("device_free") as d:
        assert device.require_free_space(d, 1) > 0
        with pytest.raises(core.Paused, match="FREE SPACE"):
            device.require_free_space(d, 10**18)


def test_build_verify_resume_cold_check_and_hold_cold() -> None:
    with T.scratch("device_build") as d:
        path = d / "f.bin"
        io = T.RealFileIO()
        counter = T.FakeCounter(io)
        led = device.WriteLedger(d / "ledger.json", 100 * MIB)
        rep = device.build_file(path, 3, SEED, led, counter, chunk_bytes=2 * MIB, pread=io.pread)
        assert rep["complete"] and rep["chunks"] == 2 and path.stat().st_size == 3 * MIB and led.total() == 3 * MIB
        assert [c["verify_status"] for c in rep["chunk_reports"]] == ["OK", "OK"] and [c["verify_counter_bytes"] for c in rep["chunk_reports"]] == [2 * MIB, MIB]
        data = path.read_bytes()
        for t in range(3):  # the file holds exactly the regenerated tiles
            assert data[t * MIB : (t + 1) * MIB] == layout.tile_bytes(SEED, t)
        assert rep["chunk_reports"][0]["sha256"] == hashlib.sha256(layout.tile_bytes(SEED, 0) + layout.tile_bytes(SEED, 1)).hexdigest()
        with pytest.raises(core.StageRefused, match="exists"):
            device.build_file(path, 3, SEED, led, counter, chunk_bytes=2 * MIB, pread=io.pread)  # never overwritten silently
        # resume at the first unverified chunk: the manifest loses chunk 1; only that chunk is written again, and charged again
        import json

        m = device.manifest_path(path)
        rec = json.loads(m.read_text())
        rec["verified_chunks"] = rec["verified_chunks"][:1]
        m.write_text(json.dumps(rec))
        rep2 = device.build_file(path, 3, SEED, led, counter, chunk_bytes=2 * MIB, resume=True, pread=io.pread)
        assert rep2["resumed_from_chunk"] == 1 and len(rep2["chunk_reports"]) == 1 and led.total() == 4 * MIB
        with pytest.raises(core.StageRefused, match="another geometry"):
            device.build_file(path, 4, SEED, led, counter, chunk_bytes=2 * MIB, resume=True, pread=io.pread)
        # cold check: exact count is cold; the bytes are compared with the regenerated tiles
        c = device.cold_check(path, 3, SEED, counter, pread=io.pread)
        assert c["cold"] and c["counter_bytes"] == 3 * MIB and c["status"] == "OK" and c["verdict"] == "COLD"
        # a page 'already cached' counts short: STORE NOT COLD
        io.short_offsets = {1 * MIB}
        c = device.cold_check(path, 3, SEED, counter, pread=io.pread)
        assert not c["cold"] and c["counter_bytes"] == 2 * MIB and c["verdict"] == "PAUSED — STORE NOT COLD"
        # hold_cold: one rebuild (the callback clears the pollution), the 10-minute wait, and checked again
        events: list[str] = []
        rec1 = device.hold_cold(path, 3, SEED, counter, lambda: (events.append("rebuild"), io.short_offsets.clear()), lambda: events.append("wait"), pread=io.pread)
        assert rec1["outcome"] == "COLD" and rec1["rebuilt"] and events == ["rebuild", "wait"] and rec1["first"]["verdict"] == "PAUSED — STORE NOT COLD" and rec1["second"]["cold"]
        events.clear()
        rec2 = device.hold_cold(path, 3, SEED, counter, lambda: events.append("rebuild"), lambda: events.append("wait"), pread=io.pread)
        assert rec2["outcome"] == "COLD" and not rec2["rebuilt"] and events == [] and rec2["second"] is None  # cold at the first check: no rebuild
        io.short_offsets = {0}
        rec3 = device.hold_cold(path, 3, SEED, counter, lambda: events.append("rebuild2"), lambda: events.append("wait2"), pread=io.pread)  # still short after the one rebuild
        assert rec3["outcome"] == "ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD" and events[-2:] == ["rebuild2", "wait2"]
        io.short_offsets = set()
        # a counter above the file size is contamination, not 'not cold'
        over = device.cold_check(path, 3, SEED, T.FakeCounter(_Over(io)), pread=io.pread)
        assert over["verdict"] == "COUNTER CONTAMINATED" and not over["cold"]
        # one byte of the file differs from the regenerated tile: ENGINEERING STOP (DATA MISMATCH), never a label
        fd = os.open(path, os.O_WRONLY)
        os.pwrite(fd, b"\x00\x01", 5 * layout.PAGE)
        os.close(fd)
        with pytest.raises(core.EngineeringStop, match="DATA MISMATCH"):
            device.cold_check(path, 3, SEED, counter, pread=io.pread)
        # deletion: unlinked, absent, free space recorded
        gone = device.delete_built_file(path)
        assert gone["absent"] and gone["free_bytes"] > 0 and not path.exists() and not device.manifest_path(path).exists()


class _Over:
    """A counter that reports one extra byte per scan."""

    def __init__(self, io: T.RealFileIO) -> None:
        self.io = io
        self.calls = 0

    def counter_read(self):  # type: ignore[no-untyped-def]
        s = self.io.counter_read()
        self.calls += 1
        return device.IOSnapshot(s.bytes_read + (1 if self.calls > 1 else 0), 0, 0)


def test_build_stops_when_the_verification_read_is_short() -> None:
    with T.scratch("device_notcold") as d:
        path = d / "f.bin"
        io = T.RealFileIO()
        io.short_offsets = {0}
        led = device.WriteLedger(d / "ledger.json", 100 * MIB)
        with pytest.raises(device.StoreNotCold, match="STORE NOT COLD"):
            device.build_file(path, 1, SEED, led, T.FakeCounter(io), chunk_bytes=MIB, pread=io.pread)
        assert led.total() == MIB  # the failed attempt is charged: failed attempts count against the cap


def test_build_refuses_a_write_past_the_cap_before_writing() -> None:
    with T.scratch("device_buildcap") as d:
        path = d / "f.bin"
        io = T.RealFileIO()
        led = device.WriteLedger(d / "ledger.json", MIB // 2)
        with pytest.raises(core.WriteBudgetExceeded):
            device.build_file(path, 1, SEED, led, T.FakeCounter(io), chunk_bytes=MIB, pread=io.pread)
        assert not path.exists() or path.stat().st_size == 0


def test_uncached_scan_requires_page_alignment() -> None:
    with T.scratch("device_align") as d:
        f = d / "f.bin"
        f.write_bytes(b"\0" * 32768)
        io = T.RealFileIO()
        with pytest.raises(ValueError, match="whole pages"):
            device.uncached_scan(f, 1, 16384, T.FakeCounter(io), pread=io.pread)
        res = device.uncached_scan(f, 0, 32768, T.FakeCounter(io), request_bytes=16384, pread=io.pread)
        assert res.counter_bytes == 32768 and res.status == "OK" and res.pages == 2


@pytest.mark.skipif(os.environ.get("P10IS5_REAL_DEVICE") != "1", reason="real-device smoke test: set P10IS5_REAL_DEVICE=1 (writes 4 MiB under experiments/_scratch, deleted at the end)")
def test_real_device_smoke() -> None:
    """The real syscalls on this machine: F_NOCACHE write and read, F_RDAHEAD off, os.pread from threads, the per-process counter through ctypes. Not a registered measurement."""
    if sys.platform != "darwin":
        pytest.skip("macOS only")
    with T.scratch("device_real") as d:
        path = d / "f.bin"
        counter = device.ProcCounter()
        led = device.WriteLedger(d / "ledger.json", 64 * MIB)
        c0 = counter.read()
        rep = device.build_file(path, 4, SEED, led, counter, chunk_bytes=4 * MIB)
        c1 = counter.read()
        assert rep["complete"] and c1.bytes_written - c0.bytes_written >= 4 * MIB and rep["chunk_reports"][0]["verify_status"] == "OK"
        cold = device.cold_check(path, 4, SEED, counter)
        assert cold["counter_bytes"] == 4 * MIB and cold["cold"], cold  # the whole file, read uncached: exact
        reqs = layout.pass_requests([0, 1, 2, 3], 4, 1, 64, T.TEST_SEED_REQUEST[0])
        res = harness.run_pass(path, reqs, 4, counter)
        assert res.counter_bytes == 64 * layout.PAGE and res.written_bytes == 0 and res.max_in_flight() >= 1
        cached_first = harness.run_pass(path, layout.pass_requests([0], 1, 64, 1, T.TEST_SEED_REQUEST[0]), 1, counter, uncached=False)
        cached_second = harness.run_pass(path, layout.pass_requests([0], 1, 64, 1, T.TEST_SEED_REQUEST[0]), 1, counter, uncached=False)
        print("real-device smoke:", {"cached_first": cached_first.counter_bytes, "cached_second": cached_second.counter_bytes, "uncached_k4": res.counter_bytes})
        assert cached_second.counter_bytes == 0  # the positive control
