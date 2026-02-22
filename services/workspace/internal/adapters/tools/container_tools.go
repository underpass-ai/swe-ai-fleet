package tools

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

const (
	containerPSDefaultLimit       = 50
	containerPSMaxLimit           = 500
	containerMaxOutputBytes       = 2 * 1024 * 1024
	containerDefaultTailLines     = 200
	containerMaxTailLines         = 10000
	containerDefaultMaxLogBytes   = 256 * 1024
	containerDefaultTimeoutSec    = 30
	containerMaxTimeoutSec        = 600
	containerDefaultMaxExecBytes  = 512 * 1024
	containerMaxRunCommandArgs    = 32
	containerMaxExecCommandArgs   = 16
	containerMaxCommandArgLength  = 256
	containerMaxRunEnvVars        = 32
	containerMaxContainerNameSize = 80
)

var (
	containerNameRe        = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$`)
	containerIDRe          = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$`)
	envKeyRe               = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)
	containerRuntimeProbes = []struct {
		Runtime string
		Args    []string
	}{
		{Runtime: "podman", Args: []string{"info", "--format", "json"}},
		{Runtime: "docker", Args: []string{"info", "--format", "{{json .}}"}},
		{Runtime: "nerdctl", Args: []string{"info", "--format", "json"}},
	}
	containerExecAllowedCommands = map[string]bool{
		"echo":    true,
		"cat":     true,
		"ls":      true,
		"pwd":     true,
		"env":     true,
		"id":      true,
		"whoami":  true,
		"date":    true,
		"uname":   true,
		"true":    true,
		"false":   true,
		"sleep":   true,
		"python":  true,
		"python3": true,
		"node":    true,
		"go":      true,
		"npm":     true,
	}
	containerExecDeniedCommands = map[string]bool{
		"rm":       true,
		"mkfs":     true,
		"dd":       true,
		"mount":    true,
		"umount":   true,
		"shutdown": true,
		"reboot":   true,
		"halt":     true,
		"poweroff": true,
	}
	containerRuntimeFallbackErrors = []string{
		"cannot connect to the docker daemon",
		"is the docker daemon running",
		"permission denied while trying to connect",
		"cannot connect to the podman socket",
		"cannot connect to podman",
		"connect: no such file or directory",
		"failed to connect",
		"connection refused",
		"rootless",
		"not found",
	}
)

type ContainerPSHandler struct {
	runner           app.CommandRunner
	client           kubernetes.Interface
	defaultNamespace string
}

type ContainerLogsHandler struct {
	runner           app.CommandRunner
	client           kubernetes.Interface
	defaultNamespace string
}

type ContainerRunHandler struct {
	runner           app.CommandRunner
	client           kubernetes.Interface
	defaultNamespace string
}

type ContainerExecHandler struct {
	runner           app.CommandRunner
	client           kubernetes.Interface
	defaultNamespace string
}

func NewContainerPSHandler(runner app.CommandRunner) *ContainerPSHandler {
	return &ContainerPSHandler{runner: runner}
}

func NewContainerPSHandlerWithKubernetes(
	runner app.CommandRunner,
	client kubernetes.Interface,
	defaultNamespace string,
) *ContainerPSHandler {
	return &ContainerPSHandler{
		runner:           runner,
		client:           client,
		defaultNamespace: strings.TrimSpace(defaultNamespace),
	}
}

func NewContainerLogsHandler(runner app.CommandRunner) *ContainerLogsHandler {
	return &ContainerLogsHandler{runner: runner}
}

func NewContainerLogsHandlerWithKubernetes(
	runner app.CommandRunner,
	client kubernetes.Interface,
	defaultNamespace string,
) *ContainerLogsHandler {
	return &ContainerLogsHandler{
		runner:           runner,
		client:           client,
		defaultNamespace: strings.TrimSpace(defaultNamespace),
	}
}

func NewContainerRunHandler(runner app.CommandRunner) *ContainerRunHandler {
	return &ContainerRunHandler{runner: runner}
}

func NewContainerRunHandlerWithKubernetes(
	runner app.CommandRunner,
	client kubernetes.Interface,
	defaultNamespace string,
) *ContainerRunHandler {
	return &ContainerRunHandler{
		runner:           runner,
		client:           client,
		defaultNamespace: strings.TrimSpace(defaultNamespace),
	}
}

func NewContainerExecHandler(runner app.CommandRunner) *ContainerExecHandler {
	return &ContainerExecHandler{runner: runner}
}

func NewContainerExecHandlerWithKubernetes(
	runner app.CommandRunner,
	client kubernetes.Interface,
	defaultNamespace string,
) *ContainerExecHandler {
	return &ContainerExecHandler{
		runner:           runner,
		client:           client,
		defaultNamespace: strings.TrimSpace(defaultNamespace),
	}
}

func (h *ContainerPSHandler) Name() string {
	return "container.ps"
}

func (h *ContainerLogsHandler) Name() string {
	return "container.logs"
}

func (h *ContainerRunHandler) Name() string {
	return "container.run"
}

func (h *ContainerExecHandler) Name() string {
	return "container.exec"
}

