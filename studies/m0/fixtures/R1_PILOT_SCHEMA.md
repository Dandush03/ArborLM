# R1 pilot lineages: structured-form schema for the second-solver agent

Written by the implementer for the separate second-solver context (ADR-0033 section 6.2, audit R6). Not a result; nothing here approves anything.

## Interface

- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.
- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`R1.<name>`); one module per family, `studies/m0/solvers_r1_<family>.py`.
- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).
- Fixtures: `studies/m0/fixtures/r1_pilot/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).
- The question text is in the fixture only so that an auditor can check the wording against the structured form; solvers must not parse it.

## Lineages (intended part, family, the builder's description of its structured form and answer rule)

### `R1.boolean_lights` (family boolean_state, intended part A)

structured: {"lamps": n, "initial": [0|1] (lamp 1..n), "switches": {colour: [lamp numbers it toggles]}, "presses": [colour], "ask": lamp number}.
Each press toggles every lamp its switch is wired to. Answer yes/no: is lamp `ask` on at the end.

Example (level 2):

```
question: There are 6 lamps numbered 1 to 6. At the start, lamps 1, 2, 3, 4 and 5 are on and the rest are off. The green switch toggles lamp 3 (each one goes from on to off or from off to on). The purple switch toggles lamp 5 (each one goes from on to off or from off to on). The blue switch toggles lamps 1, 3 and 4 (each one goes from on to off or from off to on). The switches are pressed in this order: blue, blue, blue, purple, purple, purple, blue. Is lamp 5 on at the end? Answer yes or no.
structured: {"ask": 5, "initial": [1, 1, 1, 1, 1, 0], "lamps": 6, "presses": ["blue", "blue", "blue", "purple", "purple", "purple", "blue"], "switches": {"blue": [1, 3, 4], "green": [3], "purple": [5]}}
answer: no
```

### `R1.categories_default_exceptions` (family categories, intended part B)

structured: {"chain": [group names, smallest first] (every member of chain[i] is a member of chain[i+1]), "rules": [[group, verb, true|false]],
"member": name (belongs to chain[0]), "verb": verb}. The rule of the smallest group that has a rule about the verb decides. Answer yes/no: can the member do it.

Example (level 2):

```
question: Every kozax is a metix. Every metix is a raman. Every raman is a vobox. A metix can float. A kozax can swim. A vobox cannot swim. When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. Kenji is a kozax. Can Kenji swim? Answer yes or no.
structured: {"chain": ["kozax", "metix", "raman", "vobox"], "member": "Kenji", "rules": [["metix", "float", true], ["kozax", "swim", true], ["vobox", "swim", false]], "verb": "swim"}
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

### `R1.conditional_threshold_rule` (family conditional, intended part B)

structured: {"members": [[name, weight]], "votes": {name: "yes"|"no"}, "need": T, "vetoes": [name]}. The motion passes when the total weight of
yes votes is at least T and no veto holder voted no. Answer yes/no: does it pass.

Example (level 2):

```
question: A committee votes on a motion. Bruno has weight 1, Ben has weight 2, Milo has weight 4, Vida has weight 4, Orla has weight 1, Yara has weight 3. The motion passes if the total weight of the members who vote yes is at least 8 (nobody has a veto). The votes: Bruno yes, Ben no, Milo no, Vida yes, Orla no, Yara yes. Does the motion pass? Answer yes or no.
structured: {"members": [["Bruno", 1], ["Ben", 2], ["Milo", 4], ["Vida", 4], ["Orla", 1], ["Yara", 3]], "need": 8, "vetoes": [], "votes": {"Ben": "no", "Bruno": "yes", "Milo": "no", "Orla": "no", "Vida": "yes", "Yara": "yes"}}
answer: yes
```

### `R1.containers_queue_line` (family containers, intended part A)

structured: {"line": [front..back], "ops": [["join", name] (to the back) | ["cut", name] (to the front) | ["serve"] (front leaves) |
["leave", name] (that person leaves)], "ask": "front" | "back"}. Answer: who is at the asked end at the end.

