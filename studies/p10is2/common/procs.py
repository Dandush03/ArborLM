# ruff: noqa: E501
"""Live processes of other studies and of this one (ADR-0025 sections 10, 20; ruling G7): used for the worker count, for the record of what shared the machine, and for the timing benchmark's quiet condition."""

import os

import psutil

STUDY_MODULES = ("studies.p10", "studies.p9", "studies.p8")


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
        if p.info["pid"] != me and "python" in text and any(m in text for m in STUDY_MODULES) and "studies.p10is2" not in text:
            out.append(text[:200])
    return out


def own_study_alive() -> list[str]:
    """Command lines of live processes of THIS study other than this one."""
    me = os.getpid()
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            text = " ".join(p.info["cmdline"] or [])
        except psutil.Error:
            continue
        if p.info["pid"] != me and "python" in text and "studies.p10is2" in text:
            out.append(text[:200])
    return out


def rss_gib() -> float:
    """Resident set of this process and its children, in GiB."""
    p = psutil.Process()
    try:
        return float(sum(q.memory_info().rss for q in [p, *p.children(recursive=True)])) / 2**30
    except psutil.Error:
        return 0.0