func (h *ContainerPSHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		All        bool   `json:"all"`
		Limit      int    `json:"limit"`
		NameFilter string `json:"name_filter"`
		Strict     *bool  `json:"strict"`
	}{
		Limit: containerPSDefaultLimit,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid container.ps args",
				Retryable: false,
			}
		}
	}

	limit := clampInt(request.Limit, 1, containerPSMaxLimit, containerPSDefaultLimit)
	nameFilter := strings.TrimSpace(request.NameFilter)
	if nameFilter != "" && !containerNameRe.MatchString(nameFilter) {
		return app.ToolRunResult{}, containerInvalidArgument("name_filter is invalid")
	}
	strict := resolveContainerStrictFlag(request.Strict)
	if isKubernetesRuntime(session) && h.client != nil {
		return h.invokeK8sPS(ctx, session, request.All, limit, nameFilter)
	}

	runner := ensureRunner(h.runner)
	runtime, probeOutput := detectContainerRuntime(ctx, runner, session)
	if runtime == "" {
		if strict {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "container runtime not available",
				Retryable: false,
			}
		}
		output := map[string]any{
			"runtime":     "synthetic",
			"simulated":   true,
			"all":         request.All,
			"limit":       limit,
			"name_filter": nameFilter,
			"count":       0,
			"truncated":   false,
			"containers":  []map[string]any{},
			"summary":     "container runtime unavailable; ps simulated",
			"output":      strings.TrimSpace(probeOutput),
			"exit_code":   0,
		}
		return containerResult(output, strings.TrimSpace(probeOutput), "container-ps-report.json", "container-ps-output.txt"), nil
	}

	command := buildContainerPSCommand(runtime, request.All, nameFilter)
	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  command[0],
		Args:     command[1:],
		MaxBytes: containerMaxOutputBytes,
	})
	if runErr != nil {
		if !strict {
			output := map[string]any{
				"runtime":     "synthetic",
				"simulated":   true,
				"all":         request.All,
				"limit":       limit,
				"name_filter": nameFilter,
				"count":       0,
				"truncated":   false,
				"containers":  []map[string]any{},
				"summary":     "container runtime unavailable; ps simulated",
				"output":      strings.TrimSpace(commandResult.Output),
				"exit_code":   0,
			}
			return containerResult(output, commandResult.Output, "container-ps-report.json", "container-ps-output.txt"), nil
		}
		result := containerResult(
			map[string]any{
				"runtime":     runtime,
				"simulated":   false,
				"all":         request.All,
				"limit":       limit,
				"name_filter": nameFilter,
				"count":       0,
				"truncated":   false,
				"containers":  []map[string]any{},
				"summary":     "container ps failed",
				"output":      strings.TrimSpace(commandResult.Output),
				"exit_code":   commandResult.ExitCode,
			},
			commandResult.Output,
			"container-ps-report.json",
			"container-ps-output.txt",
		)
		return result, toToolError(runErr, commandResult.Output)
	}

	containers := parseContainerPSOutput(commandResult.Output)
	truncated := false
	if len(containers) > limit {
		containers = containers[:limit]
		truncated = true
	}
	summary := fmt.Sprintf("listed %d containers", len(containers))
	output := map[string]any{
		"runtime":     runtime,
		"simulated":   false,
		"all":         request.All,
		"limit":       limit,
		"name_filter": nameFilter,
		"count":       len(containers),
		"truncated":   truncated,
		"containers":  containers,
		"summary":     summary,
		"output":      summary,
		"exit_code":   commandResult.ExitCode,
	}
	return containerResult(output, commandResult.Output, "container-ps-report.json", "container-ps-output.txt"), nil
}

func (h *ContainerPSHandler) invokeK8sPS(
	ctx context.Context,
	session domain.Session,
	all bool,
	limit int,
	nameFilter string,
) (app.ToolRunResult, *domain.Error) {
	if err := ensureK8sClient(h.client); err != nil {
		return app.ToolRunResult{}, err
	}

	namespace := resolveK8sNamespace("", session, h.defaultNamespace)
	selectors := []string{"app=workspace-container-run"}
	if sessionID := strings.TrimSpace(session.ID); sessionID != "" {
		selectors = append(selectors, "workspace_session_id="+sanitizeContainerLabelValue(sessionID))
	}

	podList, err := h.client.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{
		LabelSelector: strings.Join(selectors, ","),
	})
	if err != nil {
		return app.ToolRunResult{}, k8sExecutionFailed(fmt.Sprintf("k8s container ps failed: %v", err), true)
	}

	filter := strings.ToLower(strings.TrimSpace(nameFilter))
	containers := make([]map[string]any, 0, len(podList.Items))
	for _, pod := range podList.Items {
		if !all && pod.Status.Phase != corev1.PodRunning {
			continue
		}

		podName := strings.TrimSpace(pod.Name)
		if podName == "" {
			continue
		}
		if filter != "" && !strings.Contains(strings.ToLower(podName), filter) {
			continue
		}

		image := ""
		containerName := resolveK8sRunContainerName(&pod)
		for _, container := range pod.Spec.Containers {
			if strings.TrimSpace(container.Name) == containerName {
				image = strings.TrimSpace(container.Image)
				break
			}
		}
		if image == "" && len(pod.Spec.Containers) > 0 {
			image = strings.TrimSpace(pod.Spec.Containers[0].Image)
		}

		status := strings.ToLower(strings.TrimSpace(string(pod.Status.Phase)))
		if status == "" {
			status = "unknown"
		}
		containers = append(containers, map[string]any{
			"id":     podName,
			"image":  image,
			"name":   podName,
			"status": status,
		})
	}

	sort.Slice(containers, func(i, j int) bool {
		return asString(containers[i]["id"]) < asString(containers[j]["id"])
	})

	truncated := false
	if len(containers) > limit {
		containers = containers[:limit]
		truncated = true
	}

	summary := fmt.Sprintf("listed %d containers", len(containers))
	output := map[string]any{
		"runtime":     "k8s",
		"simulated":   false,
		"all":         all,
		"limit":       limit,
		"name_filter": nameFilter,
		"count":       len(containers),
		"truncated":   truncated,
		"containers":  containers,
		"namespace":   namespace,
		"summary":     summary,
		"output":      summary,
		"exit_code":   0,
	}
	return containerResult(output, summary, "container-ps-report.json", "container-ps-output.txt"), nil
}

