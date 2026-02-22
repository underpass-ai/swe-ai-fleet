package tools

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	k8sruntime "k8s.io/apimachinery/pkg/runtime"
	k8sfake "k8s.io/client-go/kubernetes/fake"
	k8stesting "k8s.io/client-go/testing"
)

type fakeContainerRunner struct {
	calls []app.CommandSpec
	run   func(callIndex int, spec app.CommandSpec) (app.CommandResult, error)
}

func (f *fakeContainerRunner) Run(_ context.Context, _ domain.Session, spec app.CommandSpec) (app.CommandResult, error) {
	f.calls = append(f.calls, spec)
	if f.run != nil {
		return f.run(len(f.calls)-1, spec)
	}
	return app.CommandResult{ExitCode: 0}, nil
}

func TestContainerPSHandler_SimulatedWhenRuntimeUnavailable(t *testing.T) {
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 1, Output: "cannot connect to runtime"}, errors.New("exit status 1")
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerPSHandler(runner)
	result, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"limit":25,"strict":false}`))
	if err != nil {
		t.Fatalf("unexpected container.ps error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["simulated"] != true || output["runtime"] != "synthetic" {
		t.Fatalf("expected simulated synthetic output, got %#v", output)
	}
	if output["count"] != 0 {
		t.Fatalf("expected count=0, got %#v", output["count"])
	}
}

func TestContainerPSHandler_RuntimeAndTruncation(t *testing.T) {
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command == "podman" && len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 0, Output: "{}"}, nil
			}
			if spec.Command == "podman" && len(spec.Args) > 0 && spec.Args[0] == "ps" {
				return app.CommandResult{ExitCode: 0, Output: "b123\timg-b\tb\trunning\na123\timg-a\ta\texited"}, nil
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerPSHandler(runner)
	result, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"limit":1}`))
	if err != nil {
		t.Fatalf("unexpected container.ps error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["runtime"] != "podman" || output["simulated"] != false {
		t.Fatalf("expected podman runtime output, got %#v", output)
	}
	if output["count"] != 1 || output["truncated"] != true {
		t.Fatalf("expected count=1 truncated=true, got %#v", output)
	}
	containers := output["containers"].([]map[string]any)
	if len(containers) != 1 || containers[0]["id"] != "a123" {
		t.Fatalf("expected sorted/truncated containers, got %#v", containers)
	}
}

func TestContainerRunHandler_StrictNoRuntimeFails(t *testing.T) {
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 1, Output: "no runtime"}, errors.New("exit status 1")
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerRunHandler(runner)
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"image_ref":"busybox:1.36","strict":true}`))
	if err == nil {
		t.Fatal("expected strict runtime failure")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution_failed, got %s", err.Code)
	}
}

func TestContainerRunHandler_UsesRuntime(t *testing.T) {
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command == "podman" && len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 0, Output: "{}"}, nil
			}
			if spec.Command == "podman" && len(spec.Args) > 0 && spec.Args[0] == "run" {
				if !containsArg(spec.Args, "-d") {
					t.Fatalf("expected detach flag in run args: %#v", spec.Args)
				}
				return app.CommandResult{ExitCode: 0, Output: "abc123def456\n"}, nil
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerRunHandler(runner)
	result, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir(), ID: "s1"}, json.RawMessage(`{"image_ref":"busybox:1.36","command":["echo","ok"]}`))
	if err != nil {
		t.Fatalf("unexpected container.run error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["runtime"] != "podman" || output["simulated"] != false {
		t.Fatalf("expected podman runtime output, got %#v", output)
	}
	if output["container_id"] != "abc123def456" {
		t.Fatalf("unexpected container_id: %#v", output["container_id"])
	}
}

func TestContainerLogsHandler_SimulatedID(t *testing.T) {
	handler := NewContainerLogsHandler(nil)
	result, err := handler.Invoke(context.Background(), domain.Session{}, json.RawMessage(`{"container_id":"sim-123456","strict":false}`))
	if err != nil {
		t.Fatalf("unexpected container.logs error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["simulated"] != true {
		t.Fatalf("expected simulated logs output, got %#v", output)
	}
	if !strings.Contains(output["logs"].(string), "simulated logs") {
		t.Fatalf("expected simulated logs text, got %#v", output["logs"])
	}
}

func TestContainerExecHandler_DeniesDisallowedCommand(t *testing.T) {
	handler := NewContainerExecHandler(nil)
	_, err := handler.Invoke(context.Background(), domain.Session{}, json.RawMessage(`{"container_id":"sim-123456","command":["rm","-rf","/"]}`))
	if err == nil {
		t.Fatal("expected command denial")
	}
	if err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid_argument, got %s", err.Code)
	}
}

func TestContainerExecHandler_UsesRuntime(t *testing.T) {
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command == "podman" && len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 0, Output: "{}"}, nil
			}
			if spec.Command == "podman" && len(spec.Args) > 0 && spec.Args[0] == "exec" {
				return app.CommandResult{ExitCode: 0, Output: "hello from container"}, nil
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerExecHandler(runner)
	result, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"container_id":"abc123","command":["echo","hello"],"strict":true}`))
	if err != nil {
		t.Fatalf("unexpected container.exec error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["runtime"] != "podman" || output["simulated"] != false {
		t.Fatalf("expected podman runtime output, got %#v", output)
	}
	if !strings.Contains(output["output"].(string), "hello") {
		t.Fatalf("unexpected exec output: %#v", output["output"])
	}
}

