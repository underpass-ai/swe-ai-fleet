package tools

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type ImageBuildHandler struct {
	runner app.CommandRunner
}

type ImagePushHandler struct {
	runner app.CommandRunner
}

type ImageInspectHandler struct {
	runner app.CommandRunner
}

func NewImageBuildHandler(runner app.CommandRunner) *ImageBuildHandler {
	return &ImageBuildHandler{runner: runner}
}

func NewImagePushHandler(runner app.CommandRunner) *ImagePushHandler {
	return &ImagePushHandler{runner: runner}
}

func NewImageInspectHandler(runner app.CommandRunner) *ImageInspectHandler {
	return &ImageInspectHandler{runner: runner}
}

func (h *ImageBuildHandler) Name() string {
	return "image.build"
}

func (h *ImagePushHandler) Name() string {
	return "image.push"
}

func (h *ImageBuildHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ContextPath            string `json:"context_path"`
		DockerfilePath         string `json:"dockerfile_path"`
		Tag                    string `json:"tag"`
		Push                   bool   `json:"push"`
		NoCache                bool   `json:"no_cache"`
		MaxIssues              int    `json:"max_issues"`
		IncludeRecommendations bool   `json:"include_recommendations"`
	}{
		ContextPath:            ".",
		DockerfilePath:         "Dockerfile",
		Push:                   false,
		NoCache:                false,
		MaxIssues:              200,
		IncludeRecommendations: true,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid image.build args",
				Retryable: false,
			}
		}
	}

	contextPath, contextErr := sanitizeRelativePath(request.ContextPath)
	if contextErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   contextErr.Error(),
			Retryable: false,
		}
	}
	if contextPath == "" {
		contextPath = "."
	}

	dockerfilePath, dockerfileErr := sanitizeRelativePath(request.DockerfilePath)
	if dockerfileErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   dockerfileErr.Error(),
			Retryable: false,
		}
	}
	if dockerfilePath == "" {
		dockerfilePath = "Dockerfile"
	}
	effectiveDockerfilePath := resolveImageDockerfilePath(contextPath, dockerfilePath)

	tag := strings.TrimSpace(request.Tag)
	if tag == "" {
		tag = defaultImageBuildTag(session.ID)
	}
	if tagErr := validateImageReference(tag); tagErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   tagErr.Error(),
			Retryable: false,
		}
	}

	runner := ensureRunner(h.runner)
	dockerfileResult, dockerfileRunErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "cat",
		Args:     []string{effectiveDockerfilePath},
		MaxBytes: 512 * 1024,
	})

	maxIssues := clampInt(request.MaxIssues, 1, 2000, 200)
	inspectReport := inspectDockerfileContent(
		dockerfileResult.Output,
		contextPath,
		effectiveDockerfilePath,
		maxIssues,
		request.IncludeRecommendations,
	)
	registry, repository, _, _ := parseImageReference(tag)
	digestFromDockerfile := "sha256:" + sha256Hex(dockerfileResult.Output)
	if dockerfileRunErr != nil {
		result := imageBuildResult(
			map[string]any{
				"builder":             "none",
				"simulated":           false,
				"context_path":        contextPath,
				"dockerfile_path":     effectiveDockerfilePath,
				"tag":                 tag,
				"image_ref":           tag,
				"registry":            registry,
				"repository":          repository,
				"digest":              "",
				"command":             []string{"cat", effectiveDockerfilePath},
				"push_command":        []string{},
				"push_requested":      request.Push,
				"pushed":              false,
				"push_skipped_reason": "",
				"issues_count":        len(inspectReport.Issues),
				"issues":              inspectReport.Issues,
				"recommendations":     inspectReport.Recommendations,
				"truncated":           inspectReport.Truncated,
				"exit_code":           dockerfileResult.ExitCode,
				"summary":             "image build failed: unable to read Dockerfile",
				"output":              dockerfileResult.Output,
			},
			dockerfileResult.Output,
			dockerfileResult.Output,
		)
		return result, toToolError(dockerfileRunErr, dockerfileResult.Output)
	}

	builder := detectImageBuilder(ctx, runner, session)
	simulated := false
	issuesCount := len(inspectReport.Issues)
	command := []string{}
	pushCommand := []string{}
	pushed := false
	pushSkippedReason := ""
	exitCode := 0
	summary := "image build completed"
	buildOutput := ""
	logMessage := ""
	imageDigest := digestFromDockerfile
	var runErr error

	if builder == "" {
		builder = "synthetic"
		simulated = true
		summary = "image build simulated (no container builder available)"
		buildOutput = summary
		logMessage = summary
		if request.Push {
			pushSkippedReason = "no_container_builder_available"
		}
	} else {
		command = buildImageBuildCommand(builder, contextPath, effectiveDockerfilePath, tag, request.NoCache)
		buildResult, buildErr := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  command[0],
			Args:     command[1:],
			MaxBytes: 2 * 1024 * 1024,
		})
		buildOutput = strings.TrimSpace(buildResult.Output)
		logMessage = buildOutput
		exitCode = buildResult.ExitCode
		runErr = buildErr
		if digest := extractImageDigest(buildResult.Output); digest != "" {
			imageDigest = digest
		}
		if buildErr != nil {
			summary = "image build failed"
			if request.Push {
				pushSkippedReason = "build_failed"
			}
		} else if request.Push {
			pushCommand = buildImagePushCommand(builder, tag)
			pushResult, pushErr := runner.Run(ctx, session, app.CommandSpec{
				Cwd:      session.WorkspacePath,
				Command:  pushCommand[0],
				Args:     pushCommand[1:],
				MaxBytes: 2 * 1024 * 1024,
			})
			if strings.TrimSpace(pushResult.Output) != "" {
				if strings.TrimSpace(buildOutput) != "" {
					buildOutput = buildOutput + "\n" + pushResult.Output
				} else {
					buildOutput = pushResult.Output
				}
			}
			logMessage = buildOutput
			exitCode = pushResult.ExitCode
			if pushErr != nil {
				summary = "image push failed"
				runErr = pushErr
			} else {
				pushed = true
				summary = "image build and push completed"
			}
		}
	}

	imageRef := tag
	if imageDigest != "" && !strings.Contains(imageRef, "@") {
		imageRef = imageRef + "@" + imageDigest
	}
	if strings.TrimSpace(buildOutput) == "" {
		buildOutput = summary
	}
	if strings.TrimSpace(logMessage) == "" {
		logMessage = buildOutput
	}

	result := imageBuildResult(
		map[string]any{
			"builder":             builder,
			"simulated":           simulated,
			"context_path":        contextPath,
			"dockerfile_path":     effectiveDockerfilePath,
			"tag":                 tag,
			"image_ref":           imageRef,
			"registry":            registry,
			"repository":          repository,
			"digest":              imageDigest,
			"command":             command,
			"push_command":        pushCommand,
			"push_requested":      request.Push,
			"pushed":              pushed,
			"push_skipped_reason": pushSkippedReason,
			"issues_count":        issuesCount,
			"issues":              inspectReport.Issues,
			"recommendations":     inspectReport.Recommendations,
			"truncated":           inspectReport.Truncated,
			"exit_code":           exitCode,
			"summary":             summary,
			"output":              buildOutput,
		},
		buildOutput,
		logMessage,
	)
	if runErr != nil {
		return result, toToolError(runErr, buildOutput)
	}
	return result, nil
}

