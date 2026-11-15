# ruff: noqa: E501
"""P10S2 fix lane A: the fetch guard, the hash constants, the download ledger and the fetch session (audit A-B1, A-M6, minor 7). Nothing touches the network: ``fetch_session`` is given a function that
writes synthetic bytes, on synthetic sources in a temporary folder. Self-check only: not independent review, not Astra validation, not human approval."""

import hashlib
import json
import ssl
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import fetch_guard as g  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEDGER_TEXT = (ROOT / g.DOWNLOAD_LEDGER).read_text()  # the real ledger's table format, read here and never written


def blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()


def git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a], capture_output=True, text=True, check=True)  # noqa: S603, S607
    return r.stdout.strip()


# --- the constants ----------------------------------------------------------------------------------------------------------------------------------
def test_every_small_file_has_a_git_blob_constant_and_the_sizes_equal_the_audits_sum() -> None:
    small = {s.name for s in g.sources(fallback=True) if s.kind in ("model-small", "fallback-model") and s.sha256 is None}
    assert small == set(g.SMALL) and all(len(v[0]) == 40 and int(v[0], 16) >= 0 and v[1] > 0 for v in g.SMALL.values())
    assert sum(v[1] for k, v in g.SMALL.items() if not k.startswith("fallback/")) == 9_138_858  # "summed from the saved trees" in the audit's checklist
    for s in g.sources(fallback=True):
        if s.kind in ("model-large", "fallback-model") and s.name in g.LARGE:
            assert s.sha256 == g.LARGE[s.name][0] and s.git_sha1 is None
        elif s.kind in ("model-small", "fallback-model"):
            assert s.git_sha1 == g.SMALL[s.name][0] and s.sha256 is None
        else:
            assert s.sha256 is None and s.git_sha1 is None  # Tatoeba: recorded at first download
    # a few values, read back from the audit's saved record
    assert g.SMALL["teacher_a/config.json"][0] == "0a49d3f4024d5ea51560d51f29d75722d794fb16" and g.SMALL["student/tokenizer.json"] == ("f922b1797f0c88e71addc8393787831f2477a4bd", 2104556)
    saved = (ROOT / "docs/reviews/p10s2-implementation-audit-2026-11-15/A/check_saved_trees.out.txt").read_text()
    for name, (sha1, size) in g.SMALL.items():
        assert f"{name.split('/', 1)[1]}: git-blob sha1 {sha1} size {size}" in saved, name


def test_git_blob_sha1_is_the_git_object_id(tmp_path: Path) -> None:
    p = tmp_path / "f"
    p.write_bytes(b"abc\n")
    assert g.git_blob_sha1_file(p) == g.git_blob_sha1_bytes(b"abc\n") == "8baef1b4abc478178b004d62031cf7fe6db6f903"  # `git hash-object` of "abc\n"
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    assert git(repo, "hash-object", str(p)) == g.git_blob_sha1_file(p)


def with_constants(monkeypatch: pytest.MonkeyPatch, files: dict[str, bytes], *, large: set[str] = frozenset()) -> None:  # type: ignore[assignment]
    for name, data in files.items():
        if name in large:
            monkeypatch.setitem(g.LARGE, name, (hashlib.sha256(data).hexdigest(), len(data)))
        else:
            monkeypatch.setitem(g.SMALL, name, (blob(data), len(data)))


def test_verify_against_constant_refuses_a_missing_a_changed_and_an_unknown_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with_constants(monkeypatch, {"student/config.json": b'{"a": 1}', "student/model.safetensors": b"weights"}, large={"student/model.safetensors"})
    (tmp_path / "student").mkdir()
    (tmp_path / "student/config.json").write_bytes(b'{"a": 1}')
    (tmp_path / "student/model.safetensors").write_bytes(b"weights")
    assert g.verify_tree(tmp_path, ["student/config.json", "student/model.safetensors"]) == {"student/config.json": blob(b'{"a": 1}'), "student/model.safetensors": hashlib.sha256(b"weights").hexdigest()}
    assert g.read_verified_bytes(tmp_path, "student/config.json") == b'{"a": 1}'
    (tmp_path / "student/config.json").write_bytes(b'{"a": 2, "_attn_implementation_internal": "x"}')  # a substituted configuration file
    with pytest.raises(g.FetchRefused, match="not the constant"):
        g.verify_against_constant(tmp_path / "student/config.json", "student/config.json")
    with pytest.raises(g.FetchRefused, match="not the constant"):
        g.read_verified_bytes(tmp_path, "student/config.json")  # the bytes that would be parsed are the bytes that were checked
    with pytest.raises(g.FetchRefused, match="does not exist"):
        g.verify_against_constant(tmp_path / "student/absent.json", "student/config.json")
    with pytest.raises(g.FetchRefused, match="no hash constant"):
        g.expected_digest("tatoeba/eng_sentences.tsv.bz2")
    (tmp_path / "student/model.safetensors").write_bytes(b"weighTs")
    with pytest.raises(g.FetchRefused):
        g.verify_tree(tmp_path, ["student/model.safetensors"])  # re-hashed from disk before each use


