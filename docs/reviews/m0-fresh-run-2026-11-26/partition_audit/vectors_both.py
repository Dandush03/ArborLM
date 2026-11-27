"""V1-V8 (made-up identities; seed 400004 as the text's vectors use it): full-fact comparison of the
implementer's partition() with partition_audit.partition(), using compare_impls' fact extraction.
Usage: python vectors_both.py IMPL_PARTITION_PY"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_impls as ci  # noqa: E402
import run_vectors as rv  # noqa: E402

impl = ci.load_impl(sys.argv[1])
bad = 0
for name, (lin, links, bp) in rv.VECTORS.items():
    le = {k: k.split(".", 1)[0] for k in lin}
    cands = [k for k, c in lin.items() if c]
    _, diff, _, _ = ci.compare(impl, le, links, bp, cands, 400004)
    bad += bool(diff)
    print(name, "agree" if not diff else f"DIFF {diff}")
print("VECTOR DISAGREEMENTS:", bad)
