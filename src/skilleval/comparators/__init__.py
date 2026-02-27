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

COMPARATORS: dict[str, type] = {
    "json_exact": JsonExactComparator,
    "csv_unordered": CsvUnorderedComparator,
    "csv_ordered": CsvOrderedComparator,
    "field_subset": FieldSubsetComparator,
    "file_hash": FileHashComparator,
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
    "CustomComparator",
]


def get_comparator(name: str, **kwargs: Any) -> Comparator:
    """Create a comparator instance by name.

    Args:
        name: Comparator name (must be a key in COMPARATORS).
        **kwargs: Extra arguments passed to the comparator constructor
                  (e.g. custom_script for CustomComparator).

    Returns:
        A Comparator instance.

    Raises:
        ValueError: If the comparator name is unknown.
    """
    cls = COMPARATORS.get(name)
    if cls is None:
        available = ", ".join(sorted(COMPARATORS))
        raise ValueError(f"Unknown comparator '{name}'. Available: {available}")
    return cls(**kwargs)
