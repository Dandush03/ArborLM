# Commit-hash mapping after commit-message rewrite

The five commits of this work were first created locally with multi-line messages and co-author trailers. The repository owner's global pre-push hook requires single-line messages without such trailers, so before the single push the messages were reduced to their first line and the commits re-signed. **No file content changed**: each commit's Git tree hash is identical before and after, and author timestamps are preserved. Only the commit hashes changed.

Documents and run manifests written before the push cite the original hashes (for example the freeze `a786c5d` and the raw-records commit `c389fe7`). Use this table to resolve them. The tree hash is the content identity and can be checked with `git rev-parse <commit>^{tree}`.

| Original commit (cited in records) | Pushed commit | Tree hash (unchanged) | Author time | Subject |
|---|---|---|---|---|
| `43730f195bc3f12f9c6c5f6e105fcd665844b35f` | `cf591e39e65a9e59a0671a0aaf180f3c8a9eb603` | `074c0b7da5050f6fb1f551d23150baee55dd18d3` | 2026-11-13T09:46:43-05:00 | P5 Claude-workflow review; propose P6-E/P6-Q (ADR-0011) and governance amendment (ADR-0012) |
| `981ce729261f8a606c635a7d785bdb840d5e4c2a` | `b79ad34e94f70b6d85834c8c9dfb886d0b1892c1` | `24ef53b128f9ac40be69f52e7f606764b55f5a25` | 2026-11-13T10:09:16-05:00 | ADR-0011: record human approval and pre-outcome engineering clarifications |
| `a786c5d1abba2957d0a28f4aa7064ca230e96ddc` | `9a9c132576d6010b82f48b161ed9087c6743c390` | `4a986763744cebdb7715057989d219b58f72589e` | 2026-11-13T12:36:53-05:00 | P6 freeze: P6-E and P6-Q implementation, tests, pre-freeze audit and decisions |
| `c389fe7282eaaf45cc491921ece0b073617abb77` | `b34be2cec05b96d1ab595182dd688b1b9064d44e` | `21ba1f36ebb8ff4dd7f1f19868aa081a005312e1` | 2026-11-13T13:34:34-05:00 | P6: raw and compact records of the single registered P6-E and P6-Q runs |
| `718f62047f5112ded16116a162a538d68fd32f02` | `505bb95603bae904a84448c47cfbdbabc5e14827` | `efd8eef3bb10e16f1d0812057a9d811350ef1009` | 2026-11-13T13:57:08-05:00 | P6 results review, independent recomputation, outcome record; post-run test-only repair |

The original commits remain on the local branch `backup/claude-p5-review-p6-proposal-before-message-rewrite`, which was not pushed. The fuller original commit messages are reproduced in the pull-request description and in ADR-0011 sections 7 and 8.
