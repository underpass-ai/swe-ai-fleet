package tools

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestDetectTestCommand(t *testing.T) {
	root := t.TempDir()

	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}
	cmd, args, err := detectTestCommand(root, "", nil)
	if err != nil {
		t.Fatalf("unexpected detect error: %v", err)
	}
	if cmd != "go" || len(args) < 2 || args[0] != "test" {
		t.Fatalf("unexpected go command: %s %v", cmd, args)
	}

	rootPy := t.TempDir()
	if err := os.WriteFile(filepath.Join(rootPy, "pyproject.toml"), []byte("[project]\nname='x'\n"), 0o644); err != nil {
		t.Fatalf("write pyproject failed: %v", err)
	}
	cmd, args, err = detectTestCommand(rootPy, "tests/unit", []string{"-k", "abc"})
	if err != nil {
		t.Fatalf("unexpected python detect error: %v", err)
	}
	if cmd != "pytest" || args[0] != "-q" {
		t.Fatalf("unexpected pytest command: %s %v", cmd, args)
	}

	rootNpm := t.TempDir()
	if err := os.WriteFile(filepath.Join(rootNpm, "package.json"), []byte("{}"), 0o644); err != nil {
		t.Fatalf("write package failed: %v", err)
	}
	cmd, args, err = detectTestCommand(rootNpm, "--grep demo", nil)
	if err != nil {
		t.Fatalf("unexpected npm detect error: %v", err)
	}
	if cmd != "npm" || args[0] != "test" {
		t.Fatalf("unexpected npm command: %s %v", cmd, args)
	}

	_, _, err = detectTestCommand(t.TempDir(), "", nil)
	if err == nil {
		t.Fatal("expected not found error")
	}
}

func TestRepoRunTestsInvoke_GoModule(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/repo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}
	if err := os.WriteFile(filepath.Join(root, "sample_test.go"), []byte("package main\nimport \"testing\"\nfunc TestOK(t *testing.T) {}\n"), 0o644); err != nil {
		t.Fatalf("write test file failed: %v", err)
	}

	handler := &RepoRunTestsHandler{}
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"target":"./..."}`))
	if err != nil {
		t.Fatalf("unexpected run_tests error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("expected successful exit code, got %d", result.ExitCode)
	}
	if len(result.Artifacts) == 0 {
		t.Fatal("expected test output artifact")
	}
}

func TestRepoRunTestsValidation(t *testing.T) {
	handler := &RepoRunTestsHandler{}
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"target":`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid argument error, got %#v", err)
	}

	_, err = handler.Invoke(context.Background(), session, json.RawMessage(`{}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution failed when no runner exists, got %#v", err)
	}
}

func TestSanitizeArgs(t *testing.T) {
	result := sanitizeArgs([]string{" --ok ", "", "\x00bad"})
	if len(result) != 1 || result[0] != "--ok" {
		t.Fatalf("unexpected sanitized args: %#v", result)
	}
}
