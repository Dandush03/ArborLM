# ruff: noqa: E501
"""P10IS6: check the panel walk and the ledger append on COPIES of the real public inputs (addendum 2 rulings 16 and 17). Reads the shared panel ledger and P10-I-S3's excluded set (always pass COPIES: the append is performed on the copy), the pinned WikiText-2 parquet files
(needs pyarrow, the lock's ``pilot`` extra), prints a JSON record. Writes nothing but the copy of the ledger. No network, no sealed value."""

import argparse
import hashlib
import json
from pathlib import Path

from studies.p10i_s3.data import count_overlaps, walk_panels

from . import core, d0


def main(argv: list[str] | None = None) -> int:
    from arborlm.fetch_wikitext import DOWNLOAD_FILES
    from arborlm.pilot_data import _rows

    ap = argparse.ArgumentParser(prog="studies.p10i_s6.realcheck")
    ap.add_argument("--ledger-copy", required=True)
    ap.add_argument("--s3-excluded-copy", required=True)
    ap.add_argument("--wikitext2-dir", required=True)
    a = ap.parse_args(argv)
    cfg = core.load_config()
    d2 = Path(a.wikitext2_dir)
    train, val_rows = list(_rows(d2 / DOWNLOAD_FILES[0])), list(_rows(d2 / DOWNLOAD_FILES[1]))
    lengths = [len(r.encode("utf-8")) for r in val_rows]
    raw, ledger = d0.read_ledger(Path(a.ledger_copy))
    s3, s3_sha = d0.load_s3_excluded(Path(a.s3_excluded_copy), cfg)
    _, vspans, _ = d0.validation_candidates(train, val_rows)
    n, start = int(cfg["setting"]["panel_chunks"]), int(cfg["data"]["panel_walk_start"])
    from_ledger = d0.spans_in_ledger(ledger, lengths)
    full = [*from_ledger, *s3]
    reg, cal = walk_panels(vspans, full, start, n, 2)
    ledger_only_reg, ledger_only_cal = walk_panels(vspans, from_ledger, start, n, 2)
    new = [vspans[r] for r in [*reg, *cal]]
    old = [vspans[r] for r in [*ledger_only_reg, *ledger_only_cal]]
    appended = d0.append_panels(Path(a.ledger_copy), d0.new_windows({d0.SOURCES[0]: reg, d0.SOURCES[1]: cal}, vspans, d0.row_starts(lengths)))
    after = json.loads(Path(a.ledger_copy).read_bytes())
    rec = {
        "ledger_sha256_before": hashlib.sha256(raw).hexdigest(), "windows_before": len(ledger["windows"]), "s3_spans_sha256": s3_sha, "s3_spans": len(s3), "ledger_spans": len(from_ledger),
        "new_panel_chunks": len(new), "overlaps_with_full_excluded_set": count_overlaps(new, full), "overlaps_with_s3_set_if_only_the_ledger_were_excluded": count_overlaps(old, s3),
        "append": appended, "windows_after": len(after["windows"]), "old_windows_unchanged": after["windows"][: len(ledger["windows"])] == ledger["windows"],
    }  # fmt: skip
    print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