func TestContainerRunHandler_UsesKubernetesPodRuntime(t *testing.T) {
	client := k8sfake.NewSimpleClientset()
	client.Fake.PrependReactor("get", "pods", func(action k8stesting.Action) (bool, k8sruntime.Object, error) {
		getAction, ok := action.(k8stesting.GetAction)
		if !ok {
			return false, nil, nil
		}
		obj, err := client.Tracker().Get(corev1.SchemeGroupVersion.WithResource("pods"), getAction.GetNamespace(), getAction.GetName())
		if err != nil {
			return true, nil, err
		}
		pod, ok := obj.(*corev1.Pod)
		if !ok {
			return true, obj, nil
		}
		copy := pod.DeepCopy()
		if copy.Status.Phase == "" {
			copy.Status.Phase = corev1.PodRunning
		}
		return true, copy, nil
	})

	handler := NewContainerRunHandlerWithKubernetes(nil, client, "sandbox")
	session := domain.Session{
		ID:        "session-k8s-run",
		Principal: domain.Principal{TenantID: "tenant-a"},
		Runtime: domain.RuntimeRef{
			Kind:      domain.RuntimeKindKubernetes,
			Namespace: "sandbox",
		},
	}

	result, err := handler.Invoke(
		context.Background(),
		session,
		json.RawMessage(`{"image_ref":"busybox:1.36","command":["sleep","5"],"detach":true}`),
	)
	if err != nil {
		t.Fatalf("unexpected container.run k8s error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["runtime"] != "k8s" || output["simulated"] != false {
		t.Fatalf("expected k8s runtime output, got %#v", output)
	}
	containerID := strings.TrimSpace(asString(output["container_id"]))
	if containerID == "" {
		t.Fatalf("expected non-empty container_id, got %#v", output["container_id"])
	}
	if output["namespace"] != "sandbox" {
		t.Fatalf("expected sandbox namespace, got %#v", output["namespace"])
	}

	pod, getErr := client.CoreV1().Pods("sandbox").Get(context.Background(), containerID, metav1.GetOptions{})
	if getErr != nil {
		t.Fatalf("expected created pod %s: %v", containerID, getErr)
	}
	if len(pod.Spec.Containers) != 1 || pod.Spec.Containers[0].Name != "task" {
		t.Fatalf("unexpected pod container spec: %#v", pod.Spec.Containers)
	}
	if pod.Spec.Containers[0].Image != "busybox:1.36" {
		t.Fatalf("unexpected pod image: %#v", pod.Spec.Containers[0].Image)
	}
	if strings.Join(pod.Spec.Containers[0].Command, " ") != "sleep 5" {
		t.Fatalf("unexpected pod command: %#v", pod.Spec.Containers[0].Command)
	}
}

func TestContainerPSHandler_UsesKubernetesPodRuntime(t *testing.T) {
	client := k8sfake.NewSimpleClientset(
		&corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "ws-ctr-alpha",
				Namespace: "sandbox",
				Labels: map[string]string{
					"app":                  "workspace-container-run",
					"workspace_session_id": "session-k8s-ps",
				},
			},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "task", Image: "busybox:1.36"}},
			},
			Status: corev1.PodStatus{Phase: corev1.PodRunning},
		},
		&corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "ws-ctr-bravo",
				Namespace: "sandbox",
				Labels: map[string]string{
					"app":                  "workspace-container-run",
					"workspace_session_id": "session-k8s-ps",
				},
			},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "task", Image: "busybox:1.36"}},
			},
			Status: corev1.PodStatus{Phase: corev1.PodSucceeded},
		},
		&corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "ws-ctr-other",
				Namespace: "sandbox",
				Labels: map[string]string{
					"app":                  "workspace-container-run",
					"workspace_session_id": "other-session",
				},
			},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "task", Image: "busybox:1.36"}},
			},
			Status: corev1.PodStatus{Phase: corev1.PodRunning},
		},
	)
	handler := NewContainerPSHandlerWithKubernetes(nil, client, "sandbox")
	session := domain.Session{
		ID: "session-k8s-ps",
		Runtime: domain.RuntimeRef{
			Kind:      domain.RuntimeKindKubernetes,
			Namespace: "sandbox",
		},
	}

	result, err := handler.Invoke(
		context.Background(),
		session,
		json.RawMessage(`{"all":false,"limit":20,"strict":true}`),
	)
	if err != nil {
		t.Fatalf("unexpected container.ps k8s error: %#v", err)
	}
	output := result.Output.(map[string]any)
	if output["runtime"] != "k8s" || output["simulated"] != false {
		t.Fatalf("expected k8s runtime output, got %#v", output)
	}
	if output["count"] != 1 {
		t.Fatalf("expected one running container for session, got %#v", output["count"])
	}
	containers, ok := output["containers"].([]map[string]any)
	if !ok {
		t.Fatalf("expected []map output containers, got %#v", output["containers"])
	}
	if len(containers) != 1 || containers[0]["id"] != "ws-ctr-alpha" {
		t.Fatalf("unexpected containers list: %#v", containers)
	}
	if containers[0]["status"] != "running" {
		t.Fatalf("unexpected container status: %#v", containers[0]["status"])
	}
}

