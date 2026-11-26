"""Pair audit, provenance: textual overlap between each new solver module and the committed generator/first-solver source
(all studies/m0/*.py except solvers2/, plus the earlier second solvers under docs/reviews/m0-lineage-decision-2026-11-25/).
Counts whitespace-normalised source lines of 30+ characters that occur verbatim in both, and prints them (comments and
docstrings included, since copied comments would be telling)."""
import glob, os, re, collections
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
def norm_lines(p):
    out = set()
    for ln in open(p, errors="replace"):
        s = re.sub(r"\s+", " ", ln.strip())
        if len(s) >= 30:
            out.add(s)
    return out
others = {}
for p in glob.glob(W + "/studies/m0/*.py") + glob.glob(W + "/docs/reviews/m0-lineage-decision-2026-11-25/**/*.py", recursive=True):
    others[os.path.relpath(p, W)] = norm_lines(p)
print("comparison files:", len(others))
for p in sorted(glob.glob(W + "/studies/m0/solvers2/solver2_*.py")):
    mine = norm_lines(p)
    hits = collections.defaultdict(list)
    for f, ls in others.items():
        for s in mine & ls:
            hits[s].append(f)
    print(f"== {os.path.basename(p)}: long lines {len(mine)}; shared verbatim with generator/first-solver/earlier-solver files: {len(hits)}")
    for s, fs in sorted(hits.items()):
        print(f"   {s[:140]!r}  in {len(fs)} file(s): {fs[:3]}")
