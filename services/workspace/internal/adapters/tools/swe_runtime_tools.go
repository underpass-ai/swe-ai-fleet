package tools

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

const (
	sweUnknown             = "unknown"
	sweTextPlain           = "text/plain"
	sweApplicationJSON     = "application/json"
	sweCoverageReportTxt   = "coverage-report.txt"
	sweCoverProfile        = "-coverprofile"
	sweCoverModeAtomic     = "-covermode=atomic"
	sweWorkspaceDist       = ".workspace-dist"
	sweHeuristicDockerfile = "heuristic-dockerfile"
	sweLicenseIsUnknown    = "license is unknown"
	sweCycloneDXJSON       = "cyclonedx-json"
	sweRgGlobFlag          = "--glob"
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

type SecurityScanDependenciesHandler struct {
	runner app.CommandRunner
}

type SBOMGenerateHandler struct {
	runner app.CommandRunner
}

type SecurityScanContainerHandler struct {
	runner app.CommandRunner
}

type SecurityLicenseCheckHandler struct {
	runner app.CommandRunner
}

type QualityGateHandler struct {
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

func NewSecurityScanDependenciesHandler(runner app.CommandRunner) *SecurityScanDependenciesHandler {
	return &SecurityScanDependenciesHandler{runner: runner}
}

func NewSBOMGenerateHandler(runner app.CommandRunner) *SBOMGenerateHandler {
	return &SBOMGenerateHandler{runner: runner}
}

func NewSecurityScanContainerHandler(runner app.CommandRunner) *SecurityScanContainerHandler {
	return &SecurityScanContainerHandler{runner: runner}
}

func NewSecurityLicenseCheckHandler(runner app.CommandRunner) *SecurityLicenseCheckHandler {
	return &SecurityLicenseCheckHandler{runner: runner}
}

func NewQualityGateHandler(runner app.CommandRunner) *QualityGateHandler {
	return &QualityGateHandler{runner: runner}
}

func NewCIRunPipelineHandler(runner app.CommandRunner) *CIRunPipelineHandler {
	return &CIRunPipelineHandler{runner: runner}
}

type qualityGateThresholdsRequest struct {
	MinCoveragePercent *float64 `json:"min_coverage_percent"`
	MaxDiagnostics     *int     `json:"max_diagnostics"`
	MaxVulnerabilities *int     `json:"max_vulnerabilities"`
	MaxDeniedLicenses  *int     `json:"max_denied_licenses"`
	MaxFailedTests     *int     `json:"max_failed_tests"`
}

type qualityGateRequest struct {
	Metrics map[string]any `json:"metrics"`
	qualityGateThresholdsRequest
}

type qualityGateConfig struct {
	MinCoveragePercent float64
	MaxDiagnostics     int
	MaxVulnerabilities int
	MaxDeniedLicenses  int
	MaxFailedTests     int
}

type qualityGateMetrics struct {
	CoveragePercent      float64 `json:"coverage_percent"`
	DiagnosticsCount     int     `json:"diagnostics_count"`
	VulnerabilitiesCount int     `json:"vulnerabilities_count"`
	DeniedLicensesCount  int     `json:"denied_licenses_count"`
	FailedTestsCount     int     `json:"failed_tests_count"`
}

type qualityGateRule struct {
	Name     string  `json:"name"`
	Operator string  `json:"operator"`
	Expected float64 `json:"expected"`
	Actual   float64 `json:"actual"`
	Passed   bool    `json:"passed"`
	Message  string  `json:"message"`
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
		return runGoCoverageReport(ctx, runner, session, detected.Name, target)
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
			Name:        sweCoverageReportTxt,
			ContentType: sweTextPlain,
			Data:        []byte(output),
		}},
	}
	if testErr != nil {
		return result, toToolError(testErr, output)
	}
	return result, nil
}

func runGoCoverageReport(ctx context.Context, runner app.CommandRunner, session domain.Session, projectType, target string) (app.ToolRunResult, *domain.Error) {
	coverageFile := ".workspace.cover.out"
	command := []string{"go", "test", target, sweCoverProfile, coverageFile, sweCoverModeAtomic}
	testResult, testErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "go",
		Args:     []string{"test", target, sweCoverProfile, coverageFile, sweCoverModeAtomic},
		MaxBytes: 2 * 1024 * 1024,
	})
	output := testResult.Output
	exitCode := testResult.ExitCode
	coveragePercent := 0.0

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
					"project_type":       projectType,
					"command":            command,
					"coverage_supported": true,
					"coverage_percent":   coveragePercent,
					"exit_code":          exitCode,
					"output":             output,
				},
				Artifacts: []app.ArtifactPayload{{
					Name:        sweCoverageReportTxt,
					ContentType: sweTextPlain,
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
			"project_type":       projectType,
			"command":            command,
			"coverage_supported": true,
			"coverage_percent":   coveragePercent,
			"exit_code":          exitCode,
			"output":             output,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        sweCoverageReportTxt,
			ContentType: sweTextPlain,
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
			ContentType: sweTextPlain,
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
			Args:     []string{"-p", sweWorkspaceDist},
			MaxBytes: 16 * 1024,
		}); mkdirErr != nil {
			return app.ToolRunResult{}, toToolError(mkdirErr, "failed to create "+sweWorkspaceDist)
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
			ContentType: sweTextPlain,
			Data:        []byte(commandResult.Output),
		}},
	}
	if runErr != nil {
		return result, toToolError(runErr, commandResult.Output)
	}
	return result, nil
}

func (h *SecurityScanDependenciesHandler) Name() string {
	return "security.scan_dependencies"
}

func (h *SecurityScanDependenciesHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path            string `json:"path"`
		MaxDependencies int    `json:"max_dependencies"`
	}{Path: ".", MaxDependencies: 500}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid security.scan_dependencies args",
				Retryable: false,
			}
		}
	}
	request.MaxDependencies = clampInt(request.MaxDependencies, 1, 5000, 500)

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

	runner := ensureRunner(h.runner)
	detected, detectErr := detectProjectTypeForSession(ctx, runner, session)
	if detectErr != nil {
		if errors.Is(detectErr, os.ErrNotExist) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "no supported dependency scanning toolchain found",
				Retryable: false,
			}
		}
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   detectErr.Error(),
			Retryable: false,
		}
	}

	inventory, inventoryErr := collectDependencyInventory(ctx, runner, session, detected, scanPath, request.MaxDependencies)
	if inventoryErr != nil {
		if errors.Is(inventoryErr, os.ErrNotExist) {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "dependency scanning is not supported for detected project type",
				Retryable: false,
			}
		}
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   inventoryErr.Error(),
			Retryable: false,
		}
	}

	dependencyItems := dependencyEntriesToMaps(inventory.Dependencies)
	artifacts := []app.ArtifactPayload{{
		Name:        "dependency-scan-output.txt",
		ContentType: sweTextPlain,
		Data:        []byte(inventory.Output),
	}}
	if inventoryJSON, marshalErr := json.MarshalIndent(map[string]any{
		"project_type": detected.Name,
		"path":         scanPath,
		"dependencies": dependencyItems,
		"truncated":    inventory.Truncated,
	}, "", "  "); marshalErr == nil {
		artifacts = append(artifacts, app.ArtifactPayload{
			Name:        "dependency-inventory.json",
			ContentType: sweApplicationJSON,
			Data:        inventoryJSON,
		})
	}

	result := app.ToolRunResult{
		ExitCode: inventory.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: inventory.Output}},
		Output: map[string]any{
			"project_type":       detected.Name,
			"command":            inventory.Command,
			"dependencies_count": len(dependencyItems),
			"dependencies":       dependencyItems,
			"truncated":          inventory.Truncated,
			"scanner":            "workspace-inventory-v1",
			"exit_code":          inventory.ExitCode,
			"output":             inventory.Output,
		},
		Artifacts: artifacts,
	}
	if inventory.RunErr != nil && len(dependencyItems) == 0 {
		return result, toToolError(inventory.RunErr, inventory.Output)
	}
	return result, nil
}

func (h *SBOMGenerateHandler) Name() string {
	return "sbom.generate"
}

func (h *SBOMGenerateHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path          string `json:"path"`
		Format        string `json:"format"`
		MaxComponents int    `json:"max_components"`
	}{
		Path:          ".",
		Format:        sweCycloneDXJSON,
		MaxComponents: 1000,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid sbom.generate args",
				Retryable: false,
			}
		}
	}

	format := strings.ToLower(strings.TrimSpace(request.Format))
	if format == "" {
		format = sweCycloneDXJSON
	}
	if format != sweCycloneDXJSON {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "format must be cyclonedx-json",
			Retryable: false,
		}
	}
	request.MaxComponents = clampInt(request.MaxComponents, 1, 10000, 1000)

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

	runner := ensureRunner(h.runner)
	detected, detectDomErr := detectProjectTypeOrError(ctx, runner, session, "no supported sbom toolchain found")
	if detectDomErr != nil {
		return app.ToolRunResult{}, detectDomErr
	}

	inventory, inventoryErr := collectDependencyInventory(ctx, runner, session, detected, scanPath, request.MaxComponents)
	if inventoryErr != nil {
		return app.ToolRunResult{}, dependencyInventoryError(inventoryErr, "sbom generation is not supported for detected project type")
	}

	result, buildErr := buildSBOMResult(detected.Name, inventory)
	if buildErr != nil {
		return app.ToolRunResult{}, buildErr
	}
	if inventory.RunErr != nil && len(inventory.Dependencies) == 0 {
		return result, toToolError(inventory.RunErr, inventory.Output)
	}
	return result, nil
}

// detectProjectTypeOrError wraps detectProjectTypeForSession and maps
// os.ErrNotExist to the provided notFoundMsg, so callers avoid repeated
// nested-if patterns.
func detectProjectTypeOrError(ctx context.Context, runner app.CommandRunner, session domain.Session, notFoundMsg string) (projectType, *domain.Error) {
	detected, err := detectProjectTypeForSession(ctx, runner, session)
	if err == nil {
		return detected, nil
	}
	if errors.Is(err, os.ErrNotExist) {
		return projectType{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: notFoundMsg, Retryable: false}
	}
	return projectType{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
}

// dependencyInventoryError maps a raw inventory error to a domain error,
// using notSupportedMsg when the underlying cause is os.ErrNotExist.
func dependencyInventoryError(err error, notSupportedMsg string) *domain.Error {
	if errors.Is(err, os.ErrNotExist) {
		return &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: notSupportedMsg, Retryable: false}
	}
	return &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
}

