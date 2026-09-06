"""Provider-agnostic chat types.

Every model in the roster -- frontier APIs and OpenRouter-hosted open weights
alike -- is driven through one interface, so a task runner never contains
provider-specific branching and adding a model is a config change.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class Response:
    """One model reply, plus everything needed to audit or re-price it."""

    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None
    latency_s: float = 0.0
    cached: bool = False
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text.strip())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("raw", None)  # provider payloads are large and not needed downstream
        return d


def request_key(
    model: str, messages: list[Message], params: dict[str, Any]
) -> str:
    """Stable cache key over the exact request.

    Any change to the model, the prompt or a sampling parameter produces a
    different key, so a cache hit is only ever returned for a request that is
    identical in every respect that could change the answer.
    """
    payload = {
        "model": model,
        "messages": [[m.role, m.content] for m in messages],
        "params": {k: params[k] for k in sorted(params)},
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Provider(ABC):
    """A model endpoint. Implementations must not retry silently."""

    name: str = "base"

    @abstractmethod
    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        """Single call, no caching and no retry -- both are applied by the runner."""


@dataclass
class ModelSpec:
    """One roster entry. `model_id` is pinned to an exact version, never an alias.

    Aliases like "latest" silently change the system under test between runs and
    make a published number unreproducible.
    """

    name: str
    provider: str
    model_id: str
    price_in: float = 0.0   # USD per 1M prompt tokens
    price_out: float = 0.0  # USD per 1M completion tokens
    params: dict[str, Any] | None = None