func (h *ImagePushHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ImageRef               string `json:"image_ref"`
		MaxRetries             int    `json:"max_retries"`
		Strict                 bool   `json:"strict"`
		MaxIssues              int    `json:"max_issues"`
		IncludeRecommendations bool   `json:"include_recommendations"`
	}{
		MaxRetries:             0,
		Strict:                 false,
		MaxIssues:              200,
		IncludeRecommendations: true,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid image.push args",
				Retryable: false,
			}
		}
	}

	imageRef := strings.TrimSpace(request.ImageRef)
	if imageRef == "" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "image_ref is required",
			Retryable: false,
		}
	}
	if validateErr := validateImageReference(imageRef); validateErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   validateErr.Error(),
			Retryable: false,
		}
	}

	maxRetries := clampInt(request.MaxRetries, 0, 5, 0)
	maxIssues := clampInt(request.MaxIssues, 1, 2000, 200)
	report := inspectImageReference(imageRef, maxIssues, request.IncludeRecommendations)
	registry, repository, tag, digest := parseImageReference(imageRef)

	runner := ensureRunner(h.runner)
	builder := detectImageBuilder(ctx, runner, session)
	command := []string{}
	attempts := 0
	simulated := false
	pushed := false
	pushSkippedReason := ""
	exitCode := 0
	summary := "image push completed"
	outputText := ""
	logMessage := ""
	var runErr error

	if builder == "" {
		simulated = true
		builder = "synthetic"
		pushSkippedReason = "no_container_builder_available"
		summary = "image push simulated (no container builder available)"
		outputText = summary
		logMessage = summary
		if request.Strict {
			exitCode = 1
			result := imagePushResult(
				map[string]any{
					"builder":             builder,
					"simulated":           simulated,
					"image_ref":           imageRef,
					"registry":            registry,
					"repository":          repository,
					"tag":                 tag,
					"digest":              digest,
					"command":             command,
					"attempts":            attempts,
					"max_retries":         maxRetries,
					"pushed":              false,
					"push_skipped_reason": pushSkippedReason,
					"issues_count":        len(report.Issues),
					"issues":              report.Issues,
					"recommendations":     report.Recommendations,
					"truncated":           report.Truncated,
					"exit_code":           exitCode,
					"summary":             "image push failed: no container builder available in strict mode",
					"output":              outputText,
				},
				outputText,
				logMessage,
			)
			return result, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "image push failed: no container builder available in strict mode",
				Retryable: false,
			}
		}
	} else {
		command = buildImagePushCommand(builder, imageRef)
		retryOutputs := make([]string, 0, maxRetries+1)
		for attempt := 1; attempt <= maxRetries+1; attempt++ {
			attempts = attempt
			result, err := runner.Run(ctx, session, app.CommandSpec{
				Cwd:      session.WorkspacePath,
				Command:  command[0],
				Args:     command[1:],
				MaxBytes: 2 * 1024 * 1024,
			})
			exitCode = result.ExitCode
			if strings.TrimSpace(result.Output) != "" {
				retryOutputs = append(retryOutputs, fmt.Sprintf("[attempt %d/%d]\n%s", attempt, maxRetries+1, result.Output))
			}
			if foundDigest := extractImageDigest(result.Output); foundDigest != "" {
				digest = foundDigest
			}
			if err == nil {
				pushed = true
				summary = "image push completed"
				runErr = nil
				break
			}
			runErr = err
			if attempt <= maxRetries {
				continue
			}
			summary = "image push failed"
		}
		outputText = strings.TrimSpace(strings.Join(retryOutputs, "\n"))
		logMessage = outputText
		if strings.TrimSpace(outputText) == "" {
			outputText = summary
			logMessage = summary
		}
	}

	imageRefWithDigest := imageRef
	if digest != "" && !strings.Contains(imageRefWithDigest, "@") {
		imageRefWithDigest = imageRefWithDigest + "@" + digest
	}

	result := imagePushResult(
		map[string]any{
			"builder":             builder,
			"simulated":           simulated,
			"image_ref":           imageRefWithDigest,
			"registry":            registry,
			"repository":          repository,
			"tag":                 tag,
			"digest":              digest,
			"command":             command,
			"attempts":            attempts,
			"max_retries":         maxRetries,
			"pushed":              pushed,
			"push_skipped_reason": pushSkippedReason,
			"issues_count":        len(report.Issues),
			"issues":              report.Issues,
			"recommendations":     report.Recommendations,
			"truncated":           report.Truncated,
			"exit_code":           exitCode,
			"summary":             summary,
			"output":              outputText,
		},
		outputText,
		logMessage,
	)
	if runErr != nil {
		return result, toToolError(runErr, outputText)
	}
	return result, nil
}

