# ruff: noqa: E501
"""P10IS5 stage R1, the method rehearsal (ADR-0028 sections 7, 8, 5.4; ruling 11): runs ALONE, first takes the idle baseline, then builds the control file and the rehearsal file, runs the cold check, the counter-exactness
passes on the rehearsal file's reserved band, the control-file checks, the harness figure h(k), and last the uncached re-reads at working sets of 32, 64 and 128 MiB.

Failures map to the ADR's NOT EVALUABLE reasons only where the ADR names them: a counter that is unreadable, zero on an uncached read, or above prediction is NO PHYSICAL COUNTER; a count below prediction on an uncached
read is CACHE NOT DEFEATED; a second cached pass that counts bytes is POSITIVE CONTROL FAILED; a store that cannot be held cold is STORE CANNOT BE HELD COLD. A check the ADR requires but names no reason for (the 4 KiB
amplification, the harness figure) that is not shown is recorded as CHECK NOT SHOWN and R1 is an ENGINEERING STOP, never a label. Every step is written to ``<run>/r1/steps/`` and finished steps are not run again.
"""

import hashlib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import read_json

from . import blocks, core, device, harness, layout, system
from .core import EngineeringStop, Paused
from .layout import PAGE, TILE_BYTES, TILE_PAGES, Request

STEPS = ("idle", "ec3_before", "hygiene", "build", "cold", "band", "control", "rereads", "ec3_after")
ZERO_RESULT = "NO PHYSICAL COUNTER"
READING = (
    "This study's reading of ADR-0028 section 7 (the lead's ruling: it stands): a counter that reads zero on an uncached read, or above 16,384 x pages, is NO PHYSICAL COUNTER; a short non-zero count is CACHE NOT DEFEATED; "
    "a second cached pass that counts bytes is POSITIVE CONTROL FAILED; a store that cannot be held cold is STORE CANNOT BE HELD COLD; a 4 KiB amplification or a harness figure that cannot be shown is ENGINEERING STOP (CHECK NOT SHOWN). "
    "Each is an engineering outcome, never a scientific label."
)


def step_path(run_dir: Path, name: str) -> Path:
    return run_dir / "r1" / "steps" / f"{name}.json"


def load_step(run_dir: Path, name: str) -> dict[str, Any] | None:
    p = step_path(run_dir, name)
    return read_json(p) if p.is_file() else None


def save_step(run_dir: Path, name: str, rec: Mapping[str, Any]) -> dict[str, Any]:
    core.write_record(step_path(run_dir, name), {**core.envelope("r1"), "step": name, **rec}, overwrite=True)
    return dict(rec)


def reason_of(status: str, counter_bytes: int) -> str | None:
    """The ADR's reason for an uncached pass whose counter rule failed: zero bytes counted, or above prediction, is NO PHYSICAL COUNTER (the counter is not a faithful measure); a short count is CACHE NOT DEFEATED."""
    if status == "OK":
        return None
    if status == core.STORE_PAGES_CACHED:
        return ZERO_RESULT if counter_bytes == 0 else "CACHE NOT DEFEATED"
    return ZERO_RESULT


# --- passes on the band --------------------------------------------------------------------------------------------------------------------------
def band_cells(cfg: Mapping[str, Any]) -> list[tuple[int, int]]:
    """The eight counter cells: depth 1 and depth 32 for each of the four request sizes, k-major; run in the order of ``torch.randperm(8)`` seeded by the R1 pass-order seed."""
    return [(k, s) for k in map(int, cfg["cells"]["r1_depths"]) for s in map(int, cfg["cells"]["sizes"])]


def band_requests(cfg: Mapping[str, Any]) -> dict[tuple[int, int], list[Request]]:
    """The rehearsal n(s) at k = 1 and k = 32 over tiles 896 to 951, dealt in order (k = 1 first), in the R1 request-order seed's order (ruling 11)."""
    geo = core.rehearsal_geometry(cfg)
    pos = int(cfg["device"]["band_start_tile"])
    out: dict[tuple[int, int], list[Request]] = {}
    for k, s in band_cells(cfg):
        count = geo.tiles_of[s]
        tiles = list(range(pos, pos + count))
        pos += count
        out[(k, s)] = layout.pass_requests(tiles, k, s, geo.n_of[s], int(cfg["seeds"]["r1_request_order"]))
    if pos > int(cfg["device"]["band_start_tile"]) + 56 or pos > int(cfg["device"]["rehearsal_tiles"]):
        raise AssertionError("the band passes need more than tiles 896 to 951")
    return out


