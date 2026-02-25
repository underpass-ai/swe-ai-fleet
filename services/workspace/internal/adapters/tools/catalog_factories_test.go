package tools

import (
	"encoding/json"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

// ---------------------------------------------------------------------------
// newExtraArgsPolicy
// ---------------------------------------------------------------------------

func TestNewExtraArgsPolicy(t *testing.T) {
	allowed := []string{"-v", "-run="}
	denied := []string{"-exec"}
	policy := newExtraArgsPolicy(allowed, denied)

	if len(policy.ArgFields) != 1 {
		t.Fatalf("expected 1 ArgField, got %d", len(policy.ArgFields))
	}
	af := policy.ArgFields[0]
	if af.Field != "extra_args" {
		t.Fatalf("expected Field=extra_args, got %q", af.Field)
	}
	if !af.Multi {
		t.Fatal("expected Multi=true")
	}
	if af.MaxItems != 8 {
		t.Fatalf("expected MaxItems=8, got %d", af.MaxItems)
	}
	if af.MaxLength != 64 {
		t.Fatalf("expected MaxLength=64, got %d", af.MaxLength)
	}
	if len(af.AllowedPrefix) != 2 || af.AllowedPrefix[0] != "-v" {
		t.Fatalf("unexpected AllowedPrefix: %#v", af.AllowedPrefix)
	}
	if len(af.DeniedPrefix) != 1 || af.DeniedPrefix[0] != "-exec" {
		t.Fatalf("unexpected DeniedPrefix: %#v", af.DeniedPrefix)
	}
	if len(af.DenyCharacters) != len(catalogShellDenyChars) {
		t.Fatalf("expected %d DenyCharacters, got %d", len(catalogShellDenyChars), len(af.DenyCharacters))
	}
}

func TestNewExtraArgsPolicy_NilSlices(t *testing.T) {
	policy := newExtraArgsPolicy(nil, nil)
	af := policy.ArgFields[0]
	if af.AllowedPrefix != nil {
		t.Fatalf("expected nil AllowedPrefix, got %#v", af.AllowedPrefix)
	}
	if af.DeniedPrefix != nil {
		t.Fatalf("expected nil DeniedPrefix, got %#v", af.DeniedPrefix)
	}
}

// ---------------------------------------------------------------------------
// newGitRemoteDenyPolicy
// ---------------------------------------------------------------------------

func TestNewGitRemoteDenyPolicy(t *testing.T) {
	policy := newGitRemoteDenyPolicy()
	if len(policy.ArgFields) != 2 {
		t.Fatalf("expected 2 ArgFields, got %d", len(policy.ArgFields))
	}

	remote := policy.ArgFields[0]
	if remote.Field != "remote" {
		t.Fatalf("expected Field=remote, got %q", remote.Field)
	}
	if remote.MaxLength != 128 {
		t.Fatalf("expected MaxLength=128, got %d", remote.MaxLength)
	}
	if len(remote.DenyCharacters) != len(catalogShellDenyCharsWithSpace) {
		t.Fatalf("expected %d DenyCharacters, got %d", len(catalogShellDenyCharsWithSpace), len(remote.DenyCharacters))
	}

	refspec := policy.ArgFields[1]
	if refspec.Field != "refspec" {
		t.Fatalf("expected Field=refspec, got %q", refspec.Field)
	}
	if refspec.MaxLength != 512 {
		t.Fatalf("expected MaxLength=512, got %d", refspec.MaxLength)
	}
}

// ---------------------------------------------------------------------------
// newK8sReadCapability
// ---------------------------------------------------------------------------

func TestNewK8sReadCapability(t *testing.T) {
	inputSchema := mustRawJSON(`{"type":"object","properties":{"namespace":{"type":"string"}},"required":[]}`)
	outputSchema := mustRawJSON(`{"type":"object","properties":{"pods":{"type":"array"}}}`)
	examples := []json.RawMessage{mustRawJSON(`{"namespace":"swe-ai-fleet"}`)}

	cap := newK8sReadCapability("k8s.get_pods", "List pods", "k8s.get_pods", inputSchema, outputSchema, examples)

	if cap.Name != "k8s.get_pods" {
		t.Fatalf("expected Name=k8s.get_pods, got %q", cap.Name)
	}
	if cap.Description != "List pods" {
		t.Fatalf("unexpected Description: %q", cap.Description)
	}
	if cap.Scope != domain.ScopeCluster {
		t.Fatalf("expected ScopeCluster, got %v", cap.Scope)
	}
	if cap.SideEffects != domain.SideEffectsNone {
		t.Fatalf("expected SideEffectsNone, got %v", cap.SideEffects)
	}
	if cap.RiskLevel != domain.RiskLow {
		t.Fatalf("expected RiskLow, got %v", cap.RiskLevel)
	}
	if cap.RequiresApproval {
		t.Fatal("expected RequiresApproval=false")
	}
	if cap.Idempotency != domain.IdempotencyGuaranteed {
		t.Fatalf("expected IdempotencyGuaranteed, got %v", cap.Idempotency)
	}
	if cap.Constraints.TimeoutSeconds != 30 {
		t.Fatalf("expected TimeoutSeconds=30, got %d", cap.Constraints.TimeoutSeconds)
	}
	if cap.Constraints.OutputLimitKB != 2048 {
		t.Fatalf("expected OutputLimitKB=2048, got %d", cap.Constraints.OutputLimitKB)
	}
	if cap.CostHint != "low" {
		t.Fatalf("expected CostHint=low, got %q", cap.CostHint)
	}
	if len(cap.Policy.NamespaceFields) != 1 || cap.Policy.NamespaceFields[0] != "namespace" {
		t.Fatalf("expected NamespaceFields=[namespace], got %#v", cap.Policy.NamespaceFields)
	}
	if cap.Observability.TraceName != catalogTraceName {
		t.Fatalf("expected TraceName=%q, got %q", catalogTraceName, cap.Observability.TraceName)
	}
	if cap.Observability.SpanName != "k8s.get_pods" {
		t.Fatalf("expected SpanName=k8s.get_pods, got %q", cap.Observability.SpanName)
	}
	if len(cap.Examples) != 1 {
		t.Fatalf("expected 1 example, got %d", len(cap.Examples))
	}
	if len(cap.Preconditions) != 1 || cap.Preconditions[0] != precondClusterScopeAccess {
		t.Fatalf("unexpected Preconditions: %#v", cap.Preconditions)
	}
	if len(cap.Postconditions) != 1 || cap.Postconditions[0] != postcondNoClusterMutation {
		t.Fatalf("unexpected Postconditions: %#v", cap.Postconditions)
	}
}

// ---------------------------------------------------------------------------
// newGoCapability
// ---------------------------------------------------------------------------

func TestNewGoCapability(t *testing.T) {
	inputSchema := mustRawJSON(`{"type":"object","properties":{"package":{"type":"string"}},"required":[]}`)
	examples := []json.RawMessage{mustRawJSON(`{"package":"./..."}`)}
	postconds := []string{postcondTestReportsGenerated}

	cap := newGoCapability("go.test", "Run Go tests", "go.test", inputSchema, postconds, examples)

	if cap.Name != "go.test" {
		t.Fatalf("expected Name=go.test, got %q", cap.Name)
	}
	if cap.Scope != domain.ScopeRepo {
		t.Fatalf("expected ScopeRepo, got %v", cap.Scope)
	}
	if cap.SideEffects != domain.SideEffectsReversible {
		t.Fatalf("expected SideEffectsReversible, got %v", cap.SideEffects)
	}
	if cap.RiskLevel != domain.RiskMedium {
		t.Fatalf("expected RiskMedium, got %v", cap.RiskLevel)
	}
	if cap.Constraints.TimeoutSeconds != 300 {
		t.Fatalf("expected TimeoutSeconds=300, got %d", cap.Constraints.TimeoutSeconds)
	}
	if cap.CostHint != "high" {
		t.Fatalf("expected CostHint=high, got %q", cap.CostHint)
	}
	if len(cap.Preconditions) != 1 || cap.Preconditions[0] != precondWorkspaceGoMod {
		t.Fatalf("unexpected Preconditions: %#v", cap.Preconditions)
	}
	if len(cap.Postconditions) != 1 || cap.Postconditions[0] != postcondTestReportsGenerated {
		t.Fatalf("unexpected Postconditions: %#v", cap.Postconditions)
	}
	if string(cap.OutputSchema) != string(catalogLangToolOutputSchema) {
		t.Fatal("expected OutputSchema to use catalogLangToolOutputSchema")
	}
}

// ---------------------------------------------------------------------------
// newRustCapability
// ---------------------------------------------------------------------------

func TestNewRustCapability(t *testing.T) {
	inputSchema := mustRawJSON(`{"type":"object","properties":{"target":{"type":"string"}},"required":[]}`)
	postconds := []string{"target artifacts may be generated"}

	cap := newRustCapability("rust.build", "Build Rust", "rust.build", inputSchema, postconds, "high", 300)

	if cap.Name != "rust.build" {
		t.Fatalf("expected Name=rust.build, got %q", cap.Name)
	}
	if cap.Scope != domain.ScopeRepo {
		t.Fatalf("expected ScopeRepo, got %v", cap.Scope)
	}
	if cap.RiskLevel != domain.RiskMedium {
		t.Fatalf("expected RiskMedium, got %v", cap.RiskLevel)
	}
	if cap.Constraints.TimeoutSeconds != 300 {
		t.Fatalf("expected TimeoutSeconds=300, got %d", cap.Constraints.TimeoutSeconds)
	}
	if cap.CostHint != "high" {
		t.Fatalf("expected CostHint=high, got %q", cap.CostHint)
	}
	if len(cap.Preconditions) != 1 || cap.Preconditions[0] != precondWorkspaceCargoToml {
		t.Fatalf("unexpected Preconditions: %#v", cap.Preconditions)
	}
	if string(cap.OutputSchema) != string(catalogLangToolOutputSchema) {
		t.Fatal("expected OutputSchema to use catalogLangToolOutputSchema")
	}
}

func TestNewRustCapability_DifferentCostAndTimeout(t *testing.T) {
	inputSchema := mustRawJSON(`{"type":"object","properties":{},"required":[]}`)
	cap := newRustCapability("rust.format", "Format Rust", "rust.format", inputSchema, []string{"fmt done"}, "medium", 180)

	if cap.Constraints.TimeoutSeconds != 180 {
		t.Fatalf("expected TimeoutSeconds=180, got %d", cap.Constraints.TimeoutSeconds)
	}
	if cap.CostHint != "medium" {
		t.Fatalf("expected CostHint=medium, got %q", cap.CostHint)
	}
}

// ---------------------------------------------------------------------------
// newNodeCapability
// ---------------------------------------------------------------------------

func TestNewNodeCapability(t *testing.T) {
	inputSchema := mustRawJSON(`{"type":"object","properties":{"target":{"type":"string"}},"required":[]}`)
	postconds := []string{postcondBuildArtifactsGenerated}

	cap := newNodeCapability("node.build", "Build Node", "node.build", inputSchema, postconds, "high", 300, 2048)

	if cap.Name != "node.build" {
		t.Fatalf("expected Name=node.build, got %q", cap.Name)
	}
	if cap.Scope != domain.ScopeRepo {
		t.Fatalf("expected ScopeRepo, got %v", cap.Scope)
	}
	if cap.RiskLevel != domain.RiskMedium {
		t.Fatalf("expected RiskMedium, got %v", cap.RiskLevel)
	}
	if cap.Constraints.TimeoutSeconds != 300 {
		t.Fatalf("expected TimeoutSeconds=300, got %d", cap.Constraints.TimeoutSeconds)
	}
	if cap.Constraints.OutputLimitKB != 2048 {
		t.Fatalf("expected OutputLimitKB=2048, got %d", cap.Constraints.OutputLimitKB)
	}
	if cap.CostHint != "high" {
		t.Fatalf("expected CostHint=high, got %q", cap.CostHint)
	}
	if len(cap.Preconditions) != 1 || cap.Preconditions[0] != precondWorkspacePackageJSON {
		t.Fatalf("unexpected Preconditions: %#v", cap.Preconditions)
	}
	if len(cap.Policy.PathFields) != 1 || cap.Policy.PathFields[0].Field != "target" {
		t.Fatalf("expected PathFields with target field, got %#v", cap.Policy.PathFields)
	}
	if !cap.Policy.PathFields[0].WorkspaceRelative {
		t.Fatal("expected PathFields[0].WorkspaceRelative=true")
	}
	if string(cap.OutputSchema) != string(catalogLangToolOutputSchema) {
		t.Fatal("expected OutputSchema to use catalogLangToolOutputSchema")
	}
}

func TestNewNodeCapability_DifferentTimeoutAndOutputKB(t *testing.T) {
	inputSchema := mustRawJSON(`{"type":"object","properties":{},"required":[]}`)
	cap := newNodeCapability("node.lint", "Lint Node", "node.lint", inputSchema, []string{"lint done"}, "high", 240, 1024)

	if cap.Constraints.TimeoutSeconds != 240 {
		t.Fatalf("expected TimeoutSeconds=240, got %d", cap.Constraints.TimeoutSeconds)
	}
	if cap.Constraints.OutputLimitKB != 1024 {
		t.Fatalf("expected OutputLimitKB=1024, got %d", cap.Constraints.OutputLimitKB)
	}
}

// ---------------------------------------------------------------------------
// Shared constants validation
// ---------------------------------------------------------------------------

func TestCatalogShellDenyChars(t *testing.T) {
	expected := []string{";", "|", "&", "`", "$(", ">", "<", "\n", "\r"}
	if len(catalogShellDenyChars) != len(expected) {
		t.Fatalf("expected %d deny chars, got %d", len(expected), len(catalogShellDenyChars))
	}
	for i, v := range expected {
		if catalogShellDenyChars[i] != v {
			t.Fatalf("catalogShellDenyChars[%d] = %q, want %q", i, catalogShellDenyChars[i], v)
		}
	}
}

func TestCatalogShellDenyCharsWithSpace(t *testing.T) {
	if len(catalogShellDenyCharsWithSpace) != len(catalogShellDenyChars)+1 {
		t.Fatalf("expected catalogShellDenyCharsWithSpace to have %d entries, got %d",
			len(catalogShellDenyChars)+1, len(catalogShellDenyCharsWithSpace))
	}
	last := catalogShellDenyCharsWithSpace[len(catalogShellDenyCharsWithSpace)-1]
	if last != " " {
		t.Fatalf("expected last entry to be space, got %q", last)
	}
}

func TestCatalogLangToolOutputSchema(t *testing.T) {
	var parsed map[string]any
	if err := json.Unmarshal(catalogLangToolOutputSchema, &parsed); err != nil {
		t.Fatalf("catalogLangToolOutputSchema is not valid JSON: %v", err)
	}
	props, ok := parsed["properties"].(map[string]any)
	if !ok {
		t.Fatal("expected properties in output schema")
	}
	for _, key := range []string{"exit_code", "compiled_binary_path", "coverage_percent", "diagnostics"} {
		if _, found := props[key]; !found {
			t.Fatalf("expected property %q in catalogLangToolOutputSchema", key)
		}
	}
}

// ---------------------------------------------------------------------------
// DefaultCapabilities — verify factory-produced entries are consistent
// ---------------------------------------------------------------------------

func TestDefaultCapabilities_FactoryConsistency(t *testing.T) {
	capabilities := DefaultCapabilities()
	capMap := make(map[string]domain.Capability)
	for _, c := range capabilities {
		capMap[c.Name] = c
	}

	// Verify git remote tools have correct policy from newGitRemoteDenyPolicy
	for _, name := range []string{"git.push", "git.fetch", "git.pull"} {
		cap, ok := capMap[name]
		if !ok {
			t.Fatalf("missing capability %q", name)
		}
		if len(cap.Policy.ArgFields) != 2 {
			t.Fatalf("%s: expected 2 policy ArgFields, got %d", name, len(cap.Policy.ArgFields))
		}
		if cap.Policy.ArgFields[0].Field != "remote" {
			t.Fatalf("%s: expected first ArgField=remote, got %q", name, cap.Policy.ArgFields[0].Field)
		}
		if cap.Policy.ArgFields[1].Field != "refspec" {
			t.Fatalf("%s: expected second ArgField=refspec, got %q", name, cap.Policy.ArgFields[1].Field)
		}
	}

	// Verify repo tools have correct policy from newExtraArgsPolicy
	for _, name := range []string{"repo.build", "repo.test", "repo.run_tests", "repo.test_failures_summary", "repo.stacktrace_summary"} {
		cap, ok := capMap[name]
		if !ok {
			t.Fatalf("missing capability %q", name)
		}
		if len(cap.Policy.ArgFields) != 1 {
			t.Fatalf("%s: expected 1 policy ArgField, got %d", name, len(cap.Policy.ArgFields))
		}
		af := cap.Policy.ArgFields[0]
		if af.Field != "extra_args" {
			t.Fatalf("%s: expected ArgField=extra_args, got %q", name, af.Field)
		}
		if !af.Multi {
			t.Fatalf("%s: expected Multi=true", name)
		}
		if af.MaxItems != 8 {
			t.Fatalf("%s: expected MaxItems=8, got %d", name, af.MaxItems)
		}
	}

	// Verify k8s read tools have correct metadata
	for _, name := range []string{"k8s.get_pods", "k8s.get_services", "k8s.get_deployments"} {
		cap, ok := capMap[name]
		if !ok {
			t.Fatalf("missing capability %q", name)
		}
		if cap.Scope != domain.ScopeCluster {
			t.Fatalf("%s: expected ScopeCluster, got %v", name, cap.Scope)
		}
		if cap.RiskLevel != domain.RiskLow {
			t.Fatalf("%s: expected RiskLow, got %v", name, cap.RiskLevel)
		}
		if cap.Constraints.TimeoutSeconds != 30 {
			t.Fatalf("%s: expected TimeoutSeconds=30, got %d", name, cap.Constraints.TimeoutSeconds)
		}
		if len(cap.Policy.NamespaceFields) != 1 {
			t.Fatalf("%s: expected 1 NamespaceField, got %d", name, len(cap.Policy.NamespaceFields))
		}
	}

	// Verify Go tools use factory-produced values
	for _, name := range []string{"go.build", "go.test"} {
		cap, ok := capMap[name]
		if !ok {
			t.Fatalf("missing capability %q", name)
		}
		if cap.Scope != domain.ScopeRepo {
			t.Fatalf("%s: expected ScopeRepo, got %v", name, cap.Scope)
		}
		if cap.CostHint != "high" {
			t.Fatalf("%s: expected CostHint=high, got %q", name, cap.CostHint)
		}
		if string(cap.OutputSchema) != string(catalogLangToolOutputSchema) {
			t.Fatalf("%s: expected factory OutputSchema", name)
		}
	}

	// Verify Rust tools
	for _, name := range []string{"rust.build", "rust.test", "rust.clippy"} {
		cap, ok := capMap[name]
		if !ok {
			t.Fatalf("missing capability %q", name)
		}
		if cap.Scope != domain.ScopeRepo {
			t.Fatalf("%s: expected ScopeRepo, got %v", name, cap.Scope)
		}
		if string(cap.OutputSchema) != string(catalogLangToolOutputSchema) {
			t.Fatalf("%s: expected factory OutputSchema", name)
		}
	}

	// Verify Node tools
	for _, name := range []string{"node.build", "node.test", "node.lint", "node.typecheck"} {
		cap, ok := capMap[name]
		if !ok {
			t.Fatalf("missing capability %q", name)
		}
		if len(cap.Policy.PathFields) != 1 || cap.Policy.PathFields[0].Field != "target" {
			t.Fatalf("%s: expected PathFields with target, got %#v", name, cap.Policy.PathFields)
		}
		if string(cap.OutputSchema) != string(catalogLangToolOutputSchema) {
			t.Fatalf("%s: expected factory OutputSchema", name)
		}
	}
}
