"""Compare the two r4 dumps: every key of the d27ba7f record must be bit-identical (float.hex) in the 3a9a742 record; list keys only in the new record.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json, sys
old, new = (json.load(open(p)) for p in sys.argv[1:3])
print("trees:", old["tree"], "|", new["tree"])
def walk(a, b, path, diffs):
    if isinstance(a, dict):
        for k in a:
            if k not in b: diffs.append(("missing in new", path + "/" + k)); continue
            walk(a[k], b[k], path + "/" + k, diffs)
    elif a != b:
        diffs.append(("differs", path, str(a)[:80], str(b)[:80]))
total = {}
for label, rec in old["records"].items():
    diffs = []
    walk(rec, new["records"][label], label, diffs)
    extra = sorted(set(new["records"][label]) - set(rec))
    n = sum(1 for _ in json.dumps(rec))
    total[label] = {"diffs": diffs, "new_keys": extra, "read_swap": "read_swap" in rec, "a_use_A": rec.get("read_swap", {}).get("A", {}).get("a_use")}
    print(label, "diffs:", len(diffs), "new keys:", extra, "has read_swap:", "read_swap" in rec)
print("ALL IDENTICAL:", all(not v["diffs"] for v in total.values()))
