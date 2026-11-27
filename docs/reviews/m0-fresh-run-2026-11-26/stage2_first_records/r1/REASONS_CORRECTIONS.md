# Corrections to REASONS.md (line citations only; no judgement changes)

`REASONS.md` was written before its line citations were checked against the files; it is kept as written (no file is edited). These citations replace the wrong ones. All are lines of the implementation worktree at HEAD `128a02a7`, files unchanged since `7cd0ac5a`.

- spatial_grid_walk_r5: "blocked moves 3+L//3 (213-214)" should read (212-213: `nblock` 212, `length` 213). "blocked moves are only into wall cells inside the grid (215-224, 257-259)" should read (217-224 build `walls` from in-grid wall neighbours; 252-260 insert the blocked moves).
- swap_tracking_r5: "rotation text (434)" should read 436; "the options are all objects (411, 437)" should read (411, 438).
- venn_counting_r5: "every intersection ... is stated (365-371)" should read 372-375 (`inter` 363-364, sizes 366 and the pair, triple and quad figures after it); "the convention sentence (373)" should read 377; "the key ... (366)" should read 371.
