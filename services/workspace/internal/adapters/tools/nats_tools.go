package tools

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type NATSRequestHandler struct {
	client natsClient
}

type NATSPublishHandler struct {
	client natsClient
}

type NATSSubscribePullHandler struct {
	client natsClient
}

type natsClient interface {
	Request(ctx context.Context, serverURL, subject string, payload []byte, timeout time.Duration) ([]byte, error)
	Publish(ctx context.Context, serverURL, subject string, payload []byte, timeout time.Duration) error
	SubscribePull(ctx context.Context, serverURL, subject string, timeout time.Duration, maxMessages int) ([]natsMessage, error)
}

type natsMessage struct {
	Subject string
	Data    []byte
}

type liveNATSClient struct{}

func NewNATSRequestHandler(client natsClient) *NATSRequestHandler {
	return &NATSRequestHandler{client: ensureNATSClient(client)}
}

func NewNATSPublishHandler(client natsClient) *NATSPublishHandler {
	return &NATSPublishHandler{client: ensureNATSClient(client)}
}

func NewNATSSubscribePullHandler(client natsClient) *NATSSubscribePullHandler {
	return &NATSSubscribePullHandler{client: ensureNATSClient(client)}
}

func (h *NATSRequestHandler) Name() string {
	return "nats.request"
}

func (h *NATSPublishHandler) Name() string {
	return "nats.publish"
}

func (h *NATSRequestHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ProfileID       string `json:"profile_id"`
		Subject         string `json:"subject"`
		Payload         string `json:"payload"`
		PayloadEncoding string `json:"payload_encoding"`
		TimeoutMS       int    `json:"timeout_ms"`
		MaxBytes        int    `json:"max_bytes"`
	}{
		PayloadEncoding: "utf8",
		TimeoutMS:       2000,
		MaxBytes:        65536,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid nats.request args",
				Retryable: false,
			}
		}
	}

	subject := strings.TrimSpace(request.Subject)
	if subject == "" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "subject is required",
			Retryable: false,
		}
	}
	timeoutMS := clampInt(request.TimeoutMS, 100, 10000, 2000)
	maxBytes := clampInt(request.MaxBytes, 1, 1024*1024, 65536)

	profile, profileURL, profileErr := resolveNATSProfile(session, request.ProfileID)
	if profileErr != nil {
		return app.ToolRunResult{}, profileErr
	}
	if !subjectAllowedByProfile(subject, profile) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodePolicyDenied,
			Message:   "subject outside profile allowlist",
			Retryable: false,
		}
	}

	payloadBytes, payloadErr := decodePayload(request.Payload, request.PayloadEncoding)
	if payloadErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   payloadErr.Error(),
			Retryable: false,
		}
	}

	responseBytes, err := h.client.Request(ctx, profileURL, subject, payloadBytes, time.Duration(timeoutMS)*time.Millisecond)
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   fmt.Sprintf("nats request failed: %v", err),
			Retryable: true,
		}
	}

	truncated := false
	if len(responseBytes) > maxBytes {
		responseBytes = responseBytes[:maxBytes]
		truncated = true
	}
	responseBase64 := base64.StdEncoding.EncodeToString(responseBytes)

	return app.ToolRunResult{
		Logs: []domain.LogLine{{
			At:      time.Now().UTC(),
			Channel: "stdout",
			Message: "nats request completed",
		}},
		Output: map[string]any{
			"profile_id":      profile.ID,
			"subject":         subject,
			"response_base64": responseBase64,
			"response_bytes":  len(responseBytes),
			"truncated":       truncated,
		},
	}, nil
}

