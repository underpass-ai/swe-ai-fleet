package tools

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
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

func mustSWERuntimeJSON(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	return data
}
