package tools

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestGitHandlers_StatusDiffApplyPatch(t *testing.T) {
	root := initGitRepo(t)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}
	ctx := context.Background()

	filePath := filepath.Join(root, "main.txt")
	if err := os.WriteFile(filePath, []byte("line1\nline2-modified\n"), 0o644); err != nil {
		t.Fatalf("write file failed: %v", err)
	}

	status := &GitStatusHandler{}
	statusResult, statusErr := status.Invoke(ctx, session, json.RawMessage(`{"short":true}`))
	if statusErr != nil {
		t.Fatalf("unexpected git status error: %v", statusErr)
	}
	statusOutput := statusResult.Output.(map[string]any)["status"].(string)
	if !strings.Contains(statusOutput, "main.txt") {
		t.Fatalf("expected modified file in status, got %q", statusOutput)
	}

	diff := &GitDiffHandler{}
	diffResult, diffErr := diff.Invoke(ctx, session, mustJSONGit(t, map[string]any{"paths": []string{"main.txt"}}))
	if diffErr != nil {
		t.Fatalf("unexpected git diff error: %v", diffErr)
	}
	diffOutput := diffResult.Output.(map[string]any)["diff"].(string)
	if !strings.Contains(diffOutput, "diff --git") {
		t.Fatalf("expected unified diff output, got %q", diffOutput)
	}

	patch := "diff --git a/main.txt b/main.txt\nindex c0d0fb4..83db48f 100644\n--- a/main.txt\n+++ b/main.txt\n@@ -1,2 +1,2 @@\n line1\n-line2-modified\n+line-two\n"
	apply := &GitApplyPatchHandler{}
	applyResult, applyErr := apply.Invoke(ctx, session, mustJSONGit(t, map[string]any{"patch": patch, "check": false}))
	if applyErr != nil {
		t.Fatalf("unexpected git apply error: %v", applyErr)
	}
	if applied := applyResult.Output.(map[string]any)["applied"].(bool); !applied {
		t.Fatalf("expected patch to apply: %#v", applyResult.Output)
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("read file failed: %v", err)
	}
	if !strings.Contains(string(content), "line-two") {
		t.Fatalf("expected patched content, got %q", string(content))
	}
}

func TestGitHandlers_ValidationAndFailures(t *testing.T) {
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}
	ctx := context.Background()

	status := &GitStatusHandler{}
	_, err := status.Invoke(ctx, session, json.RawMessage(`{"short":"bad"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid argument error, got %#v", err)
	}

	apply := &GitApplyPatchHandler{}
	_, err = apply.Invoke(ctx, session, json.RawMessage(`{"patch":""}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected missing patch error, got %#v", err)
	}

	_, err = apply.Invoke(ctx, session, mustJSONGit(t, map[string]any{"patch": "bad patch"}))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution failure, got %#v", err)
	}

	diff := &GitDiffHandler{}
	_, err = diff.Invoke(ctx, session, mustJSONGit(t, map[string]any{"paths": []string{"../outside"}}))
	if err == nil || err.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("expected policy denial for path traversal, got %#v", err)
	}
}

func TestToToolErrorTimeout(t *testing.T) {
	err := toToolError(context.DeadlineExceeded, "")
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution_failed for plain deadline error, got %s", err.Code)
	}

	err = toToolError(errors.New("command timeout"), "")
	if err.Code != app.ErrorCodeTimeout {
		t.Fatalf("expected timeout code, got %s", err.Code)
	}
}

func initGitRepo(t *testing.T) string {
	t.Helper()
	root := t.TempDir()

	runGit(t, root, "init")
	runGit(t, root, "config", "user.email", "tester@example.com")
	runGit(t, root, "config", "user.name", "Tester")

	if err := os.WriteFile(filepath.Join(root, "main.txt"), []byte("line1\nline2\n"), 0o644); err != nil {
		t.Fatalf("write seed file failed: %v", err)
	}
	runGit(t, root, "add", "main.txt")
	runGit(t, root, "commit", "-m", "initial")

	return root
}

func runGit(t *testing.T, cwd string, args ...string) {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = cwd
	if output, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git %v failed: %v (%s)", args, err, string(output))
	}
}

func mustJSONGit(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	return data
}
