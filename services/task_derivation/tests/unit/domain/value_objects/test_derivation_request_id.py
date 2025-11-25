"""Tests for DerivationRequestId value object."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.task_derivation.requests.derivation_request_id import (
    DerivationRequestId,
)


def test_derivation_request_id_strips_value() -> None:
    identifier = DerivationRequestId("job-123")
    assert str(identifier) == "job-123"


def test_derivation_request_id_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        DerivationRequestId(" ")