func (h *ImageInspectHandler) Name() string {
	return "image.inspect"
}

func (h *ImageInspectHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ContextPath            string `json:"context_path"`
		DockerfilePath         string `json:"dockerfile_path"`
		ImageRef               string `json:"image_ref"`
		IncludeRecommendations bool   `json:"include_recommendations"`
		MaxIssues              int    `json:"max_issues"`
	}{
		ContextPath:            ".",
		DockerfilePath:         "Dockerfile",
		IncludeRecommendations: true,
		MaxIssues:              200,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid image.inspect args",
				Retryable: false,
			}
		}
	}

	contextPath, contextErr := sanitizeRelativePath(request.ContextPath)
	if contextErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   contextErr.Error(),
			Retryable: false,
		}
	}
	if contextPath == "" {
		contextPath = "."
	}

	dockerfilePath, dockerfileErr := sanitizeRelativePath(request.DockerfilePath)
	if dockerfileErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   dockerfileErr.Error(),
			Retryable: false,
		}
	}
	if dockerfilePath == "" {
		dockerfilePath = "Dockerfile"
	}
	maxIssues := clampInt(request.MaxIssues, 1, 2000, 200)
	imageRef := strings.TrimSpace(request.ImageRef)

	if imageRef != "" {
		report := inspectImageReference(imageRef, maxIssues, request.IncludeRecommendations)
		return imageInspectResult(report, "", nil), nil
	}

	effectiveDockerfilePath := dockerfilePath
	if contextPath != "." {
		effectiveDockerfilePath = strings.TrimPrefix(strings.TrimSpace(contextPath)+"/"+strings.TrimPrefix(strings.TrimSpace(dockerfilePath), "./"), "./")
	}

	runner := ensureRunner(h.runner)
	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  "cat",
		Args:     []string{effectiveDockerfilePath},
		MaxBytes: 512 * 1024,
	})

	report := inspectDockerfileContent(commandResult.Output, contextPath, effectiveDockerfilePath, maxIssues, request.IncludeRecommendations)
	result := imageInspectResult(report, commandResult.Output, []string{"cat", effectiveDockerfilePath})
	if runErr != nil {
		return result, toToolError(runErr, commandResult.Output)
	}
	return result, nil
}

