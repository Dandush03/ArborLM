"""Re-check (auditor role, Claude Opus 5.5): the REGISTERED (non-dry-run) code path of the P7-B stage
sequence, end to end, in a scratch Git clone, with synthetic data and every confirmation file
produced by the auditor's tools exactly as they are (committed in the clone at the registered paths).

What it shows (or refutes):
  * m1  - the tools' tool_sha256 satisfies each gate's `git show HEAD:<tool path>` binding;
          a stand-in confirmation and a hash of an edited tool are refused outside a dry run.
  * M1  - simulate (either stream) refuses while the stream-B identity manifest is untracked,
          staged-only, or edited after the commit; accepts it once committed and clean, and records
          its SHA-256 and the real Git check (not the stand-in) in the linkage.
  * m3  - commits under results/ and docs/reviews/ between stages do not break linkage; an edit of
          any src/arborlm/*.py file (not only p7b_*) or of ADR-0014 makes the next stage refuse.

Everything happens inside <scratch>/clone (a `git clone` of the repository at HEAD, plus copies of
the untracked P7-B sources, tests and auditor tools, committed there as a simulated freeze). The
study code is imported from <scratch>/clone/src via PYTHONPATH; cwd is the clone. Synthetic data
only (the implementer's dry-run fixture builders, 2 parent/seed pairs, 8 contexts); no real trace,
no parquet, no model checkpoint is opened. Nothing is written in the real repository.

Independent engineering evidence; not Astra validation; not human approval.
argv: <real repo> <scratch dir>
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REAL = Path(sys.argv[1]).resolve()
SCRATCH = Path(sys.argv[2]).resolve()
CLONE = SCRATCH / "clone"
TOOLS_REL = "docs/reviews/p7b-preflight-2026-11-13/tools"
AUDIT_REL = "docs/reviews/p7b-results-audit-SCRATCH"
RESULTS_REL = "results/p7b-SCRATCH"
LOG: dict = {"checks": []}


def sh(*args: str, cwd: Path = CLONE, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=check)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return sh("git", "-c", "user.name=auditor-scratch", "-c", "user.email=scratch@example.invalid",
              "-c", "commit.gpgsign=false", *args, check=check)


def record(name: str, ok: bool, detail: str = "") -> None:
    LOG["checks"].append({"check": name, "ok": ok, "detail": detail[-600:]})
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail[-300:]}" if detail else ""), flush=True)


def setup() -> None:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    sh("git", "clone", "-q", "--no-hardlinks", str(REAL), str(CLONE), cwd=SCRATCH)
    for pattern in ("src/arborlm/p7b_*.py", "tests/test_p7b_*.py"):
        for path in sorted(REAL.glob(pattern)):
            shutil.copy2(path, CLONE / path.relative_to(REAL))
    (CLONE / TOOLS_REL).mkdir(parents=True, exist_ok=True)
    for path in sorted((REAL / TOOLS_REL).glob("*.py")):
        shutil.copy2(path, CLONE / TOOLS_REL / path.name)
    git("add", "src/arborlm", "tests", TOOLS_REL)
    git("commit", "-q", "-m", "SCRATCH simulated freeze: P7-B sources, tests, auditor tools")
    LOG["freeze_commit"] = git("rev-parse", "HEAD").stdout.strip()
    LOG["tool_sha256_at_head"] = {
        p.name: sh("git", "show", f"HEAD:{TOOLS_REL}/{p.name}").stdout and
        subprocess.run(["git", "show", f"HEAD:{TOOLS_REL}/{p.name}"], cwd=CLONE,
                       capture_output=True).stdout
        for p in sorted((CLONE / TOOLS_REL).glob("*.py"))
    }
    import hashlib

    LOG["tool_sha256_at_head"] = {k: hashlib.sha256(v).hexdigest()
                                  for k, v in LOG["tool_sha256_at_head"].items()}


def run_tool(argv: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, "-I", *argv], capture_output=True, text=True, cwd=CLONE)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def only(path: Path) -> Path:
    items = sorted(p for p in path.iterdir() if p.is_dir())
    assert len(items) == 1, items
    return items[0]


def expect_refusal(name: str, fn, match: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        text = f"{type(exc).__name__}: {exc}"
        record(name, match in text, text)
        return
    record(name, False, "no refusal")


def main() -> int:
    setup()
    os.chdir(CLONE)
    sys.path.insert(0, str(CLONE / "src"))
    os.environ["PYTHONPATH"] = str(CLONE / "src")  # inherited by the supervised workers
    import arborlm
    from arborlm import p7b_core as core
    from arborlm import p7b_gates as gates
    from arborlm import p7b_study as study
    from arborlm.p6_common import pairs
    from arborlm.p7b_synth import build_identity, synthetic_corpus, write_references

    LOG["arborlm_imported_from"] = arborlm.__file__
    record("study code imported from the clone", str(CLONE) in arborlm.__file__, arborlm.__file__)
    fixture = CLONE / "experiments" / "fixture"  # /experiments/ is git-ignored
    fixture.mkdir(parents=True)
    args = study.build_parser().parse_args(["panel"])
    args.output_root, args.results_root = CLONE / "experiments", CLONE / RESULTS_REL
    opt = study.Options(args)
    opt.dry_run, opt.synthetic = False, True  # REGISTERED code path, synthetic data
    opt.pair_list, opt.contexts = pairs()[:2], study.DRY_CONTEXTS
    opt.repo = fixture
    opt.parent_suite, opt.p5_results = fixture / "none", fixture / "p5-none"
    identity, kept = build_identity(fixture, opt.pair_list, opt.contexts)
    opt.identity_path = identity.path
    opt.reference_dir = write_references(fixture, identity, kept)
    opt.selection = opt.labels()
    labels = opt.labels()
    audit = CLONE / AUDIT_REL
    audit.mkdir(parents=True)
    T = CLONE / TOOLS_REL

    # 1. panel, then the auditor panel tool (synthetic rows of the fixture)
    code = study.run_panel(opt)[0]
    record("panel stage (registered path) completed", code == 0)
    panel_c = only(opt.results_root / "panel")
    rec = json.loads((panel_c / "panel_record.json").read_text())
    rows = {"train": synthetic_corpus(1, 400), "validation": synthetic_corpus(2, 240),
            "registered_earlier": {k: v["sha256"] for k, v in rec["earlier_panels"].items()}}
    (fixture / "rows.json").write_text(json.dumps(rows))
    rc, out = run_tool([str(T / "independent_panel.py"), "--mode", "synthetic",
                        "--synthetic-rows", str(fixture / "rows.json"),
                        "--panel-size", str(opt.contexts), "--train-pool", str(8 * opt.contexts),
                        "--panel-record", str(panel_c / "panel_record.json"),
                        "--panel-run-id", panel_c.name, "--out", str(audit / "panel_confirmation.json"),
                        "--detail", str(fixture / "panel_detail.json")])
    record("independent_panel.py AGREE", rc == 0, out)
    opt.panel_confirmation = audit / "panel_confirmation.json"

    # 2. layouts, then the auditor layout tool
    code = study.run_layouts(opt)[0]
    record("layouts stage (registered path) completed", code == 0)
    layout_c = only(opt.results_root / "layouts")
    rc, out = run_tool([str(T / "independent_layouts.py"), "--repo", str(CLONE),
                        "--identity", str(identity.path), "--base", str(fixture),
                        "--hash-table", str(layout_c / "layout_hash_table.json"),
                        "--layout-run-id", layout_c.name, "--labels", *labels,
                        "--out", str(audit / "layout_confirmation.json"),
                        "--detail", str(fixture / "layout_detail.json")])
    record("independent_layouts.py AGREE", rc == 0, out)
    opt.layout_confirmation = audit / "layout_confirmation.json"

    # m1: the gates accept the tools' files outside a dry run (binding to HEAD), before any commit
    # of results (the tools are already at HEAD from the freeze commit)
    g = gates.check_layout_confirmation(opt.layout_confirmation,
                                        hash_table_path=layout_c / "layout_hash_table.json",
                                        layout_run_id=layout_c.name, labels=labels, dry_run=False)
    record("gate (b) accepts independent_layouts.py output, registered mode",
           g["tool_binding"]["tool_sha256"] == g["tool_binding"]["tool_sha256_at_head"]
           and g["tool_binding"]["stand_in"] is False, json.dumps(g["tool_binding"]))
    g = gates.check_panel_confirmation(opt.panel_confirmation,
                                       panel_record_path=panel_c / "panel_record.json",
                                       panel_run_id=panel_c.name, dry_run=False,
                                       ranks=tuple(rec["ranks"]), rows=len(rec["row_sha256"]),
                                       earlier=rows["registered_earlier"])
    record("gate (a) accepts independent_panel.py output, registered mode",
           g["tool_binding"]["tool_sha256"] == g["tool_binding"]["tool_sha256_at_head"],
           json.dumps(g["tool_binding"]))
    # negative controls for m1
    data = json.loads(opt.layout_confirmation.read_text())
    stand = dict(data, tool=core.STAND_IN_TOOL, tool_sha256=core.STAND_IN_TOOL_SHA256)
    (fixture / "stand_in.json").write_text(json.dumps(stand))
    expect_refusal("gate (b) refuses a stand-in outside a dry run",
                   lambda: gates.check_layout_confirmation(
                       fixture / "stand_in.json", hash_table_path=layout_c / "layout_hash_table.json",
                       layout_run_id=layout_c.name, labels=labels, dry_run=False),
                   "stand-in is not accepted outside a dry run")
    edited_tool = T / "independent_layouts.py"
    original = edited_tool.read_bytes()
    edited_tool.write_bytes(original + b"# edited after the freeze\n")
    rc, out = run_tool([str(T / "independent_layouts.py"), "--repo", str(CLONE),
                        "--identity", str(identity.path), "--base", str(fixture),
                        "--hash-table", str(layout_c / "layout_hash_table.json"),
                        "--layout-run-id", layout_c.name, "--labels", *labels,
                        "--out", str(fixture / "layout_conf_edited_tool.json"),
                        "--detail", str(fixture / "layout_detail_edited.json")])
    edited_tool.write_bytes(original)
    expect_refusal("gate (b) refuses output of an edited (uncommitted) tool",
                   lambda: gates.check_layout_confirmation(
                       fixture / "layout_conf_edited_tool.json",
                       hash_table_path=layout_c / "layout_hash_table.json",
                       layout_run_id=layout_c.name, labels=labels, dry_run=False),
                   "is not the SHA-256 of")
    record("tool restored byte-identical", sh("git", "diff", "--quiet", "HEAD", "--", TOOLS_REL,
                                              check=False).returncode == 0)

    # commit point 1: layout hash table (whole layouts compact dir) + both confirmation files
    git("add", f"{RESULTS_REL}/panel", f"{RESULTS_REL}/layouts", AUDIT_REL)
    git("commit", "-q", "-m", "SCRATCH commit 1: layout hash table and confirmations")

    # 3. trace-b (gated on both confirmations, registered mode)
    code = study.run_trace_b(opt)[0]
    record("trace-b stage (registered path, after commit 1) completed: linkage intact", code == 0)
    trace_c = only(opt.results_root / "trace-b")
    tman = json.loads((trace_c / "manifest.json").read_text())
    record("trace-b linkage records real tool bindings",
           tman["linkage"]["panel_confirmation"]["tool_binding"]["stand_in"] is False
           and tman["linkage"]["layout_confirmation"]["tool_binding"]["stand_in"] is False)

    # M1: simulate must refuse while the manifest is untracked, staged-only, edited
    for stream in ("A", "B"):
        expect_refusal(f"simulate {stream} refused: stream-B manifest untracked",
                       lambda s=stream: study.run_simulate(opt, s), "not tracked by Git")
    git("add", f"{RESULTS_REL}/trace-b")
    expect_refusal("simulate A refused: manifest staged but not committed",
                   lambda: study.run_simulate(opt, "A"), "differs from HEAD")
    # commit point 2: the stream-B identity manifest (whole trace-b compact dir)
    git("commit", "-q", "-m", "SCRATCH commit 2: stream-B identity manifest")
    mpath = trace_c / core.STREAM_B_MANIFEST
    good = mpath.read_bytes()
    mpath.write_bytes(good + b" ")
    expect_refusal("simulate B refused: committed manifest edited in the working tree",
                   lambda: study.run_simulate(opt, "B"), "differs from HEAD")
    mpath.write_bytes(good)
    record("no simulate stage directory was opened by the refusals",
           not (opt.results_root / "simulate-a").exists()
           and not (opt.results_root / "simulate-b").exists())

    # m3: an edit of a non-p7b module or of ADR-0014 makes the next stage refuse
    for rel in ("src/arborlm/io.py", core.SPEC):
        p = CLONE / rel
        orig = p.read_bytes()
        p.write_bytes(orig + b"\n# scratch edit\n")
        expect_refusal(f"simulate A refused after editing {rel}",
                       lambda: study.run_simulate(opt, "A"), "differ")
        p.write_bytes(orig)
    record("tree clean again after the m3 probes",
           sh("git", "status", "--porcelain", "--untracked-files=no").stdout.strip() == "")

    # 4. simulate A, simulate B (registered path)
    for stream, stage in (("A", "simulate-a"), ("B", "simulate-b")):
        code = study.run_simulate(opt, stream)[0]
        record(f"simulate {stream} (registered path) completed", code == 0)
        man = json.loads((only(opt.results_root / stage) / "manifest.json").read_text())
        link = man["linkage"]["stream_b_identity_manifest"]
        record(f"simulate {stream} linkage: real Git check and manifest SHA-256",
               link["stand_in"] is False and "tracked, clean" in link["git_check"]
               and link["sha256"] == json.loads((trace_c / "result.json").read_text())[
                   "stream_b_identity_manifest_sha256"], json.dumps(link))
    sim_a, sim_b = only(opt.results_root / "simulate-a"), only(opt.results_root / "simulate-b")
    for compact in (sim_a, sim_b):
        for path in sorted((compact / "workers").glob("*.result.json")):
            r = json.loads(path.read_text())
            ok = r["outcome"] == "completed" and r["r1_invariants"]["all_identical"] is True
            if r["stream"] == "B":
                ok = ok and r["counts_identity"]["counts_sha256_checked"] is True
            if not ok:
                record(f"worker record {path.name}", False, json.dumps(r.get("outcome")))
    record("every worker record: completed, R=1 run-time check, counts identity (B)", True)

    # 5. auditor re-simulation, both streams
    common = ["--repo", str(CLONE), "--identity", str(identity.path), "--base", str(fixture),
              "--hash-table", str(layout_c / "layout_hash_table.json"), "--selection", *labels]
    rc, out = run_tool([str(T / "independent_resim.py"), "--stream", "A", *common,
                        "--simulate-dir", str(sim_a), "--p7a-reference", str(opt.reference_dir),
                        "--out", str(audit / "resim_confirmation_A.json"),
                        "--detail", str(fixture / "resim_A_detail.json")])
    record("independent_resim.py stream A AGREE", rc == 0, out)
    rc, out = run_tool([str(T / "independent_resim.py"), "--stream", "B", *common,
                        "--simulate-dir", str(sim_b), "--trace-b-compact", str(trace_c),
                        "--trace-b-dir", str(opt.output_root / trace_c.name / "traces"),
                        "--out", str(audit / "resim_confirmation_B.json"),
                        "--detail", str(fixture / "resim_B_detail.json")])
    record("independent_resim.py stream B AGREE (manifest-bound)", rc == 0, out)
    opt.resim_confirmation_a = audit / "resim_confirmation_A.json"
    opt.resim_confirmation_b = audit / "resim_confirmation_B.json"

    # commit point 3 (optional in the registered order): simulate records + resim confirmations
    git("add", f"{RESULTS_REL}/simulate-a", f"{RESULTS_REL}/simulate-b", AUDIT_REL)
    git("commit", "-q", "-m", "SCRATCH commit 3: simulate records and re-simulation confirmations")

    # 6. analyze (registered path, gated on both resim confirmations with real tool binding)
    code = study.run_analyze(opt)[0]
    record("analyze (registered path, after commit 3) completed", code == 0)
    an = only(opt.results_root / "analyze")
    man = json.loads((an / "manifest.json").read_text())
    record("analyze linkage: real tool bindings for both resim confirmations",
           all(man["linkage"][k]["tool_binding"]["stand_in"] is False
               and man["linkage"][k]["tool_binding"]["tool_sha256"]
               == man["linkage"][k]["tool_binding"]["tool_sha256_at_head"]
               for k in ("resim_confirmation_a", "resim_confirmation_b")))
    stage_manifests = {
        s: json.loads((only(opt.results_root / s) / "manifest.json").read_text())
        for s in ("panel", "layouts", "trace-b", "simulate-a", "simulate-b", "analyze")}
    record("every stage: dry_run false, frozen check at end passed, same package hashes",
           all(m["dry_run"] is False and m["status"] == "completed"
               and m["frozen_check_at_end"]["problem"] is None for m in stage_manifests.values())
           and len({json.dumps(m["package_source_sha256"], sort_keys=True)
                    for m in stage_manifests.values()}) == 1)
    LOG["git_heads_per_stage"] = {s: m["git_head_informational"] for s, m in stage_manifests.items()}
    LOG["repo_real_untouched_note"] = "all writes under the scratch clone"
    failed = [c for c in LOG["checks"] if not c["ok"]]
    LOG["result"] = "PASS" if not failed else f"FAIL ({len(failed)})"
    (SCRATCH / "registered_path_scratch_git.json").write_text(json.dumps(LOG, indent=1))
    print(json.dumps({"freeze_commit": LOG["freeze_commit"], "tool_sha256_at_head":
                      LOG["tool_sha256_at_head"], "git_heads_per_stage": LOG["git_heads_per_stage"],
                      "result": LOG["result"]}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
