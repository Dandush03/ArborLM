"""Re-audit of M2 / MINOR 11: can the rerun guards and linkage checks block the legitimate
registered sequence equivalence -> screen -> confirm -> analyze, and do they catch a mixed chain?

Input: the compact results root of a scratch DRY RUN (synthetic fixture). A copy is made with
every manifest and worker ``dry_run`` flag flipped to false, so the non-dry-run code paths of
``check_rerun``, ``require_completed`` and ``check_linkage`` can be exercised without real data.
result.json files are not modified, so the hashes recorded in the chain stay valid.

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_p6e_chain.py <dry-results-root> <scratch>
"""

import json
import shutil
import sys
from pathlib import Path

from arborlm.p6_retrieval_study import _worker_results, check_linkage
from arborlm.p6_stage import check_rerun, require_completed

ORDER = ("equivalence", "screen", "confirm", "analysis")


def flip(root: Path) -> None:
    for path in root.rglob("*.json"):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and data.get("dry_run") is True:
            data["dry_run"] = False
            path.write_text(json.dumps(data))


def attempt(label: str, fn) -> None:
    try:
        out = fn()
        print(f"{label}: OK {out if out is None or isinstance(out, dict) else Path(str(out)).name}")
    except Exception as exc:  # noqa: BLE001
        print(f"{label}: REFUSED {type(exc).__name__}: {str(exc)[:160]}")


def main() -> None:
    source, scratch = Path(sys.argv[1]), Path(sys.argv[2])
    full = scratch / "flipped"
    shutil.copytree(source, full)
    flip(full)
    # 1. The registered order, one stage at a time, starting from an empty results root.
    root = scratch / "sequence"
    root.mkdir()
    for stage in ORDER:
        attempt(f"[sequence] open {stage} (no supersede)",
                lambda stage=stage: check_rerun(root, stage, None, None, dry_run=False))
        shutil.copytree(full / stage, root / stage)
    for stage in ORDER[:3]:
        attempt(f"[sequence] consume {stage} (implicit id)",
                lambda stage=stage: require_completed(root, stage, None, dry_run=False))
    eq, sc, co = (require_completed(root, s, None, dry_run=False) for s in ORDER[:3])
    selection = json.loads((sc / "selection.json").read_text())
    sw, cw = _worker_results(sc), _worker_results(co)
    attempt("[sequence] linkage of the registered chain",
            lambda: check_linkage(eq, sc, co, selection, sw, cw, dry_run=False))
    attempt("[sequence] linkage with dry_run=True against non-dry records",
            lambda: check_linkage(eq, sc, co, selection, sw, cw, dry_run=True))
    # 2. Second runs.
    for stage in ORDER:
        attempt(f"[rerun] {stage} again, no supersede",
                lambda stage=stage: check_rerun(root, stage, None, None, dry_run=False))
    first_screen = sc.name
    attempt("[rerun] screen, supersede wrong id",
            lambda: check_rerun(root, "screen", "P6ESCR-nope", "r", dry_run=False))
    attempt("[rerun] screen, supersede right id, blank reason",
            lambda: check_rerun(root, "screen", first_screen, "  ", dry_run=False))
    attempt("[rerun] screen, supersede right id with reason",
            lambda: check_rerun(root, "screen", first_screen, "operator error", dry_run=False))
    # 3. A superseding screen exists (simulated copy with a different selection file).
    new_screen = root / "screen" / (first_screen + "-B")
    shutil.copytree(sc, new_screen)
    sel = json.loads((new_screen / "selection.json").read_text())
    sel["workers"] = sel.get("workers", 0) + 100
    (new_screen / "selection.json").write_text(json.dumps(sel))
    attempt("[superseded] confirm consumes screen with implicit id",
            lambda: require_completed(root, "screen", None, dry_run=False))
    attempt("[superseded] linkage: old confirm + new screen",
            lambda: check_linkage(eq, new_screen, co, sel, _worker_results(new_screen), cw,
                                  dry_run=False))
    attempt("[superseded] linkage: old confirm + old screen (explicit id)",
            lambda: check_linkage(eq, require_completed(root, "screen", first_screen,
                                                        dry_run=False),
                                  co, selection, sw, cw, dry_run=False))
    # 4. A dry-run record can never be consumed by a registered stage.
    attempt("[dry] explicit dry-run equivalence id consumed as registered",
            lambda: require_completed(source, "equivalence",
                                      next((source / "equivalence").iterdir()).name,
                                      dry_run=False))


if __name__ == "__main__":
    main()
