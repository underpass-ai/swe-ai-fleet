"""Tests for Judge evaluator class."""

from core.evaluators.judge import Judge


class TestJudge:
    """Test cases for Judge evaluator class."""

    def test_judge_review_safe_proposal(self):
        """Test judge review with a safe proposal."""
        judge = Judge()
        proposal = "echo 'Hello World'"
        telemetry = [{"action": "echo", "timestamp": "2024-01-01"}]
        
        result = judge.review(proposal, telemetry)
        
        assert result["risk"] == 0
        assert result["notes"] == []
        assert isinstance(result, dict)

    def test_judge_review_dangerous_proposal(self):
        """Test judge review with a dangerous proposal."""
        judge = Judge()
        proposal = "rm -rf /"
        telemetry = [{"action": "rm", "timestamp": "2024-01-01"}]
        
        result = judge.review(proposal, telemetry)
        
        assert result["risk"] == 100
        assert result["notes"] == []
        assert isinstance(result, dict)

    def test_judge_review_partial_dangerous_proposal(self):
        """Test judge review with proposal containing dangerous pattern."""
        judge = Judge()
        proposal = "echo 'Backup complete' && rm -rf /tmp/backup"
        telemetry = [{"action": "backup", "timestamp": "2024-01-01"}]
        
        result = judge.review(proposal, telemetry)
        
        assert result["risk"] == 100
        assert result["notes"] == []

    def test_judge_review_empty_proposal(self):
        """Test judge review with empty proposal."""
        judge = Judge()
        proposal = ""
        telemetry = []
        
        result = judge.review(proposal, telemetry)
        
        assert result["risk"] == 0
        assert result["notes"] == []

    def test_judge_review_none_telemetry(self):
        """Test judge review with None telemetry."""
        judge = Judge()
        proposal = "ls -la"
        
        result = judge.review(proposal, None)  # type: ignore
        
        assert result["risk"] == 0
        assert result["notes"] == []

    def test_judge_review_multiple_telemetry_entries(self):
        """Test judge review with multiple telemetry entries."""
        judge = Judge()
        proposal = "git status"
        telemetry = [
            {"action": "git", "timestamp": "2024-01-01"},
            {"action": "status", "timestamp": "2024-01-01"},
            {"action": "checkout", "timestamp": "2024-01-02"}
        ]
        
        result = judge.review(proposal, telemetry)
        
        assert result["risk"] == 0
        assert result["notes"] == []

    def test_judge_review_case_sensitive_dangerous_pattern(self):
        """Test that dangerous pattern detection is case sensitive."""
        judge = Judge()
        proposal = "RM -RF /"  # Different case
        
        result = judge.review(proposal, [])
        
        assert result["risk"] == 0  # Should not detect due to case difference
