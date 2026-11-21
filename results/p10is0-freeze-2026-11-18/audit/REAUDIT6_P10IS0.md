# P10-I-S0: audit of 45d97ff and 4b2523f (diff ca0a148..4b2523f), for the rebind ruling and the freeze

Auditor: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. I did not write this code. `Astra review: NOT_PERFORMED`. This is independent engineering evidence, not Astra validation and not a human approval.

**Verdict: CONFIRMED — SAFE TO REBIND.** Nothing in 45d97ff..4b2523f computes, selects or reads a Stage R measurement, duration, flag, extension decision or seed, so Stage R's 6 h stand under a rebind. Two REQUIRED fixes come before the freeze: F1 (the leak guard is weaker where it matters) and F2 (the rebind can launder a change unless the ruling pins it). Both can be made within the same three-file rebind scope; neither needs a rerun of Stage R.

## Environment and commands
- Scratch at `<S0 worktree>/experiments/_scratch/audit6/` (git-ignored), with a copy made by `git archive 4b2523f`; deleted afterwards. One synthetic sealed directory at `/Users/daniellaloush/dandush03/ArborLM-sealed/audit6-synth/` (synthetic data only), because the code refuses a sealed directory inside a working tree, which I confirmed; deleted afterwards.
- I did not touch the real run directory or sealed directory. I opened `freeze/durations.json` read-only once, to read its public `code_identity`. No sealed value, no registered seed, no git write, no network. One process at a time, every command under `timeout`. CPython 3.12.14, the locked torch, macOS arm64.

| Command (from the copy, `PYTHONPATH=$PWD uv run --locked python …`) | Result |
|---|---|
| a read-only Python check: hash every file of `durations.json`'s `code_identity` (71 files) at ca0a148, 45d97ff and 4b2523f (`git show`) | **Stage R ran under exactly 45d97ff** (0 files differ). 4b2523f differs in `drivers.py`, `sealed.py` and `stages.py` only; ca0a148 differs in `rehearsal.py`, `sealed.py` and `stages.py`. The working tree equals 4b2523f |
| `guard.py` (adversarial probes) | below, `out/guard.txt`, `out/compounds.txt` |
| `status.py <copy> <synthetic sealed dir>` | below, `out/status.txt` |
| `pytest tests/test_p10is0_guard.py tests/test_p10is0_reaudit4.py -q` | 18 passed |

