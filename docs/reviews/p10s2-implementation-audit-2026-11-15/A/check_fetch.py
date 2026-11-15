"""Audit A, check 6: pinned identities of fetch_guard.py against the ADR text character for character; the manifest validator probed with
crafted manifests (no network); the weights-only loader probed with a malicious pickle written to a scratch directory (its payload is a
harmless print, never executed if the guard holds). Written by the auditor (Claude Opus 5.5). Run from the pinned tree:  <python> <this file> <scratch dir>
"""

import json
import pickle
import re
import sys
from pathlib import Path

PIN = Path.cwd()
SCR = Path(sys.argv[1])
SCR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import fetch_guard as g  # noqa: E402

adr = (PIN / "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md").read_text()
out: list[str] = []


def say(s: str) -> None:
    out.append(s)
    print(s)


# --- identities ----------------------------------------------------------------------------------------------------------------------------
revs = dict(re.findall(r"`((?:Helsinki-NLP|HuggingFaceTB)/[\w.-]+)` @ `([0-9a-f]{40})`", adr))
say(f"[ADR] repositories and 40-hex revisions found: {revs}")
for name, (repo, rev) in (("TEACHER_A", g.TEACHER_A), ("TEACHER_B", g.TEACHER_B), ("STUDENT", g.STUDENT), ("FALLBACK", g.FALLBACK)):
    say(f"[rev] {name}: code {repo}@{rev}; ADR {revs.get(repo)}; equal: {revs.get(repo) == rev}")
shas = re.findall(r"`(pytorch_model\.bin|model\.safetensors)`, ([\d,]+) B, SHA-256 `([0-9a-f]{64})`", adr)
say(f"[ADR] weight files with size and SHA-256: {len(shas)}")
fb = re.search(r"`pytorch_model\.bin` ([\d,]+) B, SHA-256 `([0-9a-f]{64})`", adr)
adr_large = {
    "student/model.safetensors": next((s, int(b.replace(",", ""))) for f, b, s in shas if f == "model.safetensors"),
    "teacher_a/pytorch_model.bin": [(s, int(b.replace(",", ""))) for f, b, s in shas if f == "pytorch_model.bin"][0],
    "teacher_b/pytorch_model.bin": [(s, int(b.replace(",", ""))) for f, b, s in shas if f == "pytorch_model.bin"][1],
    "fallback/pytorch_model.bin": (fb.group(2), int(fb.group(1).replace(",", ""))),
}
for k, v in adr_large.items():
    say(f"[large] {k}: ADR {v[0]} {v[1]}; code {g.LARGE[k][0]} {g.LARGE[k][1]}; equal: {tuple(g.LARGE[k]) == v}")
row4 = dict((p, int(b.replace(",", ""))) for p, b in re.findall(r"`((?:eng|deu|fra|spa)/[\w-]+\.tsv\.bz2)` \(([\d,]+) B\)", adr))
row4.update({p: int(b.replace(",", "")) for p, b in re.findall(r"`((?:deu|fra)/[\w-]+_links\.tsv\.bz2)`[^(]*?\(([\d,]+) B", adr)})
sym = re.search(r"listed sizes differ slightly \(([\d,]+) B and ([\d,]+) B\)", adr)
row4["deu/deu-eng_links.tsv.bz2"] = int(sym.group(1).replace(",", ""))
row4["fra/fra-eng_links.tsv.bz2"] = int(sym.group(2).replace(",", ""))
code_t = {rel: size for rel, size in [*g.TATOEBA_FILES.values(), *g.FALLBACK_DATA.values()]}
say(f"[tatoeba] ADR files {sorted(row4)}")
say(f"[tatoeba] code files equal to ADR files with sizes: {code_t == row4}; differences: { {k: (row4.get(k), code_t.get(k)) for k in set(row4) | set(code_t) if row4.get(k) != code_t.get(k)} }")
say(f"[files] Marian files {g.MARIAN_FILES}; student files {g.STUDENT_FILES}")
adr_row1 = re.search(r"\| 1 \| Teacher A \|[^|]*\| ([^|]+) \|", adr).group(1)
adr_row3 = re.search(r"\| 3 \| Student \|[^|]*\| ([^|]+) \|", adr).group(1)
say(f"[files] row 1 equal: {re.findall(r'`([^`]+)`', adr_row1) == ['pytorch_model.bin', *g.MARIAN_FILES]}; row 3 equal: {re.findall(r'`([^`]+)`', adr_row3) == ['model.safetensors', *g.STUDENT_FILES]}")
tot = sum(v[1] for k, v in adr_large.items() if not k.startswith("fallback")) + sum(v for k, v in row4.items() if not k.startswith("spa") and "spa" not in k)
say(f"[sizes] large primary weights + Tatoeba incl. link files = {tot} B ({tot / 1e6:.1f} MB) of the 1.5 GB cap (small files not counted)")
say(f"[urls] student URL example: {[s.url for s in g.sources() if s.name == 'student/model.safetensors'][0]}")

