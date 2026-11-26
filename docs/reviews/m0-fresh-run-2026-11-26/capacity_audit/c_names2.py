"""Item 2: the distinct-item key. Reads work/sample_items.jsonl (audit label, b_sample_items.py).

(1) my own relabelling (independent code: one regex alternation of every surface form; C1 by tokenize + ast) compared
    with distinct_key.key_text on every sampled item;
(2) frames of C1: the text outside the rendered program, per lineage (constant or not);
(3) rename test: names renamed one-to-one within their class (question, structured JSON, answer), then the second
    solver is asked again; an answer that is not the renamed answer means names are data in that lineage;
    the key must not change under the renaming;
(4) per lineage: the vocabulary words the key relabels (class, constant or varying), and the word tokens left in the key
    that vary between items (numbers excluded), for inspection;
(5) collisions inside the sample: items with one key whose answers differ (after mapping names).
Writes deliver/c_names.json and prints a digest."""
import ast, builtins, collections, io, json, os, random, re, sys, tokenize
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import SCR, W, load_solvers
from studies.m0 import vocab
from studies.m0.registration import distinct_key as dk

O, C = "⟦", "⟧"
LABELS = set(vocab.COLOURS) | set(vocab.SHAPES) | {w for m in vocab.MARKS for w in m.split()}
CLASSES = {
    "people": list(vocab.NAMES), "places": list(vocab.TOWNS),
    "events": [e[4:] if e.startswith("the ") else e for e in vocab.EVENTS],
    "objects": list(vocab.OBJECTS), "pets": list(vocab.PETS), "invented": list(vocab.PSEUDO),
}
CLASSES = {c: [w for w in ws if w not in LABELS and w.lower() not in LABELS] for c, ws in CLASSES.items()}
CLASS_OF = {}
for c, ws in CLASSES.items():
    for w in ws:
        CLASS_OF.setdefault(w.lower(), c)


ALNUM = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def forms_of(excluded):
    fs = set()
    for c, ws in CLASSES.items():
        if c in excluded:
            continue
        for w in ws:
            fs.add(w)
            if w[0].islower():
                fs.add(w[0].upper() + w[1:])
    return fs, sorted({len(f) for f in fs}, reverse=True)


FORMS = {frozenset(): forms_of(frozenset()), frozenset({"invented"}): forms_of(frozenset({"invented"}))}


def scan(text, excluded):
    """(start, end, form, suffix) of each name: at a word start, the longest form that is followed by '', 's' or 'es'
    and then a non-alphanumeric character or the end."""
    fs, lens = FORMS[excluded]
    out, i, n = [], 0, len(text)
    while i < n:
        if text[i] in ALNUM and (i == 0 or text[i - 1] not in ALNUM):
            hit = None
            for L in lens:
                seg = text[i:i + L]
                if seg in fs:
                    for suf in ("", "s", "es"):
                        e = i + L + len(suf)
                        if text.startswith(suf, i + L) and (e >= n or text[e] not in ALNUM):
                            hit = (i, i + L, seg, suf)
                            break
                if hit:
                    break
            if hit:
                out.append(hit)
                i = hit[1] + len(hit[3])
                continue
        i += 1
    return out


class _M:
    def __init__(self, t):
        self.t = t
    def group(self, k):
        return self.t[2] if k == 1 else self.t[3]


def sub_names(text, excluded, fn):
    parts, at = [], 0
    for t in scan(text, excluded):
        parts.append(text[at:t[0]]); parts.append(fn(_M(t))); at = t[1] + len(t[3])
    parts.append(text[at:])
    return "".join(parts)


def my_relabel(q, excluded=frozenset()):
    ids = {}
    def rep(m):
        i = ids.setdefault(m.group(1).lower(), len(ids))
        return f"{O}N{i}{C}" + (m.group(2) or "")
    out = sub_names(q, excluded, rep)
    return re.sub(r"(?<![A-Za-z0-9])(A|a|An|an) (?=" + O + ")", lambda m: ("A" if m.group(1)[0] == "A" else "a") + " ", out)


