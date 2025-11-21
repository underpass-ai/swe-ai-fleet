"""Tests for ScoringPort protocol."""

from typing import Any


class MockScoringPort:
    """Mock implementation of ScoringPort for testing."""
    
    def __init__(self, score_value: float = 0.8, validation_result: dict[str, Any] = None):
        self.score_value = score_value
        self.validation_result = validation_result or {"valid": True, "issues": []}
    
    def score(self, proposal: Any) -> float:
        return self.score_value
    
    def validate(self, code: str) -> dict[str, Any]:
        return self.validation_result


class TestScoringPort:
    """Test cases for ScoringPort protocol."""

    def test_scoring_port_protocol_compliance(self):
        """Test that MockScoringPort implements ScoringPort protocol."""
        mock_port = MockScoringPort()
        
        # Verify it has the required methods
        assert hasattr(mock_port, 'score')
        assert hasattr(mock_port, 'validate')
        assert callable(mock_port.score)
        assert callable(mock_port.validate)

    def test_score_method(self):
        """Test score method implementation."""
        mock_port = MockScoringPort(score_value=0.9)
        proposal = {"type": "code_change", "content": "print('hello')"}
        
        result = mock_port.score(proposal)
        
        assert result == 0.9
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_score_method_boundary_values(self):
        """Test score method with boundary values."""
        # Perfect score
        perfect_port = MockScoringPort(score_value=1.0)
        assert perfect_port.score({}) == 1.0
        
        # Worst score
        worst_port = MockScoringPort(score_value=0.0)
        assert worst_port.score({}) == 0.0
        
        # Middle score
        middle_port = MockScoringPort(score_value=0.5)
        assert middle_port.score({}) == 0.5

    def test_validate_method(self):
        """Test validate method implementation."""
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": ["Minor formatting issue"],
            "score": 0.85
        }
        mock_port = MockScoringPort(validation_result=validation_result)
        code = "def hello():\n    print('world')"
        
        result = mock_port.validate(code)
        
        assert result == validation_result
        assert isinstance(result, dict)
        assert "valid" in result

    def test_validate_method_with_issues(self):
        """Test validate method with validation issues."""
        validation_result = {
            "valid": False,
            "issues": ["Syntax error on line 2", "Missing import"],
            "warnings": [],
            "score": 0.2
        }
        mock_port = MockScoringPort(validation_result=validation_result)
        code = "def broken():\n    print('missing quote"
        
        result = mock_port.validate(code)
        
        assert result == validation_result
        assert result["valid"] is False
        assert len(result["issues"]) == 2

    def test_validate_method_empty_code(self):
        """Test validate method with empty code."""
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "score": 1.0
        }
        mock_port = MockScoringPort(validation_result=validation_result)
        
        result = mock_port.validate("")
        
        assert result == validation_result
        assert result["valid"] is True

    def test_scoring_port_with_different_proposal_types(self):
        """Test scoring port with different proposal types."""
        mock_port = MockScoringPort(score_value=0.7)
        
        # Test with string proposal
        result1 = mock_port.score("Simple string proposal")
        assert result1 == 0.7
        
        # Test with dict proposal
        result2 = mock_port.score({"type": "complex", "data": [1, 2, 3]})
        assert result2 == 0.7
        
        # Test with None proposal
        result3 = mock_port.score(None)
        assert result3 == 0.7

    def test_scoring_port_integration(self):
        """Test scoring port integration scenario."""
        mock_port = MockScoringPort(
            score_value=0.8,
            validation_result={
                "valid": True,
                "issues": [],
                "warnings": ["Consider adding type hints"],
                "score": 0.8
            }
        )
        
        proposal = {"type": "feature", "description": "Add new API endpoint"}
        code = "def new_endpoint():\n    return {'status': 'ok'}"
        
        # Score the proposal
        proposal_score = mock_port.score(proposal)
        assert proposal_score == 0.8
        
        # Validate the code
        validation_result = mock_port.validate(code)
        assert validation_result["valid"] is True
        assert validation_result["score"] == 0.8
        assert len(validation_result["warnings"]) == 1
