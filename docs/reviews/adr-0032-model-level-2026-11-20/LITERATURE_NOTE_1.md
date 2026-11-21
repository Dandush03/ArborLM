# Literature and feasibility check for ADR-0032 (model-level capability parity), for test M0

- Date of check: 2026-11-20. Prepared by a Claude Fable 5.2 subagent (web research only; nothing downloaded, nothing run, no repository file changed other than this note).
- Status: scratch note, not a specification, not a result, not reviewed. `Astra review: NOT_PERFORMED`.
- Verification marks used throughout:
  - **[V]** = the page was fetched in this session and the statement is what the fetched page (abstract, model card, API metadata, licence file, README) says. Pages were read through an automatic summariser, so exact quotations and table numbers should be re-read by a human before they enter a specification.
  - **[M] UNVERIFIED** = stated from the author's memory of the literature; the source was not re-fetched in this session. Treat as a pointer to check, not as a fact.
  - **[E]** = my own estimate or arithmetic, not a sourced figure.
- arXiv items marked [V] were verified by id, title, first author and abstract through the arXiv API (`export.arxiv.org/api/query?id_list=...`). Canonical URL of each is `https://arxiv.org/abs/<id>`.

---

## 0. The ten findings that most affect the design

1. **The conjunction over domains is costly in power, and most public sets are too small for a 1–3 point margin.** With a paired item-level test, the standard error of the difference is about sqrt(d/n), d = share of items on which the two systems disagree [E]. For 80% power at one-sided 5% when the systems are truly equal, n ≈ 6.2·d/δ². With d = 0.15: δ = 3 points needs about 1,030 items, δ = 2 needs about 2,320, δ = 1 needs about 9,280. HumanEval (164 items) cannot support a margin below roughly 7–8 points. And five domains each at 80% power give about 0.8⁵ ≈ 33% power for the conjunction; about 96% power per domain is needed for 80% overall (n ≈ 11.5·d/δ²) [E]. Miller (2024) reaches the same order independently: about 969 questions to detect a 3-point difference under its assumptions, and recommends at least 1,000 questions per evaluation [V].
2. **"Run-to-run noise of the references" is close to zero for a frozen model with greedy decoding, so it is the wrong basis for δ on its own.** The dominant uncertainty is item sampling error (Miller 2024 [V]); the others are prompt format (up to 76 accuracy points in the extreme, Sclar et al. 2023 [V]), answer-ordering and scoring choices (rankings move by up to 8 positions, Alzahrani et al. 2024 [V]), sampling temperature, and quantisation. M0 should measure each of these separately and δ should be set from the item-level standard error plus the measured nuisance spreads.
3. **Quantisation changes which items are answered correctly even when the total barely moves.** Dutta et al. 2024 [V]: on MMLU, 4-bit (bitsandbytes) flips 5.7–10.9% of answers with accuracy changes of −0.8 to −2.1 points; 8-bit flips 2.5–4.2% with −0.6 to +0.05 points; on GSM8K flips are 12–32%. Consequence: every system in a comparison must use the same precision and stack, and ADR-0032's "item-level regressions" count will be non-zero from precision alone. All candidate models up to 9B fit at bf16 in 48 GB, so quantisation can be avoided.
4. **No prior result found in which a small student matches a much larger teacher across broad domains.** The "student beats teacher" results verified here (Distilling step-by-step; TinyLLM) are task-specific students trained with ground-truth labels and compared on that task; the capacity-gap literature (Cho & Hariharan; Mirzadeh et al.; Stanton et al.; Busbridge et al.) explains why. Tier 2 parity for a 0.5–1.5B student against 8–9B teachers in every domain would be unprecedented as far as this check found. (Absence in my search is not proof of absence.)
5. **Combining models rarely exceeds the best single model in every domain.** FuseLLM beats its best source on average on two of three benchmark families, loses on individual tasks, and is below the best source on all ten code tasks [V]. RouterBench: the oracle (item-level union) is far above the best single model (0.957 vs 0.828 on MMLU) but learned routers only reach the best single model [V]. "Rethinking Mixture-of-Agents": aggregating one strong model with itself beats mixing different models [V]. The ADR's router control and union ceiling are the right controls; an item-level learned router should be added beside the per-domain router.
6. **A nearest-neighbour key-value memory has a documented reasoning limit.** Geng et al. 2024 [V]: kNN-LMs improve memory-type tasks but mostly lower reasoning scores (for example GSM8K 14.83 → 12.05 on Llama-2-7B), and even with the correct answer forced into the retrieved neighbours NQ and HotpotQA stay under 50%. This is direct prior evidence for ADR-0032 open problem "a key-value memory may not carry capabilities that are not look-ups".
7. **GLM-family open weights that fit the machine and the download budget at official precision are only the 9B class.** `zai-org/GLM-4-9B-0414` and `zai-org/GLM-Z1-9B-0414` (MIT, 18.80 GB each) [V]; the older `glm-4-9b-chat` family and `glm-edge` models carry the custom "glm-4" licence [V]. `GLM-4.7-Flash` is 31.2B parameters and 62.4 GB; `GLM-4-32B-0414` is 65.1 GB; `GLM-5.3-Flash` is about 321B parameters [V]. All exceed 50 GB as officially published.
8. **Licences: the Qwen candidates are tagged Apache-2.0 and GLM-4-9B-0414 is MIT; neither licence restricts use of outputs to train another system.** The custom glm-4 licence (older GLM-4-9B, glm-edge) does have a clause that bites: a model "created, trained, fine-tuned or otherwise improved" using the materials must carry "glm-4" at the start of its name, academic research is free, and commercial use needs registration [V]. Avoid the glm-4-licensed models as teachers unless that is accepted.
9. **Whether the two teachers differ (precondition of section 7) cannot be read from the cards.** The GLM-4-9B-0414 card gives no benchmark numbers for the 9B model [V]. If the Qwen teacher is ahead in every domain the two-teacher question is NOT EVALUABLE; M0 is the right place to find out, and the specification should say what happens then.
10. **Feasible locally.** llama.cpp's Apple-silicon table lists M5 Pro at about 66–68 tokens/s generation and 1,340–1,620 tokens/s prompt processing for a 7B model at Q4_0 [V]; mlx-lm has model code for `glm4`, `qwen2`, `qwen3`, `qwen3_5` [V]. A full M0 battery of roughly 5–8 thousand items per model is hours, not days, for a 9B model without thinking mode [E]. Generated code must run in an isolated container or VM; HumanEval's own README says so [V].

---

## 1. Prior work to position against, and baselines to take

### 1.1 Knowledge distillation into small language models