func (h *NATSPublishHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ProfileID       string `json:"profile_id"`
		Subject         string `json:"subject"`
		Payload         string `json:"payload"`
		PayloadEncoding string `json:"payload_encoding"`
		TimeoutMS       int    `json:"timeout_ms"`
		MaxBytes        int    `json:"max_bytes"`
	}{
		PayloadEncoding: "utf8",
		TimeoutMS:       2000,
		MaxBytes:        65536,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid nats.publish args",
				Retryable: false,
			}
		}
	}

	subject := strings.TrimSpace(request.Subject)
	if subject == "" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "subject is required",
			Retryable: false,
		}
	}
	timeoutMS := clampInt(request.TimeoutMS, 100, 10000, 2000)
	maxBytes := clampInt(request.MaxBytes, 1, 1024*1024, 65536)

	profile, profileURL, profileErr := resolveNATSProfile(session, request.ProfileID)
	if profileErr != nil {
		return app.ToolRunResult{}, profileErr
	}
	if profile.ReadOnly {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodePolicyDenied,
			Message:   "profile is read_only",
			Retryable: false,
		}
	}
	if !subjectAllowedByProfile(subject, profile) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodePolicyDenied,
			Message:   "subject outside profile allowlist",
			Retryable: false,
		}
	}

	payloadBytes, payloadErr := decodePayload(request.Payload, request.PayloadEncoding)
	if payloadErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   payloadErr.Error(),
			Retryable: false,
		}
	}
	if len(payloadBytes) > maxBytes {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "payload exceeds max_bytes",
			Retryable: false,
		}
	}

	if err := h.client.Publish(ctx, profileURL, subject, payloadBytes, time.Duration(timeoutMS)*time.Millisecond); err != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   fmt.Sprintf("nats publish failed: %v", err),
			Retryable: true,
		}
	}

	return app.ToolRunResult{
		Logs: []domain.LogLine{{
			At:      time.Now().UTC(),
			Channel: "stdout",
			Message: "nats publish completed",
		}},
		Output: map[string]any{
			"profile_id":       profile.ID,
			"subject":          subject,
			"payload_bytes":    len(payloadBytes),
			"payload_encoding": strings.ToLower(strings.TrimSpace(request.PayloadEncoding)),
			"published":        true,
		},
	}, nil
}

func (h *NATSSubscribePullHandler) Name() string {
	return "nats.subscribe_pull"
}

func (h *NATSSubscribePullHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ProfileID   string `json:"profile_id"`
		Subject     string `json:"subject"`
		MaxMessages int    `json:"max_messages"`
		MaxBytes    int    `json:"max_bytes"`
		TimeoutMS   int    `json:"timeout_ms"`
	}{
		MaxMessages: 10,
		MaxBytes:    262144,
		TimeoutMS:   2000,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid nats.subscribe_pull args",
				Retryable: false,
			}
		}
	}

	subject := strings.TrimSpace(request.Subject)
	if subject == "" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "subject is required",
			Retryable: false,
		}
	}
	maxMessages := clampInt(request.MaxMessages, 1, 100, 10)
	maxBytes := clampInt(request.MaxBytes, 1, 1024*1024, 262144)
	timeoutMS := clampInt(request.TimeoutMS, 100, 10000, 2000)

	profile, profileURL, profileErr := resolveNATSProfile(session, request.ProfileID)
	if profileErr != nil {
		return app.ToolRunResult{}, profileErr
	}
	if !subjectAllowedByProfile(subject, profile) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodePolicyDenied,
			Message:   "subject outside profile allowlist",
			Retryable: false,
		}
	}

	messages, err := h.client.SubscribePull(
		ctx,
		profileURL,
		subject,
		time.Duration(timeoutMS)*time.Millisecond,
		maxMessages,
	)
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   fmt.Sprintf("nats subscribe_pull failed: %v", err),
			Retryable: true,
		}
	}

	outMessages := make([]map[string]any, 0, len(messages))
	totalBytes := 0
	truncated := false
	for _, msg := range messages {
		if totalBytes >= maxBytes {
			truncated = true
			break
		}

		data := msg.Data
		remaining := maxBytes - totalBytes
		msgTruncated := false
		if len(data) > remaining {
			data = data[:remaining]
			msgTruncated = true
			truncated = true
		}
		totalBytes += len(data)

		outMessages = append(outMessages, map[string]any{
			"subject":      msg.Subject,
			"data_base64":  base64.StdEncoding.EncodeToString(data),
			"size_bytes":   len(data),
			"data_trimmed": msgTruncated,
		})
	}

	return app.ToolRunResult{
		Logs: []domain.LogLine{{
			At:      time.Now().UTC(),
			Channel: "stdout",
			Message: "nats subscribe_pull completed",
		}},
		Output: map[string]any{
			"profile_id":    profile.ID,
			"subject":       subject,
			"messages":      outMessages,
			"message_count": len(outMessages),
			"total_bytes":   totalBytes,
			"truncated":     truncated,
		},
	}, nil
}

