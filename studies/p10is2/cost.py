# ruff: noqa: E501
"""Counted training multiply-adds per update (ADR-0025 section 8.5, "Counted training multiply-adds per update"). A COUNT of logical work, never measured efficiency and never a speedup.

The ADR's rule: at batch 32 and the mean training sequence length, one forward and one backward pass, counting each linear map as inputs x outputs per token and pass (twice in the backward pass where its weights
are trainable), the key scan as rows x 16 per read and the value mix as 8 x 576 per read; computed by one function tested on hand cases.

READINGS that the ADR does not fix (listed in the report; none enters a label, a gate or a comparison rule): (1) the attention score matmuls (QK^T and AV) and norms are not linear maps and are not counted;
(2) the language-model head is a linear map and is counted (its weights are frozen, so once in the backward pass); (3) the backward pass runs only through the layers above the lowest trainable parameter: for
a memory arm reading at block L (0-based, the read is the output of block L) blocks 0..L need no gradient, for LoRA (all blocks) every block does; (4) LoRA's two factors are linear maps with trainable
weights; the frozen base maps of a LoRA block are counted once in the backward pass (input gradient); (5) in the backward pass the key scan costs rows x 16 (input gradient) plus trainable rows x 16 (key
gradient), the value mix 8 x 576 (gradient to the weights) plus 8 x 576 x trainable share (value gradient). One count per update at the given batch and mean length.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StudentShape:
    width: int = 576
    layers: int = 30
    heads: int = 9
    kv_heads: int = 3
    intermediate: int = 1536
    vocab: int = 49152

    @property
    def head_dim(self) -> int:
        return self.width // self.heads

    def block_linear_maps(self) -> list[tuple[str, int, int]]:
        """(name, inputs, outputs) of the frozen linear maps of one block: q, k, v, o and the three MLP maps."""
        w, kv = self.width, self.kv_heads * self.head_dim
        return [("q", w, w), ("k", w, kv), ("v", w, kv), ("o", w, w), ("gate", w, self.intermediate), ("up", w, self.intermediate), ("down", self.intermediate, w)]


KEY_WIDTH, TOP, VECTOR = 16, 8, 576


def lora_maps(shape: StudentShape, rank: int) -> list[tuple[str, int, int]]:
    """The trainable factors on the query and value projections of one block: A (inputs x rank) and B (rank x outputs) for each of the two."""
    w, kv = shape.width, shape.kv_heads * shape.head_dim
    return [("q_A", w, rank), ("q_B", rank, w), ("v_A", w, rank), ("v_B", rank, kv)]


def per_token_forward(shape: StudentShape, *, lora_rank: int = 0) -> int:
    """Forward multiply-adds of one token through every block's linear maps and the head (LoRA factors included when ``lora_rank`` > 0)."""
    block = sum(i * o for _, i, o in shape.block_linear_maps())
    extra = sum(i * o for _, i, o in lora_maps(shape, lora_rank)) if lora_rank else 0
    return shape.layers * (block + extra) + shape.width * shape.vocab


def training_multiply_adds(
    shape: StudentShape, kind: str, *, batch: int, mean_len: float, mean_reads: float = 0.0, rows: int = 0, trainable_rows: int = 0, read_block: int = 4, lora_rank: int = 0, trainable_share: float = 1.0
) -> dict[str, float]:  # fmt: skip
    """Forward, backward and total multiply-adds of ONE update. ``kind`` is ``"memory"`` (the student frozen, a store read after block ``read_block``: ``rows`` scanned per read, ``trainable_rows`` of them
    trainable, ``mean_reads`` reads per sequence) or ``"lora"`` (rank ``lora_rank`` on q and v of every block). ``trainable_share`` is the share of the value mix's weights that train."""
    tokens = batch * mean_len
    block = sum(i * o for _, i, o in shape.block_linear_maps())
    head = shape.width * shape.vocab
    if kind == "memory":
        reads = batch * mean_reads
        fwd = tokens * (shape.layers * block + head) + reads * (rows * KEY_WIDTH + TOP * VECTOR)
        above = shape.layers - (read_block + 1)  # blocks that gradient must cross to reach the read
        bwd = tokens * (above * block + head) + reads * (rows * KEY_WIDTH + trainable_rows * KEY_WIDTH + TOP * VECTOR + TOP * VECTOR * trainable_share)
    elif kind == "lora":
        if lora_rank < 1:
            raise ValueError("a LoRA count needs a rank")
        extra = sum(i * o for _, i, o in lora_maps(shape, lora_rank))
        fwd = tokens * (shape.layers * (block + extra) + head)
        bwd = tokens * (shape.layers * (block + 2 * extra) + head)  # frozen maps once (input gradient), trainable factors twice
    else:
        raise ValueError(f"unknown kind {kind!r}")
    return {"forward": float(fwd), "backward": float(bwd), "total": float(fwd + bwd), "tokens": float(tokens)}
