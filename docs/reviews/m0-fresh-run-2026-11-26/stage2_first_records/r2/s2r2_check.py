# ruff: noqa
"""M0 stage 2, R2: second-solver fixture check, level-parameter summary and example renderings (auditor's own code).

Run from the implementation worktree root (agent-a0c9d741ea96ce52f):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python <this> <survivor_list.json> <f_solver.py> <outdir>
Fixture seed: S = int.from_bytes(sha256(b"400002|stage2-check|R2")[:8], "big"). Per lineage and level the stream is
random.Random(int.from_bytes(sha256(f"{S}|{lid}|{level}".encode())[:8], "big")); 50 items per level are built with core.build_item on
r2_fix4_set.fix4_set()[lid] (the builder of record). Only it.question is passed to the solver; the key is compared afterwards, exact string equality.
No cheap rule is computed. Not a run unit; not a run seed or dry-run seed."""
import hashlib, importlib.util, json, random, re, statistics, sys

N = 50
LABEL = b"400002|stage2-check|R2"
S = int.from_bytes(hashlib.sha256(LABEL).digest()[:8], "big")


def params(name, st, q, ans):
    """Size / depth parameters read from the structured form (for the levels condition)."""
    if name == "binary_search_trace": return {"n": len(st["xs"])}
    if name == "caesar_shift": return {"words": len(st["text"].split(" ")), "letters": sum(c != " " for c in st["text"])}
    if name == "cellular_automaton": return {"cells": len(st["row"]), "steps": st["steps"]}
    if name == "cheapest_network": return {"towns": len(st["towns"]), "cables": len(st["cables"])}
    if name == "count_divisible": return {"n": len(st["xs"]), "max_x": max(st["xs"])}
    if name == "crt_smallest": return {"k": len(st["congruences"]), "min_mod": min(m for _, m in st["congruences"]), "max_mod": max(m for _, m in st["congruences"])}
    if name == "dictionary_rank": return {"length": st["length"], "alphabet": len(st["letters"])}
    if name == "expression_eval": return {"numbers": len(re.findall(r"\d+", st["text"])), "parens": st["text"].count("(")}
    if name == "from_base": return {"digits": len(st["digits"]), "base": st["base"]}
    if name == "grid_sum": return {"rows": len(st["grid"]), "cols": len(st["grid"][0])}
    if name == "list_ops": return {"start_len": len(st["xs"]), "ops": len(st["ops"])}
    if name == "luhn_check": return {"digits": len(st["digits"])}
    if name == "min_heap_ops": return {"n": len(st["xs"]), "removals": st["removals"]}
    if name == "run_length": return {"runs": len(re.findall(r"[a-z]\d+", ans)), "length": len(st["s"])}
    if name == "sort_list": return {"n": len(st["xs"])}
    if name == "string_rewrite_nonidentity": return {"length": len(st["s"]), "rules": len(st["rules"])}
    if name == "to_base_wide": return {"n_bits": st["n"].bit_length(), "base": st["base"], "answer_digits": len(ans)}
    raise KeyError(name)


def main():
    surv_path, solver_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    surv = json.load(open(surv_path))["evaluations"]["R2"]
    spec = importlib.util.spec_from_file_location("f_solver_final_r2", solver_path)
    fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
    from studies.m0.core import build_item
    from studies.m0.r2_fix4_set import fix4_set
    reg = fix4_set()
    out = {"fixture_seed": S, "label": LABEL.decode(), "items_per_level": N, "solver": solver_path,
           "solver_sha256": hashlib.sha256(open(solver_path, "rb").read()).hexdigest(), "lineages": {}}
    examples = []
    for lid in surv:
        name = lid.split(".", 1)[1]
        lin = reg[lid]
        rec = {"covered": name in fs.SOLVERS, "items": 0, "mismatches": 0, "errors": 0, "mismatch_ids": [], "error_ids": [],
               "flags": {}, "items_hash": None, "levels": {}}
        h = hashlib.sha256()
        for lv in range(7):
            rng = random.Random(int.from_bytes(hashlib.sha256(f"{S}|{lid}|{lv}".encode()).digest()[:8], "big"))
            ps = []
            for i in range(N):
                iid = f"{lid}/stage2-check/L{lv}/{i}"
                it = build_item(lin, lv, rng, "A", iid)
                h.update(it.to_json().encode()); h.update(b"\n")
                rec["items"] += 1
                ps.append(params(name, it.structured, it.question, it.answer))
                if i == 0:
                    examples.append({"id": iid, "question": it.question, "answer": it.answer, "answer_type": it.answer_type})
                if not rec["covered"]:
                    continue
                try:
                    a, fl = fs.solve(name, it.question)
                except Exception as e:  # noqa: BLE001
                    rec["errors"] += 1; rec["error_ids"].append([iid, repr(e)[:200]]); continue
                for f in fl:
                    rec["flags"][f] = rec["flags"].get(f, 0) + 1
                if a != it.answer:
                    rec["mismatches"] += 1; rec["mismatch_ids"].append([iid, it.answer, a])
            keys = sorted(ps[0])
            rec["levels"][str(lv)] = {k: {"min": min(p[k] for p in ps), "max": max(p[k] for p in ps),
                                          "mean": round(statistics.fmean(p[k] for p in ps), 3)} for k in keys}
        rec["items_hash"] = h.hexdigest()
        out["lineages"][lid] = rec
    tot = sum(v["items"] for v in out["lineages"].values())
    mm = sum(v["mismatches"] + v["errors"] for v in out["lineages"].values())
    out["total_items"] = tot; out["total_mismatches_and_errors"] = mm
    with open(f"{outdir}/s2r2_check.out.json", "w") as f:
        json.dump(out, f, sort_keys=True, indent=2); f.write("\n")
    with open(f"{outdir}/s2r2_examples.out.json", "w") as f:
        json.dump(examples, f, sort_keys=True, indent=2); f.write("\n")
    print(f"seed {S}; items {tot}; mismatches+errors {mm}")
    for lid, v in out["lineages"].items():
        print(f"{lid:34s} covered={v['covered']} items={v['items']} mismatch={v['mismatches']} errors={v['errors']} flags={v['flags']}")


if __name__ == "__main__":
    main()
