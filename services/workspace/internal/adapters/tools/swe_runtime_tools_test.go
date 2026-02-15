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

func TestSWERuntimeHandlerNames(t *testing.T) {
	runner := &fakeSWERuntimeCommandRunner{}
	cases := []struct {
		name string
		got  string
	}{
		{name: "repo.coverage_report", got: NewRepoCoverageReportHandler(runner).Name()},
		{name: "repo.static_analysis", got: NewRepoStaticAnalysisHandler(runner).Name()},
		{name: "repo.package", got: NewRepoPackageHandler(runner).Name()},
		{name: "security.scan_secrets", got: NewSecurityScanSecretsHandler(runner).Name()},
		{name: "security.scan_dependencies", got: NewSecurityScanDependenciesHandler(runner).Name()},
		{name: "sbom.generate", got: NewSBOMGenerateHandler(runner).Name()},
		{name: "security.scan_container", got: NewSecurityScanContainerHandler(runner).Name()},
		{name: "security.license_check", got: NewSecurityLicenseCheckHandler(runner).Name()},
		{name: "quality.gate", got: NewQualityGateHandler(runner).Name()},
		{name: "ci.run_pipeline", got: NewCIRunPipelineHandler(runner).Name()},
	}

	for _, tc := range cases {
		if tc.got != tc.name {
			t.Fatalf("unexpected handler name: got=%q want=%q", tc.got, tc.name)
		}
	}
}

func TestStaticAnalysisCommandForProject_AllToolchains(t *testing.T) {
	workspaceC := t.TempDir()
	if err := os.WriteFile(filepath.Join(workspaceC, "main.c"), []byte("int main(void){return 0;}"), 0o644); err != nil {
		t.Fatalf("write main.c failed: %v", err)
	}
	workspacePy := t.TempDir()
	if err := os.MkdirAll(filepath.Join(workspacePy, ".workspace-venv", "bin"), 0o755); err != nil {
		t.Fatalf("mkdir .workspace-venv failed: %v", err)
	}
	if err := os.WriteFile(filepath.Join(workspacePy, ".workspace-venv", "bin", "python"), []byte(""), 0o755); err != nil {
		t.Fatalf("write python binary failed: %v", err)
	}

	tests := []struct {
		name      string
		workspace string
		detected  projectType
		target    string
		command   string
		minArgs   int
	}{
		{name: "go", workspace: t.TempDir(), detected: projectType{Name: "go"}, target: "", command: "go", minArgs: 2},
		{name: "rust", workspace: t.TempDir(), detected: projectType{Name: "rust"}, target: "", command: "cargo", minArgs: 2},
		{name: "node", workspace: t.TempDir(), detected: projectType{Name: "node"}, target: "pkg/web", command: "npm", minArgs: 4},
		{name: "python", workspace: workspacePy, detected: projectType{Name: "python"}, target: ".", command: ".workspace-venv/bin/python", minArgs: 3},
		{name: "java-gradle", workspace: t.TempDir(), detected: projectType{Name: "java", Flavor: "gradle"}, target: "", command: "gradle", minArgs: 2},
		{name: "java-maven", workspace: t.TempDir(), detected: projectType{Name: "java"}, target: "", command: "mvn", minArgs: 3},
		{name: "c", workspace: workspaceC, detected: projectType{Name: "c"}, target: "", command: "cc", minArgs: 3},
	}

	for _, tc := range tests {
		command, args, err := staticAnalysisCommandForProject(tc.workspace, tc.detected, tc.target)
		if err != nil {
			t.Fatalf("%s: unexpected error: %v", tc.name, err)
		}
		if command != tc.command {
			t.Fatalf("%s: unexpected command %q", tc.name, command)
		}
		if len(args) < tc.minArgs {
			t.Fatalf("%s: unexpected args: %#v", tc.name, args)
		}
	}

	_, _, err := staticAnalysisCommandForProject(t.TempDir(), projectType{Name: "unknown"}, "")
	if !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("expected os.ErrNotExist for unsupported toolchain, got %v", err)
	}
}