def run_checked_pass(path: Path, reqs: Sequence[Request], k: int, deps: blocks.Deps, contents_seed: int, *, uncached: bool = True, cache: dict[int, list[str]] | None = None) -> dict[str, Any]:
    res = harness.run_pass(path, reqs, k, deps.counter, uncached=uncached, pread=deps.pread, cross_check=deps.cross_check, opener=deps.opener)
    pages = sum(r.pages for r in reqs)
    status = device.counter_rule(res.counter_bytes, pages, res.written_bytes)
    ok, bad = harness.parity_ok(reqs, res.data, layout.expected_page_hashes(contents_seed, reqs, cache)) if uncached else (True, 0)
    lat = res.latencies_ns
    return {
        "k": k, "requests": len(reqs), "pages": pages, "predicted_bytes": PAGE * pages, "counter_bytes": res.counter_bytes, "written_bytes": res.written_bytes, "counter_status": status, "parity_ok": ok, "parity_bad_pages": bad,
        "median_ns": core.median(lat), "p90_ns": core.nearest_rank(lat, 0.9), "max_ns": max(lat), "wall_ns": res.wall_ns, "pages_per_second": res.pages_per_second, "max_in_flight": res.max_in_flight(), "switch_interval": res.switch_interval,
        "cross_start": res.cross_start, "cross_end": res.cross_end,
    }  # fmt: skip


def band_passes(path: Path, cfg: Mapping[str, Any], deps: blocks.Deps) -> dict[str, Any]:
    """Counter exactness on the reserved band: each cell's pass uncached, then repeated uncached back to back. A data mismatch is an ENGINEERING STOP (DATA MISMATCH)."""
    seed = int(cfg["seeds"]["r1_rehearsal_file_contents"])
    cells = band_cells(cfg)
    reqs = band_requests(cfg)
    order = torch.randperm(len(cells), generator=torch.Generator().manual_seed(int(cfg["seeds"]["r1_pass_order"]))).tolist()
    cache: dict[int, list[str]] = {}
    rows = []
    for idx in order:
        k, s = cells[int(idx)]
        for which in ("first", "repeat"):
            rec = run_checked_pass(path, reqs[(k, s)], k, deps, seed, cache=cache)
            if not rec["parity_ok"]:
                raise EngineeringStop("DATA MISMATCH", f"R1 band pass k={k} s={s} {which}: {rec['parity_bad_pages']} page(s) differ")
            rows.append({"cell": [k, s], "which": which, **rec})
    reasons = sorted({r for row in rows if (r := reason_of(row["counter_status"], row["counter_bytes"]))}, key=core.REASONS_ORDER.index)
    return {"passes": rows, "all_exact": not reasons, "reasons": reasons, "k32_max_in_flight": max((r["max_in_flight"] for r in rows if r["k"] == 32), default=0), "k1_max_in_flight": max((r["max_in_flight"] for r in rows if r["k"] == 1), default=0)}


# --- control-file checks -------------------------------------------------------------------------------------------------------------------------
def tile_requests(tiles: Sequence[int]) -> list[Request]:
    return [Request(j, 0, t, 0, t * TILE_BYTES, TILE_BYTES) for j, t in enumerate(tiles)]