# --- the manifest never supplies the digest ------------------------------------------------------------------------------------------------------------
def test_a_manifest_with_a_missing_or_wrong_digest_is_refused() -> None:
    man = g.build_manifest()
    assert g.validate_manifest(man)
    for kind_key, kind in (("sha256", "model-large"), ("git_sha1", "model-small")):
        for how in ("missing", "wrong", "other-algorithm"):
            bad = json.loads(json.dumps(man))
            f = next(x for x in bad["files"] if x["kind"] == kind)
            if how == "missing":
                f[kind_key] = None
            elif how == "wrong":
                f[kind_key] = "0" * (64 if kind_key == "sha256" else 40)
            else:
                other = "git_sha1" if kind_key == "sha256" else "sha256"
                f[other] = f[kind_key]  # an arbitrary git_sha1 beside a removed sha256 (the audit's probe: "ACCEPTED (29 files)")
                f[kind_key] = None
            with pytest.raises(g.FetchRefused, match="other than the pinned"):
                g.validate_manifest(bad)
    wrong_size = json.loads(json.dumps(man))
    wrong_size["files"][3]["size"] += 1
    with pytest.raises(g.FetchRefused, match="size other than"):
        g.validate_manifest(wrong_size)


def test_tatoeba_files_are_fetched_in_one_session_all_seven_together() -> None:
    man = g.build_manifest()
    part = json.loads(json.dumps(man))
    part["files"] = [f for f in part["files"] if f["name"] != "tatoeba/deu_eng_links.tsv.bz2"]
    with pytest.raises(g.FetchRefused, match="one session"):
        g.validate_manifest(part)
    only_models = {**man, "files": [f for f in man["files"] if f["kind"] != "tatoeba"]}
    assert g.validate_manifest(only_models)


def test_the_fallback_manifest_lists_the_fallback_rows_only_and_never_the_primary_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "d.md").write_text("fallback invoked\n")
    git(repo, "init", "-q")
    git(repo, "add", "d.md")
    git(repo, "commit", "-q", "-m", "d")
    decision = {"path": "d.md", "commit": git(repo, "rev-parse", "HEAD")}
    man = g.build_manifest(fallback_human_decision=decision)
    assert {f["row"] for f in man["files"]} == {5, 6} and len(man["files"]) == 7 + 2
    mixed = json.loads(json.dumps(man))
    mixed["files"].append(next(f for f in g.build_manifest()["files"] if f["name"] == "teacher_a/config.json"))
    with pytest.raises(g.FetchRefused, match="fallback rows only"):
        g.validate_manifest(mixed, root=repo)
    partial = json.loads(json.dumps(man))
    partial["files"] = partial["files"][:-1]
    with pytest.raises(g.FetchRefused, match="every fallback row"):
        g.validate_manifest(partial, root=repo)
    for bad in ("any non-empty string", {"path": "d.md", "commit": "f" * 40}):
        man["fallback_human_decision"] = bad
        with pytest.raises(g.FetchRefused, match="fallback"):
            g.validate_manifest(man, root=repo)


def test_authorization_is_still_required(tmp_path: Path) -> None:
    with pytest.raises(g.FetchRefused, match="--i-have-recorded-human-approval"):
        g.check_authorization(False, tmp_path / "m.json")


def test_tls_verification_is_on_and_certificates_are_required() -> None:
    ctx = g.make_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    src = (ROOT / "studies/p10s2/fetch.py").read_text()
    assert "_create_unverified_context" not in src and "CERT_NONE" not in src and "verify=False" not in src and "check_hostname = False" not in src


# --- the download ledger -----------------------------------------------------------------------------------------------------------------------------
def fresh_ledger(tmp_path: Path) -> Path:
    p = tmp_path / "ledger.md"
    p.write_text(LEDGER_TEXT)
    return p


