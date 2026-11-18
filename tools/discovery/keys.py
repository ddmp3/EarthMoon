"""Content keys (ADR-009): a step output is identified by its inputs, its code and its parameters."""
from __future__ import annotations

import hashlib
import json


def content_key(inputs: dict, code: str, params: dict) -> str:
    """sha256 of the canonical JSON of {inputs, code, params}. Key order never matters."""
    blob = json.dumps({"inputs": inputs, "code": code, "params": params}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