func (h *ContainerRunHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ImageRef string            `json:"image_ref"`
		Command  []string          `json:"command"`
		Env      map[string]string `json:"env"`
		Name     string            `json:"name"`
		Detach   bool              `json:"detach"`
		Remove   bool              `json:"remove"`
		Strict   *bool             `json:"strict"`
	}{
		Detach: true,
		Remove: false,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid container.run args",
				Retryable: false,
			}
		}
	}

	imageRef := strings.TrimSpace(request.ImageRef)
	if imageRef == "" {
		return app.ToolRunResult{}, containerInvalidArgument("image_ref is required")
	}
	if err := validateImageReference(imageRef); err != nil {
		return app.ToolRunResult{}, containerInvalidArgument(err.Error())
	}

	containerName := strings.TrimSpace(request.Name)
	if containerName != "" && !containerNameRe.MatchString(containerName) {
		return app.ToolRunResult{}, containerInvalidArgument("name is invalid")
	}

	envPairs, envErr := sanitizeContainerEnv(request.Env)
	if envErr != nil {
		return app.ToolRunResult{}, envErr
	}
	command, commandErr := sanitizeContainerRunCommand(request.Command)
	if commandErr != nil {
		return app.ToolRunResult{}, commandErr
	}
	strict := resolveContainerStrictFlag(request.Strict)
	if isKubernetesRuntime(session) && h.client != nil {
		return h.invokeK8sRun(ctx, session, imageRef, command, envPairs, containerName, request.Detach, request.Remove)
	}

	runner := ensureRunner(h.runner)
	runtime, probeOutput := detectContainerRuntime(ctx, runner, session)
	if runtime == "" {
		if strict {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "container runtime not available",
				Retryable: false,
			}
		}
		simulatedID := buildSimulatedContainerID(session.ID, imageRef, command, containerName)
		status := "running"
		if !request.Detach {
			status = "exited"
		}
		summary := "container run simulated"
		output := map[string]any{
			"runtime":      "synthetic",
			"simulated":    true,
			"image_ref":    imageRef,
			"name":         containerName,
			"detach":       request.Detach,
			"remove":       request.Remove,
			"command":      command,
			"env":          envPairs,
			"container_id": simulatedID,
			"status":       status,
			"summary":      summary,
			"output":       strings.TrimSpace(probeOutput),
			"exit_code":    0,
		}
		return containerResult(output, strings.TrimSpace(probeOutput), "container-run-report.json", "container-run-output.txt"), nil
	}

	runCommand := buildContainerRunCommand(runtime, imageRef, request.Detach, request.Remove, containerName, envPairs, command)
	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  runCommand[0],
		Args:     runCommand[1:],
		MaxBytes: containerMaxOutputBytes,
	})
	if runErr != nil {
		if !strict {
			simulatedID := buildSimulatedContainerID(session.ID, imageRef, command, containerName)
			status := "running"
			if !request.Detach {
				status = "exited"
			}
			summary := "container run simulated"
			output := map[string]any{
				"runtime":      "synthetic",
				"simulated":    true,
				"image_ref":    imageRef,
				"name":         containerName,
				"detach":       request.Detach,
				"remove":       request.Remove,
				"command":      command,
				"env":          envPairs,
				"container_id": simulatedID,
				"status":       status,
				"summary":      summary,
				"output":       strings.TrimSpace(commandResult.Output),
				"exit_code":    0,
			}
			return containerResult(output, commandResult.Output, "container-run-report.json", "container-run-output.txt"), nil
		}

		result := containerResult(
			map[string]any{
				"runtime":      runtime,
				"simulated":    false,
				"image_ref":    imageRef,
				"name":         containerName,
				"detach":       request.Detach,
				"remove":       request.Remove,
				"command":      command,
				"env":          envPairs,
				"container_id": "",
				"status":       "failed",
				"summary":      "container run failed",
				"output":       strings.TrimSpace(commandResult.Output),
				"exit_code":    commandResult.ExitCode,
			},
			commandResult.Output,
			"container-run-report.json",
			"container-run-output.txt",
		)
		return result, toToolError(runErr, commandResult.Output)
	}

	containerID := parseContainerRunID(commandResult.Output)
	if containerID == "" {
		containerID = buildSimulatedContainerID(session.ID, imageRef, command, containerName)
	}
	status := "running"
	if !request.Detach {
		status = "exited"
	}
	summary := fmt.Sprintf("container started: %s", containerID)
	output := map[string]any{
		"runtime":      runtime,
		"simulated":    false,
		"image_ref":    imageRef,
		"name":         containerName,
		"detach":       request.Detach,
		"remove":       request.Remove,
		"command":      command,
		"env":          envPairs,
		"container_id": containerID,
		"status":       status,
		"summary":      summary,
		"output":       strings.TrimSpace(commandResult.Output),
		"exit_code":    commandResult.ExitCode,
	}
	return containerResult(output, commandResult.Output, "container-run-report.json", "container-run-output.txt"), nil
}

func (h *ContainerLogsHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ContainerID string `json:"container_id"`
		TailLines   int    `json:"tail_lines"`
		SinceSec    int    `json:"since_seconds"`
		Timestamps  bool   `json:"timestamps"`
		Strict      *bool  `json:"strict"`
		MaxBytes    int    `json:"max_bytes"`
	}{
		TailLines: containerDefaultTailLines,
		SinceSec:  0,
		MaxBytes:  containerDefaultMaxLogBytes,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid container.logs args",
				Retryable: false,
			}
		}
	}

	containerID := strings.TrimSpace(request.ContainerID)
	if !validContainerID(containerID) {
		return app.ToolRunResult{}, containerInvalidArgument("container_id is required")
	}

	tailLines := clampInt(request.TailLines, 1, containerMaxTailLines, containerDefaultTailLines)
	sinceSec := clampInt(request.SinceSec, 0, 86400, 0)
	maxBytes := clampInt(request.MaxBytes, 1024, containerMaxOutputBytes, containerDefaultMaxLogBytes)
	strict := resolveContainerStrictFlag(request.Strict)

	if isSimulatedContainerID(containerID) && !strict {
		logs := fmt.Sprintf("simulated logs for %s", containerID)
		output := buildContainerLogsOutput("synthetic", true, containerID, tailLines, sinceSec, request.Timestamps, logs, maxBytes, 0)
		return containerResult(output, logs, "container-logs-report.json", "container-logs-output.txt"), nil
	}
	if isKubernetesRuntime(session) && h.client != nil {
		return h.invokeK8sLogs(ctx, session, containerID, tailLines, sinceSec, request.Timestamps, maxBytes)
	}

	runner := ensureRunner(h.runner)
	runtime, probeOutput := detectContainerRuntime(ctx, runner, session)
	if runtime == "" {
		if strict {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "container runtime not available",
				Retryable: false,
			}
		}
		logs := fmt.Sprintf("simulated logs for %s", containerID)
		output := buildContainerLogsOutput("synthetic", true, containerID, tailLines, sinceSec, request.Timestamps, logs, maxBytes, 0)
		output["output"] = strings.TrimSpace(probeOutput)
		return containerResult(output, logs, "container-logs-report.json", "container-logs-output.txt"), nil
	}

	logsCommand := buildContainerLogsCommand(runtime, containerID, tailLines, sinceSec, request.Timestamps)
	commandResult, runErr := runner.Run(ctx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  logsCommand[0],
		Args:     logsCommand[1:],
		MaxBytes: containerMaxOutputBytes,
	})
	if runErr != nil {
		if !strict {
			logs := fmt.Sprintf("simulated logs for %s", containerID)
			output := buildContainerLogsOutput("synthetic", true, containerID, tailLines, sinceSec, request.Timestamps, logs, maxBytes, 0)
			output["output"] = strings.TrimSpace(commandResult.Output)
			return containerResult(output, logs, "container-logs-report.json", "container-logs-output.txt"), nil
		}
		result := containerResult(
			buildContainerLogsOutput(runtime, false, containerID, tailLines, sinceSec, request.Timestamps, commandResult.Output, maxBytes, commandResult.ExitCode),
			commandResult.Output,
			"container-logs-report.json",
			"container-logs-output.txt",
		)
		return result, toToolError(runErr, commandResult.Output)
	}

	output := buildContainerLogsOutput(runtime, false, containerID, tailLines, sinceSec, request.Timestamps, commandResult.Output, maxBytes, commandResult.ExitCode)
	return containerResult(output, commandResult.Output, "container-logs-report.json", "container-logs-output.txt"), nil
}