func buildSBOMResult(projectType string, inventory dependencyInventoryResult) (app.ToolRunResult, *domain.Error) {
	components := buildCycloneDXComponents(inventory.Dependencies)
	sbomDocument := map[string]any{
		"bomFormat":    "CycloneDX",
		"specVersion":  "1.5",
		"version":      1,
		"serialNumber": "",
		"metadata": map[string]any{
			"timestamp": time.Now().UTC().Format(time.RFC3339),
			"tools": []map[string]any{
				{"vendor": "underpass-ai", "name": "workspace", "version": "v1"},
			},
			"component": map[string]any{
				"type": "application",
				"name": "workspace-repo",
			},
		},
		"components": components,
	}
	sbomBytes, marshalErr := json.MarshalIndent(sbomDocument, "", "  ")
	if marshalErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   "failed to encode sbom document",
			Retryable: false,
		}
	}

	preview := components
	if len(preview) > 25 {
		preview = preview[:25]
	}

	return app.ToolRunResult{
		ExitCode: inventory.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: inventory.Output}},
		Output: map[string]any{
			"project_type":     projectType,
			"format":           sweCycloneDXJSON,
			"generator":        "workspace.sbom.generate/v1",
			"command":          inventory.Command,
			"components_count": len(components),
			"components":       preview,
			"truncated":        inventory.Truncated,
			"artifact_name":    "sbom.cdx.json",
			"exit_code":        inventory.ExitCode,
		},
		Artifacts: []app.ArtifactPayload{
			{
				Name:        "sbom.cdx.json",
				ContentType: sweApplicationJSON,
				Data:        sbomBytes,
			},
			{
				Name:        "sbom-generate-output.txt",
				ContentType: sweTextPlain,
				Data:        []byte(inventory.Output),
			},
		},
	}, nil
}

func (h *SecurityScanContainerHandler) Name() string {
	return "security.scan_container"
}

func (h *SecurityScanContainerHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path              string `json:"path"`
		ImageRef          string `json:"image_ref"`
		MaxFindings       int    `json:"max_findings"`
		SeverityThreshold string `json:"severity_threshold"`
	}{
		Path:              ".",
		MaxFindings:       200,
		SeverityThreshold: "medium",
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid security.scan_container args",
				Retryable: false,
			}
		}
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
	maxFindings := clampInt(request.MaxFindings, 1, 2000, 200)
	threshold, thresholdErr := normalizeSeverityThreshold(request.SeverityThreshold)
	if thresholdErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   thresholdErr.Error(),
			Retryable: false,
		}
	}

	runner := ensureRunner(h.runner)
	imageRef := strings.TrimSpace(request.ImageRef)
	target := scanPath

	scanResult, scanDomErr := runContainerScan(ctx, runner, session, scanPath, imageRef, threshold, maxFindings)
	if scanDomErr != nil {
		return app.ToolRunResult{}, scanDomErr
	}
	command := scanResult.command
	commandResult := scanResult.commandResult
	runErr := scanResult.runErr
	findings := scanResult.findings
	truncated := scanResult.truncated
	scanner := scanResult.scanner
	rawOutput := scanResult.rawOutput
	if imageRef != "" {
		target = imageRef
	}

	severityCounts := intMapToAnyMap(countSecurityFindingsBySeverity(findings))
	result := app.ToolRunResult{
		ExitCode: commandResult.ExitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: rawOutput}},
		Output: map[string]any{
			"scanner":            scanner,
			"target":             target,
			"path":               scanPath,
			"image_ref":          imageRef,
			"command":            command,
			"severity_threshold": threshold,
			"findings_count":     len(findings),
			"findings":           findings,
			"severity_counts":    severityCounts,
			"truncated":          truncated,
			"exit_code":          commandResult.ExitCode,
			"output":             rawOutput,
		},
		Artifacts: []app.ArtifactPayload{
			{
				Name:        "container-scan-output.txt",
				ContentType: sweTextPlain,
				Data:        []byte(rawOutput),
			},
		},
	}
	if findingsJSON, marshalErr := json.MarshalIndent(map[string]any{
		"scanner":            scanner,
		"target":             target,
		"severity_threshold": threshold,
		"findings_count":     len(findings),
		"findings":           findings,
		"severity_counts":    severityCounts,
		"truncated":          truncated,
	}, "", "  "); marshalErr == nil {
		result.Artifacts = append(result.Artifacts, app.ArtifactPayload{
			Name:        "container-scan-findings.json",
			ContentType: sweApplicationJSON,
			Data:        findingsJSON,
		})
	}
	if runErr != nil && len(findings) == 0 {
		return result, toToolError(runErr, rawOutput)
	}
	return result, nil
}

type containerScanResult struct {
	command       []string
	commandResult app.CommandResult
	runErr        error
	findings      []map[string]any
	truncated     bool
	scanner       string
	rawOutput     string
}

func runContainerScan(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	scanPath string,
	imageRef string,
	threshold string,
	maxFindings int,
) (containerScanResult, *domain.Error) {
	command, commandResult, runErr := runTrivyScan(ctx, runner, session, scanPath, imageRef, threshold)
	rawOutput := strings.TrimSpace(commandResult.Output)

	findings := []map[string]any{}
	truncated := false
	scanner := sweHeuristicDockerfile
	useHeuristicFallback := runErr != nil

	if !useHeuristicFallback {
		parsed, parsedTruncated, parseErr := parseTrivyFindings(commandResult.Output, threshold, maxFindings)
		if parseErr != nil {
			useHeuristicFallback = true
		} else {
			scanner = "trivy"
			findings = parsed
			truncated = parsedTruncated
		}
	}

	if useHeuristicFallback {
		hResult, hErr := applyHeuristicFallback(ctx, runner, session, scanPath, threshold, maxFindings, rawOutput, command)
		if hErr != nil {
			return containerScanResult{}, hErr
		}
		rawOutput = hResult.rawOutput
		findings = hResult.findings
		truncated = hResult.truncated
		scanner = hResult.scanner
		command = hResult.command
		commandResult.ExitCode = 0
		runErr = nil
	}

	// If Trivy succeeds but produces zero findings on filesystem scans, run
	// Dockerfile heuristics as a deterministic secondary signal.
	if !useHeuristicFallback && imageRef == "" && len(findings) == 0 {
		heuristicFindings, heuristicTruncated, heuristicOutput, heuristicErr := scanContainerHeuristics(
			ctx, runner, session, scanPath, threshold, maxFindings,
		)
		if heuristicErr == nil && len(heuristicFindings) > 0 {
			rawOutput = mergeOutputStrings(rawOutput, heuristicOutput)
			findings = heuristicFindings
			truncated = heuristicTruncated
			scanner = sweHeuristicDockerfile
			command = []string{"heuristic", "dockerfile-scan", scanPath}
		}
	}

	return containerScanResult{
		command:       command,
		commandResult: commandResult,
		runErr:        runErr,
		findings:      findings,
		truncated:     truncated,
		scanner:       scanner,
		rawOutput:     rawOutput,
	}, nil
}

// runTrivyScan executes trivy against either an image reference or a
// filesystem path and returns the command slice, the raw result, and any error.
func runTrivyScan(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	scanPath, imageRef, threshold string,
) ([]string, app.CommandResult, error) {
	trivyArgs := []string{
		"--format", "json",
		"--quiet",
		"--no-progress",
		"--severity", strings.Join(severityListForThreshold(threshold), ","),
	}
	if imageRef != "" {
		command := append([]string{"trivy", "image"}, append(trivyArgs, imageRef)...)
		result, err := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  "trivy",
			Args:     append([]string{"image"}, append(trivyArgs, imageRef)...),
			MaxBytes: 2 * 1024 * 1024,
		})
		return command, result, err
	}
	command := append([]string{"trivy", "fs"}, append(trivyArgs, scanPath)...)
	result, err := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "trivy",
		Args:     append([]string{"fs"}, append(trivyArgs, scanPath)...),
		MaxBytes: 2 * 1024 * 1024,
	})
	return command, result, err
}

type heuristicFallbackResult struct {
	command    []string
	findings   []map[string]any
	truncated  bool
	scanner    string
	rawOutput  string
}

// applyHeuristicFallback runs the Dockerfile heuristic scanner as a fallback
// when Trivy is unavailable or fails to parse its output.
func applyHeuristicFallback(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	scanPath, threshold string,
	maxFindings int,
	existingOutput string,
	existingCommand []string,
) (heuristicFallbackResult, *domain.Error) {
	heuristicFindings, heuristicTruncated, heuristicOutput, heuristicErr := scanContainerHeuristics(
		ctx, runner, session, scanPath, threshold, maxFindings,
	)
	if heuristicErr != nil {
		return heuristicFallbackResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   heuristicErr.Error(),
			Retryable: false,
		}
	}
	cmd := existingCommand
	if len(cmd) == 0 {
		cmd = []string{"heuristic", "dockerfile-scan", scanPath}
	}
	return heuristicFallbackResult{
		command:   cmd,
		findings:  heuristicFindings,
		truncated: heuristicTruncated,
		scanner:   sweHeuristicDockerfile,
		rawOutput: mergeOutputStrings(existingOutput, heuristicOutput),
	}, nil
}

func mergeOutputStrings(existing, addition string) string {
	if strings.TrimSpace(existing) == "" {
		return addition
	}
	return existing + "\n\n" + addition
}

func (h *SecurityLicenseCheckHandler) Name() string {
	return "security.license_check"
}

