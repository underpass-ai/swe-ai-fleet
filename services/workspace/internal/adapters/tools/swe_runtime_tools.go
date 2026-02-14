package tools

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type RepoCoverageReportHandler struct {
	runner app.CommandRunner
}

type RepoStaticAnalysisHandler struct {
	runner app.CommandRunner
}

type RepoPackageHandler struct {
	runner app.CommandRunner
}

type SecurityScanSecretsHandler struct {
	runner app.CommandRunner
}

type CIRunPipelineHandler struct {
	runner app.CommandRunner
}

func NewRepoCoverageReportHandler(runner app.CommandRunner) *RepoCoverageReportHandler {
	return &RepoCoverageReportHandler{runner: runner}
}

func NewRepoStaticAnalysisHandler(runner app.CommandRunner) *RepoStaticAnalysisHandler {
	return &RepoStaticAnalysisHandler{runner: runner}
}

func NewRepoPackageHandler(runner app.CommandRunner) *RepoPackageHandler {
	return &RepoPackageHandler{runner: runner}
}

func NewSecurityScanSecretsHandler(runner app.CommandRunner) *SecurityScanSecretsHandler {
	return &SecurityScanSecretsHandler{runner: runner}
}

func NewCIRunPipelineHandler(runner app.CommandRunner) *CIRunPipelineHandler {
	return &CIRunPipelineHandler{runner: runner}
}

func (h *RepoCoverageReportHandler) Name() string {
	return "repo.coverage_report"
}

