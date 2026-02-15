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

func NewGitCheckoutHandler(runner app.CommandRunner) *GitCheckoutHandler {
	return &GitCheckoutHandler{runner: runner}
}

func NewGitLogHandler(runner app.CommandRunner) *GitLogHandler {
	return &GitLogHandler{runner: runner}
}

func NewGitShowHandler(runner app.CommandRunner) *GitShowHandler {
	return &GitShowHandler{runner: runner}
}

func NewGitBranchListHandler(runner app.CommandRunner) *GitBranchListHandler {
	return &GitBranchListHandler{runner: runner}
}

func NewGitCommitHandler(runner app.CommandRunner) *GitCommitHandler {
	return &GitCommitHandler{runner: runner}
}

func NewGitPushHandler(runner app.CommandRunner) *GitPushHandler {
	return &GitPushHandler{runner: runner}
}

func NewGitFetchHandler(runner app.CommandRunner) *GitFetchHandler {
	return &GitFetchHandler{runner: runner}
}

func NewGitPullHandler(runner app.CommandRunner) *GitPullHandler {
	return &GitPullHandler{runner: runner}
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

type GitCheckoutHandler struct {
	runner app.CommandRunner
}

type GitLogHandler struct {
	runner app.CommandRunner
}

type GitShowHandler struct {
	runner app.CommandRunner
}

type GitBranchListHandler struct {
	runner app.CommandRunner
}

type GitCommitHandler struct {
	runner app.CommandRunner
}

type GitPushHandler struct {
	runner app.CommandRunner
}

type GitFetchHandler struct {
	runner app.CommandRunner
}

type GitPullHandler struct {
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

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 256*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"status":  commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
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
		filteredPaths := make([]string, 0, len(request.Paths))
		for _, path := range request.Paths {
			trimmed := strings.TrimSpace(path)
			if trimmed == "" {
				continue
			}
			if _, pathErr := resolvePath(session, trimmed); pathErr != nil {
				return app.ToolRunResult{}, pathErr
			}
			filteredPaths = append(filteredPaths, trimmed)
		}
		if len(filteredPaths) > 0 {
			command = append(command, "--")
			command = append(command, filteredPaths...)
		}
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 1024*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"diff":    commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
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

	patchPaths, patchErr := extractPatchPaths(request.Patch)
	if patchErr != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid patch payload", Retryable: false}
	}
	for _, path := range patchPaths {
		if !pathAllowed(path, session.AllowedPaths) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodePolicyDenied,
				Message:   "patch touches paths outside allowed_paths",
				Retryable: false,
			}
		}
	}

	command := []string{"apply", "--whitespace=nowarn"}
	if request.Check {
		command = append(command, "--check")
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, []byte(request.Patch), 512*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command":       append([]string{"git"}, command...),
			"applied":       runErr == nil,
			"output":        commandResult.Output,
			"changed_paths": patchPaths,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitCheckoutHandler) Name() string {
	return "git.checkout"
}

func (h *GitCheckoutHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Ref        string `json:"ref"`
		Create     bool   `json:"create"`
		StartPoint string `json:"start_point"`
		Force      bool   `json:"force"`
	}{}
	if err := json.Unmarshal(args, &request); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.checkout args", Retryable: false}
	}

	ref := strings.TrimSpace(request.Ref)
	if ref == "" {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "ref is required", Retryable: false}
	}
	if !gitRefAllowed(session, ref) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "ref outside allowlist", Retryable: false}
	}

	startPoint := strings.TrimSpace(request.StartPoint)
	if startPoint != "" && !gitRefAllowed(session, startPoint) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "start_point outside allowlist", Retryable: false}
	}

	command := []string{"checkout"}
	if request.Force {
		command = append(command, "--force")
	}
	if request.Create {
		command = append(command, "-b", ref)
		if startPoint != "" {
			command = append(command, startPoint)
		}
	} else {
		command = append(command, ref)
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 512*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"ref":     ref,
			"created": request.Create,
			"output":  commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitLogHandler) Name() string {
	return "git.log"
}

