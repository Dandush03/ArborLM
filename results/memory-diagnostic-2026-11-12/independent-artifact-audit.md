# Independent diagnostic artifact audit

Luna read raw per-cell results/events and checked current original checkpoint/index hashes against each diagnostic's preserved parent provenance. No evaluations or training were performed in this audit.

- 12/12 cells completed, each evaluating 32,768 targets with zero training targets; event logs contain only diagnostic evaluations.
- Original replay and joint-within-branch deltas are exactly zero in all three seeds.
- All current original state/index hashes match the pre-intervention identities; original checkpoint bytes are unchanged.
- Independently recomputed mean disabled delta is 0.0020039925973 and mean values-permuted delta is 0.0021469779313 nats/byte. Both are below the registered 0.005 threshold.
- All per-seed signs/magnitudes match the root analysis; no discrepancy found. Earlier promotion status remains failed and unchanged.

This is an engineering/artifact audit, not scientific or Astra approval. Root interpretation is separately recorded under the human reviewer exception.
