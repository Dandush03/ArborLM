"""Shared loaders for the P9 calibration audit (auditor's own code).

Uses ``studies.p9`` ONLY to regenerate the rehearsal-0 draw and to load the verified frozen
backbones (allowed by the audit brief). Every quantity under audit is recomputed in the scripts
beside this file with the auditor's own forward passes, scoring and probes; no
``studies.p9.controls`` probe, ``evaluate`` scorer or ``analysis_*`` module is called for a number
that is reported.
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Failed to initialize NumPy")

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import torch  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from studies.p9 import controls, core, data  # noqa: E402

RUN = Path(
    "/Users/daniellaloush/dandush03/ArborLM/experiments/"
    "P9C-20261114T182513034263Z-a529fd1946ff4e52b19980bd6d3b6fcd"
)
ROOT = RUN.parent
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)

ALPHABET = torch.arange(0x40, 0x60)
PARENTS = {"b101": (101, 301), "b102": (102, 302)}

torch.set_num_threads(8)


def study():
    """Rehearsal draw 0, exactly the draw the calibration used (seeds 179001+)."""
    seeds = core.rehearsal_seeds(0)
    assert seeds.facts == 179001
    for v in seeds.data_values():
        core.assert_not_registered_seed(v)
    corpus = core.load_trained_corpus(ROOT)
    return data.build_study_data(seeds, corpus)


def backbone(name: str):
    return controls.load_backbone(PARENTS[name], ROOT)[0]


# --- the auditor's own forward through the frozen backbone ------------------------------------------
def block(blk, h: torch.Tensor) -> torch.Tensor:
    """Re-implementation of ``arborlm.model.Block.forward`` (pre-LN, 4 heads x 8, GELU FFN)."""
    b, t, d = h.shape
    x = F.layer_norm(h, (d,), blk.attn_norm.weight, blk.attn_norm.bias, 1e-5)
    qkv = x @ blk.qkv.weight.T + blk.qkv.bias
    q, k, v = qkv.reshape(b, t, 3, 4, 8).permute(2, 0, 3, 1, 4).unbind(0)
    s = (q @ k.transpose(-2, -1)) / 8**0.5
    s = s + torch.full((t, t), float("-inf")).triu(1)
    a = s.softmax(-1) @ v
    h = h + a.transpose(1, 2).reshape(b, t, d) @ blk.attn_out.weight.T + blk.attn_out.bias
    y = F.layer_norm(h, (d,), blk.ffn_norm.weight, blk.ffn_norm.bias, 1e-5)
    y = F.gelu(y @ blk.ffn_in.weight.T + blk.ffn_in.bias) @ blk.ffn_out.weight.T + blk.ffn_out.bias
    return h + y


def embed(bb, tokens: torch.Tensor) -> torch.Tensor:
    t = tokens.shape[1]
    return bb.token.weight[tokens] + bb.position.weight[:t]


def hidden0(bb, tokens: torch.Tensor) -> torch.Tensor:
    """Residual after block 0 (memory insertion point), [B, T, 32]."""
    return block(bb.blocks[0], embed(bb, tokens))


def head(bb, h: torch.Tensor) -> torch.Tensor:
    """Block 1, final norm, tied output: [B, T, 256]."""
    h = block(bb.blocks[1], h)
    h = F.layer_norm(h, (32,), bb.final_norm.weight, bb.final_norm.bias, 1e-5)
    return h @ bb.token.weight.T


@torch.no_grad()
def hidden_states(bb, tokens: torch.Tensor, chunk: int = 512):
    """(embedding, after block 0) for inputs tokens[:, :63]; each [C, 63, 32]."""
    e, h = [], []
    for s in range(0, tokens.shape[0], chunk):
        x = tokens[s : s + chunk, :63]
        e.append(embed(bb, x))
        h.append(hidden0(bb, x))
    return torch.cat(e), torch.cat(h)


def score(logits: torch.Tensor, answer: torch.Tensor):
    """Accuracy within the alphabet, ties counted wrong; p of correct renormalized over the alphabet;
    full 256-way p of the correct byte. logits [Q, 256], answer [Q] symbol indices."""
    inside = logits[:, ALPHABET]
    rows = torch.arange(len(answer))
    c = inside[rows, answer]
    other = inside.clone()
    other[rows, answer] = float("-inf")
    correct = c > other.max(-1).values
    p_sigma = inside.softmax(-1)[rows, answer]
    p_full = logits.softmax(-1)[rows, ALPHABET[answer]]
    return correct, p_sigma, p_full


def restrict(stream, facts: int):
    """Contexts whose facts are all < facts (trained subset). Own re-implementation."""
    keep = (stream.fact_ids < facts).all(1)
    return stream.tokens[keep], stream.fact_ids[keep]