func (h *ContainerExecHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ContainerID    string   `json:"container_id"`
		Command        []string `json:"command"`
		TimeoutSeconds int      `json:"timeout_seconds"`
		MaxOutputBytes int      `json:"max_output_bytes"`
		Strict         *bool    `json:"strict"`
	}{
		TimeoutSeconds: containerDefaultTimeoutSec,
		MaxOutputBytes: containerDefaultMaxExecBytes,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid container.exec args",
				Retryable: false,
			}
		}
	}

	containerID := strings.TrimSpace(request.ContainerID)
	if !validContainerID(containerID) {
		return app.ToolRunResult{}, containerInvalidArgument("container_id is required")
	}
	command, commandErr := sanitizeContainerExecCommand(request.Command)
	if commandErr != nil {
		return app.ToolRunResult{}, commandErr
	}
	maxBytes := clampInt(request.MaxOutputBytes, 1024, containerMaxOutputBytes, containerDefaultMaxExecBytes)
	timeoutSec := clampInt(request.TimeoutSeconds, 1, containerMaxTimeoutSec, containerDefaultTimeoutSec)
	strict := resolveContainerStrictFlag(request.Strict)

	if isSimulatedContainerID(containerID) && !strict {
		outputText := fmt.Sprintf("simulated exec in %s: %s", containerID, strings.Join(command, " "))
		output := map[string]any{
			"runtime":         "synthetic",
			"simulated":       true,
			"container_id":    containerID,
			"command":         command,
			"timeout_seconds": timeoutSec,
			"exit_code":       0,
			"summary":         "container exec simulated",
			"output":          outputText,
		}
		return containerResult(output, outputText, "container-exec-report.json", "container-exec-output.txt"), nil
	}
	if isKubernetesRuntime(session) && h.client != nil {
		return h.invokeK8sExec(ctx, session, containerID, command, timeoutSec, maxBytes)
	}

	runner := ensureRunner(h.runner)
	runtime, probeOutput := detectContainerRuntime(ctx, runner, session)
	if runtime == "" {
		if strict {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "container runtime not available",
				Retryable: false,
			}
		}
		outputText := fmt.Sprintf("simulated exec in %s: %s", containerID, strings.Join(command, " "))
		output := map[string]any{
			"runtime":         "synthetic",
			"simulated":       true,
			"container_id":    containerID,
			"command":         command,
			"timeout_seconds": timeoutSec,
			"exit_code":       0,
			"summary":         "container exec simulated",
			"output":          strings.TrimSpace(probeOutput),
		}
		return containerResult(output, outputText, "container-exec-report.json", "container-exec-output.txt"), nil
	}

	execCommand := buildContainerExecCommand(runtime, containerID, command)
	timeoutCtx, cancel := context.WithTimeout(ctx, time.Duration(timeoutSec)*time.Second)
	defer cancel()

	commandResult, runErr := runner.Run(timeoutCtx, session, app.CommandSpec{
		Cwd:      session.WorkspacePath,
		Command:  execCommand[0],
		Args:     execCommand[1:],
		MaxBytes: maxBytes,
	})
	if runErr != nil {
		if !strict {
			outputText := fmt.Sprintf("simulated exec in %s: %s", containerID, strings.Join(command, " "))
			output := map[string]any{
				"runtime":         "synthetic",
				"simulated":       true,
				"container_id":    containerID,
				"command":         command,
				"timeout_seconds": timeoutSec,
				"exit_code":       0,
				"summary":         "container exec simulated",
				"output":          strings.TrimSpace(commandResult.Output),
			}
			return containerResult(output, outputText, "container-exec-report.json", "container-exec-output.txt"), nil
		}
		result := containerResult(
			map[string]any{
				"runtime":         runtime,
				"simulated":       false,
				"container_id":    containerID,
				"command":         command,
				"timeout_seconds": timeoutSec,
				"exit_code":       commandResult.ExitCode,
				"summary":         "container exec failed",
				"output":          strings.TrimSpace(commandResult.Output),
			},
			commandResult.Output,
			"container-exec-report.json",
			"container-exec-output.txt",
		)
		return result, toToolError(runErr, commandResult.Output)
	}

	summary := "container exec completed"
	output := map[string]any{
		"runtime":         runtime,
		"simulated":       false,
		"container_id":    containerID,
		"command":         command,
		"timeout_seconds": timeoutSec,
		"exit_code":       commandResult.ExitCode,
		"summary":         summary,
		"output":          strings.TrimSpace(commandResult.Output),
	}
	return containerResult(output, commandResult.Output, "container-exec-report.json", "container-exec-output.txt"), nil
}

