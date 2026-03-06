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

func TestCIRunPipelineHandler_NoSupportedToolchain(t *testing.T) {
	handler := NewCIRunPipelineHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected no toolchain execution error, got %#v", err)
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
