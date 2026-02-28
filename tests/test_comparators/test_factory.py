"""Tests for skilleval.comparators — factory and registry."""

from __future__ import annotations

import pytest

from skilleval.comparators import (
    COMPARATORS,
    CsvOrderedComparator,
    CsvUnorderedComparator,
    FieldSubsetComparator,
    FileHashComparator,
    JsonExactComparator,
    get_comparator,
)


class TestGetComparator:
    @pytest.mark.parametrize(
        "name,expected_cls",
        [
            ("json_exact", JsonExactComparator),
            ("csv_ordered", CsvOrderedComparator),
            ("csv_unordered", CsvUnorderedComparator),
            ("field_subset", FieldSubsetComparator),
            ("file_hash", FileHashComparator),
        ],
    )
    def test_known_comparators(self, name: str, expected_cls: type):
        comp = get_comparator(name)
        assert isinstance(comp, expected_cls)

    def test_custom_comparator_exists_in_registry(self):
        assert "custom" in COMPARATORS

    def test_unknown_name_raises(self):
        with pytest.raises(ValueError, match="Unknown comparator"):
            get_comparator("nonexistent_comparator")

    def test_error_lists_available(self):
        with pytest.raises(ValueError, match="json_exact"):
            get_comparator("bad_name")

    def test_all_six_registered(self):
        expected_names = {
            "json_exact", "csv_ordered", "csv_unordered",
            "field_subset", "file_hash", "custom",
        }
        assert set(COMPARATORS.keys()) == expected_names