func (h *GitLogHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Ref      string `json:"ref"`
		MaxCount int    `json:"max_count"`
	}{
		Ref:      "HEAD",
		MaxCount: 20,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.log args", Retryable: false}
		}
	}

	ref := strings.TrimSpace(request.Ref)
	if ref == "" {
		ref = "HEAD"
	}
	if !gitRefAllowed(session, ref) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "ref outside allowlist", Retryable: false}
	}
	maxCount := clampInt(request.MaxCount, 1, 200, 20)

	command := []string{
		"log",
		"--date=iso-strict",
		fmt.Sprintf("--max-count=%d", maxCount),
		"--pretty=format:%H%x1f%an%x1f%ae%x1f%ad%x1f%s%x1f%P",
		ref,
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 1024*1024)
	entries := parseGitLogEntries(commandResult.Output)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"ref":     ref,
			"count":   len(entries),
			"entries": entries,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitShowHandler) Name() string {
	return "git.show"
}

func (h *GitShowHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Ref   string `json:"ref"`
		Path  string `json:"path"`
		Stat  bool   `json:"stat"`
		Patch bool   `json:"patch"`
	}{
		Ref:   "HEAD",
		Stat:  true,
		Patch: true,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.show args", Retryable: false}
		}
	}

	ref := strings.TrimSpace(request.Ref)
	if ref == "" {
		ref = "HEAD"
	}
	if !gitRefAllowed(session, ref) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "ref outside allowlist", Retryable: false}
	}

	command := []string{"show", "--no-color"}
	if request.Stat && !request.Patch {
		command = append(command, "--stat")
	}
	if !request.Stat && request.Patch {
		command = append(command, "--patch")
	}
	if !request.Stat && !request.Patch {
		command = append(command, "--pretty=fuller", "--no-patch")
	}
	command = append(command, ref)

	path := strings.TrimSpace(request.Path)
	if path != "" {
		if _, pathErr := resolvePath(session, path); pathErr != nil {
			return app.ToolRunResult{}, pathErr
		}
		command = append(command, "--", path)
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 1024*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"ref":     ref,
			"path":    path,
			"show":    commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitBranchListHandler) Name() string {
	return "git.branch_list"
}