type imageInspectReport struct {
	SourceType      string
	ContextPath     string
	DockerfilePath  string
	ImageRef        string
	Registry        string
	Repository      string
	Tag             string
	Digest          string
	BaseImages      []string
	StagesCount     int
	ExposedPorts    []string
	User            string
	Entrypoint      string
	Cmd             string
	Issues          []map[string]any
	Recommendations []string
	Truncated       bool
}

func inspectDockerfileContent(content string, contextPath string, dockerfilePath string, maxIssues int, includeRecommendations bool) imageInspectReport {
	report := imageInspectReport{
		SourceType:     "dockerfile",
		ContextPath:    contextPath,
		DockerfilePath: dockerfilePath,
		BaseImages:     []string{},
		ExposedPorts:   []string{},
		Issues:         []map[string]any{},
	}

	baseSeen := map[string]struct{}{}
	portSeen := map[string]struct{}{}
	lines := strings.Split(content, "\n")
	for idx, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		upper := strings.ToUpper(line)

		switch {
		case strings.HasPrefix(upper, "FROM "):
			image := parseFromImage(line)
			if image == "" {
				continue
			}
			report.StagesCount++
			if _, exists := baseSeen[image]; !exists {
				baseSeen[image] = struct{}{}
				report.BaseImages = append(report.BaseImages, image)
			}
			if strings.Contains(image, ":latest") {
				report.Issues = appendImageIssue(report.Issues, "dockerfile.unpinned_base_image_latest", "medium", idx+1, "Base image uses mutable latest tag.", line)
			} else if !strings.Contains(image, "@sha256:") && !hasImageTag(image) {
				report.Issues = appendImageIssue(report.Issues, "dockerfile.unpinned_base_image", "medium", idx+1, "Base image is not pinned with tag or digest.", line)
			}
		case strings.HasPrefix(upper, "EXPOSE "):
			for _, token := range strings.Fields(strings.TrimSpace(line[len("EXPOSE "):])) {
				normalized := strings.TrimSpace(token)
				if normalized == "" {
					continue
				}
				if _, exists := portSeen[normalized]; exists {
					continue
				}
				portSeen[normalized] = struct{}{}
				report.ExposedPorts = append(report.ExposedPorts, normalized)
			}
		case strings.HasPrefix(upper, "USER "):
			report.User = strings.TrimSpace(line[len("USER "):])
		case strings.HasPrefix(upper, "ENTRYPOINT "):
			report.Entrypoint = strings.TrimSpace(line[len("ENTRYPOINT "):])
		case strings.HasPrefix(upper, "CMD "):
			report.Cmd = strings.TrimSpace(line[len("CMD "):])
		case strings.HasPrefix(upper, "ADD "):
			report.Issues = appendImageIssue(report.Issues, "dockerfile.add_instead_of_copy", "low", idx+1, "Prefer COPY over ADD unless archive extraction is required.", line)
		case strings.HasPrefix(upper, "RUN "):
			lower := strings.ToLower(line)
			if (strings.Contains(lower, "curl ") || strings.Contains(lower, "wget ")) && strings.Contains(lower, "|") {
				report.Issues = appendImageIssue(report.Issues, "dockerfile.pipe_to_shell", "high", idx+1, "Avoid piping remote downloads directly into a shell.", line)
			}
			if strings.Contains(lower, "chmod 777") {
				report.Issues = appendImageIssue(report.Issues, "dockerfile.chmod_777", "medium", idx+1, "Avoid world-writable permissions (chmod 777).", line)
			}
			if strings.Contains(lower, "apt-get install") && !strings.Contains(lower, "--no-install-recommends") {
				report.Issues = appendImageIssue(report.Issues, "dockerfile.apt_install_recommends", "low", idx+1, "Use --no-install-recommends to minimize image attack surface.", line)
			}
		}
	}

	if strings.TrimSpace(report.User) == "" {
		report.Issues = appendImageIssue(report.Issues, "dockerfile.missing_user", "medium", 0, "Dockerfile does not define a non-root USER instruction.", "")
	}
	sortImageIssues(report.Issues)
	if len(report.Issues) > maxIssues {
		report.Issues = report.Issues[:maxIssues]
		report.Truncated = true
	}
	if includeRecommendations {
		report.Recommendations = imageRecommendationsFromIssues(report.Issues)
	}
	return report
}

