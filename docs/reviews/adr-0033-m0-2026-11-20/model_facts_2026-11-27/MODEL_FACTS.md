# Model facts re-read at source: set A (Qwen3) versus set B (Qwen2.5), plus GLM-4-9B-0414

All sources read on **2026-11-27**. Web reading only; no model file, dataset or package was downloaded.

## 0. Method and its limits

- Sources read: the Hugging Face model API record for each repository (`/api/models/<id>?blobs=true`: creation date, licence tag, file list with byte sizes, safetensors parameter count), each repository's raw `README.md`, `LICENSE`, `config.json`, `generation_config.json`, `tokenizer_config.json` (or `chat_template.jinja`), the Qwen release blogs, the `transformers` GitHub release records and tagged source files.
- **Limit of the reading tool.** Pages were read through a fetch tool that passes the page to a small summarising model and returns its answer. Numbers and short quotes below are as that tool returned them; I did not see the raw bytes of any page. File sizes for one repository (Qwen2.5-7B-Instruct) were read twice from two endpoints and agreed. Anything load-bearing should be re-checked by opening the URL directly.
- Nothing was load-tested. Every statement that a version "loads" a model is from release notes, tagged source and the cards, not from running code.
- No recommendation is made.

## 1. Per-model facts

URL pattern for each model `<id>`:
- card: `https://huggingface.co/<id>` ; raw card: `https://huggingface.co/<id>/raw/main/README.md`
- API record (dates, files, sizes, parameter count): `https://huggingface.co/api/models/<id>?blobs=true`
- files: `https://huggingface.co/<id>/raw/main/{LICENSE,config.json,generation_config.json,tokenizer_config.json}`

### 1.1 `Qwen/Qwen2.5-0.5B-Instruct` (set B)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2024-09-16T11:52:46Z; last modified 2024-09-25. Publisher blog dated 2024-09-19. Card citation: September 2024. | API record; https://qwenlm.github.io/blog/qwen2.5/ |
| 2 | Licence | Card tag `apache-2.0`, `license_link` to the repository LICENSE. LICENSE file exists (11,343 bytes): Apache License 2.0, "Copyright 2024 Alibaba Cloud", no extra clauses found. Blog: all open models except 3B and 72B are Apache 2.0. | API record; LICENSE; blog |
| 3 | Loading | `trust_remote_code` not mentioned on the card. `config.json`: `model_type: qwen2`, `Qwen2ForCausalLM` (built-in). Card: with `transformers<4.37.0` you get `KeyError: 'qwen2'`; "advise ... latest version". | raw card; API record |
| 4 | Thinking mode | None mentioned on the card; `enable_thinking` does not appear in the chat template. | raw card; tokenizer_config.json |
| 5 | Default system message | **Yes.** Template inserts "You are Qwen, created by Alibaba Cloud. You are a helpful assistant." when the first message is not a system message (both with and without tools). | tokenizer_config.json |
| 6 | Size | Card: 0.49B parameters (0.36B non-embedding). API safetensors count: 494,032,768, BF16. `model.safetensors` 988,097,824 bytes. | raw card; API record |
| 7 | Generation settings | Card gives no sampling recommendation and no greedy warning (example sets only `max_new_tokens=512`). `generation_config.json`: `do_sample: true`, `temperature: 0.7`, `top_p: 0.8`, `top_k: 20`, `repetition_penalty: 1.1`, `transformers_version: 4.37.0`. | raw card; generation_config.json |

### 1.2 `Qwen/Qwen2.5-1.5B-Instruct` (set B)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2024-09-17T14:10:29Z; last modified 2024-09-25. Blog 2024-09-19. | API record; blog |
| 2 | Licence | Card tag `apache-2.0` with `license_link`. LICENSE file exists (11,343 bytes, same size as the 0.5B file; its text was not read separately). | API record |
| 3 | Loading | `trust_remote_code` not mentioned. `qwen2` / `Qwen2ForCausalLM`. Card: `transformers<4.37.0` gives `KeyError: 'qwen2'`. | raw card; API record |
| 4 | Thinking mode | None; `enable_thinking` absent from the template. | raw card; tokenizer_config.json |
| 5 | Default system message | **Yes**, same sentence as 1.1. | tokenizer_config.json |
| 6 | Size | Card: 1.54B (1.31B non-embedding). API: 1,543,714,304, BF16. `model.safetensors` 3,087,467,144 bytes. | raw card; API record |
| 7 | Generation settings | No recommendation, no greedy warning on the card. `generation_config.json`: `do_sample: true`, `temperature: 0.7`, `top_p: 0.8`, `top_k: 20`, `repetition_penalty: 1.1`. | raw card; generation_config.json |