func (h *GitBranchListHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		All     bool `json:"all"`
		Remotes bool `json:"remotes"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.branch_list args", Retryable: false}
		}
	}

	command := []string{"branch", "--list", "--format=%(refname:short)%00%(upstream:short)%00%(objectname)%00%(HEAD)"}
	if request.All {
		command = append(command, "-a")
	} else if request.Remotes {
		command = append(command, "-r")
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 512*1024)
	branches := parseGitBranchEntries(commandResult.Output)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command":  append([]string{"git"}, command...),
			"count":    len(branches),
			"branches": branches,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitCommitHandler) Name() string {
	return "git.commit"
}

func (h *GitCommitHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Message string   `json:"message"`
		All     bool     `json:"all"`
		Paths   []string `json:"paths"`
	}{}
	if err := json.Unmarshal(args, &request); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.commit args", Retryable: false}
	}

	message := strings.TrimSpace(request.Message)
	if message == "" {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "message is required", Retryable: false}
	}

	command := []string{"commit", "-m", message}
	if request.All {
		command = append(command, "--all")
	}
	if len(request.Paths) > 0 {
		filteredPaths := make([]string, 0, len(request.Paths))
		for _, path := range request.Paths {
			trimmed := strings.TrimSpace(path)
			if trimmed == "" {
				continue
			}
			if _, pathErr := resolvePath(session, trimmed); pathErr != nil {
				return app.ToolRunResult{}, pathErr
			}
			filteredPaths = append(filteredPaths, trimmed)
		}
		if len(filteredPaths) > 0 {
			command = append(command, "--")
			command = append(command, filteredPaths...)
		}
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 512*1024)
	commitHash := ""
	if runErr == nil {
		hashResult, hashErr := executeGit(ctx, h.runner, session, []string{"rev-parse", "HEAD"}, nil, 64*1024)
		if hashErr == nil {
			commitHash = strings.TrimSpace(hashResult.Output)
		}
	}

	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command":   append([]string{"git"}, command...),
			"committed": runErr == nil,
			"commit":    commitHash,
			"output":    commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitPushHandler) Name() string {
	return "git.push"
}

func (h *GitPushHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Remote         string `json:"remote"`
		Refspec        string `json:"refspec"`
		SetUpstream    bool   `json:"set_upstream"`
		ForceWithLease bool   `json:"force_with_lease"`
	}{
		Remote: "origin",
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.push args", Retryable: false}
		}
	}

	remote := strings.TrimSpace(request.Remote)
	if remote == "" {
		remote = "origin"
	}
	if !gitRemoteAllowed(session, remote) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "remote outside allowlist", Retryable: false}
	}
	refspec := strings.TrimSpace(request.Refspec)
	if !gitRefspecAllowed(session, refspec) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "refspec outside allowlist", Retryable: false}
	}

	command := []string{"push"}
	if request.SetUpstream {
		command = append(command, "--set-upstream")
	}
	if request.ForceWithLease {
		command = append(command, "--force-with-lease")
	}
	command = append(command, remote)
	if refspec != "" {
		command = append(command, refspec)
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 1024*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"remote":  remote,
			"refspec": refspec,
			"pushed":  runErr == nil,
			"output":  commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitFetchHandler) Name() string {
	return "git.fetch"
}

func (h *GitFetchHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Remote  string `json:"remote"`
		Refspec string `json:"refspec"`
		Prune   bool   `json:"prune"`
		Tags    bool   `json:"tags"`
	}{
		Remote: "origin",
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.fetch args", Retryable: false}
		}
	}

	remote := strings.TrimSpace(request.Remote)
	if remote == "" {
		remote = "origin"
	}
	if !gitRemoteAllowed(session, remote) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "remote outside allowlist", Retryable: false}
	}
	refspec := strings.TrimSpace(request.Refspec)
	if !gitRefspecAllowed(session, refspec) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "refspec outside allowlist", Retryable: false}
	}

	command := []string{"fetch"}
	if request.Prune {
		command = append(command, "--prune")
	}
	if request.Tags {
		command = append(command, "--tags")
	}
	command = append(command, remote)
	if refspec != "" {
		command = append(command, refspec)
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 1024*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"remote":  remote,
			"refspec": refspec,
			"fetched": runErr == nil,
			"output":  commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func (h *GitPullHandler) Name() string {
	return "git.pull"
}

func (h *GitPullHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Remote  string `json:"remote"`
		Refspec string `json:"refspec"`
		Rebase  bool   `json:"rebase"`
	}{
		Remote: "origin",
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid git.pull args", Retryable: false}
		}
	}

	remote := strings.TrimSpace(request.Remote)
	if remote == "" {
		remote = "origin"
	}
	if !gitRemoteAllowed(session, remote) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "remote outside allowlist", Retryable: false}
	}
	refspec := strings.TrimSpace(request.Refspec)
	if !gitRefspecAllowed(session, refspec) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodePolicyDenied, Message: "refspec outside allowlist", Retryable: false}
	}

	command := []string{"pull"}
	if request.Rebase {
		command = append(command, "--rebase")
	}
	command = append(command, remote)
	if refspec != "" {
		command = append(command, refspec)
	}

	commandResult, runErr := executeGit(ctx, h.runner, session, command, nil, 1024*1024)
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"command": append([]string{"git"}, command...),
			"remote":  remote,
			"refspec": refspec,
			"pulled":  runErr == nil,
			"output":  commandResult.Output,
		},
	}
	if runErr != nil {
		return result, runErr
	}
	return result, nil
}

func executeGit(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	command []string,
	stdin []byte,
	maxBytes int,
) (app.CommandResult, *domain.Error) {
	resolvedRunner := runner
	if resolvedRunner == nil {
		resolvedRunner = NewLocalCommandRunner()
	}
	commandResult, err := resolvedRunner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "git",
		Args:     command,
		Stdin:    stdin,
		MaxBytes: maxBytes,
	})
	if err != nil {
		return commandResult, toGitToolError(err, commandResult.ExitCode, commandResult.Output)
	}
	return commandResult, nil
}

func parseGitLogEntries(output string) []map[string]any {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	entries := make([]map[string]any, 0, len(lines))
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		parts := strings.Split(trimmed, "\x1f")
		if len(parts) < 6 {
			continue
		}
		parents := []string{}
		for _, parent := range strings.Fields(strings.TrimSpace(parts[5])) {
			if parent != "" {
				parents = append(parents, parent)
			}
		}
		entries = append(entries, map[string]any{
			"hash":         strings.TrimSpace(parts[0]),
			"author_name":  strings.TrimSpace(parts[1]),
			"author_email": strings.TrimSpace(parts[2]),
			"date":         strings.TrimSpace(parts[3]),
			"subject":      strings.TrimSpace(parts[4]),
			"parents":      parents,
		})
	}
	return entries
}

func parseGitBranchEntries(output string) []map[string]any {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	branches := make([]map[string]any, 0, len(lines))
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		parts := strings.Split(trimmed, "\x00")
		if len(parts) < 4 {
			parts = strings.Split(trimmed, "\x1f")
		}
		if len(parts) < 4 {
			parts = strings.Split(trimmed, "%x1f")
		}
		if len(parts) < 4 {
			continue
		}
		name := strings.TrimSpace(parts[0])
		if name == "" {
			continue
		}
		branches = append(branches, map[string]any{
			"name":     name,
			"upstream": strings.TrimSpace(parts[1]),
			"commit":   strings.TrimSpace(parts[2]),
			"current":  strings.TrimSpace(parts[3]) == "*",
		})
	}
	return branches
}

func gitRemoteAllowed(session domain.Session, remote string) bool {
	allowlist := parseMetadataList(session.Metadata, "allowed_git_remotes")
	if len(allowlist) == 0 {
		return true
	}
	remote = strings.TrimSpace(remote)
	for _, allowed := range allowlist {
		if allowed == "*" || allowed == remote {
			return true
		}
	}
	return false
}

func gitRefAllowed(session domain.Session, ref string) bool {
	prefixes := parseMetadataList(session.Metadata, "allowed_git_ref_prefixes")
	return gitRefAllowedWithPrefixes(prefixes, ref)
}

func gitRefAllowedWithPrefixes(prefixes []string, ref string) bool {
	candidate := normalizeGitRefCandidate(ref)
	if candidate == "" {
		return true
	}
	if len(prefixes) == 0 {
		return true
	}

	for _, rawPrefix := range prefixes {
		prefix := strings.TrimSpace(rawPrefix)
		if prefix == "" {
			continue
		}
		if prefix == "*" {
			return true
		}
		if strings.HasPrefix(candidate, prefix) {
			return true
		}
		if !strings.HasPrefix(candidate, "refs/") {
			if strings.HasPrefix("refs/heads/"+candidate, prefix) || strings.HasPrefix("refs/tags/"+candidate, prefix) || strings.HasPrefix("refs/remotes/"+candidate, prefix) {
				return true
			}
		}
	}
	return false
}

func gitRefspecAllowed(session domain.Session, refspec string) bool {
	prefixes := parseMetadataList(session.Metadata, "allowed_git_ref_prefixes")
	if len(prefixes) == 0 {
		return true
	}

	spec := strings.TrimSpace(refspec)
	if spec == "" {
		return true
	}

	parts := strings.SplitN(spec, ":", 2)
	if len(parts) == 1 {
		return gitRefAllowedWithPrefixes(prefixes, parts[0])
	}
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed == "" {
			continue
		}
		if !gitRefAllowedWithPrefixes(prefixes, trimmed) {
			return false
		}
	}
	return true
}

func normalizeGitRefCandidate(raw string) string {
	candidate := strings.TrimSpace(raw)
	candidate = strings.TrimPrefix(candidate, "+")
	return strings.TrimSpace(candidate)
}

func parseMetadataList(metadata map[string]string, key string) []string {
	if len(metadata) == 0 {
		return nil
	}
	raw := strings.TrimSpace(metadata[key])
	if raw == "" {
		return nil
	}
	out := make([]string, 0, 4)
	for _, part := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(part)
		if candidate == "" {
			continue
		}
		out = append(out, candidate)
	}
	return out
}

func toGitToolError(err error, exitCode int, output string) *domain.Error {
	if strings.Contains(err.Error(), "timeout") {
		return &domain.Error{
			Code:      app.ErrorCodeTimeout,
			Message:   fmt.Sprintf("command timed out: %s", strings.TrimSpace(output)),
			Retryable: true,
		}
	}

	code := app.ErrorCodeExecutionFailed
	switch exitCode {
	case 128:
		code = app.ErrorCodeGitRepoError
	case 129:
		code = app.ErrorCodeGitUsageError
	}

	message := strings.TrimSpace(output)
	if message == "" {
		message = err.Error()
	}
	return &domain.Error{
		Code:      code,
		Message:   fmt.Sprintf("command failed: %s", message),
		Retryable: false,
	}
}

func toToolError(err error, output string) *domain.Error {
	if strings.Contains(err.Error(), "timeout") {
		return &domain.Error{Code: app.ErrorCodeTimeout, Message: fmt.Sprintf("command timed out: %s", strings.TrimSpace(output)), Retryable: true}
	}
	return &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: fmt.Sprintf("command failed: %s", strings.TrimSpace(output)), Retryable: false}
}