func (h *RepoCoverageReportHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Target string `json:"target"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid repo.coverage_report args",
				Retryable: false,
			}
		}
	}

	runner := ensureRunner(h.runner)
	detected, detectErr := detectProjectTypeForSession(ctx, runner, session)
	if detectErr != nil {
		if errors.Is(detectErr, os.ErrNotExist) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "no supported test toolchain found",
				Retryable: false,
			}
		}
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   detectErr.Error(),
			Retryable: false,
		}
	}

	target := sanitizeTarget(request.Target)
	if target == "" {
		target = "./..."
	}

	coverageSupported := detected.Name == "go"
	coveragePercent := 0.0
	command := []string{}
	output := ""
	exitCode := 0

	if detected.Name == "go" {
		coverageFile := ".workspace.cover.out"
		command = []string{"go", "test", target, "-coverprofile", coverageFile, "-covermode=atomic"}
		testResult, testErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  "go",
			Args:     []string{"test", target, "-coverprofile", coverageFile, "-covermode=atomic"},
			MaxBytes: 2 * 1024 * 1024,
		})
		output = testResult.Output
		exitCode = testResult.ExitCode
		if testErr == nil {
			coverResult, coverErr := runner.Run(ctx, session, app.CommandSpec{
				Cwd:      session.WorkspacePath,
				Command:  "go",
				Args:     []string{"tool", "cover", "-func=" + coverageFile},
				MaxBytes: 512 * 1024,
			})
			if strings.TrimSpace(coverResult.Output) != "" {
				output = strings.TrimSpace(output + "\n" + coverResult.Output)
			}
			if parsed := parseCoveragePercent(coverResult.Output); parsed != nil {
				coveragePercent = *parsed
			}
			if parsed := parseCoveragePercent(testResult.Output); parsed != nil && coveragePercent == 0.0 {
				coveragePercent = *parsed
			}
			if coverErr != nil {
				exitCode = coverResult.ExitCode
				_, _ = runner.Run(ctx, session, app.CommandSpec{
					Cwd:      session.WorkspacePath,
					Command:  "rm",
					Args:     []string{"-f", coverageFile},
					MaxBytes: 16 * 1024,
				})
				result := app.ToolRunResult{
					ExitCode: exitCode,
					Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: output}},
					Output: map[string]any{
						"project_type":       detected.Name,
						"command":            command,
						"coverage_supported": coverageSupported,
						"coverage_percent":   coveragePercent,
						"exit_code":          exitCode,
						"output":             output,
					},
					Artifacts: []app.ArtifactPayload{{
						Name:        "coverage-report.txt",
						ContentType: "text/plain",
						Data:        []byte(output),
					}},
				}
				return result, toToolError(coverErr, output)
			}
		}
		_, _ = runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  "rm",
			Args:     []string{"-f", coverageFile},
			MaxBytes: 16 * 1024,
		})

		result := app.ToolRunResult{
			ExitCode: exitCode,
			Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: output}},
			Output: map[string]any{
				"project_type":       detected.Name,
				"command":            command,
				"coverage_supported": coverageSupported,
				"coverage_percent":   coveragePercent,
				"exit_code":          exitCode,
				"output":             output,
			},
			Artifacts: []app.ArtifactPayload{{
				Name:        "coverage-report.txt",
				ContentType: "text/plain",
				Data:        []byte(output),
			}},
		}
		if testErr != nil {
			return result, toToolError(testErr, output)
		}
		return result, nil
	}

	testCommand, testArgs, commandErr := testCommandForProject(session.WorkspacePath, detected, target, nil)
	if commandErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   commandErr.Error(),
			Retryable: false,
		}
	}
	command = append([]string{testCommand}, testArgs...)
	testResult, testErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  testCommand,
		Args:     testArgs,
		MaxBytes: 2 * 1024 * 1024,
	})
	exitCode = testResult.ExitCode
	output = testResult.Output
	if parsed := parseCoveragePercent(testResult.Output); parsed != nil {
		coveragePercent = *parsed
		coverageSupported = true
	}

	result := app.ToolRunResult{
		ExitCode: exitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: output}},
		Output: map[string]any{
			"project_type":       detected.Name,
			"command":            command,
			"coverage_supported": coverageSupported,
			"coverage_percent":   coveragePercent,
			"exit_code":          exitCode,
			"output":             output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "coverage-report.txt",
			ContentType: "text/plain",
			Data:        []byte(output),
		}},
	}
	if testErr != nil {
		return result, toToolError(testErr, output)
	}
	return result, nil
}

func (h *RepoStaticAnalysisHandler) Name() string {
	return "repo.static_analysis"
}

func (h *RepoStaticAnalysisHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Target string `json:"target"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid repo.static_analysis args",
				Retryable: false,
			}
		}
	}

	runner := ensureRunner(h.runner)
	detected, detectErr := detectProjectTypeForSession(ctx, runner, session)
	if detectErr != nil {
		if errors.Is(detectErr, os.ErrNotExist) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "no supported static analysis toolchain found",
				Retryable: false,
			}
		}
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   detectErr.Error(),
			Retryable: false,
		}
	}

	command, commandArgs, commandErr := staticAnalysisCommandForProject(
		session.WorkspacePath,
		detected,
		sanitizeTarget(request.Target),
	)
	if commandErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   commandErr.Error(),
			Retryable: false,
		}
	}

	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  command,
		Args:     commandArgs,
		MaxBytes: 2 * 1024 * 1024,
	})
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"project_type": detected.Name,
			"command":      append([]string{command}, commandArgs...),
			"exit_code":    commandResult.ExitCode,
			"diagnostics":  extractDiagnostics(commandResult.Output, 80),
			"output":       commandResult.Output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "static-analysis-output.txt",
			ContentType: "text/plain",
			Data:        []byte(commandResult.Output),
		}},
	}
	if runErr != nil {
		return result, toToolError(runErr, commandResult.Output)
	}
	return result, nil
}

func (h *RepoPackageHandler) Name() string {
	return "repo.package"
}

