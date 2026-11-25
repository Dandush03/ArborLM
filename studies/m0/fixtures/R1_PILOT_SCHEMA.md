# R1 pilot lineages: structured-form schema for the second-solver agent

Written by the implementer for the separate second-solver context (ADR-0033 section 6.2, audit R6). Not a result; nothing here approves anything.

## Interface

- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.
- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`R1.<name>`); one module per family, `studies/m0/solvers_r1_<family>.py`.
- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).
- Fixtures: `studies/m0/fixtures/r1_pilot/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).
- The question text is in the fixture only so that an auditor can check the wording against the structured form; solvers must not parse it.

## Lineages (intended part, family, the builder's description of its structured form and answer rule)

### `R1.activity_selection` (family scheduling, intended part ?)

structured: {"meetings": [[name, start, end]]}. A person can attend several meetings if they do not overlap (a meeting that ends exactly when another starts is fine).
Answer: the largest number of meetings one person can attend (a number).

Example (level 2):

```
question: Leo's meeting runs from minute 48 to minute 50. Raul's meeting runs from minute 65 to minute 68. Jana's meeting runs from minute 68 to minute 71. Cyrus's meeting runs from minute 52 to minute 61. Will's meeting runs from minute 62 to minute 69. Gita's meeting runs from minute 53 to minute 62. Emil's meeting runs from minute 64 to minute 71. Kai's meeting runs from minute 52 to minute 57. Oscar's meeting runs from minute 12 to minute 17. Lila's meeting runs from minute 13 to minute 19. A meeting that ends at minute t and one that starts at minute t do not overlap. What is the largest number of these meetings that one person could attend?
structured: {"meetings": [["Leo", 48, 50], ["Raul", 65, 68], ["Jana", 68, 71], ["Cyrus", 52, 61], ["Will", 62, 69], ["Gita", 53, 62], ["Emil", 64, 71], ["Kai", 52, 57], ["Oscar", 12, 17], ["Lila", 13, 19]]}
answer: 5
```

### `R1.boolean_lights_r2` (family boolean_state, intended part ?)

Same schema as boolean_lights. The asked lamp is wired to at least one switch that is pressed (earlier shape: never toggled in 31 of 140), and the initial state is
worded without "the rest are off" when no lamp is off.

Example (level 2):

```
question: There are 6 lamps numbered 1 to 6. At the start, lamps 1, 3 and 5 are on and every other lamp is off. The green switch toggles lamps 2, 5 and 6 (each one goes from on to off or from off to on). The yellow switch toggles lamp 5 (each one goes from on to off or from off to on). The orange switch toggles lamp 1 (each one goes from on to off or from off to on). The switches are pressed in this order: green, green, yellow, yellow, orange, yellow, green. Is lamp 1 on at the end? Answer yes or no.
structured: {"ask": 1, "initial": [1, 0, 1, 0, 1, 0], "lamps": 6, "presses": ["green", "green", "yellow", "yellow", "orange", "yellow", "green"], "switches": {"green": [2, 5, 6], "orange": [1], "yellow": [5]}}
answer: no
```

### `R1.categories_default_exceptions_r3` (family categories, intended part ?)

Same schema as categories_default_exceptions. The asked verb has rules in FIVE groups above the member's own group (never in its own group). The sign vector of the five
rules (most specific first; the most specific decides) is drawn by CONSTRUCTION so that three trivial shortcuts are independent of the answer: the least specific rule agrees with the
answer with probability 1/2, and of the three middle rules none or two (equally likely) agree, so that P(majority = answer) = 1/2 and P(a random listed rule = answer) = 1/2,
with no redraw. (The r2 shape's redraw pushed 'the least specific rule' to 98 % opposite to the answer;
the r3 draft with three or four rules could not make the majority and the least specific rule both unbiased.) The chain has 6 + level // 2 groups; the member is in the smallest.

Example (level 2):

```
question: Every lokir is a vosek. Every vosek is a zidan. Every zidan is a karir. Every karir is a tedok. Every tedok is a kemok. Every kemok is a molir. A vosek cannot hum. A tedok cannot glow. A karir can hum. A kemok cannot glow. A zidan cannot glow. A zidan can hum. A kemok can hum. A lokir cannot glow. A molir cannot hum. When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. Esme is a lokir. Can Esme hum? Answer yes or no.
structured: {"chain": ["lokir", "vosek", "zidan", "karir", "tedok", "kemok", "molir"], "member": "Esme", "rules": [["vosek", "hum", false], ["tedok", "glow", false], ["karir", "hum", true], ["kemok", "glow", false], ["zidan", "glow", false], ["zidan", "hum", true], ["kemok", "hum", true], ["lokir", "glow", false], ["molir", "hum", false]], "verb": "hum"}
answer: no
```

### `R1.categories_follow_r2` (family categories, intended part ?)

Shape revision of the core lineage R1.categories_follow (same schema: {"cats", "all", "none", "kind", "x", "y"}). The item states that a group may have no members;
the answer is chosen first (yes / no / cannot be determined uniformly) and a query with that answer is drawn, so the key is balanced (earlier shape: 'cannot be
determined' in 77.6 % of items against a chance of 1/3, and an unstated existential-import convention that made 236 of 500 items ambiguous). Kinds: "all" (does
every X belong to Y: yes or cannot), "none" (does no X belong to Y: yes or cannot), "some" (do some X belong to Y: no or cannot; yes is never forced because a group may be empty).

Example (level 2):

```
question: All bador are tobor. No setor are nokan. All zimor are tobor. All nokan are bador. All zimor are setor. (A group may have no members at all; "some X are Y" says that at least one thing is both.) Does it follow that no nokan is a zimor? Answer yes, no or cannot be determined.
structured: {"all": [[1, 2], [0, 3], [1, 4], [3, 4]], "cats": ["nokan", "zimor", "setor", "bador", "tobor"], "kind": "none", "none": [[2, 0]], "x": 0, "y": 1}
answer: yes
```

### `R1.conditional_decision_tree` (family conditional, intended part B)

structured: {"tree": node, "facts": {attribute: true|false}, "actions": [action]}; a node is ["do", action] or ["if", attribute, node_if_true,
node_if_false]. Answer: the action at the leaf reached by testing each attribute against the facts.

Example (level 2):

```
question: Your rule is: if the novox light is on, then (if the deken light is on, then (if the lemir light is on, then (wait), otherwise (run)), otherwise (if the sekor light is on, then (turn left), otherwise (wait))), otherwise (if the sekor light is on, then (if the deken light is on, then (run), otherwise (jump)), otherwise (if the lemir light is on, then (jump), otherwise (jump))). Right now, it is false that the boror light is on; it is true that the deken light is on; it is false that the lemir light is on; it is true that the novox light is on; it is false that the sekor light is on. What do you do? Choose from jump, run, turn left and wait.
structured: {"actions": ["jump", "run", "turn left", "wait"], "facts": {"the boror light is on": false, "the deken light is on": true, "the lemir light is on": false, "the novox light is on": true, "the sekor light is on": false}, "tree": ["if", "the novox light is on", ["if", "the deken light is on", ["if", "the lemir light is on", ["do", "wait"], ["do", "run"]], ["if", "the sekor light is on", ["do", "turn left"], ["do", "wait"]]], ["if", "the sekor light is on", ["if", "the deken light is on", ["do", "run"], ["do", "jump"]], ["if", "the lemir light is on", ["do", "jump"], ["do", "jump"]]]]}
answer: run
```

### `R1.conditional_threshold_rule_r3` (family conditional, intended part ?)

conditional_threshold_rule_r2 with retuned redraw probabilities.

Example (level 2):

```
question: A committee votes on a motion. Yan has weight 1, Pru has weight 1, Edna has weight 1, Milo has weight 3, Hugo has weight 4, Dion has weight 1. The motion passes if the total weight of the members who vote yes, minus the total weight of the members who vote no, is at least 1 (members who abstain count for neither side). The votes: Yan yes, Pru yes, Edna abstain, Milo no, Hugo abstain, Dion no. Does the motion pass? Answer yes or no.
structured: {"margin": 1, "members": [["Yan", 1], ["Pru", 1], ["Edna", 1], ["Milo", 3], ["Hugo", 4], ["Dion", 1]], "votes": {"Dion": "no", "Edna": "abstain", "Hugo": "abstain", "Milo": "no", "Pru": "yes", "Yan": "yes"}}
answer: no
```

### `R1.containers_queue_line_r2` (family containers, intended part ?)

structured: {"line": [front..back], "ops": [["join", n] | ["cut", n] | ["serve"] | ["leave", n] | ["front_to_back"]], "ask": ["position", j]}. Answer: the person
in position j from the front (1 = front) at the end. (The earlier shape asked for the front or the back, so the last joiner or the last person let in was right in
99 of 140 items.)

Example (level 2):

```
question: A line, from front to back, is: Wanda, Orla, Greta and Marc. Ulf joins at the back. The person at the front is served and leaves. Kira joins at the back. Kira gets tired and leaves. Greta gets tired and leaves. The person at the front goes to the back of the line. Ivo is let in at the very front. The person at the front is served and leaves. Who is in position 3 from the front of the line at the end (position 1 is the very front)? Choose from Greta, Ivo, Kira, Marc, Orla, Ulf and Wanda.
structured: {"ask": ["position", 3], "line": ["Wanda", "Orla", "Greta", "Marc"], "ops": [["join", "Ulf"], ["serve"], ["join", "Kira"], ["leave", "Kira"], ["leave", "Greta"], ["front_to_back"], ["cut", "Ivo"], ["serve"]]}
answer: Orla
```

### `R1.containers_stack_piles_r3` (family containers, intended part ?)

containers_stack_piles_r2 with retuned redraw probabilities.

Example (level 2):

```
question: There are three piles of blocks. The blue pile holds, from bottom to top: whistle, ribbon and quilt. The orange pile holds, from bottom to top: hammer. The red pile holds, from bottom to top: scarf and violin. Move the top block of the orange pile onto the blue pile. Move the top block of the red pile onto the blue pile. Move the top block of the blue pile onto the orange pile. Move the top block of the red pile onto the blue pile. Move the top block of the blue pile onto the red pile. Move the top block of the orange pile onto the red pile. Move the top block of the red pile onto the orange pile. Which block is on top of the blue pile at the end? Choose from hammer, quilt, ribbon, scarf, violin and whistle.
structured: {"ask": "the blue pile", "initial": {"the blue pile": ["whistle", "ribbon", "quilt"], "the orange pile": ["hammer"], "the red pile": ["scarf", "violin"]}, "ops": [["move", "the orange pile", "the blue pile"], ["move", "the red pile", "the blue pile"], ["move", "the blue pile", "the orange pile"], ["move", "the red pile", "the blue pile"], ["move", "the blue pile", "the red pile"], ["move", "the orange pile", "the red pile"], ["move", "the red pile", "the orange pile"]], "piles": ["the blue pile", "the orange pile", "the red pile"]}
answer: hammer
```

### `R1.elimination_bracket_r3` (family elimination, intended part ?)

elimination_bracket_r2 with retuned redraw probabilities.

Example (level 2):

```
question: A knockout tournament has 4 players listed in bracket order: Kate, Oscar, Hank, Glen. In round one the first two listed play each other, the next two play each other, and so on. Whenever two players meet in the tournament, the winner is whoever won their earlier game against each other: Hank beat Oscar. Oscar beat Kate. Oscar beat Glen. Glen beat Hank. Hank beat Kate. Glen beat Kate. The winners keep their order and are paired the same way in the next round, until one player is left. Who loses the final?
structured: {"ask": ["runner_up"], "players": ["Kate", "Oscar", "Hank", "Glen"], "results": [["Hank", "Oscar"], ["Oscar", "Kate"], ["Oscar", "Glen"], ["Glen", "Hank"], ["Hank", "Kate"], ["Glen", "Kate"]]}
answer: Glen
```

### `R1.elimination_josephus` (family elimination, intended part A)

structured: {"people": [name] in circle order (after the last comes the first), "step": k, "ask": ["last"] | ["leave", j]}.
Counting starts at the first person as 1; the k-th person counted leaves, and counting restarts at the next person still in
the circle. Answer: the last person left, or the j-th person to leave.

Example (level 2):

```
question: Boris, Zita, Gwen, Uri, Milo and Abel stand in a circle in this order, and after Abel comes Boris again. Counting starts at Boris as 1 and goes around in that order. Every time the count reaches 2, the person counted leaves the circle, and counting starts again from 1 at the next person still in the circle. Who is the last person left in the circle?
structured: {"ask": ["last"], "people": ["Boris", "Zita", "Gwen", "Uri", "Milo", "Abel"], "step": 2}
answer: Milo
```

### `R1.equivalence_classes_r2` (family equivalence, intended part ?)

Same schema as equivalence_classes. The asked pair is NEVER a stated pair (earlier shape: stated verbatim in 68 of 140), and both asked
items are mentioned in some statement (earlier shape: an unmentioned item in 26 of 140, always cannot be determined).

Example (level 2):

```
question: midok is the same thing as bazir. zanix is a different thing from balek. balek is the same thing as vivex. bimor is a different thing from midok. zanix is the same thing as midok. Is bimor the same thing as vivex? Answer yes (they must be the same), no (they must be different) or cannot be determined.
structured: {"different": [["bimor", "midok"], ["zanix", "balek"]], "items": ["bimor", "bazir", "midok", "vizer", "vivex", "balek", "zanix"], "same": [["zanix", "midok"], ["midok", "bazir"], ["balek", "vivex"]], "x": "bimor", "y": "vivex"}
answer: cannot be determined
```

### `R1.equivalence_exchange_rates` (family equivalence, intended part B)

structured: {"items": [name], "rates": [[p, a, q, b]] meaning p units of a are worth the same as q units of b}. The rates connect all items.
Answer: the item whose single unit is worth the most (unique).

Example (level 2):

```
question: 27 units of apple are worth the same as 33 units of pencil. 33 units of quilt are worth the same as 34 units of apple. 15 units of whistle are worth the same as 12 units of violin. 33 units of violin are worth the same as 10 units of apple. Which of apple, pencil, quilt, violin and whistle is worth the most per single unit?
structured: {"items": ["pencil", "apple", "quilt", "violin", "whistle"], "rates": [[27, "apple", 33, "pencil"], [33, "quilt", 34, "apple"], [15, "whistle", 12, "violin"], [33, "violin", 10, "apple"]]}
answer: quilt
```

### `R1.graph_bipartite` (family graph, intended part B)

structured: {"people": [name], "rivals": [[a, b]]}. Answer yes/no: can everyone be split into two teams so that no two rivals share a team.

Example (level 2):

```
question: Ada, Ben, Bram, Gus, Jana and Zane must be split into two teams. Jana and Bram are rivals. Gus and Jana are rivals. Gus and Ben are rivals. Jana and Ada are rivals. Ben and Bram are rivals. Ben and Ada are rivals. Gus and Zane are rivals. Can they be split into two teams (either team may be any size) so that no two rivals are on the same team? Answer yes or no.
structured: {"people": ["Gus", "Ben", "Jana", "Zane", "Ada", "Bram"], "rivals": [["Jana", "Bram"], ["Gus", "Jana"], ["Gus", "Ben"], ["Jana", "Ada"], ["Ben", "Bram"], ["Ben", "Ada"], ["Gus", "Zane"]]}
answer: yes
```

### `R1.graph_shortest_route_r2` (family graph, intended part ?)

structured: {"towns": [name], "roads": [[a, b, length]] (two-way), "start": name, "end": name}. Answer: the smallest total length of a route from start to end (a
number; open answer). The shortest route has at least two roads. (The earlier shape asked for the first town on the route, which the nearest neighbour of the start
gave in 97 of 140 items.)

Example (level 2):

```
question: There is a two-way road between Oakham and Calder of length 7. There is a two-way road between Oakham and Ivybridge of length 9. There is a two-way road between Calder and Brook of length 12. There is a two-way road between Oakham and Upton of length 1. There is a two-way road between Norwick and Oakham of length 12. There is a two-way road between Norwick and Calder of length 6. There is a two-way road between Norwick and Brook of length 9. What is the smallest total length of a route from Ivybridge to Upton along these roads?
structured: {"end": "Upton", "roads": [["Oakham", "Calder", 7], ["Oakham", "Ivybridge", 9], ["Calder", "Brook", 12], ["Oakham", "Upton", 1], ["Norwick", "Oakham", 12], ["Norwick", "Calder", 6], ["Norwick", "Brook", 9]], "start": "Ivybridge", "towns": ["Norwick", "Oakham", "Ivybridge", "Calder", "Brook", "Upton"]}
answer: 10
```

### `R1.instant_runoff_r2` (family voting, intended part ?)

instant_runoff with retuned redraw probabilities.

Example (level 2):

```
question: Jade, Kate and Leo are candidates. 4 voters rank them Leo > Jade > Kate (best first). 8 voters rank them Leo > Jade > Kate (best first). 2 voters rank them Kate > Leo > Jade (best first). 2 voters rank them Jade > Leo > Kate (best first). 9 voters rank them Jade > Kate > Leo (best first). 8 voters rank them Kate > Jade > Leo (best first). The count goes in rounds: each round, every ballot counts for its best candidate still in the race; the candidate with the fewest ballots counting for them is out, and the next round starts. It continues until one candidate is left. Who is left?
structured: {"ballots": [[4, ["Leo", "Jade", "Kate"]], [8, ["Leo", "Jade", "Kate"]], [2, ["Kate", "Leo", "Jade"]], [2, ["Jade", "Leo", "Kate"]], [9, ["Jade", "Kate", "Leo"]], [8, ["Kate", "Jade", "Leo"]]], "candidates": ["Jade", "Kate", "Leo"]}
answer: Jade
```

### `R1.kinship_ancestor_r3` (family kinship, intended part ?)

kinship_ancestor_r2 with retuned redraw probabilities.

Example (level 2):

```
question: Nora's parent is Will. Stan's parent is Hank. Rhea is the parent of Leo. Pia is the parent of Emil. Hank's parent is Will. Rhea's parent is Will. Ugo's parent is Leo. Pia's parent is Ugo. Nobody else has a recorded parent. Who is the grandparent of Pia? Choose from Emil, Hank, Leo, Nora, Pia, Rhea, Stan, Ugo and Will.
structured: {"child": "Pia", "generations": 2, "parent": {"Emil": "Pia", "Hank": "Will", "Leo": "Rhea", "Nora": "Will", "Pia": "Ugo", "Rhea": "Will", "Stan": "Hank", "Ugo": "Leo"}, "people": ["Emil", "Hank", "Leo", "Nora", "Pia", "Rhea", "Stan", "Ugo", "Will"]}
answer: Leo
```

### `R1.kinship_descendants_r3` (family kinship, intended part ?)

kinship_descendants_r2 with retuned redraw probabilities (P['R1.kinship_descendants_r2']).

Example (level 2):

```
question: Stan is the parent of Anja. Stan is the parent of Gwen. Stan is the parent of Elsa. Orla is the parent of Lena. Anja is the parent of Tina. Tina is the parent of Orla. Nobody else has a recorded parent. Among the people who have a recorded parent, who has the most descendants (children, their children, and so on, all the way down)? Choose from Anja, Elsa, Gwen, Lena, Orla and Tina.
structured: {"ask": "descendants", "candidates": ["Anja", "Elsa", "Gwen", "Lena", "Orla", "Tina"], "parent": {"Anja": "Stan", "Elsa": "Stan", "Gwen": "Stan", "Lena": "Orla", "Orla": "Tina", "Tina": "Anja"}, "people": ["Stan", "Anja", "Tina", "Orla", "Elsa", "Lena", "Gwen"]}
answer: Anja
```

### `R1.minimax_tree` (family games, intended part ?)

structured: {"tree": nested list (a leaf is an integer payoff to the maximiser; an inner node is a list of its children), "first": "max"}. The maximiser chooses at the root and the two
players alternate by depth; both play perfectly. Answer: the payoff (a number).

Example (level 2):

```
question: Two players, Max and Min, play a game with 2 choices in a row, Max choosing first and then Min, and so on in turn. At each choice the mover picks one of the two options shown. The game is written as nested options: ((-2 or 9) or (-3 or 9)). When the options are all numbers, the number picked is the payoff. Max wants the payoff as large as possible and Min as small as possible, and both play perfectly. What is the payoff?
structured: {"first": "max", "tree": [[-2, 9], [-3, 9]]}
answer: -2
```

### `R1.mst_cost` (family network, intended part ?)

structured: {"towns": [name], "roads": [[a, b, length]]}. The roads connect all towns. Keep as few roads as possible so that every town can still be reached from every other,
choosing them to make the total length as small as possible. Answer: that smallest total length (a number).

Example (level 2):

```
question: A road between Arden and Fenwick could be built with length 4. A road between Ivybridge and Arden could be built with length 15. A road between Ivybridge and Zennor could be built with length 17. A road between Arden and Oakham could be built with length 11. A road between Oakham and Fenwick could be built with length 9. A road between Oakham and Zennor could be built with length 16. Some of these roads will be built so that every town can be reached from every other town, using as few roads as possible and the smallest possible total length. What is that total length?
structured: {"roads": [["Arden", "Fenwick", 4], ["Ivybridge", "Arden", 15], ["Ivybridge", "Zennor", 17], ["Arden", "Oakham", 11], ["Oakham", "Fenwick", 9], ["Oakham", "Zennor", 16]], "towns": ["Ivybridge", "Arden", "Oakham", "Fenwick", "Zennor"]}
answer: 44
```

### `R1.nim_xor` (family games, intended part ?)

structured: {"piles": [sizes]}. Two players alternate; on a turn a player removes at least one stone from ONE pile; whoever takes the last stone wins; the first player moves first.
Answer: "first" or "second" (the player who wins with perfect play).

Example (level 2):

```
question: A game has 3 piles of stones: 7, 22, 27. Two players take turns. On a turn, a player must remove at least one stone, all from a single pile (any number up to the whole pile). The player who takes the very last stone wins. Both play perfectly and the first player moves first. Who wins, the first player or the second player? Answer first or second.
structured: {"piles": [7, 22, 27]}
answer: first
```

### `R1.order_tournament_wins` (family order, intended part B)

structured: {"players": [name], "results": [[winner, loser]] (every pair of players exactly once), "ask": "most" | "fewest"}.
Answer: the player with the most (or fewest) wins; the extreme is unique in every item.

Example (level 2):

```
question: Cass, Eli, Finn, Milo and Xan played a round-robin: every pair of them played exactly one game and there were no draws. Eli beat Xan. Eli beat Cass. Milo beat Cass. Cass beat Xan. Xan beat Finn. Eli beat Milo. Finn beat Cass. Xan beat Milo. Finn beat Milo. Eli beat Finn. Who won the most games?
structured: {"ask": "most", "players": ["Xan", "Milo", "Cass", "Eli", "Finn"], "results": [["Eli", "Xan"], ["Eli", "Cass"], ["Milo", "Cass"], ["Cass", "Xan"], ["Xan", "Finn"], ["Eli", "Milo"], ["Finn", "Cass"], ["Xan", "Milo"], ["Finn", "Milo"], ["Eli", "Finn"]]}
answer: Eli
```

### `R1.spatial_grid_walk_r2` (family spatial, intended part ?)

Same as spatial_grid_walk, plus the column convention in the item ("column 1 is the westernmost"); the structured form gains
"convention": "row 1 is the northernmost, column 1 is the westernmost". (Audit: 113 of 140 keys changed under the other reading.)

Example (level 2):

```
question: A map has 3 rows (row 1 is the northernmost) and 4 columns (column 1 is the westernmost). Row 1: Timox, Nevar, Bakax, Kisik. Row 2: Robak, Rodak, Lidox, wall. Row 3: Karox, Tevik, Vabok, Sesox. You start at Nevar. You move north, then south, then north, then north, then east, then north, then north, then east, one cell each time. A move into a wall or off the map does nothing. Which place do you end on? Choose from Bakax, Karox, Kisik, Lidox, Nevar, Robak, Rodak, Sesox, Tevik, Timox and Vabok.
structured: {"convention": "row 1 is the northernmost, column 1 is the westernmost", "grid": [["Timox", "Nevar", "Bakax", "Kisik"], ["Robak", "Rodak", "Lidox", null], ["Karox", "Tevik", "Vabok", "Sesox"]], "moves": ["north", "south", "north", "north", "east", "north", "north", "east"], "start": [0, 1]}
answer: Kisik
```

### `R1.spatial_relative_directions` (family spatial, intended part A)

structured: {"places": [name], "facts": [[a, direction, k, b]] meaning a lies k blocks <direction> of b, "anchor": name}.
Streets form a grid. Answer: the place (other than the anchor) with the largest street distance (|d_ns| + |d_ew|) from the anchor.

Example (level 2):

```
question: Oakham is 1 block south of Selby. Dunmore is 1 block north of Oakham. Calder is 1 block west of Selby. Oakham is 8 blocks north of Brook. Which place is farthest from Calder by street distance (blocks north or south plus blocks east or west)? Choose from Brook, Dunmore, Oakham and Selby.
structured: {"anchor": "Calder", "facts": [["Oakham", "south", 1, "Selby"], ["Dunmore", "north", 1, "Oakham"], ["Calder", "west", 1, "Selby"], ["Oakham", "north", 8, "Brook"]], "places": ["Oakham", "Dunmore", "Selby", "Brook", "Calder"]}
answer: Brook
```

### `R1.stable_matching_r2` (family matching, intended part ?)

stable_matching with retuned redraw probabilities.

Example (level 2):

```
question: Some people ask others to partner with them. Ivo would like, from best to worst: Wade, Ada, Wren, Pablo. Lena would like, from best to worst: Pablo, Ada, Wade, Wren. Oscar would like, from best to worst: Pablo, Wade, Ada, Wren. Mona would like, from best to worst: Pablo, Wade, Wren, Ada. Wren would like, from best to worst: Oscar, Lena, Ivo, Mona. Pablo would like, from best to worst: Lena, Mona, Oscar, Ivo. Ada would like, from best to worst: Lena, Mona, Oscar, Ivo. Wade would like, from best to worst: Oscar, Ivo, Lena, Mona. Matching goes in turns: a person from Ivo, Lena, Mona and Oscar who has no partner asks the best person on their list that they have not asked yet. The person asked keeps the best proposer so far (by their own list) and says no to the others, who then ask the next person on their list. This goes on until everyone in Ivo, Lena, Mona and Oscar has a partner. Who is Oscar's partner at the end? Choose from Ada, Pablo, Wade and Wren.
structured: {"ask": "Oscar", "prefs_p": {"Ivo": ["Wade", "Ada", "Wren", "Pablo"], "Lena": ["Pablo", "Ada", "Wade", "Wren"], "Mona": ["Pablo", "Wade", "Wren", "Ada"], "Oscar": ["Pablo", "Wade", "Ada", "Wren"]}, "prefs_r": {"Ada": ["Lena", "Mona", "Oscar", "Ivo"], "Pablo": ["Lena", "Mona", "Oscar", "Ivo"], "Wade": ["Oscar", "Ivo", "Lena", "Mona"], "Wren": ["Oscar", "Lena", "Ivo", "Mona"]}, "proposers": ["Ivo", "Lena", "Oscar", "Mona"], "receivers": ["Wren", "Pablo", "Ada", "Wade"]}
answer: Wade
```

### `R1.temporal_critical_path` (family temporal, intended part A)

structured: {"jobs": [[person, days, [persons it waits for]]]}. A job with no wait starts on day 0, otherwise it starts the day
all its predecessors are finished and lasts its number of days. Answer: the person whose job finishes last (name).

Example (level 2):

```
question: Liam's job takes 9 days and starts as soon as the jobs of Ivo and Jana are all finished. Jana's job takes 1 day and starts on day 0. Flynn's job takes 4 days and starts on day 0. Ivo's job takes 13 days and starts as soon as the job of Jana is finished. Yves's job takes 1 day and starts on day 0. Whose job finishes last?
structured: {"jobs": [["Jana", 1, []], ["Ivo", 13, ["Jana"]], ["Yves", 1, []], ["Flynn", 4, []], ["Liam", 9, ["Ivo", "Jana"]]]}
answer: Liam
```

### `R1.temporal_interval_overlap` (family temporal, intended part A)

structured: {"events": [name], "spans": [["range", a, b] | ["dur", s, d]] (parallel to events; a range covers days a..b,
a duration covers days s..s+d-1), "x": name, "y": name}. Answer yes/no: do the two events share at least one day.

Example (level 2):

```
question: The music recital started on day 70 and went on for 15 days (day 70 counts as the first). The town parade ran from day 80 to day 83, both days included. The film night started on day 12 and went on for 11 days (day 12 counts as the first). The bridge opening ran from day 82 to day 90, both days included. Did the music recital and the bridge opening overlap, that is, was there at least one day on which both were going on? Answer yes or no.
structured: {"events": ["the music recital", "the town parade", "the film night", "the bridge opening"], "spans": [["dur", 70, 15], ["range", 80, 83], ["dur", 12, 11], ["range", 82, 90]], "x": "the music recital", "y": "the bridge opening"}
answer: yes
```

### `R1.temporal_weekday_shift` (family temporal, intended part A)

structured: {"days": [the seven weekday names in order], "anchor": [event, weekday], "links": [[later, earlier, n]] meaning
`later` took place n days after `earlier`, "ask": event}. Answer: the weekday on which `ask` took place (word).

Example (level 2):

```
question: The town parade took place on a Sunday. The council vote took place 113 days before the bridge opening. The town parade took place 205 days after the book sale. The town parade took place 222 days after the council vote. On which day of the week did the book sale take place?
structured: {"anchor": ["the town parade", "Sunday"], "ask": "the book sale", "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "links": [["the bridge opening", "the council vote", 113], ["the town parade", "the book sale", 205], ["the town parade", "the council vote", 222]]}
answer: Friday
```

### `R1.topological_order_r2` (family scheduling, intended part ?)

topological_order with retuned redraw probabilities.

Example (level 2):

```
question: There are 6 jobs and one job is done each day. Uma needs Ugo and Zane to be done first. Bea needs Opal to be done first. Zane needs Bea and Opal to be done first. Opal has no prerequisite. Nora needs Bea to be done first. Ugo needs Zane to be done first. Each day, among the jobs that can be done (all their prerequisites are already done), the job whose name comes first in alphabetical order is done. Which job is done on day 3? Choose from Bea, Nora, Opal, Ugo, Uma and Zane.
structured: {"day": 3, "jobs": [["Uma", ["Ugo", "Zane"]], ["Bea", ["Opal"]], ["Zane", ["Bea", "Opal"]], ["Opal", []], ["Nora", ["Bea"]], ["Ugo", ["Zane"]]]}
answer: Nora
```

### `R1.tracking_accounts` (family tracking, intended part B)

structured: {"start": {name: dollars}, "ops": [["pay", a, b, amount] | ["earn", a, amount] | ["half", a, b]], "ask": "most" | "least"}.
pay moves `amount` from a to b; earn adds to a; half moves half of a's money (always an even amount) from a to b. Nobody ever goes below zero.
Answer: the person with the most (or least) money at the end (unique).

Example (level 2):

```
question: At the start Leo has 30 dollars, Ines has 40 dollars, Walt has 80 dollars, Cara has 90 dollars. Walt earns 19 dollars. Walt pays Cara 33 dollars. Walt earns 38 dollars. Leo earns 29 dollars. Leo pays Cara 3 dollars. Ines pays Leo 1 dollar. Leo pays Ines 12 dollars. Walt pays Leo 24 dollars. Who has the most money at the end? Choose from Cara, Ines, Leo and Walt.
structured: {"ask": "most", "ops": [["earn", "Walt", 19], ["pay", "Walt", "Cara", 33], ["earn", "Walt", 38], ["earn", "Leo", 29], ["pay", "Leo", "Cara", 3], ["pay", "Ines", "Leo", 1], ["pay", "Leo", "Ines", 12], ["pay", "Walt", "Leo", 24]], "start": {"Cara": 90, "Ines": 40, "Leo": 30, "Walt": 80}}
answer: Cara
```

### `R1.venn_counting` (family sets, intended part ?)

structured: {"total": N, "groups": [names], "sizes": {group: size}, "pairs": {"a|b": size of the overlap}, "triple": size or null}. Every person is counted once. Answer: the number of people
in none of the groups (a number), by inclusion and exclusion.

Example (level 2):

```
question: Among 63 people, 35 people are in the diving group; 35 people are in the baking group; 34 people are in the chess group; 21 are in both the diving and the baking groups; 14 are in both the diving and the chess groups; 19 are in both the baking and the chess groups; 11 are in all three groups. Each person is counted once in each number that applies to them. How many of the people are in none of these groups?
structured: {"groups": ["diving", "baking", "chess"], "pairs": {"baking|chess": 19, "diving|baking": 21, "diving|chess": 14}, "sizes": {"baking": 35, "chess": 34, "diving": 35}, "total": 63, "triple": 11}
answer: 2
```
