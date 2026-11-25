# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 21: one recomputation task (one snapshot or one group of reads), written to audit21_out/results/<task>.json (+ .done).

Usage: python a21_task.py <task-id> [--limit N]   (``--limit`` scores only the first N items of each panel: timing runs only, written under timing/)

Task ids (the routing of which snapshot scores which read is mine, typed from ADR-0025 sections 5.2, 5.5, 8.1, 8.5):
  ref                         S0 and the teachers: s:E_A, s:E_B, sub:own, open:A/B
  cell|r|o|ARM                ARM in M1, D1, M-append, M-append@append, M-seq, M-ii, D-append, D-seq of replicate r, order o
  joint|r|ARM                 M-joint or D-joint
  etable|r                    E-table A on E_A and E-table B on E_B
  sep|r                       M-sep (the two M1 stores) and D-sep (the two D1 adapters) behind the oracle route
  base|r                      R-exact, R-nn, R-gloss, R-icl, R-gloss-icl; edit-distance-1 flags
  comb|r|ARM|o                C1, C2 and single answers of one arm-cell (M-append, M-ii, D-seq, D-append per order; M-joint, D-joint, M-sep, D-sep with o = -)
  combref                     S0's combined record and the ensemble's
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a21_lib as L  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(6)
torch.use_deterministic_algorithms(True)

GEN_ARMS = ("M1", "M-append", "M-seq", "M-ii", "D-seq")
CONTROL = {"M1": [0], "M-append": [1], "M-seq": [0], "M-ii": [0, 1], "M-joint": [0]}


def snap_name(r, arm, o):
    return f"r{r}/{arm}/{o}"


