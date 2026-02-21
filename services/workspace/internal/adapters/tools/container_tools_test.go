package tools

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
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
