"""Independent P5 raw-data/parent audit; no ArborLM imports or model evaluation."""

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq
import torch

ROOT = Path.cwd()
P4 = ROOT / "experiments/P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd"
OUT = ROOT / "experiments/review/p5-root-preflight"
OUT.mkdir(exist_ok=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


expected_source = {
    "train": "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7",
    "validation": "204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c",
}
ranked = {}
counts = {}
for split in expected_source:
    path = ROOT / "data/wikitext2" / f"{split}-00000-of-00001.parquet"
    assert sha(path.read_bytes()) == expected_source[split]
    candidates = {}
    total = 0
    for row, text in enumerate(pq.read_table(path, columns=["text"]).column("text").to_pylist()):
        raw = text.encode("utf-8")
        for offset in range(0, len(raw) - 64, 65):
            total += 1
            chunk = raw[offset : offset + 65]
            chunk_hash = sha(chunk)
            rank = sha(f"arborlm-pilot-v1:{split}:{row}:{offset}".encode())
            item = (rank, row, offset, chunk)
            if chunk_hash not in candidates or item[:3] < candidates[chunk_hash][:3]:
                candidates[chunk_hash] = item
    counts[split] = {"candidates": total, "unique_before_exclusion": len(candidates)}
    if split == "train":
        all_train_hashes = set(candidates)
    else:
        candidates = {h: v for h, v in candidates.items() if h not in all_train_hashes}
    counts[split]["eligible"] = len(candidates)
    ranked[split] = sorted(candidates.values(), key=lambda item: item[:3])

train_hash = sha(b"".join(item[3] for item in ranked["train"][:4096]))
assert train_hash == "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07"
expected_panels = [
    "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200",
    "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2",
    "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0",
    "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f",
]
panels = []
previous = set()
for i, expected in enumerate(expected_panels):
    rows = ranked["validation"][i * 512 : (i + 1) * 512]
    hashes = {sha(row[3]) for row in rows}
    assert len(rows) == len(hashes) == 512
    assert not hashes & (previous | all_train_hashes)
    actual = sha(b"".join(row[3] for row in rows))
    assert actual == expected
    panels.append({"panel": f"P{i + 1}", "ranks": [i * 512, (i + 1) * 512 - 1], "sha256": actual})
    previous |= hashes
selected = [
    dict(rank=i, row_index=row[1], byte_offset=row[2], rank_sha256=row[0], chunk_sha256=sha(row[3]))
    for i, row in enumerate(ranked["validation"][:2560])
    if i >= 2048
]

p5_rows = ranked["validation"][2048:2560]
p5_hashes = {sha(row[3]) for row in p5_rows}
assert len(p5_rows) == len(p5_hashes) == 512
assert not p5_hashes & (previous | all_train_hashes)
p5_hash = sha(b"".join(row[3] for row in p5_rows))
assert p5_hash not in expected_panels
panels.append(dict(panel="P5",ranks=[2048,2559],sha256=p5_hash))
prior_manifests = []
for base in (ROOT / "results", ROOT / "experiments"):
    for path in sorted(base.rglob("dataset_manifest.json")):
        record=read(path)
        hashes=record.get("checksums_sha256", {})
        val_hash=hashes.get("validation.bytes")
        if val_hash:
            assert val_hash != p5_hash, f"P5 panel already frozen: {path}"
            assert val_hash in expected_panels, f"Unrecognized prior validation panel: {path}"
            prior_manifests.append(str(path.relative_to(ROOT)))
all_cells = read(P4 / "cells.json")
parents = [row for row in all_cells if row["variant"] == "baseline"]
assert len(parents)==9
assert {(r["backbone"],r["order"],r["seed"]) for r in parents} == {(b,o,0) for b in (101,102,103) for o in (301,302,303)}
parent_records=[]
for row in parents:
    run=P4/"cells"/row["run_id"]
    compact=ROOT/"results/p4-2026-11-12"/row["label"]
    for name in ("manifest.json","result.json","terminal.json","order.json","checkpoint-0/index.json"):
        assert (run/name).read_bytes()==(compact/name).read_bytes()
    result=read(run/"result.json")
    path=run/"checkpoint-0/state.pt"
    digest=sha(path.read_bytes())
    assert digest==read(run/"checkpoint-0/index.json")["state_sha256"]==result["checkpoint_state_sha256"]["checkpoint-0"]
    state=torch.load(path,map_location="cpu",weights_only=True)
    assert state["counters"]==dict(additional_step=0,absolute_order_cursor=0,next_cyclic_order_cursor=0,additional_targets=0)
    assert state["bypass"] is True and state["optimizer"] is None and not state["optimizer_parameter_names"]
    assert not any(state["requires_grad"].values())
    assert all(n.startswith("backbone.") for n in state["model"])
    assert sum(t.numel() for t in state["model"].values())==27392
    p3=Path(state["identity"]["parent"]["checkpoint_path"])
    assert sha((p3/"state.pt").read_bytes())==state["identity"]["parent"]["checkpoint_state_sha256"]
    assert sha((p3/"index.json").read_bytes())==state["identity"]["parent"]["checkpoint_index_sha256"]
    source=torch.load(p3/"state.pt",map_location="cpu",weights_only=True)
    old_backbone={n:t for n,t in source["model"].items() if not n.startswith("memory_state.")}
    assert {n.removeprefix("backbone.") for n in state["model"]}==set(old_backbone)
    for name,tensor in state["model"].items():
        other=old_backbone[name.removeprefix("backbone.")]
        assert tensor.shape==other.shape and tensor.dtype==other.dtype
        assert torch.equal(tensor.contiguous().reshape(-1).view(torch.uint8),other.contiguous().reshape(-1).view(torch.uint8))
    parent_records.append(dict(label=row["label"],run_id=row["run_id"],state_sha256=digest,index_sha256=sha((run/"checkpoint-0/index.json").read_bytes()),backbone_sha256=result["backbone_sha256"],backbone_parameters=27392,p3_state_sha256=state["identity"]["parent"]["checkpoint_state_sha256"]))
report=dict(status="PASS",method="Independent raw Parquet reconstruction and actual P4/P3 tensor-byte audit; no ArborLM imports/model forwards",source_hashes=expected_source,candidate_counts=counts,train_sha256=train_hash,panels=panels,p5_selected_rows=selected,exact_panel_overlaps=0,prior_panel_manifest_count=len(prior_manifests),prior_panel_manifests=prior_manifests,prior_use_audit_scope="all available local/results dataset_manifest validation-byte hashes before P5 freeze; no claim about unknown external records",parents=parent_records,model_evaluations=0,training_updates=0)
(OUT/"root-data-parent-audit.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k not in ("p5_selected_rows","prior_panel_manifests")},indent=2))
