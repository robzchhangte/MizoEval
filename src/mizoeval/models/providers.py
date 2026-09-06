"""Concrete provider adapters and the client that wraps them.

Adapters are thin: they translate `Message` into the vendor's request shape and
the reply back into a `Response`. Everything shared -- caching, retry, cost
accounting -- lives in `ModelClient` so it behaves identically across vendors
and cannot drift between them.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Any

from mizoeval.models.base import Message, Provider, Response
from mizoeval.models.cache import ResponseCache

# --------------------------------------------------------------------------- adapters


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"),
                             base_url=base_url)

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        t0 = time.time()
        r = self.client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **params,
        )
        u = r.usage
        return Response(
            text=r.choices[0].message.content or "",
            model=model,
            provider=self.name,
            prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(u, "completion_tokens", 0) or 0,
            finish_reason=r.choices[0].finish_reason,
            latency_s=time.time() - t0,
        )


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter speaks the OpenAI wire format, so only the endpoint differs.

    One key reaches both frontier and open-weight models, which is what makes a
    broad roster affordable and keeps every model behind an identical call path.
    """

    name = "openrouter"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        # The Anthropic API takes the system prompt as a separate argument
        # rather than as a message with role="system".
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        params.setdefault("max_tokens", 1024)
        t0 = time.time()
        r = self.client.messages.create(
            model=model, messages=turns, **({"system": system} if system else {}), **params
        )
        return Response(
            text="".join(b.text for b in r.content if b.type == "text"),
            model=model,
            provider=self.name,
            prompt_tokens=r.usage.input_tokens,
            completion_tokens=r.usage.output_tokens,
            finish_reason=r.stop_reason,
            latency_s=time.time() - t0,
        )


class GoogleProvider(Provider):
    name = "google"

    def __init__(self, api_key: str | None = None) -> None:
        from google import genai

        self.genai = genai
        self.client = genai.Client(
            api_key=api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        )

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        from google.genai import types

        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            types.Content(role="model" if m.role == "assistant" else "user",
                          parts=[types.Part(text=m.content)])
            for m in messages
            if m.role != "system"
        ]
        cfg = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=params.get("temperature"),
            max_output_tokens=params.get("max_tokens"),
        )
        t0 = time.time()
        r = self.client.models.generate_content(model=model, contents=contents, config=cfg)
        usage = getattr(r, "usage_metadata", None)
        return Response(
            text=r.text or "",
            model=model,
            provider=self.name,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            latency_s=time.time() - t0,
        )


class MockProvider(Provider):
    """Deterministic offline provider, for exercising the pipeline without spend.

    It answers in each task's expected output format so parsers, metrics and
    runners can be tested end to end. Its answers are deliberately arbitrary --
    it verifies plumbing, never model quality.
    """

    name = "mock"

    def __init__(self, seed: int = 0, reply: str | None = None) -> None:
        self.seed = seed
        self.reply = reply

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        prompt = messages[-1].content if messages else ""
        if self.reply is not None:
            text = self.reply
        else:
            rng = random.Random(f"{self.seed}:{prompt}")
            if "Answer with the correct option letter" in prompt:
                text = rng.choice("ABCD")
            elif "Positive, Neutral, or Negative" in prompt:
                text = rng.choice(["Positive", "Neutral", "Negative"])
            elif "named entities" in prompt.lower():
                text = "[]"
            else:
                text = "mock translation output"
        return Response(text=text, model=model, provider=self.name,
                        prompt_tokens=len(prompt.split()), completion_tokens=len(text.split()))


PROVIDERS: dict[str, type[Provider]] = {
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "mock": MockProvider,
}


# --------------------------------------------------------------------------- client


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


class ModelClient:
    """Caching, retrying, cost-accounting wrapper around a `Provider`."""

    def __init__(
        self,
        spec: ModelSpec,
        cache: ResponseCache | None = None,
        max_retries: int = 5,
        use_cache: bool = True,
    ) -> None:
        self.spec = spec
        self.cache = cache if cache is not None else ResponseCache()
        self.max_retries = max_retries
        self.use_cache = use_cache
        self._provider: Provider | None = None
        self.n_calls = 0
        self.n_cache_hits = 0
        self.cost_usd = 0.0

    @property
    def provider(self) -> Provider:
        # Constructed lazily so a roster entry for a provider whose key is
        # missing does not break runs of the models that *are* configured.
        if self._provider is None:
            self._provider = PROVIDERS[self.spec.provider]()
        return self._provider

    def chat(self, messages: list[Message], **overrides: Any) -> Response:
        params = {**(self.spec.params or {}), **overrides}

        if self.use_cache:
            hit = self.cache.get(self.spec.model_id, messages, params)
            if hit is not None:
                self.n_cache_hits += 1
                return hit

        resp = self._call_with_retry(messages, params)
        self.n_calls += 1
        if resp.ok:
            self.cost_usd += (
                resp.prompt_tokens * self.spec.price_in
                + resp.completion_tokens * self.spec.price_out
            ) / 1_000_000
            if self.use_cache:
                self.cache.put(self.spec.model_id, messages, params, resp)
        return resp

    def _call_with_retry(self, messages: list[Message], params: dict[str, Any]) -> Response:
        delay = 2.0
        last = ""
        for attempt in range(self.max_retries):
            try:
                return self.provider.complete(self.spec.model_id, messages, **params)
            except Exception as exc:  # noqa: BLE001 - providers raise unrelated types
                last = f"{type(exc).__name__}: {exc}"
                if attempt == self.max_retries - 1:
                    break
                # Jittered backoff: a whole roster retrying in lockstep after a
                # rate limit would just collide again.
                time.sleep(delay + random.uniform(0, delay / 2))
                delay *= 2
        return Response(text="", model=self.spec.model_id, provider=self.spec.provider,
                        error=last)