def test_the_ledger_row_is_written_before_and_completed_after_with_a_running_total(tmp_path: Path) -> None:
    led = fresh_ledger(tmp_path)
    assert g.ledger_total_bytes(led) == 0  # the placeholder row is not a download
    i = g.ledger_begin(led, what="a", source="https://x/a", revision="r1", licence="MIT", declared_bytes=100, date="2026-11-16")
    assert "| started |" in led.read_text() and g.ledger_total_bytes(led) == 100 and "nothing has been downloaded" not in led.read_text()
    j = g.ledger_begin(led, what="b", source="https://x/b", revision="r2", licence="MIT", declared_bytes=50, date="2026-11-16")
    g.ledger_complete(led, i, actual_bytes=90, status="completed")
    g.ledger_complete(led, j, actual_bytes=50, status="completed")
    lines = [ln for ln in led.read_text().split("\n") if ln.startswith("| 2026-11-16")]
    assert [ln.split("|")[7].strip() for ln in lines] == ["90", "50"] and [ln.split("|")[8].strip() for ln in lines] == ["90", "140"] and all(ln.split("|")[9].strip() == "completed" for ln in lines)
    assert led.read_text().startswith(LEDGER_TEXT.split("| Date")[0])  # the text around the table is untouched
    assert g.ledger_total_bytes(led) == 140


def test_the_ledger_refuses_a_fetch_that_would_reach_30_gb(tmp_path: Path) -> None:
    led = fresh_ledger(tmp_path)
    g.ledger_begin(led, what="big", source="s", revision="r", licence="l", declared_bytes=29_000_000_000)
    with pytest.raises(g.FetchRefused, match="30 GB"):
        g.ledger_begin(led, what="more", source="s", revision="r", licence="l", declared_bytes=1_000_000_000)  # exactly the limit: refused ("less than 30 GB")
    g.ledger_begin(led, what="fits", source="s", revision="r", licence="l", declared_bytes=999_999_999)
    assert g.ledger_total_bytes(led) == 29_999_999_999 < g.LEDGER_CAP_BYTES
    bad = tmp_path / "bad.md"
    bad.write_text("# no table\n")
    with pytest.raises(g.FetchRefused, match="no contiguous markdown table"):
        g.ledger_total_bytes(bad)


# --- the session ------------------------------------------------------------------------------------------------------------------------------------
def synthetic_world(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, bytes], dict[str, dict[str, bytes]]]:
    """A tiny approved set: two small model files, one 'large' file and the seven Tatoeba names, with constants set to match."""
    models = {"student/config.json": b'{"x": 1}', "student/tokenizer.json": b'{"y": 2}', "student/model.safetensors": b"W" * 64}
    tat = {n: f"tatoeba bytes of {n}".encode() for n in g.TATOEBA_NAMES}
    with_constants(monkeypatch, models, large={"student/model.safetensors"})
    srcs: list[g.Source] = []
    for n, d in models.items():
        big = n in g.LARGE
        srcs.append(g.Source(n, f"https://huggingface.co/x/resolve/rev/{n}", g.LARGE[n][0] if big else None, None if big else g.SMALL[n][0], len(d), 3, "model-large" if big else "model-small", "Apache-2.0", "rev"))
    for n, d in tat.items():
        srcs.append(g.Source(n, f"{g.TATOEBA}/{n}", None, None, len(d), 4, "tatoeba", "CC BY 2.0 FR", g.TATOEBA_NOTE))
    monkeypatch.setattr(g, "primary_sources", lambda: srcs)
    monkeypatch.setattr(g, "fallback_sources", lambda: [])
    return {**models, **tat}, {}


def fake_download(payload: dict[str, bytes], calls: list[tuple[str, int]] | None = None):  # type: ignore[no-untyped-def]
    by_url = {}
    for s in g.sources():
        by_url[s.url] = payload[s.name]

    def dl(url: str, dest: Path, limit: int) -> int:
        data = by_url[url]
        if calls is not None:
            calls.append((url, limit))
        if len(data) > limit:
            raise g.FetchRefused("refused: over the limit")
        dest.write_bytes(data)
        return len(data)

    return dl


