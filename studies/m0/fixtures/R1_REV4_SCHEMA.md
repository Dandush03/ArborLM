# R1 revision-4 shapes: structured-form schema for the second-solver agent

Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything. No second solver exists for these shapes; nothing is registered in core.REGISTRY (ruling R-9).

## Interface

- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.
- Registry: `SOLVERS: dict[str, Callable]` keyed by shape id (`R1.<name>_r4`); one module per family, `studies/m0/solvers_r1_<family>.py`.
- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).
- Fixtures: `studies/m0/fixtures/r1_rev4/<shape id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).
- The question text is in the fixture only so that an auditor can check the wording against the structured form; solvers must not parse it.

## Shapes (family, what it replaces, the builder's description of its structured form and answer rule). No part is assigned: the partition is by the registered rule over the final map (see manifests/r1_rev4_parts.md).

### `R1.activity_selection_r4` (family scheduling, intended part ?)

structured: {"meetings": [[name, start, end]]}. A person can attend several meetings if they do not overlap (a meeting that ends exactly when another starts is fine). Answer: the largest
number of meetings one person can attend (open number). The day is a row of zones; each zone is one of: A, two long meetings that touch plus a short one across the join (the shortest-first
rule loses one there); B, one long early meeting over two to four short ones (the earliest-start rule gets one where the answer is the number of shorts); C, a single meeting; D, three meetings
with random overlaps. Every item has at least one A zone and one B zone, so shortest-first and earliest-start are wrong in every item and by a varying amount (the earlier shape: shortest-first
right in 93 % of the items). The answer is computed by the earliest-finish rule over all meetings and checked against the zone-wise sum.

Example (level 2):

```
question: Yan's meeting runs from minute 78 to minute 83. Dmitri's meeting runs from minute 59 to minute 63. Abel's meeting runs from minute 48 to minute 67. Bram's meeting runs from minute 38 to minute 46. Uma's meeting runs from minute 80 to minute 86. Ben's meeting runs from minute 18 to minute 22. Dell's meeting runs from minute 32 to minute 38. Will's meeting runs from minute 69 to minute 80. Zita's meeting runs from minute 37 to minute 40. Iris's meeting runs from minute 27 to minute 31. Ivo's meeting runs from minute 1 to minute 25. Maya's meeting runs from minute 4 to minute 6. Oscar's meeting runs from minute 14 to minute 16. Kenji's meeting runs from minute 8 to minute 12. Liam's meeting runs from minute 51 to minute 54. Hana's meeting runs from minute 56 to minute 58. Dion's meeting runs from minute 64 to minute 67. A meeting that ends at minute t and one that starts at minute t do not overlap. What is the largest number of these meetings that one person could attend?
structured: {"meetings": [["Yan", 78, 83], ["Dmitri", 59, 63], ["Abel", 48, 67], ["Bram", 38, 46], ["Uma", 80, 86], ["Ben", 18, 22], ["Dell", 32, 38], ["Will", 69, 80], ["Zita", 37, 40], ["Iris", 27, 31], ["Ivo", 1, 25], ["Maya", 4, 6], ["Oscar", 14, 16], ["Kenji", 8, 12], ["Liam", 51, 54], ["Hana", 56, 58], ["Dion", 64, 67]], "zones": ["B", "C", "A", "B", "A"]}
answer: 13
```

### `R1.boolean_lights_r4` (family boolean_state, intended part ?)

Same schema as boolean_lights: {"lamps", "initial", "switches": {colour: [lamp]}, "presses": [colour], "ask": lamp}. The asked lamp's toggle parity pi (0 or 1) is drawn first,
with a fair coin, independent of its initial state; the set of pressed switches wired to it is then drawn uniformly among the non-empty sets with that parity (so the lamp is
toggled at least once); unpressed switches may be wired to it or not (a coin). The answer is initial xor pi, which is therefore independent of the initial state, of the parity and
of every other lamp. The start sentence names the lamps that are on and says "all the lamps not named here are off" (the earlier "every other lamp is off" could be read as
alternate lamps).

Example (level 2):

```
question: There are 6 lamps numbered 1 to 6. At the start, lamp 1 is on, and all the lamps not named here are off. The red switch toggles lamps 1, 2 and 6 (each one goes from on to off or from off to on). The yellow switch toggles lamp 3 (each one goes from on to off or from off to on). The black switch toggles lamps 1 and 6 (each one goes from on to off or from off to on). The switches are pressed in this order: red, black, yellow, black, red, yellow, red. Is lamp 6 on at the end? Answer yes or no.
structured: {"ask": 6, "initial": [1, 0, 0, 0, 0, 0], "lamps": 6, "presses": ["red", "black", "yellow", "black", "red", "yellow", "red"], "switches": {"black": [1, 6], "red": [1, 2, 6], "yellow": [3]}}
answer: yes
```

### `R1.categories_default_exceptions_r4` (family categories, intended part ?)

Same schema as categories_default_exceptions: {"chain", "rules": [[group, verb, bool]], "member", "verb"}. The member is in the smallest group of a chain of c = T + 8 + 2 level groups;
T = 9 + 2 (level // 2) rules (always odd, so a majority never ties) concern the asked verb, none on the member's own group; the rule on the NEAREST group (the one that decides) sits at a distance d drawn uniformly from 1 to
c - T, so a rule at a given distance is the answer for only a small share of the items (the earlier shape put it at distance 1 in every level-0 and level-1 item and in 61 to 84 % of
the rest). The signs: the answer is drawn first (a fair coin); the number Y of yes
signs among the T rules is drawn uniformly from 1..T-1, independent of the answer (so the majority sign, the parity of the count, "all rules agree" and the sign of a randomly listed
rule carry no information about the answer: each is exactly independent of it); the signs are then placed at random on the rules beyond the nearest. The one reading this cannot
remove is a rule at a fixed distance beyond the nearest, whose sign agrees with the answer with probability 1/2 - 1/(2 (T - 1)) (an answer-sized hole in the multiset), between 0.06
and 0.03 below chance. Chain sentences are shuffled. No redraw.

Example (level 2):

```
question: Every sasex is a zinar. Every besak is a nimir. Every biler is a besek. Every bator is a somok. Every mamer is a besak. Every tinar is a ladix. Every zinar is a latax. Every katix is a sasex. Every besek is a sivon. Every sivon is a bator. Every ratok is a tinar. Every memon is a zidor. Every tevor is a biler. Every rokix is a mamer. Every dirin is a ratok. Every nemen is a reron. Every zidor is a nemen. Every ladix is a memon. Every zevik is a dirin. Every nimir is a tevor. Every somok is a katix. Every latax is a zevik. A reron can jump. A zidor cannot swim. A nemen cannot swim. A zevik can swim. A dirin cannot swim. A tinar cannot swim. A latax cannot swim. A zinar can jump. A memon can swim. A mamer cannot jump. A tevor can jump. A ratok cannot swim. A nemen cannot jump. A ladix can swim. A reron cannot swim. A zinar cannot swim. A latax can jump. A katix cannot jump. When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. Pete is a rokix. Can Pete swim? Answer yes or no.
structured: {"chain": ["rokix", "mamer", "besak", "nimir", "tevor", "biler", "besek", "sivon", "bator", "somok", "katix", "sasex", "zinar", "latax", "zevik", "dirin", "ratok", "tinar", "ladix", "memon", "zidor", "nemen", "reron"], "member": "Pete", "rules": [["reron", "jump", true], ["zidor", "swim", false], ["nemen", "swim", false], ["zevik", "swim", true], ["dirin", "swim", false], ["tinar", "swim", false], ["latax", "swim", false], ["zinar", "jump", true], ["memon", "swim", true], ["mamer", "jump", false], ["tevor", "jump", true], ["ratok", "swim", false], ["nemen", "jump", false], ["ladix", "swim", true], ["reron", "swim", false], ["zinar", "swim", false], ["latax", "jump", true], ["katix", "jump", false]], "verb": "swim"}
answer: no
```

### `R1.categories_follow_r4` (family categories, intended part ?)

structured: {"cats", "all": [[a, b]], "none": [[a, b]], "some": [[a, b]], "kind": "all"|"none"|"some", "x", "y", "answer_convention"}; indices into "cats".
Premises: "All A are B." (a), "No A are B." and "Some A are B." The item STATES (ruling R-4) that every group named has at least one member, what "some" and "no" say, and what the three
answers mean: yes = the statement must be true, no = it must be false (its opposite must be true), cannot be determined = it could be either. (The earlier frame, "Does it follow that
...? yes, no or cannot be determined", did not define "no": read as "no, it does not follow", 1,394 of 3,500 keys would change.)
Entailment (complete for this fragment; witnesses: one per group, in every group above it, and one per "Some" premise, in the groups above both its sides): "All x are y" must be true iff
y is above x; must be false iff some witness lies in x and in a group disjoint from y; "No x are y" is true iff x and y are disjoint (a "No" pair above one each) and false iff some witness
lies in both; "Some x are y" is true iff some witness lies in both, false iff x and y are disjoint. The answer and the kind of statement are drawn first (each uniform, independent); then the pair is
drawn uniformly among the statements of that kind with that answer that are not stated verbatim (Retry when there is none). So the kind carries no information about the answer.

Example (level 2):

```
question: All zinar are zator. No zinar are volek. Some zator are volek. All liser are volek. All liser are zator. Some zinar are zator. All liser are mekix. Every group named here has at least one member. "Some X are Y" means that at least one thing is both an X and a Y; "No X are Y" means that nothing is both. Consider the statement: "some mekix are zinar". Answer yes if the statement must be true, no if the statement must be false, or cannot be determined if the statements above leave it open (it could be true and it could be false).
structured: {"all": [[1, 2], [0, 2], [1, 4], [1, 3]], "answer_convention": "yes = must be true; no = must be false; cannot be determined = could be either; every named group is non-empty", "cats": ["zinar", "liser", "zator", "mekix", "volek"], "kind": "some", "none": [[0, 4]], "some": [[0, 2], [2, 4]], "x": 3, "y": 0}
answer: cannot be determined
```

### `R1.conditional_decision_tree_r4` (family conditional, intended part ?)

Same schema as conditional_decision_tree: {"tree", "facts", "actions"}. Four actions (eight at level 6); the leaves of the tree (2^depth of them, depth = 3, 3, 4, 4, 4, 5, 5 by level) carry each action the same
number of times (the leaf actions are a shuffled list with equal counts), so how often an action is named says nothing about which is reached (earlier shape: the most-mentioned
action was right 0.408 of the time against 0.271).

Example (level 2):

```
question: Your rule is: if the zatex light is on, then (if the zalax light is on, then (if the voson light is on, then (if the lanor light is on, then (knock), otherwise (run)), otherwise (if the lanor light is on, then (jump), otherwise (jump))), otherwise (if the nelir light is on, then (if the dedir light is on, then (run), otherwise (turn left)), otherwise (if the lanor light is on, then (knock), otherwise (run)))), otherwise (if the zalax light is on, then (if the nelir light is on, then (if the voson light is on, then (turn left), otherwise (turn left)), otherwise (if the voson light is on, then (run), otherwise (jump))), otherwise (if the nelir light is on, then (if the dedir light is on, then (knock), otherwise (turn left)), otherwise (if the lanor light is on, then (jump), otherwise (knock)))). Right now, it is false that the dedir light is on; it is false that the lanor light is on; it is true that the nelir light is on; it is false that the voson light is on; it is false that the zalax light is on; it is true that the zatex light is on. What do you do? Choose from jump, knock, run and turn left.
structured: {"actions": ["jump", "knock", "run", "turn left"], "facts": {"the dedir light is on": false, "the lanor light is on": false, "the nelir light is on": true, "the voson light is on": false, "the zalax light is on": false, "the zatex light is on": true}, "tree": ["if", "the zatex light is on", ["if", "the zalax light is on", ["if", "the voson light is on", ["if", "the lanor light is on", ["do", "knock"], ["do", "run"]], ["if", "the lanor light is on", ["do", "jump"], ["do", "jump"]]], ["if", "the nelir light is on", ["if", "the dedir light is on", ["do", "run"], ["do", "turn left"]], ["if", "the lanor light is on", ["do", "knock"], ["do", "run"]]]], ["if", "the zalax light is on", ["if", "the nelir light is on", ["if", "the voson light is on", ["do", "turn left"], ["do", "turn left"]], ["if", "the voson light is on", ["do", "run"], ["do", "jump"]]], ["if", "the nelir light is on", ["if", "the dedir light is on", ["do", "knock"], ["do", "turn left"]], ["if", "the lanor light is on", ["do", "jump"], ["do", "knock"]]]]]}
answer: turn left
```

### `R1.conditional_threshold_rule_r4` (family conditional, intended part ?)

Same schema as conditional_threshold_rule_r2/_r3: {"members": [[name, weight]], "votes": {name: "yes"|"no"|"abstain"}, "margin": D}. The motion passes when the weight
of the yes votes minus the weight of the no votes (abstentions count for neither) is at least D. Weights 1 to 9 and 6 to 12 members, so the margin has a wide spread and a partial sum (yes weight alone, say) is rarely the margin. The votes are
drawn first; the answer is then drawn (a fair coin) and D is set from the computed margin d: D = d - offset with offset in {0, 1} for yes (d >= D) and in {-1, -2} for no
(d < D). So the answer is a function of the offset alone, which is independent of the votes: no reading of the votes alone (heaviest voter, counts, sign of the margin) and no reading
of D alone carries it except through the offset's size (at most 2, against a margin spread of about 10). Nothing is redrawn on a heuristic's outcome.

Example (level 2):

```
question: A committee votes on a motion. Glen has weight 1, Pete has weight 2, Sia has weight 5, Lena has weight 2, Quinn has weight 9, Ugo has weight 2, Fern has weight 4, Elsa has weight 8. The motion passes if the total weight of the members who vote yes, minus the total weight of the members who vote no, is at least 4 (members who abstain count for neither side). The votes: Glen no, Pete no, Sia no, Lena yes, Quinn abstain, Ugo abstain, Fern abstain, Elsa yes. Does the motion pass? Answer yes or no.
structured: {"margin": 4, "members": [["Glen", 1], ["Pete", 2], ["Sia", 5], ["Lena", 2], ["Quinn", 9], ["Ugo", 2], ["Fern", 4], ["Elsa", 8]], "votes": {"Elsa": "yes", "Fern": "abstain", "Glen": "no", "Lena": "yes", "Pete": "no", "Quinn": "abstain", "Sia": "no", "Ugo": "abstain"}}
answer: no
```

### `R1.containers_stack_piles_r4` (family containers, intended part ?)

Same schema as containers_stack_piles: {"piles", "initial": {pile: [bottom..top]}, "ops": [["move", a, b] | ["reverse", p]], "ask": pile}. Blocks are never named like a colour. Every move
is a legal move of a random top block, and there are many of them for the number of blocks (12 + 3 level moves for 5 + level blocks; reversals from level 1 on, 3 in 10 operations), so the final top block of a
pile has come from nearly anywhere: the initial top, the initial bottom, the last block moved onto the pile and the first one moved onto it are each right about as often as a random
block (earlier shapes: the last block moved onto the asked pile was right 0.60 of the time, and 0.17 only after a redraw that raised the initial bottom to 0.30). The asked pile is drawn uniformly among the non-empty piles whose most
recent change was a block taken off or a turn (a design rule of the question, not a reading of a heuristic: the block last put onto the pile is then never the top, and the top is
whatever lay below it). No redraw.

Example (level 2):

```
question: There are three piles of blocks. The black pile holds, from bottom to top: teapot, quilt and flute. The purple pile holds, from bottom to top: needle and whistle. The yellow pile holds, from bottom to top: mirror and pencil. Move the top block of the yellow pile onto the purple pile. Move the top block of the purple pile onto the black pile. Move the top block of the black pile onto the yellow pile. Move the top block of the black pile onto the yellow pile. Turn the yellow pile upside down. Turn the yellow pile upside down. Turn the black pile upside down. Move the top block of the purple pile onto the black pile. Turn the yellow pile upside down. Move the top block of the purple pile onto the black pile. Move the top block of the black pile onto the yellow pile. Turn the yellow pile upside down. Move the top block of the yellow pile onto the purple pile. Move the top block of the black pile onto the yellow pile. Move the top block of the purple pile onto the yellow pile. Move the top block of the black pile onto the purple pile. Turn the black pile upside down. Move the top block of the yellow pile onto the black pile. Which block is on top of the yellow pile at the end? Choose from flute, mirror, needle, pencil, quilt, teapot and whistle.
structured: {"ask": "the yellow pile", "initial": {"the black pile": ["teapot", "quilt", "flute"], "the purple pile": ["needle", "whistle"], "the yellow pile": ["mirror", "pencil"]}, "ops": [["move", "the yellow pile", "the purple pile"], ["move", "the purple pile", "the black pile"], ["move", "the black pile", "the yellow pile"], ["move", "the black pile", "the yellow pile"], ["reverse", "the yellow pile"], ["reverse", "the yellow pile"], ["reverse", "the black pile"], ["move", "the purple pile", "the black pile"], ["reverse", "the yellow pile"], ["move", "the purple pile", "the black pile"], ["move", "the black pile", "the yellow pile"], ["reverse", "the yellow pile"], ["move", "the yellow pile", "the purple pile"], ["move", "the black pile", "the yellow pile"], ["move", "the purple pile", "the yellow pile"], ["move", "the black pile", "the purple pile"], ["reverse", "the black pile"], ["move", "the yellow pile", "the black pile"]], "piles": ["the black pile", "the purple pile", "the yellow pile"]}
answer: whistle
```

### `R1.elimination_bracket_r4` (family elimination, intended part ?)

structured: {"players": [bracket order], "results": [[winner, loser]] (every pair, a random near-regular tournament), "ask": ["champion"] | ["runner_up"] | ["beaten_by", name, exit_round]}.
Adjacent players meet in round one, the winner of a meeting is the one who won their earlier game; winners keep their order and pair adjacent again. 8 players for levels 0 to 2, 16 for
levels 3 to 6. The tournament of results is a random NEAR-REGULAR one (every player wins half their games, give or take one), so a player's number of wins says almost nothing about how far
they go (a random tournament made the most-wins player champion 47 % of the time). Question by level: 0 champion; 1 runner-up; 2 champion or runner-up; 3 champion; 4 runner-up; 5 "who
knocks X out" for X drawn uniformly among the players who lose in round 3 (the semi-finals); 6 any of the three kinds. Never round one (so the first-round neighbour is never the answer; the
earlier shape: neighbour right in 69 % of the "knocks out" items) and never round two (the knocker is then one of two players of X's own quarter, which the bracket geometry gives away).
The round of exit is chosen first; nothing is redrawn on a heuristic's outcome.

Example (level 2):

```
question: A knockout tournament has 8 players listed in bracket order: Stan, Bruno, Tina, Felix, Emil, Opal, Ivy, Sia. In round one the first two listed play each other, the next two play each other, and so on. Whenever two players meet in the tournament, the winner is whoever won their earlier game against each other: Emil beat Opal. Emil beat Sia. Bruno beat Emil. Sia beat Stan. Tina beat Stan. Opal beat Sia. Tina beat Opal. Felix beat Opal. Felix beat Tina. Ivy beat Bruno. Emil beat Ivy. Stan beat Opal. Stan beat Emil. Ivy beat Felix. Tina beat Emil. Bruno beat Stan. Felix beat Bruno. Felix beat Sia. Bruno beat Tina. Opal beat Bruno. Sia beat Tina. Stan beat Felix. Stan beat Ivy. Emil beat Felix. Ivy beat Sia. Tina beat Ivy. Sia beat Bruno. Opal beat Ivy. The winners keep their order and are paired the same way in the next round, until one player is left. Who wins the tournament? Choose from Bruno, Emil, Felix, Ivy, Opal, Sia, Stan and Tina.
structured: {"ask": ["champion"], "players": ["Stan", "Bruno", "Tina", "Felix", "Emil", "Opal", "Ivy", "Sia"], "results": [["Emil", "Opal"], ["Emil", "Sia"], ["Bruno", "Emil"], ["Sia", "Stan"], ["Tina", "Stan"], ["Opal", "Sia"], ["Tina", "Opal"], ["Felix", "Opal"], ["Felix", "Tina"], ["Ivy", "Bruno"], ["Emil", "Ivy"], ["Stan", "Opal"], ["Stan", "Emil"], ["Ivy", "Felix"], ["Tina", "Emil"], ["Bruno", "Stan"], ["Felix", "Bruno"], ["Felix", "Sia"], ["Bruno", "Tina"], ["Opal", "Bruno"], ["Sia", "Tina"], ["Stan", "Felix"], ["Stan", "Ivy"], ["Emil", "Felix"], ["Ivy", "Sia"], ["Tina", "Ivy"], ["Sia", "Bruno"], ["Opal", "Ivy"]]}
answer: Emil
```

### `R1.graph_shortest_route_r4` (family graph, intended part ?)

structured: {"towns", "roads": [[a, b, length]] (two-way), "start", "end", "planted_roads": h}. Answer: the smallest total length of a route from start to end (open number). The route
is PLANTED with h = (3, 3, 4, 4, 5, 5, 6)[level] roads: every town gets a potential (the spine towns the running length along the route, the decoy towns a value within 1 of a spine town) and every road has
length >= the difference of its ends' potentials, with equality only on the spine, so any other route is strictly longer. The shortest route therefore has exactly h roads at every level
(the earlier shape: two roads in 58 to 77 % of the items at every level), and a direct road start-end, if present, is strictly longer than the answer.

Example (level 2):

```
question: There is a two-way road between Eastvale and Ravenna of length 12. There is a two-way road between Brook and Vale of length 2. There is a two-way road between Harrow and Vale of length 8. There is a two-way road between Dunmore and Eastvale of length 14. There is a two-way road between Eastvale and Yarrow of length 3. There is a two-way road between Dunmore and Harrow of length 3. There is a two-way road between Harrow and Norwick of length 4. There is a two-way road between Brook and Eastvale of length 26. There is a two-way road between Ravenna and Yarrow of length 5. There is a two-way road between Harrow and Ravenna of length 4. There is a two-way road between Brook and Yarrow of length 20. There is a two-way road between Brook and Ravenna of length 16. What is the smallest total length of a route from Vale to Eastvale along these roads?
structured: {"end": "Eastvale", "planted_roads": 4, "roads": [["Eastvale", "Ravenna", 12], ["Brook", "Vale", 2], ["Harrow", "Vale", 8], ["Dunmore", "Eastvale", 14], ["Eastvale", "Yarrow", 3], ["Dunmore", "Harrow", 3], ["Harrow", "Norwick", 4], ["Brook", "Eastvale", 26], ["Ravenna", "Yarrow", 5], ["Harrow", "Ravenna", 4], ["Brook", "Yarrow", 20], ["Brook", "Ravenna", 16]], "start": "Vale", "towns": ["Vale", "Harrow", "Ravenna", "Yarrow", "Eastvale", "Brook", "Norwick", "Dunmore"]}
answer: 20
```

### `R1.instant_runoff_r4` (family voting, intended part ?)

Same schema as instant_runoff: {"candidates", "ballots": [[count, [ranking, best first]]]}. Rounds of elimination of the candidate with the fewest ballots counting for them, as before.
Candidates: 4 + level // 3 (at least four, so that "the top two meet in a runoff" is a different rule from the elimination count). Each candidate's first-place total is a base of 18 plus
0 to 2 (so the plurality leader is a near coin flip among the candidates), split into one to three groups of voters; the rest of every ranking is a random order. Items with a tie for
the fewest are drawn again (a validity rule, not a reading of a heuristic). The earlier shape had the plurality leader winning 79 % of the time, and the redraw that fixed that made the
items comeback-heavy by level.

Example (level 2):

```
question: Cara, Cass, Esme and Otto are candidates. 5 voters rank them Cara > Otto > Cass > Esme (best first). 19 voters rank them Otto > Cass > Cara > Esme (best first). 1 voter rank them Esme > Otto > Cass > Cara (best first). 18 voters rank them Esme > Cass > Otto > Cara (best first). 18 voters rank them Cass > Otto > Cara > Esme (best first). 15 voters rank them Cara > Esme > Cass > Otto (best first). The count goes in rounds: each round, every ballot counts for its best candidate still in the race; the candidate with the fewest ballots counting for them is out, and the next round starts. It continues until one candidate is left. Who is left?
structured: {"ballots": [[5, ["Cara", "Otto", "Cass", "Esme"]], [19, ["Otto", "Cass", "Cara", "Esme"]], [1, ["Esme", "Otto", "Cass", "Cara"]], [18, ["Esme", "Cass", "Otto", "Cara"]], [18, ["Cass", "Otto", "Cara", "Esme"]], [15, ["Cara", "Esme", "Cass", "Otto"]]], "candidates": ["Esme", "Cass", "Otto", "Cara"]}
answer: Otto
```

### `R1.kinship_ancestor_r4` (family kinship, intended part ?)

Same schema as kinship_ancestor: {"parent", "child", "generations", "people"}. The people form three families, each a random tree in which a new person is attached to one of the
last three people added (long lines, few leaves). The asked person is drawn among the members of the first family at least k generations below its root (weight depth - k + 1), and the answer is
its ancestor k generations up, which may be the root of that family (earlier shapes: never the root in _r3, always the root in the first shape). Three roots exist, and the options are the answer plus up to five people with the same number of children and the same "has a parent" status as the answer, so how often a person is
named, whether they are a leaf and whether they are parentless say nothing about which option is right. No redraw on a heuristic's outcome.

Example (level 2):

```
question: Elsa is the parent of Tom. Nell is the parent of Gwen. Dion is the parent of Uri. Elsa is the parent of Ines. Flynn's parent is Dev. Dev's parent is Pru. Sean's parent is Raul. Dev is the parent of Ivy. Cass is the parent of Kurt. Ivy is the parent of Pearl. Elsa is the parent of Uzi. Yara is the parent of Cara. Nell's parent is Dev. Raul's parent is Pru. Bea is the parent of Dion. Zane's parent is Elsa. Kenji's parent is Ivy. Cass's parent is Raul. Yara's parent is Kenji. Fern's parent is Dion. Hope is the parent of Bea. Nobody else has a recorded parent. Who is the grandparent of Kurt? Choose from Dion, Ivy and Raul.
structured: {"child": "Kurt", "generations": 2, "options": ["Dion", "Ivy", "Raul"], "parent": {"Bea": "Hope", "Cara": "Yara", "Cass": "Raul", "Dev": "Pru", "Dion": "Bea", "Fern": "Dion", "Flynn": "Dev", "Gwen": "Nell", "Ines": "Elsa", "Ivy": "Dev", "Kenji": "Ivy", "Kurt": "Cass", "Nell": "Dev", "Pearl": "Ivy", "Raul": "Pru", "Sean": "Raul", "Tom": "Elsa", "Uri": "Dion", "Uzi": "Elsa", "Yara": "Kenji", "Zane": "Elsa"}, "people": ["Bea", "Cara", "Cass", "Dev", "Dion", "Elsa", "Fern", "Flynn", "Gwen", "Hope", "Ines", "Ivy", "Kenji", "Kurt", "Nell", "Pearl", "Pru", "Raul", "Sean", "Tom", "Uri", "Uzi", "Yara", "Zane"]}
answer: Raul
```

### `R1.kinship_descendants_r4` (family kinship, intended part ?)

structured: {"people", "parent": {child: parent}, "ask": "descendants", "candidates": [the children of "root"], "root": name}. Question: among a named person's children, who has
the most descendants (children, their children, and so on). All candidates are at the same depth, so depth says nothing. Each candidate's number of descendants S_i is drawn
(distinct values, at least 6), and its numbers of children (1 to 3) and of grandchildren (1 to 3) are drawn independently of S_i; the other S_i - children - grandchildren descendants form a line
below one grandchild. So the number of children, of grandchildren and the number of times a candidate is named are independent of the answer. The named person has a parent and a brother with children, and there is an
unrelated family, so the named person is not the parentless root. (The earlier shape's answer was a child of the root 86 to 100 % of the time.)

Example (level 2):

```
question: Sven is the parent of Rosa. Emil is the parent of Igor. Kate is the parent of Lila. Will is the parent of Otto. Jana is the parent of Will. Pia is the parent of Sia. Jade is the parent of Pearl. Yves is the parent of Pru. Will is the parent of Reed. Cara is the parent of Thea. Zed is the parent of Gus. Reed is the parent of Bruno. Opal is the parent of Sven. Ada is the parent of Zita. Abel is the parent of Anja. Thea is the parent of Emil. Zane is the parent of Maya. Nora is the parent of Milo. Nico is the parent of Tina. Will is the parent of Jade. Wanda is the parent of Hank. Kira is the parent of Finn. Maya is the parent of Abel. Otto is the parent of Zane. Lila is the parent of Kai. Joss is the parent of Rex. Rosa is the parent of Joss. Hope is the parent of Uzi. Bea is the parent of Zed. Zita is the parent of Dev. Jana is the parent of Boris. Walt is the parent of Nico. Tina is the parent of Gita. Boris is the parent of Cara. Anja is the parent of Pia. Flynn is the parent of Zara. Yara is the parent of Wanda. Boris is the parent of Kira. Milo is the parent of Ada. Rex is the parent of Yara. Omar is the parent of Kate. Kai is the parent of Kenji. Igor is the parent of Flynn. Dev is the parent of Yves. Zed is the parent of Sean. Quinn is the parent of Yuri. Gita is the parent of Ulf. Bea is the parent of Jana. Hank is the parent of Walt. Pru is the parent of Omar. Jana is the parent of Opal. Jana is the parent of Nora. Nora is the parent of Hope. Quinn is the parent of Esme. Nobody else has a recorded parent. Among the children of Jana, who has the most descendants (children, their children, and so on, all the way down)? Choose from Boris, Nora, Opal and Will.
structured: {"ask": "descendants", "candidates": ["Boris", "Nora", "Opal", "Will"], "parent": {"Abel": "Maya", "Ada": "Milo", "Anja": "Abel", "Boris": "Jana", "Bruno": "Reed", "Cara": "Boris", "Dev": "Zita", "Emil": "Thea", "Esme": "Quinn", "Finn": "Kira", "Flynn": "Igor", "Gita": "Tina", "Gus": "Zed", "Hank": "Wanda", "Hope": "Nora", "Igor": "Emil", "Jade": "Will", "Jana": "Bea", "Joss": "Rosa", "Kai": "Lila", "Kate": "Omar", "Kenji": "Kai", "Kira": "Boris", "Lila": "Kate", "Maya": "Zane", "Milo": "Nora", "Nico": "Walt", "Nora": "Jana", "Omar": "Pru", "Opal": "Jana", "Otto": "Will", "Pearl": "Jade", "Pia": "Anja", "Pru": "Yves", "Reed": "Will", "Rex": "Joss", "Rosa": "Sven", "Sean": "Zed", "Sia": "Pia", "Sven": "Opal", "Thea": "Cara", "Tina": "Nico", "Ulf": "Gita", "Uzi": "Hope", "Walt": "Hank", "Wanda": "Yara", "Will": "Jana", "Yara": "Rex", "Yuri": "Quinn", "Yves": "Dev", "Zane": "Otto", "Zara": "Flynn", "Zed": "Bea", "Zita": "Ada"}, "people": ["Jana", "Opal", "Nora", "Boris", "Will", "Sven", "Rosa", "Joss", "Rex", "Yara", "Wanda", "Hank", "Walt", "Nico", "Tina", "Gita", "Ulf", "Milo", "Hope", "Uzi", "Ada", "Zita", "Dev", "Yves", "Pru", "Omar", "Kate", "Lila", "Kai", "Kenji", "Kira", "Cara", "Thea", "Finn", "Emil", "Igor", "Flynn", "Zara", "Reed", "Otto", "Jade", "Zane", "Pearl", "Bruno", "Maya", "Abel", "Anja", "Pia", "Sia", "Bea", "Zed", "Sean", "Gus", "Quinn", "Esme", "Yuri"], "root": "Jana"}
answer: Nora
```

### `R1.minimax_tree_r4` (family games, intended part ?)

structured: {"tree": nested list (a leaf is an integer payoff to Max; an inner node lists its options), "first": "max" | "min", "depth", "branching"}. Every level has its own depth and
branching: (2,2) (2,3) (3,2) (2,4) (3,3) (4,2) (3,4) for levels 0 to 6 (earlier shape: levels 0 to 2 identical, 3 and 4, 5 and 6). The first mover is drawn (Max or Min); leaves are signed
integers from -9 to 9. Answer: the payoff under perfect play (open number).

Example (level 2):

```
question: Two players, Max and Min, play a game with 3 choices in a row, Max choosing first and then Min, and so on in turn. At each choice the mover picks one of the 2 options shown. The game is written as nested options: (((-7 or 1) or (4 or -6)) or ((5 or 3) or (4 or -1))). When the options are all numbers, the number picked is the payoff. Max wants the payoff as large as possible and Min as small as possible, and both play perfectly. What is the payoff?
structured: {"branching": 2, "depth": 3, "first": "max", "tree": [[[-7, 1], [4, -6]], [[5, 3], [4, -1]]]}
answer: 4
```

### `R1.mst_cost_r4` (family network, intended part ?)

structured: {"towns", "roads": [[a, b, length]], "groups": [[town]]}. Answer: the smallest total length of roads that connect every town to every other (open number). The towns are in
2 to 4 groups of at least 3 (the groups are not stated); every pair inside a group is joined by a road of length 1 to 9, and groups are joined by roads of length 11 to 20 only. So each
town's cheapest road lies inside its group and the n - 1 cheapest roads all lie inside groups, whence neither "sum of each town's cheapest road" nor "sum of the n - 1 cheapest roads" is a
spanning tree: both differ from the answer in every item (the earlier shape: 0.93 at level 0).

Example (level 2):

```
question: A road between Fenwick and Zennor could be built with length 13. A road between Garth and Larkin could be built with length 13. A road between Brook and Fenwick could be built with length 3. A road between Garth and Zennor could be built with length 4. A road between Marlow and Zennor could be built with length 6. A road between Fenwick and Garth could be built with length 15. A road between Brook and Larkin could be built with length 9. A road between Brook and Zennor could be built with length 14. A road between Fenwick and Larkin could be built with length 8. A road between Garth and Marlow could be built with length 7. Some of these roads will be built so that every town can be reached from every other town, using as few roads as possible and the smallest possible total length. What is that total length?
structured: {"groups": [["Garth", "Marlow", "Zennor"], ["Larkin", "Brook", "Fenwick"]], "roads": [["Fenwick", "Zennor", 13], ["Garth", "Larkin", 13], ["Brook", "Fenwick", 3], ["Garth", "Zennor", 4], ["Marlow", "Zennor", 6], ["Fenwick", "Garth", 15], ["Brook", "Larkin", 9], ["Brook", "Zennor", 14], ["Fenwick", "Larkin", 8], ["Garth", "Marlow", 7]], "towns": ["Garth", "Marlow", "Zennor", "Larkin", "Brook", "Fenwick"]}
answer: 34
```

### `R1.nim_xor_r4` (family games, intended part ?)

structured: {"piles": [sizes], "size_class": m}. Two players alternate; on a turn a player removes at least one stone from ONE pile; whoever takes the last stone wins; the first player moves
first. Answer "first" or "second". Piles: an even number k (4, 4, 4, 6, 6, 8, 8), every pile in [m, 2m) (m = 32, 64, 128, 64, 128, 64, 128), so the largest pile is never larger than the rest together
and the top bit is set in every pile (an odd count of them would make the xor non-zero). The answer is drawn first; "second" (xor 0): k - 1 piles drawn, the last is their xor (in [m, 2m) because k - 1
is odd); "first": all piles drawn. The low bit of the last pile is set so the total is always even. Levels differ in the number of piles and the size class (the earlier levels differed only in size,
and level 0 had 270 distinct pile tuples).

Example (level 2):

```
question: A game has 4 piles of stones: 184, 242, 160, 234. Two players take turns. On a turn, a player must remove at least one stone, all from a single pile (any number up to the whole pile). The player who takes the very last stone wins. Both play perfectly and the first player moves first. Who wins, the first player or the second player? Answer first or second.
structured: {"piles": [184, 242, 160, 234], "size_class": 128}
answer: second
```

### `R1.order_compare_r4` (family order, intended part ?)

Same schema as order_compare: {"taller": [[a, b]] (a is taller than b), "x", "y"}. The asked pair is stated in NEITHER direction (the earlier shape: the asked or the reverse pair was
stated in 55.8 % of the items, always giving yes or no), the asked x is stated taller than someone and the asked y shorter than someone (so "x is never taller than anyone" and its mirror never apply), and the answer is drawn first (uniform over yes, no, cannot be determined); the pair is then
drawn uniformly among the pairs with that answer.

Example (level 2):

```
question: Tom is taller than Ivo. Ivo is taller than Dell. Ivo is taller than Kate. Dmitri is taller than Dell. Hal is taller than Kate. Kate is taller than Dmitri. Tom is taller than Omar. Ada is taller than Dell. Is Tom taller than Dmitri? Answer yes, no or cannot be determined.
structured: {"taller": [["Tom", "Ivo"], ["Ivo", "Dell"], ["Ivo", "Kate"], ["Dmitri", "Dell"], ["Hal", "Kate"], ["Kate", "Dmitri"], ["Tom", "Omar"], ["Ada", "Dell"]], "x": "Tom", "y": "Dmitri"}
answer: yes
```

### `R1.spatial_relative_directions_r4` (family spatial, intended part ?)

structured: {"places", "facts": [[a, direction, k, b]] (a lies k blocks <direction> of b), "x", "y"}. Streets form a grid. Answer: the street distance between x and y (blocks north or
south plus blocks east or west; an open number), where x and y are joined by no fact (at least two facts lie between them) and the distance is at least 1. The earlier shape asked for the
farthest place from an anchor; the farthest place was a leaf of the fact tree (least mentioned 0.383 against 0.245).

Example (level 2):

```
question: Ravenna is 9 blocks south of Eastvale. Vale is 8 blocks north of Thornbury. Calder is 1 block west of Brook. Vale is 8 blocks north of Eastvale. Brook is 6 blocks south of Penrith. Penrith is 7 blocks north of Vale. How far apart are Calder and Eastvale by street distance (blocks north or south plus blocks east or west)?
structured: {"facts": [["Ravenna", "south", 9, "Eastvale"], ["Vale", "north", 8, "Thornbury"], ["Calder", "west", 1, "Brook"], ["Vale", "north", 8, "Eastvale"], ["Brook", "south", 6, "Penrith"], ["Penrith", "north", 7, "Vale"]], "places": ["Thornbury", "Vale", "Penrith", "Brook", "Eastvale", "Ravenna", "Calder"], "x": "Calder", "y": "Eastvale"}
answer: 10
```

### `R1.stable_matching_r4` (family matching, intended part ?)

Same schema as stable_matching: {"proposers", "receivers", "prefs_p", "prefs_r", "ask"}. Deferred acceptance as before. The instance is PLANTED around a matching M: each proposer's rank rho_p
of M(p) is drawn; proposers are put in a random planting order with the asked proposer LAST, and the receivers above M(p) in p's list are rho_p - 1 partners of EARLIER proposers (rho_p uniform
in 1..position, so rho of the asked proposer is uniform in 1..n); each receiver's list is a random permutation of the proposers in which the receiver's partner under M is moved above every
proposer that wanted the receiver more than their own partner. Then M is stable, and no stable matching is better for any proposer (take the first proposer, in planting order, who does better
in some stable M'; the receiver he gets is the partner under M of an earlier proposer q, who then does worse than M and forms a blocking pair with that receiver), so deferred acceptance gives
M. The answer is still computed by running the procedure. The asked proposer's partner is their rho-th choice with rho uniform on 1..n, so no fixed rank (first, second, last choice) is the
answer more than 1/n of the time (the earlier shape: first choice 0.57; after a redraw on it, second choice 0.46 and first-mentioned 0.15). No redraw on a heuristic's outcome.

Example (level 2):

```
question: Some people ask others to partner with them. Vida would like, from best to worst: Yuri, Lila, Emil, Bea. Cara would like, from best to worst: Lila, Bea, Yuri, Emil. Xan would like, from best to worst: Emil, Yuri, Bea, Lila. Bruno would like, from best to worst: Bea, Yuri, Lila, Emil. Emil would like, from best to worst: Vida, Bruno, Cara, Xan. Lila would like, from best to worst: Bruno, Vida, Xan, Cara. Yuri would like, from best to worst: Xan, Cara, Bruno, Vida. Bea would like, from best to worst: Bruno, Xan, Vida, Cara. Matching goes in turns: a person from Bruno, Cara, Vida and Xan who has no partner asks the best person on their list that they have not asked yet. The person asked keeps the best proposer so far (by their own list) and says no to the others, who then ask the next person on their list. This goes on until everyone in Bruno, Cara, Vida and Xan has a partner. Who is Cara's partner at the end? Choose from Bea, Emil, Lila and Yuri.
structured: {"ask": "Cara", "prefs_p": {"Bruno": ["Bea", "Yuri", "Lila", "Emil"], "Cara": ["Lila", "Bea", "Yuri", "Emil"], "Vida": ["Yuri", "Lila", "Emil", "Bea"], "Xan": ["Emil", "Yuri", "Bea", "Lila"]}, "prefs_r": {"Bea": ["Bruno", "Xan", "Vida", "Cara"], "Emil": ["Vida", "Bruno", "Cara", "Xan"], "Lila": ["Bruno", "Vida", "Xan", "Cara"], "Yuri": ["Xan", "Cara", "Bruno", "Vida"]}, "proposers": ["Cara", "Xan", "Bruno", "Vida"], "receivers": ["Emil", "Lila", "Yuri", "Bea"]}
answer: Lila
```

### `R1.temporal_critical_path_r4` (family temporal, intended part ?)

structured: {"jobs": [[person, days, [persons it waits for]]]}. A job with no wait starts on day 0, otherwise it starts the day all its predecessors are finished and lasts its number of days.
Answer: the day on which the last job finishes (an open number; day 0 is the start). The earlier shape asked WHO finishes last, so the answer was always a job nobody waits for and the
longest job (+0.12) or the deepest job (0.72) pointed at it; a number has neither tell. Jobs: 4 + level; each waits for 0 to 2 earlier jobs; durations 1 to 15.

Example (level 2):

```
question: Xena's job takes 4 days and starts as soon as the job of Pru is finished. Tess's job takes 11 days and starts as soon as the job of Xena is finished. Pru's job takes 13 days and starts as soon as the job of Ulf is finished. Jade's job takes 9 days and starts on day 0. Thea's job takes 11 days and starts as soon as the job of Ulf is finished. Ulf's job takes 4 days and starts on day 0. Counting the start as day 0, on which day is the last of these jobs finished?
structured: {"jobs": [["Ulf", 4, []], ["Pru", 13, ["Ulf"]], ["Xena", 4, ["Pru"]], ["Thea", 11, ["Ulf"]], ["Jade", 9, []], ["Tess", 11, ["Xena"]]]}
answer: 32
```

### `R1.topological_order_r4` (family scheduling, intended part ?)

structured: {"jobs": [[name, [prerequisite names]]], "day": j}. One job is done per day; each day, among the jobs whose prerequisites are all done, the one whose name comes first in
alphabetical order is done. Answer: the job done on day j (2 <= j <= n). Prerequisites: every job after the first has 1 to 3 of them (earlier shape: 0 to 2), so the order is nearly forced and
the j-th name in alphabetical order rarely decides; no redraw.

Example (level 2):

```
question: There are 8 jobs and one job is done each day. Bea needs Uri and Wanda to be done first. Ugo needs Uma to be done first. Pearl needs Ugo and Uma to be done first. Uri needs Maya, Pearl and Ugo to be done first. Wanda needs Pearl and Ugo to be done first. Maya needs Pearl and Ugo to be done first. Lila needs Ugo and Uma to be done first. Uma has no prerequisite. Each day, among the jobs that can be done (all their prerequisites are already done), the job whose name comes first in alphabetical order is done. Which job is done on day 3? Choose from Bea, Lila, Maya, Pearl, Ugo, Uma, Uri and Wanda.
structured: {"day": 3, "jobs": [["Bea", ["Uri", "Wanda"]], ["Ugo", ["Uma"]], ["Pearl", ["Ugo", "Uma"]], ["Uri", ["Maya", "Pearl", "Ugo"]], ["Wanda", ["Pearl", "Ugo"]], ["Maya", ["Pearl", "Ugo"]], ["Lila", ["Ugo", "Uma"]], ["Uma", []]]}
answer: Lila
```

### `R1.venn_counting_r4` (family sets, intended part ?)

structured: {"total", "groups", "sizes": {group: size}, "pairs": {"a|b": n}, "triples": {"a|b|c": n}, "quad": n | null, "triple": n | null (3 groups), "ask": ...}. Every person is counted once. Given the
total, every group size, every overlap of two, of three and of four. Per level (groups, asked quantity): (2 none) (2 exactly one) (3 none) (3 exactly two) (3 at least two) (4 none) (4 exactly two)
(earlier shape: levels differed only in magnitudes). Answer: the number of people asked for (open number).

Example (level 2):

```
question: Among 43 people, 21 people are in the baking group; 27 people are in the archery group; 16 people are in the poetry group; 11 are in both the baking and the archery groups; 12 are in both the baking and the poetry groups; 4 are in both the archery and the poetry groups; 3 are in all of the baking, archery and poetry groups. Each person is counted once in each number that applies to them. How many of the people are in none of these groups?
structured: {"ask": "none", "groups": ["baking", "archery", "poetry"], "pairs": {"archery|poetry": 4, "baking|archery": 11, "baking|poetry": 12}, "quad": null, "sizes": {"archery": 27, "baking": 21, "poetry": 16}, "total": 43, "triple": 3, "triples": {"baking|archery|poetry": 3}}
answer: 3
```
