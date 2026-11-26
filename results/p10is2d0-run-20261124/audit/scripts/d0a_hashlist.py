# ruff: noqa
"""Audit D0: SHA-256 file list of a directory tree (read-only), written to a NEW file in audit_d0_out (never overwritten).

Usage: python3 -I d0a_hashlist.py <dir> <label>   -> audit_d0_out/hashlist_<label>.json  (sorted relative path -> [size, sha256]; symlinks listed by target text)
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit_d0_out")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    root, label = Path(sys.argv[1]), sys.argv[2]
    out = OUT / f"hashlist_{label}.json"
    t0 = time.time()
    files = {}
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns.sort()
        for fn in sorted(fns + [d for d in dns if os.path.islink(os.path.join(dp, d))]):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            if os.path.islink(p):
                files[rel] = ["symlink", os.readlink(p)]
            else:
                files[rel] = [os.path.getsize(p), sha(p)]
    listing = json.dumps(files, sort_keys=True)
    rec = {"root": str(root), "label": label, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": len(files),
           "list_sha256": hashlib.sha256(listing.encode()).hexdigest(), "seconds": time.time() - t0, "entries": files}
    with open(out, "x") as f:
        json.dump(rec, f)
    print(label, rec["files"], "files; list sha256", rec["list_sha256"], f"{rec['seconds']:.1f}s")


if __name__ == "__main__":
    main()
