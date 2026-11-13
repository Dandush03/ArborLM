"""Independent P4 raw-data/parent audit; no ArborLM imports or model evaluation."""

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq
import torch

ROOT = Path.cwd()
P3 = ROOT / "experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d"
OUT = ROOT / "results/p4-preflight-2026-11-12"
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
    for i, row in enumerate(ranked["validation"][:2048])
    if i >= 1536
]
luna = read(OUT / "luna-data-parent-audit.json")
assert selected == luna["validation_reconstruction"]["P4_rows"]

all_cells = read(P3 / "cells.json")
parents = [row for row in all_cells if row["condition"] == "disabled_throughout"]
assert len(parents) == 9
assert {(r["backbone"], r["order"], r["memory"]) for r in parents} == {
    (b, o, 201) for b in (101, 102, 103) for o in (301, 302, 303)
}
parent_records = []
for row in parents:
    run = P3 / "cells" / row["run_id"]
    compact = ROOT / "results/p3-lt-2026-11-12" / row["label"]
    for name in (
        "manifest.json",
        "result.json",
        "terminal.json",
        "order.json",
        "checkpoint-1024/index.json",
    ):
        assert (run / name).read_bytes() == (compact / name).read_bytes()
    result = read(run / "result.json")
    state_path = run / "checkpoint-1024/state.pt"
    index_path = run / "checkpoint-1024/index.json"
    state_hash = sha(state_path.read_bytes())
    assert state_hash == read(index_path)["state_sha256"]
    assert state_hash == result["checkpoint_state_sha256"]["checkpoint-1024"]
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    assert state["counters"]["completed_step"] == 1024
    assert state["counters"]["cumulative_targets"] == 524288
    assert state["bypass"] is True
    assert {int(s["step"]) for s in state["optimizer"]["state"].values()} == {1024}
    backbone = {n: t for n, t in state["model"].items() if not n.startswith("memory_state.")}
    assert sum(t.numel() for t in backbone.values()) == 27392
    assert all(
        not req for n, req in state["requires_grad"].items() if n.startswith("memory_state.")
    )
    parent_records.append(
        {
            "label": row["label"],
            "run_id": row["run_id"],
            "state_sha256": state_hash,
            "index_sha256": sha(index_path.read_bytes()),
            "backbone_parameters": 27392,
            "parent_step": 1024,
        }
    )

report = {
    "status": "PASS",
    "method": (
        "Independent raw Parquet ranking and actual P3 parent-byte audit; "
        "no ArborLM imports or model forwards"
    ),
    "source_hashes": expected_source,
    "candidate_counts": counts,
    "train_sha256": train_hash,
    "panels": panels,
    "exact_panel_overlaps": 0,
    "p4_selected_ids_match_luna": True,
    "parents": parent_records,
    "model_evaluations": 0,
    "training_updates": 0,
}
(OUT / "independent-data-parent-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
