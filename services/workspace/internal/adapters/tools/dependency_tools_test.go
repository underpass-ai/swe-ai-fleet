package tools

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestSecurityScanDependenciesHandler_Go(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "go" {
				t.Fatalf("expected go command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output: "example.com/demo\n" +
					"github.com/google/uuid v1.6.0\n" +
					"golang.org/x/text v0.22.0\n",
			}, nil
		},
	}
	handler := NewSecurityScanDependenciesHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"path":".","max_dependencies":2}`))
	if err != nil {
		t.Fatalf("unexpected security.scan_dependencies error: %#v", err)
	}
	if len(runner.calls) != 1 {
		t.Fatalf("expected one runner call, got %d", len(runner.calls))
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["dependencies_count"] != 2 {
		t.Fatalf("unexpected dependencies_count: %#v", output["dependencies_count"])
	}
	if output["truncated"] != true {
		t.Fatalf("expected truncated=true, got %#v", output["truncated"])
	}
}

func TestSBOMGenerateHandler_GeneratesCycloneDXArtifact(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}

	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "go" {
				t.Fatalf("expected go command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output: "example.com/demo\n" +
					"github.com/google/uuid v1.6.0\n",
			}, nil
		},
	}
	handler := NewSBOMGenerateHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"path":".","format":"cyclonedx-json","max_components":50}`))
	if err != nil {
		t.Fatalf("unexpected sbom.generate error: %#v", err)
	}

	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %T", result.Output)
	}
	if output["artifact_name"] != "sbom.cdx.json" {
		t.Fatalf("unexpected artifact_name: %#v", output["artifact_name"])
	}

	foundSBOM := false
	for _, artifact := range result.Artifacts {
		if artifact.Name != "sbom.cdx.json" {
			continue
		}
		foundSBOM = true
		if !strings.Contains(string(artifact.Data), `"bomFormat": "CycloneDX"`) {
			t.Fatalf("expected CycloneDX content, got: %s", string(artifact.Data))
		}
	}
	if !foundSBOM {
		t.Fatal("expected sbom.cdx.json artifact")
	}
}

func TestSBOMGenerateHandler_RejectsUnsupportedFormat(t *testing.T) {
	handler := NewSBOMGenerateHandler(&fakeSWERuntimeCommandRunner{})
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"format":"spdx-json"}`))
	if err == nil {
		t.Fatal("expected invalid format error")
	}
	if err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

func TestSecurityScanDependenciesHandler_InvalidPath(t *testing.T) {
	handler := NewSecurityScanDependenciesHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"path":"../outside"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid path error, got %#v", err)
	}
}

func TestSBOMGenerateHandler_RejectsInvalidPath(t *testing.T) {
	handler := NewSBOMGenerateHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"path":"../outside","format":"cyclonedx-json"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid path error, got %#v", err)
	}
}

func TestSBOMGenerateHandler_InventoryParseFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(`{"name":"demo","version":"1.0.0"}`), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, _ app.CommandSpec) (app.CommandResult, error) {
			return app.CommandResult{ExitCode: 0, Output: "{invalid-json"}, nil
		},
	}
	_, err := NewSBOMGenerateHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{"path":".","format":"cyclonedx-json"}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected sbom inventory parse failure, got %#v", err)
	}
}

func TestSecurityScanDependenciesHandler_ParseFailure(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(`{"name":"demo","version":"1.0.0"}`), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm inventory command, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: "{invalid-json"}, nil
		},
	}
	_, err := NewSecurityScanDependenciesHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, json.RawMessage(`{"path":"."}`))
	if err == nil || err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("expected dependency inventory parse failure, got %#v", err)
	}
}

func TestRuntimeDependencyParsers(t *testing.T) {
	pythonOutput := `[
  {"name":"requests","version":"2.31.0"},
  {"name":"requests","version":"2.31.0"},
  {"name":"urllib3","version":"2.2.0"},
  {"name":"click"}
]`
	pythonDeps, pythonTruncated, err := parsePythonDependencyInventory(pythonOutput, 2)
	if err != nil {
		t.Fatalf("parsePythonDependencyInventory failed: %v", err)
	}
	if len(pythonDeps) != 2 || !pythonTruncated {
		t.Fatalf("unexpected python deps result: len=%d truncated=%v", len(pythonDeps), pythonTruncated)
	}

	rustOutput := "serde v1.0.0\n├── regex v1.10.3\n└── serde v1.0.0\n"
	rustDeps, rustTruncated, err := parseRustDependencyInventory(rustOutput, 2)
	if err != nil {
		t.Fatalf("parseRustDependencyInventory failed: %v", err)
	}
	if len(rustDeps) != 2 || rustTruncated {
		t.Fatalf("unexpected rust deps result: len=%d truncated=%v", len(rustDeps), rustTruncated)
	}

	mavenOutput := "[INFO] org.apache.commons:commons-lang3:jar:3.13.0:runtime\n[INFO] junk line\n"
	mavenDeps, mavenTruncated, err := parseMavenDependencyInventory(mavenOutput, 10)
	if err != nil {
		t.Fatalf("parseMavenDependencyInventory failed: %v", err)
	}
	if len(mavenDeps) != 1 || mavenTruncated {
		t.Fatalf("unexpected maven deps: %#v truncated=%v", mavenDeps, mavenTruncated)
	}

	gradleOutput := "+--- org.slf4j:slf4j-api:1.7.36\n\\--- org.jetbrains.kotlin:kotlin-stdlib:1.9.0 -> 1.9.22\n"
	gradleDeps, gradleTruncated, err := parseGradleDependencyInventory(gradleOutput, 10)
	if err != nil {
		t.Fatalf("parseGradleDependencyInventory failed: %v", err)
	}
	if len(gradleDeps) != 2 || gradleTruncated {
		t.Fatalf("unexpected gradle deps: %#v truncated=%v", gradleDeps, gradleTruncated)
	}
}
