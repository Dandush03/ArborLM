# ruff: noqa: E501
"""P10IS5 stage R1 tests (ADR-0028 sections 7, 8, 5.4; ruling 11): the band geometry, counter exactness for every request size at depth 1 and depth 32, the cold check with one rebuild and STORE CANNOT BE HELD COLD, the control
file's positive control, pollution control, 4 KiB amplification and harness figure, the idle baseline (PAUSED after the deadline), the mapping of failures to the ADR's NOT EVALUABLE reasons, resume. A fake machine and fake reads
(no device; the 'files' are empty placeholders): the geometry is shrunk through a copy of the config so that the whole stage runs in RAM. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import blocks, core, device, layout, r1  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402

CFG = core.load_config()
SEED_R = int(CFG["seeds"]["r1_rehearsal_file_contents"])


def small_cfg() -> dict[str, Any]:
    c = copy.deepcopy(dict(CFG))
    c["device"] = {**c["device"], "band_start_tile": 8, "rehearsal_tiles": 64, "control_tiles": 24}
    c["cells"] = {**c["cells"], "r1_reread_working_set_tiles": [2, 4, 8]}
    return c


def machine(other: list[tuple[float, float]] = (), cached_pages: set[int] | None = None, opener_always_uncached: bool = False):  # type: ignore[no-untyped-def]
    clk = T.Clock()
    fs = T.FakeSystem(clk, other_windows=list(other))
    io = T.FakeIO(SEED_R)
    io.model_cache = True
    io.cache = {("rest", p) for p in (cached_pages or ())}
    gate = T.scripted_gate(lambda: T.quiet_record(True))
    opener = T.devnull_opener if opener_always_uncached else io.opener
    deps = blocks.Deps(counter=T.FakeCounter(io), gate=gate, run=fs.run, run_b=fs.run_b, sleep=clk.sleep, clock=clk, pread=io.pread, opener=opener)
    return clk, io, deps


def touching_builder(calls: list[str]):  # type: ignore[no-untyped-def]
    def build(path: Path, tiles: int, seed: int, ledger: device.WriteLedger, counter: Any, **kw: Any) -> dict[str, Any]:
        calls.append(path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")  # a placeholder: the fake reads synthesise the bytes
        ledger.begin(f"{path.name}", tiles * layout.TILE_BYTES)
        ledger.end()
        return {"path": str(path), "tiles": tiles, "complete": True}

    return build


def test_band_geometry_registered_config() -> None:
    reqs = r1.band_requests(CFG)
    assert sorted(reqs) == sorted((k, s) for k in (1, 32) for s in (1, 3, 8, 64))
    tiles: dict[tuple[int, int], set[int]] = {c: {x.tile for x in v} for c, v in reqs.items()}
    # dealt in order from tile 896: k = 1 (2, 5, 5, 16 tiles) then k = 32 (2, 5, 5, 16): tiles 896 to 951, 56 tiles
    assert tiles[(1, 1)] <= set(range(896, 898)) and tiles[(1, 3)] <= set(range(898, 903)) and tiles[(1, 8)] <= set(range(903, 908)) and tiles[(1, 64)] == set(range(908, 924))
    assert tiles[(32, 1)] <= set(range(924, 926)) and tiles[(32, 64)] == set(range(936, 952))
    allt = set().union(*tiles.values())
    assert min(allt) == 896 and max(allt) == 951 and len(allt) <= 56
    for (k, s), v in reqs.items():
        assert len(v) == {1: 100, 3: 100, 8: 40, 64: 16}[s] and [x.thread for x in v] == [j % k for j in range(len(v))] and all(x.length == s * 16384 for x in v)
    pages = [p for v in reqs.values() for x in v for p in layout.pages_of(x)]
    assert len(pages) == len(set(pages))  # no page twice inside the band's passes


def test_harness_requests_are_the_first_400_of_448_pages_of_tiles_0_to_6() -> None:
    a = r1.harness_requests(289013, 4, 400, 7)
    b = r1.harness_requests(289013, 4, 400, 7)
    assert a == b and len(a) == 400 and len({x.offset for x in a}) == 400 and all(x.tile < 7 and x.length == 16384 for x in a)
    assert [x.thread for x in a] == [j % 4 for j in range(400)] and r1.harness_requests(289013, 8, 400, 7) != a


def test_full_stage_in_ram_passes_and_every_check_is_recorded() -> None:
    cfg = small_cfg()
    with T.scratch("r1_ok") as d:
        clk, io, deps = machine()
        calls: list[str] = []
        led = device.WriteLedger(d / "run" / "ledger.json", 10**9)
        rec = r1.run_r1(cfg, d / "data", d / "run", deps, led, now=clk, builder=touching_builder(calls), hygiene=lambda ex: {"blocks_e1": False}, ec3=lambda label: {"health_ok": True, "smart_status": "Verified", "label": label})
        assert rec["passed"] and rec["outcome"] == "R1 PASSED" and rec["not_evaluable_reasons"] == [] and rec["checks_not_shown"] == [] and rec["cold"] == "COLD"
        assert calls == ["control.bin", "rehearsal.bin"] and rec["idle_own_check_passed"] and rec["idle_figures"]["samples"] == 60
        band = core.read_record(d / "run" / "r1" / "steps" / "band.json")
        assert len(band["passes"]) == 16 and band["all_exact"] and all(p["counter_bytes"] == p["predicted_bytes"] and p["parity_ok"] for p in band["passes"])
        assert {(p["cell"][0], p["cell"][1]) for p in band["passes"]} == {(k, s) for k in (1, 32) for s in (1, 3, 8, 64)} and {p["which"] for p in band["passes"]} == {"first", "repeat"}
        assert band["k32_max_in_flight"] >= 1 and sorted(p["predicted_bytes"] for p in band["passes"] if p["cell"] == [1, 64]) == [16 * 1048576] * 2
        ctrl = core.read_record(d / "run" / "r1" / "steps" / "control.json")
        assert ctrl["amplification"]["shown"] and ctrl["amplification"]["counter_bytes"] == 256 * 16384 and ctrl["amplification"]["amplification"] == 4.0
        c = ctrl["controls"]
        assert c["positive_control_passed"] and c["cached_second_counter_bytes"] == 0 and c["cached_first_counter_bytes"] == 8 * 1048576
        assert c["pollution_nocache_after_cached_counter_bytes"] == 0 and not c["nocache_bypassed_cached_pages"]  # probe 1D: F_NOCACHE does not bypass pages already cached
        assert sorted(ctrl["harness"], key=int) == ["1", "2", "4", "8", "16", "32"] and all(v["status"] == "MEASURED" and v["median_ns"] > 0 for v in ctrl["harness"].values())
        rr = core.read_record(d / "run" / "r1" / "steps" / "rereads.json")
        assert [w["working_set_tiles"] for w in rr["working_sets"]] == [2, 4, 8] and all(p["counter_status"] == "OK" for w in rr["working_sets"] for p in w["passes"]) and rr["descriptive"]
        # the idle window came first and the cold wait was taken after the build (fake time)
        assert clk.t >= 600 + 600
        # resume: nothing is built or measured again
        calls.clear()
        rec2 = r1.run_r1(cfg, d / "data", d / "run", deps, led, now=clk, builder=touching_builder(calls), hygiene=lambda ex: {"blocks_e1": False}, ec3=lambda label: {"health_ok": True, "smart_status": "Verified"})
        assert calls == [] and rec2["passed"]


def test_idle_baseline_is_taken_first_and_r1_is_paused_without_one() -> None:
    cfg = small_cfg()
    with T.scratch("r1_idle") as d:
        clk, io, deps = machine(other=[(0.0, 1e12)])
        calls: list[str] = []
        with pytest.raises(core.Paused, match="NO IDLE BASELINE"):
            r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder(calls))
        assert calls == []  # nothing was built: the idle window is taken before any write
        assert (d / "run" / "r1" / "steps" / "idle_paused.json").is_file() and clk.t <= 21600 + 600 + 700


def test_spotlight_indexing_is_recorded_by_r1_and_pauses_only_before_e1() -> None:
    """ADR section 6: 'PAUSED before E1'. R1 records the hygiene result and goes on; E1 and E2 pause (``e2.check_order``)."""
    cfg = small_cfg()
    with T.scratch("r1_spot") as d:
        clk, io, deps = machine()
        calls: list[str] = []
        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder(calls), hygiene=lambda ex: {"blocks_e1": True, "spotlight_indexes_directory": True})
        assert calls == ["control.bin", "rehearsal.bin"] and rec["passed"]  # R1 was not paused
        assert core.read_record(d / "run" / "r1" / "steps" / "hygiene.json")["blocks_e1"] is True
        from studies.p10is5 import e2

        fs = T.FakeSystem(clk)
        orig = fs.run
        deps.run = lambda a: (0, "Indexing enabled.", "") if a[0] == "mdutil" else orig(a)
        with pytest.raises(core.Paused, match="SPOTLIGHT"):
            e2.check_order({**cfg, "budget": {**cfg["budget"], "free_space_min_bytes": 1}}, deps, d, d, "E1 before", needed_bytes=1, ledger=None, file_exists=False)


def test_drive_health_warning_is_paused() -> None:
    cfg = small_cfg()
    with T.scratch("r1_health") as d:
        clk, io, deps = machine()
        with pytest.raises(core.Paused, match="DRIVE HEALTH"):
            r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder([]), ec3=lambda label: {"health_ok": False, "smart_status": "Failing"})


def test_store_that_cannot_be_held_cold_ends_r1_with_the_registered_reason() -> None:
    cfg = small_cfg()
    with T.scratch("r1_cold") as d:
        poll = {layout.TILE_PAGES * 3 + 5}  # one page of tile 3 is 'cached' and stays so across the one rebuild
        clk, io, deps = machine(cached_pages=poll)
        calls: list[str] = []
        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder(calls))
        assert calls == ["control.bin", "rehearsal.bin", "rehearsal.bin"]  # one rebuild, no third build
        assert rec["not_evaluable_reasons"] == ["STORE CANNOT BE HELD COLD"] and rec["outcome"] == "ENGINEERING NOT EVALUABLE (STORE CANNOT BE HELD COLD)" and not rec["passed"]
        cold = core.read_record(d / "run" / "r1" / "steps" / "cold.json")
        assert cold["rebuilt"] and cold["first"]["verdict"] == "PAUSED — STORE NOT COLD" and not cold["second"]["cold"]
        assert not (d / "run" / "r1" / "steps" / "band.json").exists()  # nothing is read after a store that is not cold


def test_a_store_made_cold_by_the_one_rebuild_continues() -> None:
    cfg = small_cfg()
    with T.scratch("r1_cold2") as d:
        poll = {layout.TILE_PAGES * 3 + 5}
        clk, io, deps = machine(cached_pages=poll)
        calls: list[str] = []

        def build(path: Path, tiles: int, seed: int, ledger: device.WriteLedger, counter: Any, **kw: Any) -> dict[str, Any]:
            if calls.count("rehearsal.bin") == 1:
                io.cache.clear()  # the rebuild evicts what was cached
            return touching_builder(calls)(path, tiles, seed, ledger, counter, **kw)

        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=build)
        assert calls.count("rehearsal.bin") == 2 and rec["passed"] and rec["cold"] == "COLD"
        assert core.read_record(d / "run" / "r1" / "steps" / "cold.json")["rebuilt"]


def test_band_failures_map_to_the_reasons_of_the_adr() -> None:
    cfg = small_cfg()
    with T.scratch("r1_band") as d:
        path = d / "x.bin"
        path.write_bytes(b"")
        # below prediction but not zero: CACHE NOT DEFEATED
        clk, io, deps = machine(cached_pages={layout.TILE_PAGES * 8 + 1})
        assert r1.band_passes(path, cfg, deps)["reasons"] == ["CACHE NOT DEFEATED"]
        # zero bytes counted: NO PHYSICAL COUNTER
        clk, io, deps = machine()
        deps.counter = type("C", (), {"read": lambda self: device.IOSnapshot(0, 0, 0)})()  # type: ignore[assignment]
        assert r1.band_passes(path, cfg, deps)["reasons"] == ["NO PHYSICAL COUNTER"]
        # above prediction: the counter is not exact: NO PHYSICAL COUNTER
        clk, io, deps = machine()
        io.extra = 1
        assert r1.band_passes(path, cfg, deps)["reasons"] == ["NO PHYSICAL COUNTER"]
        # data that differs from the regenerated pages is an engineering stop, not a reason
        clk, io, deps = machine()
        req = r1.band_requests(cfg)[(1, 1)][0]
        io.corrupt = {req.offset}
        with pytest.raises(core.EngineeringStop, match="DATA MISMATCH"):
            r1.band_passes(path, cfg, deps)


def test_positive_control_failure_is_reported_with_its_reason() -> None:
    cfg = small_cfg()
    with T.scratch("r1_pos") as d:
        clk, io, deps = machine(opener_always_uncached=True)  # a 'cached' pass that never caches: the second pass counts bytes
        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder([]))
        assert "POSITIVE CONTROL FAILED" in rec["not_evaluable_reasons"] and rec["outcome"] == "ENGINEERING NOT EVALUABLE (POSITIVE CONTROL FAILED)" and not rec["passed"]
        ctrl = core.read_record(d / "run" / "r1" / "steps" / "control.json")
        assert not ctrl["controls"]["positive_control_passed"] and ctrl["harness"]["1"]["status"] == "HARNESS FIGURE NOT MEASURED"  # repeated once, then not measured
        assert len(ctrl["harness"]["1"]["attempts"]) == 2


def test_unreadable_counter_ends_r1_with_no_physical_counter() -> None:
    cfg = small_cfg()
    with T.scratch("r1_nocounter") as d:
        clk, io, deps = machine()

        class Broken:
            def read(self) -> device.IOSnapshot:
                raise core.EngineeringStop("NO PHYSICAL COUNTER", "proc_pid_rusage returned 1")

        deps.counter = Broken()
        calls: list[str] = []
        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder(calls))
        assert rec["not_evaluable_reasons"] == ["NO PHYSICAL COUNTER"] and not rec["passed"] and calls == [] and clk.t == 0.0  # nothing was built or waited for


def test_amplification_not_shown_is_an_engineering_stop_not_a_label(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = small_cfg()
    monkeypatch.setattr(r1, "amplification_check", lambda path, deps: {"requests": 256, "request_bytes": 4096, "counter_bytes": 256 * 4096, "logical_bytes": 256 * 4096, "amplification": 1.0, "shown": False})
    with T.scratch("r1_amp") as d:
        clk, io, deps = machine()  # the 4 KiB requests are counted as 4 KiB: no amplification is shown
        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=touching_builder([]))
        assert "4 KiB amplification" in rec["checks_not_shown"] and not rec["passed"] and rec["outcome"].startswith("ENGINEERING STOP (CHECK NOT SHOWN")


def test_reason_mapping_function() -> None:
    assert r1.reason_of("OK", 5) is None and r1.reason_of("STORE PAGES CACHED", 0) == "NO PHYSICAL COUNTER" and r1.reason_of("STORE PAGES CACHED", 5) == "CACHE NOT DEFEATED" and r1.reason_of("COUNTER CONTAMINATED", 9) == "NO PHYSICAL COUNTER"
