package tools

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestSecurityLicenseCheckHandler_DeniedLicenseFailsStatus(t *testing.T) {
	root := t.TempDir()
	packageJSON := `{"name":"demo","version":"1.0.0","private":true}`
	if err := os.WriteFile(filepath.Join(root, "package.json"), []byte(packageJSON), 0o644); err != nil {
		t.Fatalf("write package.json failed: %v", err)
	}

	npmOutput := `{
  "name": "demo",
  "version": "1.0.0",
  "dependencies": {
    "left-pad": {
      "version": "1.3.0",
      "license": "GPL-3.0"
    }
  }
}`
	runner := &fakeSWERuntimeCommandRunner{
		run: func(callIndex int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm command, got %q", spec.Command)
			}
			if callIndex == 0 {
				if len(spec.Args) != 3 || spec.Args[0] != "ls" || spec.Args[1] != "--json" || spec.Args[2] != "--all" {
					t.Fatalf("unexpected dependency inventory args: %#v", spec.Args)
				}
			}
			if callIndex == 1 {
				if len(spec.Args) != 4 || spec.Args[3] != "--long" {
					t.Fatalf("unexpected license enrichment args: %#v", spec.Args)
				}
			}
			return app.CommandResult{ExitCode: 0, Output: npmOutput}, nil
		},
	}
	handler := NewSecurityLicenseCheckHandler(runner)
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}

	result, err := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"path":            ".",
		"denied_licenses": []string{"GPL-3.0"},
		"unknown_policy":  "warn",
	}))
	if err != nil {
		t.Fatalf("unexpected security.license_check error: %#v", err)
	}
	if len(runner.calls) != 2 {
		t.Fatalf("expected 2 npm calls, got %d", len(runner.calls))
	}
	if result.ExitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", result.ExitCode)
	}

	output := result.Output.(map[string]any)
	if output["status"] != "fail" {
		t.Fatalf("expected fail status, got %#v", output["status"])
	}
	if output["denied_count"] != 1 {
		t.Fatalf("expected denied_count=1, got %#v", output["denied_count"])
	}
}

func TestSecurityLicenseCheckHandler_InvalidUnknownPolicy(t *testing.T) {
	handler := NewSecurityLicenseCheckHandler(&fakeSWERuntimeCommandRunner{})
	_, err := handler.Invoke(context.Background(), domain.Session{WorkspacePath: t.TempDir()}, json.RawMessage(`{"unknown_policy":"block"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected unknown_policy validation error, got %#v", err)
	}
}

func TestSecurityLicenseCheckHandler_UnknownPolicyDeny(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n\ngo 1.23\n"), 0o644); err != nil {
		t.Fatalf("write go.mod failed: %v", err)
	}
	runner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "go" {
				t.Fatalf("expected go list command, got %q", spec.Command)
			}
			return app.CommandResult{ExitCode: 0, Output: "example.com/demo\nexample.com/lib v1.0.0\n"}, nil
		},
	}
	result, err := NewSecurityLicenseCheckHandler(runner).Invoke(context.Background(), domain.Session{WorkspacePath: root}, mustSWERuntimeJSON(t, map[string]any{
		"path":           ".",
		"unknown_policy": "deny",
	}))
	if err != nil {
		t.Fatalf("unexpected security.license_check invocation error: %#v", err)
	}
	if result.ExitCode != 1 {
		t.Fatalf("expected exit code 1 for unknown_policy=deny, got %d", result.ExitCode)
	}
}

func TestRuntimeLicenseParsingAndEnrichment(t *testing.T) {
	metadata := `{
  "packages": [
    {"name":"serde","version":"1.0.0","license":"MIT"},
    {"name":"tokio","version":"1.0.0","license":""}
  ]
}`
	rustMap, err := parseRustLicenseMap(metadata, 50)
	if err != nil {
		t.Fatalf("parseRustLicenseMap failed: %v", err)
	}
	if len(rustMap) != 1 {
		t.Fatalf("unexpected rust license map size: %d", len(rustMap))
	}

	nodeRunner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "npm" {
				t.Fatalf("expected npm command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output:   `{"dependencies":{"left-pad":{"version":"1.3.0","license":"MIT"}}}`,
			}, nil
		},
	}
	nodeEntries := []dependencyEntry{{Name: "left-pad", Version: "1.3.0", Ecosystem: "node", License: "unknown"}}
	enrichedNode, command, _, err := enrichDependencyLicenses(
		context.Background(),
		nodeRunner,
		domain.Session{WorkspacePath: t.TempDir()},
		licenseEnrichmentInput{
			detected: projectType{Name: "node"}, scanPath: ".",
			entries: nodeEntries, maxDependencies: 100,
		},
	)
	if err != nil {
		t.Fatalf("enrichDependencyLicenses node failed: %v", err)
	}
	if len(command) == 0 || command[0] != "npm" {
		t.Fatalf("unexpected node enrichment command: %#v", command)
	}
	if len(enrichedNode) != 1 || enrichedNode[0].License != "MIT" {
		t.Fatalf("unexpected node enriched entries: %#v", enrichedNode)
	}

	rustRunner := &fakeSWERuntimeCommandRunner{
		run: func(_ int, spec app.CommandSpec) (app.CommandResult, error) {
			if spec.Command != "cargo" {
				t.Fatalf("expected cargo command, got %q", spec.Command)
			}
			return app.CommandResult{
				ExitCode: 0,
				Output:   metadata,
			}, nil
		},
	}
	rustEntries := []dependencyEntry{{Name: "serde", Version: "1.0.0", Ecosystem: "rust", License: "unknown"}}
	enrichedRust, rustCommand, _, err := enrichDependencyLicenses(
		context.Background(),
		rustRunner,
		domain.Session{WorkspacePath: t.TempDir()},
		licenseEnrichmentInput{
			detected: projectType{Name: "rust"}, scanPath: ".",
			entries: rustEntries, maxDependencies: 100,
		},
	)
	if err != nil {
		t.Fatalf("enrichDependencyLicenses rust failed: %v", err)
	}
	if len(rustCommand) == 0 || rustCommand[0] != "cargo" {
		t.Fatalf("unexpected rust enrichment command: %#v", rustCommand)
	}
	if len(enrichedRust) != 1 || enrichedRust[0].License != "MIT" {
		t.Fatalf("unexpected rust enriched entries: %#v", enrichedRust)
	}
}
