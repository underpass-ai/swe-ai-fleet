package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func NewGitStatusHandler(runner app.CommandRunner) *GitStatusHandler {
	return &GitStatusHandler{runner: runner}
}

func NewGitDiffHandler(runner app.CommandRunner) *GitDiffHandler {
	return &GitDiffHandler{runner: runner}
}

func NewGitApplyPatchHandler(runner app.CommandRunner) *GitApplyPatchHandler {
	return &GitApplyPatchHandler{runner: runner}
}

type GitStatusHandler struct {
	runner app.CommandRunner
}

type GitDiffHandler struct {
	runner app.CommandRunner
}

type GitApplyPatchHandler struct {
	runner app.CommandRunner
}

func (h *GitStatusHandler) Name() string {
	return "git.status"
}

func (h *GitStatusHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Short bool `json:"short"`
	}{Short: true}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.status args", Retryable: false}
		}
	}

	command := []string{"status"}
	if request.Short {
		command = append(command, "--porcelain=v1")
	}

	runner := h.runner
	if runner == nil {
		runner = NewLocalCommandRunner()
	}
	commandResult, err := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "git",
		Args:     command,
		MaxBytes: 256 * 1024,
	})
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"status":  commandResult.Output,
		},
	}
	if err != nil {
		return result, toToolError(err, commandResult.Output)
	}
	return result, nil
}

func (h *GitDiffHandler) Name() string {
	return "git.diff"
}

func (h *GitDiffHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Staged bool     `json:"staged"`
		Paths  []string `json:"paths"`
		Base   string   `json:"base"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.diff args", Retryable: false}
		}
	}

	command := []string{"diff"}
	if request.Staged {
		command = append(command, "--staged")
	}
	if strings.TrimSpace(request.Base) != "" {
		command = append(command, strings.TrimSpace(request.Base))
	}
	if len(request.Paths) > 0 {
		command = append(command, "--")
		for _, path := range request.Paths {
			if strings.TrimSpace(path) == "" {
				continue
			}
			if _, pathErr := resolvePath(session, path); pathErr != nil {
				return app.ToolRunResult{}, pathErr
			}
			command = append(command, path)
		}
	}

	runner := h.runner
	if runner == nil {
		runner = NewLocalCommandRunner()
	}
	commandResult, err := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "git",
		Args:     command,
		MaxBytes: 1024 * 1024,
	})
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"diff":    commandResult.Output,
		},
	}
	if err != nil {
		return result, toToolError(err, commandResult.Output)
	}
	return result, nil
}

func (h *GitApplyPatchHandler) Name() string {
	return "git.apply_patch"
}

func (h *GitApplyPatchHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Patch string `json:"patch"`
		Check bool   `json:"check"`
	}{}
	if err := json.Unmarshal(args, &request); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.apply_patch args", Retryable: false}
	}
	if strings.TrimSpace(request.Patch) == "" {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "patch is required", Retryable: false}
	}

	command := []string{"apply", "--whitespace=nowarn"}
	if request.Check {
		command = append(command, "--check")
	}

	runner := h.runner
	if runner == nil {
		runner = NewLocalCommandRunner()
	}
	commandResult, err := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "git",
		Args:     command,
		Stdin:    []byte(request.Patch),
		MaxBytes: 512 * 1024,
	})
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"applied": err == nil,
			"output":  commandResult.Output,
		},
	}
	if err != nil {
		return result, toToolError(err, commandResult.Output)
	}
	return result, nil
}

func toToolError(err error, output string) *domain.Error {
	if strings.Contains(err.Error(), "timeout") {
		return &domain.Error{Code: app.ErrorCodeTimeout, Message: fmt.Sprintf("command timed out: %s", strings.TrimSpace(output)), Retryable: true}
	}
	return &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: fmt.Sprintf("command failed: %s", strings.TrimSpace(output)), Retryable: false}
}
