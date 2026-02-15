package tools

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeNATSClient struct {
	request func(serverURL, subject string, payload []byte, timeout time.Duration) ([]byte, error)
	pull    func(serverURL, subject string, timeout time.Duration, maxMessages int) ([]natsMessage, error)
}

func (f *fakeNATSClient) Request(_ context.Context, serverURL, subject string, payload []byte, timeout time.Duration) ([]byte, error) {
	if f.request != nil {
		return f.request(serverURL, subject, payload, timeout)
	}
	return []byte("ok"), nil
}

func (f *fakeNATSClient) SubscribePull(_ context.Context, serverURL, subject string, timeout time.Duration, maxMessages int) ([]natsMessage, error) {
	if f.pull != nil {
		return f.pull(serverURL, subject, timeout, maxMessages)
	}
	return []natsMessage{}, nil
}

func TestNATSRequestHandler_Success(t *testing.T) {
	handler := NewNATSRequestHandler(&fakeNATSClient{
		request: func(serverURL, subject string, payload []byte, timeout time.Duration) ([]byte, error) {
			if serverURL == "" || subject == "" || timeout <= 0 {
				t.Fatalf("unexpected request params: %q %q %v", serverURL, subject, timeout)
			}
			if string(payload) != "hello" {
				t.Fatalf("unexpected payload: %q", string(payload))
			}
			return []byte("response"), nil
		},
	})

	session := domain.Session{
		AllowedPaths: []string{"."},
		Metadata: map[string]string{
			"allowed_profiles":                  "dev.nats",
			"connection_profile_endpoints_json": `{"dev.nats":"nats://example:4222"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.nats","subject":"sandbox.echo","payload":"hello","timeout_ms":500,"max_bytes":16}`))
	if err != nil {
		t.Fatalf("unexpected nats.request error: %#v", err)
	}

	output := result.Output.(map[string]any)
	if output["profile_id"] != "dev.nats" {
		t.Fatalf("unexpected profile_id: %#v", output["profile_id"])
	}
	if output["subject"] != "sandbox.echo" {
		t.Fatalf("unexpected subject: %#v", output["subject"])
	}
	encoded := output["response_base64"].(string)
	decoded, decErr := base64.StdEncoding.DecodeString(encoded)
	if decErr != nil || string(decoded) != "response" {
		t.Fatalf("unexpected response data: %q err=%v", encoded, decErr)
	}
}

func TestNATSRequestHandler_DeniesSubjectOutsideProfileScope(t *testing.T) {
	handler := NewNATSRequestHandler(&fakeNATSClient{})
	session := domain.Session{
		AllowedPaths: []string{"."},
		Metadata: map[string]string{
			"allowed_profiles": "dev.nats",
		},
	}
	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.nats","subject":"prod.secret"}`))
	if err == nil {
		t.Fatal("expected policy error")
	}
	if err.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

func TestNATSSubscribePullHandler_Success(t *testing.T) {
	handler := NewNATSSubscribePullHandler(&fakeNATSClient{
		pull: func(serverURL, subject string, timeout time.Duration, maxMessages int) ([]natsMessage, error) {
			return []natsMessage{
				{Subject: subject, Data: []byte("m1")},
				{Subject: subject, Data: []byte("m2")},
			}, nil
		},
	})
	session := domain.Session{
		AllowedPaths: []string{"."},
		Metadata: map[string]string{
			"allowed_profiles":                  "dev.nats",
			"connection_profile_endpoints_json": `{"dev.nats":"nats://example:4222"}`,
		},
	}
	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.nats","subject":"sandbox.jobs","max_messages":2,"max_bytes":16}`))
	if err != nil {
		t.Fatalf("unexpected nats.subscribe_pull error: %#v", err)
	}

	output := result.Output.(map[string]any)
	if output["message_count"] != 2 {
		t.Fatalf("unexpected message_count: %#v", output["message_count"])
	}
}

func TestNATSSubscribePullHandler_ExecutionError(t *testing.T) {
	handler := NewNATSSubscribePullHandler(&fakeNATSClient{
		pull: func(serverURL, subject string, timeout time.Duration, maxMessages int) ([]natsMessage, error) {
			return nil, errors.New("connection down")
		},
	})
	session := domain.Session{
		AllowedPaths: []string{"."},
		Metadata: map[string]string{
			"allowed_profiles":                  "dev.nats",
			"connection_profile_endpoints_json": `{"dev.nats":"nats://example:4222"}`,
		},
	}
	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.nats","subject":"sandbox.jobs"}`))
	if err == nil {
		t.Fatal("expected execution error")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

func TestNATSHandlers_NamesAndLiveClientErrors(t *testing.T) {
	if NewNATSRequestHandler(nil).Name() != "nats.request" {
		t.Fatal("unexpected nats.request name")
	}
	if NewNATSSubscribePullHandler(nil).Name() != "nats.subscribe_pull" {
		t.Fatal("unexpected nats.subscribe_pull name")
	}

	client := &liveNATSClient{}
	ctx := context.Background()
	if _, err := client.Request(ctx, "://bad-url", "sandbox.echo", []byte("x"), 5*time.Millisecond); err == nil {
		t.Fatal("expected live NATS request error for invalid url")
	}
	if _, err := client.SubscribePull(ctx, "://bad-url", "sandbox.echo", 5*time.Millisecond, 1); err == nil {
		t.Fatal("expected live NATS subscribe error for invalid url")
	}
}

func TestNATSProfileAndPayloadHelpers(t *testing.T) {
	_, _, err := resolveNATSProfile(domain.Session{}, "")
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected profile_id validation error, got %#v", err)
	}

	sessionWrongKind := domain.Session{
		Metadata: map[string]string{
			"connection_profiles_json": `[{"id":"x","kind":"redis","read_only":true,"scopes":{"subjects":["sandbox.>"]}}]`,
		},
	}
	_, _, err = resolveNATSProfile(sessionWrongKind, "x")
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected wrong kind validation, got %#v", err)
	}

	profile := connectionProfile{
		ID:    "dev.nats",
		Kind:  "nats",
		Scopes: map[string]any{"subjects": []any{"sandbox.>", "dev.*"}},
	}
	if !subjectAllowedByProfile("sandbox.jobs", profile) {
		t.Fatal("expected subject to be allowed by profile")
	}
	if subjectAllowedByProfile("prod.jobs", profile) {
		t.Fatal("did not expect prod subject to be allowed")
	}

	if !natsSubjectPatternMatch("sandbox.>", "sandbox.jobs.created") {
		t.Fatal("expected > wildcard subject match")
	}
	if !natsSubjectPatternMatch("sandbox.*.created", "sandbox.jobs.created") {
		t.Fatal("expected * wildcard subject match")
	}

	raw, decErr := decodePayload(base64.StdEncoding.EncodeToString([]byte("hello")), "base64")
	if decErr != nil || string(raw) != "hello" {
		t.Fatalf("unexpected decodePayload base64 result: raw=%q err=%v", string(raw), decErr)
	}
	if _, decErr = decodePayload("%%%bad", "base64"); decErr == nil {
		t.Fatal("expected decodePayload base64 validation error")
	}
	if _, decErr = decodePayload("hello", "hex"); decErr == nil {
		t.Fatal("expected decodePayload unsupported encoding error")
	}
}
