# The human lead's second statement, 2026-11-20 (evening, Panama time), verbatim

Received after the draft ADR-0032 and its first independent review. It restates the capability-parity requirement, names five properties the roadmap must investigate, and adds self-learning as a new research direction. Recorded here unchanged; ADR-0032 Part A quotes from it.

> Fable, I want to clarify and extend the long-term ArborLM hypothesis.
>
> ArborLM must be equally capable or more capable than the models it aims to replace. Capability parity is a mandatory requirement, not an optional objective.
>
> Our goal is not to produce a cheaper but weaker model. Our goal is to preserve or improve existing capabilities while changing the economics of memory, learning and inference.
>
> The research roadmap should explicitly investigate five properties:
>
> 1. Capability parity or superiority: Against relevant pretrained reference models on independent evaluations, with no unacceptable regression hidden by average scores.
> 2. Multi-teacher knowledge acquisition: Learn from multiple models, preserve complementary capabilities, and investigate whether their combination enables additional capabilities.
> 3. Continual learning and retention: Acquire new knowledge without repeatedly retraining the entire backbone or catastrophically forgetting earlier knowledge.
> 4. Scalable memory and efficiency: Expand useful knowledge capacity and reduce the cost of storing, accessing and updating it, without sacrificing capability.
> 5. Autonomous self-improvement: Investigate whether ArborLM can learn to improve its own retrieval, memory organization, consolidation, learning efficiency and eventually problem-solving capability.
>
> New research direction: self-learning
>
> I want to investigate whether ArborLM, once sufficiently capable, can identify inefficiencies in its own operation and learn to improve them.
>
> This should be experimentally separated into:
>
> A. Self-optimization of memory and computation
>
> Can ArborLM learn better retrieval policies, memory layouts, indexing strategies, sparse-update mechanisms or consolidation methods, while preserving or improving predictive and task-level quality?
>
> B. Self-directed capability learning
>
> Can ArborLM generate useful learning challenges, obtain reliable independent feedback, improve its performance and retain those improvements without depending continuously on a larger teacher?
>
> C. Sustained improvement
>
> Can these improvements accumulate across multiple learning cycles without performance collapse, self-generated error reinforcement or increasing computational costs that eliminate the benefit?
>
> Scientific requirements
>
> - Compare against fixed training strategies, conventional continual learning, self-distillation and appropriate retrieval baselines.
> - Measure capability and efficiency separately.
> - Preserve held-out evaluations that the self-improvement process cannot inspect or optimize directly.
> - Measure useful capability gained per unit of compute, memory growth and training time.
> - Record unsuccessful cycles and regressions, not only promoted checkpoints.
> - Use bounded experimental cycles with explicit resource limits and human approval for expanding scope.
> - Do not equate improved training loss with increased general intelligence.
> - Do not claim recursive self-improvement without repeated, independently validated capability gains.
>
> Important: this is a proposed future research direction, not an achieved result.
>
> P10-I-S6 remains CONVERGENCE NOT REACHED, and the previous experiments and their registered outcomes must remain unchanged.
>
> Please incorporate self-learning as a distinct forward-looking research pillar, define prerequisite milestones, and propose staged, preregistered experiments for my approval.
>
> I want to discover whether ArborLM can eventually become better at learning—not simply store more information.
>
> let's add does metric to the readme chart as well

The lead's reading of the last line (the lead's, not his words): add rows for these properties to the README progress scorecard. Starting scores are proposed by the lead and are his to confirm.
