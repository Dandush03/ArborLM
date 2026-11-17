"""Re-check A, task 4: datagen.run's record-keeping, stage cap and offline settings on synthetic inputs (no package outside the lock is
imported: every probe stops before step 2). Also the explicit beam-score recomputation on a hand case. Written by the re-check auditor
(Claude Opus 5.5). Run:  <python> -I <this file> <pinned tree> <scratch dir>
"""

import os
import shutil
import sys
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
SCR = Path(sys.argv[2]).resolve()
if SCR.exists():
    shutil.rmtree(SCR)
SCR.mkdir(parents=True)
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
import torch  # noqa: E402

from studies.p10s2 import datagen  # noqa: E402

OUT: list[str] = []


def say(s: str) -> None:
    OUT.append(s)
    print(s)


class FakeLedger:
    def __init__(self, hours: float) -> None:
        self.hours, self.charged = hours, []

    def charge(self, stage: str, seconds: float) -> None:
        self.charged.append((stage, round(seconds, 3)))

    def remaining(self) -> float:
        return self.hours


hashed = SCR / "req.txt"
hashed.write_text("transformers==4.57.1 \\\n    --hash=sha256:" + "a" * 64 + "\n")
unhashed = SCR / "req_unhashed.txt"
unhashed.write_text("transformers==4.57.1\n")
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ.pop("TRANSFORMERS_OFFLINE", None)
for label, req, downloads in (("unhashed requirements (DatagenStop)", unhashed, SCR / "dl"), ("empty downloads folder (FetchRefused, a RuntimeError that is not a DatagenStop)", hashed, SCR / "dl")):
    out = SCR / ("out_" + label.split()[0])
    led = FakeLedger(100.0)
    try:
        datagen.run(downloads, out, led=led, stage_cap_seconds=60, wikitext_dir=SCR, requirements=req, tatoeba_record=SCR / "rec.json")
        say(f"[{label}] completed (unexpected)")
    except Exception as e:  # noqa: BLE001
        say(f"[{label}] stopped with {type(e).__name__}; prefreeze_record.json kept: {(out / 'prefreeze_record.json').is_file()}; ledger charges: {led.charged}")
say(f"[offline] HF_HUB_OFFLINE after run() when the caller had set it to '0': {os.environ.get('HF_HUB_OFFLINE')!r}; TRANSFORMERS_OFFLINE: {os.environ.get('TRANSFORMERS_OFFLINE')!r} (setdefault keeps a pre-set value)")
try:
    with datagen.charged_stage(FakeLedger(0.5), 3600):
        pass
    say("[cap] 1 h stage on a ledger with 0.5 h remaining: started (unexpected)")
except datagen.StageCapExceeded as e:
    say(f"[cap] 1 h stage on a ledger with 0.5 h remaining: refused before start: {e}")
t = [0.0]
led = FakeLedger(10.0)
try:
    with datagen.charged_stage(led, 5, clock=lambda: t[0]) as clock:
        t[0] = 6.0
        clock.tick("teacher batch")
except datagen.StageCapExceeded as e:
    say(f"[cap] tick past the cap: {e}; charged {led.charged}")
# the explicit score: Marian pad (= decoder start) 58100, EOS 0; a finished hypothesis padded after EOS, an unfinished one at the limit
trans = torch.tensor([[-1.0, -2.0, -0.5, 0.0], [-0.1, -0.2, -0.3, -0.4]])
gen = torch.tensor([[17, 23, 0, 58100], [5, 6, 7, 8]])
got = datagen.recompute_sequence_scores(trans, gen, 58100)
say(f"[score] recomputed {got}; by hand {[-3.5 / 3, -1.0 / 4]} (EOS counted, padding not)")
say(f"[score] compare_scores tolerance {datagen.SCORE_TOLERANCE}: {datagen.compare_scores(got, [-3.5 / 3 + 2e-5, -0.25])}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(OUT) + "\n")
shutil.rmtree(SCR)
