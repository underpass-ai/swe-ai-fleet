package tools

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeSWERuntimeCommandRunner struct {
	calls []app.CommandSpec
	run   func(callIndex int, spec app.CommandSpec) (app.CommandResult, error)
}

func (f *fakeSWERuntimeCommandRunner) Run(_ context.Context, _ domain.Session, spec app.CommandSpec) (app.CommandResult, error) {
	f.calls = append(f.calls, spec)
	if f.run != nil {
		return f.run(len(f.calls)-1, spec)
	}
	return app.CommandResult{ExitCode: 0, Output: "ok"}, nil
}

func TestRepoCoverageReportHandler_Go(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				return app.CommandResult{ExitCode: 0, Output: "ok\tcoverage: 71.4% of statements"}, nil
			case 1:
				return app.CommandResult{ExitCode: 0, Output: "total:\t(statements)\t80.0%"}, nil
			case 2:
				return app.CommandResult{ExitCode: 0, Output: ""}, nil
			default:
				t.Fatalf("unexpected call index %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}

	handler := NewRepoCoverageReportHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{}`))
	if err != nil {
		t.Fatalf("unexpected repo.coverage_report error: %#v", err)
	}
	if len(runner.calls) != 3 {
		t.Fatalf("expected 3 runner calls, got %d", len(runner.calls))
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["project_type"] != "go" {
		t.Fatalf("unexpected project_type: %#v", output["project_type"])
	}
	coverage, ok := output["coverage_percent"].(float64)
	if !ok || coverage != 80.0 {
		t.Fatalf("unexpected coverage_percent: %#v", output["coverage_percent"])
	}
}

func TestRepoStaticAnalysisHandler_Go(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{}
	handler := NewRepoStaticAnalysisHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"target":"./..."}`))
	if err != nil {
		t.Fatalf("unexpected repo.static_analysis error: %#v", err)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}
	if runner.calls[0].Command != "go" {
		t.Fatalf("expected go command, got %q", runner.calls[0].Command)
	}
	if len(runner.calls[0].Args) < 2 || runner.calls[0].Args[0] != "vet" || runner.calls[0].Args[1] != "./..." {
		t.Fatalf("unexpected args: %#v", runner.calls[0].Args)
	}
}

func TestRepoPackageHandler_C(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "main.c"), []byte("int main(void){return 0;}"), 0o644); err != nil {
		t.Fatalf("write main.c failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{}
	handler := NewRepoPackageHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{}`))
	if err != nil {
		t.Fatalf("unexpected repo.package error: %#v", err)
	}
	if len(runner.calls) != 2 {
		t.Fatalf("expected 2 runner calls, got %d", len(runner.calls))
	}
	if runner.calls[0].Command != "mkdir" {
		t.Fatalf("expected mkdir call, got %q", runner.calls[0].Command)
	}
	if runner.calls[1].Command != "cc" {
		t.Fatalf("expected cc call, got %q", runner.calls[1].Command)
	}

	output := result.Output.(map[string]any)
	if output["artifact_path"] != ".workspace-dist/c-app" {
		t.Fatalf("unexpected artifact_path: %#v", output["artifact_path"])
	}
}

func TestSecurityScanSecretsHandler_TruncatesFindings(t *testing.T) {
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, _ app.CommandSpec) (app.CommandResult, error) {
			return app.CommandResult{
				ExitCode: 0,
				Output: "a.txt:1:api_key = \"123456789012\"\n" +
					"b.txt:2:token = \"abcdefabcdefabcdef\"\n",
			}, nil
		},
	}
	handler := NewSecurityScanSecretsHandler(runner)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"path":".","max_results":1}`))
	if err != nil {
		t.Fatalf("unexpected security.scan_secrets error: %#v", err)
	}
	if len(runner.calls) != 1 || runner.calls[0].Command != "rg" {
		t.Fatalf("expected rg call, got %#v", runner.calls)
	}

	output := result.Output.(map[string]any)
	if output["findings_count"] != 1 {
		t.Fatalf("unexpected findings_count: %#v", output["findings_count"])
	}
	if output["truncated"] != true {
		t.Fatalf("expected truncated=true, got %#v", output["truncated"])
	}
	findings, ok := output["findings"].([]map[string]any)
	if !ok || len(findings) != 1 {
		t.Fatalf("unexpected findings: %#v", output["findings"])
	}
}

