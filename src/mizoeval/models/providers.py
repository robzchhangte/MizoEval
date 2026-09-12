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
    "MockProvider", "NLLBProvider", "HFLocalProvider",
]

# --------------------------------------------------------------------------- adapters


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"),
                             base_url=base_url)

    # Reasoning-family models (gpt-5*, o1/o3/o4) reject `max_tokens` and want
    # `max_completion_tokens`; the completion count they report includes hidden
    # reasoning tokens, which is what the budget must see.
    _REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")

    def _adapt_params(self, model: str, params: dict[str, Any]) -> dict[str, Any]:
        p = dict(params)
        if any(model.startswith(pre) for pre in self._REASONING_PREFIXES):
            if "max_tokens" in p:
                p["max_completion_tokens"] = p.pop("max_tokens")
        return p

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        params = self._adapt_params(model, params)
        t0 = time.time()
        r = self.client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **params,
        )
        u = r.usage
        details = getattr(u, "completion_tokens_details", None)
        reasoning = getattr(details, "reasoning_tokens", 0) or 0
        return Response(
            text=r.choices[0].message.content or "",
            model=model,
            provider=self.name,
            prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(u, "completion_tokens", 0) or 0,
            finish_reason=r.choices[0].finish_reason,
            latency_s=time.time() - t0,
            raw={"reasoning_tokens": reasoning} if reasoning else {},
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

    # Without this the SDK's HTTP call can block forever on a dropped
    # connection -- a single hung request stalls a whole matrix run.
    _TIMEOUT_MS = 120_000

    def _make_client(self, api_key: str | None):
        from google.genai import types as _types

        return self.genai.Client(
            api_key=api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"),
            http_options=_types.HttpOptions(timeout=self._TIMEOUT_MS),
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
        # Gemini 2.5+/3.x Flash "think" by default; those thinking tokens are
        # billed but land in `thoughts_token_count`, not `candidates_token_count`,
        # so they escape the token budget. Disable thinking by default (matches
        # how the open-weight models were run); override with thinking_budget=-1
        # for dynamic thinking or a positive cap.
        tb = params.get("thinking_budget", 0)
        thinking_cfg = None
        if tb is not None:
            try:
                thinking_cfg = types.ThinkingConfig(thinking_budget=tb)
            except Exception:  # noqa: BLE001 - older SDK / model without thinking
                thinking_cfg = None
        cfg = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=params.get("temperature"),
            max_output_tokens=params.get("max_tokens"),
            thinking_config=thinking_cfg,
        )
        t0 = time.time()
        r = self.client.models.generate_content(model=model, contents=contents, config=cfg)
        usage = getattr(r, "usage_metadata", None)
        thoughts = getattr(usage, "thoughts_token_count", 0) or 0
        completion = getattr(usage, "candidates_token_count", 0) or 0
        return Response(
            text=r.text or "",
            model=model,
            provider=self.name,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            completion_tokens=completion + thoughts,  # count thinking against budget/cost
            finish_reason=getattr(r.candidates[0], "finish_reason", None) if getattr(r, "candidates", None) else None,
            latency_s=time.time() - t0,
            raw={"thoughts_token_count": thoughts} if thoughts else None,
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
        from google.genai import types as _types

        return self.genai.Client(
            vertexai=True,
            project=project,
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            http_options=_types.HttpOptions(timeout=self._TIMEOUT_MS),
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

    # num_predict floor -- reasoning models need room for a hidden reasoning
    # pass plus the answer; a ceiling costs nothing for models that stop at EOS.
    _MIN_NUM_PREDICT = 512

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
            # Reasoning models on Ollama Cloud (gpt-oss, deepseek-r1) burn part of
            # num_predict on an internal reasoning pass before emitting any
            # visible content, and this client build has no `think: false`
            # switch. A tight cap (MCQ passes 16) then yields empty content, so
            # floor num_predict at a level that leaves room for a short answer.
            options["num_predict"] = max(int(params["max_tokens"]), self._MIN_NUM_PREDICT)
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


class NLLBProvider(Provider):
    """Local NLLB-200 seq2seq translation provider (e.g. facebook/nllb-200-3.3B)."""

    name = "nllb"
    _models: dict[str, tuple[Any, Any]] = {}

    def __init__(self, device: str = "cuda") -> None:
        import torch

        self.device = device if torch.cuda.is_available() else "cpu"

    def _get_model(self, model_id: str):
        if model_id not in self._models:
            import os
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            os.environ["USE_TF"] = "0"
            os.environ["USE_FLAX"] = "0"
            token = os.environ.get("hf_token") or os.environ.get("HF_TOKEN")
            tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                token=token,
            ).to(self.device)
            model.eval()
            self._models[model_id] = (tokenizer, model)
        return self._models[model_id]

    @staticmethod
    def _parse_mt_prompt(text: str) -> tuple[str, str, str]:
        """Extract source text and language codes from an MT chat prompt."""
        lines = text.strip().splitlines()
        if not lines:
            return "", "eng_Latn", "lus_Latn"
        last_line = lines[-1].strip()
        if last_line in ("Mizo:", "English:"):
            tgt_label = last_line[:-1]
            src_idx = None
            for i in range(len(lines) - 2, -1, -1):
                l = lines[i].strip()
                if l.startswith("English:") or l.startswith("Mizo:"):
                    src_idx = i
                    break
            if src_idx is not None:
                parts = lines[src_idx].split(":", 1)
                src_label = parts[0].strip()
                src_text_lines = [parts[1].strip()] + [l.strip() for l in lines[src_idx + 1:-1] if l.strip()]
                src_text = " ".join(src_text_lines).strip()
                src_lang = "eng_Latn" if src_label == "English" else "lus_Latn"
                tgt_lang = "lus_Latn" if tgt_label == "Mizo" else "eng_Latn"
                return src_text, src_lang, tgt_lang
        return text.strip(), "eng_Latn", "lus_Latn"

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        import time
        import torch

        tokenizer, seq2seq = self._get_model(model)
        user_content = next((m.content for m in reversed(messages) if m.role == "user"), "")
        src_text, src_lang, tgt_lang = self._parse_mt_prompt(user_content)

        t0 = time.time()
        tokenizer.src_lang = src_lang
        inputs = tokenizer(src_text, return_tensors="pt", max_length=512, truncation=True).to(self.device)
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_lang)

        num_beams = params.get("num_beams", 4)
        max_length = params.get("max_tokens", 512)

        with torch.no_grad():
            generated_tokens = seq2seq.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=max_length,
                num_beams=num_beams,
            )

        decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        text = decoded[0].strip() if decoded else ""
        prompt_tokens = int(inputs["input_ids"].shape[1])
        completion_tokens = int(generated_tokens.shape[1])

        return Response(
            text=text,
            model=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_s=time.time() - t0,
        )


