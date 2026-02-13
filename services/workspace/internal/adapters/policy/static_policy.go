package policy

import (
	"context"
	"encoding/json"
	"path/filepath"
	"strings"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type StaticPolicy struct{}

func NewStaticPolicy() *StaticPolicy {
	return &StaticPolicy{}
}

func (p *StaticPolicy) Authorize(_ context.Context, input app.PolicyInput) (app.PolicyDecision, error) {
	if !scopeAllowed(input.Session.Principal.Roles, input.Capability.Scope) {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    "principal roles cannot access tool scope",
		}, nil
	}

	if input.Capability.RiskLevel == domain.RiskHigh && !hasRole(input.Session.Principal.Roles, "platform_admin") {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    "high risk capability requires platform_admin role",
		}, nil
	}

	if input.Capability.RequiresApproval && !input.Approved {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodeApprovalRequired,
			Reason:    "tool requires explicit approval",
		}, nil
	}

	if pathAllowed, reason := argsWithinAllowedPaths(input.Args, input.Session.AllowedPaths); !pathAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	return app.PolicyDecision{Allow: true}, nil
}

func scopeAllowed(roles []string, scope domain.Scope) bool {
	if scope == domain.ScopeWorkspace || scope == domain.ScopeRepo {
		return true
	}
	if scope == domain.ScopeCluster || scope == domain.ScopeExternal {
		return hasAnyRole(roles, "devops", "platform_admin")
	}
	return false
}

func hasAnyRole(roles []string, candidates ...string) bool {
	for _, c := range candidates {
		if hasRole(roles, c) {
			return true
		}
	}
	return false
}

func hasRole(roles []string, target string) bool {
	target = strings.ToLower(strings.TrimSpace(target))
	for _, role := range roles {
		if strings.ToLower(strings.TrimSpace(role)) == target {
			return true
		}
	}
	return false
}

func argsWithinAllowedPaths(raw json.RawMessage, allowedPaths []string) (bool, string) {
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}
	if len(allowedPaths) == 0 {
		allowedPaths = []string{"."}
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}

	paths := collectPaths(payload)
	for _, path := range paths {
		if path == "" {
			continue
		}
		if !isPathWithinAllowlist(path, allowedPaths) {
			return false, "path outside allowed_paths"
		}
	}

	return true, ""
}

func collectPaths(value any) []string {
	out := []string{}
	switch typed := value.(type) {
	case map[string]any:
		for key, nested := range typed {
			normalized := strings.ToLower(strings.TrimSpace(key))
			if normalized == "path" || normalized == "context_path" || normalized == "dockerfile_path" {
				if asString, ok := nested.(string); ok {
					out = append(out, asString)
				}
			}
			if normalized == "paths" {
				if list, ok := nested.([]any); ok {
					for _, item := range list {
						if asString, ok := item.(string); ok {
							out = append(out, asString)
						}
					}
				}
			}
			out = append(out, collectPaths(nested)...)
		}
	case []any:
		for _, item := range typed {
			out = append(out, collectPaths(item)...)
		}
	}
	return out
}

func isPathWithinAllowlist(path string, allowlist []string) bool {
	cleanedPath := filepath.Clean(path)
	for _, allowed := range allowlist {
		cleanedAllowed := filepath.Clean(allowed)
		if cleanedAllowed == "." {
			if !strings.HasPrefix(cleanedPath, "..") {
				return true
			}
			continue
		}
		if cleanedPath == cleanedAllowed || strings.HasPrefix(cleanedPath, cleanedAllowed+string(filepath.Separator)) {
			return true
		}
	}
	return false
}