func (h *SecurityLicenseCheckHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path            string   `json:"path"`
		MaxDependencies int      `json:"max_dependencies"`
		AllowedLicenses []string `json:"allowed_licenses"`
		DeniedLicenses  []string `json:"denied_licenses"`
		UnknownPolicy   string   `json:"unknown_policy"`
	}{
		Path:            ".",
		MaxDependencies: 500,
		UnknownPolicy:   "warn",
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid security.license_check args",
				Retryable: false,
			}
		}
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
	maxDependencies := clampInt(request.MaxDependencies, 1, 5000, 500)
	unknownPolicy := strings.ToLower(strings.TrimSpace(request.UnknownPolicy))
	if unknownPolicy == "" {
		unknownPolicy = "warn"
	}
	if unknownPolicy != "warn" && unknownPolicy != "deny" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "unknown_policy must be warn or deny",
			Retryable: false,
		}
	}
	allowedLicenses := normalizeLicensePolicyTokens(request.AllowedLicenses)
	deniedLicenses := normalizeLicensePolicyTokens(request.DeniedLicenses)

	runner := ensureRunner(h.runner)
	detected, detectDomErr := detectProjectTypeOrError(ctx, runner, session, "no supported license check toolchain found")
	if detectDomErr != nil {
		return app.ToolRunResult{}, detectDomErr
	}

	inventory, inventoryErr := collectDependencyInventory(ctx, runner, session, detected, scanPath, maxDependencies)
	if inventoryErr != nil {
		return app.ToolRunResult{}, dependencyInventoryError(inventoryErr, "license check is not supported for detected project type")
	}

	enrichedEntries, enrichmentCommand, enrichmentOutput, enrichmentErr := enrichDependencyLicenses(
		ctx,
		runner,
		session,
		detected,
		scanPath,
		inventory.Dependencies,
		maxDependencies,
	)
	if enrichmentErr != nil && len(enrichedEntries) == 0 {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   enrichmentErr.Error(),
			Retryable: false,
		}
	}
	if len(enrichedEntries) == 0 {
		enrichedEntries = inventory.Dependencies
	}

	violations, allowedCount, deniedCount, unknownCount := classifyLicenseEntries(enrichedEntries, allowedLicenses, deniedLicenses, unknownPolicy)

	status := "pass"
	exitCode := 0
	if deniedCount > 0 || (unknownPolicy == "deny" && unknownCount > 0) {
		status = "fail"
		exitCode = 1
	} else if unknownCount > 0 {
		status = "warn"
	}

	combinedOutput := strings.TrimSpace(inventory.Output)
	if strings.TrimSpace(enrichmentOutput) != "" {
		if combinedOutput == "" {
			combinedOutput = strings.TrimSpace(enrichmentOutput)
		} else {
			combinedOutput = combinedOutput + "\n\n" + strings.TrimSpace(enrichmentOutput)
		}
	}

	result := app.ToolRunResult{
		ExitCode: exitCode,
		Logs:     []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: combinedOutput}},
		Output: map[string]any{
			"project_type":           detected.Name,
			"command":                inventory.Command,
			"license_source_command": enrichmentCommand,
			"dependencies_checked":   len(enrichedEntries),
			"allowed_count":          allowedCount,
			"denied_count":           deniedCount,
			"unknown_count":          unknownCount,
			"allowed_licenses":       allowedLicenses,
			"denied_licenses":        deniedLicenses,
			"unknown_policy":         unknownPolicy,
			"status":                 status,
			"violations":             violations,
			"dependencies":           dependencyEntriesToMaps(enrichedEntries),
			"truncated":              inventory.Truncated,
			"exit_code":              exitCode,
			"output":                 combinedOutput,
		},
		Artifacts: []app.ArtifactPayload{{
			Name:        "license-check-output.txt",
			ContentType: sweTextPlain,
			Data:        []byte(combinedOutput),
		}},
	}
	if reportBytes, marshalErr := json.MarshalIndent(map[string]any{
		"project_type":         detected.Name,
		"dependencies_checked": len(enrichedEntries),
		"allowed_count":        allowedCount,
		"denied_count":         deniedCount,
		"unknown_count":        unknownCount,
		"status":               status,
		"violations":           violations,
		"dependencies":         dependencyEntriesToMaps(enrichedEntries),
		"truncated":            inventory.Truncated,
	}, "", "  "); marshalErr == nil {
		result.Artifacts = append(result.Artifacts, app.ArtifactPayload{
			Name:        "license-check-report.json",
			ContentType: sweApplicationJSON,
			Data:        reportBytes,
		})
	}

	if inventory.RunErr != nil && len(enrichedEntries) == 0 {
		return result, toToolError(inventory.RunErr, combinedOutput)
	}
	return result, nil
}

func classifyLicenseEntries(
	entries []dependencyEntry,
	allowedLicenses []string,
	deniedLicenses []string,
	unknownPolicy string,
) (violations []map[string]any, allowedCount int, deniedCount int, unknownCount int) {
	violations = make([]map[string]any, 0, 32)
	for _, entry := range entries {
		license := strings.TrimSpace(entry.License)
		if license == "" {
			license = "unknown"
		}
		licenseStatus, reason := evaluateLicenseAgainstPolicy(license, allowedLicenses, deniedLicenses)
		if licenseStatus == "unknown" {
			unknownCount++
			if unknownPolicy == "deny" {
				violations = append(violations, map[string]any{
					"name":      entry.Name,
					"version":   entry.Version,
					"ecosystem": entry.Ecosystem,
					"license":   license,
					"reason":    "unknown license is denied by policy",
				})
			}
			continue
		}
		if licenseStatus == "denied" {
			deniedCount++
			violations = append(violations, map[string]any{
				"name":      entry.Name,
				"version":   entry.Version,
				"ecosystem": entry.Ecosystem,
				"license":   license,
				"reason":    reason,
			})
			continue
		}
		allowedCount++
	}
	return violations, allowedCount, deniedCount, unknownCount
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
		sweRgGlobFlag, "!.git",
		sweRgGlobFlag, "!node_modules",
		sweRgGlobFlag, "!target",
		sweRgGlobFlag, "!.workspace-venv",
		"-m", strconv.Itoa(request.MaxResults),
		"-e", "AKIA[0-9A-Z]{16}",
		"-e", "BEGIN RSA PRIVATE KEY",
		"-e", "BEGIN OPENSSH PRIVATE KEY",
		"-e", `(?i)(api[_-]?key|secret|token)[[:space:]]*[:=][[:space:]]*["'][^"']{12,}["']`,
		scanPath,
	}

	runner := ensureRunner(h.runner)
	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "rg",
		Args:     rgArgs,
		MaxBytes: 2 * 1024 * 1024,
	})
	if isMissingBinaryError(runErr, commandResult, "rg") {
		grepArgs := []string{
			"-RInE",
			"--binary-files=without-match",
			"--exclude-dir=.git",
			"--exclude-dir=node_modules",
			"--exclude-dir=target",
			"--exclude-dir=.workspace-venv",
			"-m", strconv.Itoa(request.MaxResults),
			"-e", "AKIA[0-9A-Z]{16}",
			"-e", "BEGIN RSA PRIVATE KEY",
			"-e", "BEGIN OPENSSH PRIVATE KEY",
			"-e", `([Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Tt][Oo][Kk][Ee][Nn])[[:space:]]*[:=][[:space:]]*["'][^"']{12,}["']`,
			scanPath,
		}
		commandResult, runErr = runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  "grep",
			Args:     grepArgs,
			MaxBytes: 2 * 1024 * 1024,
		})
	}

	// rg/grep exit 1 when there are no matches; that's a successful "clean" scan.
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
				ContentType: sweTextPlain,
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
			ContentType: sweTextPlain,
			Data:        []byte(commandResult.Output),
		}},
	}
	return result, nil
}

func isMissingBinaryError(runErr error, result app.CommandResult, command string) bool {
	if runErr == nil {
		return false
	}
	if result.ExitCode == 127 && strings.Contains(strings.ToLower(result.Output), "not found") {
		return true
	}
	errText := strings.ToLower(runErr.Error())
	return strings.Contains(errText, "not found") && strings.Contains(errText, strings.ToLower(command))
}

func (h *QualityGateHandler) Name() string {
	return "quality.gate"
}

func (h *QualityGateHandler) Invoke(_ context.Context, _ domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := qualityGateRequest{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid quality.gate args",
				Retryable: false,
			}
		}
	}

	metrics := qualityGateMetricsFromMap(request.Metrics)
	config := normalizeQualityGateConfig(request.qualityGateThresholdsRequest)
	rules, passed := evaluateQualityGate(metrics, config)
	failedRules := countFailedQualityRules(rules)
	status := "pass"
	exitCode := 0
	if !passed {
		status = "fail"
		exitCode = 1
	}
	summary := qualityGateSummary(passed, len(rules)-failedRules, len(rules))

	output := map[string]any{
		"status":             status,
		"passed":             passed,
		"failed_rules_count": failedRules,
		"rules":              rules,
		"metrics":            qualityGateMetricsToMap(metrics),
		"thresholds":         qualityGateConfigToMap(config),
		"summary":            summary,
		"output":             summary,
	}

	result := app.ToolRunResult{
		ExitCode:  exitCode,
		Logs:      []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: summary}},
		Output:    output,
		Artifacts: []app.ArtifactPayload{},
	}
	if reportBytes, marshalErr := json.MarshalIndent(output, "", "  "); marshalErr == nil {
		result.Artifacts = append(result.Artifacts, app.ArtifactPayload{
			Name:        "quality-gate-report.json",
			ContentType: sweApplicationJSON,
			Data:        reportBytes,
		})
	}
	return result, nil
}

func (h *CIRunPipelineHandler) Name() string {
	return "ci.run_pipeline"
}

// pipelineState holds the mutable accumulator shared across pipeline steps.
type pipelineState struct {
	runner         app.CommandRunner
	session        domain.Session
	ctx            context.Context
	steps          []map[string]any
	combinedOutput strings.Builder
	failedStep     string
	finalExitCode  int
	finalErr       *domain.Error
	qualityMetrics qualityGateMetrics
}

// runStep executes a single pipeline step, appends its result to the state,
// and returns false when the step failed.
func (ps *pipelineState) runStep(stepName, command string, commandArgs []string) bool {
	result, runErr := ps.runner.Run(ps.ctx, ps.session, app.CommandSpec{
		Cwd:      ps.session.WorkspacePath,
		Command:  command,
		Args:     commandArgs,
		MaxBytes: 2 * 1024 * 1024,
	})
	status := "succeeded"
	if runErr != nil {
		status = "failed"
	}
	if strings.TrimSpace(result.Output) != "" {
		if ps.combinedOutput.Len() > 0 {
			ps.combinedOutput.WriteString("\n")
		}
		ps.combinedOutput.WriteString("[" + stepName + "]\n")
		ps.combinedOutput.WriteString(result.Output)
	}
	ps.steps = append(ps.steps, map[string]any{
		"name":      stepName,
		"status":    status,
		"command":   append([]string{command}, commandArgs...),
		"exit_code": result.ExitCode,
	})
	updatePipelineQualityMetrics(stepName, result.Output, runErr, result.ExitCode, &ps.qualityMetrics)
	if runErr != nil {
		ps.failedStep = stepName
		ps.finalExitCode = result.ExitCode
		ps.finalErr = annotatePipelineStepError(toToolError(runErr, result.Output), stepName)
		return false
	}
	return true
}