func TestSecurityScanSecretsHandler_FallbackToGrepWhenRipgrepMissing(t *testing.T) {
	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				if spec.Command != "rg" {
					t.Fatalf("expected first command rg, got %q", spec.Command)
				}
				return app.CommandResult{
					ExitCode: 127,
					Output:   "sh: 1: exec: rg: not found\n",
				}, errors.New("exit 127")
			case 1:
				if spec.Command != "grep" {
					t.Fatalf("expected fallback command grep, got %q", spec.Command)
				}
				return app.CommandResult{
					ExitCode: 0,
					Output:   "secrets.txt:3:token = \"abcdefabcdefabcdef\"\n",
				}, nil
			default:
				t.Fatalf("unexpected call index: %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewSecurityScanSecretsHandler(runner)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"path":".","max_results":10}`))
	if err != nil {
		t.Fatalf("unexpected security.scan_secrets fallback error: %#v", err)
	}
	if len(runner.calls) != 2 {
		t.Fatalf("expected two runner calls, got %d", len(runner.calls))
	}

	output := result.Output.(map[string]any)
	if output["findings_count"] != 1 {
		t.Fatalf("unexpected findings_count: %#v", output["findings_count"])
	}
	findings, ok := output["findings"].([]map[string]any)
	if !ok || len(findings) != 1 {
		t.Fatalf("unexpected findings: %#v", output["findings"])
	}
}

func TestSecurityScanDependenciesHandler_Go(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "go" {
				t.Fatalf("expected go command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output: "example.com/demo\n" +
					"github.com/google/uuid v1.6.0\n" +
					"golang.org/x/text v0.22.0\n",
			}, nil
		},
	}
	handler := NewSecurityScanDependenciesHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"path":".","max_dependencies":2}`))
	if err != nil {
		t.Fatalf("unexpected security.scan_dependencies error: %#v", err)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["dependencies_count"] != 2 {
		t.Fatalf("unexpected dependencies_count: %#v", output["dependencies_count"])
	}
	if output["truncated"] != true {
		t.Fatalf("expected truncated=true, got %#v", output["truncated"])
	}
}

func TestSBOMGenerateHandler_GeneratesCycloneDXArtifact(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "go" {
				t.Fatalf("expected go command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output: "example.com/demo\n" +
					"github.com/google/uuid v1.6.0\n",
			}, nil
		},
	}
	handler := NewSBOMGenerateHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"path":".","format":"cyclonedx-json","max_components":50}`))
	if err != nil {
		t.Fatalf("unexpected sbom.generate error: %#v", err)
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["artifact_name"] != "sbom.cdx.json" {
		t.Fatalf("unexpected artifact_name: %#v", output["artifact_name"])
	}

	foundSBOM := false
	for _, artifact := range result.Artifacts {
		if artifact.Name != "sbom.cdx.json" {
			continue
		}
		foundSBOM = true
		if !strings.Contains(string(artifact.Data), `"bomFormat": "CycloneDX"`) {
			t.Fatalf("expected CycloneDX content, got: %s", string(artifact.Data))
		}
	}
	if !foundSBOM {
		t.Fatal("expected sbom.cdx.json artifact")
	}
}

