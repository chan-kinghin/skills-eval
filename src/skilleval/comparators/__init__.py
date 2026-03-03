"""Comparator registry and factory."""

from __future__ import annotations

from typing import Any

from skilleval.comparators.base import Comparator
from skilleval.comparators.csv_ordered import CsvOrderedComparator
from skilleval.comparators.csv_unordered import CsvUnorderedComparator
from skilleval.comparators.custom import CustomComparator
from skilleval.comparators.field_subset import FieldSubsetComparator
from skilleval.comparators.file_hash import FileHashComparator
from skilleval.comparators.json_exact import JsonExactComparator
from skilleval.comparators.text_contains import TextContainsComparator
from skilleval.comparators.text_exact import TextExactComparator

COMPARATORS: dict[str, type[Comparator]] = {
    "json_exact": JsonExactComparator,
    "csv_unordered": CsvUnorderedComparator,
    "csv_ordered": CsvOrderedComparator,
    "field_subset": FieldSubsetComparator,
    "file_hash": FileHashComparator,
    "text_exact": TextExactComparator,
    "text_contains": TextContainsComparator,
    "custom": CustomComparator,
}

__all__ = [
    "Comparator",
    "COMPARATORS",
    "get_comparator",
    "JsonExactComparator",
    "CsvUnorderedComparator",
    "CsvOrderedComparator",
    "FieldSubsetComparator",
    "FileHashComparator",
    "TextExactComparator",
    "TextContainsComparator",
    "CustomComparator",
]


def get_comparator(name: str, **kwargs: Any) -> Comparator:
    """Create a comparator instance by name."""
    cls = COMPARATORS.get(name)
    if cls is None:
        available = ", ".join(sorted(COMPARATORS))
        raise ValueError(f"Unknown comparator '{name}'. Available: {available}")
    return cls(**kwargs)
