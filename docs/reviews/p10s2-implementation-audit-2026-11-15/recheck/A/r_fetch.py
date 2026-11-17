"""Re-check A, tasks 2 and 3: the fetch-and-verify path on synthetic files, with an injected download function (NO network).
The hash constants of fetch_guard are swapped, in memory only, for the digests of synthetic payloads so that a whole session can run; the
real constants are compared with the saved Hub trees separately (r_hash_constants.py). Probes: a manifest with a missing or wrong digest;
the ledger row written before each file and completed after it; a tampered config.json carrying an `auto_map` / `_attn_implementation_internal`
field; overwrite and fresh-folder refusals; the 30 GB refusal; the fallback decision and the fallback manifest; the frozen Tatoeba record;
re-hash before use; a malicious pickle; the requirements check; TLS defaults of this interpreter. Written by the re-check auditor (Claude Opus 5.5).
Run:  <python> -I <this file> <pinned tree> <scratch dir>
"""

import hashlib
import json
import pickle
import shutil
import ssl
import subprocess
import sys
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
SCR = Path(sys.argv[2]).resolve()
if SCR.exists():
    shutil.rmtree(SCR)
SCR.mkdir(parents=True)
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import datagen  # noqa: E402
from studies.p10s2 import fetch_guard as g  # noqa: E402

OUT: list[str] = []


def say(s: str) -> None:
    OUT.append(s)
    print(s)


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


# --- synthetic payloads and in-memory constants --------------------------------------------------------------------------------------------
ORIG_LARGE, ORIG_SMALL, ORIG_T = dict(g.LARGE), dict(g.SMALL), dict(g.TATOEBA_FILES)
payload: dict[str, bytes] = {}
for name in list(g.LARGE):
    b = f"large weights {name}".encode() * 3
    payload[name] = b
    g.LARGE[name] = (hashlib.sha256(b).hexdigest(), len(b))
for name in list(g.SMALL):
    b = json.dumps({"model_type": "marian", "file": name}).encode() if name.endswith("config.json") else f"small {name}".encode()
    payload[name] = b
    g.SMALL[name] = (blob(b), len(b))
for k, (rel, _size) in list(g.TATOEBA_FILES.items()):
    b = f"tatoeba {k} weekly export".encode()
    payload[f"tatoeba/{k}.tsv.bz2"] = b
    g.TATOEBA_FILES[k] = (rel, len(b))
for k, (rel, _size) in list(g.FALLBACK_DATA.items()):
    b = f"fallback {k}".encode()
    payload[f"tatoeba/{k}.tsv.bz2"] = b
    g.FALLBACK_DATA[k] = (rel, len(b))
URL2NAME = {s.url: s.name for s in g.sources(fallback=True)}

# a scratch git repository standing in for the repository root (for the fallback decision and the tracked Tatoeba record)
ROOT = SCR / "repo"
ROOT.mkdir()
GIT = ["git", "-C", str(ROOT), "-c", "user.name=auditor", "-c", "user.email=auditor@invalid", "-c", "commit.gpgsign=false"]
subprocess.run([*GIT, "init", "-q"], check=True)
(ROOT / ".gitignore").write_text("/data/\n")
(ROOT / "README").write_text("scratch\n")
subprocess.run([*GIT, "add", "."], check=True)
subprocess.run([*GIT, "commit", "-q", "-m", "init"], check=True)
DATA = ROOT / "data"
DATA.mkdir()


def ledger(path: Path, total: int = 0) -> Path:
    head = "# ledger\n\n| " + " | ".join(g.LEDGER_COLUMNS) + " |\n|" + "---|" * len(g.LEDGER_COLUMNS) + "\n"
    row = "| — | — | nothing has been downloaded | — | — | — | 0 | 0 | — |\n" if not total else f"| 2026-11-01 | P10-S0 | earlier | x | x | x | {total} | {total} | completed |\n"
    path.write_text(head + row)
    return path


def downloader(tamper: dict[str, bytes] | None = None, spy: list | None = None, led: Path | None = None):
    def dl(url: str, part: Path, limit: int) -> int:
        name = URL2NAME[url]
        if spy is not None and led is not None:
            rows = g._read_ledger(led)[1]
            spy.append((name, rows[-1][2], rows[-1][8]))
        b = (tamper or {}).get(name, payload[name])
        if len(b) > limit:
            raise g.FetchRefused("limit")
        with part.open("xb") as fh:
            fh.write(b)
        return len(b)
    return dl