func inspectImageReference(imageRef string, maxIssues int, includeRecommendations bool) imageInspectReport {
	registry, repository, tag, digest := parseImageReference(imageRef)
	report := imageInspectReport{
		SourceType:      "image_ref",
		ImageRef:        imageRef,
		Registry:        registry,
		Repository:      repository,
		Tag:             tag,
		Digest:          digest,
		BaseImages:      []string{},
		ExposedPorts:    []string{},
		Issues:          []map[string]any{},
		Recommendations: []string{},
	}

	if tag == "latest" {
		report.Issues = appendImageIssue(report.Issues, "image_ref.latest_tag", "medium", 0, "Image reference uses mutable latest tag.", imageRef)
	}
	if tag == "" && digest == "" {
		report.Issues = appendImageIssue(report.Issues, "image_ref.missing_tag_or_digest", "medium", 0, "Image reference should include a fixed tag or digest.", imageRef)
	}
	if digest == "" {
		report.Issues = appendImageIssue(report.Issues, "image_ref.missing_digest", "low", 0, "Pin image reference with digest for immutable deployments.", imageRef)
	}

	sortImageIssues(report.Issues)
	if len(report.Issues) > maxIssues {
		report.Issues = report.Issues[:maxIssues]
		report.Truncated = true
	}
	if includeRecommendations {
		report.Recommendations = imageRecommendationsFromIssues(report.Issues)
	}
	return report
}

