package tools

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

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