def amplification_check(path: Path, deps: blocks.Deps, first_tile: int = 16, pages: int = 256) -> dict[str, Any]:
    """The 4 KiB amplification (probe 1E): a 4 KiB uncached request at the start of a fresh 16 KiB page counts a whole page (the per-pass check is 16,384 x pages)."""
    reqs = [Request(j, 0, (first_tile * TILE_PAGES + j) // TILE_PAGES, j % TILE_PAGES, (first_tile * TILE_PAGES + j) * PAGE, 4096) for j in range(pages)]
    res = harness.run_pass(path, reqs, 1, deps.counter, pread=deps.pread, opener=deps.opener)
    shown = res.counter_bytes == pages * PAGE
    return {"requests": pages, "request_bytes": 4096, "counter_bytes": res.counter_bytes, "logical_bytes": pages * 4096, "amplification": res.counter_bytes / (pages * 4096), "shown": shown}


def positive_and_pollution(path: Path, deps: blocks.Deps, first_tile: int = 8, tiles: int = 8) -> dict[str, Any]:
    """The positive control (a second cached pass counts 0 bytes) and the pollution control (probe 1D: an uncached read of pages already cached counts less than a whole read: ``F_NOCACHE`` does not bypass pages already
    cached). Run only on R1's control file."""
    reqs = tile_requests(range(first_tile, first_tile + tiles))
    first = harness.run_pass(path, reqs, 1, deps.counter, uncached=False, pread=deps.pread, opener=deps.opener)
    second = harness.run_pass(path, reqs, 1, deps.counter, uncached=False, pread=deps.pread, opener=deps.opener)
    polluted = harness.run_pass(path, reqs, 1, deps.counter, uncached=True, pread=deps.pread, opener=deps.opener)
    return {
        "cached_first_counter_bytes": first.counter_bytes, "cached_second_counter_bytes": second.counter_bytes, "positive_control_passed": second.counter_bytes == 0, "predicted_bytes": tiles * TILE_BYTES,
        "pollution_nocache_after_cached_counter_bytes": polluted.counter_bytes, "nocache_bypassed_cached_pages": polluted.counter_bytes >= tiles * TILE_BYTES,
    }  # fmt: skip


def harness_requests(control_seed: int, k: int, count: int, tiles: int) -> list[Request]:
    """The first ``count`` of the ``tiles`` x 64 single-page requests of the control file's tiles 0 to ``tiles - 1`` in a seeded order (derived from the control file's seed: no new seed); request j goes to thread j mod k."""
    pages = tiles * TILE_PAGES
    order = torch.randperm(pages, generator=torch.Generator().manual_seed(core.sha_seed(f"p10is5|harness|{control_seed}|{k}"))).tolist()[:count]
    return [Request(j, j % k, int(p) // TILE_PAGES, int(p) % TILE_PAGES, int(p) * PAGE, PAGE) for j, p in enumerate(order)]


def harness_figure(path: Path, cfg: Mapping[str, Any], deps: blocks.Deps, control_tiles: int | None = None) -> dict[str, Any]:
    """Section 5.4: the threaded loop at each depth on CACHED pages of the control file (400 single-page requests; descriptors without ``F_NOCACHE``); the whole file is first read once, in 1 MiB requests, without
    ``F_NOCACHE``. The pass must count 0 bytes read, otherwise it is repeated once after a new warm-up and then recorded HARNESS FIGURE NOT MEASURED. h(k) is the pass's median latency."""
    t = cfg["thresholds"]
    ctiles = control_tiles if control_tiles is not None else int(cfg["device"]["control_tiles"])
    seed = int(cfg["seeds"]["r1_control_file_contents"])

    def warm() -> device.ScanResult:
        return device.uncached_scan(path, 0, ctiles * TILE_BYTES, deps.counter, pread=deps.pread, cached=True, opener=deps.opener)

    out: dict[str, Any] = {}
    warm()
    for k in map(int, t["harness_depths"]):
        attempts = []
        for attempt in (1, 2):
            reqs = harness_requests(seed, k, int(t["harness_requests"]), int(t["harness_tiles"]))
            res = harness.run_pass(path, reqs, k, deps.counter, uncached=False, pread=deps.pread, opener=deps.opener)
            attempts.append({"counter_bytes": res.counter_bytes})
            if res.counter_bytes == 0:
                lat = res.latencies_ns
                out[str(k)] = {"status": "MEASURED", "median_ns": core.median(lat), "p90_ns": core.nearest_rank(lat, 0.9), "requests": len(reqs), "attempts": attempts, "max_in_flight": res.max_in_flight()}
                break
            warm()
        else:
            out[str(k)] = {"status": core.HARNESS_NOT_MEASURED, "attempts": attempts}
    return out


def harness_by_depth(fig: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(k): dict(v) for k, v in fig.items()}


# --- working-set re-reads (descriptive) ------------------------------------------------------------------------------------------------------------
def rereads(path: Path, cfg: Mapping[str, Any], deps: blocks.Deps) -> dict[str, Any]:
    """Uncached re-reads back to back at working sets of 32, 64 and 128 MiB (tiles from the band's start, in the order of the re-read seed): descriptive, no label. Run last."""
    start = int(cfg["device"]["band_start_tile"])
    rows = []
    for w in map(int, cfg["cells"]["r1_reread_working_set_tiles"]):
        order = torch.randperm(w, generator=torch.Generator().manual_seed(core.sha_seed(f"p10is5|reread|{cfg['seeds']['r1_reread_offsets']}|{w}"))).tolist()
        reqs = tile_requests([start + int(i) for i in order])
        passes = []
        for which in ("first", "second"):
            res = harness.run_pass(path, reqs, 1, deps.counter, pread=deps.pread, cross_check=deps.cross_check, opener=deps.opener)
            passes.append({"which": which, "counter_bytes": res.counter_bytes, "predicted_bytes": w * TILE_BYTES, "wall_ns": res.wall_ns, "bytes_per_second": w * TILE_BYTES / (res.wall_ns / 1e9), "median_ns": core.median(res.latencies_ns), "counter_status": device.counter_rule(res.counter_bytes, w * TILE_PAGES, res.written_bytes)})
        rows.append({"working_set_tiles": w, "mib": w, "passes": passes})
    return {"working_sets": rows, "descriptive": True}


# --- the stage ---------------------------------------------------------------------------------------------------------------------------------
def run_r1(
    cfg: Mapping[str, Any],
    data_dir: Path,
    run_dir: Path,
    deps: blocks.Deps,
    ledger: device.WriteLedger,
    *,
    now: Callable[[], float],
    builder: Callable[..., dict[str, Any]] = device.build_file,
    hygiene: Callable[[bool], dict[str, Any]] | None = None,
    ec3: Callable[[str], dict[str, Any]] | None = None,
    tiles: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """R1. The idle window first (taken only when no other study's process is alive), then EC3 and hygiene, the builds (control file, rehearsal file), the 10-minute wait and the cold check (one rebuild, then STORE
    CANNOT BE HELD COLD), the band passes, the control-file checks, the harness figure and the re-reads. Resumable by step. Raises ``Paused`` for the registered PAUSED outcomes."""
    d, b, q = cfg["device"], cfg["budget"], cfg["quiet"]
    n_ctrl = int((tiles or {}).get("control", d["control_tiles"]))
    n_reh = int((tiles or {}).get("rehearsal", d["rehearsal_tiles"]))
    control, rehearsal = data_dir / "control.bin", data_dir / "rehearsal.bin"
    seeds = cfg["seeds"]
    chunk = int(d["build_chunk_bytes"])
    reasons: list[str] = []

    # 0. the counter must be readable at all (otherwise nothing below can be shown): NO PHYSICAL COUNTER, recorded and R1 ends
    try:
        deps.counter.read()
    except EngineeringStop as e:
        if e.cause != "NO PHYSICAL COUNTER":
            raise
        rec0 = {**core.envelope("r1"), "step": "final", "not_evaluable_reasons": ["NO PHYSICAL COUNTER"], "checks_not_shown": [], "passed": False, "outcome": f"{core.ENG_NOT_EVALUABLE} (NO PHYSICAL COUNTER)", "detail": str(e), "idle_figures": None}
        core.write_record(run_dir / "r1" / "r1.json", rec0, overwrite=True)
        return rec0

    # 1. the idle baseline, taken first
    st = load_step(run_dir, "idle")
    if st is None:
        idle = system.idle_baseline(deps.run, deps.run_b, cfg, deps.snooze, deps.clock, lambda ev: core.append_jsonl(run_dir / "r1" / "idle_attempts.jsonl", ev))
        if idle["status"] != "MEASURED":
            save_step(run_dir, "idle_paused", idle)
            raise Paused("PAUSED — NO IDLE BASELINE", f"{len(idle['attempts'])} windows discarded over {q['retry_deadline_seconds']} s; the readings are recorded; R1 is rescheduled")
        st = save_step(run_dir, "idle", idle)
    # 2. EC3 and hygiene
    if ec3 and load_step(run_dir, "ec3_before") is None:
        rec = ec3("R1 before")
        save_step(run_dir, "ec3_before", rec)
        if not rec["health_ok"]:
            raise Paused("PAUSED — DRIVE HEALTH", f"SMART status {rec['smart_status']}")
    if hygiene and load_step(run_dir, "hygiene") is None:
        h = hygiene(False)
        save_step(run_dir, "hygiene", h)
        # Spotlight indexing of the directory is RECORDED here; it pauses the study before E1 (section 6), not R1.
    # 3. builds (the cap is checked by the ledger before every chunk; free space before the stage)
    bd = load_step(run_dir, "build")
    if bd is None:
        device.require_free_space(data_dir, int(b["free_space_min_bytes"]))
        rep_c = builder(control, n_ctrl, int(seeds["r1_control_file_contents"]), ledger, deps.counter, chunk_bytes=chunk, pread=deps.pread, min_free=int(b["free_space_min_bytes"]))
        rep_r = builder(rehearsal, n_reh, int(seeds["r1_rehearsal_file_contents"]), ledger, deps.counter, chunk_bytes=chunk, pread=deps.pread, min_free=int(b["free_space_min_bytes"]))
        bd = save_step(run_dir, "build", {"control": rep_c, "rehearsal": rep_r, "built_at": now(), "ledger_bytes": ledger.total()})
    # 4. the 10-minute wait and the cold check (one rebuild within the cap, then STORE CANNOT BE HELD COLD)
    cold = load_step(run_dir, "cold")
    if cold is None:
        wait_left = max(0.0, float(bd["built_at"]) + float(q["cold_wait_seconds"]) - now())
        deps.snooze(wait_left)

        def rebuild() -> None:
            device.guard_rebuild(ledger, rehearsal.name, n_reh * layout.TILE_BYTES, int(b["max_builds_per_file"]))  # the whole file must fit under the cap and the file is built at most twice: BEFORE it is deleted
            device.delete_built_file(rehearsal)
            builder(rehearsal, n_reh, int(seeds["r1_rehearsal_file_contents"]), ledger, deps.counter, chunk_bytes=chunk, pread=deps.pread, min_free=int(b["free_space_min_bytes"]), max_builds=int(b["max_builds_per_file"]))

        cold = save_step(run_dir, "cold", device.hold_cold(rehearsal, n_reh, int(seeds["r1_rehearsal_file_contents"]), deps.counter, rebuild, lambda: deps.snooze(float(q["cold_wait_seconds"])), pread=deps.pread))
    if cold["outcome"] != "COLD":
        reasons.append(core.STORE_CANNOT_BE_HELD_COLD)
    band = ctrl = None
    if not reasons:
        band = load_step(run_dir, "band") or save_step(run_dir, "band", band_passes(rehearsal, cfg, deps))
        reasons += list(band["reasons"])
        # control file: amplification and the controls first (fresh pages), then the harness figure (its warm-up caches the whole file)
        ctrl = load_step(run_dir, "control")
        if ctrl is None:
            amp = amplification_check(control, deps)
            pc = positive_and_pollution(control, deps)
            hf = harness_figure(control, cfg, deps, n_ctrl)
            ctrl = save_step(run_dir, "control", {"amplification": amp, "controls": pc, "harness": hf})
        if not ctrl["controls"]["positive_control_passed"]:
            reasons.append("POSITIVE CONTROL FAILED")
        load_step(run_dir, "rereads") or save_step(run_dir, "rereads", rereads(rehearsal, cfg, deps))
    if ec3 and load_step(run_dir, "ec3_after") is None:
        save_step(run_dir, "ec3_after", ec3("R1 after"))
    not_shown = []
    if not st["own_check_passed"]:
        not_shown.append("R1's own quiet check on its idle window")
    if ctrl is not None:
        if not ctrl["amplification"]["shown"]:
            not_shown.append("4 KiB amplification")
        not_shown += [f"harness figure at depth {k}" for k, v in ctrl["harness"].items() if v["status"] != "MEASURED"]
    reasons = [r for r in core.REASONS_ORDER if r in set(reasons)]
    figures = st["figures"]
    rec = {
        **core.envelope("r1"), "step": "final", "reading_of_adr_section_7": READING, "not_evaluable_reasons": reasons, "checks_not_shown": not_shown, "passed": not reasons and not not_shown, "idle_figures": figures, "idle_own_check_passed": st["own_check_passed"], "cold": cold["outcome"],
        "band_all_exact": None if band is None else band["all_exact"], "positive_control_passed": None if ctrl is None else ctrl["controls"]["positive_control_passed"], "harness": None if ctrl is None else ctrl["harness"],
        "ledger_bytes": ledger.total(), "outcome": "R1 PASSED" if not reasons and not not_shown else (f"{core.ENG_NOT_EVALUABLE} ({reasons[0]})" if reasons else f"ENGINEERING STOP (CHECK NOT SHOWN: {', '.join(not_shown)})"),
        "input_digest": hashlib.sha256(repr(sorted(figures.items())).encode()).hexdigest(),
    }  # fmt: skip
    core.write_record(run_dir / "r1" / "r1.json", rec, overwrite=True)
    return rec
