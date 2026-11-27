# ruff: noqa
"""Cross-evaluation map (M0), last step: attach the global clusters of both readings and the per-evaluation counts to
cross_evaluation_procedures_proposed.json (computed with s04_recompute.components; derived data, recomputable by s04 after drops).
Run: python s07_attach_global_clusters.py
"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s04_recompute as R  # noqa: E402

P = HERE / "cross_evaluation_procedures_proposed.json"
doc = json.loads(P.read_text())
clusters = {(c["eval"], c["cluster"]): c["survivors"] for c in doc["strict_clusters"]}
doc["addendum_text_read"] = {
    "working_definition": "docs/decisions/ADR-0033-addendum-1-lineage-clusters.md DRAFT 2 (commit a2fb316f, SHA-256 0df152b115928d34e939d0e01e641097a743694ac23787848a6cb394554e087f), sections 1, 3, 4",
    "also_checked": "DRAFT 3 (commit 9788a8ef, SHA-256 2df30a29...; committed while this map was being made), sections 1, 3, 4, 4A",
}
for name, grades in (("reading_1_strong_only", {"STRONG"}), ("reading_2_strong_plus_borderline", {"STRONG", "BORDERLINE"})):
    gl, used = R.components(clusters, doc["pairs"], grades)
    per = {}
    for e in R.EVALS:
        G = sum(1 for g in gl if e in g["evals"])
        x = sum(1 for g in gl if e in g["evals"] and len(g["evals"]) >= 2)
        per[e] = {"strict_clusters": sum(1 for (ev, _) in clusters if ev == e), "independent_units_G": G, "cross_evaluation": x, "single_evaluation": G - x}
    doc[name] = {
        "links_used": used,
        "global_clusters": [{"identity_among_survivors": g["identity"], "evals": g["evals"], "members": [{"eval": e, "cluster": c, "lineages": clusters[(e, c)]} for e, c in g["members"]]} for g in gl],
        "cross_evaluation_count": sum(1 for g in gl if len(g["evals"]) >= 2),
        "per_evaluation": per,
    }
doc["note_on_identity"] = "Identities here are the smallest SURVIVOR id; the addendum's identity is the smallest id over all written lineages in the component, registered or not, which this map has not fully judged. Identities do not change counts."
P.write_text(json.dumps(doc, indent=1) + "\n")
print({k: doc[k]["per_evaluation"] for k in ("reading_1_strong_only", "reading_2_strong_plus_borderline")})
print("wrote", P, "sha256", hashlib.sha256(P.read_bytes()).hexdigest())
