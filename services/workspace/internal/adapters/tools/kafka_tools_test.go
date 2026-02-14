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

type fakeKafkaClient struct {
	consume       func(req kafkaConsumeRequest) ([]kafkaConsumedMessage, error)
	topicMetadata func(req kafkaTopicMetadataRequest) ([]kafkaTopicPartitionMetadata, error)
}

func (f *fakeKafkaClient) Consume(_ context.Context, req kafkaConsumeRequest) ([]kafkaConsumedMessage, error) {
	if f.consume != nil {
		return f.consume(req)
	}
	return []kafkaConsumedMessage{}, nil
}

func (f *fakeKafkaClient) TopicMetadata(_ context.Context, req kafkaTopicMetadataRequest) ([]kafkaTopicPartitionMetadata, error) {
	if f.topicMetadata != nil {
		return f.topicMetadata(req)
	}
	return []kafkaTopicPartitionMetadata{}, nil
}

func TestKafkaConsumeHandler_Success(t *testing.T) {
	handler := NewKafkaConsumeHandler(&fakeKafkaClient{
		consume: func(req kafkaConsumeRequest) ([]kafkaConsumedMessage, error) {
			if len(req.Brokers) == 0 || req.Topic != "sandbox.events" || req.Timeout <= 0 {
				t.Fatalf("unexpected consume request: %#v", req)
			}
			return []kafkaConsumedMessage{
				{Key: []byte("k1"), Value: []byte("v1"), Partition: 0, Offset: 10, Time: time.Unix(1700000000, 0)},
			}, nil
		},
	})

	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.kafka":"kafka://broker-a:9092,broker-b:9092"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.kafka","topic":"sandbox.events","max_messages":1}`))
	if err != nil {
		t.Fatalf("unexpected kafka.consume error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %#v", result.Output)
	}
	if output["profile_id"] != "dev.kafka" {
		t.Fatalf("unexpected profile_id: %#v", output["profile_id"])
	}
	if output["topic"] != "sandbox.events" {
		t.Fatalf("unexpected topic: %#v", output["topic"])
	}
}

func TestKafkaConsumeHandler_DeniesTopicOutsideProfileScopes(t *testing.T) {
	handler := NewKafkaConsumeHandler(&fakeKafkaClient{})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.kafka":"broker-a:9092"}`,
		},
	}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.kafka","topic":"prod.events"}`))
	if err == nil {
		t.Fatal("expected topic policy denial")
	}
	if err.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

func TestKafkaTopicMetadataHandler_Success(t *testing.T) {
	handler := NewKafkaTopicMetadataHandler(&fakeKafkaClient{
		topicMetadata: func(req kafkaTopicMetadataRequest) ([]kafkaTopicPartitionMetadata, error) {
			if req.Topic != "sandbox.events" {
				t.Fatalf("unexpected topic: %s", req.Topic)
			}
			return []kafkaTopicPartitionMetadata{
				{PartitionID: 0, LeaderHost: "broker-a", LeaderPort: 9092, ReplicaIDs: []int{1, 2}, ISRIDs: []int{1}},
			}, nil
		},
	})

	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.kafka":"broker-a:9092"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.kafka","topic":"sandbox.events"}`))
	if err != nil {
		t.Fatalf("unexpected kafka.topic_metadata error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %#v", result.Output)
	}
	if output["partition_count"] != 1 {
		t.Fatalf("unexpected partition_count: %#v", output["partition_count"])
	}
}

func TestKafkaConsumeHandler_MapsExecutionErrors(t *testing.T) {
	handler := NewKafkaConsumeHandler(&fakeKafkaClient{
		consume: func(req kafkaConsumeRequest) ([]kafkaConsumedMessage, error) {
			return nil, errors.New("dial failed")
		},
	})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.kafka":"broker-a:9092"}`,
		},
	}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.kafka","topic":"sandbox.events"}`))
	if err == nil {
		t.Fatal("expected execution error")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}
