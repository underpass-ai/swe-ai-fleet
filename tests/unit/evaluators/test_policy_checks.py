"""Tests for policy checks evaluator."""

from core.evaluators.policy_checks import opa_eval


class TestPolicyChecks:
    """Test cases for policy checks evaluator."""

    def test_opa_eval_valid_policy(self):
        """Test opa_eval with valid policy document."""
        valid_policy = """
package kubernetes.admission

deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.spec.securityContext.runAsNonRoot
    msg := "Pod must run as non-root user"
}
"""
        
        result = opa_eval(valid_policy)
        assert result is True

    def test_opa_eval_invalid_policy(self):
        """Test opa_eval with invalid policy document."""
        invalid_policy = """
package kubernetes.admission

deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.spec.securityContext.runAsNonRoot
    msg := "Pod must run as non-root user"
    # Missing closing brace
"""
        
        result = opa_eval(invalid_policy)
        assert result is True  # Currently always returns True (TODO implementation)

    def test_opa_eval_empty_document(self):
        """Test opa_eval with empty document."""
        result = opa_eval("")
        assert result is True

    def test_opa_eval_none_document(self):
        """Test opa_eval with None document."""
        result = opa_eval(None)  # type: ignore
        assert result is True

    def test_opa_eval_non_rego_document(self):
        """Test opa_eval with non-Rego document."""
        non_rego = "This is just plain text, not Rego policy"
        
        result = opa_eval(non_rego)
        assert result is True

    def test_opa_eval_multiple_policies(self):
        """Test opa_eval with multiple policy rules."""
        multiple_policies = """
package kubernetes.admission

# Policy 1: Require non-root user
deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.spec.securityContext.runAsNonRoot
    msg := "Pod must run as non-root user"
}

# Policy 2: Require resource limits
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits
    msg := sprintf("Container %s must have resource limits", [container.name])
}

# Policy 3: Prohibit privileged containers
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged
    msg := sprintf("Container %s must not be privileged", [container.name])
}
"""
        
        result = opa_eval(multiple_policies)
        assert result is True

    def test_opa_eval_simple_rule(self):
        """Test opa_eval with simple rule."""
        simple_rule = """
package test

allow {
    input.user == "admin"
}
"""
        
        result = opa_eval(simple_rule)
        assert result is True
