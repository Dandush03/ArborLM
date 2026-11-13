"""Root preflight: strict restore/extraction and identities, no model forwards."""

import json
import tempfile
from pathlib import Path

import torch

from arborlm.engine import configure_cpu
from arborlm.optimization_followup import _optimizer
from arborlm.p2_model import FollowupModel
from arborlm.p3_checkpoint import restore
from arborlm.p4_config import BASELINE, DENSE, MEMORY, PARENT_RESULTS, PARENT_SUITE, SPEC, Cell
from arborlm.p4_data import freeze
from arborlm.p4_model import FrozenModel, backbone_digest, optimizer_for
from arborlm.p4_parent import verify_parent, verify_suite
from arborlm.records import record_environment, record_source

configure_cpu()
out = Path(tempfile.mkdtemp(prefix="p4-restore-audit-", dir="experiments/review"))
source = record_source(out, Path.cwd(), spec=SPEC)
environment = record_environment(out, family="P4_FROZEN_CAPACITY")
suite = Path("experiments") / PARENT_SUITE
mapping = verify_suite(suite, PARENT_RESULTS, source)
assert len(mapping) == 9
evidence = []
for (b, o), record in sorted(mapping.items()):
    parent = verify_parent(suite, PARENT_RESULTS, record, environment)
    model = FollowupModel(parent.cell)
    opt = _optimizer(model)
    counts = restore(parent.checkpoint, model, opt, parent.identity)
    assert counts["completed_step"] == 1024
    raw = torch.load(parent.checkpoint / "state.pt", map_location="cpu", weights_only=True)
    for name, value in model.state_dict().items():
        assert torch.equal(
            value.contiguous().reshape(-1).view(torch.uint8),
            raw["model"][name].contiguous().reshape(-1).view(torch.uint8),
        )
    digests = []
    for variant in (BASELINE, MEMORY, DENSE):
        frozen = FrozenModel(Cell(b, o, 0 if variant == BASELINE else 401, variant), model)
        optimizer = optimizer_for(frozen)
        trainable = [p for p in frozen.parameters() if p.requires_grad]
        expected = 0 if variant == BASELINE else 198401
        assert sum(p.numel() for p in trainable) == expected
        assert sum(p.numel() for p in frozen.backbone.parameters()) == 27392
        assert all(not p.requires_grad and p.grad is None for p in frozen.backbone.parameters())
        if optimizer is not None:
            included = [id(p) for group in optimizer.param_groups for p in group["params"]]
            assert included == [id(p) for p in trainable] and len(set(included)) == len(included)
            assert not optimizer.state
        for name, value in frozen.backbone.state_dict().items():
            assert torch.equal(
                value.contiguous().reshape(-1).view(torch.uint8),
                raw["model"][name].contiguous().reshape(-1).view(torch.uint8),
            )
        digests.append(backbone_digest(frozen.backbone))
    assert len(set(digests)) == 1
    parent.check_unchanged()
    evidence.append(
        dict(backbone=b, order=o, frozen_backbone_sha256=digests[0], parent=parent.provenance)
    )
data = out / "frozen-data"
data.mkdir()
manifest = freeze(data, Path("data/wikitext2"))
assert (
    manifest["checksums_sha256"]["validation.bytes"]
    == "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f"
)
result = dict(
    status="PASS",
    model_forwards=0,
    training_updates=0,
    parents=evidence,
    new_panel_sha256=manifest["checksums_sha256"]["validation.bytes"],
)
(out / "review.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        dict(
            status="PASS",
            parents=len(evidence),
            model_forwards=0,
            training_updates=0,
            new_panel_sha256=result["new_panel_sha256"],
        )
    )
)
