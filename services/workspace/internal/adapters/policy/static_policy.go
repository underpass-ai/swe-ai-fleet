package policy

import (
	"context"
	"encoding/json"
	"fmt"
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

	if pathAllowed, reason := argsWithinAllowedPaths(input.Args, input.Session.AllowedPaths, input.Capability.Policy.PathFields); !pathAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if argsAllowed, reason := argsAllowedByPolicy(input.Args, input.Capability.Policy.ArgFields); !argsAllowed {
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

func argsWithinAllowedPaths(raw json.RawMessage, allowedPaths []string, pathFields []domain.PolicyPathField) (bool, string) {
	if len(pathFields) == 0 {
		return true, ""
	}
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

	for _, field := range pathFields {
		paths, err := extractPathFieldValues(payload, field)
		if err != nil {
			return false, "invalid path field payload"
		}
		for _, path := range paths {
			if path == "" {
				continue
			}
			if !isPathWithinAllowlist(path, allowedPaths) {
				return false, "path outside allowed_paths"
			}
		}
	}

	return true, ""
}

func extractPathFieldValues(payload any, field domain.PolicyPathField) ([]string, error) {
	fieldName := strings.TrimSpace(field.Field)
	if fieldName == "" {
		return nil, nil
	}

	value, found := lookupField(payload, strings.Split(fieldName, "."))
	if !found {
		return nil, nil
	}

	if field.Multi {
		list, ok := value.([]any)
		if !ok {
			return nil, fmt.Errorf("field %s must be an array", fieldName)
		}
		paths := make([]string, 0, len(list))
		for _, entry := range list {
			asString, ok := entry.(string)
			if !ok {
				return nil, fmt.Errorf("field %s must contain strings", fieldName)
			}
			paths = append(paths, asString)
		}
		return paths, nil
	}

	asString, ok := value.(string)
	if !ok {
		return nil, fmt.Errorf("field %s must be a string", fieldName)
	}
	return []string{asString}, nil
}

func argsAllowedByPolicy(raw json.RawMessage, argFields []domain.PolicyArgField) (bool, string) {
	if len(argFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}

	for _, field := range argFields {
		values, err := extractArgFieldValues(payload, field)
		if err != nil {
			return false, "invalid args field payload"
		}
		if field.MaxItems > 0 && len(values) > field.MaxItems {
			return false, "argument list exceeds allowed length"
		}
		for _, value := range values {
			if !argValueAllowed(value, field) {
				return false, "argument not allowed by policy"
			}
		}
	}
	return true, ""
}

func extractArgFieldValues(payload any, field domain.PolicyArgField) ([]string, error) {
	fieldName := strings.TrimSpace(field.Field)
	if fieldName == "" {
		return nil, nil
	}

	value, found := lookupField(payload, strings.Split(fieldName, "."))
	if !found {
		return nil, nil
	}

	if field.Multi {
		list, ok := value.([]any)
		if !ok {
			return nil, fmt.Errorf("field %s must be an array", fieldName)
		}
		values := make([]string, 0, len(list))
		for _, entry := range list {
			strValue, ok := entry.(string)
			if !ok {
				return nil, fmt.Errorf("field %s must contain strings", fieldName)
			}
			values = append(values, strValue)
		}
		return values, nil
	}

	strValue, ok := value.(string)
	if !ok {
		return nil, fmt.Errorf("field %s must be a string", fieldName)
	}
	return []string{strValue}, nil
}

func argValueAllowed(value string, field domain.PolicyArgField) bool {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return false
	}
	if field.MaxLength > 0 && len(trimmed) > field.MaxLength {
		return false
	}

	for _, deniedChar := range field.DenyCharacters {
		if deniedChar != "" && strings.Contains(trimmed, deniedChar) {
			return false
		}
	}
	for _, deniedPrefix := range field.DeniedPrefix {
		if deniedPrefix != "" && strings.HasPrefix(trimmed, deniedPrefix) {
			return false
		}
	}
	if len(field.AllowedValues) > 0 {
		for _, allowed := range field.AllowedValues {
			if trimmed == allowed {
				return true
			}
		}
		return false
	}
	if len(field.AllowedPrefix) > 0 {
		for _, allowed := range field.AllowedPrefix {
			if allowed != "" && strings.HasPrefix(trimmed, allowed) {
				return true
			}
		}
		return false
	}
	return true
}

func lookupField(payload any, path []string) (any, bool) {
	current := payload
	for _, segment := range path {
		object, ok := current.(map[string]any)
		if !ok {
			return nil, false
		}
		next, found := object[segment]
		if !found {
			return nil, false
		}
		current = next
	}
	return current, true
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