Example (level 2):

```
question: A line, from front to back, is: Cyrus, Uzi and Zoe. Uzi gets tired and leaves. Carla joins at the back. Zita is let in at the very front. Zoe gets tired and leaves. Lila is let in at the very front. Zita gets tired and leaves. Finn joins at the back. Who is at the front of the line at the end? Choose from Carla, Cyrus, Finn, Lila, Uzi, Zita and Zoe.
structured: {"ask": "front", "line": ["Cyrus", "Uzi", "Zoe"], "ops": [["leave", "Uzi"], ["join", "Carla"], ["cut", "Zita"], ["leave", "Zoe"], ["cut", "Lila"], ["leave", "Zita"], ["join", "Finn"]]}
answer: Lila
```

### `R1.containers_stack_piles` (family containers, intended part A)

structured: {"piles": [name], "initial": {pile: [block bottom..top]}, "ops": [["move", from, to] | ["reverse", pile]], "ask": pile}.
move puts the top block of `from` on top of `to`; reverse turns a pile upside down. Answer: the block on top of `ask` at the end.

Example (level 2):

```
question: There are three piles of blocks. The orange pile holds, from bottom to top: needle, compass and ribbon. The yellow pile holds, from bottom to top: umbrella, feather and globe. The black pile holds, from bottom to top: nothing. Move the top block of the orange pile onto the black pile. Move the top block of the yellow pile onto the orange pile. Move the top block of the orange pile onto the black pile. Move the top block of the black pile onto the orange pile. Move the top block of the yellow pile onto the black pile. Move the top block of the orange pile onto the black pile. Move the top block of the black pile onto the yellow pile. Which block is on top of the orange pile at the end? Choose from compass, feather, globe, needle, ribbon and umbrella.
structured: {"ask": "the orange pile", "initial": {"the black pile": [], "the orange pile": ["needle", "compass", "ribbon"], "the yellow pile": ["umbrella", "feather", "globe"]}, "ops": [["move", "the orange pile", "the black pile"], ["move", "the yellow pile", "the orange pile"], ["move", "the orange pile", "the black pile"], ["move", "the black pile", "the orange pile"], ["move", "the yellow pile", "the black pile"], ["move", "the orange pile", "the black pile"], ["move", "the black pile", "the yellow pile"]], "piles": ["the orange pile", "the yellow pile", "the black pile"]}
answer: compass
```

### `R1.elimination_bracket` (family elimination, intended part A)

structured: {"players": [[name, rating]] in bracket order, "ask": ["runner_up"] | ["beaten_by", name]}. Adjacent players meet in round
one, the higher rating always wins, winners keep their order and are paired adjacent again. Answer: the loser of the final, or the
player who knocked the named player out.

Example (level 2):

```
question: A knockout tournament has 4 players listed in bracket order: Wade (rating 40), Sam (rating 15), Milo (rating 53), Neva (rating 46). In round one the first two listed play each other, the next two play each other, and so on. The player with the higher rating always wins. The winners keep their order and are paired the same way in the next round, until one player is left. Who knocks Neva out?
structured: {"ask": ["beaten_by", "Neva"], "players": [["Wade", 40], ["Sam", 15], ["Milo", 53], ["Neva", 46]]}
answer: Milo
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

### `R1.equivalence_classes` (family equivalence, intended part B)

structured: {"items": [name], "same": [[a, b]], "different": [[a, b]], "x": name, "y": name}. Answer: yes if x and y are forced to be the
same thing (a chain of `same`), no if they are forced to be different (their groups have a `different` statement between them),
otherwise cannot be determined.

Example (level 2):

```
question: kodar is the same thing as bamix. dakor is the same thing as kodar. dakor is the same thing as bamix. vinar is a different thing from kodar. vinar is a different thing from bamix. Is bamix the same thing as vinar? Answer yes (they must be the same), no (they must be different) or cannot be determined.
structured: {"different": [["vinar", "bamix"], ["vinar", "kodar"]], "items": ["bamix", "tanax", "nodin", "vinar", "danar", "dakor", "kodar"], "same": [["kodar", "bamix"], ["dakor", "bamix"], ["dakor", "kodar"]], "x": "bamix", "y": "vinar"}
answer: no
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