func (h *ContainerRunHandler) invokeK8sRun(
	ctx context.Context,
	session domain.Session,
	imageRef string,
	command []string,
	envPairs []string,
	containerName string,
	detach bool,
	remove bool,
) (app.ToolRunResult, *domain.Error) {
	if err := ensureK8sClient(h.client); err != nil {
		return app.ToolRunResult{}, err
	}

	namespace := resolveK8sNamespace("", session, h.defaultNamespace)
	labels := map[string]string{
		"app":                  "workspace-container-run",
		"workspace_session_id": sanitizeContainerLabelValue(session.ID),
	}
	if tenant := strings.TrimSpace(session.Principal.TenantID); tenant != "" {
		labels["workspace_tenant"] = sanitizeContainerLabelValue(tenant)
	}

	podName := "ws-ctr-" + sanitizeContainerLabelValue(session.ID)
	if strings.TrimSpace(containerName) != "" {
		namePart := strings.ToLower(strings.TrimSpace(containerName))
		namePart = strings.Map(func(r rune) rune {
			if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' {
				return r
			}
			return '-'
		}, namePart)
		namePart = strings.Trim(namePart, "-")
		if namePart != "" {
			podName = "ws-ctr-" + namePart
		}
	}
	if len(podName) > 55 {
		podName = strings.TrimSuffix(podName[:55], "-")
	}
	suffixSeed := session.ID + "|" + imageRef + "|" + strings.Join(command, " ") + "|" + containerName
	suffixHash := sha256.Sum256([]byte(suffixSeed))
	suffix := hex.EncodeToString(suffixHash[:])
	if len(suffix) > 6 {
		suffix = suffix[:6]
	}
	if podName == "" {
		podName = "ws-ctr"
	}
	podName = strings.TrimSuffix(podName, "-") + "-" + suffix

	environment := make([]corev1.EnvVar, 0, len(envPairs))
	for _, pair := range envPairs {
		key, value, found := strings.Cut(pair, "=")
		if !found {
			continue
		}
		environment = append(environment, corev1.EnvVar{Name: key, Value: value})
	}

	runContainer := corev1.Container{
		Name:            "task",
		Image:           imageRef,
		ImagePullPolicy: corev1.PullIfNotPresent,
		Env:             environment,
		SecurityContext: &corev1.SecurityContext{
			AllowPrivilegeEscalation: boolPtr(false),
			ReadOnlyRootFilesystem:   boolPtr(false),
			RunAsNonRoot:             boolPtr(true),
			RunAsUser:                int64Ptr(1000),
			RunAsGroup:               int64Ptr(1000),
			Capabilities: &corev1.Capabilities{
				Drop: []corev1.Capability{"ALL"},
			},
		},
	}
	if len(command) > 0 {
		runContainer.Command = append([]string{}, command...)
	}

	podSpec := corev1.PodSpec{
		RestartPolicy: corev1.RestartPolicyNever,
		Containers:    []corev1.Container{runContainer},
		SecurityContext: &corev1.PodSecurityContext{
			RunAsNonRoot: boolPtr(true),
			RunAsUser:    int64Ptr(1000),
			RunAsGroup:   int64Ptr(1000),
			SeccompProfile: &corev1.SeccompProfile{
				Type: corev1.SeccompProfileTypeRuntimeDefault,
			},
		},
		AutomountServiceAccountToken: boolPtr(false),
	}

	podTemplate := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      podName,
			Namespace: namespace,
			Labels:    labels,
		},
		Spec: podSpec,
	}
	pod, err := h.client.CoreV1().Pods(namespace).Create(ctx, podTemplate, metav1.CreateOptions{})
	if apierrors.IsAlreadyExists(err) {
		retryName := fmt.Sprintf("%s-%d", strings.TrimSuffix(podName, "-"), time.Now().UnixNano()%1000)
		if len(retryName) > 63 {
			retryName = strings.TrimSuffix(retryName[:63], "-")
		}
		podTemplate.ObjectMeta.Name = retryName
		pod, err = h.client.CoreV1().Pods(namespace).Create(ctx, podTemplate, metav1.CreateOptions{})
	}
	if err != nil {
		return app.ToolRunResult{}, k8sExecutionFailed(fmt.Sprintf("k8s container run failed: %v", err), true)
	}

	startedPod, startErr := waitForK8sContainerPodStarted(ctx, h.client, namespace, pod.Name, 30*time.Second)
	if startErr != nil {
		return app.ToolRunResult{}, startErr
	}

	exitCode := 0
	status := strings.ToLower(strings.TrimSpace(string(startedPod.Status.Phase)))
	if status == "" {
		status = "pending"
	}
	if !detach {
		terminalPod, terminalErr := waitForK8sContainerPodTerminal(ctx, h.client, namespace, pod.Name, 120*time.Second)
		if terminalErr != nil {
			return app.ToolRunResult{}, terminalErr
		}
		status = strings.ToLower(strings.TrimSpace(string(terminalPod.Status.Phase)))
		if terminated, ok := firstTerminatedContainerStatus(terminalPod.Status); ok {
			exitCode = int(terminated.ExitCode)
		}
		if remove {
			_ = h.client.CoreV1().Pods(namespace).Delete(ctx, pod.Name, metav1.DeleteOptions{})
		}
	}

	summary := fmt.Sprintf("k8s container pod started: %s/%s", namespace, pod.Name)
	output := map[string]any{
		"runtime":      "k8s",
		"simulated":    false,
		"namespace":    namespace,
		"pod_name":     pod.Name,
		"image_ref":    imageRef,
		"name":         containerName,
		"detach":       detach,
		"remove":       remove,
		"command":      command,
		"env":          envPairs,
		"container_id": pod.Name,
		"status":       status,
		"summary":      summary,
		"output":       summary,
		"exit_code":    exitCode,
	}
	return containerResult(output, summary, "container-run-report.json", "container-run-output.txt"), nil
}