func (h *CIRunPipelineHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Target             string                       `json:"target"`
		IncludeStatic      bool                         `json:"include_static_analysis"`
		IncludeCoverage    bool                         `json:"include_coverage"`
		IncludeQualityGate bool                         `json:"include_quality_gate"`
		FailFast           bool                         `json:"fail_fast"`
		QualityGate        qualityGateThresholdsRequest `json:"quality_gate"`
	}{IncludeStatic: true, IncludeCoverage: true, IncludeQualityGate: true, FailFast: true}
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
	detected, detectDomErr := detectProjectTypeOrError(ctx, runner, session, "no supported toolchain found")
	if detectDomErr != nil {
		return app.ToolRunResult{}, detectDomErr
	}

	target := sanitizeTarget(request.Target)
	ps := &pipelineState{
		runner:        runner,
		session:       session,
		ctx:           ctx,
		steps:         make([]map[string]any, 0, 6),
		finalErr:      nil,
	}
	qualityConfig := normalizeQualityGateConfig(request.QualityGate)

	validateCommand, validateArgs, validateErr := validateCommandForProject(session.WorkspacePath, detected, target)
	if validateErr != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: validateErr.Error(), Retryable: false}
	}
	if !ps.runStep("validate", validateCommand, validateArgs) && request.FailFast {
		return ciPipelineResult(detected.Name, ps.steps, ps.failedStep, ps.finalExitCode, ps.combinedOutput.String()), ps.finalErr
	}

	buildCommand, buildArgs, buildErr := buildCommandForProject(session.WorkspacePath, detected, target, nil)
	if buildErr != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: buildErr.Error(), Retryable: false}
	}
	if !ps.runStep("build", buildCommand, buildArgs) && request.FailFast {
		return ciPipelineResult(detected.Name, ps.steps, ps.failedStep, ps.finalExitCode, ps.combinedOutput.String()), ps.finalErr
	}

	testCommand, testArgs, testErr := testCommandForProject(session.WorkspacePath, detected, target, nil)
	if testErr != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: testErr.Error(), Retryable: false}
	}
	if !ps.runStep("test", testCommand, testArgs) && request.FailFast {
		return ciPipelineResult(detected.Name, ps.steps, ps.failedStep, ps.finalExitCode, ps.combinedOutput.String()), ps.finalErr
	}

	if request.IncludeStatic {
		if early, result, err := runPipelineStaticStep(ps, detected, target, request.FailFast); early {
			return result, err
		}
	}

	if request.IncludeCoverage {
		if early, result, err := runPipelineCoverageStep(ctx, ps, runner, session, detected, target, request.FailFast); early {
			return result, err
		}
	}

	var qualityGateOutput map[string]any
	if request.IncludeQualityGate {
		qualityGateOutput = runPipelineQualityGateStep(ps, qualityConfig)
	}

	pipelineResult := ciPipelineResult(detected.Name, ps.steps, ps.failedStep, ps.finalExitCode, ps.combinedOutput.String())
	attachPipelineQualityGateOutput(&pipelineResult, detected.Name, ps.qualityMetrics, qualityGateOutput)

	if ps.failedStep != "" {
		if ps.finalErr == nil {
			ps.finalErr = &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: "pipeline step failed: " + ps.failedStep, Retryable: false}
		}
		return pipelineResult, ps.finalErr
	}
	return pipelineResult, nil
}

// runPipelineStaticStep runs the optional static-analysis step. It returns
// early=true when fail-fast should abort the pipeline.
func runPipelineStaticStep(ps *pipelineState, detected projectType, target string, failFast bool) (bool, app.ToolRunResult, *domain.Error) {
	staticCommand, staticArgs, staticErr := staticAnalysisCommandForProject(ps.session.WorkspacePath, detected, target)
	if staticErr != nil {
		ps.steps = append(ps.steps, map[string]any{"name": "static_analysis", "status": "skipped", "command": []string{}, "exit_code": 0})
		return false, app.ToolRunResult{}, nil
	}
	if !ps.runStep("static_analysis", staticCommand, staticArgs) && failFast {
		return true, ciPipelineResult(detected.Name, ps.steps, ps.failedStep, ps.finalExitCode, ps.combinedOutput.String()), ps.finalErr
	}
	return false, app.ToolRunResult{}, nil
}

// runPipelineCoverageStep runs the optional coverage step. It returns
// early=true when fail-fast should abort the pipeline.
func runPipelineCoverageStep(ctx context.Context, ps *pipelineState, runner app.CommandRunner, session domain.Session, detected projectType, target string, failFast bool) (bool, app.ToolRunResult, *domain.Error) {
	if detected.Name != "go" {
		ps.steps = append(ps.steps, map[string]any{"name": "coverage", "status": "skipped", "command": []string{}, "exit_code": 0})
		return false, app.ToolRunResult{}, nil
	}
	coverageFile := ".workspace.cover.out"
	if !ps.runStep("coverage", "go", []string{"test", targetOrDefault(target, "./..."), sweCoverProfile, coverageFile, sweCoverModeAtomic}) && failFast {
		return true, ciPipelineResult(detected.Name, ps.steps, ps.failedStep, ps.finalExitCode, ps.combinedOutput.String()), ps.finalErr
	}
	_, _ = runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "rm",
		Args:     []string{"-f", coverageFile},
		MaxBytes: 16 * 1024,
	})
	return false, app.ToolRunResult{}, nil
}

// runPipelineQualityGateStep evaluates the quality gate, appends its step to
// ps, and returns the gate output map (or nil when the gate passes).
func runPipelineQualityGateStep(ps *pipelineState, qualityConfig qualityGateConfig) map[string]any {
	rules, passed := evaluateQualityGate(ps.qualityMetrics, qualityConfig)
	failedRules := countFailedQualityRules(rules)
	gateStatus := "succeeded"
	gateExitCode := 0
	if !passed {
		gateStatus = "failed"
		gateExitCode = 1
	}
	qualityGateOutput := map[string]any{
		"status":             ternaryQualityGateStatus(passed),
		"passed":             passed,
		"failed_rules_count": failedRules,
		"rules":              rules,
		"thresholds":         qualityGateConfigToMap(qualityConfig),
		"summary":            qualityGateSummary(passed, len(rules)-failedRules, len(rules)),
	}
	ps.steps = append(ps.steps, map[string]any{
		"name":         "quality_gate",
		"status":       gateStatus,
		"command":      []string{"quality.gate"},
		"exit_code":    gateExitCode,
		"failed_rules": failedRules,
	})
	if !passed && ps.failedStep == "" {
		ps.failedStep = "quality_gate"
		ps.finalExitCode = 1
		ps.finalErr = &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: "pipeline quality gate failed", Retryable: false}
	}
	return qualityGateOutput
}

// attachPipelineQualityGateOutput merges quality-gate data into pipelineResult.
func attachPipelineQualityGateOutput(pipelineResult *app.ToolRunResult, projectType string, metrics qualityGateMetrics, qualityGateOutput map[string]any) {
	if outputMap, ok := pipelineResult.Output.(map[string]any); ok {
		outputMap["quality_metrics"] = qualityGateMetricsToMap(metrics)
		if qualityGateOutput != nil {
			outputMap["quality_gate"] = qualityGateOutput
		}
	}
	if qualityGateOutput == nil {
		return
	}
	if reportBytes, marshalErr := json.MarshalIndent(map[string]any{
		"project_type":    projectType,
		"quality_metrics": qualityGateMetricsToMap(metrics),
		"quality_gate":    qualityGateOutput,
	}, "", "  "); marshalErr == nil {
		pipelineResult.Artifacts = append(pipelineResult.Artifacts, app.ArtifactPayload{
			Name:        "quality-gate-report.json",
			ContentType: sweApplicationJSON,
			Data:        reportBytes,
		})
	}
}

func updatePipelineQualityMetrics(stepName, output string, runErr error, exitCode int, metrics *qualityGateMetrics) {
	switch stepName {
	case "test":
		if runErr != nil || exitCode != 0 {
			failedTests := summarizeTestFailures(output, 200)
			if len(failedTests) == 0 {
				metrics.FailedTestsCount = 1
			} else {
				metrics.FailedTestsCount = len(failedTests)
			}
		} else {
			metrics.FailedTestsCount = 0
		}
	case "static_analysis":
		metrics.DiagnosticsCount = len(extractDiagnostics(output, 200))
	case "coverage":
		if parsed := parseCoveragePercent(output); parsed != nil {
			metrics.CoveragePercent = *parsed
		}
	}
}