## 1. The guard (`sealed.names_a_measure`, `validate_public`)
**What the opaque rule skips.** The key is split into parts on `/`, `\` and `.`. A part is skipped when it fully matches `^[A-Za-z]?[0-9a-f]{8,}$`: at most one letter of any case, followed by eight or more lowercase hex digits. Because `a`, `c`, `e` and `f` are hex digits, these all ride through: `acc12345678`, `Acc12345678`, `accdeadbeef`, `acc0ffee`, `acce55ed0`.

**Other parts** are tokenised, and a part is refused only if a token *starts with* a stem, or two adjacent tokens form `m p`, `m h` or `plateau value`. The old rule refused a stem anywhere in the key. So lowercase compounds that the old rule refused now pass. I checked 14 names: `trainloss`, `meanacc`, `valacc`, `testacc`, `panelaccuracy`, `probecorrect` and `hloss` give names_a_measure = False, while the old substring rule gives True for all of them. `Xacc` also passes now. `mp`, `mh` and `plateauvalue` passed under both rules. `m.p` and `m/p` pass because the pair check works within one part only.

**What still refuses:**
- `meanAcc`, `x_acc`, `train_loss`, `TrainLoss`, `recall_at_1`, `m_p`, `mP`, `m-p`.
- A float under any key that is not a time, rate, memory or load key, including under a skipped opaque key: `/identity/acc12345678: 0.951` is refused.
- Any hashes-map value that is not a 64-hex string (strings like "0.951", dicts, lists).
- `cal/accuracy.json` as a hashes-map key.

**What gets through:**
- An int or string value under an opaque-shaped key, or under any free-key map: `{"identity": {"acc12345678": 951}}` is ACCEPTED. Ints and strings were never value-checked.
- A number encoded as 64 hex in a hashes map (deliberate encoding only).
- `labels: ["accuracy 0.951"]` and any string as `sealed_digest`.

No current code path builds such keys or values. Stage R's completion line has fixed keys: `stage, status, path, sha256, labels, count, sealed_digest`.

**F1 REQUIRED (before the freeze; `sealed.py`, inside the rebind scope).** The fix for one false positive (an opaque task id containing `acc`) removed the substring protection for every non-opaque name.
- Restore the old substring test on every part that is not an exact known opaque shape.
- Restrict the opaque shapes to those the code produces: a task id `^t[0-9a-f]{14}$`, a 64-hex digest, and the fixed file-name patterns.
- Add the compound names above to the tests.

## 2. `sealed_digest`, `count` and `stage-r-status`
**Digest and count.** The digest is SHA-256 over the canonical JSON of `{relative path: SHA-256 of bytes}`, which I verified equal to my recomputation. It reveals nothing beyond file identity (a hash of hashes). `count` is the number of sealed files, wave-level information already public. Neither the digest nor the per-file hashes it covers can be inverted to values: the point files hold floats beside integer counts, so a dictionary search is not feasible.

**`stage-r-status`** on a synthetic finished Stage R with a removed cell type and condition-4 flags (6 events):
- `durations.json` unchanged in bytes and mtime; every sealed file unchanged in bytes and mtime; no access-log entry, so no sealed read.
- `EVENT_1..6.md` byte-equal to what `write_events` (the clean finish) writes from the same record; a second call writes nothing; the completion line passes the guard.
- The template is duplicated in `write_events_numbered`. Advisory A1: share it.

## 3. Every changed function, 45d97ff..4b2523f (Stage R's identity is 45d97ff)
| File | Change | Touches computation? |
|---|---|---|
| drivers.py | `emit_stage_r_completion` (new): builds and prints the completion line | No: hashes file bytes, prints |
| drivers.py | `cmd_stage_r_status` (new): reads `durations.json`, runs `ladder.events`, writes missing EVENT files, prints | No (verified read-only) |
| drivers.py | `write_events_numbered` (new): EVENT text | No |
| drivers.py | `RULING_COSMETIC_FILES` and `cmd_rebind_identity` (new): rewrite `code_identity` | No measurement. It writes `durations.json`'s identity field only (see F2) |
| drivers.py | `cmd_stage_r`: its final `sealed.emit(...)` call replaced by `emit_stage_r_completion` | No: after `durations.json` and the events are written |
| sealed.py | `WAVE_LIMIT_SENTENCE` wording (45d97ff, already in Stage R's identity) | No |
| sealed.py | `PUBLIC_KEYS` (+`sealed_digest`, `sealed_files_sha256`); `OPAQUE_ID`, `NAME_TOKENS`, `HEX64`, `MEASURE_STEMS`, `MEASURE_PAIRS`, `HASH_MAPS`; `names_a_measure` (new); `validate_public` (rule) | No: called only on public output (`emit`, `work_timing`, `cmd_a0_memory`, the rehearsal record). A stricter or looser guard can only refuse or allow a print; it cannot change a value. `write_sealed`, `read_sealed`, `sealed_dir`, `sealed_hashes` and `ALLOWED_READERS` are unchanged |
| sealed.py | `hashes_digest` (new) | No |
| stages.py | parser: `stage-r-status` and `rebind-identity` subcommands; `main` dispatch to them | No |

`run_waves`, `stage_r_extensions`, `entry_for`, `final_entry`, `stage_r_entry`, `read_state`, the ladder, the seeds, `items.py` and `adapter.py` are untouched in the range. 45d97ff's own changes (`rehearsal.py`, `sealed.py` wording, the `stages.py` `--sealed-dir` flag, README) are already inside Stage R's identity, so they need no rebind. `README.md` is not a frozen input (only `*.py`).

## 4. `rebind-identity`
**Scope checks work.** A changed `items.py` → refused ("files outside the ruling's scope differ … ['studies/p10is0/items.py']"). A ruling file outside `results/` → refused.

**But laundering is possible.** `drivers.py` holds science as well as output code: `run_waves`, `stage_r_extensions` (the extension rule), `entry_for`/`final_entry` (T and labels in `durations.json`), `cmd_caps`, `cmd_x8`, `verify_manifest`, `worker_main`. A synthetic edit appended to `drivers.py` was rebound with status COMPLETE. The command checks only that the ruling file exists under `results/`. It does not check the ruling's content, that it is committed, or that it names this diff.

**The record** (`freeze/durations_identity_rebind.json`) holds `old_identity`, `changed_files`, `ruling_file`, `ruling_sha256` and `utc`. The new hashes are only in the rewritten `durations.json`. The record is not in the frozen-input list (`frozen_paths`: package `*.py`, `plan`, `durations` and `stage_caps` only).

**Binding afterwards.** The freeze hashes the rewritten `durations.json`. `check_code_identity` and the registered stages then bind to the new identity and refuse any later change. Write the candidate plan after the rebind (its `durations_sha256` changes), then rehearse and freeze.

**F2 REQUIRED.**
- **What the ruling file must contain:** Stage R's identity commit (45d97ff) and the new commit (4b2523f, or the commit carrying F1); for every changed file, its old and new SHA-256; this audit's function list (section 3) with the statement that no listed change computes, selects or reads a Stage R measurement, duration, flag, extension decision or seed; the auditor's report path; and the ruler's name.
- **What the command must verify:** that the ruling's old and new hashes equal `durations.json`'s identity and the current files; refuse otherwise, so that one ruling cannot cover a later edit. Require the ruling file to be committed. Store the new hashes in the record, and add the record to the frozen inputs (or commit it with the ruling).

## 5. 45d97ff: sealing the rehearsal cell records
- The real rehearsal phase now writes its rehearsal-draw cell records under `<sealed>/sealed/rehearsal/` (it needs `--sealed-dir`).
- Public `rehearsal_real.json` / `rehearsal.json` pass `public_rehearsal_record`: top-level keys from a 21-key whitelist, stage keys from `status, seconds_per_update, peak_rss_bytes, evaluation_wall_seconds, items, stdout_lines, passed`, platform keys from the 7 platform fields. Anything else refuses the whole record. The whitelist is tight and holds no accuracy, loss or probe key.
- Nothing later reads the rehearsal cell records: the timing rates come from `timing/rates.json` and the stage 3 records, which stay public. The phase's time is charged to the `gates` group, which feeds P.

## 6. Other
- **A1 ADVISORY:** the duplicated EVENT template; share it so the two cannot diverge.
- **A2 ADVISORY:** `hashes`-map keys list the sealed file names, which show the exposures each run reached. That is decision-level information, already public in `durations.json` by the time such a map is published (the freeze record).
- **E3 stands** (the checker copy excludes P10-I-R's files; the definition of RATIO ABOVE 1): PENDING LEAD REVIEW.

## Appendix: scripts (verbatim; scratch deleted)

### guard.py

```python
"""Adversarial probes of sealed.names_a_measure / validate_public at 4b2523f (no sealed value involved; synthetic inputs only)."""
import json
from studies.p10is0 import sealed
def v(obj):
    try:
        sealed.validate_public(obj); return "ACCEPTED"
    except Exception as e:
        return "refused: " + str(e)[:70]