func imageInspectResult(report imageInspectReport, rawOutput string, command []string) app.ToolRunResult {
	issuesCount := len(report.Issues)
	summary := "image inspect completed"
	if report.SourceType == "dockerfile" {
		summary = "dockerfile inspect completed"
	}
	if issuesCount > 0 {
		summary = summary + " with issues"
	}

	output := map[string]any{
		"source_type":     report.SourceType,
		"context_path":    report.ContextPath,
		"dockerfile_path": report.DockerfilePath,
		"image_ref":       report.ImageRef,
		"registry":        report.Registry,
		"repository":      report.Repository,
		"tag":             report.Tag,
		"digest":          report.Digest,
		"command":         command,
		"base_images":     report.BaseImages,
		"stages_count":    report.StagesCount,
		"exposed_ports":   report.ExposedPorts,
		"user":            report.User,
		"entrypoint":      report.Entrypoint,
		"cmd":             report.Cmd,
		"issues_count":    issuesCount,
		"issues":          report.Issues,
		"recommendations": report.Recommendations,
		"truncated":       report.Truncated,
		"exit_code":       0,
		"summary":         summary,
		"output":          summary,
	}

	reportBytes, marshalErr := json.MarshalIndent(output, "", "  ")
	artifacts := []app.ArtifactPayload{
		{
			Name:        "image-inspect-report.json",
			ContentType: "application/json",
			Data:        reportBytes,
		},
	}
	if strings.TrimSpace(rawOutput) != "" {
		artifacts = append(artifacts, app.ArtifactPayload{
			Name:        "image-inspect-source.txt",
			ContentType: "text/plain",
			Data:        []byte(rawOutput),
		})
	}
	if marshalErr != nil {
		artifacts = []app.ArtifactPayload{}
	}

	logMessage := rawOutput
	if strings.TrimSpace(logMessage) == "" {
		logMessage = summary
	}
	return app.ToolRunResult{
		ExitCode:  0,
		Logs:      []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: logMessage}},
		Output:    output,
		Artifacts: artifacts,
	}
}

func imageBuildResult(output map[string]any, rawOutput string, logMessage string) app.ToolRunResult {
	reportBytes, marshalErr := json.MarshalIndent(output, "", "  ")
	artifacts := []app.ArtifactPayload{
		{
			Name:        "image-build-report.json",
			ContentType: "application/json",
			Data:        reportBytes,
		},
	}
	if strings.TrimSpace(rawOutput) != "" {
		artifacts = append(artifacts, app.ArtifactPayload{
			Name:        "image-build-output.txt",
			ContentType: "text/plain",
			Data:        []byte(rawOutput),
		})
	}
	if marshalErr != nil {
		artifacts = []app.ArtifactPayload{}
	}

	exitCode, _ := output["exit_code"].(int)
	if strings.TrimSpace(logMessage) == "" {
		logMessage = asString(output["summary"])
	}
	return app.ToolRunResult{
		ExitCode:  exitCode,
		Logs:      []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: logMessage}},
		Output:    output,
		Artifacts: artifacts,
	}
}

func imagePushResult(output map[string]any, rawOutput string, logMessage string) app.ToolRunResult {
	reportBytes, marshalErr := json.MarshalIndent(output, "", "  ")
	artifacts := []app.ArtifactPayload{
		{
			Name:        "image-push-report.json",
			ContentType: "application/json",
			Data:        reportBytes,
		},
	}
	if strings.TrimSpace(rawOutput) != "" {
		artifacts = append(artifacts, app.ArtifactPayload{
			Name:        "image-push-output.txt",
			ContentType: "text/plain",
			Data:        []byte(rawOutput),
		})
	}
	if marshalErr != nil {
		artifacts = []app.ArtifactPayload{}
	}

	exitCode, _ := output["exit_code"].(int)
	if strings.TrimSpace(logMessage) == "" {
		logMessage = asString(output["summary"])
	}
	return app.ToolRunResult{
		ExitCode:  exitCode,
		Logs:      []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: logMessage}},
		Output:    output,
		Artifacts: artifacts,
	}
}