func TestContainerExecHandler_UsesKubernetesPodRuntime(t *testing.T) {
	client := k8sfake.NewSimpleClientset(
		&corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{Name: "ctr-pod", Namespace: "sandbox"},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "task", Image: "busybox:1.36"}},
			},
			Status: corev1.PodStatus{
				Phase: corev1.PodRunning,
			},
		},
	)
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "echo" || len(spec.Args) != 1 || spec.Args[0] != "ok" {
				t.Fatalf("unexpected exec command spec: %#v", spec)
			}
			if spec.Cwd != "" {
				t.Fatalf("expected empty cwd for k8s exec, got %#v", spec.Cwd)
			}
			return app.CommandResult{ExitCode: 0, Output: "ok"}, nil
		},
	}
	handler := NewContainerExecHandlerWithKubernetes(runner, client, "sandbox")
	session := domain.Session{
		WorkspacePath: "/tmp/workspace",
		Runtime: domain.RuntimeRef{
			Kind:      domain.RuntimeKindKubernetes,
			Namespace: "sandbox",
		},
	}

	result, err := handler.Invoke(
		context.Background(),
		session,
		json.RawMessage(`{"container_id":"ctr-pod","command":["echo","ok"],"strict":true}`),
	)
	if err != nil {
		t.Fatalf("unexpected container.exec k8s error: %#v", err)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}
	output := result.Output.(map[string]any)
	if output["runtime"] != "k8s" || output["simulated"] != false {
		t.Fatalf("expected k8s runtime output, got %#v", output)
	}
	if output["pod_name"] != "ctr-pod" {
		t.Fatalf("unexpected pod_name: %#v", output["pod_name"])
	}
	if !strings.Contains(output["output"].(string), "ok") {
		t.Fatalf("unexpected exec output: %#v", output["output"])
	}
}

func TestContainerPSHandler_StrictByDefaultEnvFailsWithoutRuntime(t *testing.T) {
	t.Setenv("WORKSPACE_CONTAINER_STRICT_BY_DEFAULT", "true")
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 1, Output: "cannot connect to runtime"}, errors.New("exit status 1")
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerPSHandler(runner)
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"limit":25}`))
	if err == nil {
		t.Fatal("expected strict-by-default runtime failure")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution_failed, got %s", err.Code)
	}
}

func TestContainerPSHandler_SyntheticFallbackDisabledEnvForcesStrict(t *testing.T) {
	t.Setenv("WORKSPACE_CONTAINER_ALLOW_SYNTHETIC_FALLBACK", "false")
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 1, Output: "cannot connect to runtime"}, errors.New("exit status 1")
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerPSHandler(runner)
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"limit":25,"strict":false}`))
	if err == nil {
		t.Fatal("expected runtime failure when synthetic fallback disabled")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution_failed, got %s", err.Code)
	}
}

func TestContainerLogsHandler_SyntheticFallbackDisabledEnvForcesStrict(t *testing.T) {
	t.Setenv("WORKSPACE_CONTAINER_ALLOW_SYNTHETIC_FALLBACK", "false")
	runner := &fakeContainerRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if len(spec.Args) > 0 && spec.Args[0] == "info" {
				return app.CommandResult{ExitCode: 1, Output: "cannot connect to runtime"}, errors.New("exit status 1")
			}
			return app.CommandResult{ExitCode: 1}, errors.New("unexpected command")
		},
	}

	handler := NewContainerLogsHandler(runner)
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"container_id":"sim-123456","strict":false}`))
	if err == nil {
		t.Fatal("expected runtime failure when synthetic fallback disabled")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution_failed, got %s", err.Code)
	}
}

func TestContainerExecHandler_DeniesShellCommands(t *testing.T) {
	handler := NewContainerExecHandler(nil)
	_, err := handler.Invoke(context.Background(), domain.Session{}, json.RawMessage(`{"container_id":"sim-123456","command":["sh","-c","echo hello"]}`))
	if err == nil {
		t.Fatal("expected shell command denial")
	}
	if err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid_argument, got %s", err.Code)
	}
}

func TestContainerHandlerNames(t *testing.T) {
	if NewContainerPSHandler(nil).Name() != "container.ps" {
		t.Fatal("unexpected container.ps name")
	}
	if NewContainerLogsHandler(nil).Name() != "container.logs" {
		t.Fatal("unexpected container.logs name")
	}
	if NewContainerRunHandler(nil).Name() != "container.run" {
		t.Fatal("unexpected container.run name")
	}
	if NewContainerExecHandler(nil).Name() != "container.exec" {
		t.Fatal("unexpected container.exec name")
	}
}