def attempt(label: str, fn) -> None:
    try:
        r = fn()
        say(f"[{label}] ACCEPTED" + (f" ({r})" if r is not None and not isinstance(r, dict) else ""))
    except Exception as e:  # noqa: BLE001
        say(f"[{label}] refused: {type(e).__name__}: {str(e)[:170]}")


# --- manifests ------------------------------------------------------------------------------------------------------------------------------
base = g.build_manifest()
say(f"[manifest] build_manifest(): {len(base['files'])} files; every model file carries its constant: {all((f['sha256'] or f['git_sha1']) for f in base['files'] if not f['name'].startswith('tatoeba'))}")
attempt("validate build_manifest()", lambda: len(g.validate_manifest(base, root=ROOT)))
m = json.loads(json.dumps(base)); [f.update(git_sha1=None) for f in m["files"] if f["name"] == "teacher_a/config.json"]
attempt("manifest: small file digest missing", lambda: g.validate_manifest(m, root=ROOT))
m = json.loads(json.dumps(base)); [f.update(git_sha1="0" * 40) for f in m["files"] if f["name"] == "student/tokenizer.json"]
attempt("manifest: small file digest wrong", lambda: g.validate_manifest(m, root=ROOT))
m = json.loads(json.dumps(base)); [f.update(sha256=None, git_sha1="deadbeef") for f in m["files"] if f["name"] == "teacher_a/pytorch_model.bin"]
attempt("manifest: large file SHA-256 removed, arbitrary git_sha1", lambda: g.validate_manifest(m, root=ROOT))
m = json.loads(json.dumps(base)); m["files"].append({"name": "student/pytorch_model.bin", "url": "https://huggingface.co/x", "sha256": None, "git_sha1": None, "size": 1})
attempt("manifest: unapproved file appended", lambda: g.validate_manifest(m, root=ROOT))
m = json.loads(json.dumps(base)); m["files"] = [f for f in m["files"] if f["name"] != "tatoeba/fra_eng_links.tsv.bz2"]
attempt("manifest: six of the seven Tatoeba files", lambda: g.validate_manifest(m, root=ROOT))
m = json.loads(json.dumps(base)); [f.update(url=f["url"].replace("resolve/6183067f769a302e3861815543b9f312c71b0ca4", "resolve/main")) for f in m["files"] if f["name"].startswith("teacher_a/")]
attempt("manifest: teacher A URL with resolve/main", lambda: g.validate_manifest(m, root=ROOT))
m = json.loads(json.dumps(base)); [f.update(kind="tatoeba") for f in m["files"]]
attempt("manifest: every entry relabelled kind=tatoeba (the session reads kind from the constants, not the manifest)", lambda: len(g.validate_manifest(m, root=ROOT)))
say(f"[urls] every model URL is resolve/<40-hex pinned revision>/<file>: {all('/resolve/' + r + '/' in s.url for s in g.sources(fallback=True) if not s.name.startswith('tatoeba') for r in [s.revision])}; every URL https: {all(s.url.startswith('https://') for s in g.sources(fallback=True))}")

# --- a full primary session with a spy on the ledger ---------------------------------------------------------------------------------------
led = ledger(SCR / "LEDGER.md")
spy: list = []
dest = DATA / "p10s2-downloads-2026-11-15"
rec = g.fetch_session(base, dest, download=downloader(spy=spy, led=led), ledger_path=led, data_root=DATA, root=ROOT, free_bytes=10**9)
before_ok = all(w == n and st == "started" for n, w, st in spy)
rows = g._read_ledger(led)[1]
say(f"[session] files fetched {len(rec['files'])}; ledger row 'started' for the very file before each download call: {before_ok} ({len(spy)} calls); rows now {len(rows)}, all 'completed': {all(r[8] == 'completed' for r in rows)}; running total of the last row {rows[-1][7]} == sum of bytes {sum(int(r[6]) for r in rows)}")
say(f"[session] Tatoeba digests recorded at first download: {len(rec['tatoeba_recorded_at_first_download'])}; fetch_record.json written: {(dest / 'fetch_record.json').is_file()}")
attempt("second session into the same (non-fresh) folder", lambda: g.fetch_session(base, dest, download=downloader(), ledger_path=led, data_root=DATA, root=ROOT, free_bytes=10**9))
pre = DATA / "pre"; (pre / "teacher_a").mkdir(parents=True)
attempt("destination outside data/", lambda: g.fetch_session(base, SCR / "elsewhere", download=downloader(), ledger_path=led, data_root=DATA, root=ROOT, free_bytes=10**9))