| Reference | What the source says | Mark |
|---|---|---|
| Hinton, Vinyals, Dean 2015, "Distilling the Knowledge in a Neural Network", arXiv 1503.02531 | Soft-target distillation; the origin of the method | [M] UNVERIFIED |
| Cho & Hariharan 2019, "On the Efficacy of Knowledge Distillation", arXiv 1910.01348 | Larger, more accurate teachers often make worse teachers because small students cannot mimic them; early-stopped teachers help | [V] |
| Mirzadeh et al. 2019, "Improved Knowledge Distillation via Teacher Assistant", arXiv 1902.03393 | Student performance degrades when the teacher is much larger; an intermediate-size assistant closes part of the gap | [V] |
| Stanton et al. 2021, "Does Knowledge Distillation Really Work?", arXiv 2106.05945 | Students often keep a large gap from the teacher's predictive distribution even when they have the capacity to match; optimisation difficulty is a key cause | [V] |
| Busbridge et al. 2025, "Distillation Scaling Laws", arXiv 2502.08606 | Distillation beats supervised learning only up to a compute level that scales with student size; with one student and a teacher that must be trained, supervised learning is generally preferable | [V] |
| Hsieh et al. 2023, "Distilling Step-by-Step!", arXiv 2305.02301 | Teacher rationales as extra supervision; a 770M T5 beats few-shot 540B PaLM on a benchmark using 80% of the data | [V] |
| Gu et al. 2023, "MiniLLM", arXiv 2306.08543 | Reverse-KL, on-policy distillation of LLMs from 120M to 13B; better than standard KD baselines | [V] |
| Xu et al. 2024, "A Survey on Knowledge Distillation of LLMs", arXiv 2402.13116 | Organises LLM distillation; data augmentation (teacher-generated data) is the main vehicle | [V] |

**Lesson for the design.** Known reasons a student rarely matches its teacher: (a) capacity gap (Cho & Hariharan; Mirzadeh); (b) low fidelity even with enough capacity, from optimisation (Stanton); (c) limited transfer data. Where a small student "outperforms" a large LLM, the student is trained on the task's labelled data and the teacher is used zero- or few-shot, on a narrow task (Hsieh et al.; TinyLLM below). The ADR's Tier 1 baseline "distillation into a low-rank adapter, same teachers, same teaching data" is the standard comparison; add a **plain supervised baseline on the same teaching data with ground-truth labels where they exist**, because that is what the "exceeds teacher" literature actually measures, and state for every comparison whether the reference saw task-specific training.

### 1.2 Multi-teacher distillation

| Reference | What the source says | Mark |
|---|---|---|
| You et al. 2017, "Learning from Multiple Teacher Networks" (KDD) | Averaged teacher outputs as targets | [M] UNVERIFIED |
| Yuan et al. 2020, "Reinforced Multi-Teacher Selection for Knowledge Distillation", arXiv 2012.06048 | Per-instance dynamic weighting of teachers beats fixed or equal weights on several NLP tasks (no numbers in abstract) | [V] |
| Tian et al. 2024, "Beyond Answers: ... Multi-Teacher Knowledge Distillation" (TinyLLM), arXiv 2402.04616 | Teachers FLAN-T5-xlarge (3B) and Llama-2-chat (7B); students FLAN-T5 80M/250M/780M; six QA datasets. Student is trained with ground-truth labels plus teacher rationales. Totals: teachers 64.49 and 59.87; 780M student full fine-tuning 70.31, TinyLLM 73.88; 250M TinyLLM 65.02; 80M TinyLLM 55.78 | [V] (HTML version) |
| Wan et al. 2024, "Knowledge Fusion of Large Language Models" (FuseLLM), arXiv 2401.10491 | Fuses Llama-2-7B, MPT-7B, OpenLLaMA-7B into one. BBH: sources 39.70 / 33.38 / 33.87, fused 41.75. Common sense: best source 63.76, fused 64.56. MultiPL-E: best source 18.11, fused 15.56 (below the best source on all ten languages). On BBH it loses to the best source on several individual tasks | [V] (HTML version) |
| Allen-Zhu & Li 2020, "Towards Understanding Ensemble, Knowledge Distillation and Self-Distillation", arXiv 2012.09816 | Theory: ensembles help on "multi-view" data and that gain can be distilled into one model | [V] |
| Furlanello et al. 2018, "Born Again Neural Networks", arXiv 1805.04770 | Same-architecture students can outperform their teachers | [V] |

**Lesson.** (i) In TinyLLM the multi-teacher gain over single-teacher distillation is a few points and full fine-tuning with labels alone already beats both teachers at 780M: the "exceeds teachers" headline comes mostly from supervised task training, not from combining. (ii) FuseLLM is the closest published analogue of "two or three teachers → one model, measured across reasoning, common sense and code" and shows exactly the pattern ADR-0032 section 7 is built to expose: a higher average that hides per-task and per-domain regressions. (iii) Born-again results concern equal-capacity students. Take from this: per-domain tables only, the better single teacher per domain as a mandatory control, and single-teacher versions of S as the interference control (already in the draft).

### 1.3 Model merging, ensembling, routing

| Reference | What the source says | Mark |
|---|---|---|
| Wortsman et al. 2022, "Model soups", arXiv 2203.05482 | Averaging weights of fine-tunes of one base improves accuracy at no inference cost | [V] |
| Ilharco et al. 2022, "Editing Models with Task Arithmetic", arXiv 2212.04089 | Task vectors can be added to give multi-task ability | [V] |
| Yadav et al. 2023, "TIES-Merging", arXiv 2306.01708; Yu et al. 2023, "DARE", arXiv 2311.03099 | Interference between task vectors is the central problem; sign conflicts and redundant deltas are trimmed | [V] |
| Yadav et al. 2024, "What Matters for Model Merging at Scale?", arXiv 2410.03617 | 1B–64B models, up to 8 experts; merging works better with strong bases and larger models | [V] |
| Chen et al. 2023, "FrugalGPT", arXiv 2305.05176 | LLM cascade matches GPT-4 with up to 98% cost reduction or +4% accuracy at equal cost | [V] |
| Shnitzer et al. 2023, "LLM Routing with Benchmark Datasets", arXiv 2309.15789 | Router trained from benchmark results improves over any single model across tasks | [V] |
| Hu et al. 2024, "RouterBench", arXiv 2403.12031 | Oracle router 0.957 vs best single model 0.828 on MMLU; learned kNN/MLP routers reach the best single model at lower or similar cost but none significantly beats the trivial baseline router; cascades depend sharply on judge error (degrade past 0.2) | [V] (HTML version) |
| Ong et al. 2024, "RouteLLM", arXiv 2406.18665 | Strong/weak routing cuts cost over 2x at equal quality | [V] |
| Jiang et al. 2023, "LLM-Blender", arXiv 2306.02561 | Pairwise ranking plus generative fusion beats individual LLMs on MixInstruct | [V] |
| Wang et al. 2024, "Mixture-of-Agents", arXiv 2406.04692 | Layered aggregation of open models: 65.1% on AlpacaEval 2.0 vs 57.5% for GPT-4o | [V] |
| Li et al. 2025, "Rethinking Mixture-of-Agents", arXiv 2502.00674 | Self-MoA (aggregating samples of the single best model) beats mixed MoA by 6.6% on AlpacaEval 2.0 and 3.8% on average across MMLU, CRUX, MATH | [V] |

**Lesson.** Weight merging requires a shared base and architecture, so it does not apply to a Qwen teacher plus a GLM teacher; it is a positioning reference, not a baseline. Routing and ensembling do apply and are the baselines a two-teacher claim must face. Two facts to design around: the item-level oracle is usually far above the best single model, so "union of teachers" is a generous ceiling and the gap to it should be reported, not treated as reachable; and realised combination gains are small and can be reproduced by sampling the best model several times (Self-MoA). Add as controls: (1) per-domain router (in the draft), (2) a learned per-item router, (3) the better teacher sampled k times with majority vote, at the inference cost S is allowed.

### 1.4 Continual learning for LLMs: metrics and baselines