func annotatePipelineStepError(err *domain.Error, stepName string) *domain.Error {
	if err == nil {
		return nil
	}
	if err.Code == app.ErrorCodeTimeout {
		err.Message = "pipeline step timed out: " + stepName
	} else if err.Code == app.ErrorCodeExecutionFailed {
		err.Message = "pipeline step failed: " + stepName
	}
	return err
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
			ContentType: sweTextPlain,
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
		args := []string{"build", "-o", sweWorkspaceDist + "/app"}
		args = append(args, targetOrDefault(target, "."))
		return "go", args, sweWorkspaceDist + "/app", true, nil
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
		return pythonExecutable, []string{"-m", "pip", "wheel", ".", "-w", sweWorkspaceDist}, sweWorkspaceDist, true, nil
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
		return "cc", []string{"-std=c11", "-O2", "-Wall", "-Wextra", "-o", sweWorkspaceDist + "/c-app", source}, sweWorkspaceDist + "/c-app", true, nil
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

func qualityGateMetricsFromMap(raw map[string]any) qualityGateMetrics {
	if len(raw) == 0 {
		return qualityGateMetrics{}
	}
	metrics := qualityGateMetrics{
		CoveragePercent:      floatFromAny(raw["coverage_percent"]),
		DiagnosticsCount:     intFromAny(raw["diagnostics_count"]),
		VulnerabilitiesCount: intFromAny(raw["vulnerabilities_count"]),
		DeniedLicensesCount:  intFromAny(raw["denied_licenses_count"]),
		FailedTestsCount:     intFromAny(raw["failed_tests_count"]),
	}
	if metrics.VulnerabilitiesCount == 0 {
		metrics.VulnerabilitiesCount = intFromAny(raw["vulns_count"])
	}
	if metrics.DeniedLicensesCount == 0 {
		metrics.DeniedLicensesCount = intFromAny(raw["denied_count"])
	}
	return metrics
}

func normalizeQualityGateConfig(request qualityGateThresholdsRequest) qualityGateConfig {
	config := qualityGateConfig{
		MinCoveragePercent: -1,
		MaxDiagnostics:     -1,
		MaxVulnerabilities: -1,
		MaxDeniedLicenses:  -1,
		MaxFailedTests:     0,
	}
	if request.MinCoveragePercent != nil {
		value := *request.MinCoveragePercent
		switch {
		case value < 0:
			config.MinCoveragePercent = -1
		case value > 100:
			config.MinCoveragePercent = 100
		default:
			config.MinCoveragePercent = value
		}
	}
	if request.MaxDiagnostics != nil {
		config.MaxDiagnostics = clampMaxThreshold(*request.MaxDiagnostics)
	}
	if request.MaxVulnerabilities != nil {
		config.MaxVulnerabilities = clampMaxThreshold(*request.MaxVulnerabilities)
	}
	if request.MaxDeniedLicenses != nil {
		config.MaxDeniedLicenses = clampMaxThreshold(*request.MaxDeniedLicenses)
	}
	if request.MaxFailedTests != nil {
		config.MaxFailedTests = clampMaxThreshold(*request.MaxFailedTests)
	}
	return config
}

func clampMaxThreshold(value int) int {
	if value < 0 {
		return -1
	}
	if value > 100000 {
		return 100000
	}
	return value
}

func evaluateQualityGate(metrics qualityGateMetrics, config qualityGateConfig) ([]qualityGateRule, bool) {
	rules := make([]qualityGateRule, 0, 5)

	if config.MinCoveragePercent >= 0 {
		passed := metrics.CoveragePercent >= config.MinCoveragePercent
		rules = append(rules, qualityGateRule{
			Name:     "coverage_percent",
			Operator: ">=",
			Expected: config.MinCoveragePercent,
			Actual:   metrics.CoveragePercent,
			Passed:   passed,
			Message:  fmt.Sprintf("coverage %.2f%% >= %.2f%%", metrics.CoveragePercent, config.MinCoveragePercent),
		})
	}

	appendMaxRule := func(name string, actual int, max int) {
		if max < 0 {
			return
		}
		passed := actual <= max
		rules = append(rules, qualityGateRule{
			Name:     name,
			Operator: "<=",
			Expected: float64(max),
			Actual:   float64(actual),
			Passed:   passed,
			Message:  fmt.Sprintf("%s %d <= %d", name, actual, max),
		})
	}

	appendMaxRule("diagnostics_count", metrics.DiagnosticsCount, config.MaxDiagnostics)
	appendMaxRule("vulnerabilities_count", metrics.VulnerabilitiesCount, config.MaxVulnerabilities)
	appendMaxRule("denied_licenses_count", metrics.DeniedLicensesCount, config.MaxDeniedLicenses)
	appendMaxRule("failed_tests_count", metrics.FailedTestsCount, config.MaxFailedTests)

	passed := true
	for _, rule := range rules {
		if !rule.Passed {
			passed = false
			break
		}
	}
	return rules, passed
}

func countFailedQualityRules(rules []qualityGateRule) int {
	failed := 0
	for _, rule := range rules {
		if !rule.Passed {
			failed++
		}
	}
	return failed
}

func qualityGateSummary(passed bool, passedRules int, totalRules int) string {
	if totalRules <= 0 {
		if passed {
			return "quality gate passed (no active rules)"
		}
		return "quality gate failed (no active rules)"
	}
	if passed {
		return fmt.Sprintf("quality gate passed (%d/%d rules)", passedRules, totalRules)
	}
	return fmt.Sprintf("quality gate failed (%d/%d rules)", passedRules, totalRules)
}

func qualityGateConfigToMap(config qualityGateConfig) map[string]any {
	return map[string]any{
		"min_coverage_percent": config.MinCoveragePercent,
		"max_diagnostics":      config.MaxDiagnostics,
		"max_vulnerabilities":  config.MaxVulnerabilities,
		"max_denied_licenses":  config.MaxDeniedLicenses,
		"max_failed_tests":     config.MaxFailedTests,
	}
}

func qualityGateMetricsToMap(metrics qualityGateMetrics) map[string]any {
	return map[string]any{
		"coverage_percent":      metrics.CoveragePercent,
		"diagnostics_count":     metrics.DiagnosticsCount,
		"vulnerabilities_count": metrics.VulnerabilitiesCount,
		"denied_licenses_count": metrics.DeniedLicensesCount,
		"failed_tests_count":    metrics.FailedTestsCount,
	}
}

func ternaryQualityGateStatus(passed bool) string {
	if passed {
		return "pass"
	}
	return "fail"
}

func intFromAny(value any) int {
	switch typed := value.(type) {
	case int:
		return typed
	case int8:
		return int(typed)
	case int16:
		return int(typed)
	case int32:
		return int(typed)
	case int64:
		return int(typed)
	case uint:
		return int(typed)
	case uint8:
		return int(typed)
	case uint16:
		return int(typed)
	case uint32:
		return int(typed)
	case uint64:
		return int(typed)
	case float32:
		return int(typed)
	case float64:
		return int(typed)
	case json.Number:
		if parsed, err := typed.Int64(); err == nil {
			return int(parsed)
		}
		if parsed, err := typed.Float64(); err == nil {
			return int(parsed)
		}
	case string:
		if parsed, err := strconv.Atoi(strings.TrimSpace(typed)); err == nil {
			return parsed
		}
	}
	return 0
}

func floatFromAny(value any) float64 {
	switch typed := value.(type) {
	case float32:
		return float64(typed)
	case float64:
		return typed
	case int:
		return float64(typed)
	case int8:
		return float64(typed)
	case int16:
		return float64(typed)
	case int32:
		return float64(typed)
	case int64:
		return float64(typed)
	case uint:
		return float64(typed)
	case uint8:
		return float64(typed)
	case uint16:
		return float64(typed)
	case uint32:
		return float64(typed)
	case uint64:
		return float64(typed)
	case json.Number:
		if parsed, err := typed.Float64(); err == nil {
			return parsed
		}
	case string:
		if parsed, err := strconv.ParseFloat(strings.TrimSpace(typed), 64); err == nil {
			return parsed
		}
	}
	return 0
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

type dependencyEntry struct {
	Name      string
	Version   string
	Ecosystem string
	License   string
}

type dependencyInventoryResult struct {
	Command      []string
	ExitCode     int
	Output       string
	Dependencies []dependencyEntry
	Truncated    bool
	RunErr       error
}

func collectDependencyInventory(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	detected projectType,
	scanPath string,
	maxDependencies int,
) (dependencyInventoryResult, error) {
	cwd := session.WorkspacePath
	if scanPath != "" && scanPath != "." {
		cwd = filepath.Join(session.WorkspacePath, filepath.FromSlash(scanPath))
	}

	var command string
	var commandArgs []string
	var parser func(string, int) ([]dependencyEntry, bool, error)

	switch detected.Name {
	case "go":
		command = "go"
		commandArgs = []string{"list", "-m", "all"}
		parser = parseGoDependencyInventory
	case "node":
		command = "npm"
		commandArgs = []string{"ls", "--json", "--all"}
		parser = parseNodeDependencyInventory
	case "python":
		pythonExecutable := resolvePythonExecutable(session.WorkspacePath)
		command = pythonExecutable
		commandArgs = []string{"-m", "pip", "list", "--format=json"}
		parser = parsePythonDependencyInventory
	case "rust":
		command = "cargo"
		commandArgs = []string{"tree", "--prefix", "none"}
		parser = parseRustDependencyInventory
	case "java":
		if detected.Flavor == "gradle" {
			command = "gradle"
			commandArgs = []string{"dependencies", "--configuration", "runtimeClasspath"}
			parser = parseGradleDependencyInventory
		} else {
			command = "mvn"
			commandArgs = []string{"-q", "dependency:list", "-DincludeScope=runtime", "-DoutputAbsoluteArtifactFilename=false"}
			parser = parseMavenDependencyInventory
		}
	default:
		return dependencyInventoryResult{}, os.ErrNotExist
	}

	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      cwd,
		Command:  command,
		Args:     commandArgs,
		MaxBytes: 2 * 1024 * 1024,
	})

	dependencies, truncated, parseErr := parser(commandResult.Output, maxDependencies)
	if parseErr != nil && runErr == nil {
		return dependencyInventoryResult{}, parseErr
	}
	if parseErr != nil && runErr != nil {
		dependencies = nil
		truncated = false
	}

	sort.Slice(dependencies, func(i, j int) bool {
		left := dependencies[i]
		right := dependencies[j]
		if left.Ecosystem != right.Ecosystem {
			return left.Ecosystem < right.Ecosystem
		}
		if left.Name != right.Name {
			return left.Name < right.Name
		}
		return left.Version < right.Version
	})

	return dependencyInventoryResult{
		Command:      append([]string{command}, commandArgs...),
		ExitCode:     commandResult.ExitCode,
		Output:       commandResult.Output,
		Dependencies: dependencies,
		Truncated:    truncated,
		RunErr:       runErr,
	}, nil
}

func parseGoDependencyInventory(output string, maxDependencies int) ([]dependencyEntry, bool, error) {
	lines := splitOutputLines(output)
	out := make([]dependencyEntry, 0, minInt(len(lines), maxDependencies))
	seen := map[string]struct{}{}
	truncated := false
	for _, line := range lines {
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		name := strings.TrimSpace(fields[0])
		if name == "" {
			continue
		}

		version := "unknown"
		for _, token := range fields[1:] {
			token = strings.TrimSpace(token)
			if strings.HasPrefix(token, "v") {
				version = strings.TrimPrefix(token, "v")
				break
			}
		}

		key := "go|" + name + "|" + version
		if _, exists := seen[key]; exists {
			continue
		}
		if len(out) >= maxDependencies {
			truncated = true
			break
		}
		seen[key] = struct{}{}
		out = append(out, dependencyEntry{Name: name, Version: version, Ecosystem: "go", License: "unknown"})
	}
	return out, truncated, nil
}

func parsePythonDependencyInventory(output string, maxDependencies int) ([]dependencyEntry, bool, error) {
	var payload []map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		return nil, false, err
	}

	out := make([]dependencyEntry, 0, minInt(len(payload), maxDependencies))
	seen := map[string]struct{}{}
	truncated := false
	for _, item := range payload {
		name, _ := item["name"].(string)
		version, _ := item["version"].(string)
		name = strings.TrimSpace(name)
		version = strings.TrimSpace(version)
		if name == "" {
			continue
		}
		if version == "" {
			version = "unknown"
		}
		key := "python|" + strings.ToLower(name) + "|" + version
		if _, exists := seen[key]; exists {
			continue
		}
		if len(out) >= maxDependencies {
			truncated = true
			break
		}
		seen[key] = struct{}{}
		out = append(out, dependencyEntry{Name: name, Version: version, Ecosystem: "python", License: "unknown"})
	}
	return out, truncated, nil
}

