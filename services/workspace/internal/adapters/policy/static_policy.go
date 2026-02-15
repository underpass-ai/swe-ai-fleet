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

	if profilesAllowed, reason := argsAllowedByProfilePolicy(input.Args, input.Session.Metadata, input.Capability.Policy.ProfileFields); !profilesAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if subjectsAllowed, reason := argsAllowedBySubjectPolicy(input.Args, input.Session.Metadata, input.Capability.Policy.SubjectFields); !subjectsAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if topicsAllowed, reason := argsAllowedByTopicPolicy(input.Args, input.Session.Metadata, input.Capability.Policy.TopicFields); !topicsAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if queuesAllowed, reason := argsAllowedByQueuePolicy(input.Args, input.Session.Metadata, input.Capability.Policy.QueueFields); !queuesAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if keyPrefixesAllowed, reason := argsAllowedByKeyPrefixPolicy(input.Args, input.Session.Metadata, input.Capability.Policy.KeyPrefixFields); !keyPrefixesAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if namespacesAllowed, reason := argsAllowedByNamespacePolicy(input.Args, input.Session.Metadata, input.Capability.Policy.NamespaceFields); !namespacesAllowed {
		return app.PolicyDecision{
			Allow:     false,
			ErrorCode: app.ErrorCodePolicyDenied,
			Reason:    reason,
		}, nil
	}

	if registriesAllowed, reason := argsAllowedByRegistryPolicy(input.Args, input.Session.Metadata, input.Capability.Policy.RegistryFields); !registriesAllowed {
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

func argsAllowedByProfilePolicy(raw json.RawMessage, metadata map[string]string, profileFields []domain.PolicyProfileField) (bool, string) {
	if len(profileFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedProfiles := parseAllowedProfiles(metadata)
	// Backward-compatible default while profile governance is rolled out.
	if len(allowedProfiles) == 0 {
		return true, ""
	}
	if allowedProfiles["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}

	for _, field := range profileFields {
		values, err := extractProfileFieldValues(payload, field)
		if err != nil {
			return false, "invalid profile field payload"
		}
		for _, value := range values {
			candidate := strings.TrimSpace(value)
			if candidate == "" {
				continue
			}
			if !allowedProfiles[candidate] {
				return false, "profile not allowed"
			}
		}
	}

	return true, ""
}

func extractProfileFieldValues(payload any, field domain.PolicyProfileField) ([]string, error) {
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

func parseAllowedProfiles(metadata map[string]string) map[string]bool {
	if len(metadata) == 0 {
		return map[string]bool{}
	}
	raw := strings.TrimSpace(metadata["allowed_profiles"])
	if raw == "" {
		return map[string]bool{}
	}

	result := make(map[string]bool)
	for _, item := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(item)
		if candidate == "" {
			continue
		}
		result[candidate] = true
	}
	return result
}

func argsAllowedBySubjectPolicy(raw json.RawMessage, metadata map[string]string, subjectFields []domain.PolicySubjectField) (bool, string) {
	if len(subjectFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedSubjects := parseAllowedNATSSubjects(metadata)
	// Backward-compatible default while subject governance is rolled out.
	if len(allowedSubjects) == 0 {
		return true, ""
	}
	if allowedSubjects["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}

	for _, field := range subjectFields {
		values, err := extractSubjectFieldValues(payload, field)
		if err != nil {
			return false, "invalid subject field payload"
		}
		for _, value := range values {
			subject := strings.TrimSpace(value)
			if subject == "" {
				continue
			}
			if !natsSubjectAllowed(subject, allowedSubjects) {
				return false, "subject not allowed"
			}
		}
	}

	return true, ""
}

func extractSubjectFieldValues(payload any, field domain.PolicySubjectField) ([]string, error) {
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

func parseAllowedNATSSubjects(metadata map[string]string) map[string]bool {
	if len(metadata) == 0 {
		return map[string]bool{}
	}
	raw := strings.TrimSpace(metadata["allowed_nats_subjects"])
	if raw == "" {
		return map[string]bool{}
	}

	result := make(map[string]bool)
	for _, item := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(item)
		if candidate == "" {
			continue
		}
		result[candidate] = true
	}
	return result
}

func natsSubjectAllowed(subject string, allowlist map[string]bool) bool {
	for pattern := range allowlist {
		if natsSubjectMatch(pattern, subject) {
			return true
		}
	}
	return false
}

func argsAllowedByTopicPolicy(raw json.RawMessage, metadata map[string]string, topicFields []domain.PolicyTopicField) (bool, string) {
	if len(topicFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedTopics := parseAllowlist(metadata, "allowed_kafka_topics")
	// Backward-compatible default while topic governance is rolled out.
	if len(allowedTopics) == 0 || allowedTopics["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}
	for _, field := range topicFields {
		values, err := extractTopicFieldValues(payload, field)
		if err != nil {
			return false, "invalid topic field payload"
		}
		for _, value := range values {
			topic := strings.TrimSpace(value)
			if topic == "" {
				continue
			}
			if !patternAllowlistMatch(topic, allowedTopics) {
				return false, "topic not allowed"
			}
		}
	}

	return true, ""
}

func extractTopicFieldValues(payload any, field domain.PolicyTopicField) ([]string, error) {
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

func argsAllowedByQueuePolicy(raw json.RawMessage, metadata map[string]string, queueFields []domain.PolicyQueueField) (bool, string) {
	if len(queueFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedQueues := parseAllowlist(metadata, "allowed_rabbit_queues")
	// Backward-compatible default while queue governance is rolled out.
	if len(allowedQueues) == 0 || allowedQueues["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}
	for _, field := range queueFields {
		values, err := extractQueueFieldValues(payload, field)
		if err != nil {
			return false, "invalid queue field payload"
		}
		for _, value := range values {
			queue := strings.TrimSpace(value)
			if queue == "" {
				continue
			}
			if !patternAllowlistMatch(queue, allowedQueues) {
				return false, "queue not allowed"
			}
		}
	}

	return true, ""
}

func extractQueueFieldValues(payload any, field domain.PolicyQueueField) ([]string, error) {
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

func argsAllowedByKeyPrefixPolicy(raw json.RawMessage, metadata map[string]string, keyPrefixFields []domain.PolicyKeyPrefixField) (bool, string) {
	if len(keyPrefixFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedPrefixes := parseAllowlist(metadata, "allowed_redis_key_prefixes")
	// Backward-compatible default while key-prefix governance is rolled out.
	if len(allowedPrefixes) == 0 || allowedPrefixes["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}
	for _, field := range keyPrefixFields {
		values, err := extractKeyPrefixFieldValues(payload, field)
		if err != nil {
			return false, "invalid key prefix field payload"
		}
		for _, value := range values {
			key := strings.TrimSpace(value)
			if key == "" {
				continue
			}
			if !prefixAllowlistMatch(key, allowedPrefixes) {
				return false, "key prefix not allowed"
			}
		}
	}

	return true, ""
}

func extractKeyPrefixFieldValues(payload any, field domain.PolicyKeyPrefixField) ([]string, error) {
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

func argsAllowedByNamespacePolicy(raw json.RawMessage, metadata map[string]string, namespaceFields []string) (bool, string) {
	if len(namespaceFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedNamespaces := parseAllowlist(metadata, "allowed_k8s_namespaces")
	// Backward-compatible default while namespace governance is rolled out.
	if len(allowedNamespaces) == 0 || allowedNamespaces["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}

	for _, field := range namespaceFields {
		values, err := extractStringFieldValues(payload, field)
		if err != nil {
			return false, "invalid namespace field payload"
		}
		for _, value := range values {
			namespace := strings.TrimSpace(value)
			if namespace == "" {
				continue
			}
			if !patternAllowlistMatch(namespace, allowedNamespaces) {
				return false, "namespace not allowed"
			}
		}
	}

	return true, ""
}

func argsAllowedByRegistryPolicy(raw json.RawMessage, metadata map[string]string, registryFields []string) (bool, string) {
	if len(registryFields) == 0 {
		return true, ""
	}
	if len(raw) == 0 || string(raw) == "null" {
		return true, ""
	}

	allowedRegistries := parseAllowlist(metadata, "allowed_image_registries")
	// Backward-compatible default while registry governance is rolled out.
	if len(allowedRegistries) == 0 || allowedRegistries["*"] {
		return true, ""
	}

	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "invalid args payload"
	}

	for _, field := range registryFields {
		values, err := extractStringFieldValues(payload, field)
		if err != nil {
			return false, "invalid registry field payload"
		}
		for _, value := range values {
			candidate := strings.TrimSpace(value)
			if candidate == "" {
				continue
			}
			registry := extractRegistryFromImageRef(candidate)
			if patternAllowlistMatch(candidate, allowedRegistries) || patternAllowlistMatch(registry, allowedRegistries) {
				continue
			}
			return false, "registry not allowed"
		}
	}

	return true, ""
}

func extractStringFieldValues(payload any, fieldPath string) ([]string, error) {
	fieldPath = strings.TrimSpace(fieldPath)
	if fieldPath == "" {
		return nil, nil
	}

	value, found := lookupField(payload, strings.Split(fieldPath, "."))
	if !found {
		return nil, nil
	}

	switch typed := value.(type) {
	case string:
		return []string{typed}, nil
	case []any:
		values := make([]string, 0, len(typed))
		for _, entry := range typed {
			strValue, ok := entry.(string)
			if !ok {
				return nil, fmt.Errorf("field %s must contain strings", fieldPath)
			}
			values = append(values, strValue)
		}
		return values, nil
	default:
		return nil, fmt.Errorf("field %s must be a string or array of strings", fieldPath)
	}
}

func extractRegistryFromImageRef(imageRef string) string {
	trimmed := strings.TrimSpace(imageRef)
	if trimmed == "" {
		return ""
	}
	withoutDigest := strings.SplitN(trimmed, "@", 2)[0]
	segments := strings.Split(withoutDigest, "/")
	if len(segments) == 0 {
		return ""
	}
	first := strings.TrimSpace(segments[0])
	if len(segments) == 1 {
		return "docker.io"
	}
	if strings.Contains(first, ".") || strings.Contains(first, ":") || first == "localhost" {
		return first
	}
	return "docker.io"
}

func parseAllowlist(metadata map[string]string, metadataKey string) map[string]bool {
	if len(metadata) == 0 {
		return map[string]bool{}
	}
	raw := strings.TrimSpace(metadata[metadataKey])
	if raw == "" {
		return map[string]bool{}
	}

	result := make(map[string]bool)
	for _, item := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(item)
		if candidate == "" {
			continue
		}
		result[candidate] = true
	}
	return result
}

func patternAllowlistMatch(value string, allowlist map[string]bool) bool {
	for pattern := range allowlist {
		if wildcardPatternMatch(pattern, value) {
			return true
		}
	}
	return false
}

func prefixAllowlistMatch(value string, allowlist map[string]bool) bool {
	for prefix := range allowlist {
		if prefix == "*" {
			return true
		}
		if strings.HasPrefix(value, prefix) {
			return true
		}
	}
	return false
}

func wildcardPatternMatch(pattern string, value string) bool {
	pattern = strings.TrimSpace(pattern)
	value = strings.TrimSpace(value)
	if pattern == "" || value == "" {
		return false
	}
	if pattern == "*" || pattern == value {
		return true
	}
	if strings.HasSuffix(pattern, ".>") {
		return strings.HasPrefix(value, strings.TrimSuffix(pattern, ">"))
	}
	if strings.Contains(pattern, "*") {
		parts := strings.Split(pattern, "*")
		if len(parts) == 2 {
			return strings.HasPrefix(value, parts[0]) && strings.HasSuffix(value, parts[1])
		}
	}
	// Topic/queue defaults are prefix-style patterns like "sandbox.".
	if strings.HasSuffix(pattern, ".") || strings.HasSuffix(pattern, ":") || strings.HasSuffix(pattern, "/") {
		return strings.HasPrefix(value, pattern)
	}
	return false
}

func natsSubjectMatch(pattern string, subject string) bool {
	if pattern == subject {
		return true
	}
	patternTokens := strings.Split(strings.TrimSpace(pattern), ".")
	subjectTokens := strings.Split(strings.TrimSpace(subject), ".")
	if len(patternTokens) == 0 || len(subjectTokens) == 0 {
		return false
	}

	for idx, token := range patternTokens {
		switch token {
		case ">":
			return true
		case "*":
			if idx >= len(subjectTokens) {
				return false
			}
			continue
		default:
			if idx >= len(subjectTokens) || subjectTokens[idx] != token {
				return false
			}
		}
	}

	return len(patternTokens) == len(subjectTokens)
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
