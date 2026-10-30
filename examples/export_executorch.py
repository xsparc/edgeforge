"""Export a local PyTorch module to a self-contained portable ExecuTorch bundle."""

import io
from pathlib import Path

import numpy as np
import torch
from executorch.exir import to_edge_transform_and_lower

from edgeforge.bundle import pack
from edgeforge.contracts import ModelConfig


class Double(torch.nn.Module):
    def forward(self, x):
        return x + x


exported = torch.export.export(Double().eval(), (torch.ones(2),))
program = to_edge_transform_and_lower(exported, partitioner=[]).to_executorch()
vectors = io.BytesIO()
np.savez(
    vectors,
    input__x=np.array([[1, 2]], dtype="float32"),
    output__y=np.array([[2, 4]], dtype="float32"),
)
config = ModelConfig(
    runtime="executorch",
    provider="portable",
    inputs=[{"name": "x", "dtype": "float32", "shape": [2]}],
    outputs=[{"name": "y", "dtype": "float32", "shape": [2]}],
)
with Path("double.efb").open("xb") as output:
    output.write(pack(program.buffer, vectors.getvalue(), config))