keys = ["acc12345678", "accdeadbeef", "acc0ffee", "acce55ed0", "t1af0a449caccd5", "a0123456789", "bad1dea5", "deadbeefcafe", "Acc12345678", "acc_12345678", "m_p", "mP", "m.p", "m/p", "m-p", "meanAcc", "accuracy", "recall_at_1", "lossy", "glossary", "x_acc", "Xacc", "plateau_value", "plateauValue", "precise", "accept", "access", "bitsy", "correction", "curves2", "entropy0", "margin1", "nll", "c0rrect", "4cc", "ac_c"]
res = {k: sealed.names_a_measure(k) for k in keys}
probes = {
 "opaque-acc key in identity map, float": {"identity": {"acc12345678": 0.951}},
 "opaque-acc key in identity map, int": {"identity": {"acc12345678": 951}},
 "opaque-acc key in identity map, str": {"identity": {"acc12345678": "0.951"}},
 "opaque-acc key in cell_types map, nested dict": {"cell_types": {"acc12345678": {"e_star": 951}}},
 "hashes key with measure path": {"hashes": {"cal/accuracy.json": "0" * 64}},
 "hashes key opaque acc path": {"hashes": {"accdeadbeef/acc12345678.json": "0" * 64}},
 "hashes value non-hex": {"hashes": {"x.json": "0.951"}},
 "hashes value 64-hex encoding a number": {"hashes": {"x.json": ("%064x" % 951)}},
 "hashes value nested dict": {"hashes": {"x.json": {"acc": 0.9}}},
 "hashes value list": {"hashes": {"x.json": ["0" * 64]}},
 "sealed_files_sha256 nested map key": {"sealed_files_sha256": {"a/b": "f" * 64}},
 "count int": {"count": 951},
 "list of floats under labels": {"labels": [0.951]},
 "labels string with value": {"labels": ["accuracy 0.951"]},
 "float under skipped key in shapes": {"shapes": {"acc12345678": 0.95}},
 "int under shapes": {"shapes": {"accuracy": 951}},
 "sealed_digest any string": {"sealed_digest": "accuracy=0.951"},
}
print(json.dumps({"names_a_measure": res, "validate_public": {k: v(o) for k, o in probes.items()}}, indent=1))
```

### status.py

```python
"""stage-r-status on a synthetic finished Stage R (scratch copy only; no real file): durations.json and the sealed directory unchanged (bytes and mtimes),
no sealed read logged, the events equal those a clean finish writes, the completion line passes the guard; rebind-identity scope and record."""
import contextlib, hashlib, io, json, os, sys
from pathlib import Path
from arborlm.io import write_json
from studies.p10is0 import core, drivers, ladder, sealed
from studies.p10is0.plan import StageRefused
repo, base = Path(sys.argv[1]), Path(sys.argv[2])
rd, sb, ev1, ev2 = base / "run", base / "sealedbase", base / "events-status", base / "events-clean"
rd.mkdir(parents=True); (rd / "TEST_PROFILE").write_text("t\n")
ctx = drivers.Ctx(repo, rd, registered=False, sealed_dir=sb)
for i in range(3):
    sealed.write_sealed(sb, f"8K-16K-A6-c1-r0-e{8*2**i}.json", {"obs": {"a": [900 + i, 1000]}, "exposures": 8 * 2**i})