func ensureNATSClient(client natsClient) natsClient {
	if client != nil {
		return client
	}
	return &liveNATSClient{}
}

func (c *liveNATSClient) Request(ctx context.Context, serverURL, subject string, payload []byte, timeout time.Duration) ([]byte, error) {
	nc, err := nats.Connect(serverURL, nats.Name("workspace-tool-nats-request"))
	if err != nil {
		return nil, err
	}
	defer nc.Drain()

	requestCtx := ctx
	cancel := func() {}
	if timeout > 0 {
		requestCtx, cancel = context.WithTimeout(ctx, timeout)
	}
	defer cancel()

	msg, err := nc.RequestWithContext(requestCtx, subject, payload)
	if err != nil {
		return nil, err
	}
	return msg.Data, nil
}

func (c *liveNATSClient) Publish(ctx context.Context, serverURL, subject string, payload []byte, timeout time.Duration) error {
	nc, err := nats.Connect(serverURL, nats.Name("workspace-tool-nats-publish"))
	if err != nil {
		return err
	}
	defer nc.Drain()

	if err := nc.Publish(subject, payload); err != nil {
		return err
	}

	flushCtx := ctx
	cancel := func() {}
	if timeout > 0 {
		flushCtx, cancel = context.WithTimeout(ctx, timeout)
	}
	defer cancel()
	return nc.FlushWithContext(flushCtx)
}

func (c *liveNATSClient) SubscribePull(ctx context.Context, serverURL, subject string, timeout time.Duration, maxMessages int) ([]natsMessage, error) {
	nc, err := nats.Connect(serverURL, nats.Name("workspace-tool-nats-subscribe"))
	if err != nil {
		return nil, err
	}
	defer nc.Drain()

	sub, err := nc.SubscribeSync(subject)
	if err != nil {
		return nil, err
	}
	if err := nc.Flush(); err != nil {
		return nil, err
	}

	deadline := time.Now().Add(timeout)
	out := make([]natsMessage, 0, maxMessages)
	for len(out) < maxMessages {
		remaining := time.Until(deadline)
		if timeout <= 0 {
			remaining = time.Second
		}
		if remaining <= 0 {
			break
		}

		msg, nextErr := sub.NextMsg(remaining)
		if nextErr != nil {
			if nextErr == nats.ErrTimeout || strings.Contains(strings.ToLower(nextErr.Error()), "timeout") {
				break
			}
			return nil, nextErr
		}
		out = append(out, natsMessage{Subject: msg.Subject, Data: msg.Data})
	}
	return out, nil
}

func resolveNATSProfile(session domain.Session, requestedProfileID string) (connectionProfile, string, *domain.Error) {
	profileID := strings.TrimSpace(requestedProfileID)
	if profileID == "" {
		return connectionProfile{}, "", &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "profile_id is required",
			Retryable: false,
		}
	}

	profiles := filterProfilesByAllowlist(resolveConnectionProfiles(session), session.Metadata)
	for _, profile := range profiles {
		if profile.ID != profileID {
			continue
		}
		if strings.TrimSpace(strings.ToLower(profile.Kind)) != "nats" {
			return connectionProfile{}, "", &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "profile is not a nats profile",
				Retryable: false,
			}
		}
		if endpoint := resolveProfileEndpoint(session.Metadata, profileID); endpoint != "" {
			return profile, endpoint, nil
		}
		if profileID == "dev.nats" {
			return profile, "nats://nats.swe-ai-fleet.svc.cluster.local:4222", nil
		}
		return connectionProfile{}, "", &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   "nats profile endpoint not configured",
			Retryable: false,
		}
	}

	return connectionProfile{}, "", &domain.Error{
		Code:      app.ErrorCodeNotFound,
		Message:   "connection profile not found",
		Retryable: false,
	}
}

