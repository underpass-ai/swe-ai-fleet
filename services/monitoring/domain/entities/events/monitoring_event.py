"""Monitoring event domain entity."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MonitoringEvent:
    """
    Domain entity representing a system monitoring event.

    Encapsulates event data from any source (NATS, logs, etc.)
    """

    source: str
    type: str
    subject: str
    timestamp: str
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate event parameters.

        Raises:
            ValueError: If parameters are invalid
        """
        if not self.source or len(self.source.strip()) == 0:
            raise ValueError("source cannot be empty")
        if not self.type or len(self.type.strip()) == 0:
            raise ValueError("type cannot be empty")
        if not self.subject or len(self.subject.strip()) == 0:
            raise ValueError("subject cannot be empty")
        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")
        if self.data is None:
            raise ValueError("data cannot be None")

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dict with event data
        """
        return {
            "source": self.source,
            "type": self.type,
            "subject": self.subject,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def create(
        cls,
        source: str,
        type: str,
        subject: str,
        data: dict[str, Any],
        metadata: dict[str, Any] = None,
    ) -> "MonitoringEvent":
        """Factory method to create validated MonitoringEvent.

        Args:
            source: Event source
            type: Event type
            subject: Event subject
            data: Event payload
            metadata: Optional metadata

        Returns:
            MonitoringEvent instance

        Raises:
            ValueError: If validation fails
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        instance = cls(
            source=source,
            type=type,
            subject=subject,
            timestamp=timestamp,
            data=data,
            metadata=metadata or {},
        )
        instance.validate()
        return instance

    @classmethod
    def from_nats_message(
        cls,
        subject: str,
        data: dict[str, Any],
        sequence: int = None,
    ) -> "MonitoringEvent":
        """Factory to create event from NATS message.

        Args:
            subject: NATS subject
            data: Message data (already parsed)
            sequence: Optional message sequence number

        Returns:
            MonitoringEvent instance
        """
        metadata = {}
        if sequence is not None:
            metadata["sequence"] = sequence

        return cls.create(
            source="NATS",
            type=subject,
            subject=subject,
            data=data,
            metadata=metadata,
        )
