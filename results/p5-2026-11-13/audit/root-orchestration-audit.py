"""Verify P5 reporting commits, ACK accounting and source preservation without models."""

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

RESULTS = Path("results/p5-2026-11-13")
PREFLIGHT = Path("results/p5-preflight-2026-11-13")
SUITE = "P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be"
LAUNCH = "6b3e25726d709ab0efe05777ab8205bea5b59464"
ACK_FIELDS = {"suite_id", "worker_id", "commit", "push_completed"}


def load(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.check_output(["git", *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def tree(ref, path=None):
    output = git("ls-tree", "-rz", ref, *(("--", str(path)) if path else ()))
    rows = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        assert kind == "blob", (ref, name, kind)
        rows[Path(name.decode())] = (mode, blob)
    return rows


def same_tree_files(expected):
    for path, (mode, blob) in expected.items():
        assert path.is_file() and not path.is_symlink(), path
        assert git_blob(path.read_bytes()) == blob, path
        assert bool(path.stat().st_mode & 0o111) == (mode == "100755"), path


def bind_bundle(bundle, raw, commit, ancestors):
    assert re.fullmatch("[0-9a-f]{40}", commit) and commit in ancestors, commit
    committed = tree(commit, bundle)
    assert committed
    changed = git("diff-tree", "--no-commit-id", "-r", "-z", "--name-only", commit)
    assert {Path(p.decode()) for p in changed.split(b"\0") if p} == set(committed), commit
    observed = {p for p in bundle.rglob("*") if p.is_file()}
    assert observed == set(committed), bundle
    same_tree_files(committed)
    for name in observed:
        original = raw / name.relative_to(bundle)
        assert original.read_bytes() == name.read_bytes(), name
    return {name: sha((bundle / name).read_bytes()) for name in ("manifest.json", "result.json")}


def close(actual, expected):
    assert math.isfinite(actual) and math.isclose(actual, expected, abs_tol=1e-9, rel_tol=0), (
        actual,
        expected,
    )


def check_worker(bundle, frozen, ceiling):
    manifest = load(bundle / "manifest.json")
    terminal = load(bundle / "terminal.json")
    result = load(bundle / "result.json")
    for key in ("source_sha256", "spec_sha256", "config_sha256", "lock_sha256"):
        assert manifest[key] == frozen[key], (bundle, key)
    limits = frozen["limits"]
    assert 0 < manifest["limits"]["process_seconds"] <= ceiling
    assert manifest["limits"]["rss_bytes"] == limits["rss_bytes"]
    assert manifest["limits"]["poll_seconds"] == limits["poll_seconds"]
    assert terminal["status"] == manifest["status"] == result["outcome"] == "completed"
    assert terminal["returncode"] == 0 and terminal["reason"] is None
    assert 0 < terminal["process_wall_seconds"] <= manifest["limits"]["process_seconds"]
    assert 0 < terminal["peak_process_tree_rss_bytes"] <= limits["rss_bytes"]
    return manifest, terminal, result


def preserve_sources(freeze, tip):
    frozen = load(PREFLIGHT / "execution-freeze/source.json")["archive_file_sha256"]
    launch_tree = tree(LAUNCH)
    assert len(frozen) == 95
    for name, digest in frozen.items():
        path = Path(name)
        assert sha(path.read_bytes()) == digest, path
        assert path.is_file() and not path.is_symlink(), path
        assert launch_tree[path] == tip[path], path
    config = Path("configs/p5_hierarchy_ablation.toml")
    assert sha(config.read_bytes()) == freeze["config_file_sha256"]
    accepted = load(PREFLIGHT / "root-acceptance/acceptance.json")
    prior = accepted["prior_source_results_preservation"]
    reference = prior["reference_commit"]
    protected = {
        path: blob
        for path, blob in tree(reference).items()
        if path.parts[0] in {"src", "configs", "tests", "results"}
        or path.parts[:2] == ("docs", "decisions")
        or str(path) in {"pyproject.toml", "uv.lock"}
    }
    assert len(protected) == prior["protected_existing_files"] == 2763
    assert all(tip.get(path) == blob for path, blob in protected.items())
    same_tree_files(protected)
    return {
        "frozen_source_files": len(frozen),
        "prior_reference_commit": reference,
        "protected_existing_files": len(protected),
    }


def audit(args):
    freeze = load(PREFLIGHT / "execution-freeze/freeze.json")
    raw = args.raw
    assert raw.name == SUITE
    ancestors = set(git("rev-list", "HEAD").decode().splitlines())
    assert LAUNCH in ancestors
    tip = tree("HEAD")
    sources = preserve_sources(freeze, tip)
    limits = freeze["limits"]
    final = RESULTS / "suite"
    final_term = load(final / "terminal.json")
    final_result = load(final / "result.json")
    assert final_term == load(raw / "terminal.json")
    assert (final / "result.json").read_bytes() == (raw / "result.json").read_bytes()
    assert (final / "metrics.jsonl").read_bytes() == (raw / "metrics.jsonl").read_bytes()
    assert final_term["status"] == final_result["outcome"] == "completed"
    assert final_term["reason"] is None and final_term["rss_limit_exceeded"] is False

    quality = RESULTS / "quality-suite"
    quality_m, quality_t, quality_r = check_worker(quality, freeze, limits["quality_seconds"])
    quality_id = quality_m["run_id"]
    assert quality_m["parent_p5_suite_id"] == SUITE
    assert quality_m["dataset_manifest_sha256"] == freeze["dataset_manifest_sha256"]
    quality_raw = raw / "quality" / quality_id
    assert len(quality_r["cells"]) == len(freeze["execution_order"]) == 117
    assert quality_r["counts"] == {
        "additional_training_targets": 28311552,
        "integrity_evaluations": 9,
        "scientific_evaluations": 612,
        "snapshots": 333,
    }
    ledger = load(args.ledger)
    journal = load(args.journal)
    keys = ("index", "label", "commit", "status")
    assert all(row["kind"] == "quality" for row in journal)
    assert ledger == [{key: row[key] for key in keys} for row in journal]
    quality_bindings = []
    recount = dict.fromkeys(quality_r["counts"], 0)
    trained = 0
    for i, (row, cell, saved) in enumerate(
        zip(ledger, freeze["execution_order"], quality_r["cells"], strict=True), 1
    ):
        assert row["index"] == i and row["status"] == "completed"
        assert row["label"] == cell["label"] == saved["label"]
        assert all(saved[k] == value for k, value in cell.items())
        bundle = RESULTS / row["label"]
        m, t, r = check_worker(bundle, freeze, limits["cell_seconds"])
        assert m["run_id"] == saved["run_id"] and m["parent_p5_suite_id"] == quality_id
        assert m["dataset_manifest_sha256"] == freeze["dataset_manifest_sha256"]
        assert r["final"]["nll"] == saved["final_nll"] == journal[i - 1]["nll"]
        assert t["process_wall_seconds"] == saved["wall_seconds"] == journal[i - 1]["wall_seconds"]
        assert t["peak_process_tree_rss_bytes"] == saved["peak_rss_bytes"]
        snapshots = len(r["checkpoint_state_sha256"])
        updates = r["completed_steps"]
        baseline = cell["variant"] == "baseline"
        assert updates == (0 if baseline else 512)
        assert r["additional_training_targets"] == updates * 8 * 64
        assert snapshots == (1 if baseline else 3)
        recount["additional_training_targets"] += r["additional_training_targets"]
        recount["snapshots"] += snapshots
        recount["scientific_evaluations"] += (
            1 + (r["initial"] is not None) + len(r["interventions"])
        )
        recount["integrity_evaluations"] += int(baseline)
        trained += int(not baseline)
        hashes = bind_bundle(bundle, quality_raw / "cells" / m["run_id"], row["commit"], ancestors)
        quality_bindings.append({**row, "run_id": m["run_id"], "sha256": hashes})
    assert recount == quality_r["counts"] and trained == 108

    timing = final_result["timing_workers"]
    timing_status = load(final / "timing-status.json")
    assert timing_status["workers"] == timing
    records = [json.loads(line) for line in (final / "metrics.jsonl").read_text().splitlines()]
    assert len(timing) == 36 and len(records) == 73
    timing_records = records[1::2]
    ack_records = records[::2]
    assert records[0]["event"] == "quality_stage_reporting_acknowledged"
    assert len(ack_records) == 37
    bindings = [(quality, quality_raw, quality_id, quality_t)]
    observed_calls = []
    for row, event in zip(timing, timing_records, strict=True):
        assert event["event"] == "timing_worker_finished"
        assert {key: event[key] for key in row} == row
        bundle = RESULTS / "timing" / row["label"]
        cap_key = "timing_baseline_seconds" if row["seed"] == 0 else "timing_quartet_seconds"
        m, t, r = check_worker(bundle, freeze, limits[cap_key])
        assert m["run_id"] == row["run_id"] and m["parent_p5_suite_id"] == SUITE
        assert m["quality_stage_run_id"] == quality_id
        assert all(m[key] == row[key] for key in ("backbone", "order", "seed"))
        assert t["process_wall_seconds"] == row["wall_seconds"]
        assert t["peak_process_tree_rss_bytes"] == row["peak_rss_bytes"]
        calls = 192 if row["seed"] == 0 else 2112
        assert calls == row["timing_scope_calls"] == r["timing_scope_calls"]
        assert r["training_targets"] == r["scientific_evaluation_targets"] == 0
        observed_calls.append(calls)
        bindings.append((bundle, raw / "timing-workers" / m["run_id"], m["run_id"], t))
    assert len({r["label"] for r in timing}) == 36 and observed_calls.count(192) == 9
    assert sum(observed_calls) == final_result["timing_scope_calls"] == 58752

    ack_bindings = []
    waits = []
    assert {p.name for p in args.acks.glob("*.json")} == {f"{item[2]}.json" for item in bindings}
    assert {p.name for p in (raw / "report-acks").glob("*.json")} == {
        f"{item[2]}.json" for item in bindings
    }
    for i, ((bundle, origin, worker, t), event) in enumerate(
        zip(bindings, ack_records, strict=True)
    ):
        file = f"{worker}.json"
        ack_bytes = (args.acks / file).read_bytes()
        assert ack_bytes == (raw / "report-acks" / file).read_bytes()
        ack = json.loads(ack_bytes)
        assert set(ack) == ACK_FIELDS and ack == {key: event[key] for key in ACK_FIELDS}
        assert ack["suite_id"] == SUITE and ack["worker_id"] == worker
        assert ack["push_completed"] is True
        if i:
            assert event["event"] == "reporting_acknowledged"
        waits.append(event["external_wait_seconds"])
        assert math.isfinite(waits[-1]) and waits[-1] >= 0
        close(event["accounting"]["external_reporting_wait_seconds"], math.fsum(waits))
        hashes = bind_bundle(bundle, origin, ack["commit"], ancestors)
        ack_bindings.append(
            {
                **ack,
                "bundle": str(bundle),
                "ack_sha256": sha(ack_bytes),
                "sha256": hashes,
                "external_wait_seconds": waits[-1],
                "wall_seconds": t["process_wall_seconds"],
                "peak_rss_bytes": t["peak_process_tree_rss_bytes"],
            }
        )

    commits = [r["commit"] for r in quality_bindings + ack_bindings]
    assert len(set(commits)) == 154
    for previous, current in zip([LAUNCH, *commits[:-1]], commits, strict=True):
        subprocess.run(["git", "merge-base", "--is-ancestor", previous, current], check=True)
    acc = final_term["accounting"]
    excluded = math.fsum(waits)
    close(acc["external_reporting_wait_seconds"], excluded)
    active = acc["timing_stage_wall_seconds"] - excluded
    close(acc["timing_worker_active_seconds"], active)
    quality_time = acc["quality_stage_wall_seconds"]
    close(acc["quality_worker_seconds"], quality_time)
    close(acc["combined_worker_active_seconds"], quality_time + active)
    assert 0 < quality_t["process_wall_seconds"] <= quality_time <= limits["quality_seconds"]
    assert 0 < active <= limits["timing_seconds"]
    assert quality_time + active <= limits["combined_seconds"]
    max_timing_rss = max(row["peak_rss_bytes"] for row in timing)
    assert (
        max(max_timing_rss, quality_t["peak_process_tree_rss_bytes"])
        <= (final_term["peak_suite_process_tree_rss_bytes"])
        <= limits["rss_bytes"]
    )
    return {
        "status": "PASS",
        "suite": SUITE,
        "source_preservation": sources,
        "quality_checkpoint_count": len(quality_bindings),
        "quality_counts_recounted": recount,
        "quality_trained_cells": trained,
        "quality_checkpoint_bindings": quality_bindings,
        "ack_count": len(ack_bindings),
        "ack_bindings": ack_bindings,
        "timing_worker_count": len(timing),
        "timing_scope_calls": sum(observed_calls),
        "accounting": acc,
        "peak_suite_rss_bytes": final_term["peak_suite_process_tree_rss_bytes"],
        "peak_quality_stage_rss_bytes": quality_t["peak_process_tree_rss_bytes"],
        "max_timing_worker_rss_bytes": max_timing_rss,
        "scope": (
            "Git ancestry and immutable content plus recorded ACK and push attestations; "
            "Git does not establish that a chat report was delivered."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = RESULTS / "audit"
    parser.add_argument("--raw", type=Path, default=Path("experiments") / SUITE)
    parser.add_argument("--ledger", type=Path, default=default / "root-orchestration-ledger.json")
    parser.add_argument("--acks", type=Path, default=default / "root-orchestration-acks")
    parser.add_argument(
        "--journal", type=Path, default=Path("experiments/review/p5-push-journal.json")
    )
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError("Run the audit with assertions enabled")
    print(json.dumps(audit(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
