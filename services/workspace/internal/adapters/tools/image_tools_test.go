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

type fakeImageCommandRunner struct {
	calls []app.CommandSpec
	run   func(callIndex int, spec app.CommandSpec) (app.CommandResult, error)
}

func (f *fakeImageCommandRunner) Run(_ context.Context, _ domain.Session, spec app.CommandSpec) (app.CommandResult, error) {
	f.calls = append(f.calls, spec)
	if f.run != nil {
		return f.run(len(f.calls)-1, spec)
	}
	return app.CommandResult{ExitCode: 0, Output: ""}, nil
}

func TestImageInspectHandler_Dockerfile(t *testing.T) {
	dockerfile := "FROM alpine:latest\nRUN curl -fsSL https://example.com/install.sh | sh\nUSER app\nEXPOSE 8080\n"
	runner := &fakeImageCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			if callIndex != 0 {
				t.Fatalf("unexpected call index: %d", callIndex)
			}
			if spec.Command != "cat" {
				t.Fatalf("expected cat command, got %q", spec.Command)
			}
			if len(spec.Args) != 1 || spec.Args[0] != "Dockerfile" {
				t.Fatalf("unexpected cat args: %#v", spec.Args)
			}
			return app.CommandResult{ExitCode: 0, Output: dockerfile}, nil
		},
	}
	handler := NewImageInspectHandler(runner)
	session := domain.Session{WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"context_path":".","dockerfile_path":"Dockerfile","max_issues":20}`))
	if err != nil {
		t.Fatalf("unexpected image.inspect error: %#v", err)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one command call, got %d", len(runner.calls))
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["source_type"] != "dockerfile" {
		t.Fatalf("expected dockerfile source type, got %#v", output["source_type"])
	}
	if output["stages_count"] != 1 {
		t.Fatalf("expected stages_count=1, got %#v", output["stages_count"])
	}
	if output["issues_count"] == 0 {
		t.Fatalf("expected issues_count > 0, got %#v", output["issues_count"])
	}
}

func TestImageInspectHandler_ImageRef(t *testing.T) {
	runner := &fakeImageCommandRunner{}
	handler := NewImageInspectHandler(runner)
	session := domain.Session{WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"image_ref":"ghcr.io/acme/api:latest"}`))
	if err != nil {
		t.Fatalf("unexpected image.inspect image_ref error: %#v", err)
	}
	if len(runner.calls) != 0 {
		t.Fatalf("expected no command calls in image_ref mode, got %d", len(runner.calls))
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["source_type"] != "image_ref" {
		t.Fatalf("expected image_ref source type, got %#v", output["source_type"])
	}
	if output["registry"] != "ghcr.io" {
		t.Fatalf("expected registry ghcr.io, got %#v", output["registry"])
	}
	if output["issues_count"] == 0 {
		t.Fatalf("expected at least one issue for latest tag, got %#v", output["issues_count"])
	}
}

func TestImageBuildHandler_UsesBuilderWhenAvailable(t *testing.T) {
	digest := "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	runner := &fakeImageCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			switch spec.Command {
			case "cat":
				return app.CommandResult{
					ExitCode: 0,
					Output:   "FROM alpine:3.20\nRUN echo ok\nUSER app\n",
				}, nil
			case "buildah":
				if len(spec.Args) > 0 && spec.Args[0] == "version" {
					return app.CommandResult{ExitCode: 0, Output: "buildah version 1.36.0"}, nil
				}
				return app.CommandResult{
					ExitCode: 0,
					Output:   "STEP 1/2\nSTEP 2/2\nCOMMIT\n" + digest + "\n",
				}, nil
			default:
				t.Fatalf("unexpected command: %s %#v", spec.Command, spec.Args)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewImageBuildHandler(runner)
	session := domain.Session{ID: "session-build", WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"context_path":".","dockerfile_path":"Dockerfile","tag":"ghcr.io/acme/demo:1.0.0","push":false}`))
	if err != nil {
		t.Fatalf("unexpected image.build error: %#v", err)
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["builder"] != "buildah" {
		t.Fatalf("expected builder buildah, got %#v", output["builder"])
	}
	if output["simulated"] != false {
		t.Fatalf("expected simulated=false, got %#v", output["simulated"])
	}
	imageRef := asString(output["image_ref"])
	if !strings.HasPrefix(imageRef, "ghcr.io/acme/demo:1.0.0@sha256:") {
		t.Fatalf("unexpected image_ref: %s", imageRef)
	}
	if output["exit_code"] != 0 {
		t.Fatalf("expected exit_code=0, got %#v", output["exit_code"])
	}
}

func TestImageBuildHandler_SyntheticFallbackWithoutBuilder(t *testing.T) {
	runner := &fakeImageCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			switch spec.Command {
			case "cat":
				return app.CommandResult{
					ExitCode: 0,
					Output:   "FROM alpine:3.20\nRUN echo fallback\n",
				}, nil
			case "buildah", "podman", "docker":
				return app.CommandResult{ExitCode: 127, Output: "not found"}, context.DeadlineExceeded
			default:
				t.Fatalf("unexpected command: %s %#v", spec.Command, spec.Args)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewImageBuildHandler(runner)
	session := domain.Session{ID: "session-fallback", WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"context_path":".","dockerfile_path":"Dockerfile","tag":"ghcr.io/acme/demo:latest","push":true}`))
	if err != nil {
		t.Fatalf("unexpected synthetic image.build error: %#v", err)
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["builder"] != "synthetic" {
		t.Fatalf("expected synthetic builder, got %#v", output["builder"])
	}
	if output["simulated"] != true {
		t.Fatalf("expected simulated=true, got %#v", output["simulated"])
	}
	if output["push_skipped_reason"] != "no_container_builder_available" {
		t.Fatalf("unexpected push_skipped_reason: %#v", output["push_skipped_reason"])
	}
	imageRef := asString(output["image_ref"])
	if !strings.Contains(imageRef, "@sha256:") {
		t.Fatalf("expected digest-pinned image_ref, got %s", imageRef)
	}
	if output["exit_code"] != 0 {
		t.Fatalf("expected exit_code=0, got %#v", output["exit_code"])
	}
}

