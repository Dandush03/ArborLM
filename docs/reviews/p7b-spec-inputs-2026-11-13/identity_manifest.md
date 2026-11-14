# P7-B spec inputs: identity manifest

Read-only identity manifest of the immutable inputs a proposed P7-B study would reuse. Identity only: no interpretation, no execution. Full detail: `docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.json`.

- Generated (UTC): 2026-11-13T22:24:30Z
- Model: claude-haiku-5-5

## Run IDs and stage manifest hashes

| stage | run ID | manifest.json sha256 |
|---|---|---|
| trace | `P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e` | `8632a26f0b1b61461cd1c9c16d280836adad5586b215042699e5c8c25d091075` |
| simulate | `P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b` | `d9397042ca7da5823cb29cb9f67c1bf74e51a6d2e77efcae72f5d9caf27eb876` |
| analyze | `P7AA-20261113T215004286617Z-1d1e2c7e136e466f9e423f94d58d602a` | `f1702854dbeafcd78703a16d9d371e02e03438fd94a752eab436d5acf009b108` |

Trace binaries: `experiments/P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e/traces/<label>/`.

## Totals

- Checkpoints: 81 total; by kind: fixed_tree 27, flat 27, learned_tree 27
- Trace files checked: 270 (expected 270); existing: 270; recorded sha256 == computed: 270
- Checkpoints with all files matching: 81 of 81
- Mismatches: 0
- Missing items: 0
- Simulate records read: 81; frequency-matched stream hashes: 243; P5 results read: 81; state sha256 matching P5 at step: 81; replay NLL equal to P5 final NLL: 81

## Overall hash

- sha256: `77dea76d96672b13336415ff325388c9c76d8e3b09cf25f2242d9cfe44e2a86a`
- Triples: 270, each `[label, role, recorded sha256]`, sorted by cell_index then role.
- Method: `triples [label, role, recorded_sha256] for every trace file entry, sorted by (cell_index, role) with role strings in ascending string order (calibration.branches < calibration.selected < evaluation.branches < evaluation.selected); serialized as json.dumps(triples, separators=(',', ':'), ensure_ascii=True) with no trailing newline; overall = SHA-256 of that string's UTF-8 bytes, lowercase hex.`

## NEEDS REVIEW

- P5 dense (27) and baseline (9) cells are not in the P7-A trace set and are excluded; the 81 checkpoints are the fixed_tree, flat and learned_tree cells (27 each).
- cell_index is recorded 0-based in the trace records (values 0 to 80, unique); it is used as-is for ordering.
- analyze stage (P7AA-20261113T215004286617Z-1d1e2c7e136e466f9e423f94d58d602a): only the manifest.json sha256 was taken; analysis.json was not inspected (not requested).
- trace binaries are under experiments/, which git check-ignore reports as ignored; they are not version-controlled and exist only as local files.
- trace stage manifest records astra_review = "NOT_PERFORMED" (literal value, not interpreted).
- trace stage manifest records human_approval = "ADR-0013 section 14: human approval of 2026-11-13 ('Approve as drafted'), revision 2 with the pre-outcome clarifications, as amended by section 14 items 8 to 14 (clarification 2 withdrawn)" (literal value, not interpreted).
- simulate stage manifest records astra_review = "NOT_PERFORMED" (literal value, not interpreted).
- simulate stage manifest records human_approval = "ADR-0013 section 14: human approval of 2026-11-13 ('Approve as drafted'), revision 2 with the pre-outcome clarifications, as amended by section 14 items 8 to 14 (clarification 2 withdrawn)" (literal value, not interpreted).
- analyze stage manifest records astra_review = "NOT_PERFORMED" (literal value, not interpreted).
- analyze stage manifest records human_approval = "ADR-0013 section 14: human approval of 2026-11-13 ('Approve as drafted'), revision 2 with the pre-outcome clarifications, as amended by section 14 items 8 to 14 (clarification 2 withdrawn)" (literal value, not interpreted).

## Per-checkpoint table

Sha256 values are the recorded values, shown as first 12 hex. Full values are in the JSON.

