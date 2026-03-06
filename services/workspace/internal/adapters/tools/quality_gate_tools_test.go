package tools

import (
	"context"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestQualityGateHandler_PassAndFail(t *testing.T) {
	handler := NewQualityGateHandler(nil)
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}

	passResult, passErr := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"metrics": map[string]any{
			"coverage_percent":   82.5,
			"diagnostics_count":  0,
			"failed_tests_count": 0,
		},
		"min_coverage_percent": 80,
		"max_diagnostics":      0,
		"max_failed_tests":     0,
	}))
	if passErr != nil {
		t.Fatalf("unexpected quality.gate pass error: %#v", passErr)
	}
	if passResult.ExitCode != 0 {
		t.Fatalf("expected pass exit code 0, got %d", passResult.ExitCode)
	}
	passOutput := passResult.Output.(map[string]any)
	if passOutput["status"] != "pass" {
		t.Fatalf("expected pass status, got %#v", passOutput["status"])
	}

	failResult, failErr := handler.Invoke(context.Background(), session, mustSWERuntimeJSON(t, map[string]any{
		"metrics": map[string]any{
			"failed_tests_count": 2,
		},
		"max_failed_tests": 0,
	}))
	if failErr != nil {
		t.Fatalf("unexpected quality.gate fail invocation error: %#v", failErr)
	}
	if failResult.ExitCode != 1 {
		t.Fatalf("expected fail exit code 1, got %d", failResult.ExitCode)
	}
	failOutput := failResult.Output.(map[string]any)
	if failOutput["status"] != "fail" {
		t.Fatalf("expected fail status, got %#v", failOutput["status"])
	}
}

func TestQualityGateConfigHelpers(t *testing.T) {
	minCoverage := 120.0
	maxDiagnostics := -2
	maxVulns := 200001
	maxDenied := 5
	maxFailed := 3
	config := normalizeQualityGateConfig(qualityGateThresholdsRequest{
		MinCoveragePercent: &minCoverage,
		MaxDiagnostics:     &maxDiagnostics,
		MaxVulnerabilities: &maxVulns,
		MaxDeniedLicenses:  &maxDenied,
		MaxFailedTests:     &maxFailed,
	})
	if config.MinCoveragePercent != 100 {
		t.Fatalf("unexpected min coverage clamp: %f", config.MinCoveragePercent)
	}
	if config.MaxDiagnostics != -1 {
		t.Fatalf("unexpected max diagnostics clamp: %d", config.MaxDiagnostics)
	}
	if config.MaxVulnerabilities != 100000 {
		t.Fatalf("unexpected max vulnerabilities clamp: %d", config.MaxVulnerabilities)
	}
	if qualityGateSummary(true, 0, 0) != "quality gate passed (no active rules)" {
		t.Fatal("unexpected qualityGateSummary for no rules")
	}
	if ternaryQualityGateStatus(false) != "fail" {
		t.Fatal("unexpected ternary quality gate status")
	}
}
