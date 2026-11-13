# P2 independent artifact audit

- Scope: read-only engineering and artifact verification for the completed ADR-0007 run. This is not scientific interpretation, Astra validation, or human publication approval.
- Suite: `experiments/P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7`.
- Compact cell records: `results/p2-2026-11-12/`; local checkpoints and frozen data remain under the suite directory.
- Result: all 36 registered cells completed; no integrity or arithmetic discrepancy was found in the checks below.

## Artifact and execution checks

- Cell grid: 36 (27 learned cells and 9 paired controls); all terminal records report completed with return code 0.
- Per cell: exactly 256 ordered training events and 131,072 next-byte targets. Validation at steps 0 and 256 has 32,768 targets each. Total training targets: 4,718,592.
- Every cell has checkpoint 128 and 256 state files whose SHA-256 matches both its checkpoint index and result record; embedded step, cursor, target count, and cell identity match registration.
- Controls report identical initial/final frozen-memory hashes; checkpoint memory tensors at steps 128 and 256 also match fresh registered initialization. Control stored/trainable counts are 225,793/27,392; learned counts are 225,793/225,793.
- Diagnostics: learned cells have the four registered conditions in order; controls have enabled replay only. Each diagnostic records 32,768 evaluation targets, zero training targets, and unchanged parent checkpoint hashes. Enabled replay is bitwise identical; joint within-branch permutation satisfies the 1e-6 absolute tolerance.
- Independently regenerated all 27 value and joint permutation ID arrays from registered CPU RNG seeds; IDs and hashes match. Each order stream is the registered `torch.randperm(2048)`, appears identically in all 12 cells sharing that order, and covers rows 0..2047 exactly once.
- Frozen dataset manifest file checksums match. Training bytes SHA-256: `1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07`. P2 validation bytes SHA-256: `8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2` (512 rows / 32,768 targets). Acquisition says the deferred test split was neither acquired nor inspected.
- All cells share source archive and `source_sha256` `6fea4b684a364ef85c8cda6ea1df683f9e7f8332dd4645caf7094b620da02801`; lock, spec, config, and data-manifest identities are invariant. Recorded HEAD values vary across 17 commits, including the freeze commit; every post-freeze commit touched only `results/`.
- Source-state bookkeeping: 33/36 per-cell manifests set `dirty=true`; all 36 recorded `source.diff` files are empty and hash-valid, and the actual archived source bytes are identical. The dirty bit is therefore retained as a provenance caveat rather than treated as source equality evidence.

## Independently recomputed paired-cell arithmetic

D = disabled − enabled; P = values-permuted − enabled; G = paired control − enabled; S = paired control − disabled. Every `G = D + S` check over 27 learned cells is within 1e-12. Values below are reconstructed from raw intervention NLLs and the corresponding B/O control NLL.

