# ruff: noqa: E501
"""P10IS5 machine-record tests (ADR-0028 sections 3.1 EC3, 6 hygiene, 8 quiet rule): parsers on canned output (strings as this machine printed them on 2026-11-18), the quiet rule condition by condition, the idle
baseline (discarded and retaken when another study's process is alive; PAUSED after the 6-hour deadline), EC3 NOT READABLE, hygiene NOT CHECKABLE. Nothing here runs a system tool: ``run`` is a fake. Self-check only."""

import plistlib
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import core, system  # noqa: E402

CFG = core.load_config()
BATT = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=36307043)\t100%; charged; 0:00 remaining present: true\n"
PMSET = " powermode            0\n lowpowermode         0\n"
THERM = "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\n"
HID = '    | | |   "HIDIdleTime" = 13387188164083\n'
PS = "  PID COMMAND\n    1 /sbin/launchd\n  101 /Applications/Claude.app/Contents/MacOS/Claude\n  202 /x/.venv/bin/python -m pytest tests/test_other.py\n  303 uv run python -m studies.p10s1.stages registered a1\n  404 /usr/bin/caffeinate -i uv run python -m studies.p10is5.stages r1\n  505 /x/.venv/bin/python -m studies.p10is5.stages r1\n"
PPID = "  PID  PPID\n    1     0\n  404     1\n  505   404\n  202     1\n  303     1\n  606   505\n"


def plist_driver(read: int, write: int, rops: int, wops: int) -> bytes:
    return plistlib.dumps([{"Statistics": {"Bytes (Read)": 0, "Bytes (Write)": 0, "Operations (Read)": 0, "Operations (Write)": 0}, "IORegistryEntryChildren": [{"BSD Name": "disk9"}]}, {"Statistics": {"Bytes (Read)": read, "Bytes (Write)": write, "Operations (Read)": rops, "Operations (Write)": wops}, "IORegistryEntryChildren": [{"BSD Name": "disk0", "IORegistryEntryChildren": [{"BSD Name": "disk0s1"}]}]}])


def test_parsers_on_canned_output() -> None:
    assert system.parse_loadavg("{ 4.28 6.18 5.11 }") == (4.28, 6.18, 5.11)
    assert system.parse_boottime("{ sec = 1794270220, usec = 98602 } Mon Nov  9 19:23:40 2026") == 1794270220
    assert system.parse_hid_idle_seconds(HID) == pytest.approx(13387.188164083)
    assert system.parse_on_ac(BATT) is True and system.parse_on_ac("Now drawing from 'Battery Power'") is False and system.parse_on_ac("") is None
    assert system.parse_low_power(PMSET) is False and system.parse_low_power(" lowpowermode 1\n") is True and system.parse_low_power(" powermode 0\n") is False
    assert system.parse_thermal_warning(THERM) is False and system.parse_thermal_warning("CPU_Speed_Limit = 70\n") is True and system.parse_thermal_warning("") is None
    df = system.parse_df_k("Filesystem 1024-blocks Used Available Capacity iused ifree %iused Mounted on\n/dev/disk3s5 1948404040 1209619608 710904944 63% 9543023 7109049440 0% /System/Volumes/Data\n")
    assert df == {"device": "/dev/disk3s5", "total_bytes": 1948404040 * 1024, "used_bytes": 1209619608 * 1024, "free_bytes": 710904944 * 1024}
    assert system.parse_smart_status("   SMART Status:              Verified\n") == "Verified"
    assert system.parse_driver_stats(plist_driver(10, 20, 3, 4)) == {"read_bytes": 10, "write_bytes": 20, "read_ops": 3, "write_ops": 4}  # the driver that holds disk0, not the first one
    assert system.parse_driver_stats(plist_driver(1, 1, 1, 1), "disk7") is None
    vol = plistlib.dumps([{"BSD Name": "disk3s5", "Statistics": {"Bytes read from block device": 5, "Bytes written to block device": 6, "Bytes read by user": 7}}])
    assert system.parse_volume_stats(vol, "disk3s5") == {"read_blockdev": 5, "written_blockdev": 6, "read_by_user": 7}


def test_other_study_processes_excludes_the_stage_own_family_and_matches_the_three_markers() -> None:
    fam = system.process_family(system.parse_ppids(PPID), 505)
    assert fam == {505, 404, 606}  # itself, its launcher and its child; not launchd and not the other processes (202, 303)
    others = system.other_study_processes(system.parse_ps(PS), fam, CFG["quiet"]["process_markers"])
    assert sorted(p for p, _ in others) == [202, 303]  # pytest and another study's stage; Claude and launchd match no marker
    assert system.other_study_processes(system.parse_ps(PS), {505, 404, 202, 303}, CFG["quiet"]["process_markers"]) == []
    assert system.other_study_processes([(9, "/Users/x/ArborLM/.venv/bin/python script.py")], set(), CFG["quiet"]["process_markers"]) != []  # 'arborlm' is matched case-insensitively (the conservative reading)


