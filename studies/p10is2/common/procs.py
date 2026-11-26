# ruff: noqa: E501
"""Live processes of other studies and of this one (ADR-0025 sections 10, 20; ruling G7): used for the worker count, for the record of what shared the machine, and for the timing benchmark's quiet condition."""

import os

import psutil

STUDY_MODULES = ("studies.p10", "studies.p9", "studies.p8")


def is_keep_awake(cmd: list[str]) -> bool:
    """A keep-awake process (``caffeinate``). The launch scripts start ``caffeinate -i -w <the stage's own pid>``, which ends when the stage ends; it is the stage's own process FAMILY, never another process of a study, even
    if a keep-awake WRAPPER carries the stage's command line (the defect that held P10-I-S5's quiet check for 2.5 hours: the watcher was counted as a live study process)."""
    return bool(cmd) and os.path.basename(cmd[0]) == "caffeinate"


def other_studies_alive(own_pid: int | None = None) -> list[str]:
    """Command lines of live processes of ANOTHER study (``python -m studies.p10…``/``p9…``/``p8…``); this study's processes (``studies.p10is2``) and this process are excluded."""
    me = own_pid or os.getpid()
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = p.info["cmdline"] or []
        except psutil.Error:
            continue
        text = " ".join(cmd)
        if is_keep_awake(list(cmd)):
            continue
        if p.info["pid"] != me and "python" in text and any(m in text for m in STUDY_MODULES) and "studies.p10is2" not in text:
            out.append(text[:200])
    return out


def ancestor_pids(pid: int | None = None) -> set[int]:
    """The process ids of this process's ancestors: its parent (``uv run``, a shell), the shell's parent, a keep-awake watcher: its own launcher, which is family, not another process (audit R11, ruling 15)."""
    out: set[int] = set()
    try:
        p = psutil.Process(pid or os.getpid()).parent()
        while p is not None and p.pid not in out and p.pid > 1:
            out.add(p.pid)
            p = p.parent()
    except psutil.Error:
        pass
    return out


def own_study_alive() -> list[str]:
    """Command lines of live processes of THIS study other than this one and its ancestors (its own launcher counts as family)."""
    me = os.getpid()
    family = ancestor_pids()
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = list(p.info["cmdline"] or [])
        except psutil.Error:
            continue
        text = " ".join(cmd)
        if is_keep_awake(cmd):
            continue
        if p.info["pid"] != me and p.info["pid"] not in family and "python" in text and "studies.p10is2" in text:
            out.append(text[:200])
    return out


def rss_gib() -> float:
    """Resident set of this process and its children, in GiB."""
    p = psutil.Process()
    try:
        return float(sum(q.memory_info().rss for q in [p, *p.children(recursive=True)])) / 2**30
    except psutil.Error:
        return 0.0