func parseNodeDependencyInventory(output string, maxDependencies int) ([]dependencyEntry, bool, error) {
	var payload map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		return nil, false, err
	}

	rootDependencies, _ := payload["dependencies"].(map[string]any)
	out := make([]dependencyEntry, 0, minInt(len(rootDependencies), maxDependencies))
	seen := map[string]struct{}{}
	truncated := false
	walkNodeDependencies(rootDependencies, maxDependencies, seen, &out, &truncated)
	return out, truncated, nil
}

func walkNodeDependencies(
	tree map[string]any,
	maxDependencies int,
	seen map[string]struct{},
	out *[]dependencyEntry,
	truncated *bool,
) {
	if tree == nil || *truncated {
		return
	}

	names := make([]string, 0, len(tree))
	for name := range tree {
		names = append(names, name)
	}
	sort.Strings(names)

	for _, name := range names {
		if len(*out) >= maxDependencies {
			*truncated = true
			return
		}
		node, ok := extractNodePackageNode(tree, name)
		if !ok {
			continue
		}
		appendNodeDependencyEntry(name, node, seen, out)

		children, _ := node["dependencies"].(map[string]any)
		walkNodeDependencies(children, maxDependencies, seen, out, truncated)
		if *truncated {
			return
		}
	}
}

func extractNodePackageNode(tree map[string]any, name string) (map[string]any, bool) {
	rawNode, ok := tree[name]
	if !ok {
		return nil, false
	}
	node, ok := rawNode.(map[string]any)
	return node, ok
}

func appendNodeDependencyEntry(name string, node map[string]any, seen map[string]struct{}, out *[]dependencyEntry) {
	version, _ := node["version"].(string)
	version = strings.TrimSpace(version)
	if version == "" {
		version = "unknown"
	}
	key := "node|" + name + "|" + version
	if _, exists := seen[key]; exists {
		return
	}
	seen[key] = struct{}{}
	license := normalizeFoundLicense(nodeStringOrList(node["license"]))
	if license == "" {
		license = "unknown"
	}
	*out = append(*out, dependencyEntry{Name: name, Version: version, Ecosystem: "node", License: license})
}

func parseRustDependencyInventory(output string, maxDependencies int) ([]dependencyEntry, bool, error) {
	lines := splitOutputLines(output)
	out := make([]dependencyEntry, 0, minInt(len(lines), maxDependencies))
	seen := map[string]struct{}{}
	truncated := false
	for _, line := range lines {
		clean := strings.TrimLeft(line, " │├└─`+\\")
		fields := strings.Fields(clean)
		if len(fields) < 2 {
			continue
		}

		name := strings.TrimSpace(fields[0])
		version := strings.TrimSpace(fields[1])
		if strings.HasPrefix(version, "v") {
			version = strings.TrimPrefix(version, "v")
		}
		version = strings.TrimSpace(strings.TrimSuffix(version, ","))
		if name == "" || version == "" {
			continue
		}

		key := "rust|" + name + "|" + version
		if _, exists := seen[key]; exists {
			continue
		}
		if len(out) >= maxDependencies {
			truncated = true
			break
		}
		seen[key] = struct{}{}
		out = append(out, dependencyEntry{Name: name, Version: version, Ecosystem: "rust", License: "unknown"})
	}
	return out, truncated, nil
}

func parseMavenDependencyInventory(output string, maxDependencies int) ([]dependencyEntry, bool, error) {
	lines := splitOutputLines(output)
	out := make([]dependencyEntry, 0, minInt(len(lines), maxDependencies))
	seen := map[string]struct{}{}
	truncated := false
	for _, line := range lines {
		clean := strings.TrimSpace(strings.TrimPrefix(line, "[INFO]"))
		if clean == "" || !strings.Contains(clean, ":") {
			continue
		}

		parts := strings.Split(clean, ":")
		if len(parts) < 4 {
			continue
		}
		group := strings.TrimSpace(parts[0])
		artifact := strings.TrimSpace(parts[1])
		version := strings.TrimSpace(parts[3])
		if group == "" || artifact == "" || version == "" {
			continue
		}
		if strings.Contains(group, " ") {
			continue
		}

		name := group + ":" + artifact
		key := "java|" + name + "|" + version
		if _, exists := seen[key]; exists {
			continue
		}
		if len(out) >= maxDependencies {
			truncated = true
			break
		}
		seen[key] = struct{}{}
		out = append(out, dependencyEntry{Name: name, Version: version, Ecosystem: "java", License: "unknown"})
	}
	return out, truncated, nil
}

func parseGradleDependencyInventory(output string, maxDependencies int) ([]dependencyEntry, bool, error) {
	lines := splitOutputLines(output)
	out := make([]dependencyEntry, 0, minInt(len(lines), maxDependencies))
	seen := map[string]struct{}{}
	truncated := false
	for _, line := range lines {
		name, version, ok := parseGradleCoordinate(line)
		if !ok {
			continue
		}
		key := "java|" + name + "|" + version
		if _, exists := seen[key]; exists {
			continue
		}
		if len(out) >= maxDependencies {
			truncated = true
			break
		}
		seen[key] = struct{}{}
		out = append(out, dependencyEntry{Name: name, Version: version, Ecosystem: "java", License: "unknown"})
	}
	return out, truncated, nil
}

func parseGradleCoordinate(line string) (name, version string, ok bool) {
	clean := strings.TrimSpace(strings.TrimLeft(line, "+\\|`- "))
	if clean == "" {
		return "", "", false
	}
	parts := strings.Fields(clean)
	if len(parts) == 0 {
		return "", "", false
	}
	coordinate := strings.TrimSpace(parts[0])
	if strings.Count(coordinate, ":") < 2 {
		return "", "", false
	}
	segments := strings.Split(coordinate, ":")
	if len(segments) < 3 {
		return "", "", false
	}
	group := strings.TrimSpace(segments[0])
	artifact := strings.TrimSpace(segments[1])
	version = strings.TrimSpace(segments[2])
	if idx := strings.Index(version, "->"); idx >= 0 {
		version = strings.TrimSpace(version[idx+2:])
	}
	version = strings.TrimSpace(strings.TrimSuffix(version, "(*)"))
	if group == "" || artifact == "" || version == "" {
		return "", "", false
	}
	return group + ":" + artifact, version, true
}

func dependencyEntriesToMaps(entries []dependencyEntry) []map[string]any {
	out := make([]map[string]any, 0, len(entries))
	for _, entry := range entries {
		out = append(out, map[string]any{
			"name":      entry.Name,
			"version":   entry.Version,
			"ecosystem": entry.Ecosystem,
			"license":   nonEmptyOrDefault(strings.TrimSpace(entry.License), "unknown"),
		})
	}
	return out
}

func buildCycloneDXComponents(entries []dependencyEntry) []map[string]any {
	components := make([]map[string]any, 0, len(entries))
	for _, entry := range entries {
		components = append(components, map[string]any{
			"type":    "library",
			"name":    entry.Name,
			"version": entry.Version,
			"purl":    dependencyPURL(entry),
		})
	}
	return components
}

func dependencyPURL(entry dependencyEntry) string {
	name := strings.TrimSpace(entry.Name)
	version := strings.TrimSpace(entry.Version)
	if version == "" {
		version = "unknown"
	}

	switch entry.Ecosystem {
	case "go":
		return "pkg:golang/" + name + "@" + version
	case "node":
		return "pkg:npm/" + name + "@" + version
	case "python":
		return "pkg:pypi/" + strings.ToLower(name) + "@" + version
	case "rust":
		return "pkg:cargo/" + name + "@" + version
	case "java":
		parts := strings.SplitN(name, ":", 2)
		if len(parts) == 2 {
			return "pkg:maven/" + parts[0] + "/" + parts[1] + "@" + version
		}
		return "pkg:maven/" + name + "@" + version
	default:
		return "pkg:generic/" + name + "@" + version
	}
}

func normalizeSeverityThreshold(raw string) (string, error) {
	threshold := strings.ToLower(strings.TrimSpace(raw))
	switch threshold {
	case "", "medium", "moderate":
		return "medium", nil
	case "low":
		return "low", nil
	case "high":
		return "high", nil
	case "critical":
		return "critical", nil
	default:
		return "", errors.New("severity_threshold must be one of: low, medium, high, critical")
	}
}

func severityListForThreshold(threshold string) []string {
	switch normalizeFindingSeverity(threshold) {
	case "critical":
		return []string{"CRITICAL"}
	case "high":
		return []string{"CRITICAL", "HIGH"}
	case "medium":
		return []string{"CRITICAL", "HIGH", "MEDIUM"}
	default:
		return []string{"CRITICAL", "HIGH", "MEDIUM", "LOW"}
	}
}

type trivyVulnerability struct {
	VulnerabilityID  string `json:"VulnerabilityID"`
	PkgName          string `json:"PkgName"`
	InstalledVersion string `json:"InstalledVersion"`
	FixedVersion     string `json:"FixedVersion"`
	Severity         string `json:"Severity"`
	Title            string `json:"Title"`
	Description      string `json:"Description"`
	PrimaryURL       string `json:"PrimaryURL"`
}

type trivyMisconfiguration struct {
	ID          string `json:"ID"`
	AVDID       string `json:"AVDID"`
	Type        string `json:"Type"`
	Title       string `json:"Title"`
	Description string `json:"Description"`
	Message     string `json:"Message"`
	Resolution  string `json:"Resolution"`
	Severity    string `json:"Severity"`
}

type trivySecret struct {
	RuleID    string `json:"RuleID"`
	Category  string `json:"Category"`
	Title     string `json:"Title"`
	Severity  string `json:"Severity"`
	StartLine int    `json:"StartLine"`
	Match     string `json:"Match"`
}

type trivyResult struct {
	Target            string                  `json:"Target"`
	Class             string                  `json:"Class"`
	Type              string                  `json:"Type"`
	Vulnerabilities   []trivyVulnerability    `json:"Vulnerabilities"`
	Misconfigurations []trivyMisconfiguration `json:"Misconfigurations"`
	Secrets           []trivySecret           `json:"Secrets"`
}

type trivyReport struct {
	Results []trivyResult `json:"Results"`
}