class HFLocalProvider(Provider):
    """Local HuggingFace causal LM provider (e.g. meta-llama/Llama-3.1-8B-Instruct)."""

    name = "hf_local"
    _models: dict[str, tuple[Any, Any]] = {}

    def __init__(self, device: str = "cuda") -> None:
        import torch

        self.device = device if torch.cuda.is_available() else "cpu"

    def _get_model(self, model_id: str):
        if model_id not in self._models:
            import os
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            os.environ["USE_TF"] = "0"
            os.environ["USE_FLAX"] = "0"
            token = os.environ.get("hf_token") or os.environ.get("HF_TOKEN")
            tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token_id = tokenizer.eos_token_id

            kwargs: dict[str, Any] = {"token": token}
            if self.device != "cpu":
                kwargs["device_map"] = "auto"
                if "bnb" not in model_id.lower() and "4bit" not in model_id.lower():
                    kwargs["torch_dtype"] = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            else:
                kwargs["torch_dtype"] = torch.float32

            model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
            model.eval()
            self._models[model_id] = (tokenizer, model)
        return self._models[model_id]

    def complete(self, model: str, messages: list[Message], **params: Any) -> Response:
        import time
        import torch

        tokenizer, causal_model = self._get_model(model)
        t0 = time.time()

        chat_messages = [{"role": m.role, "content": m.content} for m in messages]
        prompt = tokenizer.apply_chat_template(
            chat_messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(self.device)
        input_len = int(inputs["input_ids"].shape[1])

        max_new_tokens = params.get("max_tokens", 512)
        temperature = params.get("temperature", 0.0)
        do_sample = temperature > 0.0

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }
        if do_sample:
            gen_kwargs["temperature"] = temperature
            gen_kwargs["do_sample"] = True
        else:
            gen_kwargs["do_sample"] = False

        with torch.no_grad():
            outputs = causal_model.generate(
                **inputs,
                **gen_kwargs,
            )

        gen_tokens = outputs[0][input_len:]
        text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()

        return Response(
            text=text,
            model=model,
            provider=self.name,
            prompt_tokens=input_len,
            completion_tokens=len(gen_tokens),
            latency_s=time.time() - t0,
        )


PROVIDERS: dict[str, type[Provider]] = {
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "vertex": VertexProvider,
    "ollama_cloud": OllamaCloudProvider,
    "mock": MockProvider,
    "nllb": NLLBProvider,
    "hf_local": HFLocalProvider,
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
        budget=None,
    ) -> None:
        self.spec = spec
        self.cache = cache if cache is not None else ResponseCache()
        self.max_retries = max_retries
        self.use_cache = use_cache
        self.budget = budget  # optional TokenBudget; raises BudgetExceeded when spent
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
                return hit  # cache hits are free, so they never touch the budget

        if self.budget is not None:
            self.budget.check()  # raises BudgetExceeded before spending more

        resp = self._call_with_retry(messages, params)
        self.n_calls += 1
        if resp.ok:
            self.cost_usd += (
                resp.prompt_tokens * self.spec.price_in
                + resp.completion_tokens * self.spec.price_out
            ) / 1_000_000
            if self.budget is not None:
                self.budget.record(resp.prompt_tokens, resp.completion_tokens)
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