### `R1.graph_shortest_route` (family graph, intended part B)

structured: {"towns": [name], "roads": [[a, b, length]] (two-way), "start": name, "end": name}. The shortest route from start to end is
unique and has at least two roads. Answer: the town reached first after leaving `start` on that route.

Example (level 2):

```
question: There is a two-way road between Selby and Thornbury of length 1. There is a two-way road between Garth and Selby of length 3. There is a two-way road between Arden and Thornbury of length 4. There is a two-way road between Brook and Garth of length 1. There is a two-way road between Brook and Thornbury of length 5. There is a two-way road between Brook and Selby of length 1. There is a two-way road between Brook and Arden of length 4. There is a two-way road between Brook and Marlow of length 5. There is a two-way road between Arden and Marlow of length 2. You drive from Thornbury to Marlow along the route with the smallest total length. Which town do you reach first after leaving Thornbury? Choose from Arden, Brook, Garth, Marlow and Selby.
structured: {"end": "Marlow", "roads": [["Selby", "Thornbury", 1], ["Garth", "Selby", 3], ["Arden", "Thornbury", 4], ["Brook", "Garth", 1], ["Brook", "Thornbury", 5], ["Brook", "Selby", 1], ["Brook", "Arden", 4], ["Brook", "Marlow", 5], ["Arden", "Marlow", 2]], "start": "Thornbury", "towns": ["Brook", "Garth", "Arden", "Selby", "Marlow", "Thornbury"]}
answer: Arden
```

### `R1.kinship_descendants` (family kinship, intended part B)

structured: {"people": [name], "parent": {child: parent}, "ask": "grandchildren" | "descendants"}. Every listed child has exactly one recorded
parent; one person (the root) has none. Answer: the person with the most grandchildren (or the most descendants of any depth); unique.

Example (level 2):

```
question: Otto is the parent of Nico. Cara is the parent of Liam. Otto is the parent of Kate. Cara is the parent of Otto. Nico is the parent of Walt. Nico is the parent of Xena. Nobody else has a recorded parent. Who has the most descendants (children, their children, and so on, all the way down)? Choose from Cara, Kate, Liam, Nico, Otto, Walt and Xena.
structured: {"ask": "descendants", "parent": {"Kate": "Otto", "Liam": "Cara", "Nico": "Otto", "Otto": "Cara", "Walt": "Nico", "Xena": "Nico"}, "people": ["Cara", "Otto", "Nico", "Kate", "Xena", "Walt", "Liam"]}
answer: Cara
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

### `R1.spatial_grid_walk` (family spatial, intended part A)

structured: {"grid": [[name | null]] rows top to bottom (null = wall), "start": [row, col] (0-based), "moves": [direction]}.
north is towards row 0. A move into a wall or off the grid leaves you where you are. Answer: the name of the cell you end on.

Example (level 2):

```
question: A map has 3 rows (row 1 is the northernmost) and 4 columns. Row 1: Minox, Motor, Vokon, Zisox. Row 2: Todon, Bivak, Zelik, Totak. Row 3: Sisok, Vazar, Zokex, wall. You start at Todon. You move north, then east, then west, then south, then south, then east, then north, then west, one cell each time. A move into a wall or off the map does nothing. Which place do you end on? Choose from Bivak, Minox, Motor, Sisok, Todon, Totak, Vazar, Vokon, Zelik, Zisox and Zokex.
structured: {"grid": [["Minox", "Motor", "Vokon", "Zisox"], ["Todon", "Bivak", "Zelik", "Totak"], ["Sisok", "Vazar", "Zokex", null]], "moves": ["north", "east", "west", "south", "south", "east", "north", "west"], "start": [1, 0]}
answer: Todon
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