| B | M | O | D | P | G | S |
|---:|---:|---:|---:|---:|---:|---:|
| 101 | 201 | 301 | 0.000108231 | 0.000043679 | 0.031574976 | 0.031466745 |
| 101 | 202 | 301 | 0.000257507 | 0.000293255 | 0.027331635 | 0.027074128 |
| 101 | 203 | 301 | 0.000008527 | 0.000064880 | 0.033347528 | 0.033339001 |
| 101 | 201 | 302 | -0.000070754 | -0.000202402 | -0.002386402 | -0.002315648 |
| 101 | 202 | 302 | 0.002338737 | 0.002466027 | -0.003041010 | -0.005379748 |
| 101 | 203 | 302 | -0.000042252 | -0.000087306 | 0.000327457 | 0.000369709 |
| 101 | 201 | 303 | 0.000163265 | 0.000212971 | -0.031203028 | -0.031366292 |
| 101 | 202 | 303 | 0.000419389 | 0.000467528 | -0.001398314 | -0.001817703 |
| 101 | 203 | 303 | 0.000060730 | 0.000059698 | -0.048181299 | -0.048242029 |
| 102 | 201 | 301 | 0.000538111 | 0.000556182 | -0.014146868 | -0.014684979 |
| 102 | 202 | 301 | -0.000157665 | -0.000117943 | -0.007802647 | -0.007644981 |
| 102 | 203 | 301 | 0.000113346 | 0.000054378 | -0.009914022 | -0.010027368 |
| 102 | 201 | 302 | 0.000084933 | 0.000029121 | 0.005712222 | 0.005627289 |
| 102 | 202 | 302 | 0.000404656 | 0.000241444 | 0.013557099 | 0.013152443 |
| 102 | 203 | 302 | 0.000093661 | 0.000286847 | 0.002842680 | 0.002749018 |
| 102 | 201 | 303 | 0.002531998 | 0.002415758 | 0.016710296 | 0.014178298 |
| 102 | 202 | 303 | 0.001285821 | 0.001326866 | 0.030026834 | 0.028741013 |
| 102 | 203 | 303 | 0.001371875 | 0.001459539 | 0.031645130 | 0.030273255 |
| 103 | 201 | 301 | 0.002499685 | 0.002419673 | 0.014658481 | 0.012158796 |
| 103 | 202 | 301 | 0.001297485 | 0.001289316 | 0.006607231 | 0.005309746 |
| 103 | 203 | 301 | 0.000094619 | 0.000188168 | 0.021105748 | 0.021011129 |
| 103 | 201 | 302 | 0.001366522 | 0.001306798 | -0.023086987 | -0.024453510 |
| 103 | 202 | 302 | 0.003419571 | 0.003406301 | 0.063023124 | 0.059603553 |
| 103 | 203 | 302 | 0.000153359 | 0.000194281 | 0.052808709 | 0.052655350 |
| 103 | 201 | 303 | -0.000697263 | -0.000656441 | 0.003323924 | 0.004021186 |
| 103 | 202 | 303 | 0.001094218 | 0.000900462 | 0.009580135 | 0.008485917 |
| 103 | 203 | 303 | -0.000007108 | -0.000106927 | -0.041259196 | -0.041252088 |

### Descriptive summaries

| Metric | Mean | Sample SD | Min | Max | Positive | Zero | Negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| D | 0.000693748 | 0.001008201 | -0.000697263 | 0.003419571 | 22 | 0 | 5 |
| P | 0.000685635 | 0.001002791 | -0.000656441 | 0.003406301 | 22 | 0 | 5 |
| G | 0.006731979 | 0.025953640 | -0.048181299 | 0.063023124 | 17 | 0 | 10 |
| S | 0.006038231 | 0.025615544 | -0.048242029 | 0.059603553 | 17 | 0 | 10 |

### Prespecified descriptive flags and factor decomposition

- Both D and P positive: 22/27.
- Both D and P at least 0.005: 0/27.
- Either D or P nonpositive: 5/27.
- Flags: consistent dependence `False`; heterogeneous useful dependence `False`; measured factor sensitivity `False`. All three are false.
- D marginal ranges: backbone 0.000664190; memory 0.000945885; order 0.000332065; combined interaction RMS 0.000858668. All are below 0.005.
- G marginal ranges: backbone 0.011154403; memory 0.015191942; order 0.015612490; interaction RMS 0.023140163. These are descriptive only.
- These are correlated cells from one corpus panel and shared controls; no p-values, confidence intervals, independence claim, or promotion inference is made.

## Audit execution

- Read-only artifact checks used `.venv/bin/python`, standard-library JSON/SHA-256 parsing, and `torch.load(..., weights_only=True)` for completed checkpoint artifacts. No training, diagnostics, or source/config/spec/test edits were performed.
- Python emitted its existing PyTorch warning that NumPy is not installed. The audit used tensor operations and standard-library hashing and did not require NumPy.
- Audit discrepancy list: none.
