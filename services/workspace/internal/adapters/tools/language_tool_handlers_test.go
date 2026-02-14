package tools

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeLanguageCommandRunner struct {
	calls []app.CommandSpec
	run   func(callIndex int, spec app.CommandSpec) (app.CommandResult, error)
}

func (f *fakeLanguageCommandRunner) Run(_ context.Context, _ domain.Session, spec app.CommandSpec) (app.CommandResult, error) {
	f.calls = append(f.calls, spec)
	if f.run != nil {
		return f.run(len(f.calls)-1, spec)
	}
	return app.CommandResult{ExitCode: 0, Output: "ok"}, nil
}

func TestRustBuildHandler_BuildsExpectedCommand(t *testing.T) {
	runner := &fakeLanguageCommandRunner{}
	handler := NewRustBuildHandler(runner)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustLanguageJSON(t, map[string]any{
		"target":  "workspace-crate",
		"release": true,
	}))
	if err != nil {
		t.Fatalf("unexpected rust.build error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", result.ExitCode)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}

	got := runner.calls[0]
	wantArgs := []string{"build", "--package", "workspace-crate", "--release"}
	if got.Command != "cargo" {
		t.Fatalf("expected cargo command, got %q", got.Command)
	}
	if !reflect.DeepEqual(got.Args, wantArgs) {
		t.Fatalf("unexpected rust.build args: got=%v want=%v", got.Args, wantArgs)
	}
}

func TestNodeInstallHandler_UsesInstallWhenUseCIFalse(t *testing.T) {
	runner := &fakeLanguageCommandRunner{}
	handler := NewNodeInstallHandler(runner)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustLanguageJSON(t, map[string]any{
		"use_ci":         false,
		"ignore_scripts": true,
	}))
	if err != nil {
		t.Fatalf("unexpected node.install error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", result.ExitCode)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}

	got := runner.calls[0]
	wantArgs := []string{"install", "--ignore-scripts"}
	if got.Command != "npm" {
		t.Fatalf("expected npm command, got %q", got.Command)
	}
	if !reflect.DeepEqual(got.Args, wantArgs) {
		t.Fatalf("unexpected node.install args: got=%v want=%v", got.Args, wantArgs)
	}
}

func TestNodeTypecheckHandler_AppendsTargetAfterDoubleDash(t *testing.T) {
	runner := &fakeLanguageCommandRunner{}
	handler := NewNodeTypecheckHandler(runner)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustLanguageJSON(t, map[string]any{
		"target": "packages/web",
	}))
	if err != nil {
		t.Fatalf("unexpected node.typecheck error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", result.ExitCode)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}

	got := runner.calls[0]
	wantArgs := []string{"run", "typecheck", "--if-present", "--", "packages/web"}
	if got.Command != "npm" {
		t.Fatalf("expected npm command, got %q", got.Command)
	}
	if !reflect.DeepEqual(got.Args, wantArgs) {
		t.Fatalf("unexpected node.typecheck args: got=%v want=%v", got.Args, wantArgs)
	}
}

func TestCBuildHandler_CompilesRequestedSource(t *testing.T) {
	root := t.TempDir()
	mainC := filepath.Join(root, "main.c")
	if err := os.WriteFile(mainC, []byte("int main(void){return 0;}"), 0o644); err != nil {
		t.Fatalf("write main.c failed: %v", err)
	}

	runner := &fakeLanguageCommandRunner{}
	handler := NewCBuildHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustLanguageJSON(t, map[string]any{
		"source":      "main.c",
		"output_name": "todo-c",
		"standard":    "c11",
	}))
	if err != nil {
		t.Fatalf("unexpected c.build error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", result.ExitCode)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}

	got := runner.calls[0]
	wantArgs := []string{"-std=c11", "-O2", "-Wall", "-Wextra", "-o", "todo-c", "main.c"}
	if got.Command != "cc" {
		t.Fatalf("expected cc command, got %q", got.Command)
	}
	if !reflect.DeepEqual(got.Args, wantArgs) {
		t.Fatalf("unexpected c.build args: got=%v want=%v", got.Args, wantArgs)
	}
}

func TestCTestHandler_CompilesAndExecutesBinary(t *testing.T) {
	root := t.TempDir()
	testC := filepath.Join(root, "todo_test.c")
	if err := os.WriteFile(testC, []byte("int main(void){return 0;}"), 0o644); err != nil {
		t.Fatalf("write todo_test.c failed: %v", err)
	}

	runner := &fakeLanguageCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			if callIndex == 0 {
				return app.CommandResult{ExitCode: 0, Output: "compile ok"}, nil
			}
			if callIndex == 1 {
				return app.CommandResult{ExitCode: 0, Output: "tests ok"}, nil
			}
			return app.CommandResult{ExitCode: 1, Output: "unexpected call"}, nil
		},
	}
	handler := NewCTestHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustLanguageJSON(t, map[string]any{
		"source":      "todo_test.c",
		"output_name": "todo-c-test",
		"standard":    "c11",
		"run":         true,
	}))
	if err != nil {
		t.Fatalf("unexpected c.test error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", result.ExitCode)
	}
	if len(runner.calls) != 2 {
		t.Fatalf("expected two runner calls, got %d", len(runner.calls))
	}

	compileCall := runner.calls[0]
	execCall := runner.calls[1]
	wantCompileArgs := []string{"-std=c11", "-O0", "-g", "-Wall", "-Wextra", "-o", "todo-c-test", "todo_test.c"}
	if compileCall.Command != "cc" {
		t.Fatalf("expected cc compile command, got %q", compileCall.Command)
	}
	if !reflect.DeepEqual(compileCall.Args, wantCompileArgs) {
		t.Fatalf("unexpected c.test compile args: got=%v want=%v", compileCall.Args, wantCompileArgs)
	}
	if execCall.Command != "./todo-c-test" {
		t.Fatalf("expected execution command ./todo-c-test, got %q", execCall.Command)
	}
}

func mustLanguageJSON(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	return data
}
