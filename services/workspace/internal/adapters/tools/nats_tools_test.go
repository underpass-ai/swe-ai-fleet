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