func parseTrivyFindings(output, threshold string, maxFindings int) ([]map[string]any, bool, error) {
	trimmed := strings.TrimSpace(output)
	if trimmed == "" {
		return nil, false, errors.New("empty trivy output")
	}

	report := trivyReport{}
	if err := json.Unmarshal([]byte(trimmed), &report); err != nil {
		var rawResults []trivyResult
		if errAlt := json.Unmarshal([]byte(trimmed), &rawResults); errAlt != nil {
			return nil, false, err
		}
		report.Results = rawResults
	}

	findings := make([]map[string]any, 0, minInt(maxFindings, 256))
	for _, result := range report.Results {
		target := strings.TrimSpace(result.Target)
		if target == "" {
			target = "unknown"
		}
		findings = appendTrivyResultFindings(findings, result, target, threshold)
	}

	sort.Slice(findings, func(i, j int) bool {
		left := findings[i]
		right := findings[j]
		leftRank := securitySeverityRank(normalizeFindingSeverity(asString(left["severity"])))
		rightRank := securitySeverityRank(normalizeFindingSeverity(asString(right["severity"])))
		if leftRank != rightRank {
			return leftRank > rightRank
		}
		leftTarget := asString(left["target"])
		rightTarget := asString(right["target"])
		if leftTarget != rightTarget {
			return leftTarget < rightTarget
		}
		leftID := asString(left["id"])
		rightID := asString(right["id"])
		if leftID != rightID {
			return leftID < rightID
		}
		return asString(left["kind"]) < asString(right["kind"])
	})

	truncated := false
	if len(findings) > maxFindings {
		findings = findings[:maxFindings]
		truncated = true
	}
	return findings, truncated, nil
}

func appendTrivyResultFindings(findings []map[string]any, result trivyResult, target, threshold string) []map[string]any {
	for _, vulnerability := range result.Vulnerabilities {
		severity := normalizeFindingSeverity(vulnerability.Severity)
		if !severityAtOrAbove(severity, threshold) {
			continue
		}
		id := nonEmptyOrDefault(strings.TrimSpace(vulnerability.VulnerabilityID), "unknown")
		findings = append(findings, map[string]any{
			"kind":              "vulnerability",
			"id":                id,
			"title":             nonEmptyOrDefault(strings.TrimSpace(vulnerability.Title), id),
			"severity":          severity,
			"target":            target,
			"package":           strings.TrimSpace(vulnerability.PkgName),
			"installed_version": nonEmptyOrDefault(strings.TrimSpace(vulnerability.InstalledVersion), "unknown"),
			"fixed_version":     nonEmptyOrDefault(strings.TrimSpace(vulnerability.FixedVersion), "unknown"),
			"description":       truncateString(strings.TrimSpace(vulnerability.Description), 400),
			"primary_url":       strings.TrimSpace(vulnerability.PrimaryURL),
		})
	}

	for _, misconfiguration := range result.Misconfigurations {
		severity := normalizeFindingSeverity(misconfiguration.Severity)
		if !severityAtOrAbove(severity, threshold) {
			continue
		}
		id := strings.TrimSpace(misconfiguration.ID)
		if id == "" {
			id = nonEmptyOrDefault(strings.TrimSpace(misconfiguration.AVDID), "unknown")
		}
		findings = append(findings, map[string]any{
			"kind":        "misconfiguration",
			"id":          id,
			"title":       nonEmptyOrDefault(strings.TrimSpace(misconfiguration.Title), id),
			"severity":    severity,
			"target":      target,
			"type":        strings.TrimSpace(misconfiguration.Type),
			"description": truncateString(strings.TrimSpace(misconfiguration.Description), 400),
			"message":     truncateString(strings.TrimSpace(misconfiguration.Message), 240),
			"resolution":  truncateString(strings.TrimSpace(misconfiguration.Resolution), 240),
		})
	}

	for _, secret := range result.Secrets {
		severity := normalizeFindingSeverity(secret.Severity)
		if !severityAtOrAbove(severity, threshold) {
			continue
		}
		id := nonEmptyOrDefault(strings.TrimSpace(secret.RuleID), "unknown")
		findings = append(findings, map[string]any{
			"kind":     "secret",
			"id":       id,
			"title":    nonEmptyOrDefault(strings.TrimSpace(secret.Title), id),
			"severity": severity,
			"target":   target,
			"category": strings.TrimSpace(secret.Category),
			"line":     secret.StartLine,
			"match":    truncateString(strings.TrimSpace(secret.Match), 180),
		})
	}
	return findings
}

func scanContainerHeuristics(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	scanPath string,
	threshold string,
	maxFindings int,
) ([]map[string]any, bool, string, error) {
	findResult, findErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "find",
		Args:     []string{scanPath, "-type", "f"},
		MaxBytes: 512 * 1024,
	})
	if findErr != nil {
		return nil, false, "", findErr
	}

	dockerfiles := make([]string, 0, 8)
	for _, candidate := range splitOutputLines(findResult.Output) {
		clean := strings.TrimSpace(candidate)
		if clean == "" {
			continue
		}
		if strings.Contains(clean, "/.git/") || strings.Contains(clean, "/node_modules/") || strings.Contains(clean, "/vendor/") || strings.Contains(clean, "/target/") || strings.Contains(clean, "/.workspace-venv/") {
			continue
		}
		if isDockerfileCandidate(filepath.Base(clean)) {
			dockerfiles = append(dockerfiles, clean)
		}
	}
	sort.Strings(dockerfiles)

	findings := make([]map[string]any, 0, minInt(maxFindings, 64))
	truncated := false
	for _, dockerfilePath := range dockerfiles {
		contentResult, contentErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  "cat",
			Args:     []string{dockerfilePath},
			MaxBytes: 512 * 1024,
		})
		if contentErr != nil {
			continue
		}
		findings, truncated = scanDockerfileContent(findings, contentResult.Output, dockerfilePath, threshold, maxFindings)
		if truncated {
			break
		}
	}

	outputLines := []string{
		"heuristic container scan fallback executed",
		"scanner=heuristic-dockerfile",
		"dockerfiles_scanned=" + strconv.Itoa(len(dockerfiles)),
		"findings_count=" + strconv.Itoa(len(findings)),
		"truncated=" + strconv.FormatBool(truncated),
	}
	if len(dockerfiles) == 0 {
		outputLines = append(outputLines, "note=no Dockerfile found under requested path")
	}
	return findings, truncated, strings.Join(outputLines, "\n"), nil
}

func scanDockerfileContent(
	findings []map[string]any,
	content string,
	dockerfilePath string,
	threshold string,
	maxFindings int,
) ([]map[string]any, bool) {
	hasUser := false
	for index, rawLine := range strings.Split(content, "\n") {
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		lower := strings.ToLower(line)
		if strings.HasPrefix(lower, "user ") {
			hasUser = true
		}
		ruleID, severity, message := dockerfileHeuristicRule(lower)
		if ruleID == "" || !severityAtOrAbove(severity, threshold) {
			continue
		}
		findings = append(findings, map[string]any{
			"kind":     "misconfiguration",
			"id":       ruleID,
			"title":    message,
			"severity": severity,
			"target":   filepath.ToSlash(dockerfilePath),
			"line":     index + 1,
		})
		if len(findings) >= maxFindings {
			return findings, true
		}
	}
	if !hasUser && severityAtOrAbove("medium", threshold) {
		findings = append(findings, map[string]any{
			"kind":     "misconfiguration",
			"id":       "dockerfile.missing_user",
			"title":    "Dockerfile does not define a non-root USER instruction.",
			"severity": "medium",
			"target":   filepath.ToSlash(dockerfilePath),
			"line":     0,
		})
		if len(findings) >= maxFindings {
			return findings, true
		}
	}
	return findings, false
}

func countSecurityFindingsBySeverity(findings []map[string]any) map[string]int {
	counts := map[string]int{
		"critical": 0,
		"high":     0,
		"medium":   0,
		"low":      0,
		"unknown":  0,
	}
	for _, finding := range findings {
		severity := normalizeFindingSeverity(asString(finding["severity"]))
		counts[severity] = counts[severity] + 1
	}
	return counts
}

func normalizeLicensePolicyTokens(tokens []string) []string {
	if len(tokens) == 0 {
		return nil
	}
	out := make([]string, 0, len(tokens))
	seen := map[string]struct{}{}
	for _, token := range tokens {
		for _, part := range splitPolicyTokens(token) {
			normalized := normalizeLicenseToken(part)
			if normalized == "" {
				continue
			}
			if _, exists := seen[normalized]; exists {
				continue
			}
			seen[normalized] = struct{}{}
			out = append(out, normalized)
		}
	}
	sort.Strings(out)
	return out
}

func enrichDependencyLicenses(
	ctx context.Context,
	runner app.CommandRunner,
	session domain.Session,
	detected projectType,
	scanPath string,
	entries []dependencyEntry,
	maxDependencies int,
) ([]dependencyEntry, []string, string, error) {
	enriched := cloneDependencyEntries(entries)
	if len(enriched) == 0 {
		return enriched, nil, "", nil
	}
	for i := range enriched {
		enriched[i].License = nonEmptyOrDefault(strings.TrimSpace(enriched[i].License), "unknown")
	}

	cwd := session.WorkspacePath
	if scanPath != "" && scanPath != "." {
		cwd = filepath.Join(session.WorkspacePath, filepath.FromSlash(scanPath))
	}

	switch detected.Name {
	case "node":
		command := []string{"npm", "ls", "--json", "--all", "--long"}
		result, runErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      cwd,
			Command:  command[0],
			Args:     command[1:],
			MaxBytes: 2 * 1024 * 1024,
		})
		licenseByDependency, parseErr := parseNodeLicenseMap(result.Output, maxDependencies)
		if parseErr != nil && runErr == nil {
			return enriched, command, result.Output, parseErr
		}
		applyDependencyLicenses(enriched, licenseByDependency)
		return enriched, command, result.Output, runErr
	case "rust":
		command := []string{"cargo", "metadata", "--format-version", "1"}
		result, runErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      cwd,
			Command:  command[0],
			Args:     command[1:],
			MaxBytes: 2 * 1024 * 1024,
		})
		licenseByDependency, parseErr := parseRustLicenseMap(result.Output, maxDependencies)
		if parseErr != nil && runErr == nil {
			return enriched, command, result.Output, parseErr
		}
		applyDependencyLicenses(enriched, licenseByDependency)
		return enriched, command, result.Output, runErr
	default:
		return enriched, nil, "", nil
	}
}

