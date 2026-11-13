"""Fixed, generated symbolic data; train and validation motifs are disjoint."""

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import Tensor

from .io import atomic_write, canonical_json, sha256

TOKENIZER = {
    "version": "integer-identity-v1",
    "ids": list(range(16)),
    "mapping": "integer identity",
    "special_tokens": [],
    "padding": False,
}
GENERATOR = {
    "version": "sha256-cycle8-v1",
    "digest": "SHA-256",
    "input": "arborlm-e0-v1:{seed}:{counter}",
    "encoding": "UTF-8",
    "counter_initial": 0,
    "motif": "first eight digest bytes modulo 16",
    "duplicates": "reject motifs already accepted in either split",
    "generation_order": ["train", "validation"],
    "splits": {"train": {"seed": 101, "rows": 256}, "validation": {"seed": 202, "rows": 64}},
    "row": "cyclic repeat of motif, truncated to 33 token IDs",
}


@dataclass(frozen=True)
class Dataset:
    train: list[list[int]]
    validation: list[list[int]]

    def files(self) -> dict[str, bytes]:
        return {
            "train.json": canonical_json(self.train),
            "validation.json": canonical_json(self.validation),
            "tokenizer.json": canonical_json(TOKENIZER),
            "generator.json": canonical_json(GENERATOR),
        }

    def checksums(self) -> dict[str, str]:
        return {name: sha256(content) for name, content in self.files().items()}

    def record(self, directory: Path, *, verify_existing: bool = False) -> None:
        files = self.files()
        manifest = {
            "name": "arborlm-e0-symbolic-motifs",
            "generator_version": GENERATOR["version"],
            "tokenizer_version": TOKENIZER["version"],
            "provenance": "ArborLM repository-generated fixture",
            "code_license": "Apache-2.0",
            "third_party_dataset": False,
            "external_license_grant_inferred": False,
            "rows": {"train": len(self.train), "validation": len(self.validation)},
            "checksums_sha256": self.checksums(),
        }
        files["dataset_manifest.json"] = canonical_json(manifest)
        if verify_existing:
            for name, content in files.items():
                if sha256((directory / name).read_bytes()) != sha256(content):
                    raise ValueError(f"dataset checksum mismatch: {name}")
        else:
            for name, content in files.items():
                atomic_write(directory / name, content)


def generate_dataset() -> Dataset:
    accepted: set[tuple[int, ...]] = set()

    def split(seed: int, count: int) -> list[list[int]]:
        rows: list[list[int]] = []
        counter = 0
        while len(rows) < count:
            digest = bytes.fromhex(sha256(f"arborlm-e0-v1:{seed}:{counter}".encode()))
            motif = tuple(byte % 16 for byte in digest[:8])
            counter += 1
            if motif not in accepted:
                accepted.add(motif)
                rows.append(list((motif * 5)[:33]))
        return rows

    return Dataset(split(101, 256), split(202, 64))


def next_token_batch(rows: list[list[int]]) -> tuple[Tensor, Tensor]:
    batch = torch.tensor(rows, dtype=torch.int64, device="cpu")
    if batch.ndim != 2 or batch.shape[0] == 0 or batch.shape[1] != 33:
        raise ValueError("E0 data rows must contain 33 tokens")
    return batch[:, :32], batch[:, 1:]
