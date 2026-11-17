"""Auditor C: chrF-norm of studies/p10s2/text.py against the auditor's definition (spec_rules.chrf_def) and hand cases.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import random, sys
from fractions import Fraction as F
PIN = sys.argv[1]; sys.path.insert(0, PIN); sys.path.insert(0, PIN + "/src"); sys.path.insert(0, sys.argv[2])
from studies.p10s2.text import chrf_pair, chrf_item, normalize
import spec_rules as S
try:
    import sacrebleu  # noqa
    print("sacrebleu available", sacrebleu.__version__)
except Exception as e:
    print("sacrebleu not available in this interpreter:", type(e).__name__)
# hand case 1: hyp 'ab', ref 'abc' (after whitespace removal).
# n=1: hyp {a,b} ref {a,b,c}: match 2, P=1, R=2/3. n=2: hyp {ab}, ref {ab,bc}: P=1, R=1/2. n>=3: hyp has none -> not effective.
# avgP = 1, avgR = (2/3+1/2)/2 = 7/12. F2 = 5*1*(7/12)/(4*1+7/12) = (35/12)/(55/12) = 7/11
print("hand1", chrf_pair("ab", "abc"), float(F(7, 11)))
# hand case 2: identical -> 1; empty hyp -> 0; punctuation/case/whitespace-insensitive
print("hand2", chrf_pair("Das ist gut.", "das  ist gut"), chrf_pair("", "abc"), chrf_pair("abc", ""), chrf_pair("!!!", "abc"))
# hand case 3: repeated n-grams clipped: hyp 'aaaa', ref 'aa'. n=1: hyp a:4 ref a:2 match 2 P=1/2 R=1; n=2: hyp aa:3 ref aa:1 match1 P=1/3 R=1; n=3,4: hyp has, ref none -> not effective.
# avgP=(1/2+1/3)/2=5/12 avgR=1; F2=5*(5/12)*1/(4*5/12+1)= (25/12)/(32/12)=25/32
print("hand3", chrf_pair("aaaa", "aa"), 25/32)
# max over references
print("hand4", chrf_item("abc", ["xyz", "abc", "ab"]))
rng = random.Random(229701)
alpha = "aäbßcdeéfg ,.!'-ÉÄ"
worst = 0.0
for _ in range(20000):
    h = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 14)))
    r = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 14)))
    worst = max(worst, abs(chrf_pair(h, r) - S.chrf_def(h, r)))
print("random 20000 pairs: max |impl - auditor definition| =", worst)
