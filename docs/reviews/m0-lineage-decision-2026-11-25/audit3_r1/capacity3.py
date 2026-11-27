# ruff: noqa
"""Audit 3 (R1): structural capacity per shape and level, by two keys, estimated from collisions.

Keys (computed from the rendered TEXT; the structured form is used only to know which strings are entity names):
  LOW  = an isomorphism-invariant key: entity names erased and refined by 3 rounds of Weisfeiler-Lehman over the
         sentences they occur in; sentence order ignored except for shapes whose operations are a sequence
         (queue, stack piles, swaps, accounts); alphabetical name lists treated as sets. A function of the
         structure up to renaming and presentation order, so #distinct LOW keys <= #structures (a lower bound).
  HIGH = names replaced by their order of first appearance, text order kept (presentation variants count as
         distinct: an upper bound on structures).
From N items per (shape, level) (seed base 7100 + level; throwaway): D = distinct keys, C = colliding pairs,
S_eff = N(N-1)/(2C) (the collision estimate of 1/sum p^2, itself <= support); if C == 0 the 95 % bound N(N-1)/6.
usage (worktree root): PYTHONHASHSEED=0 uv run --locked python <this> <N> [lineage-substring]
"""
import hashlib, json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
import gen

STOP = {"all", "none", "some", "first", "last", "most", "fewest", "least", "tallest", "shortest", "champion", "runner_up", "beaten_by", "position", "leave", "join", "cut",
        "serve", "front_to_back", "move", "reverse", "turn", "walk", "left", "right", "around", "cw90", "cw270", "ccw90", "cw180", "max", "min", "range", "dur", "pay", "earn",
        "half", "is_knight", "is_knave", "both_knights", "some_knave", "yes", "no", "abstain", "descendants", "grandchildren", "adj", "end", "pos", "between", "notnext", "not",
        "either", "owns", "attr", "and", "or", "if", "do", "colour", "shape", "mark", "swap", "rotate", "was", "one", "two", "atleast_two", "north", "south", "east", "west",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "first", "second", "knight", "knave", "cannot be determined", "convention", "answer_convention"}
STOP |= {"taller", "people", "events", "players", "items", "rules", "chain", "member", "verb", "cats", "x", "y", "kind", "ask", "lamps", "initial", "switches", "presses",
         "members", "votes", "margin", "line", "ops", "piles", "results", "step", "same", "different", "rates", "rel", "rivals", "towns", "roads", "start", "end", "candidates",
         "ballots", "child", "generations", "options", "parent", "root", "statements", "who", "tree", "depth", "branching", "size_class", "true_count", "clues", "seat",
         "pets", "grid", "moves", "places", "facts", "proposers", "receivers", "prefs_p", "prefs_r", "hold", "jobs", "spans", "days", "anchor", "links", "total", "groups",
         "sizes", "pairs", "triples", "quad", "triple", "meetings", "zones", "day", "planted_roads", "owners", "actions", "seq", "query", "vars", "rule", "none", "all", "some"}
ORDERED = {"R1.containers_queue_line_r2", "R1.containers_stack_piles_r4", "R1.swap_tracking", "R1.tracking_accounts"}
SETLIST = ("Choose from", "are candidates", "played a round-robin", "must be split into two teams", "sit in a row", "each own exactly one different pet", "One of ",
           "Who is the tallest of", "Who is the shortest of", "Which of ", "of these events took place", "Matching goes in turns")


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from strings(v)


def entities(b):
    q = b.question
    out = set()
    for s in strings(b.structured):
        if not s or s in STOP or len(s) > 30 or not re.fullmatch(r"[A-Za-z][A-Za-z' -]*", s):
            continue
        if re.search(r"(?<![A-Za-z])" + re.escape(s) + r"(?![A-Za-z])", q, re.I):
            out.add(s)
    return sorted(out, key=lambda s: (-len(s), s))


NORM = [  # paraphrases that say the same thing (presentation, not structure)
    (re.compile(r"([A-Z][a-z]+) is shorter than ([A-Z][a-z]+)\."), r"\2 is taller than \1."),
    (re.compile(r"([A-Z][a-z]+)'s parent is ([A-Z][a-z]+)\."), r"\2 is the parent of \1."),
    (re.compile(r"([A-Za-z][\w -]*?) took place (\d+ days?) before ([\w -]+?)\."), r"\3 took place \2 after \1."),
    (re.compile(r"(\w+) is (\d+ blocks?) south of (\w+)\."), r"\3 is \2 north of \1."),
    (re.compile(r"(\w+) is (\d+ blocks?) west of (\w+)\."), r"\3 is \2 east of \1."),
]


def tokenise(b):
    ents = entities(b)
    q = b.question
    for rx, rep_ in NORM:
        q = rx.sub(rep_, q)
    b = type(b)(q, b.structured, b.answer, b.answer_type, b.k)
    if not ents:
        return b.question, []
    pat = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(e) for e in ents) + r")(?![A-Za-z])", re.I)
    low = {e.lower(): e for e in ents}
    seq = []

    def rep(m):
        seq.append(low[m.group(1).lower()])
        return "§"

    t = pat.sub(rep, b.question)
    return t, seq