### 1.3 `Qwen/Qwen2.5-7B-Instruct` (set B)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2024-09-16T11:55:40Z; last modified 2025-01-12. Blog 2024-09-19. | API record; blog |
| 2 | Licence | Card tag `apache-2.0` with `license_link`. LICENSE file exists (11,343 bytes; text not read separately). | API record |
| 3 | Loading | `trust_remote_code` not mentioned. `qwen2` / `Qwen2ForCausalLM`; `config.json` `transformers_version: 4.43.1`. Card: `transformers<4.37.0` gives `KeyError: 'qwen2'`. | raw card; config.json |
| 4 | Thinking mode | None; `enable_thinking` absent from the template. | raw card; tokenizer_config.json |
| 5 | Default system message | **Yes**, same sentence as 1.1. | tokenizer_config.json |
| 6 | Size | Card: 7.61B (6.53B non-embedding). API: 7,615,616,512, BF16; `config.json` `torch_dtype: bfloat16`. Four shards: 3,945,441,440 + 3,864,726,352 + 3,864,726,424 + 3,556,377,672 = **15,231,271,888 bytes**. | raw card; API record; `/api/models/Qwen/Qwen2.5-7B-Instruct/tree/main` |
| 7 | Generation settings | No recommendation, no greedy warning on the card. `generation_config.json`: `do_sample: true`, `temperature: 0.7`, `top_p: 0.8`, `top_k: 20`, `repetition_penalty: 1.05`. | raw card; generation_config.json |

