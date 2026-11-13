# Independent engineering audit of P1 raw artifacts

Auditor: Luna subagent `/root/luna_contract_audit`, requested by the authorized root reviewer after the trial. Read-only audit; no training or artifact edits. This is not independent Astra scientific validation.

- All 18 expected variant/seed pairs appear once, in registered order, with completed status.
- Every cell contains 256 ordered training events, 131,072 targets and two evaluations of 32,768 targets. Total: 4,608 optimizer steps and 2,359,296 training targets. Loss and gradient-norm records are finite.
- Each checkpoint hash in the result and index matches its actual local `state.pt` bytes. Frozen dataset checksums, config/spec/data approval identities and lock hashes match the recorded suite.
- Independently recomputed means/sample standard deviations and paired deltas match `analysis.json`. Mean improvement over small dense is 0.0092854773, missing 0.01 by 0.0007145227. All other registered screen gates pass. All three learned routers have 256 nonzero-gradient steps and nonzero parameter movement.

## Traceability exception

The seed-44 learned-tree cell records Git commit `f231e2e`, while the suite and other 17 cells record `0b0555c`. This occurred because the first seed's result-only checkpoint was committed/pushed during the running suite at the human's request. The auditor verified that the intervening diff contains only `results/` paths; **all 18 source archives have the same SHA-256**, and config/spec/data/lock hashes match. There was no executed-source change. Keep both commit records; do not rewrite them to imply a single Git HEAD throughout the suite.

Scientific interpretation remains the root reviewer's responsibility under the recorded human exception. The failed promotion gate is unchanged.
