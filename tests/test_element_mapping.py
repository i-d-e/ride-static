"""Validate config/element-mapping.yaml against the actual domain model.

Pins the Backend-Frontend contract at build time: every Block and Inline
dataclass exported by src.model must have a mapping entry, and every
mapping entry must reference a real dataclass. Drift in either direction
fails the test.

Phase 8 will additionally check that every `template:` path exists under
templates/html/; for now the templates do not yet exist (greenfield).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.model import block as block_mod
from src.model import inline as inline_mod

MAPPING_PATH = Path(__file__).resolve().parent.parent / "config" / "element-mapping.yaml"

# Discriminator-bearing classes whose `kind` field must be enumerated in `variants`.
_VARIANT_KINDS = {
    "List": {"bulleted", "ordered", "labeled"},
    "Figure": {"graphic", "code_example"},
}

_REFERENCE_BUCKETS = {"local", "criteria", "external", "orphan"}


@pytest.fixture(scope="module")
def mapping() -> dict:
    return yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))


def _model_class_names(module) -> set[str]:
    """Concrete dataclass names exposed by a model module."""
    return {
        name for name in dir(module)
        if not name.startswith("_")
        and isinstance(getattr(module, name), type)
        and getattr(getattr(module, name), "__dataclass_fields__", None) is not None
    }


def test_top_level_keys(mapping):
    assert set(mapping) >= {"blocks", "inlines", "extensibility"}


def test_blocks_cover_every_dataclass(mapping):
    """Every Block dataclass in src.model.block has a mapping entry, and vice versa."""
    model_blocks = _model_class_names(block_mod) - {
        "Block",  # Union alias
        "ListItem", "TableRow", "TableCell",  # structural sub-types, rendered by parent
    }
    mapped = set(mapping["blocks"])
    assert model_blocks == mapped, (
        f"block mapping drift: only-in-model={model_blocks - mapped}, "
        f"only-in-yaml={mapped - model_blocks}"
    )


def test_inlines_cover_every_dataclass(mapping):
    model_inlines = _model_class_names(inline_mod) - {"Inline"}
    mapped = set(mapping["inlines"])
    assert model_inlines == mapped, (
        f"inline mapping drift: only-in-model={model_inlines - mapped}, "
        f"only-in-yaml={mapped - model_inlines}"
    )


@pytest.mark.parametrize("klass,kinds", _VARIANT_KINDS.items())
def test_variants_cover_all_kinds(mapping, klass, kinds):
    """List and Figure carry a `kind` discriminator; the YAML must enumerate every value."""
    entry = mapping["blocks"][klass]
    variants = set((entry.get("variants") or {}).keys())
    assert variants == kinds, f"{klass} variants drift: yaml={variants} model={kinds}"


def test_reference_buckets_complete(mapping):
    """Reference must enumerate all four resolution buckets from pipeline.md."""
    by_bucket = mapping["inlines"]["Reference"].get("by_bucket") or {}
    assert set(by_bucket) == _REFERENCE_BUCKETS


def test_extensibility_strategy_known(mapping):
    strategy = mapping["extensibility"]["unknown_element_strategy"]
    assert strategy in {"warn-and-render-text", "raise"}