### 1.4 `Qwen/Qwen3-0.6B` (set A)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2025-04-27T03:40:08Z; last modified 2025-07-26. Publisher blog dated 2025-04-29. | API record; https://qwenlm.github.io/blog/qwen3/ |
| 2 | Licence | Card tag `apache-2.0` with `license_link`. LICENSE file exists (11,343 bytes): Apache License 2.0, "Copyright 2024 Alibaba Cloud", no extra clauses found. Blog: the dense models are "under Apache 2.0 license". | API record; LICENSE; blog |
| 3 | Loading | `trust_remote_code` not mentioned. `model_type: qwen3`, `Qwen3ForCausalLM` (built-in, a new class, not Qwen2's). Card: with `transformers<4.51.0` you get `KeyError: 'qwen3'`; "advise ... latest version". | raw card; API record |
| 4 | Thinking mode | **Yes, on by default** ("By default, Qwen3 has thinking capabilities enabled"; `enable_thinking` "Default is True"). Off: pass `enable_thinking=False` to `tokenizer.apply_chat_template` (the "hard switch"); the template then appends an empty `<think>\n\n</think>\n\n` block after the assistant prompt. Soft switch: `/think` and `/no_think` in a user or system message, valid only while `enable_thinking=True`; the card says they are "not valid" when it is False, and that with the soft switch a `<think>` block is still emitted (possibly empty). **Different sampling per mode:** thinking `Temperature=0.6, TopP=0.95, TopK=20, MinP=0`; non-thinking `Temperature=0.7, TopP=0.8, TopK=20, MinP=0`. | raw card; tokenizer_config.json |
| 5 | Default system message | **No.** The template writes a system block only if the first message is a system message or tools are given. "You are Qwen, created by Alibaba Cloud" does not appear. | tokenizer_config.json |
| 6 | Size | Card: 0.6B parameters (0.44B non-embedding). API safetensors count: **751,632,384**, BF16 (the card's figure and the API count differ; reported as found). `model.safetensors` 1,503,300,328 bytes. | raw card; API record |
| 7 | Generation settings | **Greedy warning present**, in the thinking-mode bullet only: "DO NOT use greedy decoding, as it can lead to performance degradation and endless repetitions." The non-thinking bullet says "we suggest using" the values above and carries no greedy warning. `presence_penalty` 0 to 2 may be adjusted against repetition (1.5 suggested if significant). `generation_config.json` holds the *thinking-mode* values: `do_sample: true`, `temperature: 0.6`, `top_p: 0.95`, `top_k: 20`, `transformers_version: 4.51.0`. | raw card; generation_config.json |

### 1.5 `Qwen/Qwen3-1.7B` (set A)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2025-04-27T03:41:05Z; last modified 2025-07-26. Blog 2025-04-29. | API record; blog |
| 2 | Licence | Card tag `apache-2.0` with `license_link`. LICENSE file exists (11,343 bytes; text not read separately). | API record |
| 3 | Loading | As 1.4: no `trust_remote_code`; `qwen3` / `Qwen3ForCausalLM`; `transformers<4.51.0` gives `KeyError: 'qwen3'`. | raw card; API record |
| 4 | Thinking mode | As 1.4 (on by default; `enable_thinking=False`; `/think`, `/no_think`; same two sampling sets). Template condition `enable_thinking is defined and enable_thinking is false` emits the empty think block. | raw card; tokenizer_config.json |
| 5 | Default system message | **No.** | tokenizer_config.json |
| 6 | Size | Card: 1.7B (1.4B non-embedding). API: 2,031,739,904, BF16. Two shards: 3,441,185,608 + 622,329,984 = **4,063,515,592 bytes**. | raw card; API record |
| 7 | Generation settings | Same greedy warning as 1.4. `generation_config.json`: `do_sample: true`, `temperature: 0.6`, `top_p: 0.95`, `top_k: 20`. | raw card; generation_config.json |

### 1.6 `Qwen/Qwen3-8B` (set A)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2025-04-27T03:42:21Z; last modified 2025-07-26. Blog 2025-04-29. | API record; blog |
| 2 | Licence | Card tag `apache-2.0` with `license_link`. LICENSE file exists (11,343 bytes; text not read separately). | API record |
| 3 | Loading | As 1.4. `config.json`: `model_type: qwen3`, `Qwen3ForCausalLM`, `transformers_version: 4.51.0`. Card also says to upgrade to `transformers>=4.51.0` in its long-context (YaRN) note. | raw card; config.json |
| 4 | Thinking mode | As 1.4; the card calls `enable_thinking=False` a "hard switch". | raw card; tokenizer_config.json |
| 5 | Default system message | **No.** | tokenizer_config.json |
| 6 | Size | Card: 8.2B (6.95B non-embedding). API: 8,190,735,360, BF16; `config.json` `torch_dtype: bfloat16`. Five shards: 3,996,250,744 + 3,993,160,032 + 3,959,604,768 + 3,187,841,392 + 1,244,659,840 = **16,381,516,776 bytes**. | raw card; API record |
| 7 | Generation settings | Same greedy warning as 1.4, stated for thinking mode. `generation_config.json`: `do_sample: true`, `temperature: 0.6`, `top_p: 0.95`, `top_k: 20`. | raw card; generation_config.json |

### 1.7 `zai-org/GLM-4-9B-0414` (both sets)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | Release date | Repository created 2025-04-07T11:57:02Z ("initial commit"); seven commits, the last on 2025-04-14T15:40:17Z. The card states no date; "0414" is in the name. The publisher's own announcement was not read. | API record; `https://huggingface.co/api/models/zai-org/GLM-4-9B-0414/commits/main` |
| 2 | Licence | Card tag `mit` (no `license_link`). LICENSE file exists (1,064 bytes): MIT License, "Copyright (c) 2025 Zhipu AI". **No naming, attribution or use clause was found beyond the standard MIT notice requirement**, in the LICENSE or in the card body. | API record; LICENSE; raw card |
| 3 | Loading | `trust_remote_code` not mentioned; card example uses `AutoTokenizer` and `AutoModelForCausalLM.from_pretrained(MODEL_PATH, device_map="auto")`. `config.json`: `model_type: glm4`, `Glm4ForCausalLM` (built-in), `transformers_version: 4.52.0.dev0`. **The card states no minimum `transformers` version** (install line is `pip install -U transformers accelerate`). The file list has no `.py` file. | raw card; rendered card; config.json; API record |
| 4 | Thinking mode | None described for this checkpoint; reasoning is attributed to the sibling GLM-Z1 models. The chat template has no thinking variable. | raw card; chat_template.jinja |
| 5 | Default system message | **No.** Template always begins `[gMASK]<sop>`; a `<|system|>` block appears only when a system message or tools are supplied. (The card's examples build a tools system prompt and a Chinese search-answer system prompt; neither is a default.) | chat_template.jinja; raw card |
| 6 | Size | Card body gives no parameter count for this checkpoint; the rendered page shows "9B params", BF16. API: 9,400,279,040, BF16; `config.json` `torch_dtype: bfloat16`. Four shards: 4,984,283,160 + 4,895,274,600 + 4,895,274,616 + 4,025,786,080 = **18,800,618,456 bytes**. | rendered card; API record; config.json |
| 7 | Generation settings | No temperature or top-p recommendation and no greedy warning. The tool-calling example passes `do_sample: True`, `max_new_tokens: 1024`. `generation_config.json` holds only `eos_token_id: [151329, 151336, 151338]`, `pad_token_id: 151329`, `transformers_version: 4.52.0.dev0` (no sampling keys). | raw card; generation_config.json |

## 2. The `transformers` library

| Question | Finding | Source |
|---|---|---|
| Qwen3 support | Added in **v4.51.0**, published 2025-04-05: "The Qwen3 architecture has been contributed to transformers and is available in v4.51.0" (weights were not yet released then). It is a **new model class**, not Qwen2's: `src/transformers/models/qwen3/modeling_qwen3.py` at tag v4.51.0 defines `Qwen3Model`, `Qwen3ForCausalLM` and others, generated from `modular_qwen3.py`. | https://github.com/huggingface/transformers/releases/tag/v4.51.0 ; https://raw.githubusercontent.com/huggingface/transformers/v4.51.0/src/transformers/models/qwen3/modeling_qwen3.py |
| GLM-4-0414 support | Added in **v4.51.3**, published 2025-04-14T15:51:52Z ("Patch release v4.51.3"): "very exceptionally, we diverge from semantic versioning to merge GLM-4 in this patch release"; item "Add glm4 (#37388)". Classes `Glm4Model`, `Glm4ForCausalLM` in `models/glm4/modeling_glm4.py` at tag v4.51.3; the same path at tag v4.51.2 returns 404. The older `glm` type (`GlmForCausalLM`, for `glm-4-9b-chat`) is a different class and config type. | https://github.com/huggingface/transformers/releases/tag/v4.51.3 ; https://raw.githubusercontent.com/huggingface/transformers/v4.51.3/src/transformers/models/glm4/modeling_glm4.py |
| Qwen2 (for Qwen2.5) | Added in v4.37.0, published 2024-01-22. | https://github.com/huggingface/transformers/releases/tag/v4.37.0 |
| One version for all of set A | **v4.51.3** is the earliest: Qwen3 needs 4.51.0 or later, GLM-4-0414 needs 4.51.3. Its auto-config mapping lists `qwen3`, `glm4` (and `qwen2`, `glm`, `qwen3_moe`). | https://raw.githubusercontent.com/huggingface/transformers/v4.51.3/src/transformers/models/auto/configuration_auto.py |
| One version for all of set B | **v4.51.3** is also the earliest: Qwen2.5 needs only 4.37.0 or later, but the shared GLM-4-9B-0414 needs 4.51.3. | same |
| `torch` 2.8 | **UNCONFIRMED.** v4.51.3 `setup.py` requires `torch>=2.0` with no upper bound (also `tokenizers>=0.21,<0.22`, `huggingface-hub>=0.30.0,<1.0`, `safetensors>=0.4.3`, Python `>=3.9.0`), so the pin does not exclude 2.8. But PyTorch 2.8.0 was published 2025-08-06, almost four months after v4.51.3, so that release cannot have been tested against it, and no `transformers` release note stating torch 2.8 support was found or read. | https://raw.githubusercontent.com/huggingface/transformers/v4.51.3/setup.py ; https://github.com/pytorch/pytorch/releases/tag/v2.8.0 |

Note: the current documentation site shows `transformers` v5.24.1 as the version in its links (seen on https://huggingface.co/docs/transformers/model_doc/qwen3). Whether the v5 line still loads these checkpoints unchanged was not examined.

## 3. Comparison, set A versus set B (no recommendation)

| | Set A (Qwen3 0.6B / 1.7B / 8B + GLM-4-9B-0414) | Set B (Qwen2.5 0.5B / 1.5B / 7B Instruct + GLM-4-9B-0414) |
|---|---|---|
| Age of the Qwen models | Repositories created 2025-04-27; blog 2025-04-29 (about 19 months before 2026-11-27) | Repositories created 2024-09-16/17; blog 2024-09-19 (about 26 months) |
| Thinking switch to fix | Yes. Thinking is on by default; `enable_thinking=False` in `apply_chat_template` turns it off. Card gives different sampling values per mode and warns against greedy decoding (in the thinking-mode bullet). | No thinking mode. No greedy warning on the cards. |
| Default system message in template | None for Qwen3 | Qwen2.5 inserts "You are Qwen, created by Alibaba Cloud. You are a helpful assistant." unless a system message is supplied |
| Library version needed | Earliest single version v4.51.3 (Qwen3 from 4.51.0; GLM-4-0414 from 4.51.3). Built-in classes, no `trust_remote_code`. | Earliest single version v4.51.3 (Qwen2.5 from 4.37.0; GLM-4-0414 from 4.51.3). Built-in classes, no `trust_remote_code`. |
| Download size, safetensors only | 1,503,300,328 + 4,063,515,592 + 16,381,516,776 + 18,800,618,456 = **40,748,951,152 bytes** (40.75 GB; 37.95 GiB) | 988,097,824 + 3,087,467,144 + 15,231,271,888 + 18,800,618,456 = **38,107,455,312 bytes** (38.11 GB; 35.49 GiB) |
| Parameter counts (API) | 751,632,384 / 2,031,739,904 / 8,190,735,360 / 9,400,279,040 | 494,032,768 / 1,543,714,304 / 7,615,616,512 / 9,400,279,040 |
| Licences | Qwen3: Apache 2.0 (tag and LICENSE). GLM: MIT (tag and LICENSE). | Qwen2.5 at these three sizes: Apache 2.0 (tag and LICENSE). GLM: MIT (tag and LICENSE). |

Tokenizer and config files add roughly 16 MB (Qwen3), 11 MB (Qwen2.5) and 20 MB (GLM) per repository on top of the weights.

## 4. UNCONFIRMED items

1. **`torch` 2.8 support in `transformers` 4.51.3.** Only the dependency pin (`torch>=2.0`, no cap) was read; no statement of support and no test. PyTorch 2.8.0 postdates the release.
2. **Exact first-public date of each checkpoint.** Only repository creation dates and blog dates were read. A repository can be created private before it is published: Qwen3 repositories were created 2025-04-27 and the blog is dated 2025-04-29; Qwen2.5 repositories 2024-09-16/17 and the blog 2024-09-19. The Qwen commit histories were not read.
3. **GLM-4-9B-0414 public release date.** Repository created 2025-04-07, last commit 2025-04-14; the publisher's announcement was not read, and the commit titles do not say when the weights were added or when the repository became public.
4. **Minimum `transformers` version for GLM-4-9B-0414 as stated by its card:** the card states none. v4.51.3 is from the library's release notes and tagged source, and the repository's `config.json` records `4.52.0.dev0`.
5. **GLM-4-9B-0414 naming or use clause:** none was found (standard MIT text, card body silent). This is an absence reported by a summarising reader of a 1,064-byte LICENSE and a 43,961-byte card; worth one direct look.
6. **LICENSE text of Qwen2.5-1.5B, Qwen2.5-7B, Qwen3-1.7B, Qwen3-8B:** files exist at 11,343 bytes each, the same size as the two that were read (Apache 2.0); their text was not read individually.
7. **Qwen3-0.6B parameter count:** the card says 0.6B, the API safetensors record says 751,632,384. Both reported; not reconciled.
8. **Nothing was loaded.** "Loads with built-in classes" rests on `config.json` (`architectures`, `model_type`), the absence of `.py` files in the listings, the cards' example code, and the library's tagged source.
9. **Whether current `transformers` (the docs site shows v5.24.1) still loads all seven unchanged:** not examined.
10. **All quotes and numbers passed through a summarising fetch tool** (section 0); none was read as raw bytes.