func TestPackageCommandForProject_AllToolchains(t *testing.T) {
	workspaceC := t.TempDir()
	if err := os.WriteFile(filepath.Join(workspaceC, "app.c"), []byte("int main(void){return 0;}"), 0o644); err != nil {
		t.Fatalf("write app.c failed: %v", err)
	}
	workspacePy := t.TempDir()
	if err := os.MkdirAll(filepath.Join(workspacePy, ".workspace-venv", "bin"), 0o755); err != nil {
		t.Fatalf("mkdir .workspace-venv failed: %v", err)
	}
	if err := os.WriteFile(filepath.Join(workspacePy, ".workspace-venv", "bin", "python"), []byte(""), 0o755); err != nil {
		t.Fatalf("write python binary failed: %v", err)
	}

	tests := []struct {
		name       string
		workspace  string
		detected   projectType
		target     string
		command    string
		wantEnsure bool
		wantPath   string
	}{
		{name: "go", workspace: t.TempDir(), detected: projectType{Name: "go"}, target: "", command: "go", wantEnsure: true, wantPath: ".workspace-dist/app"},
		{name: "rust", workspace: t.TempDir(), detected: projectType{Name: "rust"}, target: "core", command: "cargo", wantEnsure: false, wantPath: "target/release"},
		{name: "node", workspace: t.TempDir(), detected: projectType{Name: "node"}, target: "", command: "npm", wantEnsure: false, wantPath: ""},
		{name: "python", workspace: workspacePy, detected: projectType{Name: "python"}, target: "", command: ".workspace-venv/bin/python", wantEnsure: true, wantPath: ".workspace-dist"},
		{name: "java-gradle", workspace: t.TempDir(), detected: projectType{Name: "java", Flavor: "gradle"}, target: "", command: "gradle", wantEnsure: false, wantPath: "build/libs"},
		{name: "java-maven", workspace: t.TempDir(), detected: projectType{Name: "java"}, target: "", command: "mvn", wantEnsure: false, wantPath: "target"},
		{name: "c", workspace: workspaceC, detected: projectType{Name: "c"}, target: "app.c", command: "cc", wantEnsure: true, wantPath: ".workspace-dist/c-app"},
	}

	for _, tc := range tests {
		command, args, artifactPath, ensureDist, err := packageCommandForProject(tc.workspace, tc.detected, tc.target)
		if err != nil {
			t.Fatalf("%s: unexpected error: %v", tc.name, err)
		}
		if command != tc.command {
			t.Fatalf("%s: unexpected command %q", tc.name, command)
		}
		if len(args) == 0 {
			t.Fatalf("%s: expected non-empty args", tc.name)
		}
		if artifactPath != tc.wantPath {
			t.Fatalf("%s: unexpected artifact path %q", tc.name, artifactPath)
		}
		if ensureDist != tc.wantEnsure {
			t.Fatalf("%s: unexpected ensureDist=%v", tc.name, ensureDist)
		}
	}

	_, _, _, _, err := packageCommandForProject(t.TempDir(), projectType{Name: "c"}, "missing.txt")
	if err == nil {
		t.Fatal("expected missing c source error")
	}
}

func TestRuntimeDependencyParsers(t *testing.T) {
	pythonOutput := `[
  {"name":"requests","version":"2.31.0"},
  {"name":"requests","version":"2.31.0"},
  {"name":"urllib3","version":"2.2.0"},
  {"name":"click"}
]`
	pythonDeps, pythonTruncated, err := parsePythonDependencyInventory(pythonOutput, 2)
	if err != nil {
		t.Fatalf("parsePythonDependencyInventory failed: %v", err)
	}
	if len(pythonDeps) != 2 || !pythonTruncated {
		t.Fatalf("unexpected python deps result: len=%d truncated=%v", len(pythonDeps), pythonTruncated)
	}

	rustOutput := "serde v1.0.0\n├── regex v1.10.3\n└── serde v1.0.0\n"
	rustDeps, rustTruncated, err := parseRustDependencyInventory(rustOutput, 2)
	if err != nil {
		t.Fatalf("parseRustDependencyInventory failed: %v", err)
	}
	if len(rustDeps) != 2 || rustTruncated {
		t.Fatalf("unexpected rust deps result: len=%d truncated=%v", len(rustDeps), rustTruncated)
	}

	mavenOutput := "[INFO] org.apache.commons:commons-lang3:jar:3.13.0:runtime\n[INFO] junk line\n"
	mavenDeps, mavenTruncated, err := parseMavenDependencyInventory(mavenOutput, 10)
	if err != nil {
		t.Fatalf("parseMavenDependencyInventory failed: %v", err)
	}
	if len(mavenDeps) != 1 || mavenTruncated {
		t.Fatalf("unexpected maven deps: %#v truncated=%v", mavenDeps, mavenTruncated)
	}

	gradleOutput := "+--- org.slf4j:slf4j-api:1.7.36\n\\--- org.jetbrains.kotlin:kotlin-stdlib:1.9.0 -> 1.9.22\n"
	gradleDeps, gradleTruncated, err := parseGradleDependencyInventory(gradleOutput, 10)
	if err != nil {
		t.Fatalf("parseGradleDependencyInventory failed: %v", err)
	}
	if len(gradleDeps) != 2 || gradleTruncated {
		t.Fatalf("unexpected gradle deps: %#v truncated=%v", gradleDeps, gradleTruncated)
	}
}

