# Preserve the executed import order in this archival checker.
# ruff: noqa: I001
"""Root P5 strict restoration/data freeze; no model forwards."""

import json
from pathlib import Path
from arborlm.engine import configure_cpu
from arborlm.io import canonical_json, sha256, write_json, read_json
from arborlm.records import record_source, record_environment
from arborlm.p5_config import SPEC, PARENT_SUITE, PARENT_RESULTS
from arborlm.p5_parent import verify_suite, verify_parent, extract_verified
from arborlm.p5_model import backbone_digest
from arborlm.p5_data import freeze, load_frozen

out = Path("experiments/review/p5-root-preflight/strict-restoration")
out.mkdir()
source = record_source(out, Path.cwd(), spec=SPEC)
env = record_environment(out, family="P5_PREFLIGHT_NO_FORWARD")
configure_cpu()
suite = Path("experiments") / PARENT_SUITE
mapping = verify_suite(suite, PARENT_RESULTS, source)
records = []
for key, record in sorted(mapping.items()):
    parent = verify_parent(suite, PARENT_RESULTS, record, env)
    backbone = extract_verified(parent)
    assert all(not p.requires_grad and p.grad is None for p in backbone.parameters())
    assert backbone_digest(backbone) == parent.provenance["backbone_sha256"]
    parent.check_unchanged()
    records.append(
        {
            "parent": list(key),
            "digest": backbone_digest(backbone),
            "parameters": sum(p.numel() for p in backbone.parameters()),
        }
    )
folder = out / "frozen-data"
folder.mkdir()
manifest = freeze(folder, Path("data/wikitext2"))
train, old, new, reloaded = load_frozen(folder, sha256(canonical_json(manifest)))
assert reloaded == manifest and list(train.shape) == [4096, 65] and list(new.shape) == [512, 65]
luna = read_json(Path("results/p5-preflight-2026-11-13/independent-data-parent-audit.json"))
ids = read_json(folder / "validation_first_2560.selected.json")
for panel, entry in luna["prior_and_p5_validation_panels"].items():
    start, end = map(int, panel.split(":"))
    assert [
        {k: x[k] for k in ("row", "byte_offset", "rank_sha256", "chunk_sha256")}
        for x in ids[start:end]
    ] == entry["selected_ids"]
assert manifest["checksums_sha256"]["validation.bytes"] == luna["p5_panel_bytes_sha256"]
report = {
    "status": "PASS",
    "strict_restored_parents": records,
    "manifest_sha256": sha256(canonical_json(manifest)),
    "validation_sha256": manifest["checksums_sha256"]["validation.bytes"],
    "all2560_ids_match_independent_reconstruction": True,
    "model_forwards": 0,
    "training_updates": 0,
    "scientific_evaluations": 0,
    "source_sha256_at_check": source["archive"]["sha256"],
    "source_is_final_freeze": False,
}
write_json(out / "root-strict-restore.json", report)
print(json.dumps(report, indent=2))