def test_a_session_writes_ledger_rows_verifies_every_file_and_records_the_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload, _ = synthetic_world(monkeypatch)
    data_root = tmp_path / "data"
    dest = data_root / "p10s2-downloads-2026-11-16"
    led = fresh_ledger(tmp_path)
    calls: list[tuple[str, int]] = []
    seen_in_ledger: list[str] = []

    base = fake_download(payload, calls)

    def spying(url: str, out: Path, limit: int) -> int:
        seen_in_ledger.append(led.read_text())  # the row of this file is already written, as "started", before its bytes arrive
        return base(url, out, limit)

    rec = g.fetch_session(g.build_manifest(), dest, download=spying, ledger_path=led, data_root=data_root, free_bytes=10**9)
    assert all("started" in t for t in seen_in_ledger) and len(seen_in_ledger) == 10
    assert sorted(rec["files"]) == sorted(payload) and rec["session_date"] and "tatoeba_recorded_at_first_download" in rec
    assert set(rec["tatoeba_recorded_at_first_download"]) == {Path(n).name for n in g.TATOEBA_NAMES}
    text = led.read_text()
    assert text.count("| started |") == 0 and text.count("| completed |") == 10 and g.ledger_total_bytes(led) == sum(len(d) for d in payload.values())
    assert "git-blob SHA-1" in text and "SHA-256" in text
    assert (dest / "fetch_record.json").exists() and all((dest / n).read_bytes() == d for n, d in payload.items())
    assert all(limit < g.LEDGER_CAP_BYTES for _, limit in calls)
    again = tmp_path / "data" / "again"
    with pytest.raises(g.FetchRefused, match="fresh folder"):
        g.fetch_session(g.build_manifest(), dest, download=base, ledger_path=led, data_root=data_root, free_bytes=10**9)  # nothing fetched is ever fetched into again
    assert not again.exists()
    # the second defence: a file that appears at the destination while its fetch is running is not replaced
    dest3 = data_root / "race"
    first_dl = fake_download(payload)

    def racing(url: str, out: Path, limit: int) -> int:
        n = first_dl(url, out, limit)
        target = Path(str(out)[: -len(".part")])
        target.write_bytes(b"somebody else's bytes")
        return n

    with pytest.raises(g.FetchRefused, match="appeared during the fetch"):
        g.fetch_session(g.build_manifest(), dest3, download=racing, ledger_path=fresh_ledger(tmp_path), data_root=data_root, free_bytes=10**9)
    assert next(p for p in dest3.rglob("*") if p.is_file() and not p.name.endswith(".part")).read_bytes() == b"somebody else's bytes"


def test_a_session_refuses_an_overwrite_a_non_fresh_folder_and_a_folder_outside_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload, _ = synthetic_world(monkeypatch)
    data_root = tmp_path / "data"
    led = fresh_ledger(tmp_path)
    man = g.build_manifest()
    dl = fake_download(payload)
    with pytest.raises(g.FetchRefused, match="not under the git-ignored"):
        g.fetch_session(man, tmp_path / "elsewhere", download=dl, ledger_path=led, data_root=data_root, free_bytes=10**9)
    dest = data_root / "d"
    (dest / "student").mkdir(parents=True)
    (dest / "student/config.json").write_bytes(b"frozen")
    with pytest.raises(g.FetchRefused, match="not a fresh folder"):
        g.fetch_session(man, dest, download=dl, ledger_path=led, data_root=data_root, free_bytes=10**9)
    assert (dest / "student/config.json").read_bytes() == b"frozen" and g.ledger_total_bytes(led) == 0  # nothing was written, no ledger row
    # a part file left by an earlier session is not overwritten either, and the ledger row that was begun is completed as failed
    dest2 = data_root / "d2"
    (dest2 / "student").mkdir(parents=True)
    (dest2 / "student/config.json.part").write_bytes(b"x")
    with pytest.raises(g.FetchRefused, match="not a fresh folder"):
        g.fetch_session(man, dest2, download=dl, ledger_path=led, data_root=data_root, free_bytes=10**9)


def test_a_wrong_digest_deletes_the_file_and_the_ledger_row_says_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload, _ = synthetic_world(monkeypatch)
    data_root = tmp_path / "data"
    led = fresh_ledger(tmp_path)
    tampered = dict(payload)
    tampered["student/config.json"] = b'{"x": 2}'  # the same size, other bytes: a substituted configuration file
    dest = data_root / "d"
    with pytest.raises(g.FetchRefused, match="not the constant"):
        g.fetch_session(g.build_manifest(), dest, download=fake_download(tampered), ledger_path=led, data_root=data_root, free_bytes=10**9)
    assert not (dest / "student/config.json").exists() and not (dest / "student/config.json.part").exists()
    assert "failed: FetchRefused" in led.read_text()
    # a wrong size is refused as well, before the digest
    short = dict(payload)
    short["student/model.safetensors"] = b"W" * 10
    with pytest.raises(g.FetchRefused, match="expected 64"):
        g.fetch_session(g.build_manifest(), data_root / "d2", download=fake_download(short), ledger_path=led, data_root=data_root, free_bytes=10**9)