cfg = ctx.cfg
ent = {"e_star": 8, "t_exposures": 16, "convergence": "SHOWN", "flat_below_floor": False, "extension": "none", "reference_flags": {"cond4": True, "other": []}, "reference_flags_computed": True, "reference_below_floor_at_t": [], "reference_nonfinite": False, "nonfinite_in_rehearsal": False, "removed": False, "labels": []}
entries = {ct.name: dict(ent) for ct in core.cell_types(cfg)}
entries["8K/8K"]["reference_flags"] = {"cond4": False, "other": [3]}; entries["8K/8K"]["removed"] = True
rec = ladder.durations_record(entries, drivers.code_identity(repo)); rec["attempt"] = 0
dp = repo / core.DURATIONS; dp.parent.mkdir(parents=True, exist_ok=True); write_json(dp, core.jsonable(rec))
drivers.write_events(ev2, ladder.events(entries, core.cell_types(cfg)), rec)   # what a clean finish writes
snap = lambda r: {str(p.relative_to(r)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in sorted(r.rglob("*")) if p.is_file()}
before_d, before_s = (hashlib.sha256(dp.read_bytes()).hexdigest(), dp.stat().st_mtime_ns), snap(sb)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    r = drivers.cmd_stage_r_status(ctx, events_dir=ev1)
after_d, after_s = (hashlib.sha256(dp.read_bytes()).hexdigest(), dp.stat().st_mtime_ns), snap(sb)
same_events = {p.name: p.read_text() == (ev2 / p.name).read_text() for p in sorted(ev1.glob("*.md"))}
line = json.loads(buf.getvalue())
out = {"durations_unchanged": before_d == after_d, "sealed_unchanged": before_s == after_s, "access_log_exists": (sb / sealed.ACCESS_LOG).exists(),
       "events_written": r["event_files_written"], "events_equal_clean_finish": same_events, "completion_line_keys": sorted(line), "count": line["count"],
       "digest_is_sha256_of_hash_map": line["sealed_digest"] == hashlib.sha256(json.dumps(sealed.sealed_hashes(sb), sort_keys=True).encode()).hexdigest()}
# second call writes nothing
with contextlib.redirect_stdout(io.StringIO()):
    out["second_call_written"] = drivers.cmd_stage_r_status(ctx, events_dir=ev1)["event_files_written"]
# rebind: scope and record
rf = base / "results" / "ruling.md"; rf.parent.mkdir(parents=True); rf.write_text("ruling\n")
p = repo / "studies/p10is0/drivers.py"; orig = p.read_bytes()
p.write_bytes(orig + b"\n# a science change hidden in drivers.py would be accepted the same way\n")
try:
    out["rebind_with_drivers_change"] = drivers.cmd_rebind_identity(ctx, rf)
    out["rebind_record_keys"] = sorted(json.loads((repo / core.FREEZE_DIR / "durations_identity_rebind.json").read_text())["rebinds"][-1])
finally:
    p.write_bytes(orig)
q = repo / "studies/p10is0/items.py"; o2 = q.read_bytes(); q.write_bytes(o2 + b"\n# x\n")
try:
    drivers.cmd_rebind_identity(ctx, rf); out["rebind_with_items_change"] = "ACCEPTED"
except StageRefused as e:
    out["rebind_with_items_change"] = str(e)[:120]
finally:
    q.write_bytes(o2)
out["ruling_outside_results"] = None
try:
    drivers.cmd_rebind_identity(ctx, base / "x.md")
except StageRefused as e:
    out["ruling_outside_results"] = str(e)[:60]
from studies.p10is0 import plan as planmod
out["rebind_record_in_frozen_inputs"] = "studies/p10is0/freeze/durations_identity_rebind.json" in planmod.frozen_paths(repo)
print(json.dumps(out, indent=1, default=str))
```

The identity check was a read-only Python snippet: load `code_identity` from `freeze/durations.json`, then compare each SHA-256 with `git -C <worktree> show <commit>:<file>` for ca0a148, 45d97ff and 4b2523f, and with the working-tree file.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
