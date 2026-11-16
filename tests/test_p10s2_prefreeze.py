# ruff: noqa: E501
"""P10S2 fixed launch scripts, the freeze procedure and its refusals, and the fetch guard (ADR-0022 sections 13.3, 14.1, 16, 18). Pre-freeze lessons carried from the P9-II audit and its first generation
attempt (a launch script that never passed a required flag was never executed): every launch script is run here, with a stub in place of ``uv``, and its arguments are parsed by the real parser. Nothing is
downloaded and the fetch step is never called. Self-check only: not independent review, not Astra validation, not human approval."""

import ast
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import budget, core, fetch_guard, freeze, stages  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "studies" / "p10s2" / "launch"
REGISTERED = ("gates", "train", "evaluate", "timing", "recompute", "analysis", "report")
PREFREEZE = ("datagen", "calibrate", "rehearse")
GIB = 2**30


def run_script(name: str, args: list[str], tmp: Path) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run a launch script with a stub ``uv`` first on PATH; return the process and the arguments the stub received (one per line)."""
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    out = tmp / "uv_args.txt"
    out.unlink(missing_ok=True)
    stub = bindir / "uv"
    stub.write_text(f'#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > "{out}"\npwd >> "{out}"\n')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
    p = subprocess.run(["sh", str(LAUNCH / f"{name}.sh"), *args], capture_output=True, text=True, env=env, cwd=tmp, check=False)  # noqa: S603, S607
    lines = out.read_text().splitlines() if out.exists() else []
    return p, lines


@pytest.mark.parametrize("name", REGISTERED)
def test_registered_scripts_pass_every_required_flag_to_the_real_parser(name: str, tmp_path: Path) -> None:
    p, lines = run_script(name, [str(tmp_path / "run"), "abc123"], tmp_path)
    assert p.returncode == 0, p.stderr
    assert lines[:5] == ["run", "--locked", "python", "-m", "studies.p10s2.stages"]
    argv = lines[5:-1]
    assert Path(lines[-1]).resolve() == ROOT.resolve()  # the script changes to the repository root before the exec
    args = stages.build_parser().parse_args(argv)  # the parser requires every flag: this fails if the script omitted one (the P9-II first-attempt failure)
    assert args.command == "registered" and args.name == name and args.freeze_commit == "abc123" and args.run_dir == str(tmp_path / "run") and args.caps == "studies/p10s2/freeze/stage_caps.json"
    assert argv.count("--caps") == 1 and all(a.startswith("--") or not a.startswith("-") for a in argv)  # nothing else is passed


@pytest.mark.parametrize("name", PREFREEZE)
def test_prefreeze_scripts_pass_the_stage_cap_and_every_required_flag(name: str, tmp_path: Path) -> None:
    p, lines = run_script(name, [str(tmp_path / "run"), "deadbeef"], tmp_path)
    assert p.returncode == 0, p.stderr
    if name == "datagen":  # the locked pyarrow comes from an extra of the lock, so the launch script may add "--extra pilot" before the requirements
        assert lines[:5] == ["run", "--locked", "--extra", "pilot", "python"] and "--with-requirements" not in lines  # re-check A, R2: the packages are installed by install_datagen and put on the datagen process's path only
    else:
        assert lines[:3] == ["run", "--locked", "python"]
    mod = "studies.p10s2.datagen" if name == "datagen" else "studies.p10s2.stages"
    i = lines.index("-m")
    assert lines[i + 1] == mod
    argv = lines[i + 2 : -1]
    cap = float(argv[argv.index("--stage-cap-seconds") + 1])
    assert cap == float(core.CFG["prefreeze_caps"][name])  # the stage cap equals the configured one
    assert "--code-commit" in argv and argv[argv.index("--code-commit") + 1] == "deadbeef"
    if name == "datagen":
        flags = set(re.findall(r'add_argument\("(--[a-z-]+)"[^)]*required=True', (ROOT / "studies/p10s2/datagen.py").read_text()))
        assert flags <= set(argv) and {"--downloads", "--out", "--code-commit", "--stage-cap-seconds"} <= flags
    else:
        args = stages.build_parser().parse_args(argv)
        assert args.command == name and args.stage_cap_seconds == cap and args.code_commit == "deadbeef" and args.run_dir == str(tmp_path / "run")


def test_script_argument_handling(tmp_path: Path) -> None:
    for name in (*REGISTERED, *PREFREEZE):
        p, lines = run_script(name, [], tmp_path)
        assert p.returncode == 2 and "usage:" in p.stderr and lines == []  # nothing is launched without exactly the run directory and the commit
        p, lines = run_script(name, ["a", "b", "c"], tmp_path)
        assert p.returncode == 2 and lines == []
    p, lines = run_script("gates", ["relative/run", "c1"], tmp_path)
    assert lines[lines.index("--run-dir") + 1] == str(tmp_path / "relative/run")  # a relative run directory is made absolute against the caller's directory
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["registered", "gates", "--run-dir", "x", "--freeze-commit", "c"])  # --caps is required (every script passes it)
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["registered", "invent", "--run-dir", "x", "--freeze-commit", "c", "--caps", "y"])
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["calibrate", "--run-dir", "x", "--code-commit", "c", "--data-dir", "d", "--updates", "1"])  # --stage-cap-seconds is required


def test_prefreeze_stage_caps_are_the_upper_end_of_the_adr_projections() -> None:
    caps = core.CFG["prefreeze_caps"]
    assert caps == {"datagen": 6480, "calibrate": 7920, "rehearse": 11520} and caps["datagen"] == pytest.approx(1.8 * 3600) and caps["calibrate"] == pytest.approx(2.2 * 3600) and caps["rehearse"] == pytest.approx(3.2 * 3600)


# --- the freeze procedure -------------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a], capture_output=True, text=True, check=True)  # noqa: S603, S607
    return r.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    for rel, content in (("studies/p10s2/x.py", "x = 1\n"), ("src/arborlm/a.py", "a = 1\n"), ("uv.lock", "lock\n"), ("pyproject.toml", "[project]\n"), ("tests/test_p10s2_a.py", "def test_a(): pass\n"), ("tests/test_other.py", "")):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text(content)
    (r / core.DEFAULT_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (r / core.DEFAULT_CONFIG).write_text((ROOT / core.DEFAULT_CONFIG).read_text())
    (r / core.SPEC).parent.mkdir(parents=True, exist_ok=True)
    (r / core.SPEC).write_text("adr\n")
    git(r, "init", "-q", "-b", "main")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "freeze")
    return r


def test_preconditions_clean_tree_ancestor_and_frozen_paths(repo: Path) -> None:
    c = git(repo, "rev-parse", "HEAD")
    ident = freeze.check_preconditions(repo, c)
    assert ident["commit"] == c and len(ident["tree"]) == 40
    with pytest.raises(freeze.FreezeRefused, match="requires --freeze-commit"):
        freeze.check_preconditions(repo, None)
    with pytest.raises(freeze.FreezeRefused, match="not a commit"):
        freeze.check_preconditions(repo, "0" * 40)
    (repo / "scratch.txt").write_text("x")
    with pytest.raises(freeze.FreezeRefused, match="not clean"):
        freeze.check_preconditions(repo, c)  # an untracked file also makes the tree unclean
    (repo / "scratch.txt").unlink()
    for rel in ("studies/p10s2/x.py", "src/arborlm/a.py", "uv.lock", "pyproject.toml", core.SPEC, "studies/p10s2/new.py", str(core.DEFAULT_CONFIG)):
        p = repo / rel
        old = p.read_text() if p.exists() else None
        p.write_text((old or "") + "# changed\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"change {rel}")
        with pytest.raises(freeze.FreezeRefused, match="differs from the freeze commit"):
            freeze.check_preconditions(repo, c)
        git(repo, "reset", "-q", "--hard", c)
    t = repo / "tests/test_p10s2_a.py"
    t.write_text("def test_a(): assert True\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "test changed")
    with pytest.raises(freeze.FreezeRefused, match="test_p10s2_a.py differs"):
        freeze.check_preconditions(repo, c)
    git(repo, "reset", "-q", "--hard", c)
    (repo / "tests/test_other.py").write_text("changed")  # a test of another study is not frozen here
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "other test")
    assert freeze.check_preconditions(repo, c)["commit"] == c
    # a commit that is not an ancestor of HEAD
    git(repo, "checkout", "-q", "-b", "side", c)
    (repo / "studies/p10s2/side.py").write_text("s = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "side")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    with pytest.raises(freeze.FreezeRefused, match="not an ancestor"):
        freeze.check_preconditions(repo, side)


def test_code_commit_must_equal_a_clean_head(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    assert freeze.check_code_commit(repo, head) == head
    with pytest.raises(freeze.FreezeRefused):
        freeze.check_code_commit(repo, None)
    (repo / "studies/p10s2/x.py").write_text("x = 2\n")
    with pytest.raises(freeze.FreezeRefused, match="not clean"):
        freeze.check_code_commit(repo, head)
    git(repo, "commit", "-q", "-a", "-m", "next")
    with pytest.raises(freeze.FreezeRefused, match="not a clean HEAD"):
        freeze.check_code_commit(repo, head)


def test_registered_stage_refuses_a_stage_without_a_cap_and_a_full_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    caps = {"n4-U2000": {"train": 3600.0}}
    assert budget.cap_for(caps, "train", 4, 2000) == 3600.0
    with pytest.raises(budget.CapMissing):
        budget.cap_for(caps, "gates", 4, 2000)
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("train", 35.5 * 3600)
    from studies.p10s2.ledger import LedgerRefused

    with pytest.raises(LedgerRefused):
        led.refuse_if_over(3600.0 / 3600.0, 36.0, "stage train")
    assert not capsys.readouterr().err


# --- the fetch guard (nothing is downloaded; the fetch step is never called) ------------------------------------------------------------------------------
def test_pinned_identities_equal_the_adr() -> None:
    adr = (ROOT / core.SPEC).read_text()
    for repo_rev in (fetch_guard.TEACHER_A, fetch_guard.TEACHER_B, fetch_guard.STUDENT, fetch_guard.FALLBACK):
        assert repo_rev[0] in adr and repo_rev[1] in adr
    for name, (digest, size) in fetch_guard.LARGE.items():
        assert digest in adr and f"{size:,}" in adr, name
    for _name, (rel, size) in {**fetch_guard.TATOEBA_FILES, **fetch_guard.FALLBACK_DATA}.items():
        assert rel.split("/")[-1] in adr and f"{size:,}" in adr
    assert fetch_guard.TATOEBA == "https://downloads.tatoeba.org/exports/per_language"


def test_authorization_flag_and_manifest_are_required(tmp_path: Path) -> None:
    m = tmp_path / "manifest.json"
    with pytest.raises(fetch_guard.FetchRefused, match="--i-have-recorded-human-approval"):
        fetch_guard.check_authorization(False, m)
    with pytest.raises(fetch_guard.FetchRefused, match="manifest path is required"):
        fetch_guard.check_authorization(True, None)
    with pytest.raises(fetch_guard.FetchRefused, match="does not exist"):
        fetch_guard.check_authorization(True, m)
    m.write_text("{}")
    fetch_guard.check_authorization(True, m)
    assert fetch_guard.APPROVAL_FLAG == "--i-have-recorded-human-approval"


def test_manifest_lists_exactly_the_approved_downloads_and_demands_digests() -> None:
    man = fetch_guard.build_manifest()
    names = {f["name"] for f in man["files"]}
    assert "teacher_a/pytorch_model.bin" in names and "student/model.safetensors" in names and "tatoeba/deu_eng_links.tsv.bz2" in names
    assert not any(n.startswith("fallback/") or "spa" in n for n in names)  # the fallback files only if the fallback rule is invoked
    files = fetch_guard.validate_manifest(man)  # every digest is a constant of reviewed code (git-blob SHA-1 for the small files, SHA-256 for the large ones), filled in by build_manifest
    assert all((f["sha256"] is None) != (f["git_sha1"] is None) for f in files if f["kind"] != "tatoeba") and all(f["sha256"] is None and f["git_sha1"] is None for f in files if f["kind"] == "tatoeba")
    assert sum(int(f["size"] or 0) for f in files) < 1.5e9 and sum(f["size"] or 0 for f in man["files"] if f["kind"] == "tatoeba") == 24947715 + 12144786 + 9805546 + 3557634 + 2679128 + 3552331 + 2678076
    big = json.loads(json.dumps(man))
    big["files"][0]["size"] = int(2e9)
    with pytest.raises(fetch_guard.FetchRefused, match="size other than"):
        fetch_guard.validate_manifest(big)
    other = json.loads(json.dumps(man))
    other["files"].append({"name": "tatoeba/other.tsv.bz2", "url": "https://example.invalid/x"})
    with pytest.raises(fetch_guard.FetchRefused, match="not an approved download"):
        fetch_guard.validate_manifest(other)
    wrong_url = json.loads(json.dumps(man))
    wrong_url["files"][0]["url"] = "https://example.invalid/model.bin"
    with pytest.raises(fetch_guard.FetchRefused, match="URL other than the approved"):
        fetch_guard.validate_manifest(wrong_url)
    wrong_sha = json.loads(json.dumps(man))
    wrong_sha["files"][0]["sha256"] = "1" * 64
    with pytest.raises(fetch_guard.FetchRefused, match="other than the pinned"):
        fetch_guard.validate_manifest(wrong_sha)
    dup = json.loads(json.dumps(man))
    dup["files"].append(dup["files"][0])
    with pytest.raises(fetch_guard.FetchRefused, match="listed twice"):
        fetch_guard.validate_manifest(dup)
    with pytest.raises(fetch_guard.FetchRefused, match="no file"):
        fetch_guard.validate_manifest({"files": []})


def test_fallback_files_need_a_recorded_human_decision(tmp_path: Path) -> None:
    # the fallback is invoked by a decision that names a committed record (path and commit), not by any non-empty string; the fallback manifest lists the fallback rows only
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "decision.md").write_text("the human lead invoked the fallback\n")
    git(repo, "init", "-q")
    git(repo, "add", "decision.md")
    git(repo, "commit", "-q", "-m", "decision")
    commit = git(repo, "rev-parse", "HEAD")
    decision = {"path": "decision.md", "commit": commit}
    man = fetch_guard.build_manifest(fallback_human_decision=decision)
    names = {f["name"] for f in man["files"]}
    assert "fallback/pytorch_model.bin" in names and "tatoeba/spa_sentences.tsv.bz2" in names and man["fallback_human_decision"] == decision
    assert not any(n.startswith(("teacher_a/", "teacher_b/", "student/")) or n in fetch_guard.TATOEBA_NAMES for n in names)  # the primary files stay frozen and are not listed again
    assert fetch_guard.validate_manifest(man, root=repo)
    for bad in ("the human lead invoked the fallback on <date> (recorded in the ADR)", None, {"path": "decision.md"}, {"path": "decision.md", "commit": "abc"}, {"path": "missing.md", "commit": commit}, {"path": "../x", "commit": commit}):
        man["fallback_human_decision"] = bad
        with pytest.raises(fetch_guard.FetchRefused, match="fallback"):
            fetch_guard.validate_manifest(man, root=repo)


def test_verify_file_and_tatoeba_digests_are_recorded_at_first_download(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    d = fetch_guard.sha256_file(p)
    fetch_guard.verify_file(p, d)
    with pytest.raises(fetch_guard.FetchRefused):
        fetch_guard.verify_file(p, "0" * 64)
    assert fetch_guard.record_tatoeba_digests([p]) == {"f.bin": d}


def test_the_fetch_step_checks_authorization_first_and_touches_the_network_only_in_one_function() -> None:
    src = (ROOT / "studies/p10s2/fetch.py").read_text()
    tree = ast.parse(src)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "") for n in ast.walk(main) if isinstance(n, ast.Call)]
    assert calls.index("check_authorization") < calls.index("run")  # the guard runs before anything is fetched
    for path in sorted((ROOT / "studies" / "p10s2").glob("*.py")):
        t = ast.parse(path.read_text())
        for fn in [n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(fn):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    if any(m.split(".")[0] in ("urllib", "socket", "http", "requests", "ftplib") for m in mods):
                        assert (path.name, fn.name) == ("fetch.py", "_download")
        for node in t.body:
            if isinstance(node, ast.Import | ast.ImportFrom):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                assert not any(m.split(".")[0] in ("urllib", "socket", "http", "requests", "ftplib", "huggingface_hub", "transformers", "tokenizers", "safetensors", "sacrebleu", "numpy") for m in mods), (path.name, mods)


def test_no_test_imports_the_fetch_step_or_the_data_generation_step() -> None:
    # only the fix-A tests may import them, and only to run their pure helpers on synthetic files (never ``_download`` and never ``run``); every other test file still may not
    for path in sorted((ROOT / "tests").glob("test_p10s2_*.py")):
        if path.name.startswith("test_p10s2_fixA_"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names]
                assert not (node.module == "studies.p10s2" and any(n in ("fetch", "datagen") for n in names)), path.name
                assert node.module not in ("studies.p10s2.fetch", "studies.p10s2.datagen"), path.name
            if isinstance(node, ast.Import):
                assert not any(a.name in ("studies.p10s2.fetch", "studies.p10s2.datagen") for a in node.names), path.name


def test_the_requirements_file_is_the_resolved_hashed_set_of_the_eight_pins() -> None:
    text = (ROOT / "studies/p10s2/requirements-datagen.txt").read_text()
    head = [ln for ln in text.splitlines() if ln.startswith("#")]
    body = "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))
    pins = re.findall(r"^([A-Za-z0-9_.\-]+)==([^\s\\]+)", body, flags=re.MULTILINE)
    assert len(pins) == 28 and not {"torch", "pyarrow"} & {n.lower() for n, _ in pins}  # 28 packages, none of the lock's heavy ones
    assert dict(pins)["transformers"] == "4.57.1" and dict(pins)["numpy"] == "2.3.3" and dict(pins)["sacrebleu"] == "2.5.1"
    assert body.count("--hash=sha256:") >= 28 and "--with-requirements" not in text and "PENDING" not in text and "NOT INSTALLED" not in text
    joined = "\n".join(head)
    assert "--generate-hashes --python-version 3.12 --exclude-newer 2026-11-01T00:00:00Z" in joined and "2026-11-15" in joined and "Nothing is installed by this file alone" in joined and "30 GB" not in joined
    with tempfile.TemporaryDirectory() as d:
        assert not any(Path(d).iterdir())
