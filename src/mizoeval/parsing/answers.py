"""Extract structured answers from free-form model output.

Parsing is where benchmark papers quietly lose accuracy points. A model that
knows the answer but writes "The answer is B." instead of "B" scores zero under
a naive parser, and the paper then reports a knowledge gap that is really a
formatting gap. Every parser here therefore tries an ordered series of
strategies, from strictest to loosest, and reports *which* one fired -- so the
run can quantify how much of the score depends on lenient parsing, and report
the parse-failure rate rather than absorbing it into the accuracy.

`ParseResult.strategy == "none"` is a genuine failure and must be counted
separately from a wrong answer: they mean different things.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

ABCD = ("A", "B", "C", "D")


@dataclass
class ParseResult:
    value: Any | None
    strategy: str  # which rule matched; "none" means unparseable

    @property
    def ok(self) -> bool:
        return self.value is not None


# --------------------------------------------------------------------------- MCQ

# Ordered strictest-first. An explicit tag beats a bare letter, which beats a
# letter recovered from prose, because each later rule is more likely to pick up
# an incidental capital letter rather than the model's actual choice.
_MCQ_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("answer_tag", re.compile(r"\[\s*ANSWER\s*:\s*([A-Z])\s*\]", re.IGNORECASE)),
    ("final_answer", re.compile(r"(?:final\s+)?answer\s*(?:is)?\s*[:\-]?\s*\(?([A-Z])\)?\b",
                                re.IGNORECASE)),
    ("bare_letter", re.compile(r"^\s*\(?([A-Z])\)?\s*[.:)]?\s*$")),
    ("leading_letter", re.compile(r"^\s*\(?([A-Z])\)?\s*[.:)\-]\s+")),
    ("option_line", re.compile(r"^\s*option\s+([A-Z])\b", re.IGNORECASE | re.MULTILINE)),
]


def parse_mcq(text: str, valid: tuple[str, ...] = ABCD) -> ParseResult:
    """Recover the chosen option letter from a model's reply."""
    if not text or not text.strip():
        return ParseResult(None, "none")
    stripped = text.strip()

    for name, rx in _MCQ_RULES:
        m = rx.search(stripped)
        if m and m.group(1).upper() in valid:
            return ParseResult(m.group(1).upper(), name)

    # Last resort: a single distinct valid letter appearing anywhere as a
    # standalone token. Ambiguous when several appear, so we require exactly one
    # -- guessing among candidates would inflate the score with coin flips.
    found = {t.upper() for t in re.findall(r"\b([A-Za-z])\b", stripped) if t.upper() in valid}
    if len(found) == 1:
        return ParseResult(found.pop(), "unique_letter")
    return ParseResult(None, "none")


# --------------------------------------------------------------------------- sentiment

SENTIMENT_LABELS = ("Positive", "Neutral", "Negative")


def parse_sentiment(text: str, labels: tuple[str, ...] = SENTIMENT_LABELS) -> ParseResult:
    if not text or not text.strip():
        return ParseResult(None, "none")
    stripped = text.strip()
    lowered = stripped.lower()
    lookup = {l.lower(): l for l in labels}

    if lowered in lookup:
        return ParseResult(lookup[lowered], "exact")

    m = re.search(r"(?:sentiment|label|answer)\s*(?:is)?\s*[:\-]?\s*(\w+)", lowered)
    if m and m.group(1) in lookup:
        return ParseResult(lookup[m.group(1)], "labelled")

    # Require a unique mention: a reply that weighs "positive" against
    # "negative" has not committed to either, and picking one would be noise.
    hits = {lookup[l] for l in lookup if re.search(rf"\b{re.escape(l)}\b", lowered)}
    if len(hits) == 1:
        return ParseResult(hits.pop(), "unique_mention")
    if len(hits) > 1:
        # A closing statement is a real commitment, so prefer the last mention.
        last = max(hits, key=lambda h: lowered.rfind(h.lower()))
        return ParseResult(last, "last_mention")
    return ParseResult(None, "none")


# --------------------------------------------------------------------------- NER

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_entity_json(text: str) -> ParseResult:
    """Parse a JSON list of `{text, type}` entity spans.

    Generative models are poor at emitting token-aligned CoNLL directly, so the
    prompt asks for spans and the alignment happens afterwards. Models very
    often wrap JSON in a code fence or add a sentence around it, so both are
    tolerated.
    """
    if not text or not text.strip():
        return ParseResult(None, "none")

    candidates: list[tuple[str, str]] = []
    m = _JSON_BLOCK.search(text)
    if m:
        candidates.append(("fenced", m.group(1).strip()))
    candidates.append(("raw", text.strip()))
    start, end = text.find("["), text.rfind("]")
    if 0 <= start < end:
        candidates.append(("bracket_slice", text[start:end + 1]))

    for name, blob in candidates:
        try:
            data = json.loads(blob)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            data = data.get("entities", data.get("spans", []))
        if not isinstance(data, list):
            continue
        out = []
        for item in data:
            if isinstance(item, dict):
                surface = item.get("text") or item.get("entity") or item.get("span")
                etype = item.get("type") or item.get("label") or item.get("tag")
                if surface and etype:
                    out.append({"text": str(surface), "type": str(etype).upper()})
        return ParseResult(out, name)
    return ParseResult(None, "none")


def align_spans_to_tokens(
    tokens: list[str], spans: list[dict[str, str]], valid_types: set[str]
) -> list[str]:
    """Project surface spans back onto the token sequence as BIO tags.

    Longest spans are matched first so that a nested or overlapping shorter span
    cannot claim tokens belonging to the longer one. A span that matches no
    token run is dropped: inventing an alignment would fabricate a prediction
    the model never made.
    """
    tags = ["O"] * len(tokens)
    lowered = [t.lower() for t in tokens]

    for span in sorted(spans, key=lambda s: -len(s["text"].split())):
        etype = span["type"].upper()
        if etype not in valid_types:
            continue
        want = [w.lower() for w in span["text"].split()]
        if not want:
            continue
        for i in range(len(tokens) - len(want) + 1):
            if lowered[i:i + len(want)] != want:
                continue
            if any(t != "O" for t in tags[i:i + len(want)]):
                continue  # already claimed by a longer span
            tags[i] = f"B-{etype}"
            for j in range(i + 1, i + len(want)):
                tags[j] = f"I-{etype}"
            break
    return tags


# --------------------------------------------------------------------------- MT


def clean_translation(text: str) -> str:
    """Strip the scaffolding models wrap around a requested translation.

    Preambles like "Sure! Here is the translation:" are not part of the output
    and would be scored as insertions against the reference, penalising a
    correct translation for its politeness.
    """
    if not text:
        return ""
    out = text.strip()

    m = _JSON_BLOCK.search(out)
    if m:
        out = m.group(1).strip()

    out = re.sub(
        r"^\s*(sure|certainly|of course|here'?s?|here is|translation)\b[^\n:]*:\s*",
        "", out, flags=re.IGNORECASE,
    )
    # Models often add a trailing gloss or note after a blank line; keep the
    # first block, which is the translation itself.
    parts = [p.strip() for p in out.split("\n\n") if p.strip()]
    if parts:
        out = parts[0]
    out = re.sub(r"^\s*[\"'](.*)[\"']\s*$", r"\1", out, flags=re.DOTALL)
    return out.strip()
