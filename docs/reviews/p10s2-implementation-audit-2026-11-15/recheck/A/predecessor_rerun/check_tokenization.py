"""Audit A, check 5: segment conventions of ADR-0022 section 14.2 step 4 probed on the synthetic tokenizer stand-in: NFC before tokenization,
read positions recomputed independently from token bytes, test (a) on prompts, the sentence parser on Unicode line separators, and the
router's generator use (section 9: a fresh +3 generator after the initialization). Written by the auditor (Claude Opus 5.5).
Run from the pinned tree:  <python> <this file>
"""

import bz2
import sys
import unicodedata
from pathlib import Path

PIN = Path.cwd()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import core, data, tokenization as T  # noqa: E402

out: list[str] = []


def say(s: str) -> None:
    out.append(s)
    print(s)


sample = "English: the cafe is open now\nGerman: das cafe ist offen\nFrench: le café est ouvert\n" * 20
tok = T.SyntheticTokenizer(sample, merges=80)
vocab = {w: i for i, w in enumerate(["the", "café", "is", "open", "now", "tom", "cant", "swim"])}
nfc = "the café is open now"
nfd = unicodedata.normalize("NFD", nfc)
a = T.build_example(tok, "A", nfc, None, vocab, "k1")
b = T.build_example(tok, "A", nfd, None, vocab, "k2")
say(f"[NFC] same normalized key: {data.normalize(nfc) == data.normalize(nfd)}; same prompt ids: {a.prompt_ids == b.prompt_ids}; reads equal: {a.reads == b.reads} (ADR: raw NFC text is tokenized; the bank tokenizes the raw text as stored)")

# independent read positions: the token whose bytes end where the word ends
def my_reads(ex: T.Example, source: str) -> list[tuple[int, int]]:
    table = tok.token_bytes()
    ends, acc = [], 0
    for i in ex.prompt_ids:
        acc += len(table[i])
        ends.append(acc)
    label = len("English:".encode())
    res, pos = [], 0
    text = " " + source
    for w in source.split():
        s = text.index(w, pos)
        pos = s + len(w)
        end_byte = label + len(text[:pos].encode())
        k = next(i for i, e in enumerate(ends) if e >= end_byte)
        nw = data.normalize(w)
        if nw in vocab:
            res.append((k, vocab[nw]))
    return res


for src in ("the café is open now", "Tom can't swim.", "the  cafe,is open now!"):
    ex = T.build_example(tok, "A", src, "x", vocab, "k")
    say(f"[reads] {src!r}: implementation {list(ex.reads)}; mine {my_reads(ex, src)}; equal: {list(ex.reads) == my_reads(ex, src)}")
segs = [T.prompt_segments(tok, "A", s) for s in ("the café is open now", "Tom can't swim.", "the cafe is open now")]
say(f"[test a] prompts, segment ids vs whole-string ids on the stand-in: {T.check_segments_vs_whole(segs, tok)}")

# the sentence parser and Unicode line boundaries inside a sentence
raw = "1\teng\tfirst part second part\n2\teng\tplain\n3\teng\tx\x85y\n".encode()
parsed = data.parse_sentences(bz2.compress(raw))
say(f"[parse] sentences with U+2028 / U+0085 inside the text: {parsed} (split('\\n') would keep 'first part\\u2028second part')")

# the router: one generator for initialization and sampling (section 9 asks for a fresh +3 generator after the initialization)
import inspect  # noqa: E402

from studies.p10s2 import routing  # noqa: E402

src = inspect.getsource(routing.train_router)
say(f"[router] plan.gen(3, ...) calls in train_router: {src.count('plan.gen(3')}; the same generator object passed to Router(...), randperm (prefixes), randint (lengths) and randint (batches): {src.count('generator=gen') + src.count(', gen)')}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