def my_c1(q, structured):
    from studies.m0.c1grammar import render
    src = render(structured["program"])
    a = q.index(src)
    tree = ast.parse(src)
    bound, used = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            (bound if not isinstance(n.ctx, ast.Load) else used).add(n.id)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            bound.add(n.name)
    names = bound | (used - set(dir(builtins)))
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    lines = src.splitlines(keepends=True); off = [0]
    for ln in lines:
        off.append(off[-1] + len(ln))
    ids, out, pos, prev = {}, [], 0, None
    for t in toks:
        if t.type == tokenize.NAME and t.string in names and not (prev is not None and prev.string == "."):
            s = off[t.start[0] - 1] + t.start[1]; e = off[t.end[0] - 1] + t.end[1]
            out.append(src[pos:s]); out.append(f"{O}V{ids.setdefault(t.string, len(ids))}{C}"); pos = e
        if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT):
            prev = t
    out.append(src[pos:])
    return q[:a] + "".join(out) + q[a + len(src):], q[:a] + "…" + q[a + len(src):], sorted(names)


def rename_text_item(r, rng, excluded):
    """Rename every vocabulary name of the item to another of its class, one-to-one, in question, structured and answer."""
    found = sorted({t[2] for t in scan(r["question"], excluded)})
    if not found:
        return None
    mapping = {}
    byc = collections.defaultdict(list)
    for f in sorted({f.lower(): f for f in found}.values()):
        byc[CLASS_OF[f.lower()]].append(f)
    for c, fl in sorted(byc.items()):
        image = rng.sample(CLASSES[c], len(fl))  # injective; may reuse names present in the item (all of them are renamed)
        for f, new in zip(fl, image):
            if f[0].isupper() and new[0].islower():
                new = new[0].upper() + new[1:]
            mapping[f] = new
    for f in found:
        if f not in mapping:
            mapping[f] = mapping[[g for g in mapping if g.lower() == f.lower()][0]]
    if False:
        new = None
        if f[0].isupper() and new[0].islower():
            new = new[0].upper() + new[1:]
        mapping[f] = new
    low = {k.lower(): v for k, v in mapping.items()}
    def sub(text):
        def rep(m):
            w = m.group(1)
            n = low.get(w.lower())
            if n is None:
                return m.group(0)
            n = (n[0].upper() + n[1:]) if w[0].isupper() else (n[0].lower() + n[1:] if CLASS_OF[w.lower()] not in ("people", "places") else n)
            return n + (m.group(2) or "")
        return sub_names(text, excluded, rep)
    q2 = sub(r["question"])
    # articles: fix a/an agreement in the renamed question as a builder would write it
    q2 = re.sub(r"(?<![A-Za-z0-9])(a|an|A|An) ([A-Za-z])", lambda m: (("An" if m.group(1)[0] == "A" else "an") if m.group(2).lower() in "aeiou" else ("A" if m.group(1)[0] == "A" else "a")) + " " + m.group(2), q2) if False else q2
    st2 = json.loads(sub(json.dumps(r["structured"])))
    return q2, st2, sub(r["answer"]), mapping