func (h *RepoPackageHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Target string `json:"target"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid repo.package args",
				Retryable: false,
			}
		}
	}

	runner := ensureRunner(h.runner)
	detected, detectErr := detectProjectTypeForSession(ctx, runner, session)
	if detectErr != nil {
		if errors.Is(detectErr, os.ErrNotExist) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "no supported packaging toolchain found",
				Retryable: false,
			}
		}
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   detectErr.Error(),
			Retryable: false,
		}
	}

	command, commandArgs, artifactPath, ensureDist, commandErr := packageCommandForProject(
		session.WorkspacePath,
		detected,
		sanitizeTarget(request.Target),
	)
	if commandErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   commandErr.Error(),
			Retryable: false,
		}
	}
	if ensureDist {
		if _, mkdirErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  "mkdir",
			Args:     []string{"-p", ".workspace-dist"},
			MaxBytes: 16 * 1024,
		}); mkdirErr != nil {
			return app.ToolRunResult{}, toToolError(mkdirErr, "failed to create .workspace-dist")
		}
	}

	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  command,
		Args:     commandArgs,
		MaxBytes: 2 * 1024 * 1024,
	})

	if detected.Name == "node" {
		if packed := detectNodePackageArtifact(commandResult.Output); packed != "" {
			artifactPath = packed
		}
	}

	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"project_type":  detected.Name,
			"command":       append([]string{command}, commandArgs...),
			"artifact_path": artifactPath,
			"exit_code":     commandResult.ExitCode,
			"output":        commandResult.Output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "package-output.txt",
			ContentType: "text/plain",
			Data:        []byte(commandResult.Output),
		}},
	}
	if runErr != nil {
		return result, toToolError(runErr, commandResult.Output)
	}
	return result, nil
}

func (h *SecurityScanSecretsHandler) Name() string {
	return "security.scan_secrets"
}

func (h *SecurityScanSecretsHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path       string `json:"path"`
		MaxResults int    `json:"max_results"`
	}{Path: ".", MaxResults: 200}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid security.scan_secrets args",
				Retryable: false,
			}
		}
	}
	if request.MaxResults <= 0 {
		request.MaxResults = 200
	}
	if request.MaxResults > 2000 {
		request.MaxResults = 2000
	}

	scanPath, pathErr := sanitizeRelativePath(request.Path)
	if pathErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   pathErr.Error(),
			Retryable: false,
		}
	}
	if scanPath == "" {
		scanPath = "."
	}

	rgArgs := []string{
		"-n",
		"--hidden",
		"--glob", "!.git",
		"--glob", "!node_modules",
		"--glob", "!target",
		"--glob", "!.workspace-venv",
		"-m", strconv.Itoa(request.MaxResults),
		"-e", "AKIA[0-9A-Z]{16}",
		"-e", "BEGIN RSA PRIVATE KEY",
		"-e", "BEGIN OPENSSH PRIVATE KEY",
		"-e", `(?i)(api[_-]?key|secret|token)[[:space:]]*[:=][[:space:]]*["'][^"']{12,}["']`,
		scanPath,
	}

	commandResult, runErr := ensureRunner(h.runner).Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "rg",
		Args:     rgArgs,
		MaxBytes: 2 * 1024 * 1024,
	})

	// ripgrep exits 1 when there are no matches; that's a successful "clean" scan.
	if runErr != nil && commandResult.ExitCode != 1 {
		result := app.ToolRunResult{
			ExitCode: commandResult.ExitCode,
			Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
			Output: map[string]any{
				"findings_count": 0,
				"findings":       []any{},
				"truncated":      false,
				"output":         commandResult.Output,
			},
			Artifacts: []app.ArtifactPayload{{
				Name:        "secrets-scan-output.txt",
				ContentType: "text/plain",
				Data:        []byte(commandResult.Output),
			}},
		}
		return result, toToolError(runErr, commandResult.Output)
	}

	findings := parseSecretFindings(commandResult.Output, request.MaxResults)
	result := app.ToolRunResult{
		ExitCode: 0,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: commandResult.Output}},
		Output: map[string]any{
			"findings_count": len(findings),
			"findings":       findings,
			"truncated":      len(findings) >= request.MaxResults,
			"output":         commandResult.Output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "secrets-scan-output.txt",
			ContentType: "text/plain",
			Data:        []byte(commandResult.Output),
		}},
	}
	return result, nil
}

func (h *CIRunPipelineHandler) Name() string {
	return "ci.run_pipeline"
}

func (h *CIRunPipelineHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Target          string `json:"target"`
		IncludeStatic   bool   `json:"include_static_analysis"`
		IncludeCoverage bool   `json:"include_coverage"`
		FailFast        bool   `json:"fail_fast"`
	}{IncludeStatic: true, IncludeCoverage: true, FailFast: true}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid ci.run_pipeline args",
				Retryable: false,
			}
		}
	}

	runner := ensureRunner(h.runner)
	detected, detectErr := detectProjectTypeForSession(ctx, runner, session)
	if detectErr != nil {
		if errors.Is(detectErr, os.ErrNotExist) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "no supported toolchain found",
				Retryable: false,
			}
		}
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   detectErr.Error(),
			Retryable: false,
		}
	}

	target := sanitizeTarget(request.Target)
	steps := make([]map[string]any, 0, 5)
	combinedOutput := strings.Builder{}
	failedStep := ""
	finalExitCode := 0
	finalErr := (*domain.Error)(nil)

	runStep := func(stepName string, command string, commandArgs []string) bool {
		result, runErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  command,
			Args:     commandArgs,
			MaxBytes: 2 * 1024 * 1024,
		})
		status := "succeeded"
		if runErr != nil {
			status = "failed"
		}
		if strings.TrimSpace(result.Output) != "" {
			if combinedOutput.Len() > 0 {
				combinedOutput.WriteString("\n")
			}
			combinedOutput.WriteString("[" + stepName + "]\n")
			combinedOutput.WriteString(result.Output)
		}
		steps = append(steps, map[string]any{
			"name":      stepName,
			"status":    status,
			"command":   append([]string{command}, commandArgs...),
			"exit_code": result.ExitCode,
		})
		if runErr != nil {
			failedStep = stepName
			finalExitCode = result.ExitCode
			finalErr = toToolError(runErr, result.Output)
			if finalErr != nil && finalErr.Code == app.ErrorCodeTimeout {
				finalErr.Message = "pipeline step timed out: " + stepName
			}
			if finalErr != nil && finalErr.Code == app.ErrorCodeExecutionFailed {
				finalErr.Message = "pipeline step failed: " + stepName
			}
			return false
		}
		return true
	}

	validateCommand, validateArgs, validateErr := validateCommandForProject(session.WorkspacePath, detected, target)
	if validateErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   validateErr.Error(),
			Retryable: false,
		}
	}
	if !runStep("validate", validateCommand, validateArgs) && request.FailFast {
		return ciPipelineResult(detected.Name, steps, failedStep, finalExitCode, combinedOutput.String()), finalErr
	}

	buildCommand, buildArgs, buildErr := buildCommandForProject(session.WorkspacePath, detected, target, nil)
	if buildErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   buildErr.Error(),
			Retryable: false,
		}
	}
	if !runStep("build", buildCommand, buildArgs) && request.FailFast {
		return ciPipelineResult(detected.Name, steps, failedStep, finalExitCode, combinedOutput.String()), finalErr
	}

	testCommand, testArgs, testErr := testCommandForProject(session.WorkspacePath, detected, target, nil)
	if testErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   testErr.Error(),
			Retryable: false,
		}
	}
	if !runStep("test", testCommand, testArgs) && request.FailFast {
		return ciPipelineResult(detected.Name, steps, failedStep, finalExitCode, combinedOutput.String()), finalErr
	}

	if request.IncludeStatic {
		staticCommand, staticArgs, staticErr := staticAnalysisCommandForProject(session.WorkspacePath, detected, target)
		if staticErr == nil {
			if !runStep("static_analysis", staticCommand, staticArgs) && request.FailFast {
				return ciPipelineResult(detected.Name, steps, failedStep, finalExitCode, combinedOutput.String()), finalErr
			}
		} else {
			steps = append(steps, map[string]any{
				"name":      "static_analysis",
				"status":    "skipped",
				"command":   []string{},
				"exit_code": 0,
			})
		}
	}

	if request.IncludeCoverage {
		if detected.Name == "go" {
			coverageFile := ".workspace.cover.out"
			if !runStep("coverage", "go", []string{"test", targetOrDefault(target, "./..."), "-coverprofile", coverageFile, "-covermode=atomic"}) && request.FailFast {
				return ciPipelineResult(detected.Name, steps, failedStep, finalExitCode, combinedOutput.String()), finalErr
			}
			_, _ = runner.Run(ctx, session, app.CommandSpec{
				Cwd:      session.WorkspacePath,
				Command:  "rm",
				Args:     []string{"-f", coverageFile},
				MaxBytes: 16 * 1024,
			})
		} else {
			steps = append(steps, map[string]any{
				"name":      "coverage",
				"status":    "skipped",
				"command":   []string{},
				"exit_code": 0,
			})
		}
	}

	if failedStep != "" {
		return ciPipelineResult(detected.Name, steps, failedStep, finalExitCode, combinedOutput.String()), finalErr
	}
	return ciPipelineResult(detected.Name, steps, "", 0, combinedOutput.String()), nil
}

func ciPipelineResult(projectType string, steps []map[string]any, failedStep string, exitCode int, output string) app.ToolRunResult {
	summary := "pipeline succeeded"
	if failedStep != "" {
		summary = "pipeline failed on " + failedStep
	}
	return app.ToolRunResult{
		ExitCode: exitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: output}},
		Output: map[string]any{
			"project_type": projectType,
			"steps":        steps,
			"exit_code":    exitCode,
			"failed_step":  failedStep,
			"summary":      summary,
			"output":       output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "ci-pipeline-output.txt",
			ContentType: "text/plain",
			Data:        []byte(output),
		}},
	}
}

func staticAnalysisCommandForProject(workspacePath string, detected projectType, target string) (string, []string, error) {
	switch detected.Name {
	case "go":
		return "go", []string{"vet", targetOrDefault(target, "./...")}, nil
	case "rust":
		return "cargo", []string{"clippy", "--all-targets", "--all-features", "--", "-D", "warnings"}, nil
	case "node":
		args := []string{"run", "lint", "--if-present"}
		if strings.TrimSpace(target) != "" {
			args = append(args, "--", target)
		}
		return "npm", args, nil
	case "python":
		pythonExecutable := resolvePythonExecutable(workspacePath)
		return pythonExecutable, []string{"-m", "compileall", targetOrDefault(target, ".")}, nil
	case "java":
		if detected.Flavor == "gradle" {
			return "gradle", []string{"check", "-x", "test"}, nil
		}
		return "mvn", []string{"-q", "-DskipTests", "verify"}, nil
	case "c":
		source, sourceErr := resolveCSourceForBuild(workspacePath, target)
		if sourceErr != nil {
			return "", nil, sourceErr
		}
		return "cc", []string{"-std=c11", "-fsyntax-only", source}, nil
	default:
		return "", nil, os.ErrNotExist
	}
}

func packageCommandForProject(workspacePath string, detected projectType, target string) (string, []string, string, bool, error) {
	switch detected.Name {
	case "go":
		args := []string{"build", "-o", ".workspace-dist/app"}
		args = append(args, targetOrDefault(target, "."))
		return "go", args, ".workspace-dist/app", true, nil
	case "rust":
		args := []string{"build", "--release"}
		if strings.TrimSpace(target) != "" {
			args = append(args, "--package", target)
		}
		return "cargo", args, "target/release", false, nil
	case "node":
		return "npm", []string{"pack", "--silent"}, "", false, nil
	case "python":
		pythonExecutable := resolvePythonExecutable(workspacePath)
		return pythonExecutable, []string{"-m", "pip", "wheel", ".", "-w", ".workspace-dist"}, ".workspace-dist", true, nil
	case "java":
		if detected.Flavor == "gradle" {
			return "gradle", []string{"assemble"}, "build/libs", false, nil
		}
		return "mvn", []string{"-q", "-DskipTests", "package"}, "target", false, nil
	case "c":
		source, sourceErr := resolveCSourceForBuild(workspacePath, target)
		if sourceErr != nil {
			return "", nil, "", false, sourceErr
		}
		return "cc", []string{"-std=c11", "-O2", "-Wall", "-Wextra", "-o", ".workspace-dist/c-app", source}, ".workspace-dist/c-app", true, nil
	default:
		return "", nil, "", false, os.ErrNotExist
	}
}

func detectNodePackageArtifact(output string) string {
	lines := splitOutputLines(output)
	for _, line := range lines {
		if strings.HasSuffix(line, ".tgz") && !strings.Contains(line, " ") {
			return line
		}
	}
	return ""
}

func parseSecretFindings(output string, maxResults int) []map[string]any {
	lines := splitOutputLines(output)
	findings := make([]map[string]any, 0, len(lines))
	for _, line := range lines {
		parts := strings.SplitN(line, ":", 3)
		if len(parts) < 3 {
			continue
		}
		lineNo, _ := strconv.Atoi(parts[1])
		snippet := strings.TrimSpace(parts[2])
		if len(snippet) > 200 {
			snippet = snippet[:200]
		}
		findings = append(findings, map[string]any{
			"path":    strings.TrimSpace(parts[0]),
			"line":    lineNo,
			"snippet": snippet,
		})
		if len(findings) >= maxResults {
			break
		}
	}
	return findings
}

func targetOrDefault(target string, fallback string) string {
	trimmed := strings.TrimSpace(target)
	if trimmed == "" {
		return fallback
	}
	return trimmed
}
