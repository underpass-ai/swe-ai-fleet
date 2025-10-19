"""Tests for DeliberationStatusMapper."""

from services.orchestrator.infrastructure.dto import orchestrator_dto
from services.orchestrator.infrastructure.mappers import DeliberationStatusMapper


class TestDeliberationStatusMapper:
    """Test suite for DeliberationStatusMapper."""
    
    def test_string_to_proto_enum_pending(self):
        """Test converting PENDING status."""
        proto_status = DeliberationStatusMapper.string_to_proto_enum(
            "DELIBERATION_STATUS_PENDING"
        )
        assert proto_status == orchestrator_dto.DELIBERATION_STATUS_PENDING
    
    def test_string_to_proto_enum_in_progress(self):
        """Test converting IN_PROGRESS status."""
        proto_status = DeliberationStatusMapper.string_to_proto_enum(
            "DELIBERATION_STATUS_IN_PROGRESS"
        )
        assert proto_status == orchestrator_dto.DELIBERATION_STATUS_IN_PROGRESS
    
    def test_string_to_proto_enum_completed(self):
        """Test converting COMPLETED status."""
        proto_status = DeliberationStatusMapper.string_to_proto_enum(
            "DELIBERATION_STATUS_COMPLETED"
        )
        assert proto_status == orchestrator_dto.DELIBERATION_STATUS_COMPLETED
    
    def test_string_to_proto_enum_failed(self):
        """Test converting FAILED status."""
        proto_status = DeliberationStatusMapper.string_to_proto_enum(
            "DELIBERATION_STATUS_FAILED"
        )
        assert proto_status == orchestrator_dto.DELIBERATION_STATUS_FAILED
    
    def test_string_to_proto_enum_timeout(self):
        """Test converting TIMEOUT status."""
        proto_status = DeliberationStatusMapper.string_to_proto_enum(
            "DELIBERATION_STATUS_TIMEOUT"
        )
        assert proto_status == orchestrator_dto.DELIBERATION_STATUS_TIMEOUT
    
    def test_string_to_proto_enum_unknown(self):
        """Test converting unknown status returns UNKNOWN."""
        proto_status = DeliberationStatusMapper.string_to_proto_enum("INVALID_STATUS")
        assert proto_status == orchestrator_dto.DELIBERATION_STATUS_UNKNOWN
    
    def test_proto_enum_to_string_pending(self):
        """Test converting protobuf enum to string."""
        status_str = DeliberationStatusMapper.proto_enum_to_string(
            orchestrator_dto.DELIBERATION_STATUS_PENDING
        )
        assert status_str == "DELIBERATION_STATUS_PENDING"
    
    def test_proto_enum_to_string_unknown(self):
        """Test converting unknown enum returns UNKNOWN string."""
        status_str = DeliberationStatusMapper.proto_enum_to_string(999)
        assert status_str == "DELIBERATION_STATUS_UNKNOWN"