def thresholds() -> dict[str, float]:
    return {"load_ceiling": 2.5, "read_bytes": 1000.0, "write_bytes": 2000.0, "read_ops": 10.0, "write_ops": 20.0}


def good_readings() -> dict[str, Any]:
    return {"load": 2.0, "other_processes": [], "hid_idle_seconds": 700.0, "power": {"on_ac": True, "low_power": False, "thermal_warning": False}, "activity": {"read_bytes": 10.0, "write_bytes": 10.0, "read_ops": 1.0, "write_ops": 1.0}, "boot_time": 5}


def test_quiet_rule_each_condition_alone() -> None:
    assert system.evaluate_quiet(good_readings(), thresholds(), 600.0, 5)["ok"]
    cases: dict[str, Any] = {
        "load": {"load": 2.5001}, "no_other_study_process": {"other_processes": [[1, "pytest"]]}, "hid_idle": {"hid_idle_seconds": 599.0}, "ac_power": {"power": {"on_ac": False, "low_power": False, "thermal_warning": False}},
        "power_mode_not_low": {"power": {"on_ac": True, "low_power": True, "thermal_warning": False}}, "no_thermal_warning": {"power": {"on_ac": True, "low_power": False, "thermal_warning": True}},
        "disk_activity": {"activity": {"read_bytes": 10.0, "write_bytes": 2001.0, "read_ops": 1.0, "write_ops": 1.0}}, "boot_time_unchanged": {"boot_time": 6},
    }  # fmt: skip
    for cond, change in cases.items():
        r = system.evaluate_quiet({**good_readings(), **change}, thresholds(), 600.0, 5)
        assert not r["ok"] and r["failed"] == [cond], cond
    assert system.evaluate_quiet({**good_readings(), "load": 2.5}, thresholds(), 600.0, 5)["ok"]  # at the ceiling is quiet ("at most")
    assert not system.evaluate_quiet({**good_readings(), "hid_idle_seconds": None}, thresholds(), 600.0, 5)["ok"]  # unreadable fails the rule


def test_quiet_thresholds_are_the_idle_p95_plus_half() -> None:
    cfg = {**CFG, "fixed_after_r1_and_m": {**CFG["fixed_after_r1_and_m"], "load_p95": 2.13, "read_bytes_per_s_p95": 7.0}}
    t = system.quiet_thresholds(cfg)
    assert t["load_ceiling"] == pytest.approx(2.63) and t["read_bytes"] == 7.0


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


def test_wait_for_quiet_has_a_deadline() -> None:
    clk = Clock()
    n = {"n": 0}

    def read() -> dict[str, Any]:
        n["n"] += 1
        return {"ok": False, "failed": ["load"]}

    rec, hist = system.wait_for_quiet(read, retry_interval=600.0, deadline=21600.0, sleep=clk.sleep, clock=clk)
    assert rec is None and len(hist) == 37 and clk.t == 21600.0  # readings at 0, 600, ..., 21,600 s: at most six hours
    clk = Clock()
    seq = iter([False, False, True])
    rec, hist = system.wait_for_quiet(lambda: {"ok": next(seq), "failed": []}, retry_interval=600.0, deadline=21600.0, sleep=clk.sleep, clock=clk)
    assert rec is not None and len(hist) == 3 and clk.t == 1200.0


class FakeSystem:
    """Canned ``run`` and ``run_b``; the disk counters advance by fixed rates per second of fake time; ``other_at`` lists (time, True) windows in which another study's process is alive."""

    def __init__(self, clk: Clock, other_windows: Sequence[tuple[float, float]] = (), load: float = 2.0) -> None:
        self.clk, self.other, self.load = clk, other_windows, load
        self.pid_rows = PS

    def run(self, argv: Sequence[str]) -> tuple[int, str, str]:
        a = list(argv)
        if a[:2] == ["sysctl", "-n"] and a[2] == "vm.loadavg":
            return 0, f"{{ {self.load + (self.clk.t % 7) / 100:.2f} 1.0 1.0 }}", ""
        if a[:2] == ["sysctl", "-n"]:
            return 0, "{ sec = 5, usec = 1 }", ""
        if a[0] == "ps" and "pid,ppid" in a:
            return 0, "  PID  PPID\n  505   404\n  404     1\n", ""
        if a[0] == "ps":
            busy = any(lo <= self.clk.t < hi for lo, hi in self.other)
            return 0, "  PID COMMAND\n    1 /sbin/launchd\n  404 caffeinate\n" + ("  900 python -m pytest\n" if busy else ""), ""
        if a[:2] == ["pmset", "-g"] and len(a) == 3 and a[2] == "batt":
            return 0, BATT, ""
        if a[:2] == ["pmset", "-g"] and len(a) == 3:
            return 0, THERM, ""
        if a[:2] == ["pmset", "-g"]:
            return 0, PMSET, ""
        if a[0] == "ioreg":
            return 0, HID, ""
        return 127, "", "unknown"

    def run_b(self, argv: Sequence[str]) -> tuple[int, bytes]:
        t = int(self.clk.t)
        return 0, plist_driver(1000 * t, 2000 * t, 10 * t, 20 * t)