func evaluateLicenseAgainstPolicy(license string, allowedLicenses []string, deniedLicenses []string) (string, string) {
	tokens := licenseExpressionTokens(license)
	if len(tokens) == 0 {
		return "unknown", sweLicenseIsUnknown
	}
	allowedSet := sliceToStringSet(allowedLicenses)
	deniedSet := sliceToStringSet(deniedLicenses)

	unknown, deniedStatus, deniedReason := checkTokensAgainstDenied(tokens, deniedSet)
	if deniedStatus != "" {
		return deniedStatus, deniedReason
	}

	if len(allowedSet) > 0 {
		return checkTokensAgainstAllowed(tokens, allowedSet, unknown)
	}

	if unknown {
		return "unknown", sweLicenseIsUnknown
	}
	return "allowed", ""
}

func sliceToStringSet(items []string) map[string]struct{} {
	set := make(map[string]struct{}, len(items))
	for _, item := range items {
		set[item] = struct{}{}
	}
	return set
}

func checkTokensAgainstDenied(tokens []string, deniedSet map[string]struct{}) (unknown bool, status, reason string) {
	for _, token := range tokens {
		if token == "UNKNOWN" {
			unknown = true
			continue
		}
		if _, denied := deniedSet[token]; denied {
			return unknown, "denied", "matched denied license: " + token
		}
	}
	return unknown, "", ""
}

func checkTokensAgainstAllowed(tokens []string, allowedSet map[string]struct{}, unknown bool) (string, string) {
	for _, token := range tokens {
		if _, allowed := allowedSet[token]; allowed {
			return "allowed", ""
		}
	}
	if unknown {
		return "unknown", sweLicenseIsUnknown
	}
	return "denied", "license not present in allowed_licenses"
}

func parseNodeLicenseMap(output string, maxDependencies int) (map[string]string, error) {
	var payload map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		return nil, err
	}
	dependencies, _ := payload["dependencies"].(map[string]any)
	licenseByDependency := make(map[string]string, minInt(len(dependencies), maxDependencies))
	seen := map[string]struct{}{}
	walkNodeLicenseMap(dependencies, maxDependencies, seen, licenseByDependency)
	return licenseByDependency, nil
}

func walkNodeLicenseMap(tree map[string]any, maxDependencies int, seen map[string]struct{}, out map[string]string) {
	if tree == nil {
		return
	}
	names := make([]string, 0, len(tree))
	for name := range tree {
		names = append(names, name)
	}
	sort.Strings(names)

	for _, name := range names {
		if len(out) >= maxDependencies {
			return
		}
		rawNode, ok := tree[name]
		if !ok {
			continue
		}
		node, ok := rawNode.(map[string]any)
		if !ok {
			continue
		}
		version := nonEmptyOrDefault(strings.TrimSpace(asString(node["version"])), "unknown")
		key := dependencyLicenseLookupKey("node", name, version)
		if _, exists := seen[key]; !exists {
			seen[key] = struct{}{}
			license := normalizeFoundLicense(nodeStringOrList(node["license"]))
			if license != "" && license != "unknown" {
				out[key] = license
			}
		}

		children, _ := node["dependencies"].(map[string]any)
		walkNodeLicenseMap(children, maxDependencies, seen, out)
	}
}

func parseRustLicenseMap(output string, maxDependencies int) (map[string]string, error) {
	type rustMetadata struct {
		Packages []struct {
			Name    string `json:"name"`
			Version string `json:"version"`
			License string `json:"license"`
		} `json:"packages"`
	}

	payload := rustMetadata{}
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		return nil, err
	}
	out := make(map[string]string, minInt(len(payload.Packages), maxDependencies))
	for _, pkg := range payload.Packages {
		if len(out) >= maxDependencies {
			break
		}
		name := strings.TrimSpace(pkg.Name)
		version := nonEmptyOrDefault(strings.TrimSpace(pkg.Version), "unknown")
		if name == "" {
			continue
		}
		license := normalizeFoundLicense(pkg.License)
		if license == "" || license == "unknown" {
			continue
		}
		out[dependencyLicenseLookupKey("rust", name, version)] = license
	}
	return out, nil
}

func applyDependencyLicenses(entries []dependencyEntry, licenseByDependency map[string]string) {
	if len(entries) == 0 || len(licenseByDependency) == 0 {
		return
	}
	for index := range entries {
		key := dependencyLicenseLookupKey(entries[index].Ecosystem, entries[index].Name, entries[index].Version)
		license, exists := licenseByDependency[key]
		if !exists {
			continue
		}
		entries[index].License = nonEmptyOrDefault(license, entries[index].License)
	}
}

func cloneDependencyEntries(entries []dependencyEntry) []dependencyEntry {
	if len(entries) == 0 {
		return nil
	}
	out := make([]dependencyEntry, len(entries))
	copy(out, entries)
	return out
}

func dependencyLicenseLookupKey(ecosystem, name, version string) string {
	normalizedEcosystem := strings.TrimSpace(strings.ToLower(ecosystem))
	normalizedName := strings.TrimSpace(name)
	switch normalizedEcosystem {
	case "node", "python", "rust":
		normalizedName = strings.ToLower(normalizedName)
	}
	return normalizedEcosystem + "|" + normalizedName + "|" + nonEmptyOrDefault(strings.TrimSpace(version), "unknown")
}

func splitPolicyTokens(raw string) []string {
	return strings.FieldsFunc(raw, func(r rune) bool {
		switch r {
		case ',', ';':
			return true
		default:
			return unicode.IsSpace(r)
		}
	})
}

func normalizeLicenseToken(raw string) string {
	token := strings.ToUpper(strings.TrimSpace(raw))
	token = strings.Trim(token, "()")
	token = strings.ReplaceAll(token, "_", "-")
	switch token {
	case "", "N/A", "NONE", "NOASSERTION":
		return "UNKNOWN"
	default:
		return token
	}
}

func licenseExpressionTokens(raw string) []string {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return nil
	}
	parts := strings.FieldsFunc(strings.ToUpper(trimmed), func(r rune) bool {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			return false
		}
		switch r {
		case '.', '-', '+':
			return false
		default:
			return true
		}
	})
	tokens := make([]string, 0, len(parts))
	seen := map[string]struct{}{}
	for _, part := range parts {
		token := normalizeLicenseToken(part)
		switch token {
		case "", "AND", "OR", "WITH", "LICENSE", "ONLY", "LATER":
			continue
		}
		if _, exists := seen[token]; exists {
			continue
		}
		seen[token] = struct{}{}
		tokens = append(tokens, token)
	}
	return tokens
}

func normalizeFoundLicense(raw string) string {
	tokens := licenseExpressionTokens(raw)
	if len(tokens) == 0 {
		token := normalizeLicenseToken(raw)
		if token == "" {
			return ""
		}
		if token == "UNKNOWN" {
			return "unknown"
		}
		return token
	}
	if len(tokens) == 1 {
		if tokens[0] == "UNKNOWN" {
			return "unknown"
		}
		return tokens[0]
	}
	return strings.Join(tokens, " OR ")
}

func nodeStringOrList(raw any) string {
	switch typed := raw.(type) {
	case string:
		return typed
	case []any:
		parts := make([]string, 0, len(typed))
		for _, item := range typed {
			if value, ok := item.(string); ok && strings.TrimSpace(value) != "" {
				parts = append(parts, strings.TrimSpace(value))
			}
		}
		return strings.Join(parts, " OR ")
	default:
		return ""
	}
}

func normalizeFindingSeverity(raw string) string {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "critical":
		return "critical"
	case "high":
		return "high"
	case "medium", "moderate":
		return "medium"
	case "low":
		return "low"
	default:
		return "unknown"
	}
}

func severityAtOrAbove(severity, threshold string) bool {
	return securitySeverityRank(normalizeFindingSeverity(severity)) >= securitySeverityRank(normalizeFindingSeverity(threshold))
}

func securitySeverityRank(severity string) int {
	switch normalizeFindingSeverity(severity) {
	case "critical":
		return 4
	case "high":
		return 3
	case "medium":
		return 2
	case "low":
		return 1
	default:
		return 0
	}
}

func dockerfileHeuristicRule(line string) (string, string, string) {
	switch {
	case strings.HasPrefix(line, "from "):
		if strings.Contains(line, "@sha256:") {
			return "", "", ""
		}
		if strings.Contains(line, ":latest") || !strings.Contains(line, ":") {
			return "dockerfile.unpinned_base_image", "medium", "Base image should be pinned to a fixed version or digest."
		}
	case strings.HasPrefix(line, "add "):
		return "dockerfile.add_instead_of_copy", "low", "Prefer COPY over ADD unless archive extraction is required."
	case strings.HasPrefix(line, "run "):
		if (strings.Contains(line, "curl ") || strings.Contains(line, "wget ")) && strings.Contains(line, "|") {
			return "dockerfile.pipe_to_shell", "high", "Avoid piping remote content directly into a shell."
		}
		if strings.Contains(line, "chmod 777") {
			return "dockerfile.chmod_777", "medium", "Avoid world-writable permissions (chmod 777)."
		}
		if strings.Contains(line, "apt-get install") && !strings.Contains(line, "--no-install-recommends") {
			return "dockerfile.apt_install_recommends", "low", "Use --no-install-recommends to reduce image attack surface."
		}
	}
	return "", "", ""
}

func isDockerfileCandidate(name string) bool {
	lower := strings.ToLower(strings.TrimSpace(name))
	if lower == "" {
		return false
	}
	if lower == "dockerfile" {
		return true
	}
	return strings.HasPrefix(lower, "dockerfile.") || strings.HasSuffix(lower, ".dockerfile")
}

func asString(raw any) string {
	value, _ := raw.(string)
	return strings.TrimSpace(value)
}

func intMapToAnyMap(raw map[string]int) map[string]any {
	out := make(map[string]any, len(raw))
	for key, value := range raw {
		out[key] = value
	}
	return out
}

func truncateString(raw string, maxLen int) string {
	if maxLen <= 0 {
		return ""
	}
	if len(raw) <= maxLen {
		return raw
	}
	return raw[:maxLen]
}

func nonEmptyOrDefault(raw, fallback string) string {
	if strings.TrimSpace(raw) == "" {
		return fallback
	}
	return raw
}

func targetOrDefault(target, fallback string) string {
	trimmed := strings.TrimSpace(target)
	if trimmed == "" {
		return fallback
	}
	return trimmed
}
