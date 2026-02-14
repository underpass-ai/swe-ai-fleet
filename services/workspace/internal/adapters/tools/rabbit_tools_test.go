package tools

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeRabbitClient struct {
	consume   func(req rabbitConsumeRequest) ([]rabbitConsumedMessage, error)
	queueInfo func(req rabbitQueueInfoRequest) (rabbitQueueInfo, error)
}

func (f *fakeRabbitClient) Consume(_ context.Context, req rabbitConsumeRequest) ([]rabbitConsumedMessage, error) {
	if f.consume != nil {
		return f.consume(req)
	}
	return []rabbitConsumedMessage{}, nil
}

func (f *fakeRabbitClient) QueueInfo(_ context.Context, req rabbitQueueInfoRequest) (rabbitQueueInfo, error) {
	if f.queueInfo != nil {
		return f.queueInfo(req)
	}
	return rabbitQueueInfo{Name: req.Queue}, nil
}

func TestRabbitConsumeHandler_Success(t *testing.T) {
	handler := NewRabbitConsumeHandler(&fakeRabbitClient{
		consume: func(req rabbitConsumeRequest) ([]rabbitConsumedMessage, error) {
			if req.URL == "" || req.Queue != "sandbox.jobs" || req.Timeout <= 0 {
				t.Fatalf("unexpected consume request: %#v", req)
			}
			return []rabbitConsumedMessage{
				{
					Body:        []byte("hello"),
					Exchange:    "events",
					RoutingKey:  "sandbox.jobs",
					Redelivered: false,
					Timestamp:   time.Unix(1700000000, 0),
				},
			}, nil
		},
	})

	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.rabbit":"amqp://guest:guest@rabbit:5672/"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.rabbit","queue":"sandbox.jobs","max_messages":1}`))
	if err != nil {
		t.Fatalf("unexpected rabbit.consume error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %#v", result.Output)
	}
	if output["profile_id"] != "dev.rabbit" {
		t.Fatalf("unexpected profile_id: %#v", output["profile_id"])
	}
	if output["queue"] != "sandbox.jobs" {
		t.Fatalf("unexpected queue: %#v", output["queue"])
	}
}

func TestRabbitConsumeHandler_DeniesQueueOutsideProfileScopes(t *testing.T) {
	handler := NewRabbitConsumeHandler(&fakeRabbitClient{})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.rabbit":"amqp://guest:guest@rabbit:5672/"}`,
		},
	}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.rabbit","queue":"prod.jobs"}`))
	if err == nil {
		t.Fatal("expected queue policy denial")
	}
	if err.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

func TestRabbitQueueInfoHandler_Success(t *testing.T) {
	handler := NewRabbitQueueInfoHandler(&fakeRabbitClient{
		queueInfo: func(req rabbitQueueInfoRequest) (rabbitQueueInfo, error) {
			if req.Queue != "sandbox.jobs" {
				t.Fatalf("unexpected queue: %s", req.Queue)
			}
			return rabbitQueueInfo{Name: req.Queue, Messages: 5, Consumers: 2}, nil
		},
	})

	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.rabbit":"amqp://guest:guest@rabbit:5672/"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.rabbit","queue":"sandbox.jobs"}`))
	if err != nil {
		t.Fatalf("unexpected rabbit.queue_info error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %#v", result.Output)
	}
	if output["messages"] != 5 {
		t.Fatalf("unexpected messages count: %#v", output["messages"])
	}
}

func TestRabbitQueueInfoHandler_MapsExecutionErrors(t *testing.T) {
	handler := NewRabbitQueueInfoHandler(&fakeRabbitClient{
		queueInfo: func(req rabbitQueueInfoRequest) (rabbitQueueInfo, error) {
			return rabbitQueueInfo{}, errors.New("dial failed")
		},
	})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.rabbit":"amqp://guest:guest@rabbit:5672/"}`,
		},
	}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.rabbit","queue":"sandbox.jobs"}`))
	if err == nil {
		t.Fatal("expected execution error")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}