# --- tampered small file: auto_map / _attn_implementation_internal --------------------------------------------------------------------------
evil_cfg = json.dumps({"model_type": "marian", "auto_map": {"AutoModel": "evil.EvilModel"}, "_attn_implementation_internal": "evil/kernel"}).encode()
led2 = ledger(SCR / "LEDGER2.md")
d2 = DATA / "tampered"
attempt("session where teacher_a/config.json arrives with auto_map and _attn_implementation_internal", lambda: g.fetch_session(base, d2, download=downloader({"teacher_a/config.json": evil_cfg}), ledger_path=led2, data_root=DATA, root=ROOT, free_bytes=10**9))
rows2 = g._read_ledger(led2)[1]
say(f"   after the refusal: tampered file on disk: {(d2 / 'teacher_a/config.json').exists()}; .part left: {(d2 / 'teacher_a/config.json.part').exists()}; last ledger row: {rows2[-1][2]} / {rows2[-1][8]} / bytes {rows2[-1][6]}")
same = json.dumps({"model_type": "marian", "auto_map": "x"}).encode()
same = (same + b" " * 200)[: len(payload["teacher_a/config.json"])] if len(same) <= len(payload["teacher_a/config.json"]) else same
say(f"   same-size tamper possible: {len(same) == len(payload['teacher_a/config.json'])}")
attempt("session where teacher_a/config.json arrives SAME SIZE with an auto_map field", lambda: g.fetch_session(base, DATA / "tampered2", download=downloader({"teacher_a/config.json": same}), ledger_path=ledger(SCR / "LEDGER5.md"), data_root=DATA, root=ROOT, free_bytes=10**9))
# tampering on disk after a good fetch: the re-hash before use refuses it
good = dest / "teacher_b/config.json"
orig = good.read_bytes()
good.write_bytes(evil_cfg)
attempt("datagen.verify_downloads after config.json was replaced on disk", lambda: datagen.verify_downloads(dest, ROOT / "studies/p10s2/records/tatoeba_session.json", root=ROOT))
attempt("fetch_guard.read_verified_bytes of the replaced config.json", lambda: g.read_verified_bytes(dest, "teacher_b/config.json"))
good.write_bytes(orig)

# --- the 30 GB refusal ----------------------------------------------------------------------------------------------------------------------
calls: list = []
led3 = ledger(SCR / "LEDGER3.md", total=30_000_000_000 - 1000)
attempt("session with the ledger 1,000 bytes below 30 GB (the synthetic session declares 1,447 bytes)", lambda: g.fetch_session(base, DATA / "big", download=lambda u, p, l: calls.append(u) or 0, ledger_path=led3, data_root=DATA, root=ROOT, free_bytes=10**12))
say(f"   download calls made before the refusal: {len(calls)}; ledger rows after: {len(g._read_ledger(led3)[1])}")
attempt("ledger_begin of 1 byte at 29,999,999,999", lambda: g.ledger_begin(ledger(SCR / "LEDGER4.md", total=29_999_999_999), what="x", source="x", revision="x", licence="x", declared_bytes=1))

# --- the fallback --------------------------------------------------------------------------------------------------------------------------
attempt("fallback manifest with a free-text decision", lambda: g.validate_manifest(g.build_manifest(fallback_human_decision="the human lead said yes"), root=ROOT))
attempt("fallback decision naming an uncommitted record", lambda: g.validate_manifest(g.build_manifest(fallback_human_decision={"path": "docs/decision.md", "commit": "0" * 40}), root=ROOT))
(ROOT / "docs").mkdir()
(ROOT / "docs/decision.md").write_text("fallback invoked\n")
subprocess.run([*GIT, "add", "docs/decision.md"], check=True)
subprocess.run([*GIT, "commit", "-q", "-m", "decision"], check=True)
head = subprocess.run([*GIT, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
fbm = g.build_manifest(fallback_human_decision={"path": "docs/decision.md", "commit": head})
say(f"[fallback] manifest names: {sorted(f['name'] for f in fbm['files'])}")
attempt("fallback manifest with a committed decision", lambda: len(g.validate_manifest(fbm, root=ROOT)))
mixed = json.loads(json.dumps(fbm)); mixed["files"] += [f for f in base["files"] if f["name"].startswith("tatoeba/eng_")]
attempt("fallback manifest that also lists a primary Tatoeba file", lambda: g.validate_manifest(mixed, root=ROOT))
attempt("fallback session into the primary folder", lambda: g.fetch_session(fbm, dest, download=downloader(), ledger_path=led, data_root=DATA, root=ROOT, free_bytes=10**9))
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (dest / "tatoeba").iterdir()}
g.fetch_session(fbm, DATA / "p10s2-fallback-2026-11-22", download=downloader(), ledger_path=led, data_root=DATA, root=ROOT, free_bytes=10**9)
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (dest / "tatoeba").iterdir()}
say(f"[fallback] fallback session into a fresh folder: primary Tatoeba files unchanged: {before == after}")