func TestRuntimeLicenseParsingAndEnrichment(t *testing.T) {
	metadata := `{
  "packages": [
    {"name":"serde","version":"1.0.0","license":"MIT"},
    {"name":"tokio","version":"1.0.0","license":""}
  ]
}`
	rustMap, err := parseRustLicenseMap(metadata, 50)
	if err != nil {
		t.Fatalf("parseRustLicenseMap failed: %v", err)
	}
	if len(rustMap) != 1 {
		t.Fatalf("unexpected rust license map size: %d", len(rustMap))
	}

	nodeRunner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output: `{"dependencies":{"left-pad":{"version":"1.3.0","license":"MIT"}}}`,
			}, nil
		},
	}
	nodeEntries := []dependencyEntry{{Name: "left-pad", Version: "1.3.0", Ecosystem: "node", License: "unknown"}}
	enrichedNode, command, _, err := enrichDependencyLicenses(
		context.Background(),
		nodeRunner,
		domain.Session{WorkspacePath: t.TempDir()},
		projectType{Name: "node"},
		".",
		nodeEntries,
		100,
	)
	if err != nil {
		t.Fatalf("enrichDependencyLicenses node failed: %v", err)
	}
	if len(command) == 0 || command[0] != "npm" {
		t.Fatalf("unexpected node enrichment command: %#v", command)
	}
	if len(enrichedNode) != 1 || enrichedNode[0].License != "MIT" {
		t.Fatalf("unexpected node enriched entries: %#v", enrichedNode)
	}

	rustRunner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "cargo" {
				t.Fatalf("expected cargo command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output:   metadata,
			}, nil
		},
	}
	rustEntries := []dependencyEntry{{Name: "serde", Version: "1.0.0", Ecosystem: "rust", License: "unknown"}}
	enrichedRust, rustCommand, _, err := enrichDependencyLicenses(
		context.Background(),
		rustRunner,
		domain.Session{WorkspacePath: t.TempDir()},
		projectType{Name: "rust"},
		".",
		rustEntries,
		100,
	)
	if err != nil {
		t.Fatalf("enrichDependencyLicenses rust failed: %v", err)
	}
	if len(rustCommand) == 0 || rustCommand[0] != "cargo" {
		t.Fatalf("unexpected rust enrichment command: %#v", rustCommand)
	}
	if len(enrichedRust) != 1 || enrichedRust[0].License != "MIT" {
		t.Fatalf("unexpected rust enriched entries: %#v", enrichedRust)
	}
}