| cell | label | kind | P5 final NLL | state sha256 | eval-selected sha256 | calib-selected sha256 | all files match |
|---|---|---|---|---|---|---|---|
| 0 | b101-o301-flat-s501 | flat | 2.3409496657550335 | e3cb9050ca96 | c31b5bfab8d5 | 3892d13f7cdf | yes |
| 1 | b101-o301-fixed_tree-s501 | fixed_tree | 2.342264696955681 | 8da717412c64 | dd1df5846b92 | b1bab32ab146 | yes |
| 2 | b101-o301-learned_tree-s501 | learned_tree | 2.343716148287058 | a4a1361af7ea | d6a03ebd00f1 | d3644fcfb1f4 | yes |
| 3 | b101-o301-flat-s502 | flat | 2.3428814709186554 | 2f6e7c9f72a0 | 81c371aba27e | dbf1263e1193 | yes |
| 4 | b101-o301-fixed_tree-s502 | fixed_tree | 2.3413650318980217 | ca78ff026b2c | e01ee1f86754 | a00772f3a24b | yes |
| 5 | b101-o301-learned_tree-s502 | learned_tree | 2.343947123736143 | 11e033b1970b | c8a8625ac305 | 7347b48f0903 | yes |
| 6 | b101-o301-flat-s503 | flat | 2.344075158238411 | f090703a5f9a | 80307234e104 | 6b239e2ffbc7 | yes |
| 7 | b101-o301-fixed_tree-s503 | fixed_tree | 2.3432606272399426 | aed0a6405e4b | ee722149d83c | 8a3f946fe426 | yes |
| 8 | b101-o301-learned_tree-s503 | learned_tree | 2.3436701484024525 | a5c9bdc9c4e6 | a1b1af8550dc | ea5583b7344e | yes |
| 9 | b101-o302-flat-s501 | flat | 2.3451704680919647 | 0156811f3648 | 35b52b98f213 | 7d4704e2e88d | yes |
| 10 | b101-o302-fixed_tree-s501 | fixed_tree | 2.347589645534754 | 156605a3bdc5 | 57003837f3f6 | 83f01fb21873 | yes |
| 11 | b101-o302-learned_tree-s501 | learned_tree | 2.3488382287323475 | 0e4110bdb79d | cd6498579156 | 6b7ad7305f70 | yes |
| 12 | b101-o302-flat-s502 | flat | 2.347139548510313 | 07eb5cf6d83f | f1d89d72e455 | 36c5b4eac3ba | yes |
| 13 | b101-o302-fixed_tree-s502 | fixed_tree | 2.346570499241352 | fcbc9bb92e6f | 3dcad9175d08 | 2169e9d95eec | yes |
| 14 | b101-o302-learned_tree-s502 | learned_tree | 2.3465416952967644 | 67622843c369 | f3f363b6b764 | 66e186ef0158 | yes |
| 15 | b101-o302-flat-s503 | flat | 2.34827196970582 | c92f19096a6e | 9c92ce6882c1 | 3d5c4a29a3d4 | yes |
| 16 | b101-o302-fixed_tree-s503 | fixed_tree | 2.347669929265976 | 5cbf6194ee54 | 9470458ebbd6 | 7794a5ed2a84 | yes |
| 17 | b101-o302-learned_tree-s503 | learned_tree | 2.3504481613636017 | 3bc54c27afc2 | 79415485be66 | 842d88a3b152 | yes |
| 18 | b101-o303-flat-s501 | flat | 2.3318656347692013 | f92a390d5287 | dbc7bc211eeb | c327d6c55fdc | yes |
| 19 | b101-o303-fixed_tree-s501 | fixed_tree | 2.3283774703741074 | d71bfb76c454 | b448939bf5c1 | 3c27938e54a8 | yes |
| 20 | b101-o303-learned_tree-s501 | learned_tree | 2.3330789357423782 | 46cbb2ca572c | 016a9d7445db | cbeb17fe887f | yes |
| 21 | b101-o303-flat-s502 | flat | 2.3297587893903255 | 1f5f8c770aa2 | 9ba68fb8505d | b15ff42bc734 | yes |
| 22 | b101-o303-fixed_tree-s502 | fixed_tree | 2.331806182861328 | 5ed2d32f8e6c | cf18151fdae2 | d5b2ad7e90b0 | yes |
| 23 | b101-o303-learned_tree-s502 | learned_tree | 2.331391580402851 | 25d3fb6e9ab4 | 76e5d4526c43 | 5d8dfde7a8ed | yes |
| 24 | b101-o303-flat-s503 | flat | 2.330879181623459 | 2e4f43d7dc9b | f760db5263a9 | f59588a33aed | yes |
| 25 | b101-o303-fixed_tree-s503 | fixed_tree | 2.330566219985485 | 94c3e4cca0f3 | 39d443a86c2d | 7228a6735cae | yes |
| 26 | b101-o303-learned_tree-s503 | learned_tree | 2.3320956267416477 | 4884ee0a043a | e788ac082e48 | c13abda59f2c | yes |
| 27 | b102-o301-flat-s501 | flat | 2.345330871641636 | 2a692adb900b | d5592674dcff | d9e72cc11ade | yes |
| 28 | b102-o301-fixed_tree-s501 | fixed_tree | 2.344926968216896 | 7d9a9d3e2b8c | 9b9193e7e5e6 | 6c543fac706e | yes |
| 29 | b102-o301-learned_tree-s501 | learned_tree | 2.3448420129716396 | b6c9f6ea53d3 | 02c94d23eb86 | 91719e2beffb | yes |
| 30 | b102-o301-flat-s502 | flat | 2.343133918941021 | fa07b9edd7c2 | a66fbfddd366 | 4073f83438c6 | yes |
| 31 | b102-o301-fixed_tree-s502 | fixed_tree | 2.3464319854974747 | 6a29247ac127 | 49a31631a7b2 | fc5baebfaf2f | yes |
| 32 | b102-o301-learned_tree-s502 | learned_tree | 2.3457918614149094 | 173d476bac74 | 36bd0455d55c | fcdeb91b66cb | yes |
| 33 | b102-o301-flat-s503 | flat | 2.347969263792038 | a607855bb706 | d06d4794e20b | fd2ee7c78dd9 | yes |
| 34 | b102-o301-fixed_tree-s503 | fixed_tree | 2.3445779234170914 | 21235981a8cb | 90e9d67648c5 | f1114e2aceac | yes |
| 35 | b102-o301-learned_tree-s503 | learned_tree | 2.3469155244529247 | 00f9aafc9872 | 60c6a361dd93 | 090f734f3c06 | yes |
| 36 | b102-o302-flat-s501 | flat | 2.3551100604236126 | c3eb02086429 | cc0290a615b2 | a2f323030c77 | yes |
| 37 | b102-o302-fixed_tree-s501 | fixed_tree | 2.3556465432047844 | 28c39717f917 | 5065c976ec4e | dc55434616dd | yes |
| 38 | b102-o302-learned_tree-s501 | learned_tree | 2.3531961776316166 | 4474a888f135 | c64de36cf911 | 1cad950bf830 | yes |
| 39 | b102-o302-flat-s502 | flat | 2.35405395925045 | 697a7593f41c | aef457ed41df | b483e39ba5fc | yes |
| 40 | b102-o302-fixed_tree-s502 | fixed_tree | 2.3538060300052166 | eca58be8599c | 4e15634a414a | 2695e09a0e0b | yes |
| 41 | b102-o302-learned_tree-s502 | learned_tree | 2.354742880910635 | 90cf64fc6bac | 60c1f96fb16a | e90032ae59d4 | yes |
| 42 | b102-o302-flat-s503 | flat | 2.353546939790249 | d53153c300f8 | 5dab7c682919 | c53028c7103a | yes |
| 43 | b102-o302-fixed_tree-s503 | fixed_tree | 2.351746443659067 | 3e58c0ec0621 | 49c95c9abfa3 | f9abcf3c118e | yes |
| 44 | b102-o302-learned_tree-s503 | learned_tree | 2.3519374802708626 | 25a10dc84514 | bc5088cffec9 | e0c5e5e839df | yes |
| 45 | b102-o303-flat-s501 | flat | 2.2991468384861946 | e0c398d11d89 | 894317c8e150 | c50845cc26a4 | yes |
| 46 | b102-o303-fixed_tree-s501 | fixed_tree | 2.299361888319254 | 0ba249a38596 | 999c0c5c1259 | 7855847fb167 | yes |
| 47 | b102-o303-learned_tree-s501 | learned_tree | 2.2989170514047146 | 234e78b167a2 | 443b59dc55b2 | 813b20416b1c | yes |
| 48 | b102-o303-flat-s502 | flat | 2.298189576715231 | 8cf4d210c497 | f9d0b8056cf0 | 6c74a3f04611 | yes |
| 49 | b102-o303-fixed_tree-s502 | fixed_tree | 2.3016174100339413 | 4f812aec307a | 0fe88d6e32c7 | 95c57b2ef04d | yes |
| 50 | b102-o303-learned_tree-s502 | learned_tree | 2.2999987192451954 | 591d9e3be465 | a11f1ba6720f | ea6e93643ee7 | yes |
| 51 | b102-o303-flat-s503 | flat | 2.3000066578388214 | 9426ff228334 | 69e806b3e2c2 | d30081ee3e3c | yes |
| 52 | b102-o303-fixed_tree-s503 | fixed_tree | 2.3031235449016094 | 3b5758b98c3f | 7b4176e4f216 | 382d565d8be4 | yes |
| 53 | b102-o303-learned_tree-s503 | learned_tree | 2.299691516906023 | 79755f7d4575 | 6cfafa15d449 | b89aa96be642 | yes |
| 54 | b103-o301-flat-s501 | flat | 2.338084999471903 | cc9ff55c4b5c | fed09daf81aa | 84a3d1c3438e | yes |
| 55 | b103-o301-fixed_tree-s501 | fixed_tree | 2.3405484445393085 | c3cf7f86a477 | 7f2cbb492a56 | d2205c8310fc | yes |
| 56 | b103-o301-learned_tree-s501 | learned_tree | 2.340602733194828 | 61c8a48102c2 | 198123fe3980 | 6dcc86d6fcde | yes |
| 57 | b103-o301-flat-s502 | flat | 2.337301906198263 | 92dbe5205231 | ba7f8635c1ee | bb433ba0a185 | yes |
| 58 | b103-o301-fixed_tree-s502 | fixed_tree | 2.3380714766681194 | d5f36021f6e3 | 4a66fb7c9cc5 | 11b7fb10fe1d | yes |
| 59 | b103-o301-learned_tree-s502 | learned_tree | 2.33848213031888 | 57031bd53372 | 0615aa646d47 | dcef40b420ce | yes |
| 60 | b103-o301-flat-s503 | flat | 2.3386850468814373 | e970267d2093 | 882f85ca6156 | e799cee44409 | yes |
| 61 | b103-o301-fixed_tree-s503 | fixed_tree | 2.336878601461649 | f3736d80896f | aff678104c6a | 4a24bf3c4f53 | yes |
| 62 | b103-o301-learned_tree-s503 | learned_tree | 2.3404549062252045 | a5cf0bb22d43 | 1c5e7b9b7f77 | 8caea0a62786 | yes |
| 63 | b103-o302-flat-s501 | flat | 2.2948864810168743 | 9a426c3288c9 | 7955f98d94cb | 43a9e59f7281 | yes |
| 64 | b103-o302-fixed_tree-s501 | fixed_tree | 2.3005886785686016 | 57bd683df2e6 | a7e34a044471 | 9c7082f7933e | yes |
| 65 | b103-o302-learned_tree-s501 | learned_tree | 2.2980961576104164 | 3ad5065438dd | 2cd7199bbc84 | f19cad872aea | yes |
| 66 | b103-o302-flat-s502 | flat | 2.2962247878313065 | 7809ed9617dc | f2d9d6aa86c1 | d0b412e6f890 | yes |
| 67 | b103-o302-fixed_tree-s502 | fixed_tree | 2.2995293512940407 | c3f52229766e | 3c582d7200e5 | 1851e9fc24fd | yes |
| 68 | b103-o302-learned_tree-s502 | learned_tree | 2.298950109630823 | cb76644966d0 | 06c3c61732e9 | aa103f89e758 | yes |
| 69 | b103-o302-flat-s503 | flat | 2.294914860278368 | 2c8e72c0ab7c | c519463beeea | 0d011214dcdc | yes |
| 70 | b103-o302-fixed_tree-s503 | fixed_tree | 2.2985712960362434 | 2f381d50e4dd | a7464c335b48 | 618ac9eabaa9 | yes |
| 71 | b103-o302-learned_tree-s503 | learned_tree | 2.3001260310411453 | 61d58071e112 | baed76b115e9 | 61bb5c1d4325 | yes |
| 72 | b103-o303-flat-s501 | flat | 2.3494262285530567 | 9fcb28306a32 | 3d10faecd0bb | 7ade9f03f462 | yes |
| 73 | b103-o303-fixed_tree-s501 | fixed_tree | 2.353515774011612 | e3f914b023e8 | 6d136e5f6614 | 6fb7f6748c94 | yes |
| 74 | b103-o303-learned_tree-s501 | learned_tree | 2.353934284299612 | 039366f82968 | 4bca18621377 | ae9244c6a559 | yes |
| 75 | b103-o303-flat-s502 | flat | 2.350401919335127 | 43fd7bcd4eef | 5975d9f9ab6d | 5b98df741ef3 | yes |
| 76 | b103-o303-fixed_tree-s502 | fixed_tree | 2.3507665134966373 | aed5fd27a2ac | 7c26093ad694 | fc069159bc90 | yes |
| 77 | b103-o303-learned_tree-s502 | learned_tree | 2.353295397013426 | 9d170c1977c4 | 4e494c3aba6d | 1f26d3e865e4 | yes |
| 78 | b103-o303-flat-s503 | flat | 2.35227482765913 | eebe2fdfc02b | 9c343b452b87 | 8dacab80299d | yes |
| 79 | b103-o303-fixed_tree-s503 | fixed_tree | 2.3522463850677013 | f609876f0069 | 9a2e47e68b0a | d47ecd5b3971 | yes |
| 80 | b103-o303-learned_tree-s503 | learned_tree | 2.3534763902425766 | 11cd090d388a | 6c72c52f0c5f | b2fb6bb084e1 | yes |