# --- the frozen Tatoeba record --------------------------------------------------------------------------------------------------------------
recp = ROOT / "studies/p10s2/records/tatoeba_session.json"
r1 = g.freeze_tatoeba_record(dest, recp, root=ROOT)
say(f"[tatoeba record] first use writes it: status {r1['status']!r}; files {len(r1['files'])}")
attempt("second use while the record is not committed", lambda: g.freeze_tatoeba_record(dest, recp, root=ROOT))
subprocess.run([*GIT, "add", "studies/p10s2/records/tatoeba_session.json"], check=True)
subprocess.run([*GIT, "commit", "-q", "-m", "freeze tatoeba"], check=True)
attempt("use after commit", lambda: g.freeze_tatoeba_record(dest, recp, root=ROOT)["status"])
t = dest / "tatoeba/eng_sentences.tsv.bz2"
ob = t.read_bytes()
t.write_bytes(ob + b"x")
attempt("use after one Tatoeba file changed on disk", lambda: g.freeze_tatoeba_record(dest, recp, root=ROOT))
t.write_bytes(ob)
other = DATA / "second-weekly"
g.fetch_session(base, other, download=downloader({"tatoeba/eng_sentences.tsv.bz2": b"a later weekly export"}), ledger_path=led, data_root=DATA, root=ROOT, free_bytes=10**9)
say("[tatoeba] a second primary session (a later weekly export) into another fresh folder is ACCEPTED by fetch_session (nothing in the ledger stops it)")
attempt("the committed record against that second folder", lambda: g.freeze_tatoeba_record(other, recp, root=ROOT))

# --- weights-only load of a malicious pickle -------------------------------------------------------------------------------------------------
class Evil:
    def __reduce__(self):  # noqa: D105
        return (print, ("PAYLOAD EXECUTED",))


bad = SCR / "evil.bin"
bad.write_bytes(pickle.dumps({"w": Evil()}))
attempt("load_pickle_weights(malicious pickle, its own digest)", lambda: g.load_pickle_weights(bad, g.sha256_file(bad)))
attempt("load_pickle_weights(malicious pickle, a wrong digest)", lambda: g.load_pickle_weights(bad, "0" * 64))
bad.unlink()

# --- the requirements check ------------------------------------------------------------------------------------------------------------------
req = (PIN / "studies/p10s2/requirements-datagen.txt").read_text()
say(f"[requirements] pinned file at fc08681: unhashed pins = {datagen.unhashed_requirements(req)}")
hashed = "transformers==4.57.1 \\\n    --hash=sha256:" + "a" * 64 + "\n    # via -r x\nnumpy==2.3.3 \\\n    --hash=sha256:" + "b" * 64 + " \\\n    --hash=sha256:" + "c" * 64 + "\n"
say(f"[requirements] a uv-compile-style hashed file: unhashed = {datagen.unhashed_requirements(hashed)}")
sneaky = hashed + "--extra-index-url http://example.invalid/simple\n-e ./local_pkg\n-r other-unhashed.txt\n"
say(f"[requirements] hashed file plus '--extra-index-url http://...', '-e ./local_pkg', '-r other.txt' lines: unhashed = {datagen.unhashed_requirements(sneaky)} (option lines are skipped by the check)")

# --- TLS defaults of this interpreter (offline) ---------------------------------------------------------------------------------------------
ctx = g.make_ssl_context()
paths = ssl.get_default_verify_paths()
say(f"[tls] make_ssl_context: verify_mode CERT_REQUIRED {ctx.verify_mode == ssl.CERT_REQUIRED}, check_hostname {ctx.check_hostname}; CA certificates loaded into the default context: {ctx.cert_store_stats()}; default cafile {paths.cafile} exists={bool(paths.cafile) and Path(paths.cafile).exists()}; capath {paths.capath}; OpenSSL {ssl.OPENSSL_VERSION}")

# restore the real constants (not needed after exit; for clarity)
g.LARGE.clear(); g.LARGE.update(ORIG_LARGE); g.SMALL.clear(); g.SMALL.update(ORIG_SMALL); g.TATOEBA_FILES.clear(); g.TATOEBA_FILES.update(ORIG_T)
Path(__file__).with_suffix(".out.txt").write_text("\n".join(OUT) + "\n")
shutil.rmtree(SCR)