| Reference | What the source says | Mark |
|---|---|---|
| Lopez-Paz & Ranzato 2017, "Gradient Episodic Memory", arXiv 1706.08840 | Defines the task-by-task accuracy matrix R and from it average accuracy, backward transfer (BWT) and forward transfer (FWT); proposes GEM | [V] (abstract); formulas [M] |
| Chaudhry et al. 2018, "Riemannian Walk", arXiv 1801.10112 | Defines the forgetting and intransigence measures | [V] (abstract); formulas [M] |
| Chaudhry et al. 2019, "On Tiny Episodic Memories", arXiv 1902.10486 | Simple experience replay with a tiny memory beats specialised methods; one example per class gives 7–17% | [V] |
| Kirkpatrick et al. 2017, EWC, arXiv 1612.00796 | Regularisation baseline | [M] UNVERIFIED |
| Luo et al. 2023, "An Empirical Study of Catastrophic Forgetting in LLMs During Continual Fine-tuning", arXiv 2308.08747 | Forgetting is observed from 1B to 7B and grows with scale in that range | [V] |
| Wang et al. 2023, "TRACE", arXiv 2310.06762 | Eight-task continual benchmark for LLMs; after sequential training Llama-2-chat-13B falls from 28.8% to 2% on GSM8K | [V] |
| Wang et al. 2023, "O-LoRA", arXiv 2310.14152 | One LoRA per task in mutually orthogonal subspaces; no replay data | [V] |
| Biderman et al. 2024, "LoRA Learns Less and Forgets Less", arXiv 2405.09673 | Low-rank LoRA underperforms full fine-tuning on the target domain but forgets less; forgetting measured on HellaSwag, WinoGrande, ARC-Challenge; e.g. code instruction-tuning, source-domain average 0.414 (full) vs 0.509 (LoRA r=64) | [V] (HTML version) |
| Kotha et al. 2023, arXiv 2309.10105 | Part of apparent forgetting is task-inference skew, partly recoverable by re-prompting | [V] |
| Surveys: Wu et al. 2024, arXiv 2402.01364; Shi et al. 2024, arXiv 2404.16789 | Taxonomies: continual pre-training, instruction tuning, alignment; contrast with RAG and model editing | [V] |

Standard definitions, with a[i][j] = score on task j after learning task i, T tasks [M — check against the two papers before quoting]:
- Average accuracy: mean over j of a[T][j].
- Backward transfer: BWT = (1/(T−1)) · Σ_{j<T} (a[T][j] − a[j][j]). Negative means forgetting.
- Forward transfer: FWT = (1/(T−1)) · Σ_{j>1} (a[j−1][j] − b[j]), b[j] = score of the untrained model on task j.
- Forgetting (Chaudhry): for task j after step k, max over earlier steps l<k of a[l][j], minus a[k][j]; averaged over j.
- Intransigence: single-task (or joint) reference score on task j minus a[j][j]; the inability to learn the new task.

**Lesson.** ADR-0032 section 6 already measures per-capability forgetting against the post-acquisition value (the Chaudhry measure, kept per capability rather than averaged) and against a single-capability system (intransigence). To be comparable with the literature, print the full a[i][j] matrix and BWT, and report per order. Standard baselines to include: sequential fine-tuning of LoRA (lower bound), LoRA with experience replay (strong and cheap), one LoRA per task with an oracle or learned task selector (the fair "parameter-isolation" upper bound, which by construction does not forget), O-LoRA, joint multi-task training (upper bound), and retrieval. Note the LoRA-per-task baseline: a memory that grows per capability is closer to that family than to a single shared adapter, so it is the comparison a reviewer will ask for. Also measure held-out general ability (the Biderman et al. trio or the M0 battery) after each step, since TRACE shows the worst losses are in abilities that were never part of the sequence.

### 1.5 External and parametric memories, retrieval, editing

| Reference | What the source says | Mark |
|---|---|---|
| Khandelwal et al. 2019, kNN-LM, arXiv 1911.00172 | Interpolating with nearest neighbours from a datastore: WikiText-103 perplexity 15.79, 2.9 better, no training | [V] |
| Wang et al. 2023, "kNN-LM Does Not Improve Open-ended Text Generation", arXiv 2305.14625 | Lower perplexity overall, but higher on most tokens, and no gain in generation quality | [V] |
| Geng et al. 2024, "Great Memory, Shallow Reasoning: Limits of kNN-LMs", arXiv 2408.11815 | Memory-type tasks mostly improve; reasoning tasks mostly fall (GSM8K 14.83→12.05 Llama-2-7B; 45.72→44.28 Llama-3-8B); with the answer forced into the neighbours NQ reaches 46.40 and HotpotQA 49.85 | [V] (HTML version) |
| Lewis et al. 2020, RAG, arXiv 2005.11401 | Retrieval-augmented generation, state of the art on three open-domain QA tasks | [V] |
| Ovadia et al. 2023, "Fine-Tuning or Retrieval?", arXiv 2312.05934 | RAG consistently beats unsupervised fine-tuning for injecting knowledge, existing or new | [V] |
| Lample et al. 2019, "Large Memory Layers with Product Keys", arXiv 1907.05242 | Sparse key-value layer up to a billion parameters; 12-layer model with memory beats a 24-layer baseline, about twice as fast | [V] |
| Berges et al. 2024, "Memory Layers at Scale", arXiv 2412.09764 | Trainable key-value layers, up to 128B memory parameters, trained jointly from scratch on 1T tokens; beat dense models with more than twice the compute, especially on factual tasks | [V] |
| Geva et al. 2020, "Transformer Feed-Forward Layers Are Key-Value Memories", arXiv 2012.14913 | Interpretation of feed-forward layers as key-value stores | [V] |
| Hartvigsen et al. 2022, GRACE, arXiv 2211.11031 | Discrete key-value adaptor on a frozen model for thousands of sequential edits | [V] |
| Wang et al. 2024, WISE, arXiv 2405.14768 | Side memory with routing and sharding for lifelong editing | [V] |
| Gupta et al. 2024, arXiv 2401.07453; Meng et al. ROME arXiv 2202.05262, MEMIT arXiv 2210.07229 | In-weight editing scales to thousands of facts but sequential edits lead to gradual then abrupt forgetting | [V] |
| Das et al. 2024, Larimar, arXiv 2403.11901 | Episodic memory attached to an LLM for one-shot updates | [V] |
| Cao et al. 2025, "Memory Decoder", arXiv 2508.09874 | A pretrained plug-in memory module for frozen Qwen and Llama models; average perplexity reduction 6.17 points over three domains | [V] |

**Lesson.** (i) The closest precedents for "frozen pretrained model + attached key-value memory" are GRACE/WISE (scope: facts and edits) and Memory Decoder (scope: domain perplexity, on Qwen). None of them claims gains in reasoning or code generation. (ii) Memory layers that do help broadly (Lample; Berges) are trained jointly with the backbone from scratch, which is not the ADR's setting. (iii) kNN-LM evidence says a look-up memory can lower loss while leaving generation and reasoning unchanged or worse: this is the documented version of the gap between component evidence (NLL) and model-level evidence that ADR-0032 Part B draws. (iv) Retrieval over the teaching data is a strong baseline for knowledge and must be in Tier 1 (it is). Memory Decoder and a kNN-LM over the same teaching data are the two memory baselines most directly comparable to S.

---

## 2. Statistical practice for "parity"

### 2.1 Sources