def test_idle_window_is_discarded_when_another_study_is_alive_and_retaken_from_the_start() -> None:
    clk = Clock()
    fs = FakeSystem(clk, other_windows=[(95.0, 105.0)])  # another study's process is alive during the 10th sample of the first window
    w = system.take_idle_window(fs.run, fs.run_b, CFG, clk.sleep, clk)
    assert w["discarded"] and w["failed_sample"] in (9, 10) and not w["samples"][-1]["ok"]
    clk2 = Clock()
    fs2 = FakeSystem(clk2, other_windows=[(95.0, 105.0)])
    base = system.idle_baseline(fs2.run, fs2.run_b, CFG, clk2.sleep, clk2)
    assert base["status"] == "MEASURED" and base["attempts"][0]["discarded"] and not base["attempts"][-1]["discarded"] and len(base["attempts"]) == 2
    fig = base["figures"]
    assert fig["samples"] == 60 and fig["read_bytes_per_s_p95"] == pytest.approx(1000.0) and fig["write_ops_per_s_p95"] == pytest.approx(20.0)
    assert fig["load_ceiling"] == pytest.approx(fig["load_p95"] + 0.5)
    assert clk2.t >= 600 + 600  # a failed window, the 10-minute retry wait, then a whole new window


def test_idle_baseline_is_paused_after_six_hours() -> None:
    clk = Clock()
    fs = FakeSystem(clk, other_windows=[(0.0, 1e9)])
    base = system.idle_baseline(fs.run, fs.run_b, CFG, clk.sleep, clk)
    assert base["status"] == "PAUSED — NO IDLE BASELINE" and len(base["attempts"]) >= 30 and clk.t <= 21600 + 600 + 200


def test_idle_figures_use_nearest_rank_95th() -> None:
    window = {"loads": [float(i) for i in range(1, 61)], "rate_rows": [{"read_bytes": float(i), "write_bytes": 0.0, "read_ops": 0.0, "write_ops": 0.0} for i in range(1, 61)]}
    fig = system.idle_figures(window, CFG)
    assert fig["load_p95"] == 57.0 and fig["read_bytes_per_s_p95"] == 57.0 and fig["load_ceiling"] == 57.5  # rank ceil(0.95 x 60) = 57


def test_ec3_prints_wear_counters_not_readable_and_pauses_on_bad_smart() -> None:
    def run(argv: Sequence[str]) -> tuple[int, str, str]:
        if argv[0] == "diskutil":
            return 0, "   SMART Status:              Verified\n", ""
        return 0, "Filesystem 1024-blocks Used Available Capacity iused ifree %iused Mounted on\n/dev/disk3s5 100 50 50 50% 1 1 0% /\n", ""

    rec = system.ec3_record(run, lambda a: (0, plist_driver(1, 2, 3, 4)), Path("/"), "test")
    assert rec["health_ok"] and rec["lifetime_bytes_written"] == rec["percentage_used"] == rec["temperature"] == "NOT READABLE"
    assert rec["driver_since_boot"]["write_bytes"] == 2 and rec["free"]["free_bytes"] == 50 * 1024
    bad = system.ec3_record(lambda a: (0, "   SMART Status: Failing\n" if a[0] == "diskutil" else "", ""), lambda a: (1, b""), Path("/"), "test")
    assert not bad["health_ok"] and bad["driver_since_boot"] == "NOT READABLE"


def test_hygiene_records_each_check_and_its_consequence() -> None:
    def run(argv: Sequence[str]) -> tuple[int, str, str]:
        a = list(argv)
        if a[:2] == ["tmutil", "listlocalsnapshots"]:
            return 0, "Snapshots for disk /:\ncom.apple.TimeMachine.2026-11-18-120000.local\n", ""
        if a[:2] == ["tmutil", "destinationinfo"]:
            return 1, "", "tmutil: No destinations configured."
        if a[:2] == ["tmutil", "isexcluded"]:
            return 0, "[Included] /x.noindex", ""
        if a[:2] == ["tmutil", "addexclusion"]:
            return 1, "", "tmutil: addexclusion: Operation not permitted"
        if a[0] == "diskutil":
            return 1, "", "requires administrator privileges"
        if a[0] == "mdutil":
            return 0, "/x.noindex:\n\tIndexing enabled.", ""
        return 0, "", ""

    h = system.hygiene_record(run, Path("/x.noindex"), file_exists=True, add_exclusion=True)
    assert h["snapshot_present"] and h["store_retained_by_snapshot"] and h["spotlight_indexes_directory"] and h["blocks_e1"] and h["exclusion_not_set"]
    assert h["apfs_snapshots"]["status"] == "NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS" and h["time_machine_add_exclusion"]["status"] == "NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS"
    assert h["time_machine_destinations"]["status"] == "NOT READABLE" and h["noindex_suffix"]
    clean = system.hygiene_record(lambda a: (0, "Indexing disabled." if a[0] == "mdutil" else "", ""), Path("/x.noindex"), file_exists=False)
    assert not clean["blocks_e1"] and not clean["store_retained_by_snapshot"]