func (h *ContainerLogsHandler) invokeK8sLogs(
	ctx context.Context,
	session domain.Session,
	containerID string,
	tailLines int,
	sinceSec int,
	timestamps bool,
	maxBytes int,
) (app.ToolRunResult, *domain.Error) {
	if err := ensureK8sClient(h.client); err != nil {
		return app.ToolRunResult{}, err
	}

	namespace := resolveK8sNamespace("", session, h.defaultNamespace)
	pod, err := h.client.CoreV1().Pods(namespace).Get(ctx, containerID, metav1.GetOptions{})
	if apierrors.IsNotFound(err) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeNotFound,
			Message:   "container pod not found",
			Retryable: false,
		}
	}
	if err != nil {
		return app.ToolRunResult{}, k8sExecutionFailed(fmt.Sprintf("k8s container logs failed: %v", err), true)
	}

	containerName := resolveK8sRunContainerName(pod)
	options := &corev1.PodLogOptions{
		Container:  containerName,
		Timestamps: timestamps,
	}
	tailLines64 := int64(tailLines)
	options.TailLines = &tailLines64
	if sinceSec > 0 {
		sinceSec64 := int64(sinceSec)
		options.SinceSeconds = &sinceSec64
	}

	stream, streamErr := h.client.CoreV1().Pods(namespace).GetLogs(containerID, options).Stream(ctx)
	if streamErr != nil {
		return app.ToolRunResult{}, k8sExecutionFailed(fmt.Sprintf("k8s container logs failed: %v", streamErr), true)
	}
	defer stream.Close()

	rawLogs, readErr := io.ReadAll(stream)
	if readErr != nil {
		return app.ToolRunResult{}, k8sExecutionFailed(fmt.Sprintf("k8s container logs failed: %v", readErr), true)
	}

	logText := string(rawLogs)
	output := buildContainerLogsOutput("k8s", false, containerID, tailLines, sinceSec, timestamps, logText, maxBytes, 0)
	output["namespace"] = namespace
	output["pod_name"] = containerID
	output["container"] = containerName
	output["source"] = "k8s_sdk"
	return containerResult(output, logText, "container-logs-report.json", "container-logs-output.txt"), nil
}

func (h *ContainerExecHandler) invokeK8sExec(
	ctx context.Context,
	session domain.Session,
	containerID string,
	command []string,
	timeoutSec int,
	maxBytes int,
) (app.ToolRunResult, *domain.Error) {
	if err := ensureK8sClient(h.client); err != nil {
		return app.ToolRunResult{}, err
	}

	namespace := resolveK8sNamespace("", session, h.defaultNamespace)
	pod, err := h.client.CoreV1().Pods(namespace).Get(ctx, containerID, metav1.GetOptions{})
	if apierrors.IsNotFound(err) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeNotFound,
			Message:   "container pod not found",
			Retryable: false,
		}
	}
	if err != nil {
		return app.ToolRunResult{}, k8sExecutionFailed(fmt.Sprintf("k8s container exec failed: %v", err), true)
	}
	if pod.Status.Phase != corev1.PodRunning {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   fmt.Sprintf("container pod is not running (phase=%s)", strings.ToLower(string(pod.Status.Phase))),
			Retryable: false,
		}
	}

	containerName := resolveK8sRunContainerName(pod)
	runner := ensureRunner(h.runner)
	execSession := session
	execSession.Runtime.Kind = domain.RuntimeKindKubernetes
	execSession.Runtime.Namespace = namespace
	execSession.Runtime.PodName = containerID
	execSession.Runtime.Container = containerName
	execSession.Runtime.Workdir = "/"

	timeoutCtx, cancel := context.WithTimeout(ctx, time.Duration(timeoutSec)*time.Second)
	defer cancel()

	commandResult, runErr := runner.Run(timeoutCtx, execSession, app.CommandSpec{
		Cwd:      "",
		Command:  command[0],
		Args:     command[1:],
		MaxBytes: maxBytes,
	})
	if runErr != nil {
		result := containerResult(
			map[string]any{
				"runtime":         "k8s",
				"simulated":       false,
				"namespace":       namespace,
				"pod_name":        containerID,
				"container":       containerName,
				"container_id":    containerID,
				"command":         command,
				"timeout_seconds": timeoutSec,
				"exit_code":       commandResult.ExitCode,
				"summary":         "container exec failed",
				"output":          strings.TrimSpace(commandResult.Output),
			},
			commandResult.Output,
			"container-exec-report.json",
			"container-exec-output.txt",
		)
		return result, toToolError(runErr, commandResult.Output)
	}

	output := map[string]any{
		"runtime":         "k8s",
		"simulated":       false,
		"namespace":       namespace,
		"pod_name":        containerID,
		"container":       containerName,
		"container_id":    containerID,
		"command":         command,
		"timeout_seconds": timeoutSec,
		"exit_code":       commandResult.ExitCode,
		"summary":         "container exec completed",
		"output":          strings.TrimSpace(commandResult.Output),
	}
	return containerResult(output, commandResult.Output, "container-exec-report.json", "container-exec-output.txt"), nil
}

func waitForK8sContainerPodStarted(
	ctx context.Context,
	client kubernetes.Interface,
	namespace string,
	podName string,
	timeout time.Duration,
) (*corev1.Pod, *domain.Error) {
	deadlineCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	for {
		pod, err := client.CoreV1().Pods(namespace).Get(deadlineCtx, podName, metav1.GetOptions{})
		if apierrors.IsNotFound(err) {
			select {
			case <-deadlineCtx.Done():
				return nil, k8sExecutionFailed("k8s container pod did not become ready before timeout", false)
			case <-ticker.C:
				continue
			}
		}
		if err != nil {
			return nil, k8sExecutionFailed(fmt.Sprintf("k8s container run failed: %v", err), true)
		}
		switch pod.Status.Phase {
		case corev1.PodRunning, corev1.PodSucceeded:
			return pod, nil
		case corev1.PodFailed:
			return nil, k8sExecutionFailed("k8s container pod failed to start", false)
		}

		select {
		case <-deadlineCtx.Done():
			return nil, k8sExecutionFailed("k8s container pod did not become ready before timeout", false)
		case <-ticker.C:
		}
	}
}

func waitForK8sContainerPodTerminal(
	ctx context.Context,
	client kubernetes.Interface,
	namespace string,
	podName string,
	timeout time.Duration,
) (*corev1.Pod, *domain.Error) {
	deadlineCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()

	for {
		pod, err := client.CoreV1().Pods(namespace).Get(deadlineCtx, podName, metav1.GetOptions{})
		if err != nil {
			return nil, k8sExecutionFailed(fmt.Sprintf("k8s container wait failed: %v", err), true)
		}
		if pod.Status.Phase == corev1.PodSucceeded || pod.Status.Phase == corev1.PodFailed {
			return pod, nil
		}
		select {
		case <-deadlineCtx.Done():
			return nil, k8sExecutionFailed("k8s container pod did not complete before timeout", false)
		case <-ticker.C:
		}
	}
}

func resolveK8sRunContainerName(pod *corev1.Pod) string {
	if pod == nil {
		return "task"
	}
	for _, container := range pod.Spec.Containers {
		if strings.TrimSpace(container.Name) == "task" {
			return "task"
		}
	}
	if len(pod.Spec.Containers) > 0 {
		name := strings.TrimSpace(pod.Spec.Containers[0].Name)
		if name != "" {
			return name
		}
	}
	return "task"
}

