# ruff: noqa
"""Summarize the eight tensors_*.json files: count agreement against the recorded reads. Run: python3 -B summarize_tensors.py"""
import glob, json, os
OUT = os.path.dirname(os.path.abspath(__file__))
lines, n_cmp, n_diff = [], 0, 0
worst_fact = 0.0
for p in sorted(glob.glob(f"{OUT}/tensors_*.json")):
    d = json.load(open(p))
    lines.append(f"== {os.path.basename(p)}: draw hashes equal manifest {d['draw_hashes_equal_manifest']}; keys equal raw tensor {d['keys_equal_raw_tensor']}; facts in table {d['facts_in_table']}; seconds {d['seconds']}")
    if "p10s1_tree_recall_recorded" in d:
        lines.append(f"   P10-S1 recorded tree_recall_of_exhaustive_top8 at this snapshot: {d['p10s1_tree_recall_recorded']}; my CR8(T0) {d['my_cr8_T0']}")
    for name, r in d["reads"].items():
        cnt = r["counts"]
        cdiff = []
        for p_ in ("A", "B"):
            c = cnt[p_]
            n_cmp += 2
            for k in ("correct", "useful"):
                if c[f"mine_{k}"] != c[f"rec_{k}"]:
                    n_diff += 1
                    cdiff.append(f"{p_}.{k} {c[f'mine_{k}']} vs {c[f'rec_{k}']}")
        fm, fr = r.get("facts_mine", {}), r.get("facts_recorded", {})
        fd = []
        for k, v in fm.items():
            kr = "share_span_both" if k == "span" else k
            if kr in fr:
                n_cmp += 1
                dv = abs(v - fr[kr])
                worst_fact = max(worst_fact, dv)
                if dv > 1e-6:
                    n_diff += 1
                    fd.append(f"{k} {v:.6f} vs {fr[kr]:.6f}")
        g4 = r.get("gate4_vs_study_path")
        extra = ""
        if g4:
            extra = f" gate4[sets_differ {g4['sets_differ']}, ties {g4['float_ties']}, non-ties {g4['not_float_ties']}, max dw {g4['max_weight_diff']:.2e}]"
            n_cmp += 1
            if g4["not_float_ties"] or g4["max_weight_diff"] > 1e-6 or g4["float_ties"] > 0.001 * g4["facts"]:
                n_diff += 1
        if "pair_mine" in r and r.get("pair_recorded"):
            pm, pr = r["pair_mine"], r["pair_recorded"]
            for k in ("share_selected_changed", "tv_mean"):
                n_cmp += 1
                if abs(pm[k] - pr[k]) > 1e-6:
                    n_diff += 1
                    fd.append(f"pair {k} {pm[k]:.6f} vs {pr[k]:.6f}")
        if "candidates_facts_mine" in r:
            cm, cr = r["candidates_facts_mine"], r["candidates_facts_recorded"]
            n_cmp += 2
            for k in ("mean", "p99"):
                if abs(cm[k] - cr[k]) > 1e-9:
                    n_diff += 1
                    fd.append(f"candidates {k} {cm[k]} vs {cr[k]}")
            extra += f" index hash equal {r['index_sha256_equal_record']}; float64-vs-float32 candidate-set differences {r['facts_whose_float64_candidate_set_differs_from_p10s1_float32_mask']}"
        a = (cnt["A"]["mine_useful"] + cnt["B"]["mine_useful"]) / 65536
        lines.append(f"   {name:16s} a_use {a:.4f} i(A,B) {cnt['A']['mine_i']:.4f},{cnt['B']['mine_i']:.4f} CR8 {fm.get('cr8', float('nan')):.4f} AM_C {fm.get('am_c', float('nan')):.4f} counts {'EXACT' if not cdiff else cdiff} facts {'AGREE' if not fd else fd} misses {r['lookup_misses']}{extra}")
lines.append(f"COMPARISONS {n_cmp}; DIFFERENCES {n_diff}; largest |fact-measure difference| {worst_fact:.2e}")
text = "\n".join(lines)
print(text)
open(f"{OUT}/summarize_tensors.out.txt", "w").write(text + "\n")
