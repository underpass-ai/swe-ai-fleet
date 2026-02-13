package tools

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type RepoRunTestsHandler struct {
	runner app.CommandRunner
}

func NewRepoRunTestsHandler(runner app.CommandRunner) *RepoRunTestsHandler {
	return &RepoRunTestsHandler{runner: runner}
}

func (h *RepoRunTestsHandler) Name() string {
	return "repo.run_tests"
}

func (h *RepoRunTestsHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Target    string   `json:"target"`
		ExtraArgs []string `json:"extra_args"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid repo.run_tests args", Retryable: false}
		}
	}

	command, commandArgs, detectErr := detectTestCommand(session.WorkspacePath, request.Target, request.ExtraArgs)
	if detectErr != nil {
		message := detectErr.Error()
		if errors.Is(detectErr, os.ErrNotExist) {
			message = "no supported test runner found (expected go.mod, pytest.ini/pyproject.toml, or package.json)"
		}
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: message, Retryable: false}
	}

	runner := h.runner
	if runner == nil {
		runner = NewLocalCommandRunner()
	}
	commandResult, err := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  command,
		Args:     commandArgs,
		MaxBytes: 2 * 1024 * 1024,
	})
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command":   append([]string{command}, commandArgs...),
			"exit_code": commandResult.ExitCode,
			"output":    commandResult.Output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "test-output.txt",
			ContentType: "text/plain",
			Data:        []byte(commandResult.Output),
		}},
	}
	if err != nil {
		return result, toToolError(err, commandResult.Output)
	}

	return result, nil
}

func detectTestCommand(workspacePath, target string, extraArgs []string) (string, []string, error) {
	if exists(filepath.Join(workspacePath, "go.mod")) {
		args := []string{"test"}
		if strings.TrimSpace(target) == "" {
			args = append(args, "./...")
		} else {
			args = append(args, strings.TrimSpace(target))
		}
		args = append(args, sanitizeArgs(extraArgs)...)
		return "go", args, nil
	}

	if exists(filepath.Join(workspacePath, "pytest.ini")) || exists(filepath.Join(workspacePath, "pyproject.toml")) {
		args := []string{"-q"}
		if strings.TrimSpace(target) != "" {
			args = append(args, strings.TrimSpace(target))
		}
		args = append(args, sanitizeArgs(extraArgs)...)
		return "pytest", args, nil
	}

	if exists(filepath.Join(workspacePath, "package.json")) {
		args := []string{"test"}
		if strings.TrimSpace(target) != "" || len(extraArgs) > 0 {
			args = append(args, "--")
			if strings.TrimSpace(target) != "" {
				args = append(args, strings.TrimSpace(target))
			}
			args = append(args, sanitizeArgs(extraArgs)...)
		}
		return "npm", args, nil
	}

	return "", nil, os.ErrNotExist
}

func sanitizeArgs(items []string) []string {
	out := make([]string, 0, len(items))
	for _, item := range items {
		trimmed := strings.TrimSpace(item)
		if trimmed == "" {
			continue
		}
		if strings.Contains(trimmed, "\x00") {
			continue
		}
		out = append(out, trimmed)
	}
	return out
}

func exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