def h(x):
    return hashlib.sha256(repr(x).encode()).hexdigest()[:16]


# run-3 addition: symmetric phrasings (the order of the two names is presentation). (template regex, slot groups whose labels are sorted)
SYM = [
    (re.compile(r"^\u00a7 and \u00a7 (are rivals|swap what they are holding|do not sit next to each other)\."), [(0, 1)]),
    (re.compile(r"^\u00a7 is (the same thing as|a different thing from) \u00a7\."), [(0, 1)]),
    (re.compile(r"(two-way road between|A road between) \u00a7 and \u00a7 "), [(0, 1)]),
    (re.compile(r"^(Some|No) \u00a7 are \u00a7\."), [(0, 1)]),
    (re.compile(r"^\u00a7 owns either the \u00a7 or the \u00a7\."), [(1, 2)]),
    (re.compile(r'^\u00a7 says: "(It was \u00a7 or \u00a7|\u00a7 and \u00a7 are both knights|at least one of \u00a7 and \u00a7 is a knave)\."'), [(1, 2)]),
    (re.compile(r"^\u00a7 sits somewhere between \u00a7 and \u00a7\."), [(1, 2)]),
    (re.compile(r"are in both the \u00a7 and the \u00a7 groups"), [(0, 1)]),
    (re.compile(r"are in all of the "), [(0, 1, 2)]),
]
ROT = re.compile(r"^\u00a7 hands their item to \u00a7, \u00a7 hands theirs to \u00a7, and \u00a7 hands theirs to \u00a7, all at once\.")


def sym_groups(s):
    for rx, gs in SYM:
        if rx.search(s):
            return gs
    return []


def keys(lid, b):
    t, seq = tokenise(b)
    if SYMMETRIC_MODE:
        t = t.replace("; ", ". ")  # venn: one clause per sentence, clause order is presentation
    # HIGH: first-appearance relabelling, text order kept
    idx = {}
    hi = h((t, tuple(idx.setdefault(e, len(idx)) for e in seq)))
    # LOW: WL over sentences
    sents = re.split(r"(?<=[.?!])\s+", t)
    it = iter(seq)
    S = []
    for i, s in enumerate(sents):
        k = s.count("§")
        ents = [next(it) for _ in range(k)]
        setlike = any(w in s for w in SETLIST)
        S.append((i if lid in ORDERED else -1, s, ents, setlike))
    lab = {e: "E" for e in set(seq)}
    for _ in range(3):
        new = {}
        for e in lab:
            ctx = []
            for pos, s, ents, setlike in S:
                if e not in ents:
                    continue
                if setlike:
                    ctx.append((pos, s, "set", tuple(sorted(lab[x] for x in ents)), ents.count(e)))
                else:
                    ctx.append((pos, s, tuple(j for j, x in enumerate(ents) if x == e), sig_of(s, ents, lab)) if not SYMMETRIC_MODE else
                               (pos, s, tuple(sorted({role_of(s, j) for j, x in enumerate(ents) if x == e})), sig_of(s, ents, lab)))
            new[e] = h((lab[e], tuple(sorted(map(repr, ctx)))))
        lab = new
    sig = [(pos, s, tuple(sorted(lab[x] for x in ents)) if setlike else sig_of(s, ents, lab)) for pos, s, ents, setlike in S]
    lo = h(tuple(sorted(map(repr, sig))) if lid not in ORDERED else tuple(map(repr, sig)))
    return lo, hi


SYMMETRIC_MODE = os.environ.get("AUDIT3_SYM") == "1"


def role_of(s, j):
    if ROT.search(s):
        return "rot"
    for g in sym_groups(s):
        if j in g:
            return min(g)
    return j


def sig_of(s, ents, lab):
    labs = [lab[x] for x in ents]
    if not SYMMETRIC_MODE:
        return tuple(labs)
    if ROT.search(s):
        a, b_, c = labs[0], labs[1], labs[3]
        return min((a, b_, c), (b_, c, a), (c, a, b_))
    for g in sym_groups(s):
        vals = sorted(labs[i] for i in g)
        for i, v in zip(g, vals):
            labs[i] = v
    return tuple(labs)


def est(cnt, n):
    c = sum(v * (v - 1) // 2 for v in cnt.values())
    return (n * (n - 1) / (2 * c)) if c else None, c


def main():
    N = int(sys.argv[1]); filt = sys.argv[2] if len(sys.argv) > 2 else ""
    L = gen.lineages()
    out = []
    for lid in sorted(L):
        if filt and filt not in lid:
            continue
        for lv in range(7):
            its = gen.items(L[lid], lv, N, 7100)
            lo, hi = Counter(), Counter()
            for b in its:
                a, c = keys(lid, b)
                lo[a] += 1; hi[c] += 1
            sl, cl = est(lo, N); sh, ch = est(hi, N)
            out.append({"lineage": lid, "level": lv, "N": N, "low_distinct": len(lo), "low_pairs": cl, "low_S_eff": round(sl) if sl else None,
                        "high_distinct": len(hi), "high_pairs": ch, "high_S_eff": round(sh) if sh else None, "bound_if_no_collision": round(N * (N - 1) / 6)})
            print(json.dumps(out[-1]), flush=True)


if __name__ == "__main__":
    main()
