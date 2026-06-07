from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BackendResult:
    status: str
    backend: str
    data: Dict[str, Any]


class ImageBackend:
    """Base interface for all image generation backends."""

    name = "base"

    def __init__(self, config: Dict[str, Any], root_dir):
        self.config = config
        self.root_dir = root_dir

    def available(self) -> bool:
        raise NotImplementedError

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
