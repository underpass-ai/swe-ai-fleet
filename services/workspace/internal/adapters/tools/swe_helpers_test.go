package tools

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeSWERuntimeCommandRunner struct {
	calls []app.CommandSpec
	run   func(callIndex int, spec app.CommandSpec) (app.CommandResult, error)
}

func (f *fakeSWERuntimeCommandRunner) Run(_ context.Context, _ domain.Session, spec app.CommandSpec) (app.CommandResult, error) {
	f.calls = append(f.calls, spec)
	if f.run != nil {
		return f.run(len(f.calls)-1, spec)
	}
	return app.CommandResult{ExitCode: 0, Output: "ok"}, nil
}

func mustSWERuntimeJSON(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	return data
}

func TestSWERuntimeHandlerNames(t *testing.T) {
	runner := &fakeSWERuntimeCommandRunner{}
	cases := []struct {
		name string
		got  string
	}{
		{name: "repo.coverage_report", got: NewRepoCoverageReportHandler(runner).Name()},
		{name: "repo.static_analysis", got: NewRepoStaticAnalysisHandler(runner).Name()},
		{name: "repo.package", got: NewRepoPackageHandler(runner).Name()},
		{name: "security.scan_secrets", got: NewSecurityScanSecretsHandler(runner).Name()},
		{name: "security.scan_dependencies", got: NewSecurityScanDependenciesHandler(runner).Name()},
		{name: "sbom.generate", got: NewSBOMGenerateHandler(runner).Name()},
		{name: "security.scan_container", got: NewSecurityScanContainerHandler(runner).Name()},
		{name: "security.license_check", got: NewSecurityLicenseCheckHandler(runner).Name()},
		{name: "quality.gate", got: NewQualityGateHandler(runner).Name()},
		{name: "ci.run_pipeline", got: NewCIRunPipelineHandler(runner).Name()},
	}

	for _, tc := range cases {
		if tc.got != tc.name {
			t.Fatalf("unexpected handler name: got=%q want=%q", tc.got, tc.name)
		}
	}
}

func TestRuntimeScalarConverters(t *testing.T) {
	if got := intFromAny(json.Number("12")); got != 12 {
		t.Fatalf("unexpected intFromAny json.Number: %d", got)
	}
	if got := intFromAny(" 7 "); got != 7 {
		t.Fatalf("unexpected intFromAny string: %d", got)
	}
	if got := intFromAny(uint16(9)); got != 9 {
		t.Fatalf("unexpected intFromAny uint16: %d", got)
	}
	if got := intFromAny("bad"); got != 0 {
		t.Fatalf("unexpected intFromAny fallback: %d", got)
	}

	if got := floatFromAny(json.Number("3.5")); got != 3.5 {
		t.Fatalf("unexpected floatFromAny json.Number: %f", got)
	}
	if got := floatFromAny(" 2.25 "); got != 2.25 {
		t.Fatalf("unexpected floatFromAny string: %f", got)
	}
	if got := floatFromAny(int64(5)); got != 5 {
		t.Fatalf("unexpected floatFromAny int64: %f", got)
	}
	if got := floatFromAny("oops"); got != 0 {
		t.Fatalf("unexpected floatFromAny fallback: %f", got)
	}
}

func TestRuntimeSecurityHelpers(t *testing.T) {
	threshold, err := normalizeSeverityThreshold("moderate")
	if err != nil {
		t.Fatalf("normalizeSeverityThreshold failed: %v", err)
	}
	if threshold != "medium" {
		t.Fatalf("unexpected normalized threshold: %q", threshold)
	}
	if _, err := normalizeSeverityThreshold("severe"); err == nil {
		t.Fatal("expected normalizeSeverityThreshold error")
	}

	levels := severityListForThreshold("high")
	if len(levels) != 2 || levels[0] != "CRITICAL" || levels[1] != "HIGH" {
		t.Fatalf("unexpected severity levels: %#v", levels)
	}
	if !severityAtOrAbove("critical", "high") {
		t.Fatal("expected critical to be above high")
	}
	if severityAtOrAbove("low", "high") {
		t.Fatal("low must not pass high threshold")
	}

	if id, sev, _ := dockerfileHeuristicRule("run curl -s https://x | sh"); id == "" || sev != "high" {
		t.Fatalf("unexpected dockerfile heuristic result: id=%q sev=%q", id, sev)
	}
	if !isDockerfileCandidate("Dockerfile.prod") || isDockerfileCandidate("README.md") {
		t.Fatal("unexpected Dockerfile candidate detection")
	}
}

func TestRuntimeLicensePolicyHelpers(t *testing.T) {
	allowed, reason := evaluateLicenseAgainstPolicy("MIT", []string{"MIT"}, []string{"GPL-3.0"})
	if allowed != "allowed" || reason != "" {
		t.Fatalf("expected allowed license, got status=%q reason=%q", allowed, reason)
	}
	denied, reason := evaluateLicenseAgainstPolicy("GPL-3.0", nil, []string{"GPL-3.0"})
	if denied != "denied" || !strings.Contains(reason, "denied") {
		t.Fatalf("expected denied license, got status=%q reason=%q", denied, reason)
	}
	unknown, _ := evaluateLicenseAgainstPolicy("", nil, nil)
	if unknown != "unknown" {
		t.Fatalf("expected unknown license status, got %q", unknown)
	}

	if got := normalizeFoundLicense("mit or apache-2.0"); got != "MIT OR APACHE-2.0" {
		t.Fatalf("unexpected normalized license: %q", got)
	}
	if got := nodeStringOrList([]any{"MIT", "Apache-2.0"}); got != "MIT OR Apache-2.0" {
		t.Fatalf("unexpected nodeStringOrList result: %q", got)
	}
}
