# Independent P5 data and parent preflight audit

This audit independently reconstructed the pinned train/validation selection from raw Parquet and verified all nine P4 baseline checkpoint parents against their P3 step-1024 disabled-throughout controls. It imported no ArborLM modules and executed no model forwards, training, evaluation, or timing.

## Results

- P5 validation ranks 2048–2559 contain 512 rows with bytes SHA-256 `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`; selected-ID record SHA-256 `28e6360c51d2a838728bd6912d5694aea21da8a95210f54ff8377b7b29e83edb`.
- The raw-Parquet reconstruction matched P1, P2, P3, and P4 panel hashes and the registered first-2048 P4 selected-ID record. The train first-4096 bytes hash matched `1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07`.
- Exact overlap was zero between the new panel and all four earlier panels, and between the new panel and the full train candidate set. A scan of local experiment/result JSON range records found no earlier declaration of the proposed P5 interval.
- All 9 P4 baseline state/index hashes matched actual files and compact indexes; each P4 frozen tensor map was byte-identical to the mapped P3 step-1024 backbone, with 27,392 parameters, frozen flags, and no optimizer. P4 parent provenance and numerical environment records were consistent across the matrix.
- Root independently reran the published checker and compared all 512 selected rows, all nine parent hashes, P3 tensor identities, and the panel hash; all matched.

The complete machine-readable output, selected row IDs, hashes, and parent map are in `independent-data-parent-audit.json`. Raw stdout/stderr are retained alongside it. The stderr contains only a local PyTorch warning about optional NumPy being unavailable.

## Temporal scope of the prior-use scan

The scan for earlier declarations of ranks 2048–2559 was performed against the recorded pre-freeze repository/results inventory. P5 preflight manifests now exist and intentionally declare that interval, so rerunning the historical prior-use scan against the current tree will find P5 itself. Preserve this report and its original inventory/result snapshot as the evidence for the pre-freeze scan; do not interpret a post-freeze scan as evidence of prior use.

## Reproduction

Run from the repository root with the pinned local dataset and registered P3/P4 artifacts present:

```sh
uv run --locked --extra pilot python results/p5-preflight-2026-11-13/independent-data-parent-audit.py
```

Ruff check passed for the audit script. This establishes data/parent engineering identities only. It is not a P5 model preflight, scientific validation, or Astra review. P5 training, evaluation, and timing remain unauthorized until root accepts the complete engineering preflight and freeze.