func TestRuntimeScalarConverters(t *testing.T) {
	if got := intFromAny(json.Number("12")); got != 12 {
		t.Fatalf("unexpected intFromAny json.Number: %d", got)
	}
	if got := intFromAny(" 7 "); got != 7 {
		t.Fatalf("unexpected intFromAny string: %d", got)
	}
	if got := intFromAny(uint16(9)); got != 9 {
		t.Fatalf("unexpected intFromAny uint16: %d", got)
	}
	if got := intFromAny("bad"); got != 0 {
		t.Fatalf("unexpected intFromAny fallback: %d", got)
	}

	if got := floatFromAny(json.Number("3.5")); got != 3.5 {
		t.Fatalf("unexpected floatFromAny json.Number: %f", got)
	}
	if got := floatFromAny(" 2.25 "); got != 2.25 {
		t.Fatalf("unexpected floatFromAny string: %f", got)
	}
	if got := floatFromAny(int64(5)); got != 5 {
		t.Fatalf("unexpected floatFromAny int64: %f", got)
	}
	if got := floatFromAny("oops"); got != 0 {
		t.Fatalf("unexpected floatFromAny fallback: %f", got)
	}
}

func TestRuntimeSecurityHelpers(t *testing.T) {
	threshold, err := normalizeSeverityThreshold("moderate")
	if err != nil {
		t.Fatalf("normalizeSeverityThreshold failed: %v", err)
	}
	if threshold != "medium" {
		t.Fatalf("unexpected normalized threshold: %q", threshold)
	}
	if _, err := normalizeSeverityThreshold("severe"); err == nil {
		t.Fatal("expected normalizeSeverityThreshold error")
	}

	levels := severityListForThreshold("high")
	if len(levels) != 2 || levels[0] != "CRITICAL" || levels[1] != "HIGH" {
		t.Fatalf("unexpected severity levels: %#v", levels)
	}
	if !severityAtOrAbove("critical", "high") {
		t.Fatal("expected critical to be above high")
	}
	if severityAtOrAbove("low", "high") {
		t.Fatal("low must not pass high threshold")
	}

	if id, sev, _ := dockerfileHeuristicRule("run curl -s https://x | sh"); id == "" || sev != "high" {
		t.Fatalf("unexpected dockerfile heuristic result: id=%q sev=%q", id, sev)
	}
	if !isDockerfileCandidate("Dockerfile.prod") || isDockerfileCandidate("README.md") {
		t.Fatal("unexpected Dockerfile candidate detection")
	}
}

func TestRuntimeLicensePolicyHelpers(t *testing.T) {
	allowed, reason := evaluateLicenseAgainstPolicy("MIT", []string{"MIT"}, []string{"GPL-3.0"})
	if allowed != "allowed" || reason != "" {
		t.Fatalf("expected allowed license, got status=%q reason=%q", allowed, reason)
	}
	denied, reason := evaluateLicenseAgainstPolicy("GPL-3.0", nil, []string{"GPL-3.0"})
	if denied != "denied" || !strings.Contains(reason, "denied") {
		t.Fatalf("expected denied license, got status=%q reason=%q", denied, reason)
	}
	unknown, _ := evaluateLicenseAgainstPolicy("", nil, nil)
	if unknown != "unknown" {
		t.Fatalf("expected unknown license status, got %q", unknown)
	}

	if got := normalizeFoundLicense("mit or apache-2.0"); got != "MIT OR APACHE-2.0" {
		t.Fatalf("unexpected normalized license: %q", got)
	}
	if got := nodeStringOrList([]any{"MIT", "Apache-2.0"}); got != "MIT OR Apache-2.0" {
		t.Fatalf("unexpected nodeStringOrList result: %q", got)
	}
}

