"""Numbers present in rev4 but absent from rev5, and new numbers in rev5 (multiset by token). python3 -I numdiff.py rev4 rev5"""
import re, sys
from collections import Counter
a=open(sys.argv[1],encoding='utf-8').read(); b=open(sys.argv[2],encoding='utf-8').read()
tok=lambda t: Counter(re.findall(r'(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?', t))
A,B=tok(a),tok(b)
print("numbers whose count DROPPED from rev4 to rev5:", {k:(A[k],B[k]) for k in A if B[k]<A[k]})
print("numbers NEW or more frequent in rev5:", sorted(k for k in B if B[k]>A[k]))
