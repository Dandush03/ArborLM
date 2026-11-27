# R1 fix-round-3 shapes: structured-form schema for the second-solver agent

Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything. No second solver exists for these shapes; nothing is registered in core.REGISTRY (ruling R-9).

## Interface

- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.
- Registry: `SOLVERS: dict[str, Callable]` keyed by shape id (`R1.<name>_r5`); one module per family, `studies/m0/solvers_r1_<family>.py`.
- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).
- Fixtures: `studies/m0/fixtures/r1_fix3/<shape id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).
- The question text is in the fixture only so that an auditor can check the wording against the structured form; solvers must not parse it.

## Shapes (family, the builder's description of its structured form and answer rule). No part is assigned (see manifests/r1_fix3_parts.md).

### `R1.activity_selection_r5` (family scheduling, intended part ?)

structured: {"meetings": [[name, start, end]], "zones": [kind]}. Largest number of meetings one person can attend (open number); a meeting that ends at minute t and one that starts at minute t do not overlap.
The day is a row of zones, none of which touches the next. Zones: A, two long meetings that touch and a short one across the join (shortest first loses one); B, one long early meeting over 2 to 6 short ones (earliest
start gets one); C, one meeting; D, three meetings with random overlaps; E, a clique of 2 to 6 meetings that share a minute (contributes 1, adds 2 to 6 meetings); F, 1 to 10 separate meetings (contributes that many).
E and F make the answer independent of the number of meetings (the earlier shape: "two thirds of the meetings" scored +0.46 at level 0). Every item has two A and two B zones, the rest are drawn from A, A, A, B, B, B, D, E, F (the trap zones make a greedy pass in the listed order wrong most of the time).

Example (level 2):

```
question: Iris's meeting runs from minute 21 to minute 42. Nico's meeting runs from minute 67 to minute 71. Emil's meeting runs from minute 77 to minute 80. Hank's meeting runs from minute 49 to minute 53. Dion's meeting runs from minute 84 to minute 87. Xavi's meeting runs from minute 97 to minute 106. Sean's meeting runs from minute 45 to minute 52. Esme's meeting runs from minute 81 to minute 83. Elsa's meeting runs from minute 7 to minute 11. Anja's meeting runs from minute 22 to minute 26. Alma's meeting runs from minute 75 to minute 88. Walt's meeting runs from minute 13 to minute 16. Fay's meeting runs from minute 60 to minute 69. Vance's meeting runs from minute 69 to minute 74. Zane's meeting runs from minute 125 to minute 129. Ugo's meeting runs from minute 109 to minute 115. Raul's meeting runs from minute 129 to minute 135. Rosa's meeting runs from minute 136 to minute 142. Lars's meeting runs from minute 147 to minute 149. Rhea's meeting runs from minute 36 to minute 39. Hana's meeting runs from minute 3 to minute 6. Dmitri's meeting runs from minute 89 to minute 97. Ada's meeting runs from minute 31 to minute 35. Ivo's meeting runs from minute 117 to minute 119. Kai's meeting runs from minute 119 to minute 125. Vera's meeting runs from minute 52 to minute 57. Leo's meeting runs from minute 27 to minute 31. Bram's meeting runs from minute 95 to minute 99. Yves's meeting runs from minute 0 to minute 18. Sia's meeting runs from minute 144 to minute 146. A meeting that ends at minute t and one that starts at minute t do not overlap. What is the largest number of these meetings that one person could attend?
structured: {"meetings": [["Iris", 21, 42], ["Nico", 67, 71], ["Emil", 77, 80], ["Hank", 49, 53], ["Dion", 84, 87], ["Xavi", 97, 106], ["Sean", 45, 52], ["Esme", 81, 83], ["Elsa", 7, 11], ["Anja", 22, 26], ["Alma", 75, 88], ["Walt", 13, 16], ["Fay", 60, 69], ["Vance", 69, 74], ["Zane", 125, 129], ["Ugo", 109, 115], ["Raul", 129, 135], ["Rosa", 136, 142], ["Lars", 147, 149], ["Rhea", 36, 39], ["Hana", 3, 6], ["Dmitri", 89, 97], ["Ada", 31, 35], ["Ivo", 117, 119], ["Kai", 119, 125], ["Vera", 52, 57], ["Leo", 27, 31], ["Bram", 95, 99], ["Yves", 0, 18], ["Sia", 144, 146]], "zones": ["B", "B", "A", "A", "B", "A", "F"]}
answer: 24
```

### `R1.attribute_rule_r5` (family rules, intended part ?)

structured: {"rule", "owners", "items"} as attribute_rule. The rule is built as before but two deeper (depth 3 + level // 2: a rule of two tests is decided by counting them, so no k separates the satisfying badge), leaves 'colour/shape/mark is v', and, or, not). The number k of the rule's tests that a badge matches is drawn
FIRST (uniformly among 1 .. leaves - 1 for which at least one badge that satisfies the rule and at least n - 1 that do not exist); the satisfying badge is drawn uniformly among the badges that match exactly k tests and
satisfy the rule, and each of the other n - 1 uniformly among the distinct badges that match exactly k tests and do not. So every badge matches the same number of tests: "the badge that matches most tests" and its
variants are uninformative by construction. Nothing is redrawn on a heuristic.

Example (level 2):

```
question: A gate opens for a badge if the badge satisfies this rule: (it has a dot or (it is not true that it has a star and (it is oval or it has a cross))) or it is blue. The badges: Kai's badge is yellow, oval and has a cross; Opal's badge is red, oval and has a star; Emil's badge is orange, oval and has a star; Ivy's badge is green, oval and has a star; Xan's badge is black, oval and has a star; Ugo's badge is white, oval and has a star. Whose badge opens the gate? Choose from Emil, Ivy, Kai, Opal, Ugo and Xan.
structured: {"items": [{"colour": "yellow", "mark": "a cross", "shape": "oval"}, {"colour": "red", "mark": "a star", "shape": "oval"}, {"colour": "orange", "mark": "a star", "shape": "oval"}, {"colour": "green", "mark": "a star", "shape": "oval"}, {"colour": "black", "mark": "a star", "shape": "oval"}, {"colour": "white", "mark": "a star", "shape": "oval"}], "owners": ["Kai", "Opal", "Emil", "Ivy", "Xan", "Ugo"], "rule": ["or", ["or", ["attr", "mark", "a dot"], ["and", ["not", ["attr", "mark", "a star"]], ["or", ["attr", "shape", "oval"], ["attr", "mark", "a cross"]]]], ["attr", "colour", "blue"]]}
answer: Kai
```

### `R1.categories_follow_r5` (family categories, intended part ?)

structured: {"cats", "all", "none", "some", "kind", "x", "y", "answer_convention"} as categories_follow_r4 (indices into "cats"; the same convention sentence and the same complete entailment). The kind of statement and the
class are drawn first (each uniform, independent) and the premises are planted around the asked pair: all-yes: a chain of 2 .. 2 + level "All" steps from x to y; all-no, none-yes, some-no: x and y each lie below one end of
a "No a are b" premise (1 .. 1 + level // 2 "All" steps on each side); none-no, some-yes: x and y have a common member group below both, or lie above the two ends of a "Some a are b" premise; cannot be determined: x and y
lie in separate chains and a "No" premise ties one chain to a third group. 3 + level // 2 decoy groups hang below random groups with one "All" and carry a random "No" or "Some" to another group. The planting is repeated (up to
300 times, the class and kind kept) until the closure of the earlier shape derives the drawn class with no inconsistency (validity); the asked statement is never stated verbatim. Every yes and no therefore
needs a "No" or "Some" lifted through at least one "All" (or a chain of two), which a reading without lifting cannot do (the earlier shape: +0.38 to +0.45).

Example (level 2):

```
question: All tosir are sodox. Some movir are sodox. No nedar are nozak. All zobex are teven. Some tosir are nedar. All teven are nozak. All teven are sodox. All movir are zobex. All nedar are lovan. All sodox are lovan. Some zobex are teven. Every group named here has at least one member. "Some X are Y" means that at least one thing is both an X and a Y; "No X are Y" means that nothing is both. Consider the statement: "no lovan is a nozak". Answer yes if the statement must be true, no if the statement must be false, or cannot be determined if the statements above leave it open (it could be true and it could be false).
structured: {"all": [[0, 1], [1, 2], [0, 3], [4, 0], [5, 2], [6, 1], [7, 4]], "answer_convention": "yes = must be true; no = must be false; cannot be determined = could be either; every named group is non-empty", "cats": ["teven", "sodox", "lovan", "nozak", "zobex", "nedar", "tosir", "movir"], "kind": "none", "none": [[5, 3]], "some": [[4, 0], [6, 5], [7, 1]], "x": 2, "y": 3}
answer: no
```

### `R1.conditional_chain_r5` (family conditional, intended part ?)

structured: {"vars", "facts": [[v, bool]], "rules": [[[[v, bool]], [v, bool]]], "query"} as conditional_chain. The answer class (yes / no / cannot be determined) is drawn FIRST, uniformly. The asked variable q is never a stated
fact (the earlier shape stated it in 37 to 49 % of the items). yes / no: a chain of d = 2 + level // 3 rules leads from a stated fact to q (the antecedent of a rule is the previous variable, with a second, true,
stated fact in half of the rules); a decoy chain of the same length is added to every other item class too. Every item has exactly two rules that conclude q: yes / no: the last rule of the chain and one trap rule of the
opposite sign whose antecedent is a literal that is false in the hidden world; cannot be determined: two trap rules of opposite signs. The remaining rules (n + level in all) are sound random rules (a rule whose antecedent
holds in the hidden world has a conclusion that holds there; none concludes q). The class is then checked by enumerating every assignment (a Retry only when the checked class differs from the drawn one: a validity rule).

Example (level 2):

```
question: If D is false, then G is true. If G is true, then I is false. If D is true, then C is true. If H is false, then H is false. If I is true, then G is false. If H is true and A is true, then D is false. If G is true and A is false, then G is true. If I is true, then G is true. B is true. If F is true and G is false, then E is false. If H is false and A is true, then C is false. E is true. A is true. If B is true, then H is false. Is C true? Answer yes, no or cannot be determined.
structured: {"facts": [["B", true], ["E", true], ["A", true]], "query": "C", "rules": [[[["B", true]], ["H", false]], [[["H", false], ["A", true]], ["C", false]], [[["D", true]], ["C", true]], [[["H", true], ["A", true]], ["D", false]], [[["G", true], ["A", false]], ["G", true]], [[["I", true]], ["G", true]], [[["G", true]], ["I", false]], [[["D", false]], ["G", true]], [[["H", false]], ["H", false]], [[["I", true]], ["G", false]], [[["F", true], ["G", false]], ["E", false]]], "vars": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}
answer: no
```

### `R1.containers_queue_line_r5` (family containers, intended part ?)

structured: {"line": [front..back], "ops": [["join", n] | ["cut", n] | ["serve"] | ["leave", n] | ["front_to_back"]], "ask": ["position", j]} as containers_queue_line_r2. The asked position j (2, 3 or 4) is drawn
first. 8 + 2 * level operations: one of each kind, in random places, and the rest drawn with the weights of the earlier shape except that 'cut' counts twice; a person who leaves is drawn among the people in positions 2 to j of the line at that moment, and the line never has fewer than j + 2 people, so
every serve, cut, leave and front-to-back move shifts the person in position j, and ignoring any one kind of operation changes who stands there (the earlier shape: ignoring 'leave' scored +0.22 to +0.48).
The line starts with 9 + level // 2 people.

Example (level 2):

```
question: A line, from front to back, is: Xavi, Pru, Omar, Mona, Fern, Wren, Gita, Bea, Reed and Zoe. Omar gets tired and leaves. The person at the front is served and leaves. Igor is let in at the very front. The person at the front goes to the back of the line. Greta is let in at the very front. Eli is let in at the very front. The person at the front goes to the back of the line. Ivy joins at the back. Fern gets tired and leaves. The person at the front goes to the back of the line. Rex joins at the back. Maya is let in at the very front. Who is in position 4 from the front of the line at the end (position 1 is the very front)? Choose from Bea, Eli, Fern, Gita, Greta, Igor, Ivy, Maya, Mona, Omar, Pru, Reed, Rex, Wren, Xavi and Zoe.
structured: {"ask": ["position", 4], "line": ["Xavi", "Pru", "Omar", "Mona", "Fern", "Wren", "Gita", "Bea", "Reed", "Zoe"], "ops": [["leave", "Omar"], ["serve"], ["cut", "Igor"], ["front_to_back"], ["cut", "Greta"], ["cut", "Eli"], ["front_to_back"], ["join", "Ivy"], ["leave", "Fern"], ["front_to_back"], ["join", "Rex"], ["cut", "Maya"]]}
answer: Wren
```

### `R1.elimination_bracket_r5` (family elimination, intended part ?)

structured: {"players": [bracket order], "results": [[winner, loser]], "ask": ["champion"] | ["runner_up"]} as elimination_bracket_r4 (the same near-regular tournament, bracket and wording), restricted to the question kinds whose
shortcut readings were small in the third audit: 'who wins' and 'who loses the final', never 'who knocks X out' (the other-quarter beater scored +0.36 at level 5). 8 players for levels 0 to 2 and 16 for levels 3 to 6; the question
kind by level: champion, runner-up, either, champion, runner-up, either, either. The one reading left is 'the best record inside each half' (+0.08 to +0.17 in the earlier shape at these levels).

Example (level 2):

```
question: A knockout tournament has 8 players listed in bracket order: Sven, Vic, Ivo, Pia, Ben, Pru, Cara, Uri. In round one the first two listed play each other, the next two play each other, and so on. Whenever two players meet in the tournament, the winner is whoever won their earlier game against each other: Ivo beat Pru. Vic beat Pia. Cara beat Sven. Sven beat Uri. Pru beat Uri. Vic beat Uri. Pia beat Ben. Ben beat Vic. Uri beat Ben. Sven beat Vic. Uri beat Ivo. Pru beat Sven. Pia beat Pru. Vic beat Ivo. Ivo beat Cara. Uri beat Pia. Pia beat Cara. Sven beat Ivo. Vic beat Cara. Ivo beat Pia. Pru beat Vic. Pia beat Sven. Ben beat Ivo. Cara beat Uri. Sven beat Ben. Cara beat Ben. Cara beat Pru. Ben beat Pru. The winners keep their order and are paired the same way in the next round, until one player is left. Who wins the tournament? Choose from Ben, Cara, Ivo, Pia, Pru, Sven, Uri and Vic.
structured: {"ask": ["champion"], "players": ["Sven", "Vic", "Ivo", "Pia", "Ben", "Pru", "Cara", "Uri"], "results": [["Ivo", "Pru"], ["Vic", "Pia"], ["Cara", "Sven"], ["Sven", "Uri"], ["Pru", "Uri"], ["Vic", "Uri"], ["Pia", "Ben"], ["Ben", "Vic"], ["Uri", "Ben"], ["Sven", "Vic"], ["Uri", "Ivo"], ["Pru", "Sven"], ["Pia", "Pru"], ["Vic", "Ivo"], ["Ivo", "Cara"], ["Uri", "Pia"], ["Pia", "Cara"], ["Sven", "Ivo"], ["Vic", "Cara"], ["Ivo", "Pia"], ["Pru", "Vic"], ["Pia", "Sven"], ["Ben", "Ivo"], ["Cara", "Uri"], ["Sven", "Ben"], ["Cara", "Ben"], ["Cara", "Pru"], ["Ben", "Pru"]]}
answer: Cara
```

### `R1.equivalence_classes_r5` (family kinship, intended part ?)

structured: {"items", "same": [[a, b]], "different": [[a, b]], "x", "y"} as equivalence_classes. The answer class is drawn first. A planted chain of d "same" links (d uniform in 2 + level .. 7 + level) joins x and y (yes);
for no, the chain is cut in the middle by one "different" link (d links in all); for cannot be determined x and y lie in two separate chains of about d / 2 links. Decoy items (6 + level of them) form separate small groups that
are tied to the chains by "different" links (never between the groups of x and y unless the answer is no) and by "same" links within themselves. The asked pair is never stated and a common same-neighbour exists only by chance
(the earlier shape: common neighbour scored +0.29).

Example (level 2):

```
question: vitik is the same thing as zodok. zodok is the same thing as dedax. soran is the same thing as later. vodik is a different thing from vitik. kavar is the same thing as lizek. tikan is the same thing as tilon. volin is a different thing from vodik. lizek is the same thing as dosix. volin is the same thing as tikan. bevin is the same thing as soran. tilon is a different thing from vosir. tilon is the same thing as kaner. vosir is the same thing as vitik. Is vosir the same thing as later? Answer yes (they must be the same), no (they must be different) or cannot be determined.
structured: {"different": [["vodik", "vitik"], ["volin", "vodik"], ["tilon", "vosir"]], "items": ["kaner", "dedax", "soran", "vitik", "tikan", "later", "bevin", "vodik", "vosir", "zodok", "lizek", "volin", "tilon", "kavar", "dosix"], "same": [["vosir", "vitik"], ["vitik", "zodok"], ["zodok", "dedax"], ["bevin", "soran"], ["soran", "later"], ["volin", "tikan"], ["tikan", "tilon"], ["tilon", "kaner"], ["kavar", "lizek"], ["lizek", "dosix"]], "x": "vosir", "y": "later"}
answer: cannot be determined
```

### `R1.equivalence_exchange_rates_r5` (family equivalence, intended part ?)

structured: {"items", "rates": [[p, a, q, b]] (p units of a are worth q units of b), "x", "y", "n"}. Question: how many units of Y are worth the same as N units of X (an open whole number). Values are drawn
from the numbers 2 .. 399 whose only prime factors are 2, 3 and 5 (distinct), the rates are the reduced ratios of neighbours (times 1 or 2), and X and Y are the ends of a spine of L = 3 + level // 2 rates;
N is a multiple of v_Y / gcd(v_X, v_Y) chosen so that the answer is a whole number. 2 + level // 3 further items hang from random items. (The earlier shape asked which item is worth the most per unit; the local
maximum rule was right 20 to 49 % of the time.)

Example (level 2):

```
question: 9 units of compass are worth the same as 16 units of apple. 512 units of pencil are worth the same as 50 units of feather. 18 units of feather are worth the same as 32 units of compass. 243 units of book are worth the same as 128 units of drum. 12 units of pencil are worth the same as 1 units of orange. 8 units of compass are worth the same as 9 units of book. How many units of drum are worth the same as 729 units of pencil?
structured: {"items": ["pencil", "feather", "compass", "book", "drum", "orange", "apple"], "n": 729, "rates": [[9, "compass", 16, "apple"], [512, "pencil", 50, "feather"], [18, "feather", 32, "compass"], [243, "book", 128, "drum"], [12, "pencil", 1, "orange"], [8, "compass", 9, "book"]], "x": "pencil", "y": "drum"}
answer: 75
```

### `R1.event_timeline_r5` (family temporal, intended part ?)

structured: {"events", "rel": [[later, earlier, days]], "x", "y"}. Question: how many days apart did X and Y take place (an open number >= 1). The facts are "A took place d days after B" / "B took place d days
before A", d uniform in 1 .. 60. The spine between X and Y has L = 4 + level // 2 statements and the sign of every one is random; 2 + level // 3 further events hang from random events. (The earlier shape asked which event came first or
last; the event at the far end of the largest stated gap was right 40 to 48 % of the time.) The days are consecutive numbers, X and Y are on different days (the sum is not zero; otherwise Retry).

Example (level 2):

```
question: The bake-off took place 37 days before the harvest fair. The concert took place 33 days after the music recital. The harvest fair took place 60 days after the quiz night. The bake-off took place 48 days before the music recital. The concert took place 48 days after the film night. The town parade took place 22 days before the film night. The boat race took place 47 days after the music recital. How many days apart did the film night and the quiz night take place?
structured: {"events": ["the bake-off", "the boat race", "the concert", "the film night", "the harvest fair", "the music recital", "the quiz night", "the town parade"], "rel": [["the harvest fair", "the bake-off", 37], ["the concert", "the music recital", 33], ["the harvest fair", "the quiz night", 60], ["the music recital", "the bake-off", 48], ["the concert", "the film night", 48], ["the film night", "the town parade", 22], ["the boat race", "the music recital", 47]], "x": "the film night", "y": "the quiz night"}
answer: 56
```

### `R1.graph_bipartite_r5` (family graph, intended part ?)

structured: {"people": [name], "rivals": [[a, b]]} as graph_bipartite. n = 13 + level people (the earlier 4 + level people allowed at most 11 / 34 / 156 / 1,044 / 12,346 different graphs at levels 0 to 4, far below the
capacity the generator must have). A connected bipartite graph is built (a random spanning tree that attaches each person to one of the last three earlier people on the other side, so paths are long; then 2 + level // 2 + (0 to 2)
more edges across the two sides). yes: one more edge across the sides. no: one edge inside a side, between two people at distance 4 or more (so the shortest odd cycle has 5 or more people: NO item has a triangle; the earlier
rule 'a triangle means no' scored +0.40 to +0.50). The two classes have the same number of rivalries. The answer is drawn first; the graph is then checked two-colourable (yes) or not (no) as validity.

Example (level 2):

```
question: Ben, Bruno, Cara, Dara, Dell, Eli, Emil, Gita, Gwen, Kira, Liam, Pete, Pru, Stan and Xena must be split into two teams. Gwen and Pru are rivals. Emil and Eli are rivals. Cara and Dara are rivals. Cara and Gwen are rivals. Ben and Dara are rivals. Bruno and Liam are rivals. Dell and Pete are rivals. Ben and Eli are rivals. Eli and Bruno are rivals. Pete and Gita are rivals. Liam and Ben are rivals. Stan and Pru are rivals. Kira and Emil are rivals. Emil and Stan are rivals. Pete and Xena are rivals. Dell and Eli are rivals. Dell and Gwen are rivals. Xena and Eli are rivals. Bruno and Pete are rivals. Kira and Gita are rivals. Can they be split into two teams (either team may be any size) so that no two rivals are on the same team? Answer yes or no.
structured: {"people": ["Pete", "Dell", "Bruno", "Liam", "Gita", "Kira", "Eli", "Gwen", "Xena", "Cara", "Emil", "Ben", "Dara", "Stan", "Pru"], "rivals": [["Gwen", "Pru"], ["Emil", "Eli"], ["Cara", "Dara"], ["Cara", "Gwen"], ["Ben", "Dara"], ["Bruno", "Liam"], ["Dell", "Pete"], ["Ben", "Eli"], ["Eli", "Bruno"], ["Pete", "Gita"], ["Liam", "Ben"], ["Stan", "Pru"], ["Kira", "Emil"], ["Emil", "Stan"], ["Pete", "Xena"], ["Dell", "Eli"], ["Dell", "Gwen"], ["Xena", "Eli"], ["Bruno", "Pete"], ["Kira", "Gita"]]}
answer: yes
```

### `R1.kinship_cousins_r5` (family kinship, intended part ?)

structured: {"parent": {child: parent}, "x", "y"} as kinship_cousins. One family: a root with 4 + level // 3 children, the first with 2 to 4 children and the others with 1 to 4, each of those with 0 to 3 children (up to four generations).
"Two people are cousins if their parents are different people who have the same parent." The pair type is drawn first, uniformly: cousins (answer yes); siblings (same parent; they share a grandparent, so "share a grandparent" is
wrong); another relation in which the parents differ and no grandparent is shared (second cousins, a person and their cousin's child, or an uncle and a nephew). So "same family" is always yes and the two clauses of the
definition each leave a third of the items on the wrong side (+0.17 at best for any one clause alone; the earlier shape's same-family rule scored +0.41 to +0.45).

Example (level 2):

```
question: Bram is the parent of Igor. Sia is the parent of Dion. Uri is the parent of Marc. Fern is the parent of Gus. Hope is the parent of Eli. Gita is the parent of Sia. Kurt is the parent of Mona. Tara is the parent of Gita. Gita is the parent of Uri. Gita is the parent of Fern. Tara is the parent of Bram. Finn is the parent of Opal. Fern is the parent of Dev. Eli is the parent of Pia. Bram is the parent of Raul. Mona is the parent of Omar. Mona is the parent of Cyrus. Eli is the parent of Dmitri. Eli is the parent of Elsa. Finn is the parent of Gwen. Hope is the parent of Otto. Tara is the parent of Hope. Gita is the parent of Finn. Tara is the parent of Kurt. Nobody else has a recorded parent. Two people are cousins if their parents are different people who have the same parent. Are Omar and Finn cousins? Answer yes or no.
structured: {"parent": {"Bram": "Tara", "Cyrus": "Mona", "Dev": "Fern", "Dion": "Sia", "Dmitri": "Eli", "Eli": "Hope", "Elsa": "Eli", "Fern": "Gita", "Finn": "Gita", "Gita": "Tara", "Gus": "Fern", "Gwen": "Finn", "Hope": "Tara", "Igor": "Bram", "Kurt": "Tara", "Marc": "Uri", "Mona": "Kurt", "Omar": "Mona", "Opal": "Finn", "Otto": "Hope", "Pia": "Eli", "Raul": "Bram", "Sia": "Gita", "Uri": "Gita"}, "x": "Omar", "y": "Finn"}
answer: no
```

### `R1.kinship_descendants_r5` (family kinship, intended part ?)

structured: {"people", "parent", "ask": "descendants", "candidates", "root"} as kinship_descendants_r4. Each candidate's number of descendants S_i is drawn (distinct, at least 8); the candidate has 1 to 3 children and 1 to 3
grandchildren (independent of S_i); the height H_i (generations below the candidate, 3 to 5) is drawn independently of S_i, a line of H_i - 2 people hangs below one grandchild and the remaining
S_i - children - grandchildren - (H_i - 2) descendants hang from random people at depth 2 or more but less than H_i (never from the candidate's children). So the number of children, grandchildren, the depth of the
line below and the number of times a candidate is named are all independent of S_i (the earlier shape: the candidate with the deepest line scored +0.42 to +0.67).

Example (level 2):

```
question: Sean is the parent of Rex. Jade is the parent of Kurt. Quinn is the parent of Opal. Yves is the parent of Tom. Ugo is the parent of Tara. Alva is the parent of Uzi. Kurt is the parent of Lars. Kurt is the parent of Rhea. Tess is the parent of Abel. Eli is the parent of Edna. Cleo is the parent of Flynn. Rex is the parent of Jon. Rex is the parent of Emil. Gus is the parent of Milo. Rex is the parent of Nora. Bea is the parent of Gus. Edna is the parent of Sia. Pete is the parent of Cleo. Carla is the parent of Yves. Quinn is the parent of Ada. Vera is the parent of Esme. Milo is the parent of Ugo. Pete is the parent of Gwen. Yves is the parent of Hugo. Uzi is the parent of Sven. Bea is the parent of Cyrus. Vera is the parent of Anja. Tom is the parent of Alma. Fern is the parent of Zane. Zane is the parent of Dell. Hana is the parent of Cara. Gwen is the parent of Carla. Nico is the parent of Xavi. Oscar is the parent of Eli. Vera is the parent of Mona. Edna is the parent of Hal. Zita is the parent of Sean. Cleo is the parent of Jade. Gwen is the parent of Zita. Bea is the parent of Fern. Kurt is the parent of Yara. Abel is the parent of Joss. Abel is the parent of Lila. Cleo is the parent of Alva. Yves is the parent of Bram. Pete is the parent of Bea. Jules is the parent of Liam. Tess is the parent of Pete. Uzi is the parent of Vera. Jules is the parent of Neva. Sven is the parent of Wren. Nico is the parent of Felix. Hana is the parent of Nico. Oscar is the parent of Hana. Pete is the parent of Oscar. Tom is the parent of Viv. Oscar is the parent of Fay. Sean is the parent of Quinn. Nobody else has a recorded parent. Among the children of Pete, who has the most descendants (children, their children, and so on, all the way down)? Choose from Bea, Cleo, Gwen and Oscar.
structured: {"ask": "descendants", "candidates": ["Bea", "Cleo", "Gwen", "Oscar"], "parent": {"Abel": "Tess", "Ada": "Quinn", "Alma": "Tom", "Alva": "Cleo", "Anja": "Vera", "Bea": "Pete", "Bram": "Yves", "Cara": "Hana", "Carla": "Gwen", "Cleo": "Pete", "Cyrus": "Bea", "Dell": "Zane", "Edna": "Eli", "Eli": "Oscar", "Emil": "Rex", "Esme": "Vera", "Fay": "Oscar", "Felix": "Nico", "Fern": "Bea", "Flynn": "Cleo", "Gus": "Bea", "Gwen": "Pete", "Hal": "Edna", "Hana": "Oscar", "Hugo": "Yves", "Jade": "Cleo", "Jon": "Rex", "Joss": "Abel", "Kurt": "Jade", "Lars": "Kurt", "Liam": "Jules", "Lila": "Abel", "Milo": "Gus", "Mona": "Vera", "Neva": "Jules", "Nico": "Hana", "Nora": "Rex", "Opal": "Quinn", "Oscar": "Pete", "Pete": "Tess", "Quinn": "Sean", "Rex": "Sean", "Rhea": "Kurt", "Sean": "Zita", "Sia": "Edna", "Sven": "Uzi", "Tara": "Ugo", "Tom": "Yves", "Ugo": "Milo", "Uzi": "Alva", "Vera": "Uzi", "Viv": "Tom", "Wren": "Sven", "Xavi": "Nico", "Yara": "Kurt", "Yves": "Carla", "Zane": "Fern", "Zita": "Gwen"}, "people": ["Pete", "Bea", "Gwen", "Cleo", "Oscar", "Fern", "Gus", "Cyrus", "Milo", "Zane", "Ugo", "Tara", "Dell", "Zita", "Carla", "Yves", "Sean", "Quinn", "Ada", "Rex", "Tom", "Viv", "Emil", "Opal", "Hugo", "Jon", "Nora", "Alma", "Bram", "Alva", "Jade", "Flynn", "Kurt", "Uzi", "Vera", "Anja", "Esme", "Mona", "Yara", "Rhea", "Lars", "Sven", "Wren", "Eli", "Fay", "Hana", "Nico", "Edna", "Cara", "Hal", "Felix", "Xavi", "Sia", "Tess", "Abel", "Lila", "Joss", "Jules", "Neva", "Liam"], "root": "Pete"}
answer: Gwen
```

### `R1.knights_knaves_r5` (family truth, intended part ?)

structured: {"people", "statements": [[kind, [args]]], "who"} as knights_knaves, with two more kinds ("same_kind", "differ"). 4 + level // 2 people. A hidden assignment of knights and knaves is drawn first (a fair
coin each); each person's statement is then drawn uniformly among the statements (kind, arguments) that are TRUE under the hidden assignment if the speaker is a knight and FALSE if a knave, so the kind of statement
is independent of the speaker's type by construction. Statement sets with more than one solution are redrawn (validity: a unique answer). The asked person is uniform. (The earlier shape: 'a speaker who accuses someone is a knight' scored +0.20 to +0.33.)

Example (level 2):

```
question: Each person is either a knight, who always tells the truth, or a knave, who always lies. Abel says: "exactly one of Abel and Nell is a knight." Esme says: "Abel and Rex are both knights." Rex says: "Abel and Rex are of the same kind." Greta says: "Abel is a knave." Nell says: "exactly one of Rex and Nell is a knight." Is Abel a knight or a knave? Answer knight or knave.
structured: {"people": ["Abel", "Esme", "Rex", "Greta", "Nell"], "statements": [["differ", [0, 4]], ["both_knights", [0, 2]], ["same_kind", [0, 2]], ["is_knave", [0]], ["differ", [2, 4]]], "who": 0}
answer: knight
```

### `R1.minimax_tree_r5` (family trees, intended part ?)

structured: {"tree", "first", "depth", "branching"} as minimax_tree_r4 (the same wording). Trees are larger at every level and always branch three or more ways: (depth, branching) = (3,3) (3,4) (4,3) (3,5) (3,6) (5,3) (4,4), so 27 to 256 leaves (the earlier level 0 had 4 leaves
and 'the median leaf' scored +0.55, 'the option with the best leaf' +0.68). The first mover is drawn; leaves are integers from -50 to 50 (open number answer; the earlier range -9..9 put the answer on one value in a fifth of the deepest trees).

Example (level 2):

```
question: Two players, Max and Min, play a game with 4 choices in a row, Min choosing first and then Max, and so on in turn. At each choice the mover picks one of the 3 options shown. The game is written as nested options: ((((50 or -47 or -15) or (-19 or 38 or -38) or (-33 or 46 or 26)) or ((-19 or -29 or 28) or (-41 or -30 or 35) or (1 or -23 or -9)) or ((42 or -45 or -5) or (-20 or -18 or -28) or (48 or 0 or -34))) or (((-20 or -5 or -14) or (39 or 36 or 28) or (-12 or -47 or 45)) or ((9 or -31 or -24) or (-35 or -9 or -28) or (-11 or 24 or -23)) or ((47 or -4 or 30) or (19 or -45 or 31) or (-6 or 9 or 7))) or (((18 or 32 or 31) or (22 or -32 or -38) or (7 or 49 or 6)) or ((38 or 27 or -39) or (-30 or 29 or -2) or (-42 or 42 or 48)) or ((46 or 3 or 35) or (-18 or -1 or -12) or (-29 or -10 or 0)))). When the options are all numbers, the number picked is the payoff. Max wants the payoff as large as possible and Min as small as possible, and both play perfectly. What is the payoff?
structured: {"branching": 3, "depth": 4, "first": "min", "tree": [[[[50, -47, -15], [-19, 38, -38], [-33, 46, 26]], [[-19, -29, 28], [-41, -30, 35], [1, -23, -9]], [[42, -45, -5], [-20, -18, -28], [48, 0, -34]]], [[[-20, -5, -14], [39, 36, 28], [-12, -47, 45]], [[9, -31, -24], [-35, -9, -28], [-11, 24, -23]], [[47, -4, 30], [19, -45, 31], [-6, 9, 7]]], [[[18, 32, 31], [22, -32, -38], [7, 49, 6]], [[38, 27, -39], [-30, 29, -2], [-42, 42, 48]], [[46, 3, 35], [-18, -1, -12], [-29, -10, 0]]]]}
answer: 9
```

### `R1.nim_xor_r5` (family games, intended part ?)

structured: {"piles": [sizes], "size_class": m} as nim_xor_r4. The answer ('first' or 'second') is drawn first. second: the last pile is the xor of the others (xor 0); first: the last pile is that xor with ONE bit
flipped, the bit position drawn uniformly among bits 1 .. log2(m) - 1 (so the xor of the piles is a single power of two). Every pile is in [m, 2m), so the top bit is in every pile and the sum is even. A
run of the xor on one or two bit positions is then right only 1 / (log2(m) - 1) of the time on the first-player items (+0.5 / (bits) over chance, 0.06 at 9 bits; the earlier shape: bit 1 alone scored +0.23 to +0.30).

Example (level 2):

```
question: A game has 4 piles of stones: 1766, 1213, 2016, 1979. Two players take turns. On a turn, a player must remove at least one stone, all from a single pile (any number up to the whole pile). The player who takes the very last stone wins. Both play perfectly and the first player moves first. Who wins, the first player or the second player? Answer first or second.
structured: {"piles": [1766, 1213, 2016, 1979], "size_class": 1024}
answer: first
```

### `R1.order_compare_r5` (family order, intended part ?)

structured: {"taller": [[a, b]] (a is taller than b), "x", "y"} as order_compare. The answer class is drawn first (uniform over yes, no, cannot be determined). The depth is controlled by level: a planted chain whose
x-to-y part has d steps, d uniform in 2 + level .. 7 + level, with 1 or 2 more people above x and below y. yes: x is d steps above y; no: the reverse; cannot be determined: x and y lie in two separate chains of about d / 2 steps each. Every person outside the
chains is a leaf: x and y each get 0 to 3 shorter and 0 to 3 taller leaves (independent of the class), and 1 + level // 3 more hang from random chain persons, so the degrees of x and y say nothing. The asked pair is stated in neither direction. So a search of k steps answers only the items with d <= k (at most a sixth of the yes / no items), and
the earlier shape's "two steps, else cannot be determined" (+0.64 at every level) reads chance.

Example (level 2):

```
question: Eli is taller than Mona. Ugo is taller than Nora. Neva is taller than Nora. Hana is taller than Uma. Wade is taller than Ugo. Mona is taller than Rosa. Yara is taller than Wade. Gus is taller than Wade. Wade is taller than Fern. Mona is taller than Xan. Wade is taller than Hugo. Xan is taller than Tom. Uma is taller than Wade. Sia is taller than Mona. Yuri is taller than Mona. Tom is taller than Hana. Mona is taller than Thea. Dell is taller than Rhea. Rhea is taller than Mona. Kenji is taller than Wade. Is Mona taller than Wade? Answer yes, no or cannot be determined.
structured: {"taller": [["Eli", "Mona"], ["Ugo", "Nora"], ["Neva", "Nora"], ["Hana", "Uma"], ["Wade", "Ugo"], ["Mona", "Rosa"], ["Yara", "Wade"], ["Gus", "Wade"], ["Wade", "Fern"], ["Mona", "Xan"], ["Wade", "Hugo"], ["Xan", "Tom"], ["Uma", "Wade"], ["Sia", "Mona"], ["Yuri", "Mona"], ["Tom", "Hana"], ["Mona", "Thea"], ["Dell", "Rhea"], ["Rhea", "Mona"], ["Kenji", "Wade"]], "x": "Mona", "y": "Wade"}
answer: yes
```

### `R1.road_reachability_r5` (family graph, intended part ?)

structured: {"towns", "roads": [[a, b]] (one-way a -> b), "x", "y"} as road_reachability. The answer (yes / no) is drawn first. The route is a planted chain x = c0 -> c1 -> ... -> cd = y with d uniform in 3 + level .. 6 + level.
yes: the chain is complete. no: the link c_j -> c_{j+1} is missing (j uniform in 0 .. d - 2), so y is out of reach; every other town of the 'no' item is placed so that no road leads from the towns x can reach to the
others. In both classes the outdegree k of x is drawn first (1 to 3, extra roads of x go to other towns that x can reach), a reversed road c_{i+1} -> c_i is added with probability 1/2, and the number of further roads is drawn
independently of the answer (2 to n / 2 + 2). So the outdegree of x, the number of roads, and 'within two roads' carry no information (the earlier shape: outdegree >= 2 scored +0.35).

Example (level 2):

```
question: There is a one-way road from Fenwick to Selby. There is a one-way road from Yarrow to Norwick. There is a one-way road from Westmere to Brook. There is a one-way road from Brook to Garth. There is a one-way road from Harrow to Brook. There is a one-way road from Norwick to Westmere. There is a one-way road from Brook to Oakham. There is a one-way road from Fenwick to Ravenna. There is a one-way road from Ravenna to Yarrow. There is a one-way road from Larkin to Calder. There are no other roads. Can you travel from Fenwick to Calder using these roads? Answer yes or no.
structured: {"roads": [[9, 4], [11, 3], [12, 5], [5, 0], [2, 5], [3, 12], [5, 6], [9, 8], [8, 11], [13, 7]], "towns": ["Garth", "Kelso", "Harrow", "Norwick", "Selby", "Brook", "Oakham", "Calder", "Ravenna", "Fenwick", "Eastvale", "Yarrow", "Westmere", "Larkin"], "x": 9, "y": 7}
answer: no
```

### `R1.seating_row_r5` (family arrangement, intended part ?)

structured: {"people", "clues", "seat"} as seating_row. n = 6, 7, 7, 7, 7, 7, 7 seats (the earlier level 0 had three seats: at most a few hundred structures). The asked seat is drawn first and no clue names a person
in that seat ('pos' clues are drawn only for the other seats), so the answer is never stated; clues of all six kinds (including 'between', which the earlier shape used only from level 3) are added at random until the
answer is unique. With 'between' from level 0 the structure count at level 0 reaches 60,000 by the collision estimate at 20,000 draws (without it, 20,000)).

Example (level 2):

```
question: Kira, Lars, Lila, Pablo, Pearl, Sven and Tess sit in a row of 7 seats numbered 1 to 7 from the left, one person per seat. Pablo sits in seat 1. Lila sits immediately to the left of Tess. Pablo sits at one of the two ends of the row. Kira sits in seat 5. Tess sits immediately to the left of Kira. Pablo and Tess do not sit next to each other. Kira sits somewhere between Pearl and Sven. Sven sits at one of the two ends of the row. Pearl sits somewhere between Lars and Pablo. Lila sits somewhere to the left of Lars. Who sits in seat 2?
structured: {"clues": [["pos", 1, 0], ["adj", 6, 3], ["end", 1], ["pos", 0, 4], ["adj", 3, 0], ["notnext", 1, 3], ["between", 2, 0, 4], ["end", 4], ["between", 5, 2, 1], ["left", 6, 5]], "people": ["Kira", "Pablo", "Pearl", "Tess", "Sven", "Lars", "Lila"], "seat": 1}
answer: Pearl
```

### `R1.spatial_grid_walk_r5` (family spatial, intended part ?)

structured: {"grid": [[name | null]], "start": [row, col], "moves": [direction], "convention": ...} as spatial_grid_walk_r2. About 30 % of the cells are walls (the earlier shape: 15 %). The walk has
L = 4 + level + (0 to 3) free moves (so its length is not always odd or even, which would fix the colour of the end cell on the grid) and 3 + level // 3 moves blocked by a wall. The END cell is drawn first, uniformly among the open
cells that a walk of exactly L free steps can reach from the start; the free walk is then drawn uniformly among such walks (counted by dynamic programming); the blocked moves are inserted at uniformly drawn places where the
current cell has a wall next to it, each blocked direction uniform among the walls next to that cell (a Retry when no place has one: validity). So a walk that ignores the walls enters a wall in almost every item (the earlier
shape scored +0.46 to +0.66) and the end cell is not tied to the start cell.

Example (level 2):

```
question: A map has 3 rows (row 1 is the northernmost) and 4 columns (column 1 is the westernmost). Row 1: Tamex, Lovar, wall, Virak. Row 2: wall, wall, Vedan, Kokin. Row 3: Kosen, Dekik, wall, wall. You start at Kosen. You move east, then west, then east, then north, then east, then west, then east, then west, then north, one cell each time. A move into a wall or off the map does nothing. Which place do you end on? Choose from Dekik, Kokin, Kosen, Lovar, Tamex, Vedan and Virak.
structured: {"convention": "row 1 is the northernmost, column 1 is the westernmost", "grid": [["Tamex", "Lovar", null, "Virak"], [null, null, "Vedan", "Kokin"], ["Kosen", "Dekik", null, null]], "moves": ["east", "west", "east", "north", "east", "west", "east", "west", "north"], "start": [2, 0]}
answer: Kosen
```

### `R1.spatial_relative_directions_r5` (family spatial, intended part ?)

structured: {"places", "facts": [[a, direction, k, b]], "x", "y"} as spatial_relative_directions_r4. X and Y are the ends of a spine of L = 5 + level // 3 facts (each a random direction and k uniform in 1 .. 9);
2 + level // 3 further places hang from random places. Answer: the street distance |dx| + |dy| (an open number, >= 1, else Retry). Summing the legs ignoring direction is right only when no two legs cancel
(about 6 % of the items at L = 6; the earlier shape: 40 to 65 % at the shorter paths).

Example (level 2):

```
question: Upton is 7 blocks west of Selby. Norwick is 4 blocks south of Larkin. Larkin is 5 blocks east of Upton. Upton is 2 blocks west of Westmere. Fenwick is 5 blocks east of Dunmore. Dunmore is 2 blocks east of Norwick. Thornbury is 9 blocks west of Westmere. How far apart are Selby and Fenwick by street distance (blocks north or south plus blocks east or west)?
structured: {"facts": [["Upton", "west", 7, "Selby"], ["Norwick", "south", 4, "Larkin"], ["Larkin", "east", 5, "Upton"], ["Upton", "west", 2, "Westmere"], ["Fenwick", "east", 5, "Dunmore"], ["Dunmore", "east", 2, "Norwick"], ["Thornbury", "west", 9, "Westmere"]], "places": ["Selby", "Upton", "Larkin", "Norwick", "Dunmore", "Fenwick", "Westmere", "Thornbury"], "x": "Selby", "y": "Fenwick"}
answer: 9
```

### `R1.swap_tracking_r5` (family tracking, intended part ?)

structured: {"hold": {person: item}, "ops": [["swap", a, b] | ["rotate", a, b, c]], "who": person} as swap_tracking. 5 + level // 2 people and 6 + 2 * level operations (the earlier shape had 3 people at level 0 and
13 different structures there). Operations: a swap with probability 1/2, a three-way rotation otherwise (each person's item goes to the next in the cycle). The asked person is drawn uniformly among the people whose FINAL item
has been moved by at least one rotation and at least one swap on its way (traced backwards through the operations): a structural condition on the question, not on any rule's answer, so no kind of
operation can be ignored (the earlier shape: ignoring the three-way hand-overs scored +0.17 to +0.21).

Example (level 2):

```
question: At the start Sean holds the lantern, Jon holds the umbrella, Hana holds the teapot, Thea holds the feather, Abel holds the quilt, Pete holds the apple. Sean hands their item to Jon, Jon hands theirs to Pete, and Pete hands theirs to Sean, all at once. Thea and Jon swap what they are holding. Sean and Hana swap what they are holding. Abel hands their item to Pete, Pete hands theirs to Hana, and Hana hands theirs to Abel, all at once. Sean and Hana swap what they are holding. Hana and Thea swap what they are holding. Pete hands their item to Jon, Jon hands theirs to Hana, and Hana hands theirs to Pete, all at once. Pete and Sean swap what they are holding. Thea and Hana swap what they are holding. Thea and Pete swap what they are holding. What is Sean holding at the end? Choose from apple, feather, lantern, quilt, teapot and umbrella.
structured: {"hold": {"Abel": "quilt", "Hana": "teapot", "Jon": "umbrella", "Pete": "apple", "Sean": "lantern", "Thea": "feather"}, "ops": [["rotate", "Sean", "Jon", "Pete"], ["swap", "Thea", "Jon"], ["swap", "Sean", "Hana"], ["rotate", "Abel", "Pete", "Hana"], ["swap", "Sean", "Hana"], ["swap", "Hana", "Thea"], ["rotate", "Pete", "Jon", "Hana"], ["swap", "Pete", "Sean"], ["swap", "Thea", "Hana"], ["swap", "Thea", "Pete"]], "who": "Sean"}
answer: lantern
```

### `R1.temporal_critical_path_r5` (family temporal, intended part ?)

structured: {"jobs": [[person, days, [persons it waits for]]]}. Answer: how many days in all pass until the last job has finished (an open number). The item STATES the convention: jobs take whole days; a
job that waits for nobody starts at the beginning of day 1; a job that waits for others starts at the beginning of the first day after the last of them has finished its final day; the count runs from the beginning of day 1
to the end of the final day of the last job. (The earlier item said 'starts on day 0 ... on which day is the last job finished' and the key was one too high under the inclusive-day reading in 7,000 of 7,000 items.) 8 + level jobs;
durations 5 to 12 days; the first two wait for nobody and every later job waits for exactly two of the four jobs before it, so a walk back through 'the longest predecessor' has to choose at every step of a long chain and the finish times of the two predecessors differ by more than a duration does (the earlier shape: 50 % of the jobs had one prerequisite and
that walk scored +0.69 to +0.86).

Example (level 2):

```
question: Ulf's job takes 10 days and waits for the jobs of Gita and Glen. Elsa's job takes 9 days and waits for the jobs of Jade and Uzi. Jade's job takes 7 days and waits for the jobs of Kenji and Uzi. Glen's job takes 11 days and waits for nobody. Gita's job takes 9 days and waits for the jobs of Cleo and Glen. Cleo's job takes 12 days and waits for nobody. Iris's job takes 5 days and waits for the jobs of Kenji and Lena. Lena's job takes 8 days and waits for the jobs of Gita and Glen. Kenji's job takes 11 days and waits for the jobs of Gita and Ulf. Uzi's job takes 10 days and waits for the jobs of Kenji and Lena. Jobs take whole days. A job that waits for nobody starts at the beginning of day 1. A job that waits for others starts at the beginning of the first day after the last of them has finished its final day. How many days in all pass, counting from the beginning of day 1 to the end of the final day of the last job to finish?
structured: {"jobs": [["Glen", 11, []], ["Cleo", 12, []], ["Gita", 9, ["Cleo", "Glen"]], ["Lena", 8, ["Gita", "Glen"]], ["Ulf", 10, ["Gita", "Glen"]], ["Kenji", 11, ["Gita", "Ulf"]], ["Iris", 5, ["Kenji", "Lena"]], ["Uzi", 10, ["Kenji", "Lena"]], ["Jade", 7, ["Kenji", "Uzi"]], ["Elsa", 9, ["Jade", "Uzi"]]]}
answer: 68
```

### `R1.temporal_interval_overlap_r5` (family temporal, intended part ?)

structured: {"events", "spans": [["range", a, b] | ["dur", s, d]], "x", "y"} as temporal_interval_overlap. The asked pair: the answer (yes / no) and the gap g between the two starts (uniform 0 .. 40) are drawn
independently; the event that starts first lasts L days with L uniform in g + 1 .. g + 12 (they overlap) or in max(2, g - 11) .. g (they do not), and the other lasts 2 to 60 days (so 'the longer of the two lasts longer than the gap' is not the test). So the gap between the starts says nothing
(the earlier shape: 'the starts are within 20 days' scored +0.39 to +0.42), the duration of the event that starts last is irrelevant, and both date formats occur. 4 + (level + 1) // 2 events; the other events are random.

Example (level 2):

```
question: The town parade ran from day 111 to day 116, both days included. The chess final started on day 34 and went on for 12 days (day 34 counts as the first). The harvest fair ran from day 73 to day 75, both days included. The cycle tour started on day 14 and went on for 12 days (day 14 counts as the first). The concert ran from day 79 to day 86, both days included. Did the chess final and the cycle tour overlap, that is, was there at least one day on which both were going on? Answer yes or no.
structured: {"events": ["the town parade", "the chess final", "the harvest fair", "the cycle tour", "the concert"], "spans": [["range", 111, 116], ["dur", 34, 12], ["range", 73, 75], ["dur", 14, 12], ["range", 79, 86]], "x": "the chess final", "y": "the cycle tour"}
answer: no
```

### `R1.temporal_weekday_shift_r5` (family temporal, intended part ?)

structured: {"days", "anchor": [event, weekday], "links": [[later, earlier, n]], "ask"} as temporal_weekday_shift. The asked event lies at the end of a spine of L = 5 + level // 3 links from the anchor, each link
with a random direction and n uniform in 1 .. 300 (days); 2 + level // 3 further events hang from random events. So "ignore before and after" is right only when the spine is monotone (about 1/16) or by chance (1/7).

Example (level 2):

```
question: The bake-off took place on a Thursday. The bridge opening took place 34 days after the concert. The concert took place 299 days before the bake-off. The chess final took place 290 days before the cycle tour. The bridge opening took place 284 days before the cycle tour. The chess final took place 113 days after the market day. The book sale took place 176 days after the concert. The harvest fair took place 129 days after the bake-off. On which day of the week did the market day take place?
structured: {"anchor": ["the bake-off", "Thursday"], "ask": "the market day", "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "links": [["the bridge opening", "the concert", 34], ["the bake-off", "the concert", 299], ["the cycle tour", "the chess final", 290], ["the cycle tour", "the bridge opening", 284], ["the chess final", "the market day", 113], ["the book sale", "the concert", 176], ["the harvest fair", "the bake-off", 129]]}
answer: Friday
```

### `R1.topological_order_r5` (family scheduling, intended part ?)

structured: {"jobs": [[name, [prerequisites]]], "day": j} as topological_order_r4. 10 + level jobs in 4 + level // 2 parallel chains of unequal length (each job needs the one before it in its chain), and
every job also needs, with probability 1/10, one job of another chain that sits earlier in its chain than it (a cross prerequisite). Names are drawn independently of the position in a chain, so the alphabetical
rule decides most days and a layered order (depth, then name) usually differs from the true one. Answer: the job done on day j (3 .. n).

Example (level 2):

```
question: There are 12 jobs and one job is done each day. Nora has no prerequisite. Bram needs Greta to be done first. Greta needs Nora to be done first. Flynn needs Bram to be done first. Ada has no prerequisite. Wren needs Cara to be done first. Cara needs Jana to be done first. Kurt has no prerequisite. Zita needs Tara to be done first. Jana has no prerequisite. Tara needs Flynn and Jana to be done first. Xavi has no prerequisite. Each day, among the jobs that can be done (all their prerequisites are already done), the job whose name comes first in alphabetical order is done. Which job is done on day 7? Choose from Ada, Bram, Cara, Flynn, Greta, Jana, Kurt, Nora, Tara, Wren, Xavi and Zita.
structured: {"day": 7, "jobs": [["Nora", []], ["Bram", ["Greta"]], ["Greta", ["Nora"]], ["Flynn", ["Bram"]], ["Ada", []], ["Wren", ["Cara"]], ["Cara", ["Jana"]], ["Kurt", []], ["Zita", ["Tara"]], ["Jana", []], ["Tara", ["Flynn", "Jana"]], ["Xavi", []]]}
answer: Bram
```

### `R1.tracking_accounts_r5` (family tracking, intended part ?)

structured: {"start": {name: dollars}, "ops": [["pay", a, b, amount] | ["earn", a, amount] | ["half", a, b]], "ask": name} as tracking_accounts, except that the question asks how many dollars ONE person
has at the end (an open number; the earlier shape asked who has the most or the least, and a walk that ignored the earnings scored +0.50 to +0.57). The asked person is drawn first and three operations
that involve them are planted at random places: a payment (they pay or are paid), an earning, and a halving (they give or receive half). Everyone starts with 50 to 80 dollars; pay and earn amounts are 5 to 50;
the payer always has the money; 6 + 2 * level operations among 4 + level // 2 people. Ignoring any one kind of operation therefore changes the asked person's balance.

Example (level 2):

```
question: At the start Tina has 80 dollars, Hal has 74 dollars, Kira has 59 dollars, Kate has 62 dollars, Greta has 67 dollars. Kira pays Kate 22 dollars. Hal earns 13 dollars. Greta pays Hal 12 dollars. Kira pays Hal 7 dollars. Hal pays Kira 35 dollars. Hal pays Greta 16 dollars. Greta pays Kate 27 dollars. Hal pays Kira 20 dollars. Greta gives half of their money to Hal. Hal earns 42 dollars. How many dollars does Hal have at the end?
structured: {"ask": "Hal", "ops": [["pay", "Kira", "Kate", 22], ["earn", "Hal", 13], ["pay", "Greta", "Hal", 12], ["pay", "Kira", "Hal", 7], ["pay", "Hal", "Kira", 35], ["pay", "Hal", "Greta", 16], ["pay", "Greta", "Kate", 27], ["pay", "Hal", "Kira", 20], ["half", "Greta", "Hal"], ["earn", "Hal", 42]], "start": {"Greta": 67, "Hal": 74, "Kate": 62, "Kira": 59, "Tina": 80}}
answer: 99
```

### `R1.venn_counting_r5` (family sets, intended part ?)

structured: {"total", "groups", "sizes", "pairs", "triples", "quad", "triple", "ask"} as venn_counting_r4 (the same levels: groups and asked quantity, the same wording). Only the magnitudes are wider: every region holds
1 to 24 + 4 * level people and the number in none of the groups is 0 to 30 + 2 * level, because the earlier level 0 (two groups, regions of 1 to 9) could print only about 11,000 different items, below the demand of 22,830.

Example (level 2):

```
question: Among 168 people, 83 people are in the choir group; 97 people are in the baking group; 93 people are in the diving group; 46 are in both the choir and the baking groups; 56 are in both the choir and the diving groups; 57 are in both the baking and the diving groups; 31 are in all of the choir, baking and diving groups. Each person is counted once in each number that applies to them. How many of the people are in none of these groups?
structured: {"ask": "none", "groups": ["choir", "baking", "diving"], "pairs": {"baking|diving": 57, "choir|baking": 46, "choir|diving": 56}, "quad": null, "sizes": {"baking": 97, "choir": 83, "diving": 93}, "total": 168, "triple": 31, "triples": {"choir|baking|diving": 31}}
answer: 23
```
