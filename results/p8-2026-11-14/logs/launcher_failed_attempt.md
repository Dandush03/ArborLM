# Failed launcher attempt (kept)

2026-11-14, about 04:36 UTC. The lead's first shell line for restore-gate → evaluate → P7-B reproduction stored the command prefix in a shell variable that zsh does not word-split, so all three commands exited 127 ("command not found") in under a millisecond. No stage started, no run directory was created and no data was read. The same three commands were then launched correctly, once. Recorded because failed attempts are kept.
