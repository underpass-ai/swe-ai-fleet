package tools

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestSecurityScanContainerHandler_HeuristicFallbackWhenTrivyMissing(t *testing.T) {
	root := t.TempDir()
	dockerfile := "FROM alpine:latest\nRUN curl -sSL https://example.com/install.sh | sh\n"
	if err := os.WriteFile(filepath.Join(root, "Dockerfile"), []byte(dockerfile), 0o644); err != nil {
		t.Fatalf("write Dockerfile failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				if spec.Command != "trivy" {
					t.Fatalf("expected first command trivy, got %q", spec.Command)
				}
				return app.CommandResult{
					ExitCode: 127,
					Output:   "sh: 1: trivy: not found",
				}, errors.New("exit 127")
			case 1:
				if spec.Command != "find" {
					t.Fatalf("expected second command find, got %q", spec.Command)
				}
				return app.CommandResult{ExitCode: 0, Output: "./Dockerfile\n"}, nil
			case 2:
				if spec.Command != "cat" {
					t.Fatalf("expected third command cat, got %q", spec.Command)
				}
				return app.CommandResult{ExitCode: 0, Output: dockerfile}, nil
			default:
				t.Fatalf("unexpected command call index %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewSecurityScanContainerHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"path":               ".",
		"max_findings":       10,
		"severity_threshold": "medium",
	}))
	if err != nil {
		t.Fatalf("unexpected security.scan_container error: %#v", err)
	}
	if len(runner.calls) != 3 {
		t.Fatalf("expected three runner calls, got %d", len(runner.calls))
	}

	output := result.Output.(map[string]any)
	if output["scanner"] != "heuristic-dockerfile" {
		t.Fatalf("expected heuristic scanner, got %#v", output["scanner"])
	}
	if output["findings_count"] == 0 {
		t.Fatalf("expected findings_count > 0, got %#v", output["findings_count"])
	}
}

func TestSecurityScanContainerHandler_HeuristicFallbackWhenTrivyHasNoFindings(t *testing.T) {
	root := t.TempDir()
	dockerfile := "FROM alpine:latest\nRUN chmod 777 /tmp\n"
	if err := os.WriteFile(filepath.Join(root, "Dockerfile"), []byte(dockerfile), 0o644); err != nil {
		t.Fatalf("write Dockerfile failed: %v", err)
	}

	trivyNoFindings := `{"Results":[{"Target":"go.mod","Class":"lang-pkgs","Type":"gomod"}]}`
	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				if spec.Command != "trivy" {
					t.Fatalf("expected first command trivy, got %q", spec.Command)
				}
				return app.CommandResult{
					ExitCode: 0,
					Output:   trivyNoFindings,
				}, nil
			case 1:
				if spec.Command != "find" {
					t.Fatalf("expected second command find, got %q", spec.Command)
				}
				return app.CommandResult{ExitCode: 0, Output: "./Dockerfile\n"}, nil
			case 2:
				if spec.Command != "cat" {
					t.Fatalf("expected third command cat, got %q", spec.Command)
				}
				return app.CommandResult{ExitCode: 0, Output: dockerfile}, nil
			default:
				t.Fatalf("unexpected command call index %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewSecurityScanContainerHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"path":               ".",
		"max_findings":       10,
		"severity_threshold": "medium",
	}))
	if err != nil {
		t.Fatalf("unexpected security.scan_container error: %#v", err)
	}
	if len(runner.calls) != 3 {
		t.Fatalf("expected three runner calls, got %d", len(runner.calls))
	}

	output := result.Output.(map[string]any)
	if output["scanner"] != "heuristic-dockerfile" {
		t.Fatalf("expected heuristic scanner, got %#v", output["scanner"])
	}
	if output["findings_count"] == 0 {
		t.Fatalf("expected findings_count > 0, got %#v", output["findings_count"])
	}
}

func TestSecurityScanContainerHandler_InvalidSeverity(t *testing.T) {
	handler := NewSecurityScanContainerHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, mustSWERuntimeJSON(t, map[string]any{"severity_threshold": "severe"}))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected severity validation error, got %#v", err)
	}
}

func TestSecurityScanContainerHandler_TrivyPath(t *testing.T) {
	raw := `{"Results":[{"Target":"demo","Vulnerabilities":[{"VulnerabilityID":"CVE-1","Severity":"HIGH","PkgName":"openssl","InstalledVersion":"1.0","FixedVersion":"1.1","Title":"issue"}]}]}`
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "trivy" {
				t.Fatalf("expected trivy command, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: raw}, nil
		},
	}
	result, err := NewSecurityScanContainerHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, mustSWERuntimeJSON(t, map[string]any{
		"path":               ".",
		"severity_threshold": "medium",
	}))
	if err != nil {
		t.Fatalf("unexpected trivy path error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["scanner"] != "trivy" {
		t.Fatalf("expected trivy scanner, got %#v", output["scanner"])
	}
}

func TestParseTrivyFindings_AppliesSeverityThreshold(t *testing.T) {
	raw := `{
  "Results": [
    {
      "Target": "alpine:3.20",
      "Vulnerabilities": [
        {"VulnerabilityID":"CVE-1","PkgName":"openssl","InstalledVersion":"1.0","FixedVersion":"1.1","Severity":"HIGH","Title":"high issue"},
        {"VulnerabilityID":"CVE-2","PkgName":"busybox","InstalledVersion":"1.0","FixedVersion":"1.1","Severity":"LOW","Title":"low issue"}
      ]
    }
  ]
}`

	findings, truncated, err := parseTrivyFindings(raw, "high", 50)
	if err != nil {
		t.Fatalf("unexpected parse error: %v", err)
	}
	if truncated {
		t.Fatal("did not expect truncation")
	}
	if len(findings) != 1 {
		t.Fatalf("expected one finding above threshold, got %d", len(findings))
	}
	if findings[0]["id"] != "CVE-1" {
		t.Fatalf("unexpected finding selected: %#v", findings[0])
	}
}

func TestParseTrivyFindings_WithMisconfigAndSecrets(t *testing.T) {
	report := `{
  "Results": [
    {
      "Target": "image:latest",
      "Vulnerabilities": [
        {"VulnerabilityID":"CVE-1","PkgName":"openssl","InstalledVersion":"1.0","FixedVersion":"1.1","Severity":"HIGH","Title":"high vuln"}
      ],
      "Misconfigurations": [
        {"ID":"MISCONF-1","Type":"Dockerfile","Title":"bad config","Severity":"MEDIUM","Message":"fix me"}
      ],
      "Secrets": [
        {"RuleID":"SECRET-1","Category":"AWS","Title":"aws key","Severity":"CRITICAL","StartLine":12,"Match":"AKIA..."}
      ]
    }
  ]
}`

	findings, truncated, err := parseTrivyFindings(report, "medium", 10)
	if err != nil {
		t.Fatalf("parseTrivyFindings failed: %v", err)
	}
	if truncated {
		t.Fatal("did not expect truncation")
	}
	if len(findings) != 3 {
		t.Fatalf("expected 3 findings, got %d", len(findings))
	}
	if findings[0]["severity"] != "critical" {
		t.Fatalf("expected critical finding first, got %#v", findings[0])
	}

	rawArray := `[{"Target":"repo","Vulnerabilities":[{"VulnerabilityID":"CVE-2","Severity":"LOW"}]}]`
	if _, _, err := parseTrivyFindings(rawArray, "low", 1); err != nil {
		t.Fatalf("parseTrivyFindings raw array failed: %v", err)
	}
}