func TestSBOMGenerateHandler_RejectsUnsupportedFormat(t *testing.T) {
	handler := NewSBOMGenerateHandler(&fakeSWERuntimeCommandRunner{})
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"format":"spdx-json"}`))
	if err == nil {
		t.Fatal("expected invalid format error")
	}
	if err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

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

func TestSecurityLicenseCheckHandler_DeniedLicenseFailsStatus(t *testing.T) {
	root := t.TempDir()
	packageJSON := `{"name":"demo","version":"1.0.0","private":true}`
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(packageJSON), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}

	npmOutput := `{
  "name": "demo",
  "version": "1.0.0",
  "dependencies": {
    "left-pad": {
      "version": "1.3.0",
      "license": "GPL-3.0"
    }
  }
}`
	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm command, got %q", spec.Command)
			}
			if callIndex == 0 {
				if len(spec.Args) != 3 || spec.Args[0] != "ls" || spec.Args[1] != "--json" || spec.Args[2] != "--all" {
					t.Fatalf("unexpected dependency inventory args: %#v", spec.Args)
				}
			}
			if callIndex == 1 {
				if len(spec.Args) != 4 || spec.Args[3] != "--long" {
					t.Fatalf("unexpected license enrichment args: %#v", spec.Args)
				}
			}
			return app.CommandResult{ExitCode: 0, Output: npmOutput}, nil
		},
	}
	handler := NewSecurityLicenseCheckHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"path":            ".",
		"denied_licenses": []string{"GPL-3.0"},
		"unknown_policy":  "warn",
	}))
	if err != nil {
		t.Fatalf("unexpected security.license_check error: %#v", err)
	}
	if len(runner.calls) != 2 {
		t.Fatalf("expected 2 npm calls, got %d", len(runner.calls))
	}
	if result.ExitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", result.ExitCode)
	}

	output := result.Output.(map[string]any)
	if output["status"] != "fail" {
		t.Fatalf("expected fail status, got %#v", output["status"])
	}
	if output["denied_count"] != 1 {
		t.Fatalf("expected denied_count=1, got %#v", output["denied_count"])
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

func TestQualityGateHandler_PassAndFail(t *testing.T) {
	handler := NewQualityGateHandler(nil)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	passResult, passErr := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"metrics": map[string]any{
			"coverage_percent":   82.5,
			"diagnostics_count":  0,
			"failed_tests_count": 0,
		},
		"min_coverage_percent": 80,
		"max_diagnostics":      0,
		"max_failed_tests":     0,
	}))
	if passErr != nil {
		t.Fatalf("unexpected quality.gate pass error: %#v", passErr)
	}
	if passResult.ExitCode != 0 {
		t.Fatalf("expected pass exit code 0, got %d", passResult.ExitCode)
	}
	passOutput := passResult.Output.(map[string]any)
	if passOutput["status"] != "pass" {
		t.Fatalf("expected pass status, got %#v", passOutput["status"])
	}

	failResult, failErr := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"metrics": map[string]any{
			"failed_tests_count": 2,
		},
		"max_failed_tests": 0,
	}))
	if failErr != nil {
		t.Fatalf("unexpected quality.gate fail invocation error: %#v", failErr)
	}
	if failResult.ExitCode != 1 {
		t.Fatalf("expected fail exit code 1, got %d", failResult.ExitCode)
	}
	failOutput := failResult.Output.(map[string]any)
	if failOutput["status"] != "fail" {
		t.Fatalf("expected fail status, got %#v", failOutput["status"])
	}
}

func TestCIRunPipelineHandler_FailFast(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, _ app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				return app.CommandResult{ExitCode: 0, Output: "validate ok"}, nil
			case 1:
				return app.CommandResult{ExitCode: 2, Output: "build failed"}, errors.New("exit 2")
			default:
				return app.CommandResult{ExitCode: 0, Output: "should not run"}, nil
			}
		},
	}
	handler := NewCIRunPipelineHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"fail_fast":               true,
		"include_static_analysis": false,
		"include_coverage":        false,
	}))
	if err == nil {
		t.Fatal("expected ci.run_pipeline to fail")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
	if len(runner.calls) != 2 {
		t.Fatalf("expected fail-fast after 2 calls, got %d", len(runner.calls))
	}

	output := result.Output.(map[string]any)
	if output["failed_step"] != "build" {
		t.Fatalf("unexpected failed_step: %#v", output["failed_step"])
	}
}

func TestCIRunPipelineHandler_QualityGateFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, _ app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				return app.CommandResult{ExitCode: 0, Output: "validate ok"}, nil
			case 1:
				return app.CommandResult{ExitCode: 0, Output: "build ok"}, nil
			case 2:
				return app.CommandResult{ExitCode: 0, Output: "tests ok"}, nil
			default:
				t.Fatalf("unexpected call index %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewCIRunPipelineHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"include_static_analysis": false,
		"include_coverage":        false,
		"include_quality_gate":    true,
		"fail_fast":               true,
		"quality_gate": map[string]any{
			"min_coverage_percent": 80,
			"max_failed_tests":     0,
		},
	}))
	if err == nil {
		t.Fatal("expected ci.run_pipeline quality gate error")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
	if len(runner.calls) != 3 {
		t.Fatalf("expected 3 runner calls, got %d", len(runner.calls))
	}

	output := result.Output.(map[string]any)
	if output["failed_step"] != "quality_gate" {
		t.Fatalf("unexpected failed_step: %#v", output["failed_step"])
	}
	qualityGate, ok := output["quality_gate"].(map[string]any)
	if !ok {
		t.Fatalf("expected quality_gate map, got %T", output["quality_gate"])
	}
	if qualityGate["status"] != "fail" {
		t.Fatalf("expected quality gate fail status, got %#v", qualityGate["status"])
	}
}

func mustSWERuntimeJSON(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	return data
}