func resolveProfileEndpoint(_ map[string]string, profileID string) string {
	raw := strings.TrimSpace(os.Getenv("WORKSPACE_CONN_PROFILE_ENDPOINTS_JSON"))
	if raw == "" {
		return ""
	}

	var parsed map[string]string
	if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
		return ""
	}
	endpoint := strings.TrimSpace(parsed[profileID])
	if endpoint == "" {
		return ""
	}
	if !profileEndpointAllowed(profileID, endpoint) {
		return ""
	}
	return endpoint
}

func profileEndpointAllowed(profileID string, endpoint string) bool {
	raw := strings.TrimSpace(os.Getenv("WORKSPACE_CONN_PROFILE_HOST_ALLOWLIST_JSON"))
	if raw == "" {
		return true
	}

	var allowlist map[string][]string
	if err := json.Unmarshal([]byte(raw), &allowlist); err != nil {
		return false
	}
	rules, found := allowlist[strings.TrimSpace(profileID)]
	if !found || len(rules) == 0 {
		return false
	}

	host := endpointHost(endpoint)
	if host == "" {
		return false
	}
	for _, rule := range rules {
		if hostMatchesAllowRule(host, rule) {
			return true
		}
	}
	return false
}

func endpointHost(endpoint string) string {
	trimmed := strings.TrimSpace(endpoint)
	if trimmed == "" {
		return ""
	}
	parsed, err := url.Parse(trimmed)
	if err == nil && parsed != nil && strings.TrimSpace(parsed.Hostname()) != "" {
		return strings.ToLower(strings.TrimSpace(parsed.Hostname()))
	}

	parsed, err = url.Parse("//" + trimmed)
	if err != nil || parsed == nil {
		return ""
	}
	return strings.ToLower(strings.TrimSpace(parsed.Hostname()))
}

func hostMatchesAllowRule(host string, rawRule string) bool {
	rule := strings.ToLower(strings.TrimSpace(rawRule))
	if rule == "" {
		return false
	}

	if _, cidr, err := net.ParseCIDR(rule); err == nil {
		ip := net.ParseIP(host)
		return ip != nil && cidr.Contains(ip)
	}
	if strings.HasPrefix(rule, "*.") {
		suffix := strings.TrimPrefix(rule, "*.")
		return host == suffix || strings.HasSuffix(host, "."+suffix)
	}
	return host == rule
}

func subjectAllowedByProfile(subject string, profile connectionProfile) bool {
	raw, found := profile.Scopes["subjects"]
	if !found {
		return false
	}
	list, ok := raw.([]string)
	if !ok {
		// if profile comes from JSON decode to map[string]any, support []any.
		asAny, okAny := raw.([]any)
		if !okAny {
			return false
		}
		list = make([]string, 0, len(asAny))
		for _, entry := range asAny {
			strValue, okStr := entry.(string)
			if okStr {
				list = append(list, strValue)
			}
		}
	}
	for _, pattern := range list {
		if natsSubjectPatternMatch(pattern, subject) {
			return true
		}
	}
	return false
}

func natsSubjectPatternMatch(pattern, subject string) bool {
	pattern = strings.TrimSpace(pattern)
	subject = strings.TrimSpace(subject)
	if pattern == "" || subject == "" {
		return false
	}
	if pattern == subject {
		return true
	}

	patternTokens := strings.Split(pattern, ".")
	subjectTokens := strings.Split(subject, ".")
	for idx, token := range patternTokens {
		switch token {
		case ">":
			return true
		case "*":
			if idx >= len(subjectTokens) {
				return false
			}
		default:
			if idx >= len(subjectTokens) || subjectTokens[idx] != token {
				return false
			}
		}
	}
	return len(patternTokens) == len(subjectTokens)
}

func decodePayload(payload, encoding string) ([]byte, error) {
	enc := strings.ToLower(strings.TrimSpace(encoding))
	if enc == "" || enc == "utf8" || enc == "utf-8" {
		return []byte(payload), nil
	}
	if enc == "base64" {
		decoded, err := base64.StdEncoding.DecodeString(payload)
		if err != nil {
			return nil, fmt.Errorf("invalid base64 payload")
		}
		return decoded, nil
	}
	return nil, fmt.Errorf("unsupported payload_encoding")
}

func clampInt(value, min, max, fallback int) int {
	if value == 0 {
		value = fallback
	}
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
