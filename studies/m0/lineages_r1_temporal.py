# ruff: noqa: E501
"""R1 pilot, family "temporal" (intended part A). Three lineages with different solution procedures:
interval intersection, modular (weekday) arithmetic over a spanning tree of offsets, and a longest-path pass over a job DAG."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot, pl
from studies.m0.vocab import EVENTS, NAMES

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@pilot("temporal", "A")
def temporal_interval_overlap(level: int, r: random.Random) -> Built:
    """structured: {"events": [name], "spans": [["range", a, b] | ["dur", s, d]] (parallel to events; a range covers days a..b,
    a duration covers days s..s+d-1), "x": name, "y": name}. Answer yes/no: do the two events share at least one day."""
    n = 3 + (level + 1) // 2
    events = r.sample(EVENTS, n)
    spans, text, ab = [], [], []
    for ev in events:
        s, d = r.randint(1, 120), r.randint(2, 25)
        ab.append((s, s + d - 1))
        if r.random() < 0.5:
            spans.append(["range", s, s + d - 1])
            text.append(f"{ev.capitalize()} ran from day {s} to day {s + d - 1}, both days included.")
        else:
            spans.append(["dur", s, d])
            text.append(f"{ev.capitalize()} started on day {s} and went on for {pl(d, 'day')} (day {s} counts as the first).")
    want = r.choice(("yes", "no"))
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j and (max(ab[i][0], ab[j][0]) <= min(ab[i][1], ab[j][1])) == (want == "yes")]
    if not pairs:
        raise Retry
    i, j = r.choice(pairs)
    q = " ".join(text) + f" Did {events[i]} and {events[j]} overlap, that is, was there at least one day on which both were going on? Answer yes or no."
    return Built(q, {"events": events, "spans": spans, "x": events[i], "y": events[j]}, want, "yn", 2)


@pilot("temporal", "A")
def temporal_weekday_shift(level: int, r: random.Random) -> Built:
    """structured: {"days": [the seven weekday names in order], "anchor": [event, weekday], "links": [[later, earlier, n]] meaning
    `later` took place n days after `earlier`, "ask": event}. Answer: the weekday on which `ask` took place (word)."""
    n = 2 + level
    ev = r.sample(EVENTS, n)
    wd = {ev[0]: r.randrange(7)}
    links = []
    for i in range(1, n):
        parent = ev[r.randrange(i)]
        delta = r.choice([x for x in range(-300, 301) if x != 0])
        wd[ev[i]] = (wd[parent] + delta) % 7
        links.append([ev[i], parent, delta] if delta > 0 else [parent, ev[i], -delta])
    r.shuffle(links)
    sents = [f"{a.capitalize()} took place {pl(k, 'day')} after {b}." if r.random() < 0.5 else f"{b.capitalize()} took place {pl(k, 'day')} before {a}." for a, b, k in links]
    ask = r.choice(ev[1:])
    q = f"{ev[0].capitalize()} took place on a {DAYS[wd[ev[0]]]}. " + " ".join(sents) + f" On which day of the week did {ask} take place?"
    return Built(q, {"days": list(DAYS), "anchor": [ev[0], DAYS[wd[ev[0]]]], "links": links, "ask": ask}, DAYS[wd[ask]], "word", 7)


@pilot("temporal", "A")
def temporal_critical_path(level: int, r: random.Random) -> Built:
    """structured: {"jobs": [[person, days, [persons it waits for]]]}. A job with no wait starts on day 0, otherwise it starts the day
    all its predecessors are finished and lasts its number of days. Answer: the person whose job finishes last (name)."""
    n = 3 + level
    people = r.sample(NAMES, n)
    jobs, finish = [], {}
    for i, p in enumerate(people):
        deps = r.sample(people[:i], min(i, r.choice((0, 1, 1, 2)))) if i else []
        d = r.randint(1, 15)
        jobs.append([p, d, deps])
        finish[p] = max([finish[x] for x in deps], default=0) + d
    top = max(finish.values())
    if sum(1 for v in finish.values() if v == top) != 1:
        raise Retry
    order = jobs[:]
    r.shuffle(order)
    text = [f"{p}'s job takes {pl(d, 'day')} and starts on day 0." if not deps else f"{p}'s job takes {pl(d, 'day')} and starts as soon as {'the job of ' + deps[0] + ' is' if len(deps) == 1 else 'the jobs of ' + and_(deps) + ' are all'} finished." for p, d, deps in order]
    q = " ".join(text) + " Whose job finishes last?"
    return Built(q, {"jobs": jobs}, next(p for p, v in finish.items() if v == top), "name", n)