# --- manifest validator probes ----------------------------------------------------------------------------------------------------------
def probe(label: str, m: dict) -> None:
    try:
        files = g.validate_manifest(m)
        say(f"[manifest] {label}: ACCEPTED ({len(files)} files)")
    except g.FetchRefused as e:
        say(f"[manifest] {label}: refused - {e}")


base = g.build_manifest()
probe("build_manifest() as written (small files carry no digest)", base)
m = json.loads(json.dumps(base))
for f in m["files"]:
    if f["sha256"] is None and f["kind"] == "model-small":
        f["git_sha1"] = "0" * 40  # an arbitrary string: nothing ever compares it
probe("small files given an arbitrary git_sha1 string", m)
m2 = json.loads(json.dumps(m))
for f in m2["files"]:
    if f["name"] == "teacher_a/pytorch_model.bin":
        f["sha256"] = None
        f["git_sha1"] = "deadbeef"
probe("large pickle file with sha256 removed and an arbitrary git_sha1", m2)
m3 = json.loads(json.dumps(m))
m3["files"] = [f for f in m3["files"] if f["kind"] == "tatoeba"]
for f in m3["files"]:
    f["size"] = None
probe("Tatoeba only, sizes removed (cap total 0)", m3)
m4 = json.loads(json.dumps(m))
m4["files"][0]["url"] = m4["files"][0]["url"].replace("6183067f", "main0000")
probe("teacher URL changed", m4)
m5 = json.loads(json.dumps(m))
m5["files"].append({"name": "student/pytorch_model.bin", "url": "https://huggingface.co/x", "sha256": None, "size": 1, "kind": "model-large"})
probe("unapproved file appended", m5)
m6 = g.build_manifest(fallback_human_decision="any text at all")
for f in m6["files"]:
    if f["kind"] in ("model-small", "fallback-model") and not f["sha256"]:
        f["git_sha1"] = "0" * 40
probe("fallback with an arbitrary decision string", m6)
say(f"[manifest] the fallback manifest re-lists the primary Tatoeba files (a later weekly export would overwrite the frozen ones at the same path): {[f['name'] for f in m6['files'] if f['kind'] == 'tatoeba'][:3]} ...")
m7 = json.loads(json.dumps(m))
for f in m7["files"]:
    f["kind"] = "tatoeba"
probe("every entry's kind set to 'tatoeba' by the manifest (run() trusts the manifest's kind)", m7)

# --- weights-only loading of a malicious pickle -----------------------------------------------------------------------------------------
class Evil:
    def __reduce__(self):  # noqa: D105
        return (print, ("PAYLOAD EXECUTED",))


bad = SCR / "evil.bin"
with bad.open("wb") as fh:
    pickle.dump({"w": Evil()}, fh)
digest = g.sha256_file(bad)
try:
    g.load_pickle_weights(bad, digest)
    say("[pickle] malicious pickle LOADED (guard failed)")
except Exception as e:  # noqa: BLE001
    say(f"[pickle] malicious pickle refused by weights_only: {type(e).__name__}")
try:
    g.load_pickle_weights(bad, "0" * 64)
except g.FetchRefused as e:
    say(f"[pickle] wrong digest refused before unpickling: {str(e)[:60]}...")
bad.unlink()
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
