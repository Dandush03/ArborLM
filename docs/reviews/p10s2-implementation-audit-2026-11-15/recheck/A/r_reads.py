"""Re-check A: read positions under the lead's ruling C-M5 ("the read for a word is at the word's last subword, never at a following
punctuation token"), recomputed from token BYTES (not from the tokenizer's offsets, which the implementation uses), on the synthetic
tokenizer stand-in; NFC before tokenization (audit minor 1). Written by the re-check auditor (Claude Opus 5.5).
Run:  <python> -I <this file> <pinned tree>
"""

import sys
import unicodedata
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import tokenization as T  # noqa: E402

OUT: list[str] = []


def say(s: str) -> None:
    OUT.append(s)
    print(s)


sample = "English: the cafe is open now\nGerman: das cafe ist offen\nFrench: le café est ouvert, n'est-ce pas?\n" * 20 + "Tom can't swim. swim! swim.\n" * 10
tok = T.SyntheticTokenizer(sample, merges=120)
vocab = {w: i for i, w in enumerate(["the", "café", "is", "open", "now", "tom", "cant", "swim", "nestce", "pas"])}


def mine(ex: T.Example, source: str) -> list[tuple[int, int]]:
    table = tok.token_bytes()
    spans, acc = [], 0
    for i in ex.prompt_ids:
        spans.append((acc, acc + len(table[i])))
        acc += len(table[i])
    src = unicodedata.normalize("NFC", source)
    prefix = "English:" + " "
    base = len(prefix.encode())
    res, pos = [], 0
    for w in src.split():
        s = src.index(w, pos)
        pos = s + len(w)
        letters = [k for k, ch in enumerate(w) if unicodedata.category(ch)[0] != "P"]
        nw = "".join(ch for ch in unicodedata.normalize("NFC", w).lower() if unicodedata.category(ch)[0] != "P")
        if not letters or nw not in vocab:
            continue
        last_char = s + letters[-1]
        byte_lo = base + len(src[:last_char].encode())  # first byte of the last letter
        k = next(i for i, (a, b) in enumerate(spans) if a <= byte_lo < b)
        res.append((k, vocab[nw]))
    return res


cases = ["the café is open now", "Tom can't swim.", "the  cafe,is open now!", "swim! swim. (swim)", "n'est-ce pas?", unicodedata.normalize("NFD", "the café is open now")]
for src in cases:
    ex = T.build_example(tok, "A", src, "x", vocab, "k")
    m = mine(ex, src)
    say(f"[reads] {src!r}: implementation {list(ex.reads)}; mine (from bytes) {m}; equal: {list(ex.reads) == m}")
a = T.build_example(tok, "A", cases[0], None, vocab, "k1")
b = T.build_example(tok, "A", cases[-1], None, vocab, "k2")
say(f"[NFC] NFD source gives the same prompt ids and reads as its NFC form: {a.prompt_ids == b.prompt_ids and a.reads == b.reads}")
try:
    T.build_example(tok, "A", "two\nlines", None, vocab, "k3")
    say("[newline] a source with a newline: ACCEPTED (unexpected)")
except ValueError as e:
    say(f"[newline] a source with a newline is refused: {e}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(OUT) + "\n")
