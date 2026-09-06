"""Versioned prompt templates.

Every template carries a version tag and is hashed at load time. The hash goes
into each result record, so a run is always tied to the exact prompt text that
produced it and the appendix can reproduce the wording without guesswork. Change
a template => bump its version; never edit one in place once results exist under it.

Regimes per task:
  MCQ        zero_shot, five_shot, cot        (cot emits an [ANSWER: X] tag)
  MT         zero_shot, five_shot             (both directions, set by `direction`)
  sentiment  zero_shot, five_shot
  NER        few_shot                         (tag definitions + JSON span output)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Callable

PROMPT_SET_VERSION = "v1"


@dataclass(frozen=True)
class Template:
    task: str
    regime: str
    version: str
    system: str
    render: Callable[..., str]  # kwargs -> user message
    note: str = ""

    @property
    def id(self) -> str:
        return f"{self.task}/{self.regime}/{self.version}"

    @property
    def hash(self) -> str:
        """Hash of the system prompt + the rendered source, for provenance.

        The render function's source is included so a logic change (not just a
        wording change) also moves the hash.
        """
        import inspect

        blob = self.system + "\n--\n" + inspect.getsource(self.render)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- MCQ

_MCQ_SYSTEM = (
    "You are answering multiple-choice questions about Mizoram, a state in "
    "northeast India, drawn from its civil-service examinations. Use only your "
    "own knowledge."
)


def _fmt_choices(choices: dict[str, str]) -> str:
    return "\n".join(f"{k}. {choices[k]}" for k in sorted(choices))


def _mcq_zero_shot(question: str, choices: dict[str, str], **_: object) -> str:
    return (
        f"Question: {question}\n"
        f"Options:\n{_fmt_choices(choices)}\n\n"
        "Answer with the correct option letter (A, B, C, or D) only."
    )


def _mcq_five_shot(
    question: str, choices: dict[str, str], exemplars: list[dict], **_: object
) -> str:
    shots = []
    for ex in exemplars[:5]:
        shots.append(
            f"Question: {ex['question']}\n"
            f"Options:\n{_fmt_choices(ex['choices'])}\n"
            f"Answer: {ex['answer']}"
        )
    body = "\n\n".join(shots)
    return (
        f"{body}\n\n"
        f"Question: {question}\n"
        f"Options:\n{_fmt_choices(choices)}\n\n"
        "Answer with the correct option letter (A, B, C, or D) only."
    )


def _mcq_cot(question: str, choices: dict[str, str], **_: object) -> str:
    return (
        f"Question: {question}\n"
        f"Options:\n{_fmt_choices(choices)}\n\n"
        "Think step by step, then give your final answer on the last line in "
        "exactly this format: [ANSWER: X]  (where X is A, B, C, or D)."
    )


# --------------------------------------------------------------------------- MT

_MT_SYSTEM = (
    "You are a professional translator working between English and Mizo "
    "(Lushai, ISO 639-3 lus), the language of Mizoram, northeast India."
)

_LANG = {"en": "English", "mz": "Mizo"}


def _mt_zero_shot(source: str, direction: str, **_: object) -> str:
    src, tgt = direction.split("2")
    return (
        f"Translate the following text from {_LANG[src]} to {_LANG[tgt]}. "
        f"Output only the translation, with no preamble or notes.\n\n"
        f"{_LANG[src]}: {source}\n{_LANG[tgt]}:"
    )


def _mt_five_shot(source: str, direction: str, exemplars: list[dict], **_: object) -> str:
    src, tgt = direction.split("2")
    shots = "\n\n".join(
        f"{_LANG[src]}: {ex[src]}\n{_LANG[tgt]}: {ex[tgt]}" for ex in exemplars[:5]
    )
    return (
        f"Translate from {_LANG[src]} to {_LANG[tgt]}. Output only the translation.\n\n"
        f"{shots}\n\n{_LANG[src]}: {source}\n{_LANG[tgt]}:"
    )


# --------------------------------------------------------------------------- sentiment

_SENT_SYSTEM = (
    "You classify the sentiment of short social-media comments written in Mizo "
    "(Lushai), often code-mixed with English."
)


def _sent_zero_shot(text: str, **_: object) -> str:
    return (
        f"Comment: {text}\n\n"
        "Classify the overall sentiment as Positive, Neutral, or Negative. "
        "Answer with one word only."
    )


def _sent_five_shot(text: str, exemplars: list[dict], **_: object) -> str:
    shots = "\n".join(f"Comment: {ex['text']}\nSentiment: {ex['label']}" for ex in exemplars[:6])
    return (
        f"{shots}\n\n"
        f"Comment: {text}\nSentiment: "
        "(answer Positive, Neutral, or Negative with one word only)"
    )


# --------------------------------------------------------------------------- NER

_NER_SYSTEM = (
    "You extract named entities from Mizo (Lushai) news sentences. "
    "Return only entities that are explicitly present in the text."
)

# Kept in one place so the prompt and the scoring tagset cannot drift apart.
NER_TAG_DEFINITIONS = {
    "NEP": "person name",
    "NEL": "location or place name",
    "NEO": "organisation, institution, department, or named body",
    "NEMI": "miscellaneous named entity (named scheme, post, grade, award, event name)",
    "NETI": "time expression (date, day, month, year, explicit period)",
    "NEF": "facility or infrastructure (office building, road, bridge, named venue)",
    "NEAR": "artefact or vehicle (named product, vehicle type)",
}


def _ner_few_shot(tokens: list[str], exemplars: list[dict], **_: object) -> str:
    defs = "\n".join(f"  {t}: {d}" for t, d in NER_TAG_DEFINITIONS.items())
    shots = []
    for ex in exemplars[:3]:
        shots.append(
            f'Sentence: {" ".join(ex["tokens"])}\n'
            f"Entities: {ex['entities_json']}"
        )
    shot_block = "\n\n".join(shots)
    return (
        f"Entity types:\n{defs}\n\n"
        "For each sentence, list every named entity as a JSON array of objects "
        '{\"text\": <exact substring>, \"type\": <type code>}. '
        "Use the exact surface text from the sentence. If there are none, output [].\n\n"
        f"{shot_block}\n\n"
        f'Sentence: {" ".join(tokens)}\n'
        "Entities:"
    )


# --------------------------------------------------------------------------- registry

_TEMPLATES: list[Template] = [
    Template("mcq", "zero_shot", PROMPT_SET_VERSION, _MCQ_SYSTEM, _mcq_zero_shot),
    Template("mcq", "five_shot", PROMPT_SET_VERSION, _MCQ_SYSTEM, _mcq_five_shot),
    Template("mcq", "cot", PROMPT_SET_VERSION, _MCQ_SYSTEM, _mcq_cot,
             note="expects a trailing [ANSWER: X] tag"),
    Template("mt", "zero_shot", PROMPT_SET_VERSION, _MT_SYSTEM, _mt_zero_shot),
    Template("mt", "five_shot", PROMPT_SET_VERSION, _MT_SYSTEM, _mt_five_shot),
    Template("sentiment", "zero_shot", PROMPT_SET_VERSION, _SENT_SYSTEM, _sent_zero_shot),
    Template("sentiment", "five_shot", PROMPT_SET_VERSION, _SENT_SYSTEM, _sent_five_shot),
    Template("ner", "few_shot", PROMPT_SET_VERSION, _NER_SYSTEM, _ner_few_shot),
]

REGISTRY: dict[tuple[str, str], Template] = {(t.task, t.regime): t for t in _TEMPLATES}


def get_template(task: str, regime: str) -> Template:
    try:
        return REGISTRY[(task, regime)]
    except KeyError:
        avail = ", ".join(f"{t}/{r}" for t, r in REGISTRY)
        raise KeyError(f"no template for {task}/{regime}; available: {avail}") from None


def all_template_hashes() -> dict[str, str]:
    """Task/regime -> hash. Written into every run manifest for provenance."""
    return {t.id: t.hash for t in _TEMPLATES}