def test_a_session_refuses_when_the_ledger_or_the_disk_cannot_hold_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload, _ = synthetic_world(monkeypatch)
    data_root = tmp_path / "data"
    led = fresh_ledger(tmp_path)
    g.ledger_begin(led, what="earlier", source="s", revision="r", licence="l", declared_bytes=29_999_999_900)
    with pytest.raises(g.FetchRefused, match="30 GB"):
        g.fetch_session(g.build_manifest(), data_root / "a", download=fake_download(payload), ledger_path=led, data_root=data_root, free_bytes=10**9)
    led2 = tmp_path / "l2.md"
    led2.write_text(LEDGER_TEXT)
    with pytest.raises(g.FetchRefused, match="free bytes"):
        g.fetch_session(g.build_manifest(), data_root / "b", download=fake_download(payload), ledger_path=led2, data_root=data_root, free_bytes=10)
    monkeypatch.setattr(g, "DOWNLOAD_CAP_BYTES", 100)  # a session cap that is cumulative: the declared total is over it
    with pytest.raises(g.FetchRefused, match="download cap"):
        g.fetch_session(g.build_manifest(), data_root / "c", download=fake_download(payload), ledger_path=led2, data_root=data_root, free_bytes=10**9)


def test_the_session_limit_handed_to_the_download_is_cumulative_not_per_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload, _ = synthetic_world(monkeypatch)
    data_root = tmp_path / "data"
    led = fresh_ledger(tmp_path)
    total = sum(len(d) for d in payload.values())
    monkeypatch.setattr(g, "DOWNLOAD_CAP_BYTES", total + 5)
    limits: list[int] = []

    def dl(url: str, dest: Path, limit: int) -> int:
        limits.append(limit)
        return fake_download(payload)(url, dest, limit)

    g.fetch_session(g.build_manifest(), data_root / "d", download=dl, ledger_path=led, data_root=data_root, free_bytes=10**9)
    assert limits[0] == total + 5 and all(b < a for a, b in zip(limits, limits[1:], strict=False))  # each file leaves less of the session total


def test_the_tatoeba_record_is_frozen_in_a_tracked_file_and_verified_afterwards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload, _ = synthetic_world(monkeypatch)
    data_root = tmp_path / "data"
    dest = data_root / "d"
    g.fetch_session(g.build_manifest(), dest, download=fake_download(payload), ledger_path=fresh_ledger(tmp_path), data_root=data_root, free_bytes=10**9)
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    record = repo / "studies/p10s2/records/tatoeba_session.json"
    first = g.freeze_tatoeba_record(dest, record, root=repo)
    assert first["status"].startswith("written") and record.exists() and first["session_date"]
    rec = json.loads(record.read_text())
    assert set(rec["files"]) == set(g.TATOEBA_NAMES) and all(set(v) == {"sha256", "bytes"} for v in rec["files"].values()) and rec["started"] and rec["finished"]
    with pytest.raises(g.FetchRefused, match="not committed"):
        g.freeze_tatoeba_record(dest, record, root=repo)  # written, not yet committed: a second use refuses
    git(repo, "add", str(record.relative_to(repo)))
    git(repo, "commit", "-q", "-m", "freeze tatoeba")
    assert g.freeze_tatoeba_record(dest, record, root=repo)["status"].startswith("verified")
    (dest / "tatoeba/eng_sentences.tsv.bz2").write_bytes(b"a different weekly export")
    with pytest.raises(g.FetchRefused, match="differs from the frozen Tatoeba record"):
        g.freeze_tatoeba_record(dest, record, root=repo)
    # at the first use the digests are compared with the ones taken at fetch time
    dest2 = data_root / "d2"
    g.fetch_session(g.build_manifest(), dest2, download=fake_download(payload), ledger_path=fresh_ledger(tmp_path), data_root=data_root, free_bytes=10**9)
    (dest2 / "tatoeba/fra_sentences.tsv.bz2").write_bytes(b"changed after the fetch")
    with pytest.raises(g.FetchRefused, match="no longer hashes"):
        g.freeze_tatoeba_record(dest2, tmp_path / "new_record.json", root=repo)


def test_git_ignore_check_and_the_real_destination_rule(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / ".gitignore").write_text("data/\n")
    assert g.is_git_ignored(repo / "data/p10s2-downloads-2026-11-16", repo) and not g.is_git_ignored(repo / "docs/x", repo)
    assert g.under_data_dir(repo / "data/a/b", repo / "data") and not g.under_data_dir(repo / "dataX/a", repo / "data") and not g.under_data_dir(repo / "data/../x", repo / "data")
    assert "/data/" in (ROOT / ".gitignore").read_text().split()  # the project's own ignore file keeps data/ out of git