func firstTerminatedContainerStatus(status corev1.PodStatus) (corev1.ContainerStateTerminated, bool) {
	for _, containerStatus := range status.ContainerStatuses {
		if containerStatus.State.Terminated != nil {
			return *containerStatus.State.Terminated, true
		}
	}
	return corev1.ContainerStateTerminated{}, false
}

func detectContainerRuntime(ctx context.Context, runner app.CommandRunner, session domain.Session) (string, string) {
	probeOutputs := make([]string, 0, len(containerRuntimeProbes))
	for _, probe := range containerRuntimeProbes {
		result, err := runner.Run(ctx, session, app.CommandSpec{
			Cwd:      session.WorkspacePath,
			Command:  probe.Runtime,
			Args:     probe.Args,
			MaxBytes: 64 * 1024,
		})
		if err == nil && result.ExitCode == 0 {
			return probe.Runtime, result.Output
		}
		if strings.TrimSpace(result.Output) != "" {
			probeOutputs = append(probeOutputs, fmt.Sprintf("%s: %s", probe.Runtime, strings.TrimSpace(result.Output)))
		}
	}
	return "", strings.Join(probeOutputs, "\n")
}

func buildContainerPSCommand(runtime string, all bool, nameFilter string) []string {
	command := []string{runtime, "ps"}
	if all {
		command = append(command, "-a")
	}
	if strings.TrimSpace(nameFilter) != "" {
		command = append(command, "--filter", "name="+strings.TrimSpace(nameFilter))
	}
	command = append(command, "--format", "{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}")
	return command
}

func buildContainerRunCommand(runtime string, imageRef string, detach bool, remove bool, containerName string, envPairs []string, command []string) []string {
	out := []string{runtime, "run"}
	if detach {
		out = append(out, "-d")
	}
	if remove {
		out = append(out, "--rm")
	}
	if strings.TrimSpace(containerName) != "" {
		out = append(out, "--name", strings.TrimSpace(containerName))
	}
	for _, pair := range envPairs {
		out = append(out, "-e", pair)
	}
	out = append(out, imageRef)
	out = append(out, command...)
	return out
}

func buildContainerLogsCommand(runtime string, containerID string, tailLines int, sinceSec int, timestamps bool) []string {
	out := []string{runtime, "logs", "--tail", fmt.Sprintf("%d", tailLines)}
	if sinceSec > 0 {
		out = append(out, "--since", fmt.Sprintf("%ds", sinceSec))
	}
	if timestamps {
		out = append(out, "--timestamps")
	}
	out = append(out, containerID)
	return out
}

func buildContainerExecCommand(runtime string, containerID string, command []string) []string {
	out := []string{runtime, "exec", containerID}
	out = append(out, command...)
	return out
}

func parseContainerPSOutput(raw string) []map[string]any {
	lines := strings.Split(strings.TrimSpace(raw), "\n")
	out := make([]map[string]any, 0, len(lines))
	for _, rawLine := range lines {
		line := strings.TrimSpace(rawLine)
		if line == "" {
			continue
		}
		if strings.HasPrefix(strings.ToUpper(line), "CONTAINER ID") {
			continue
		}
		if strings.Contains(line, "\t") {
			parts := strings.SplitN(line, "\t", 4)
			if len(parts) < 4 {
				continue
			}
			id := strings.TrimSpace(parts[0])
			if id == "" {
				continue
			}
			out = append(out, map[string]any{
				"id":     id,
				"image":  strings.TrimSpace(parts[1]),
				"name":   strings.TrimSpace(parts[2]),
				"status": strings.TrimSpace(parts[3]),
			})
			continue
		}

		fields := strings.Fields(line)
		if len(fields) < 4 {
			continue
		}
		id := strings.TrimSpace(fields[0])
		if id == "" {
			continue
		}
		name := strings.TrimSpace(fields[len(fields)-1])
		status := strings.TrimSpace(strings.Join(fields[2:len(fields)-1], " "))
		out = append(out, map[string]any{
			"id":     id,
			"image":  strings.TrimSpace(fields[1]),
			"name":   name,
			"status": status,
		})
	}
	sort.Slice(out, func(i, j int) bool {
		return asString(out[i]["id"]) < asString(out[j]["id"])
	})
	return out
}

func parseContainerRunID(raw string) string {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return ""
	}
	firstLine := strings.Split(trimmed, "\n")[0]
	firstToken := strings.Fields(strings.TrimSpace(firstLine))
	if len(firstToken) == 0 {
		return ""
	}
	candidate := strings.TrimSpace(firstToken[0])
	if validContainerID(candidate) {
		return candidate
	}
	return ""
}

func sanitizeContainerRunCommand(command []string) ([]string, *domain.Error) {
	if len(command) == 0 {
		return []string{}, nil
	}
	if len(command) > containerMaxRunCommandArgs {
		return nil, containerInvalidArgument("command exceeds allowed arguments")
	}
	out := make([]string, 0, len(command))
	for _, arg := range command {
		trimmed := strings.TrimSpace(arg)
		if trimmed == "" {
			return nil, containerInvalidArgument("command contains empty argument")
		}
		if len(trimmed) > containerMaxCommandArgLength {
			return nil, containerInvalidArgument("command argument exceeds maximum length")
		}
		if strings.Contains(trimmed, "\n") || strings.Contains(trimmed, "\r") {
			return nil, containerInvalidArgument("command contains invalid characters")
		}
		out = append(out, trimmed)
	}
	return out, nil
}

func sanitizeContainerExecCommand(command []string) ([]string, *domain.Error) {
	if len(command) == 0 {
		return nil, containerInvalidArgument("command is required")
	}
	if len(command) > containerMaxExecCommandArgs {
		return nil, containerInvalidArgument("command exceeds allowed arguments")
	}

	out, err := sanitizeContainerRunCommand(command)
	if err != nil {
		return nil, err
	}
	if len(out) == 0 {
		return nil, containerInvalidArgument("command is required")
	}

	executable := normalizeExecCommandName(out[0])
	if containerExecDeniedCommands[executable] {
		return nil, containerInvalidArgument("command is not allowed")
	}
	if !containerExecAllowedCommands[executable] {
		return nil, containerInvalidArgument("command is not allowlisted")
	}
	return out, nil
}