func TestRuntimeArtifactAndPURLHelpers(t *testing.T) {
	packOutput := "npm notice package-size: 10 kB\nworkspace-demo-1.0.0.tgz\n"
	if got := detectNodePackageArtifact(packOutput); got != "workspace-demo-1.0.0.tgz" {
		t.Fatalf("unexpected package artifact: %q", got)
	}
	if got := dependencyPURL(dependencyEntry{Name: "github.com/foo/bar", Version: "1.0.0", Ecosystem: "go"}); got == "" || !strings.HasPrefix(got, "pkg:golang/") {
		t.Fatalf("unexpected go purl: %q", got)
	}
	if got := dependencyPURL(dependencyEntry{Name: "serde", Version: "1.0.0", Ecosystem: "rust"}); !strings.HasPrefix(got, "pkg:cargo/") {
		t.Fatalf("unexpected rust purl: %q", got)
	}
	if got := dependencyPURL(dependencyEntry{Name: "group:artifact", Version: "1.0.0", Ecosystem: "java"}); !strings.HasPrefix(got, "pkg:maven/") {
		t.Fatalf("unexpected java purl: %q", got)
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

func TestQualityGateConfigHelpers(t *testing.T) {
	minCoverage := 120.0
	maxDiagnostics := -2
	maxVulns := 200001
	maxDenied := 5
	maxFailed := 3
	config := normalizeQualityGateConfig(qualityGateThresholdsRequest{
		MinCoveragePercent: &minCoverage,
		MaxDiagnostics:     &maxDiagnostics,
		MaxVulnerabilities: &maxVulns,
		MaxDeniedLicenses:  &maxDenied,
		MaxFailedTests:     &maxFailed,
	})
	if config.MinCoveragePercent != 100 {
		t.Fatalf("unexpected min coverage clamp: %f", config.MinCoveragePercent)
	}
	if config.MaxDiagnostics != -1 {
		t.Fatalf("unexpected max diagnostics clamp: %d", config.MaxDiagnostics)
	}
	if config.MaxVulnerabilities != 100000 {
		t.Fatalf("unexpected max vulnerabilities clamp: %d", config.MaxVulnerabilities)
	}
	if qualityGateSummary(true, 0, 0) != "quality gate passed (no active rules)" {
		t.Fatal("unexpected qualityGateSummary for no rules")
	}
	if ternaryQualityGateStatus(false) != "fail" {
		t.Fatal("unexpected ternary quality gate status")
	}
}

func TestRepoCoverageReportHandler_GoCoverCommandFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			switch callIndex {
			case 0:
				return app.CommandResult{ExitCode: 0, Output: "ok\tcoverage: 55.0% of statements"}, nil
			case 1:
				if spec.Command != "go" {
					t.Fatalf("unexpected cover command: %q", spec.Command)
				}
				return app.CommandResult{ExitCode: 1, Output: "cover failed"}, errors.New("exit 1")
			case 2:
				return app.CommandResult{ExitCode: 0, Output: ""}, nil
			default:
				t.Fatalf("unexpected call index %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}

	result, err := NewRepoCoverageReportHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected cover command execution failure, got %#v", err)
	}
	if result.ExitCode != 1 {
		t.Fatalf("expected exit code 1 from cover failure, got %d", result.ExitCode)
	}
}

func TestRepoCoverageReportHandler_NonGoPath(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(`{"name":"demo","version":"1.0.0"}`), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm command for non-go coverage, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: "tests passed"}, nil
		},
	}
	result, err := NewRepoCoverageReportHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{}`))
	if err != nil {
		t.Fatalf("unexpected non-go coverage error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["project_type"] != "node" {
		t.Fatalf("unexpected project_type: %#v", output["project_type"])
	}
	if output["coverage_supported"] != false {
		t.Fatalf("expected coverage_supported=false, got %#v", output["coverage_supported"])
	}
}

func TestRepoPackageHandler_NodeArtifactDetection(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(`{"name":"demo","version":"1.0.0"}`), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm pack command, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: "demo-1.0.0.tgz"}, nil
		},
	}

	result, err := NewRepoPackageHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{}`))
	if err != nil {
		t.Fatalf("unexpected repo.package node error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["artifact_path"] != "demo-1.0.0.tgz" {
		t.Fatalf("unexpected artifact_path: %#v", output["artifact_path"])
	}
}

func TestSecurityScanDependenciesHandler_InvalidPath(t *testing.T) {
	handler := NewSecurityScanDependenciesHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"path":"../outside"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid path error, got %#v", err)
	}
}

func TestSBOMGenerateHandler_RejectsInvalidPath(t *testing.T) {
	handler := NewSBOMGenerateHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"path":"../outside","format":"cyclonedx-json"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid path error, got %#v", err)
	}
}

func TestSecurityScanContainerHandler_InvalidSeverity(t *testing.T) {
	handler := NewSecurityScanContainerHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"severity_threshold":"severe"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected severity validation error, got %#v", err)
	}
}

func TestSecurityLicenseCheckHandler_InvalidUnknownPolicy(t *testing.T) {
	handler := NewSecurityLicenseCheckHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"unknown_policy":"block"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected unknown_policy validation error, got %#v", err)
	}
}