func TestImagePushHandler_UsesBuilderWhenAvailable(t *testing.T) {
	digest := "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	runner := &fakeImageCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			switch spec.Command {
			case "buildah":
				if len(spec.Args) > 0 && spec.Args[0] == "version" {
					return app.CommandResult{ExitCode: 0, Output: "buildah version 1.36.0"}, nil
				}
				if len(spec.Args) > 0 && spec.Args[0] == "push" {
					return app.CommandResult{ExitCode: 0, Output: "pushed\n" + digest + "\n"}, nil
				}
				t.Fatalf("unexpected buildah args: %#v", spec.Args)
				return app.CommandResult{}, nil
			default:
				t.Fatalf("unexpected command: %s %#v", spec.Command, spec.Args)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewImagePushHandler(runner)
	session := domain.Session{ID: "session-push", WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"image_ref":"ghcr.io/acme/demo:1.0.0","max_retries":1}`))
	if err != nil {
		t.Fatalf("unexpected image.push error: %#v", err)
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["builder"] != "buildah" {
		t.Fatalf("expected builder buildah, got %#v", output["builder"])
	}
	if output["simulated"] != false {
		t.Fatalf("expected simulated=false, got %#v", output["simulated"])
	}
	if output["pushed"] != true {
		t.Fatalf("expected pushed=true, got %#v", output["pushed"])
	}
	if output["attempts"] != 1 {
		t.Fatalf("expected attempts=1, got %#v", output["attempts"])
	}
	imageRef := asString(output["image_ref"])
	if !strings.HasPrefix(imageRef, "ghcr.io/acme/demo:1.0.0@sha256:") {
		t.Fatalf("unexpected image_ref: %s", imageRef)
	}
}

func TestImagePushHandler_SyntheticFallbackWithoutBuilder(t *testing.T) {
	runner := &fakeImageCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			switch spec.Command {
			case "buildah", "podman", "docker":
				return app.CommandResult{ExitCode: 127, Output: "not found"}, errors.New("not found")
			default:
				t.Fatalf("unexpected command: %s %#v", spec.Command, spec.Args)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewImagePushHandler(runner)
	session := domain.Session{ID: "session-push-fallback", WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"image_ref":"ghcr.io/acme/demo:latest"}`))
	if err != nil {
		t.Fatalf("unexpected synthetic image.push error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["builder"] != "synthetic" {
		t.Fatalf("expected synthetic builder, got %#v", output["builder"])
	}
	if output["simulated"] != true {
		t.Fatalf("expected simulated=true, got %#v", output["simulated"])
	}
	if output["pushed"] != false {
		t.Fatalf("expected pushed=false, got %#v", output["pushed"])
	}
	if output["push_skipped_reason"] != "no_container_builder_available" {
		t.Fatalf("unexpected push_skipped_reason: %#v", output["push_skipped_reason"])
	}
}

func TestImagePushHandler_StrictFailsWithoutBuilder(t *testing.T) {
	runner := &fakeImageCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			switch spec.Command {
			case "buildah", "podman", "docker":
				return app.CommandResult{ExitCode: 127, Output: "not found"}, errors.New("not found")
			default:
				t.Fatalf("unexpected command: %s %#v", spec.Command, spec.Args)
				return app.CommandResult{}, nil
			}
		},
	}
	handler := NewImagePushHandler(runner)
	session := domain.Session{ID: "session-push-strict", WorkspacePath: "/workspace/repo", AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"image_ref":"ghcr.io/acme/demo:latest","strict":true}`))
	if err == nil {
		t.Fatalf("expected strict image.push to fail without builder")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected execution_failed code, got %s", err.Code)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["exit_code"] != 1 {
		t.Fatalf("expected exit_code=1, got %#v", output["exit_code"])
	}
}