func resolveContainerStrictFlag(requested *bool) bool {
	if !containerSyntheticFallbackEnabled() {
		return true
	}
	if requested != nil {
		return *requested
	}
	return envBool("WORKSPACE_CONTAINER_STRICT_BY_DEFAULT", true)
}

func containerSyntheticFallbackEnabled() bool {
	return envBool("WORKSPACE_CONTAINER_ALLOW_SYNTHETIC_FALLBACK", true)
}

func envBool(name string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(name)))
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	case "":
		return fallback
	default:
		return fallback
	}
}

func sanitizeContainerEnv(raw map[string]string) ([]string, *domain.Error) {
	if len(raw) == 0 {
		return []string{}, nil
	}
	if len(raw) > containerMaxRunEnvVars {
		return nil, containerInvalidArgument("env exceeds maximum variables")
	}

	keys := make([]string, 0, len(raw))
	for key := range raw {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	out := make([]string, 0, len(keys))
	for _, key := range keys {
		trimmedKey := strings.TrimSpace(key)
		if !envKeyRe.MatchString(trimmedKey) {
			return nil, containerInvalidArgument("env key is invalid")
		}
		value := raw[key]
		if strings.Contains(value, "\n") || strings.Contains(value, "\r") {
			return nil, containerInvalidArgument("env value contains invalid characters")
		}
		if len(value) > containerMaxCommandArgLength {
			return nil, containerInvalidArgument("env value exceeds maximum length")
		}
		out = append(out, trimmedKey+"="+value)
	}
	return out, nil
}

func buildContainerLogsOutput(runtime string, simulated bool, containerID string, tailLines int, sinceSec int, timestamps bool, raw string, maxBytes int, exitCode int) map[string]any {
	truncated := false
	trimmed := []byte(raw)
	if len(trimmed) > maxBytes {
		trimmed = truncate(trimmed, maxBytes)
		truncated = true
	}
	logText := string(trimmed)
	lineCount := 0
	if strings.TrimSpace(logText) != "" {
		lineCount = strings.Count(logText, "\n") + 1
	}
	summary := fmt.Sprintf("retrieved logs for container %s", containerID)
	return map[string]any{
		"runtime":       runtime,
		"simulated":     simulated,
		"container_id":  containerID,
		"tail_lines":    tailLines,
		"since_seconds": sinceSec,
		"timestamps":    timestamps,
		"bytes":         len(trimmed),
		"line_count":    lineCount,
		"truncated":     truncated,
		"logs":          logText,
		"summary":       summary,
		"output":        summary,
		"exit_code":     exitCode,
	}
}

func validContainerID(containerID string) bool {
	return containerIDRe.MatchString(strings.TrimSpace(containerID))
}

func isSimulatedContainerID(containerID string) bool {
	return strings.HasPrefix(strings.TrimSpace(containerID), "sim-")
}

func buildSimulatedContainerID(sessionID string, imageRef string, command []string, name string) string {
	joined := sessionID + "|" + imageRef + "|" + strings.Join(command, " ") + "|" + name
	hash := sha256.Sum256([]byte(joined))
	encoded := hex.EncodeToString(hash[:])
	if len(encoded) > 12 {
		encoded = encoded[:12]
	}
	return "sim-" + encoded
}

func normalizeExecCommandName(raw string) string {
	trimmed := strings.TrimSpace(raw)
	trimmed = strings.TrimPrefix(trimmed, "/usr/bin/")
	trimmed = strings.TrimPrefix(trimmed, "/bin/")
	trimmed = strings.TrimPrefix(trimmed, "/usr/local/bin/")
	parts := strings.Split(trimmed, "/")
	if len(parts) == 0 {
		return ""
	}
	return strings.ToLower(strings.TrimSpace(parts[len(parts)-1]))
}

func containsArg(args []string, target string) bool {
	target = strings.TrimSpace(target)
	for _, arg := range args {
		if strings.TrimSpace(arg) == target {
			return true
		}
	}
	return false
}

func shouldFallbackToContainerSimulation(output string) bool {
	lower := strings.ToLower(strings.TrimSpace(output))
	if lower == "" {
		return false
	}
	for _, pattern := range containerRuntimeFallbackErrors {
		if strings.Contains(lower, pattern) {
			return true
		}
	}
	return false
}

func boolPtr(value bool) *bool {
	return &value
}

func sanitizeContainerLabelValue(raw string) string {
	normalized := strings.ToLower(strings.TrimSpace(raw))
	if normalized == "" {
		return "unknown"
	}
	builder := strings.Builder{}
	builder.Grow(len(normalized))
	for _, r := range normalized {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' || r == '.' || r == '_' {
			builder.WriteRune(r)
			continue
		}
		builder.WriteRune('-')
	}
	value := strings.Trim(builder.String(), "-._")
	if value == "" {
		value = "unknown"
	}
	if len(value) > 63 {
		value = strings.Trim(value[:63], "-._")
	}
	if value == "" {
		return "unknown"
	}
	return value
}

func containerResult(output map[string]any, rawOutput string, reportName string, outputName string) app.ToolRunResult {
	summary := asString(output["summary"])
	reportBytes, marshalErr := json.MarshalIndent(output, "", "  ")
	artifacts := []app.ArtifactPayload{
		{
			Name:        reportName,
			ContentType: "application/json",
			Data:        reportBytes,
		},
	}
	if strings.TrimSpace(rawOutput) != "" {
		artifacts = append(artifacts, app.ArtifactPayload{
			Name:        outputName,
			ContentType: "text/plain",
			Data:        []byte(rawOutput),
		})
	}
	if marshalErr != nil {
		artifacts = []app.ArtifactPayload{}
	}

	exitCode := 0
	if value, ok := output["exit_code"].(int); ok {
		exitCode = value
	}
	if strings.TrimSpace(summary) == "" {
		summary = "container tool completed"
	}
	return app.ToolRunResult{
		ExitCode:  exitCode,
		Logs:      []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: summary}},
		Output:    output,
		Artifacts: artifacts,
	}
}

func containerInvalidArgument(message string) *domain.Error {
	return &domain.Error{
		Code:      app.ErrorCodeInvalidArgument,
		Message:   message,
		Retryable: false,
	}
}
