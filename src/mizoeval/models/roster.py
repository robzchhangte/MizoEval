"""Load the model roster from `configs/models.yaml`.

The roster is data, not code, so adding or dropping a model is a config edit and
the set of models in the paper is auditable from one file. Every entry pins an
exact `model_id`; the loader rejects obvious alias strings so an unpinned model
cannot silently enter a run.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mizoeval.models.base import ModelSpec

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROSTER = ROOT / "configs" / "models.yaml"

_ALIASES = {"latest", "newest", "stable", "preview"}


def load_roster(path: Path | str = DEFAULT_ROSTER, enabled_only: bool = True) -> list[ModelSpec]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    defaults = doc.get("defaults", {}) or {}
    specs: list[ModelSpec] = []

    for entry in doc.get("models", []):
        if enabled_only and not entry.get("enabled", True):
            continue
        model_id = str(entry["model_id"])
        if any(a in model_id.lower().split("-") or a in model_id.lower().split("/")
               for a in _ALIASES):
            raise ValueError(
                f"roster entry {entry['name']!r} uses an alias in model_id "
                f"({model_id!r}); pin an exact version so runs stay reproducible"
            )
        params = {**(defaults.get("params") or {}), **(entry.get("params") or {})}
        specs.append(
            ModelSpec(
                name=entry["name"],
                provider=entry["provider"],
                model_id=model_id,
                price_in=float(entry.get("price_in", 0.0)),
                price_out=float(entry.get("price_out", 0.0)),
                params=params or None,
            )
        )

    names = [s.name for s in specs]
    if len(names) != len(set(names)):
        raise ValueError("roster has duplicate model names")
    return specs


def get_spec(name: str, path: Path | str = DEFAULT_ROSTER) -> ModelSpec:
    for spec in load_roster(path, enabled_only=False):
        if spec.name == name:
            return spec
    raise KeyError(f"no roster entry named {name!r} in {path}")
