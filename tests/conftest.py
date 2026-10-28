import io

import numpy as np
import pytest

from edgeforge.contracts import ModelConfig


@pytest.fixture
def config():
    return ModelConfig(
        runtime="onnx",
        inputs=[{"name": "x", "dtype": "float32", "shape": [2]}],
        outputs=[{"name": "y", "dtype": "float32", "shape": [2]}],
    )


@pytest.fixture
def vectors():
    buffer = io.BytesIO()
    np.savez(
        buffer,
        input__x=np.array([[1, 2], [3, 4]], dtype="float32"),
        output__y=np.array([[2, 4], [6, 8]], dtype="float32"),
    )
    return buffer.getvalue()
