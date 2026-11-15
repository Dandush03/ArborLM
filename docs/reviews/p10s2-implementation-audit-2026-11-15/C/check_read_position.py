"""Auditor C: where the read of a word with trailing punctuation lands (studies/p10s2/tokenization.tokenize_segment).
Saved copy of the two inline runs whose output is in check_read_position.out.txt. Usage: python check_read_position.py <pin>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import re
import sys

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[1] + "/src")
from studies.p10s2.tokenization import SyntheticTokenizer, tokenize_segment  # noqa: E402

t = " Tom is here, the cat sat."
tok = SyntheticTokenizer("the cat sat on the mat. tom is here, and the dog too.", merges=40)
seg = tokenize_segment(tok, t, with_words=True)
ids, offs = tok.encode_offsets(t)
print("tokens:", [t[s:e] for s, e in offs])
print("reads (token index, word):", [(k, w, t[offs[k][0]:offs[k][1]]) for k, w in seg.word_last])


class PreSplit:  # GPT-2-style pre-tokenization: letters and punctuation are separate pieces
    bos_id = None

    def encode_offsets(self, text):
        o = [(m.start(), m.end()) for m in re.finditer(r" ?[A-Za-z]+| ?[^\sA-Za-z]+|\s+", text)]
        return list(range(len(o))), o

    def encode(self, text):
        return self.encode_offsets(text)[0]


seg = tokenize_segment(PreSplit(), t, with_words=True)
offs = PreSplit().encode_offsets(t)[1]
print("pre-split tokens:", [t[s:e] for s, e in offs])
print("reads:", [(k, w, t[offs[k][0]:offs[k][1]]) for k, w in seg.word_last], "-> 'here' and 'sat' are read at the punctuation token")
