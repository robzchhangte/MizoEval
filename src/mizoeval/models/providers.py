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
from typing import Any

from mizoeval.models.base import Message, ModelSpec, Provider, Response
from mizoeval.models.cache import ResponseCache

__all__ = [
    "ModelSpec", "ModelClient", "PROVIDERS", "OpenAIProvider", "OpenRouterProvider",
    "AnthropicProvider", "GoogleProvider", "VertexProvider", "OllamaCloudProvider",
    "MockProvider",
]

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
    """Gemini via the public Generative Language API (API-key auth)."""

    name = "google"

    def __init__(self, api_key: str | None = None) -> None:
        from google import genai

        self.genai = genai
        self.client = self._make_client(api_key)

    def _make_client(self, api_key: str | None):
        return self.genai.Client(
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


class VertexProvider(GoogleProvider):
    """Gemini via Vertex AI.

    Same request/response handling as `GoogleProvider` -- only the client
    construction differs. Vertex authenticates with Application Default
    Credentials (`gcloud auth application-default login`), not an API key, and
    needs a GCP project and region. Set `GOOGLE_CLOUD_PROJECT` and, optionally,
    `GOOGLE_CLOUD_LOCATION` (default `us-central1`).
    """

    name = "vertex"

    def _make_client(self, api_key: str | None):  # noqa: ARG002 - Vertex uses ADC
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if not project:
            raise RuntimeError(
                "VertexProvider needs GOOGLE_CLOUD_PROJECT set, plus "
                "`gcloud auth application-default login` completed."
            )
        return self.genai.Client(
            vertexai=True,
            project=project,
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )


class OllamaCloudProvider(Provider):
    """Open-weight models hosted on Ollama Cloud, via the native `ollama` client.

    The free tier is rate-limited per key, so this adapter drives a `KeyPool`
    (`keys.txt`, git-ignored) and rotates to the next key when one reports
    itself exhausted -- a 429, or an auth error that means the key is spent.
    Rotation is transparent to the caller: `complete()` retries on the new key
    and only raises once every key is cooling down.

    Free tier => price stays 0 in the roster and the cost accounting reflects that.
    """

    name = "ollama_cloud"

    # Substrings that mean "this key is out of quota", not "the request was bad".
    _EXHAUSTED_MARKERS = (
        "rate limit", "ratelimit", "too many requests", "quota", "exhaust",
        "limit reached", "429", "capacity",
    )

    def __init__(self, api_key: str | None = None, key_pool=None) -> None:
        from ollama import Client

        self._Client = Client
        self._host = os.environ.get("OLLAMA_HOST", "https://ollama.com")
        if key_pool is not None:
            self._pool = key_pool
        elif api_key:
            from mizoeval.models.keypool import KeyPool

            self._pool = KeyPool(keys=[api_key])
        else:
            self._pool = self._default_pool()
        self._client = self._build_client()

    @staticmethod
    def _default_pool():
        """Prefer keys.txt (rotation); fall back to a single env key."""
        from mizoeval.models.keypool import DEFAULT_KEYS_FILE, KeyPool

        if DEFAULT_KEYS_FILE.exists():
            return KeyPool.from_file(DEFAULT_KEYS_FILE)
        env = os.environ.get("OLLAMA_API_KEY")
        if not env:
            raise RuntimeError(
                "no Ollama credentials: create keys.txt (one key per line) or set OLLAMA_API_KEY"
            )
        return KeyPool(keys=[env])

    def _build_client(self):
        return self._Client(
            host=self._host,
            headers={"Authorization": "Bearer " + self._pool.current()},
        )

    def _is_exhaustion(self, exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        if status in (401, 403, 429):
            return True
        msg = str(exc).lower()
        return any(m in msg for m in self._EXHAUSTED_MARKERS)

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        from mizoeval.models.keypool import AllKeysExhausted

        options: dict[str, Any] = {}
        if params.get("temperature") is not None:
            options["temperature"] = params["temperature"]
        if params.get("max_tokens") is not None:
            options["num_predict"] = params["max_tokens"]
        payload = [{"role": m.role, "content": m.content} for m in messages]

        attempts = 0
        while True:
            attempts += 1
            t0 = time.time()
            try:
                r = self._client.chat(
                    model=model, messages=payload, stream=False, options=options or None
                )
                return Response(
                    text=(r.get("message", {}) or {}).get("content", "") or "",
                    model=model,
                    provider=self.name,
                    prompt_tokens=r.get("prompt_eval_count", 0) or 0,
                    completion_tokens=r.get("eval_count", 0) or 0,
                    finish_reason=r.get("done_reason"),
                    latency_s=time.time() - t0,
                )
            except AllKeysExhausted:
                raise
            except Exception as exc:  # noqa: BLE001 - ollama raises ResponseError and httpx errors
                if not self._is_exhaustion(exc) or attempts > len(self._pool.keys):
                    raise
                self._pool.rotate(reason=f"{type(exc).__name__}: {str(exc)[:80]}")
                self._client = self._build_client()


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
            low = prompt.lower()
            if "[answer: x]" in low:  # MCQ chain-of-thought
                text = f"Reasoning about the question.\n[ANSWER: {rng.choice('ABCD')}]"
            elif "option letter (a, b, c, or d)" in low:  # MCQ zero/few-shot
                text = rng.choice("ABCD")
            elif "positive, neutral, or negative" in low:  # sentiment
                text = rng.choice(["Positive", "Neutral", "Negative"])
            elif "entities:" in low and "json array" in low:  # NER
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
    "vertex": VertexProvider,
    "ollama_cloud": OllamaCloudProvider,
    "mock": MockProvider,
}


# --------------------------------------------------------------------------- client


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