| Reference | What the source says | Mark |
|---|---|---|
| Miller 2024, "Adding Error Bars to Evals", arXiv 2411.00640 | Use paired standard errors wherever practicable (question-level scores of two models are positively correlated; correlations 0.37–0.64 in its illustrative table); sample-size formula n = (z_{α/2}+z_β)²(ω² + σ_A²/K_A + σ_B²/K_B)/δ²; worked example: about 969 questions to detect a 3-point difference at α=0.05, power 0.80; "should contain at least 1,000 questions"; clustered standard errors can be over 3x naive ones when items share a passage (DROP 3.05x); resampling each question K times or using next-token probabilities reduces variance; advises against lowering temperature to reduce variance | [V] (HTML version) |
| Madaan et al. 2024, "Quantifying Variance in Evaluation Benchmarks", arXiv 2406.10229 | Standard deviation across 10 training seeds of 7B models (percentage points): MMLU 0.57 (n=14,042), MMLU-cloze 0.22, HumanEval 1.11 (n=164), GSM8K 0.41 (n=1,319), ARC-Challenge 0.80 (n=1,165), HellaSwag 0.21 (n=10,042); per-model 95% CI from item sampling is larger: MMLU 0.72, HumanEval 3.98, GSM8K 0.87, ARC-C 2.74; continuous metrics have much higher signal-to-noise than discrete ones; item-response-theory subsets do not reduce variance meaningfully | [V] (HTML version). Note: these are low-accuracy from-scratch models; the seed is the training seed, which a frozen reference does not have |
| Card et al. 2020, "With Little Power Comes Great Responsibility", arXiv 2010.06595 | Underpowered NLP comparisons are common; a typical 2,000-sentence MT test set has about 75% power for 1 BLEU | [V] |
| Bowyer et al. 2025, "Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints", arXiv 2503.01747 | CLT error bars badly understate uncertainty on small sets; use exact or Bayesian intervals | [V] |
| Sclar et al. 2023, arXiv 2310.11324 | Formatting alone moves few-shot accuracy by up to 76 points (Llama-2-13B) | [V] |
| Alzahrani et al. 2024, arXiv 2402.01781 | Reordering choices or changing the answer-selection method shifts rankings by up to 8 positions | [V] |
| Atil et al. 2024, "Non-Determinism of 'Deterministic' LLM Settings", arXiv 2408.04667 | With settings meant to be deterministic, accuracy varied by up to 15% across runs for five (hosted) LLMs on eight tasks | [V] |
| Song et al. 2024, arXiv 2407.10457 | Greedy and sampled decoding give different scores; evaluations should report the decoding regime and its spread | [V] |
| Dutta et al. 2024, "Accuracy is Not All You Need", arXiv 2407.09141 | Item-level "flips" between a model and its quantised version: MMLU 8-bit 2.5–4.2%, 4-bit 5.7–10.9%; GSM8K 12–32%; accuracy change small | [V] (HTML version) |
| Polo et al. 2024, tinyBenchmarks, arXiv 2402.14992 | About 100 curated items estimate full-benchmark scores (fine for ranking; too few for a margin of a few points) | [V] |
| Biderman et al. 2024, "Lessons from the Trenches", arXiv 2405.14782 | Reproducibility practice for LM evaluation (the lm-evaluation-harness authors) | [V] |
| Tango 1998, Statistics in Medicine 17:891–908 | Score test and compatible confidence interval for the difference of paired proportions with a non-inferiority margin; McNemar's test is the special case of zero margin; valid with empty off-diagonal cells | [V] via search result summary and the copy at https://www.site.uottawa.ca/~nat/Courses/csi5388/Tango.paired.pdf (not read in full) |
| Fagerland, Lydersen, Laake 2014, Statistics in Medicine | Review of recommended tests and intervals for paired binomial proportions; implemented in R package `ratesci` (https://cran.r-project.org/package=ratesci) | [V] via search summary only |
| Dror et al. 2018, "The Hitchhiker's Guide to Testing Statistical Significance in NLP" (ACL); Koehn 2004 (paired bootstrap); Dietterich 1998 (McNemar for classifiers) | Standard NLP references for paired tests | [M] UNVERIFIED |
| Berger & Hsu 1996, Statistical Science (intersection–union tests) | A conjunction of per-endpoint tests each at level α has overall level α with no multiplicity correction | [M] UNVERIFIED |
| Walker & Nowacki 2011, J Gen Intern Med, "Understanding Equivalence and Noninferiority Testing"; FDA guidance on non-inferiority trials | Margin must be fixed in advance and justified; non-inferiority via a one-sided confidence bound against −δ | [M] UNVERIFIED |

### 2.2 What this implies for ADR-0032 section 4–5

1. **Test form.** The rule in section 5 (one-sided confidence bound of S − R above −δ, per domain, conjunction) is the textbook non-inferiority test combined as an intersection–union test. For binary item scores on the same items, use the paired form: Tango's score interval (exact-ish, handles small or zero discordant cells) or a paired bootstrap over items; a paired bootstrap over clusters where items share a passage or a template (Miller: naive errors can be 3x too small). Avoid CLT intervals on sets of a few hundred items (Bowyer et al.).
2. **No multiplicity correction is needed for the conjunction** (intersection–union) [M], but the conjunction's power is the product-like combination of the per-domain powers, so each domain needs high power on its own (finding 1 above).
3. **Sample sizes** [E], paired, one-sided α = 0.05, true difference zero, n ≈ k·d/δ² with k = 6.2 (80% power) or 11.5 (96% power, for a five-domain conjunction at about 80% overall):

   | discordant share d | δ = 1 pt | δ = 2 pt | δ = 3 pt | δ = 5 pt |
   |---|---|---|---|---|
   | 0.10, 80% power | 6,200 | 1,550 | 690 | 250 |
   | 0.20, 80% power | 12,400 | 3,100 | 1,380 | 500 |
   | 0.30, 80% power | 18,600 | 4,650 | 2,070 | 740 |
   | 0.20, 96% power | 23,000 | 5,750 | 2,560 | 920 |

   d must be measured, not assumed; M0 can measure it between each pair of references and between a model and itself under nuisance changes. Two very different systems that score the same (a small student with memory against a large teacher) can have d well above 0.3.
   Reading: a 1-point margin is out of reach of every public set except MMLU-size ones; 2–3 points needs 1.5–5 thousand items per domain; HumanEval+ and MBPP+ together (542 items) support roughly a 5–6 point margin.
4. **What "noise" M0 should measure**, each as its own number per domain and model: (a) item-sampling standard error (bootstrap); (b) repeat-run spread on the same stack with the same seed (expected zero; non-zero means non-determinism in the stack and must be found); (c) spread over sampling seeds if a non-greedy decoder is registered (the Qwen3.5 cards recommend sampling, see section 4); (d) spread over a small registered set of prompt formats and answer orders; (e) flips and score change between precisions (bf16, 8-bit, 4-bit) if any quantisation is to be used anywhere; (f) the pairwise discordant share d between references. δ fixed from (a)–(d) before any S score exists is consistent with the draft; fixing it from (b) alone would give a margin near zero that no finite test can meet.
5. **Variance reduction that is free**: paired analysis; continuous scoring where the task allows (log-likelihood of the correct option rather than argmax; Madaan et al. report far higher signal-to-noise); K samples per item when sampling.
6. **Item-level regressions** (section 5) should be read against the measured flip rate of a nuisance change (finding 3), otherwise ordinary churn will be read as regression.

---

## 3. Candidate evaluations per domain

Sizes and licences below are from the Hugging Face dataset API (`https://huggingface.co/api/datasets/<id>`) unless marked. "sha" is the dataset repository commit at the time of the check and is what a specification would pin. Runtime remarks are [E].

### 3.1 Reasoning

| Evaluation | Items | Licence | Fixed version | Notes |
|---|---|---|---|---|
| GSM8K (`openai/gsm8k`, config main) | test 1,319 (train 7,473) | MIT [V] | sha 740312ad… (last modified 2026-03-23) [V] | Needs generation (about 150–300 output tokens with reasoning). Heavily exposed: GSM1k (Zhang et al. 2024, arXiv 2405.00332 [V]) found drops of up to 8% on a fresh matched set for some models |
| BIG-Bench Hard (`lukaemon/bbh` mirror; source https://github.com/suzgunmirac/BIG-Bench-Hard) | 6,511 over 27 tasks (24×250, 187, 178, 146) [V] | MIT per the GitHub repository [V]; the HF mirror states no licence [V] | mirror sha 982bb89f… | Short answers; exact match. Large enough for a 2–3 point margin overall, not per task |
| ARC-Challenge (`allenai/ai2_arc`) | test 1,172 (train 1,119; val 299) | CC BY-SA 4.0 [V] | sha 210d026f… | Multiple choice; scorable by log-likelihood, fast |
| GSM-Symbolic (`apple/GSM-Symbolic`) | main, p1, p2 configs; counts not on the card [V]; 100 templates × 50 instances per the paper [M] | **CC BY-NC-ND 4.0** [V] | sha 93b5b375… | Research use permitted; **no derivatives**, so do not publish modified versions; templated variants show score variance and drops (Mirzadeh et al. 2024, arXiv 2410.05229 [V]) |
| LiveBench (https://github.com/LiveBench/LiveBench; arXiv 2406.19314 [V]) | 18 tasks in 6 categories; total not stated in README [V] | not stated in README text [V] — UNVERIFIED | Latest release listed 2025-04-25; only releases up to 2024-11-25 fully public [V] | README: "Local model inference is unmaintained", needs an OpenAI-compatible server [V]. Public questions now predate the candidate models, so its contamination limit no longer holds for them |

### 3.2 Coding, scored by execution

| Evaluation | Items | Licence | Fixed version | Notes |
|---|---|---|---|---|
| HumanEval (`openai/openai_humaneval`) | 164 | MIT [V] | sha 7dce6050… | Too small alone; certainly in training data |
| HumanEval+ (`evalplus/humanevalplus`) | 164 | Apache-2.0 [V] | sha d32357cf… | 80x more tests than HumanEval; lowers pass@k by 19–29% (Liu et al. 2023, arXiv 2305.01210 [V]) |
| MBPP+ (`evalplus/mbppplus`) | 378 (v0.2.0, down from 399) | Apache-2.0 [V] | sha b2d74c91… | 35x more tests [V] |
| MBPP (`google-research-datasets/mbpp`) | full: test 500, train 374, val 90, prompt 10; sanitized: test 257 | CC BY 4.0 [V] | sha 4bb6404f… | |
| BigCodeBench (`bigcode/bigcodebench`) | 1,140 (splits v0.1.0_hf … v0.1.4) | Apache-2.0 [V] | sha b74c0d0b…; pin the split name | Uses 139 libraries (arXiv 2406.15877 [V]); the execution image is large and counts against the download budget — size UNVERIFIED |
| LiveCodeBench (https://github.com/LiveCodeBench/LiveCodeBench; arXiv 2403.07974 [V]) | release_v1 400 … release_v5 880, release_v6 1,055 (May 2023–Apr 2025) [V] | not stated in README [V] — UNVERIFIED | pin release tag | Problems are dated, so a post-cutoff subset can be selected; whether a release later than v6 exists was not checked. Small models score near zero on the hard part, which gives a floor effect |
| CRUXEval (`cruxeval-org/cruxeval`; arXiv 2401.03065 [V]) | 800 functions, input and output prediction | MIT [V] | sha b96af045… | Scored by comparing predicted values, so no model-written program has to be executed for the output-prediction half — the lowest-risk "code understanding" measure |

Coding domain total available with licences confirmed: HumanEval+ 164 + MBPP+ 378 + BigCodeBench 1,140 + CRUXEval 800 ≈ 2,480 items, enough for a margin of about 3 points if pooled [E]; pooled analysis must cluster by benchmark.

### 3.3 Language understanding

| Evaluation | Items | Licence | Fixed version | Notes |
|---|---|---|---|---|
| SuperGLUE (`aps/super_glue`) validation splits | BoolQ 3,270; RTE 277; CB 56; COPA 100; WiC 638; MultiRC 4,848; ReCoRD 10,000; WSC 104 [V] | tagged "other" (per-task licences) [V] — check each task's own licence, UNVERIFIED | sha 3de24cf8… | Test labels are hidden; validation is used. BoolQ, MultiRC and ReCoRD share passages → clustered errors |
| MMLU (`cais/mmlu`, config all) | test 14,042; val 1,531; dev 285 | MIT [V] | sha c30699e8… | Knowledge-heavy; standard 4-choice format had near-chance, non-monotone behaviour for weak models in Madaan et al.; cloze scoring is steadier |
| MMLU-Pro (`TIGER-Lab/MMLU-Pro`) | test 12,032; val 70 | MIT [V] | sha b189ec76… (modified 2026-05-02; pin) | 10 options; the Qwen3.5-0.8B card reports 29.7 for that model without thinking [V], so small students are well above chance but far from ceiling |
| ANLI (`facebook/anli`) | test R1 1,000; R2 1,000; R3 1,200 | **CC BY-NC 4.0** [V] | sha 8e4813d8… | Adversarially collected; research use only |
| HellaSwag, WinoGrande | 10,042 val; 1,267 val [M] | MIT; CC BY [M] — UNVERIFIED | — | Used by Biderman et al. as "source-domain" forgetting probes [V] |

### 3.4 Generalisation (tasks and distributions absent from teaching)

Public options: GSM-Symbolic p1/p2 against GSM8K (same skill, shifted surface and added clauses); ANLI rounds; MBPP+ when teaching used HumanEval-style data and the reverse; BBH tasks held out by task; CRUXEval when teaching was code generation. The stronger design is structural: register, before teaching, which tasks and which template families are held out, and build the generalisation set from held-out **templates** (not just held-out instances) of the private generators in 3.6.

### 3.5 Knowledge retention

| Evaluation | Items | Licence | Fixed version | Notes |
|---|---|---|---|---|
| TOFU (`locuslab/TOFU`; arXiv 2401.06121 [V]) | 200 fictitious author profiles × 20 QA pairs = 4,000; plus real-author and world-facts control sets | MIT [V] | sha 324592d8… | Fictitious, so absent from every model's pretraining at the time of release (2024); public since then, so later models may have seen it. Good template for the private version |
| PopQA (`akariasai/PopQA`; source https://github.com/AlexTMallen/adaptive-retrieval) | about 14k entity questions [V] | HF card states none [V]; GitHub repository is MIT [V] | sha 098765c7… | Long-tail entities by popularity; small models fail the tail (see Kandpal et al. 2022, arXiv 2211.08411 [V]), which leaves room for a memory to help |
| zsRE / CounterFact (model-editing sets) | about 22k counterfactual records [M] | MIT [M] — UNVERIFIED | — | Standard for sequential-edit retention (ROME/MEMIT/GRACE/WISE) |

Retention in the ADR's sense (section 6) is measured on whatever was taught; these sets supply the taught material and the untaught controls.

### 3.6 Privately generated sets (recommended for every domain where one can be built)

Rationale: whether Qwen or GLM saw a public benchmark is unknowable; GSM1k and GSM-Symbolic show measurable inflation on the public versions [V]. Options, all generated from registered seeds by code written before any model is scored:

- **Reasoning**: own arithmetic-word-problem templates in the GSM-Symbolic manner (own templates, because Apple's are NC-ND); synthetic deduction or relational chains with controlled depth; algorithmic tasks (sorting, counting, base conversion) with exact answers. Thousands of items at no cost, so the sample-size problem of section 2 disappears.
- **Coding by execution**: generated function specifications with reference solutions and property or unit tests produced by the generator (the reference is executed to produce expected outputs; the model's code is then run in the sandbox). Cheaper and safer variant: CRUXEval-style output prediction on generated programs, scored by string comparison.
- **Language understanding**: hardest to generate without a model in the loop. Options: rule-generated entailment and minimal pairs (grammatical-acceptability pairs in the BLiMP manner [M]); or fresh human-written text published after all candidate models' release dates, with questions written by a person. Any model-written items must be validated against human or rule labels, as section 4 of the ADR already requires.
- **Knowledge retention**: fictitious entities and facts in the TOFU manner, generated privately. This is also the natural teaching material for M1–M3 and gives exact control of what was and was not taught.
- **Generalisation**: held-out template families of the generators above.
- Caveat to state in the specification: a private generated set measures a narrower construct than a human-written benchmark; report public and private scores side by side, never pooled.

### 3.7 Harness

- `lm-evaluation-harness` (EleutherAI; described in arXiv 2405.14782 [V]) carries most of the public tasks above with fixed prompts; pin a commit. EvalPlus (https://github.com/evalplus/evalplus) supports `hf`, `vllm`, `openai`-compatible and `ollama` backends and documents generation on the host with execution inside its Docker image [V]. An OpenAI-compatible local server (llama.cpp server or `mlx_lm.server`) is the common denominator for EvalPlus, LiveBench and LiveCodeBench.
- UNVERIFIED [M]: mlx-lm ships an `mlx_lm.evaluate` command wrapping lm-evaluation-harness; lm-evaluation-harness accepts `--device mps`.

---

## 4. Candidate exact model versions and licences

All figures in this section are from the Hugging Face model API (`https://huggingface.co/api/models/<id>?blobs=true`) and the raw model cards and LICENSE files, fetched 2026-11-20 [V] unless marked. "Download" is the sum of weight shards at the published precision (decimal GB); tokenizer and config files add a few MB. **I read the licence tag and card statement for the Qwen models but did not open the LICENSE file in each Qwen repository; I opened the LICENSE file for `GLM-4-9B-0414` and `glm-4-9b-chat`.**

### 4.1 Small Qwen students

| Model | Parameters | Download | Licence tag | Commit (sha) | Notes |
|---|---|---|---|---|---|
| `Qwen/Qwen2.5-0.5B-Instruct` | 494,032,768 | 0.99 GB | apache-2.0 | 7ae55760… (2024-09-25) | Text-only, no thinking mode; most mature tooling |
| `Qwen/Qwen2.5-1.5B-Instruct` | 1,543,714,304 | 3.09 GB | apache-2.0 | 989aa798… (2024-09-25) | |
| `Qwen/Qwen3-0.6B` | 751,632,384 | 1.50 GB | apache-2.0 | c1899de2… (2025-07-26) | Text-only; has a thinking mode [M] |
| `Qwen/Qwen3-1.7B` | 2,031,739,904 | 4.06 GB | apache-2.0 | 70d244cc… (2025-07-26) | Above the 1.5B end of the stated range by parameter count |
| `Qwen/Qwen3.5-0.8B` | 873,438,784 | 1.75 GB | apache-2.0 | 2fc06364… (2026-03-02) | **Multimodal** ("Causal Language Model with Vision Encoder"); non-thinking by default; card warns it is "more prone to entering thinking loops" in thinking mode; card needs "the latest transformers" from main; card's stated uses include "task-specific fine-tuning, and other research" |
| `Qwen/Qwen3.5-2B` | 2,274,069,824 | 4.55 GB | apache-2.0 | 15852e8c… (2026-03-02) | Multimodal; above the stated range |

Base (not chat-tuned) variants `Qwen3.5-0.8B-Base` and `Qwen3.5-2B-Base` exist and are tagged apache-2.0 in the organisation listing [V]; sizes not fetched.

### 4.2 Larger Qwen teachers that fit in 48 GB

| Model | Parameters | Download | Licence tag | Commit | Fits? [E] |
|---|---|---|---|---|---|
| `Qwen/Qwen2.5-7B-Instruct` | 7,615,616,512 | 15.23 GB | apache-2.0 | a09a3545… (2025-01-12) | bf16 about 15 GB in memory: yes |
| `Qwen/Qwen3-8B` | 8,190,735,360 | 16.38 GB | apache-2.0 | b968826d… (2025-07-26) | yes |
| `Qwen/Qwen3.5-9B` | 9,653,104,368 | 19.31 GB | apache-2.0 | c2022362… (2026-03-02) | yes at bf16; multimodal; **thinking on by default**; context 262,144; card says `/think` `/nothink` soft switches are not supported, thinking is disabled through `enable_thinking=False` in the chat template; needs transformers from main per the card |
| `Qwen/Qwen3-14B` | 14,768,307,200 | 29.54 GB | apache-2.0 | 40c06982… (2025-07-26) | bf16 fits memory (about 30 GB) but leaves little of the 50 GB download budget |
| `Qwen/Qwen3.5-27B` | 27,781,427,952 | 55.56 GB | apache-2.0 | 81a287ca… (**modified 2026-11-20**, the day of this check) | Over the download budget at published precision; a 4-bit conversion would fit memory. Repository still changing: pin the sha |

Official Qwen GGUF example: `Qwen/Qwen2.5-7B-Instruct-GGUF` (apache-2.0, sha bb5d59e0…): q4_k_m 4.68 GB, q8_0 8.10 GB, fp16 15.24 GB [V]. Newer families listed in the organisation (Qwen3.6-27B, Qwen3.6-35B-A3B, Qwen3.8-27B apache-2.0; Qwen3.8-Flash-Next and Qwen3.8-2.4T-A95B tagged "other") are all too large for the budget at published precision [V: listing only; sizes not fetched for these].

From memory, UNVERIFIED: `Qwen2.5-3B-Instruct` carries a non-commercial "qwen-research" licence and `Qwen2.5-72B-Instruct` the "qwen" licence, unlike the rest of Qwen2.5; the Qwen3 cards advise against greedy decoding in thinking mode. The Qwen3.5 cards [V] recommend sampling for all modes (for example temperature 0.7, top_p 0.8, top_k 20 for non-thinking general use on the 9B; temperature 1.0 on the 0.8B text setting), which matters for the "run-to-run noise" definition in M0: a registered decoding regime is needed, and greedy decoding departs from the vendor's recommendation.

### 4.3 Open-weight GLM-family models (organisation `zai-org` on Hugging Face; formerly THUDM)

| Model | Parameters | Download | Licence | Commit | Notes |
|---|---|---|---|---|---|
| `zai-org/GLM-4-9B-0414` | 9,400,279,040 | 18.80 GB | **MIT**; LICENSE file reads "MIT License, Copyright (c) 2025 Zhipu AI", standard text | 645b8482… (2025-04-14) | The card is shared with the 32B models and gives **no benchmark numbers for the 9B model**; shows a function-calling example with it; mentions Transformers, vLLM, SGLang |
| `zai-org/GLM-Z1-9B-0414` | 9,400,279,040 | 18.80 GB | MIT (tag) | b221b06f… (2025-04-28) | Reasoning ("thinking") variant; card claims strength in mathematical reasoning, no numbers |
| `zai-org/GLM-4-32B-0414`, `GLM-Z1-32B-0414` | about 32B | 65.13 GB (GLM-4-32B) | MIT (tag) | — | Over the download budget at published precision |
| `zai-org/GLM-4.7-Flash` | 31,221,488,576 (`glm4_moe_lite`) | 62.44 GB | MIT (tag) | 7dd20894… (2026-01-29) | Over the download budget at published precision |
| `zai-org/glm-4-9b-chat`, `glm-4-9b`, `-hf` variants, `glm-4-9b-chat-1m` | about 9B | not fetched | "other": custom **glm-4 licence** | — | See clause below |
| `zai-org/glm-edge-1.5b-chat` | 1,593,427,968 | 3.19 GB | "other", `license_name: glm-4` | 7b201d3c… (2024-11-28) | A GLM model in the student size range, same custom licence; `glm-edge-4b-chat` also listed, not fetched |
| `zai-org/GLM-4.5`, `-Air`, `GLM-4.6`, `GLM-4.7`, `GLM-5`, `GLM-5.1`, `GLM-5.2` | far larger | not fetched | MIT (tag) | — | Not feasible locally |
| `zai-org/GLM-5.3`, `GLM-5.3-BF16` | not fetched | **"other"** — terms not read, UNVERIFIED | — | — |
| `zai-org/GLM-5.3-Flash` | 321,323,031,390 | about 328 GB | MIT (tag) | 46a050be… (2026-10-15) | Not feasible locally |

**Licence clauses relevant to training another system on model outputs.**
- MIT (GLM-4-9B-0414, GLM-Z1-9B-0414) and Apache-2.0 (Qwen candidates): neither contains any restriction on the use of outputs; both permit use, modification and distribution, with notice retention. Research use and distillation from outputs are not restricted by the licence text. [V for the MIT file; Apache-2.0 by tag and card statement only]
- glm-4 licence (`glm-4-9b-chat` LICENSE file) [V, through a summariser; re-read before relying on it]: grants a "non-exclusive, worldwide, non-transferable, non-sublicensable, revocable, royalty-free copyright license"; "This license allows you to use all open source models in this repository for free for academic research"; commercial use requires registration; distributed products must display "Built with glm-4"; and for AI models created, trained, fine-tuned or otherwise improved using the materials, "you should also add "glm-4" to the beginning of any such AI model name". It contains no explicit ban on distillation, but the naming clause plausibly reaches a student trained on that model's outputs. It also bars military or illegal use and is governed by PRC law (Haidian District court, Beijing).
- Not checked: terms of service of the hosted APIs (Z.ai / Zhipu, Alibaba Model Studio). They are irrelevant if weights are run locally, and would need reading if any hosted model were used as a teacher.
- This is a reading of licence texts, not legal advice.

### 4.4 Sets that fit the 50 GB download budget at published precision [E, from the sizes above]

| Set | Student(s) | Qwen teacher | GLM teacher | Total |
|---|---|---|---|---|
| A (2025 generation, text-only) | Qwen3-0.6B 1.50 + Qwen3-1.7B 4.06 | Qwen3-8B 16.38 | GLM-4-9B-0414 18.80 | 40.7 GB |
| B (most mature tooling, no thinking mode) | Qwen2.5-0.5B 0.99 + Qwen2.5-1.5B 3.09 | Qwen2.5-7B 15.23 | GLM-4-9B-0414 18.80 | 38.1 GB |
| C (newest small Qwen) | Qwen3.5-0.8B 1.75 + Qwen3.5-2B 4.55 | Qwen3.5-9B 19.31 | GLM-4-9B-0414 18.80 | 44.4 GB |

Datasets in section 3 add well under 1 GB together [E]; a code-execution container image adds an unknown amount (UNVERIFIED) and must be counted. Remarks:
- Set B is the conservative choice: text-only, no thinking mode to register, supported everywhere, and both teachers are 2024–early-2025 models of similar class. Its weakness is age (weaker teachers).
- In Set C the Qwen teacher (2026) is a generation newer than the only feasible GLM teacher (April 2025). The risk that the Qwen teacher is ahead in every domain, making section 7 NOT EVALUABLE, is highest here. GLM-Z1-9B-0414 as the GLM teacher (reasoning-tuned) is one way to obtain a teacher with a different profile; whether it actually differs is an M0 measurement, not something the cards establish.
- A same-family student and teacher (Qwen/Qwen) share a tokenizer and training lineage; the GLM teacher does not. Output-level (text) distillation is unaffected; any logit-level method would need tokenizer alignment (as FuseLLM had to do [M]).
- Thinking mode must be registered per model (on/off, token budget). It changes scores, run time (5–20x more output tokens [E]) and, for the 0.8B, stability (the card's loop warning [V]).

---

## 5. Feasibility on the stated machine (Apple silicon, 18 CPU cores, 48 GB unified memory, MPS, no CUDA)

### 5.1 Inference stacks

| Stack | Support for these models | Remarks |
|---|---|---|
| **MLX / mlx-lm** (https://github.com/ml-explore/mlx-lm) | Model code directories present for `glm4`, `glm4_moe`, `glm4_moe_lite`, `qwen2`, `qwen3`, `qwen3_5`, `qwen3_moe` and others [V, GitHub contents API]. Community conversions exist: `mlx-community/GLM-4-9B-0414-{4bit,6bit,8bit,bf16}`, `mlx-community/Qwen3.5-9B-{4bit,…,8bit,bf16}` [V, listing] | README: quantise with `mlx_lm.convert -q`; LoRA and full fine-tuning supported, including on quantised models; batch generation example; wired-memory note for models large relative to RAM (macOS 15+) [V]. Converting locally from the official repository keeps provenance clean; community conversions are third-party artefacts whose fidelity is unverified |
| **llama.cpp (Metal)** | GGUF conversions: official for Qwen2.5 (`Qwen/Qwen2.5-7B-Instruct-GGUF`) [V]; community for GLM-4-9B-0414 (`bartowski/THUDM_GLM-4-9B-0414-GGUF`, `lmstudio-community/GLM-4-9B-0414-GGUF`) [V, listing]. A repository named `…GLM-4-9B-0414-GGUF-fixed` exists, which suggests early conversions had a defect — details UNVERIFIED | Fast and deterministic for inference; no practical way to attach a learned memory or read hidden states, so it suits M0 only. Using it for M0 and another stack for M1 would confound the S-versus-reference comparison with a stack change (finding 3) |
| **PyTorch MPS + transformers** | Works for all of them in principle; Qwen3.5 cards require transformers from the main branch [V], which conflicts with a locked environment (`uv.lock` unchanged) unless run through `uv run --with` | Slowest of the three for generation [M]; some operators fall back to CPU [M]; bitsandbytes 4/8-bit quantisation is CUDA-only [M] — all three UNVERIFIED in this session. Its advantage: it is where an ArborLM memory would be attached with gradients, so M1 onward likely lives here or in MLX |

Recommendation for the specification to consider: choose the stack that M1 will use (PyTorch MPS or MLX) and measure the references on that same stack and precision in M0; use llama.cpp only as a cross-check of the reference scores. Run every model at bf16 (all candidates ≤ 9.65B fit: at most about 19 GB) so that no quantisation enters the comparison; if anything is quantised, everything is, by the same method.

### 5.2 Memory [E]

bf16 weights need about 2 bytes per parameter: 0.5–2B students 1–4.5 GB; 7–9.65B teachers 15–19.5 GB. One teacher plus one student at bf16 with caches fits in 48 GB; two 9B teachers at bf16 loaded at once (about 38 GB) does not leave safe headroom next to other work, so run them one at a time. Measurements already running on the machine reduce this further.

### 5.3 Throughput, order of magnitude

Source: llama.cpp discussion "Performance of llama.cpp on Apple Silicon M-series" (https://github.com/ggml-org/llama.cpp/discussions/4167) [V], Llama 7B at Q4_0: M5 Pro (16 GPU cores) 1,340 tokens/s prompt processing and 67.6 tokens/s generation; M5 Pro (20 GPU cores) 1,621 and 66.3; M4 Pro about 364–440 and 50; M5 Max (40) 3,220 and 120. The M5/M6 rows were measured at a later llama.cpp commit than M1–M4 and are not strictly comparable. Which chip the project machine has was not checked by me; "18 cores, 48 GB" is consistent with a Pro-class chip.

Estimates from those figures for one 7–9B model at 4-bit on a Pro-class M5, single stream [E]: 
- Multiple-choice by log-likelihood (MMLU-Pro 12,032 items × about 250 prompt tokens ≈ 3M tokens): about 30–40 minutes; 5-shot MMLU (about 7M tokens): about 1.5 hours.
- GSM8K with visible reasoning (1,319 × about 250 output tokens): about 1.5 hours; BBH 6,511 short answers: 1–2 hours.
- HumanEval+ and MBPP+ (542 × about 200 output tokens): about 30 minutes generation plus test execution; BigCodeBench 1,140: 1–2 hours plus execution.
- bf16 instead of 4-bit: generation is memory-bandwidth bound, so expect roughly 2–4x slower [E, UNVERIFIED]. Thinking mode: 5–20x more output tokens. Students of 0.5–2B: several times faster than the teachers.
- Whole battery (about 25–30 thousand items across domains, including private sets) for four models, no thinking, bf16: on the order of 1–3 days of machine time if run alone; with K repeated samples or several prompt formats, multiply accordingly. Batched generation (mlx-lm, or llama.cpp server with parallel slots) can cut this severalfold. These are planning numbers; M0's own rehearsal should measure them.

### 5.4 Running generated code safely

- The HumanEval repository states: "This program exists to run untrusted model-generated code. Users are strongly encouraged not to do so outside of a robust security sandbox", and ships with the execution call commented out for that reason (https://github.com/openai/human-eval) [V]. HumanEval's in-process guards are not a security boundary [M].
- EvalPlus documents generation on the host and execution inside its Docker image `ganler/evalplus` [V]. LiveCodeBench's README has no safety warning but executes model code with timeouts [V]; time limits cause "slight (< 0.5) points of variation" there [V], so pin process counts and timeouts.
- So yes: a container or VM is needed. On this machine the options are: Apple's `container` tool (https://github.com/apple/container; Linux containers as lightweight virtual machines; requires Apple silicon and macOS 26 or later [V]; the machine reports Darwin 27, so it qualifies), or Docker Desktop / Colima / Podman with a Linux VM [M]. Registered settings should include: no network, non-root user, read-only root filesystem with a size-limited scratch directory, CPU, memory, process and wall-time limits, no host mounts other than the per-task input, and a fresh container per batch. macOS `sandbox-exec` is deprecated and should not be relied on [M, UNVERIFIED].
- Pulling a container image is a download and counts against the 50 GB budget and the approval rule. Image digests should be pinned like dataset shas.
- Generation and execution can be separated in time: generate all completions first (GPU-bound), store them, execute later in the sandbox (CPU-bound). That also makes the scoring step re-runnable from stored records.
- CRUXEval-style output prediction and the private "predict the output" variant need no execution of model-written code.

---

## 6. Points the M0 specification may need to settle that the draft does not yet mention

1. The decoding regime per model (greedy versus the vendor's recommended sampling; thinking on or off; output-token cap), because it defines what "run-to-run noise" is.
2. One stack and one numeric precision for every system in a comparison; flips under precision change measured, not assumed.
3. δ derived from item-sampling error and registered nuisance spreads, with the per-domain item count chosen from a power calculation for the conjunction (section 2.2), using the measured discordant share.
4. Per-domain minimum item counts; pooled public sets analysed with clustering by benchmark and by shared passage or template.
5. What is registered if the two teachers do not differ in M0 (for example: stop, or substitute GLM-Z1-9B-0414, decided in advance).
6. A floor and ceiling rule: a domain where a reference is near chance or near 100% cannot show non-inferiority meaningfully and should be labelled NOT EVALUABLE in advance by rule.
7. Dataset shas, model shas, harness commit, container image digest and chat-template text all recorded; `Qwen3.5-27B` changed on the day of this check, which shows upstream repositories do move.
8. Additional baselines suggested by the literature for later tests (not M0): supervised fine-tuning with ground-truth labels on the teaching data; one adapter per capability with a task selector; kNN-LM and Memory Decoder over the same teaching data; learned per-item router and best-teacher-sampled-k-times for the two-teacher test.

## 7. What was not done or could not be confirmed

- No full papers were read end to end; numbers come from abstracts and from machine-summarised HTML versions of seven papers (2406.10229, 2411.00640, 2407.09141, 2402.04616, 2403.12031, 2401.10491, 2408.11815, 2405.09673). PDF fetches failed to parse; the HTML versions were used instead.
- Items marked [M] were not re-fetched: Hinton et al. 2015; You et al. 2017; EWC; the exact BWT/FWT/forgetting formulas; Dror et al. 2018; Koehn 2004; Dietterich 1998; Berger & Hsu 1996; Walker & Nowacki 2011; HellaSwag/WinoGrande/CounterFact sizes and licences; GSM-Symbolic instance counts; Qwen2.5-3B/72B licence exceptions; Qwen3 greedy-decoding advice; bitsandbytes and MPS behaviour; `mlx_lm.evaluate`; `sandbox-exec`.
- Licences not confirmed: LiveBench, LiveCodeBench (README states none); SuperGLUE per-task licences; `GLM-5.3` ("other"); the LICENSE files inside the Qwen repositories (tags and card statements only).
- Not checked: size of any code-execution container image; whether LiveCodeBench has a release after v6; the precise chip of the project machine; published benchmark scores of GLM-4-9B-0414 against Qwen models of the same size (the card has none).
- No model, dataset or image was downloaded; no measurement was run; throughput and run-time figures are estimates from a third-party table.
