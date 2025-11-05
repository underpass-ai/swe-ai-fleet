"""Unit tests for CapabilityCollection."""

import pytest

from core.agents_and_tools.common.domain.entities.capability import Capability
from core.agents_and_tools.common.domain.entities.capability_collection import (
    CapabilityCollection,
)


class TestCapabilityCollectionCreation:
    """Test CapabilityCollection creation."""

    def test_create_collection_from_tuple(self):
        """Test creating collection from tuple."""
        caps = (
            Capability("files", "read_file"),
            Capability("git", "commit"),
        )

        collection = CapabilityCollection(items=caps)

        assert collection.count() == 2

    def test_create_collection_from_list(self):
        """Test creating collection from list using from_list."""
        caps = [
            Capability("files", "read_file"),
            Capability("git", "commit"),
        ]

        collection = CapabilityCollection.from_list(caps)

        assert collection.count() == 2

    def test_create_collection_rejects_empty(self):
        """Test fail-fast on empty collection."""
        with pytest.raises(ValueError, match="CapabilityCollection cannot be empty"):
            CapabilityCollection(items=())


class TestCapabilityCollectionQueries:
    """Test CapabilityCollection query methods."""

    def test_has_capability_returns_true_for_existing(self):
        """Test has_capability finds existing capabilities."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
            Capability("git", "commit"),
        ])

        assert collection.has_capability("files", "read_file") is True
        assert collection.has_capability("git", "commit") is True

    def test_has_capability_returns_false_for_missing(self):
        """Test has_capability returns False for missing."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
        ])

        assert collection.has_capability("git", "commit") is False

    def test_get_by_tool_filters_correctly(self):
        """Test get_by_tool returns capabilities for specific tool."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
            Capability("files", "write_file"),
            Capability("git", "commit"),
        ])

        files_caps = collection.get_by_tool("files")
        assert len(files_caps) == 2
        assert all(cap.tool == "files" for cap in files_caps)


class TestCapabilityCollectionFiltering:
    """Test CapabilityCollection filtering methods."""

    def test_get_write_capabilities_filters_writes(self):
        """Test get_write_capabilities returns only write operations."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
            Capability("files", "write_file"),
            Capability("git", "log"),
            Capability("git", "commit"),
        ])

        writes = collection.get_write_capabilities()
        assert len(writes) == 2
        assert all(cap.is_write_operation() for cap in writes)

    def test_get_read_capabilities_filters_reads(self):
        """Test get_read_capabilities returns only read operations."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
            Capability("files", "write_file"),
            Capability("git", "log"),
            Capability("git", "commit"),
        ])

        reads = collection.get_read_capabilities()
        assert len(reads) == 2
        assert all(not cap.is_write_operation() for cap in reads)

    def test_filter_by_tools_returns_subset(self):
        """Test filter_by_tools returns new collection with only allowed tools."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
            Capability("git", "commit"),
            Capability("docker", "build"),
        ])

        filtered = collection.filter_by_tools(frozenset(["files", "git"]))

        assert filtered.count() == 2
        assert all(cap.tool in ["files", "git"] for cap in filtered)

    def test_filter_by_tools_rejects_empty_result(self):
        """Test filter_by_tools raises if result is empty."""
        collection = CapabilityCollection.from_list([Capability("files", "read_file")])

        with pytest.raises(ValueError, match="Filtering resulted in empty collection"):
            collection.filter_by_tools(frozenset(["docker"]))


class TestCapabilityCollectionHelpers:
    """Test CapabilityCollection helper methods."""

    def test_get_tool_names_returns_unique_sorted(self):
        """Test get_tool_names returns unique sorted tool names."""
        collection = CapabilityCollection.from_list([
            Capability("git", "commit"),
            Capability("files", "read_file"),
            Capability("files", "write_file"),
            Capability("docker", "build"),
        ])

        names = collection.get_tool_names()
        assert names == ["docker", "files", "git"]  # Unique and sorted

    def test_to_list_returns_list(self):
        """Test to_list returns list of capabilities."""
        caps_list = [Capability("files", "read_file"), Capability("git", "commit")]
        collection = CapabilityCollection.from_list(caps_list)

        result = collection.to_list()
        assert isinstance(result, list)
        assert len(result) == 2


class TestCapabilityCollectionProtocols:
    """Test CapabilityCollection supports Python protocols."""

    def test_iteration(self):
        """Test iteration over collection."""
        caps = [Capability("files", "read_file"), Capability("git", "commit")]
        collection = CapabilityCollection.from_list(caps)

        iterated = list(collection)
        assert len(iterated) == 2

    def test_len_function(self):
        """Test len() works."""
        collection = CapabilityCollection.from_list([
            Capability("files", "read_file"),
            Capability("git", "commit"),
        ])

        assert len(collection) == 2

    def test_contains_operator(self):
        """Test 'in' operator works."""
        cap = Capability("files", "read_file")
        collection = CapabilityCollection.from_list([cap])

        assert cap in collection
        assert Capability("git", "commit") not in collection

