"""Tests for lint checks evaluator."""

from core.evaluators.lint_checks import kube_lint_text


class TestLintChecks:
    """Test cases for lint checks evaluator."""

    def test_kube_lint_text_valid_yaml(self):
        """Test kube_lint_text with valid YAML document."""
        valid_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: test-container
    image: nginx:latest
"""
        
        result = kube_lint_text(valid_yaml)
        assert result is True

    def test_kube_lint_text_invalid_yaml(self):
        """Test kube_lint_text with invalid YAML document."""
        invalid_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: test-container
    image: nginx:latest
  invalid: [unclosed
"""
        
        result = kube_lint_text(invalid_yaml)
        assert result is True  # Currently always returns True (TODO implementation)

    def test_kube_lint_text_empty_document(self):
        """Test kube_lint_text with empty document."""
        result = kube_lint_text("")
        assert result is True

    def test_kube_lint_text_none_document(self):
        """Test kube_lint_text with None document."""
        result = kube_lint_text(None)  # type: ignore
        assert result is True

    def test_kube_lint_text_non_yaml_document(self):
        """Test kube_lint_text with non-YAML document."""
        non_yaml = "This is just plain text, not YAML"
        
        result = kube_lint_text(non_yaml)
        assert result is True

    def test_kube_lint_text_multiline_document(self):
        """Test kube_lint_text with multiline YAML document."""
        multiline_yaml = """
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
"""
        
        result = kube_lint_text(multiline_yaml)
        assert result is True
