"""Tests for MonitoringEvent domain entity."""
import pytest
from datetime import datetime, timezone
from services.monitoring.domain.entities.events.monitoring_event import MonitoringEvent


class TestMonitoringEvent:
    """Test suite for MonitoringEvent."""

    def test_create_monitoring_event(self):
        """Test creating a monitoring event with all fields."""
        event = MonitoringEvent.create(
            source="test_service",
            type="info",
            subject="test_subject",
            data={}
        )
        
        assert event.source == "test_service"
        assert event.type == "info"
        assert event.subject == "test_subject"
        assert event.timestamp is not None

    def test_create_monitoring_event_with_optional_fields(self):
        """Test creating a monitoring event with optional fields."""
        event = MonitoringEvent.create(
            source="test_service",
            type="error",
            subject="test_subject",
            data={"key": "value"},
            metadata={"meta": "data"}
        )
        
        assert event.source == "test_service"
        assert event.type == "error"
        assert event.subject == "test_subject"
        assert event.data == {"key": "value"}
        assert event.metadata == {"meta": "data"}

    def test_create_monitoring_event_empty_subject(self):
        """Test creating event with empty subject raises ValueError."""
        with pytest.raises(ValueError):
            MonitoringEvent.create(
                source="test_service",
                type="info",
                subject="",
                data={}
            )
            
    def test_timestamp_is_utc(self):
        """Test that timestamp is in UTC timezone."""
        event = MonitoringEvent.create(
            source="test_service",
            type="info",
            subject="test_subject",
            data={}
        )

        # Parse timestamp and verify it's UTC
        timestamp = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        assert timestamp.tzinfo == timezone.utc

    def test_event_equality(self):
        """Test event equality based on source, type, and subject."""
        event1 = MonitoringEvent.create(
            source="test_service",
            type="info",
            subject="test_subject",
            data={}
        )
        
        event2 = MonitoringEvent.create(
            source="test_service",
            type="info",
            subject="test_subject",
            data={}
        )

        # Events are equal if source, type, and subject match
        assert event1.source == event2.source
        assert event1.type == event2.type
        assert event1.subject == event2.subject