func appendImageIssue(issues []map[string]any, id string, severity string, line int, message string, snippet string) []map[string]any {
	return append(issues, map[string]any{
		"id":       strings.TrimSpace(id),
		"severity": normalizeFindingSeverity(severity),
		"line":     line,
		"message":  strings.TrimSpace(message),
		"snippet":  truncateString(strings.TrimSpace(snippet), 240),
	})
}

func sortImageIssues(issues []map[string]any) {
	sort.Slice(issues, func(i, j int) bool {
		left := issues[i]
		right := issues[j]
		leftSeverity := normalizeFindingSeverity(asString(left["severity"]))
		rightSeverity := normalizeFindingSeverity(asString(right["severity"]))
		if securitySeverityRank(leftSeverity) != securitySeverityRank(rightSeverity) {
			return securitySeverityRank(leftSeverity) > securitySeverityRank(rightSeverity)
		}
		leftLine, leftLineOK := left["line"].(int)
		rightLine, rightLineOK := right["line"].(int)
		if leftLineOK && rightLineOK && leftLine != rightLine {
			return leftLine < rightLine
		}
		return asString(left["id"]) < asString(right["id"])
	})
}

func imageRecommendationsFromIssues(issues []map[string]any) []string {
	if len(issues) == 0 {
		return []string{"No immediate issues detected for the provided image source."}
	}
	out := make([]string, 0, 6)
	seen := map[string]struct{}{}
	appendUnique := func(value string) {
		if strings.TrimSpace(value) == "" {
			return
		}
		if _, exists := seen[value]; exists {
			return
		}
		seen[value] = struct{}{}
		out = append(out, value)
	}
	for _, issue := range issues {
		switch asString(issue["id"]) {
		case "dockerfile.unpinned_base_image", "dockerfile.unpinned_base_image_latest", "image_ref.latest_tag", "image_ref.missing_tag_or_digest", "image_ref.missing_digest":
			appendUnique("Pin base images and deployment references with fixed tags and digests.")
		case "dockerfile.missing_user":
			appendUnique("Set a non-root USER in Dockerfile runtime stages.")
		case "dockerfile.pipe_to_shell":
			appendUnique("Avoid piping remote scripts into shell; download, verify, then execute explicitly.")
		case "dockerfile.chmod_777":
			appendUnique("Replace broad permissions like chmod 777 with minimum required permissions.")
		case "dockerfile.add_instead_of_copy":
			appendUnique("Prefer COPY over ADD to keep image layers predictable.")
		case "dockerfile.apt_install_recommends":
			appendUnique("Use --no-install-recommends for apt installations.")
		}
	}
	return out
}

func parseFromImage(line string) string {
	fields := strings.Fields(strings.TrimSpace(line))
	if len(fields) < 2 {
		return ""
	}
	for _, token := range fields[1:] {
		clean := strings.TrimSpace(token)
		if clean == "" {
			continue
		}
		if strings.HasPrefix(clean, "--") {
			continue
		}
		if strings.EqualFold(clean, "AS") {
			break
		}
		return clean
	}
	return ""
}

func hasImageTag(image string) bool {
	trimmed := strings.TrimSpace(image)
	if trimmed == "" {
		return false
	}
	lastSlash := strings.LastIndex(trimmed, "/")
	lastColon := strings.LastIndex(trimmed, ":")
	return lastColon > lastSlash
}

func parseImageReference(ref string) (string, string, string, string) {
	trimmed := strings.TrimSpace(ref)
	if trimmed == "" {
		return "", "", "", ""
	}
	namePart := trimmed
	digest := ""
	if index := strings.Index(namePart, "@"); index >= 0 {
		digest = strings.TrimSpace(namePart[index+1:])
		namePart = strings.TrimSpace(namePart[:index])
	}

	tag := ""
	if lastSlash := strings.LastIndex(namePart, "/"); strings.LastIndex(namePart, ":") > lastSlash {
		tagIndex := strings.LastIndex(namePart, ":")
		tag = strings.TrimSpace(namePart[tagIndex+1:])
		namePart = strings.TrimSpace(namePart[:tagIndex])
	}

	registry := "docker.io"
	repository := namePart
	parts := strings.Split(namePart, "/")
	if len(parts) > 1 {
		first := strings.TrimSpace(parts[0])
		if strings.Contains(first, ".") || strings.Contains(first, ":") || first == "localhost" {
			registry = first
			repository = strings.Join(parts[1:], "/")
		}
	}
	return registry, strings.TrimSpace(repository), strings.TrimSpace(tag), strings.TrimSpace(digest)
}