def main():
    task = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    outdir = L.OUT / (os.environ.get("A21_LIMIT_DIR", "validate") if limit is not None else "results")
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / (task.replace("|", "__").replace("@", "_at_") + ".json")
    if Path(str(path) + ".done").exists():
        print("done already", task)
        return
    t0 = time.perf_counter()
    data = L.Data(check_hashes=(limit is None))
    model = L.Model(data)
    sc = L.Scorer(model)
    t_load = time.perf_counter() - t0
    recs, vals, extra = {}, {}, {}

    def cut(xs):
        return xs if limit is None else xs[:limit]

    def full_panel(arm_id, arm, prefix, caps=L.TWO):
        for c in caps:
            prompts, refs = data.panel(L.PANEL[c], c)
            prompts, refs = cut(prompts), cut(refs)
            recs[f"{prefix}|s:{L.PANEL[c]}"] = sc.panel(arm_id, arm, prompts, refs)

    def controls(arm_id, arm, prefix, r, stages, caps):
        ab = L.ablations(arm, r, stages, caps)
        for c in caps:
            prompts, refs = data.panel(L.PANEL[c], c)
            sub = data.subsample(c)
            if limit is not None:
                sub = [i for i in sub if i < limit]
            recs[f"{prefix}|sub:own:{L.PANEL[c]}"] = sc.panel(arm_id, arm, prompts, refs, indices=sub)
            for name in ("value", "code", "marker", "words"):
                recs[f"{prefix}|sub:{name}:{L.PANEL[c]}"] = sc.panel(arm_id, arm, prompts, refs, ab=ab[name], ab_id=name, indices=sub)

    kind = task.split("|")[0]
    if kind == "ref":
        null = L.Arm("null")
        full_panel("S0", null, "S0|-|-")
        for c in L.TWO:
            n = L.PANEL[c]
            sub = data.subsample(c)
            s = recs[f"S0|-|-|s:{n}"]
            recs[f"S0|-|-|sub:own:{n}"] = {"items": [s["items"][i] for i in sub if limit is None or i < limit]}
            items = data.part["panels"][n]
            texts = cut(data.teacher[c][n])
            refs = [list(it["refs"][c]) for it in items][: len(texts)]
            t_items = [L.chrf(t, rf) for t, rf in zip(texts, refs)]
            recs[f"TEACHER|-|-|s:{n}"] = {"items": t_items, "exact": [L.exact(t, rf) for t, rf in zip(texts, refs)], "texts": texts}
            recs[f"TEACHER|-|-|sub:own:{n}"] = {"items": [t_items[i] for i in sub if limit is None or i < limit]}
            idx, prompts, orefs = data.open_panel(c)
            recs[f"S0|-|-|open:{c}"] = sc.panel("S0", null, cut(prompts), cut(orefs))
            ot = [data.teacher[c]["E_open"][j] for j in cut(idx)]
            recs[f"TEACHER|-|-|open:{c}"] = {"items": [L.chrf(t, rf) for t, rf in zip(ot, cut(orefs))], "texts": ot}
    elif kind == "cell":
        _, r, o, a = task.split("|")
        r = int(r)
        name = snap_name(r, "M-append", o) + "@append" if a == "M-append@append" else snap_name(r, a, o)
        arm = L.arm_from(name, r)
        prefix = f"{a}|{o}|{r}"
        full_panel(a, arm, prefix)
        first, second = o[0], o[1]
        if a in CONTROL:
            controls(a, arm, prefix, r, CONTROL[a], [first if a == "M1" else second])
        if a in GEN_ARMS:
            router = L.load_router(r, (first,) if a == "M1" else L.TWO)
            g = L.gen_records(model, arm, router, {}, {})
            for read, rec in (("gen:token64", g["token64"]), ("gen:first_marker", g["first_marker"])):
                recs[f"{prefix}|{read}"] = {"gen": rec}
        if a in ("M-append", "M-ii"):
            for c in L.TWO:
                prompts, refs = data.dcon(c)
                recs[f"{prefix}|dcon:{c}"] = sc.panel(a, arm, cut(prompts), cut(refs))
        if a in ("M1", "M-append"):
            for c in L.TWO:
                prompts, refs = data.seen(r, c)
                recs[f"{prefix}|seen:{c}"] = sc.panel(a, arm, cut(prompts), cut(refs))
                _idx, prompts, refs = data.open_panel(c)
                recs[f"{prefix}|open:{c}"] = sc.panel(a, arm, cut(prompts), cut(refs))
        if a == "M-append":
            router = L.load_router(r, L.TWO)
            preds = {}
            for c in L.TWO:
                prompts, refs = data.panel(L.PANEL[c], c)
                prompts, refs = cut(prompts), cut(refs)

                def learned(i, p):
                    pred = L.route(router, model.hidden(p["ids"], L.READ_LAYER, len(p["ids"]) - 1))
                    preds.setdefault(c, []).append(pred)
                    return [] if pred == "none" else [pred]

                recs[f"{prefix}|lr:{L.PANEL[c]}"] = sc.panel(a, arm, prompts, refs, tasks_of=learned)
            extra["route_accuracy_mine"] = {c: sum(1 for x in v if x == c) / len(v) for c, v in preds.items()}
        if a == "M-ii":
            m1, _ = L.load_snapshot(snap_name(r, "M1", o))
            b32, a32 = m1["store"]["values"][0], arm.raw["values"][0]
            vals[f"{prefix}|modification"] = float((a32 - b32).norm() / b32.norm())  # float32, the precision of the stored values
            before, after = b32.double(), a32.double()
            extra["modification_f64"] = float((after - before).norm() / before.norm())  # the same quantity in float64
            extra["modification_rows_changed_share"] = float(((after - before).abs().sum(dim=1) > 0).double().mean())
    elif kind == "joint":
        _, r, a = task.split("|")
        r = int(r)
        arm = L.arm_from(snap_name(r, a, "-"), r)
        prefix = f"{a}|-|{r}"
        full_panel(a, arm, prefix)
        if a == "M-joint":
            controls(a, arm, prefix, r, CONTROL[a], list(L.TWO))
    elif kind == "etable":
        r = int(task.split("|")[1])
        for c in L.TWO:
            arm = L.arm_from(snap_name(r, "E-table", c), r)
            full_panel("E-table-" + c, arm, f"E-table|-|{r}", caps=(c,))
    elif kind == "sep":
        r = int(task.split("|")[1])
        mA, mB = L.arm_from(snap_name(r, "M1", "AB"), r), L.arm_from(snap_name(r, "M1", "BA"), r)
        msep = L.Arm("msep", stores={"A": mA.store, "B": mB.store}, codes=mA.codes, layer=L.READ_LAYER)
        full_panel("M-sep", msep, f"M-sep|-|{r}")
        dA, dB = L.arm_from(snap_name(r, "D1", "AB"), r), L.arm_from(snap_name(r, "D1", "BA"), r)
        dsep = L.Arm("lsep", adapters={"A": dA.adapter, "B": dB.adapter})
        full_panel("D-sep", dsep, f"D-sep|-|{r}")
    elif kind == "base":
        r = int(task.split("|")[1])
        vocab = set(data.vocab)
        null = L.Arm("null")
        gl = data.gloss
        train_keys = [x["key"] for c in L.TWO for x in data.draws[r][c]]
        by_len = {}
        for k in train_keys:
            w = tuple(k.split())
            by_len.setdefault(len(w), []).append(w)
        for c in L.TWO:
            n = L.PANEL[c]
            items = cut(data.part["panels"][n])
            refs = [list(it["refs"][c]) for it in items]
            prompts = cut(data.panel(n, c)[0])
            train = data.draws[r][c]
            table = {L.norm(x["en"]): x["target"] for x in train}
            outs = [table.get(L.norm(it["en"]), "") for it in items]
            recs[f"R-exact|-|{r}|s:{n}"] = {"items": [L.chrf(o_, rf) for o_, rf in zip(outs, refs)]}
            vals[f"R-exact|-|{r}|hits:{n}"] = float(sum(1 for it in items if L.norm(it["en"]) in table))
            idx = L.Tfidf(train)
            nn_out = [train[idx.nearest(it["en"], 1)[0]]["target"] for it in items]
            recs[f"R-nn|-|{r}|s:{n}"] = {"items": [L.chrf(o_, rf) for o_, rf in zip(nn_out, refs)]}
            lex = L.dice_lexicon(train)
            gl_out = [" ".join(lex.get(w, w) for w in L.norm(it["en"]).split()) for it in items]
            recs[f"R-gloss|-|{r}|s:{n}"] = {"items": [L.chrf(o_, rf) for o_, rf in zip(gl_out, refs)]}
            icl = {"items": [], "sequences": []}
            gicl = {"items": [], "sequences": []}
            for it, p, rf in zip(items, prompts, refs):
                demos = [train[i] for i in reversed(idx.nearest(it["en"], 4))]  # the 4 nearest pairs, nearest last
                ids = [t for dm in demos for t in data.train_ids(c, dm)] + p["ids"]
                g, _ = model.greedy(ids)
                icl["items"].append(L.chrf(data.answer_text(g), rf))
                icl["sequences"].append(g)
                pairs = [(w, lex[w]) for w in L.norm(it["en"]).split() if w in vocab and w in lex]
                gids = list(p["ids"])
                if pairs:
                    lines = []
                    for k, (w, gw) in enumerate(pairs):
                        lines += [*(gl["source_words"][w] if k == 0 else gl["source_words_after_newline"][w]), *gl["separator"], *gl["words"][c][gw]]
                    assert gl["last_newline"]["rule"] == "own-segment"
                    gids = lines + list(gl["newline"]) + list(p["ids"])
                g2, _ = model.greedy(gids)
                gicl["items"].append(L.chrf(data.answer_text(g2), rf))
                gicl["sequences"].append(g2)
            recs[f"R-icl|-|{r}|s:{n}"] = icl
            recs[f"R-gloss-icl|-|{r}|s:{n}"] = gicl
            flags = []
            for it in items:
                w = tuple(it["key"].split())
                flags.append(any(L.edit1(w, t) for ln in (len(w) - 1, len(w), len(w) + 1) for t in by_len.get(ln, ())))
            recs[f"edit1|-|{r}|edit1:{n}"] = {"flags": flags}
    elif kind == "comb":
        _, r, a, o = task.split("|")
        r = int(r)
        if a == "M-sep":
            mA, mB = L.arm_from(snap_name(r, "M1", "AB"), r), L.arm_from(snap_name(r, "M1", "BA"), r)
            arm = L.Arm("msep", stores={"A": mA.store, "B": mB.store}, codes=mA.codes, layer=L.READ_LAYER)
        elif a == "D-sep":
            dA, dB = L.arm_from(snap_name(r, "D1", "AB"), r), L.arm_from(snap_name(r, "D1", "BA"), r)
            arm = L.Arm("lsep", adapters={"A": dA.adapter, "B": dB.adapter})
        else:
            arm = L.arm_from(snap_name(r, a, o), r)
        extra["combined"] = L.combined_cell(model, arm, data, limit)
        extra["combined_key"] = f"{a}|{o}|{r}"
    elif kind == "combref":
        extra["S0"] = L.combined_cell(model, L.Arm("null"), data, limit)
        extra["ensemble"] = L.ensemble_record(data)
    else:
        raise SystemExit(f"unknown task {task}")
    out = {"task": task, "records": recs, "values": vals, "extra": extra, "seconds": time.perf_counter() - t0, "load_seconds": t_load, "decode_calls": sc.calls, "memo_hits": sc.hits,
           "limit": limit, "torch": torch.__version__, "threads": torch.get_num_threads(), "pid": os.getpid()}
    L.write_json_once(path, out)
    print(f"{task}: {out['seconds']:.1f} s, {sc.calls} decodes ({sc.hits} memo hits)")


if __name__ == "__main__":
    main()