func TestSecurityScanSecretsHandler_NoMatchesExitCodeOne(t *testing.T) {
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, _ app.CommandSpec) (app.CommandResult, error) {
			return app.CommandResult{ExitCode: 1, Output: ""}, errors.New("exit 1")
		},
	}
	result, err := NewSecurityScanSecretsHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"path":"."}`))
	if err != nil {
		t.Fatalf("expected clean scan for exit code 1, got %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["findings_count"] != 0 {
		t.Fatalf("expected zero findings, got %#v", output["findings_count"])
	}
}

func TestCIRunPipelineHandler_NoSupportedToolchain(t *testing.T) {
	handler := NewCIRunPipelineHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected no toolchain execution error, got %#v", err)
	}
}

func TestRepoStaticAnalysisHandler_RunErrorMapping(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, _ app.CommandSpec) (app.CommandResult, error) {
			return app.CommandResult{ExitCode: 1, Output: "vet failed"}, errors.New("exit 1")
		},
	}
	_, err := NewRepoStaticAnalysisHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{"target":"./..."}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected repo.static_analysis execution error, got %#v", err)
	}
}

func TestRepoPackageHandler_MkdirFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			if callIndex == 0 && spec.Command == "mkdir" {
				return app.CommandResult{ExitCode: 1, Output: "mkdir failed"}, errors.New("exit 1")
			}
			return app.CommandResult{ExitCode: 0, Output: "ok"}, nil
		},
	}
	_, err := NewRepoPackageHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected mkdir failure mapping, got %#v", err)
	}
}

func TestSecurityScanDependenciesHandler_ParseFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(`{"name":"demo","version":"1.0.0"}`), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm inventory command, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: "{invalid-json"}, nil
		},
	}
	_, err := NewSecurityScanDependenciesHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{"path":"."}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected dependency inventory parse failure, got %#v", err)
	}
}

func TestSBOMGenerateHandler_InventoryParseFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(`{"name":"demo","version":"1.0.0"}`), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, _ app.CommandSpec) (app.CommandResult, error) {
			return app.CommandResult{ExitCode: 0, Output: "{invalid-json"}, nil
		},
	}
	_, err := NewSBOMGenerateHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{"path":".","format":"cyclonedx-json"}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected sbom inventory parse failure, got %#v", err)
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

func TestSecurityLicenseCheckHandler_UnknownPolicyDeny(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "go" {
				t.Fatalf("expected go list command, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: "example.com/demo\nexample.com/lib v1.0.0\n"}, nil
		},
	}
	result, err := NewSecurityLicenseCheckHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, mustSWERuntimeJSON(t, map[string]any{
		"path":           ".",
		"unknown_policy": "deny",
	}))
	if err != nil {
		t.Fatalf("unexpected security.license_check invocation error: %#v", err)
	}
	if result.ExitCode != 1 {
		t.Fatalf("expected exit code 1 for unknown_policy=deny, got %d", result.ExitCode)
	}
}

func TestCIRunPipelineHandler_SuccessPath(t *testing.T) {
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
			case 3:
				return app.CommandResult{ExitCode: 0, Output: "static ok"}, nil
			case 4:
				return app.CommandResult{ExitCode: 0, Output: "ok\tcoverage: 82.5% of statements"}, nil
			case 5:
				return app.CommandResult{ExitCode: 0, Output: ""}, nil
			default:
				t.Fatalf("unexpected pipeline call index: %d", callIndex)
				return app.CommandResult{}, nil
			}
		},
	}

	result, err := NewCIRunPipelineHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, mustSWERuntimeJSON(t, map[string]any{
		"include_static_analysis": true,
		"include_coverage":        true,
		"include_quality_gate":    true,
		"fail_fast":               true,
		"quality_gate": map[string]any{
			"min_coverage_percent": 80,
			"max_failed_tests":     0,
		},
	}))
	if err != nil {
		t.Fatalf("unexpected ci.run_pipeline success error: %#v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", result.ExitCode)
	}
	output := result.Output.(map[string]any)
	if output["failed_step"] != "" {
		t.Fatalf("expected no failed_step, got %#v", output["failed_step"])
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