func resolveImageDockerfilePath(contextPath string, dockerfilePath string) string {
	effectiveDockerfilePath := dockerfilePath
	if contextPath != "." {
		effectiveDockerfilePath = strings.TrimPrefix(strings.TrimSpace(contextPath)+"/"+strings.TrimPrefix(strings.TrimSpace(dockerfilePath), "./"), "./")
	}
	return effectiveDockerfilePath
}

func defaultImageBuildTag(sessionID string) string {
	candidate := strings.ToLower(strings.TrimSpace(sessionID))
	if candidate == "" {
		return "workspace.local/workspace:latest"
	}
	normalized := make([]rune, 0, len(candidate))
	for _, r := range candidate {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' || r == '_' || r == '.' {
			normalized = append(normalized, r)
		} else {
			normalized = append(normalized, '-')
		}
	}
	value := strings.Trim(strings.Join([]string{"workspace.local/workspace", string(normalized)}, ":"), ":")
	value = strings.ReplaceAll(value, "--", "-")
	if strings.HasSuffix(value, ":") {
		value += "latest"
	}
	if !strings.Contains(value, ":") {
		value += ":latest"
	}
	return value
}

func validateImageReference(ref string) error {
	trimmed := strings.TrimSpace(ref)
	if trimmed == "" {
		return fmt.Errorf("tag is required")
	}
	if len(trimmed) > 255 {
		return fmt.Errorf("tag exceeds 255 characters")
	}
	for _, r := range trimmed {
		if r == '\n' || r == '\r' || r == '\t' || r == ' ' {
			return fmt.Errorf("tag must not contain whitespace")
		}
	}
	if strings.HasPrefix(trimmed, ":") || strings.HasPrefix(trimmed, "@") {
		return fmt.Errorf("tag must include a repository name")
	}
	return nil
}

func detectImageBuilder(ctx context.Context, runner app.CommandRunner, session domain.Session) string {
	candidates := []string{"buildah", "podman", "docker"}
	for _, candidate := range candidates {
		result, err := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  candidate,
			Args:     []string{"version"},
			MaxBytes: 64 * 1024,
		})
		if err == nil && result.ExitCode == 0 {
			return candidate
		}
	}
	return ""
}

func buildImageBuildCommand(builder string, contextPath string, dockerfilePath string, tag string, noCache bool) []string {
	switch builder {
	case "buildah":
		args := []string{"buildah", "bud"}
		if noCache {
			args = append(args, "--no-cache")
		}
		return append(args, []string{"-f", dockerfilePath, "-t", tag, contextPath}...)
	case "podman":
		args := []string{"podman", "build"}
		if noCache {
			args = append(args, "--no-cache")
		}
		return append(args, []string{"-f", dockerfilePath, "-t", tag, contextPath}...)
	default:
		args := []string{"docker", "build"}
		if noCache {
			args = append(args, "--no-cache")
		}
		return append(args, []string{"-f", dockerfilePath, "-t", tag, contextPath}...)
	}
}

func buildImagePushCommand(builder string, tag string) []string {
	switch builder {
	case "buildah":
		return []string{"buildah", "push", tag}
	case "podman":
		return []string{"podman", "push", tag}
	default:
		return []string{"docker", "push", tag}
	}
}

var imageDigestPattern = regexp.MustCompile(`sha256:[a-f0-9]{64}`)

func extractImageDigest(output string) string {
	match := imageDigestPattern.FindString(strings.ToLower(output))
	return strings.TrimSpace(match)
}

func sha256Hex(input string) string {
	sum := sha256.Sum256([]byte(input))
	return hex.EncodeToString(sum[:])
}