def main():
    sol = load_solvers()
    rows = collections.defaultdict(list)
    for line in open(f"{SCR}/work/sample_items.jsonl"):
        r = json.loads(line); rows[r["id"]].append(r)
    rng = random.Random(20261126)
    report = {}
    total_mismatch_mine = 0
    for lid, rs in rows.items():
        ev = lid.split(".")[0]
        excl = frozenset(dk.DATA_VOCABULARY.get(lid, frozenset()))
        rec = {"items": len(rs)}
        # (1)
        mism = []
        frames = collections.Counter()
        keys_by = collections.defaultdict(list)
        for r in rs:
            theirs = dk.key_text(lid, r["question"], r["structured"])
            if ev == "C1":
                mine, frame, _ = my_c1(r["question"], r["structured"])
                frames[frame] += 1
            else:
                mine = my_relabel(r["question"], excl)
            if mine != theirs:
                mism.append({"level": r["level"], "i": r["i"], "theirs": theirs[:300], "mine": mine[:300]})
            keys_by[theirs].append(r)
        total_mismatch_mine += len(mism)
        rec["my_relabel_differs"] = len(mism); rec["my_relabel_examples"] = mism[:3]
        if ev == "C1":
            rec["c1_frames"] = {k[:200]: v for k, v in frames.most_common(5)}
            rec["c1_n_frames"] = len(frames)
        # (5) collisions
        coll = 0; coll_bad = []
        for kt, grp in keys_by.items():
            if len(grp) > 1:
                coll += len(grp) - 1
                ans = {g["answer"] for g in grp}
                if len(ans) > 1 and ev != "C1":
                    # answers may differ only by names; map names to placeholders in the answer
                    norm = {my_relabel(g["question"] + " ||| " + g["answer"], excl).split(" ||| ")[-1] for g in grp}
                    if len(norm) > 1:
                        coll_bad.append({"key": kt[:200], "answers": sorted(ans)[:4]})
                elif len(ans) > 1:
                    coll_bad.append({"key": kt[:200], "answers": sorted(ans)[:4]})
        rec["sample_key_repeats"] = coll; rec["sample_key_repeats_with_different_answers"] = coll_bad[:5]
        rec["n_key_repeats_with_different_answers"] = len(coll_bad)
        # (3) rename test
        n_ren, n_key_changed, n_ans_changed, ex = 0, 0, 0, []
        for r in rs:
            if ev == "C1":
                continue
            got = rename_text_item(r, rng, excl)
            if got is None:
                continue
            q2, st2, a2, mapping = got
            n_ren += 1
            if dk.key_text(lid, q2, st2) != dk.key_text(lid, r["question"], r["structured"]):
                n_key_changed += 1
                if len(ex) < 3:
                    ex.append({"what": "key changed", "q": r["question"][:200], "q2": q2[:200]})
            try:
                a = sol[lid](q2, st2)
            except Exception as e:  # noqa
                a = f"ERROR {type(e).__name__}: {e}"
            if a != a2:
                n_ans_changed += 1
                if len(ex) < 6:
                    ex.append({"what": "solver answer changed under renaming", "map": mapping, "renamed_answer": a2[:80], "solver": str(a)[:80]})
        rec["rename"] = {"items_with_names": n_ren, "key_changed": n_key_changed, "answer_changed": n_ans_changed, "examples": ex}
        # (4) vocabulary hits and varying tokens
        if ev != "C1":
            hits = collections.Counter(); per_item_words = []
            for r in rs:
                ws = {t[2] for t in scan(r["question"], excl)}
                per_item_words.append(ws)
                hits.update(ws)
            n = len(rs)
            rec["relabelled_words_constant"] = sorted(w for w, c in hits.items() if c == n)
            var = sorted(((w, c) for w, c in hits.items() if c < n), key=lambda t: -t[1])
            rec["relabelled_words_varying_classes"] = dict(collections.Counter(CLASS_OF[w.lower()] for w, _ in var))
            rec["relabelled_words_varying_sample"] = [w for w, _ in var[:25]]
            # English-looking invented-word hits (pseudo words that are dictionary words are flagged by hand later)
            rec["invented_hits_all"] = sorted({w for w, _ in var if CLASS_OF[w.lower()] == "invented"})[:60] if len([1 for w, _ in var if CLASS_OF[w.lower()] == "invented"]) < 400 else "many"
        tok = collections.Counter()
        for r in rs:
            kt = dk.key_text(lid, r["question"], r["structured"])
            tok.update(set(re.findall(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z'-]*", re.sub(O + r"[NV]\d+" + C, " ", kt))))
        n = len(rs)
        varying = sorted(((w, c) for w, c in tok.items() if c < n), key=lambda t: (-t[1], t[0]))
        rec["varying_tokens_left_in_key"] = [f"{w}:{c}" for w, c in varying[:80]]
        rec["n_varying_tokens_left_in_key"] = len(varying)
        report[lid] = rec
        print(lid, "mine!=theirs", len(mism), "| rename items", n_ren, "key_changed", n_key_changed, "answer_changed", n_ans_changed,
              "| repeats", coll, "repeats_diff_answer", len(coll_bad), "| varying tokens", len(varying), flush=True)
    print("TOTAL my relabel differs:", total_mismatch_mine)
    with open(f"{SCR}/deliver/c_names2.json", "x") as f:
        json.dump(report, f, indent=1, sort_keys=True, ensure_ascii=False)


main()
