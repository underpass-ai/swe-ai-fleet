package tools

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"strconv"
	"strings"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

const (
	sweUnknown             = "unknown"
	sweTextPlain           = "text/plain"
	sweApplicationJSON     = "application/json"
	sweCoverageReportTxt   = "coverage-report.txt"
	sweCoverProfile        = "-coverprofile"
	sweCoverModeAtomic     = "-covermode=atomic"
	sweWorkspaceDist       = ".workspace-dist"
	sweHeuristicDockerfile = "heuristic-dockerfile"
	sweLicenseIsUnknown    = "license is unknown"
	sweCycloneDXJSON       = "cyclonedx-json"
	sweRgGlobFlag          = "--glob"
)

func detectProjectTypeOrError(ctx context.Context, runner app.CommandRunner, session domain.Session, notFoundMsg string) (projectType, *domain.Error) {
	detected, err := detectProjectTypeForSession(ctx, runner, session)
	if err == nil {
		return detected, nil
	}
	if errors.Is(err, os.ErrNotExist) {
		return projectType{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: notFoundMsg, Retryable: false}
	}
	return projectType{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
}

// dependencyInventoryError maps a raw inventory error to a domain error,
// using notSupportedMsg when the underlying cause is os.ErrNotExist.
func dependencyInventoryError(err error, notSupportedMsg string) *domain.Error {
	if errors.Is(err, os.ErrNotExist) {
		return &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: notSupportedMsg, Retryable: false}
	}
	return &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
}

func isMissingBinaryError(runErr error, result app.CommandResult, command string) bool {
	if runErr == nil {
		return false
	}
	if result.ExitCode == 127 && strings.Contains(strings.ToLower(result.Output), "not found") {
		return true
	}
	errText := strings.ToLower(runErr.Error())
	return strings.Contains(errText, "not found") && strings.Contains(errText, strings.ToLower(command))
}

func intFromAny(value any) int {
	switch typed := value.(type) {
	case int:
		return typed
	case int8:
		return int(typed)
	case int16:
		return int(typed)
	case int32:
		return int(typed)
	case int64:
		return int(typed)
	case uint:
		return int(typed)
	case uint8:
		return int(typed)
	case uint16:
		return int(typed)
	case uint32:
		return int(typed)
	case uint64:
		return int(typed)
	case float32:
		return int(typed)
	case float64:
		return int(typed)
	case json.Number:
		if parsed, err := typed.Int64(); err == nil {
			return int(parsed)
		}
		if parsed, err := typed.Float64(); err == nil {
			return int(parsed)
		}
	case string:
		if parsed, err := strconv.Atoi(strings.TrimSpace(typed)); err == nil {
			return parsed
		}
	}
	return 0
}

func floatFromAny(value any) float64 {
	switch typed := value.(type) {
	case float32:
		return float64(typed)
	case float64:
		return typed
	case int:
		return float64(typed)
	case int8:
		return float64(typed)
	case int16:
		return float64(typed)
	case int32:
		return float64(typed)
	case int64:
		return float64(typed)
	case uint:
		return float64(typed)
	case uint8:
		return float64(typed)
	case uint16:
		return float64(typed)
	case uint32:
		return float64(typed)
	case uint64:
		return float64(typed)
	case json.Number:
		if parsed, err := typed.Float64(); err == nil {
			return parsed
		}
	case string:
		if parsed, err := strconv.ParseFloat(strings.TrimSpace(typed), 64); err == nil {
			return parsed
		}
	}
	return 0
}

func normalizeSeverityThreshold(raw string) (string, error) {
	threshold := strings.ToLower(strings.TrimSpace(raw))
	switch threshold {
	case "", "medium", "moderate":
		return "medium", nil
	case "low":
		return "low", nil
	case "high":
		return "high", nil
	case "critical":
		return "critical", nil
	default:
		return "", errors.New("severity_threshold must be one of: low, medium, high, critical")
	}
}

func severityListForThreshold(threshold string) []string {
	switch normalizeFindingSeverity(threshold) {
	case "critical":
		return []string{"CRITICAL"}
	case "high":
		return []string{"CRITICAL", "HIGH"}
	case "medium":
		return []string{"CRITICAL", "HIGH", "MEDIUM"}
	default:
		return []string{"CRITICAL", "HIGH", "MEDIUM", "LOW"}
	}
}

func normalizeFindingSeverity(raw string) string {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "critical":
		return "critical"
	case "high":
		return "high"
	case "medium", "moderate":
		return "medium"
	case "low":
		return "low"
	default:
		return "unknown"
	}
}

func severityAtOrAbove(severity, threshold string) bool {
	return securitySeverityRank(normalizeFindingSeverity(severity)) >= securitySeverityRank(normalizeFindingSeverity(threshold))
}

func securitySeverityRank(severity string) int {
	switch normalizeFindingSeverity(severity) {
	case "critical":
		return 4
	case "high":
		return 3
	case "medium":
		return 2
	case "low":
		return 1
	default:
		return 0
	}
}

func asString(raw any) string {
	value, _ := raw.(string)
	return strings.TrimSpace(value)
}

func intMapToAnyMap(raw map[string]int) map[string]any {
	out := make(map[string]any, len(raw))
	for key, value := range raw {
		out[key] = value
	}
	return out
}

func truncateString(raw string, maxLen int) string {
	if maxLen <= 0 {
		return ""
	}
	if len(raw) <= maxLen {
		return raw
	}
	return raw[:maxLen]
}

func nonEmptyOrDefault(raw, fallback string) string {
	if strings.TrimSpace(raw) == "" {
		return fallback
	}
	return raw
}

func targetOrDefault(target, fallback string) string {
	trimmed := strings.TrimSpace(target)
	if trimmed == "" {
		return fallback
	}
	return trimmed
}
