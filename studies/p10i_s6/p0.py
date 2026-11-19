# ruff: noqa: E501
"""P10IS6 stage P0, parents (ADR-0031 section 7): the adapter identity gate on all nine old parents, then twelve new backbones (nine registered, three calibration). New training: needs the human lead's explicit approval (Decision 1 carries it).

``python -m studies.p10i_s6.p0 --train-bytes <WikiText-2 train.bytes of the P1 freeze> --out <dir>``: the file is the 4,096 ranked train chunks (hash-checked against ``p2_data.P1_TRAIN_SHA256``); ranks 0-2047 are the parents' training rows. The identity gate runs FIRST and a failure is an ENGINEERING STOP before
anything is trained. The record ``parents_record.json`` (key ``adapter_identity``, the digests, the declared re-use of control memory seed 201) is what the plan and the core gate read. Not exercised against the real files by the implementer.
"""

import argparse
import json
from pathlib import Path

import torch

from arborlm.io import file_sha256, write_json

from . import core, gates, parents


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - the lead's command (new training)
    from arborlm.p2_data import P1_TRAIN_SHA256

    ap = argparse.ArgumentParser(prog="studies.p10i_s6.p0")
    ap.add_argument("--train-bytes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo")
    a = ap.parse_args(argv)
    repo = Path(a.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    gates.configure_process()
    tb = Path(a.train_bytes)
    if file_sha256(tb) != P1_TRAIN_SHA256:
        raise core.EngineeringStop("ENGINEERING STOP — train.bytes does not hash to the recorded P1 train SHA-256")
    rows = torch.frombuffer(bytearray(tb.read_bytes()), dtype=torch.uint8).long().reshape(-1, 65)
    gate = parents.identity_gate(repo, rows, cfg)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if not gate["passed"]:
        write_json(out / "adapter_identity_FAILED.json", gate)
        raise core.EngineeringStop("ENGINEERING STOP — the adapter identity gate did not reproduce all nine old parents; nothing was trained (the human lead decides between an amended recipe and the alternative of open choice 3)")
    rec = {"adapter_identity": gate, "registered": parents.train_new_parents(cfg, rows, out, group="registered"), "calibration": parents.train_new_parents(cfg, rows, out, group="calibration")}
    write_json(out / "parents_record.json", rec)
    print(json.dumps({"parents_record": str(out / "parents_record.json"), "adapter_identity_passed": True}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
