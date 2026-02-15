package tools

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	kafkago "github.com/segmentio/kafka-go"
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
			if len(req.Brokers) == 0 || req.Topic != "sandbox.events" || req.Timeout <= 0 || req.OffsetMode != "latest" || req.OffsetStart != kafkago.LastOffset {
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
	if output["offset_mode"] != "latest" {
		t.Fatalf("unexpected offset_mode: %#v", output["offset_mode"])
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

func TestKafkaConsumeHandler_OffsetModes(t *testing.T) {
	absoluteChecked := false
	timestampChecked := false
	handler := NewKafkaConsumeHandler(&fakeKafkaClient{
		consume: func(req kafkaConsumeRequest) ([]kafkaConsumedMessage, error) {
			switch req.Topic {
			case "sandbox.absolute":
				if req.OffsetMode != "absolute" || req.OffsetStart != 42 || req.OffsetAt != nil {
					t.Fatalf("unexpected absolute offset consume request: %#v", req)
				}
				absoluteChecked = true
			case "sandbox.timestamp":
				if req.OffsetMode != "timestamp" || req.OffsetAt == nil || req.OffsetStart != 0 {
					t.Fatalf("unexpected timestamp offset consume request: %#v", req)
				}
				expected := time.UnixMilli(1730000000000).UTC()
				if !req.OffsetAt.Equal(expected) {
					t.Fatalf("unexpected timestamp offset value: got=%s expected=%s", req.OffsetAt.UTC(), expected)
				}
				timestampChecked = true
			default:
				t.Fatalf("unexpected topic: %s", req.Topic)
			}
			return []kafkaConsumedMessage{}, nil
		},
	})

	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.kafka":"broker-a:9092"}`,
		},
	}

	_, err := handler.Invoke(
		context.Background(),
		session,
		json.RawMessage(`{"profile_id":"dev.kafka","topic":"sandbox.absolute","partition":0,"offset_mode":"absolute","offset":42,"max_messages":1}`),
	)
	if err != nil {
		t.Fatalf("unexpected absolute mode consume error: %#v", err)
	}

	_, err = handler.Invoke(
		context.Background(),
		session,
		json.RawMessage(`{"profile_id":"dev.kafka","topic":"sandbox.timestamp","partition":0,"offset_mode":"timestamp","timestamp_ms":1730000000000,"max_messages":1}`),
	)
	if err != nil {
		t.Fatalf("unexpected timestamp mode consume error: %#v", err)
	}

	if !absoluteChecked || !timestampChecked {
		t.Fatalf("expected both offset-mode branches to be exercised: absolute=%v timestamp=%v", absoluteChecked, timestampChecked)
	}
}

func TestKafkaHandlers_NamesAndLiveClientErrors(t *testing.T) {
	if NewKafkaConsumeHandler(nil).Name() != "kafka.consume" {
		t.Fatal("unexpected kafka.consume name")
	}
	if NewKafkaTopicMetadataHandler(nil).Name() != "kafka.topic_metadata" {
		t.Fatal("unexpected kafka.topic_metadata name")
	}

	client := &liveKafkaClient{}
	ctx := context.Background()
	messages, err := client.Consume(ctx, kafkaConsumeRequest{
		Brokers:     []string{"127.0.0.1:1"},
		Topic:       "sandbox.events",
		Partition:   0,
		OffsetStart: 0,
		MaxMessages: 1,
		Timeout:     5 * time.Millisecond,
	})
	if err != nil {
		t.Fatalf("unexpected live kafka consume error: %v", err)
	}
	if len(messages) != 0 {
		t.Fatalf("expected zero consumed messages from dead broker, got %d", len(messages))
	}

	_, err = client.TopicMetadata(ctx, kafkaTopicMetadataRequest{
		Brokers: []string{"127.0.0.1:1"},
		Topic:   "sandbox.events",
	})
	if err == nil {
		t.Fatal("expected live kafka metadata connection error")
	}
}

func TestKafkaHelpers_ProfileResolutionAndPatterning(t *testing.T) {
	_, _, err := resolveKafkaProfile(domain.Session{}, "")
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected profile_id validation error, got %#v", err)
	}

	sessionWrongKind := domain.Session{
		Metadata: map[string]string{
			"connection_profiles_json": `[{"id":"x","kind":"nats","read_only":true,"scopes":{"topics":["sandbox."]}}]`,
		},
	}
	_, _, err = resolveKafkaProfile(sessionWrongKind, "x")
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected wrong kind error, got %#v", err)
	}

	brokers := splitKafkaBrokers("kafka://broker-a:9092, tcp://broker-b:9092, broker-c:9092")
	if len(brokers) != 3 || brokers[0] != "broker-a:9092" || brokers[1] != "broker-b:9092" || brokers[2] != "broker-c:9092" {
		t.Fatalf("unexpected splitKafkaBrokers output: %#v", brokers)
	}

	profile := connectionProfile{Scopes: map[string]any{"topics": []any{"sandbox.", "dev.>"}}}
	if !topicAllowedByProfile("sandbox.jobs", profile) {
		t.Fatal("expected topicAllowedByProfile allow")
	}
	if topicAllowedByProfile("prod.jobs", profile) {
		t.Fatal("expected topicAllowedByProfile deny")
	}

	offsetSpec, offsetErr := resolveKafkaConsumeOffset("", "earliest", nil)
	if offsetErr != nil || offsetSpec.OffsetStart != kafkago.FirstOffset || offsetSpec.Mode != "earliest" {
		t.Fatalf("unexpected earliest offset parse: offset=%+v err=%v", offsetSpec, offsetErr)
	}
	offsetSpec, offsetErr = resolveKafkaConsumeOffset("", float64(77), nil)
	if offsetErr != nil || offsetSpec.Mode != "absolute" || offsetSpec.OffsetStart != 77 {
		t.Fatalf("unexpected absolute offset parse: offset=%+v err=%v", offsetSpec, offsetErr)
	}
	timestamp := int64(1730000000000)
	offsetSpec, offsetErr = resolveKafkaConsumeOffset("timestamp", nil, &timestamp)
	if offsetErr != nil || offsetSpec.Mode != "timestamp" || offsetSpec.OffsetAt == nil || !offsetSpec.OffsetAt.Equal(time.UnixMilli(timestamp).UTC()) {
		t.Fatalf("unexpected timestamp offset parse: offset=%+v err=%v", offsetSpec, offsetErr)
	}
	if _, offsetErr = resolveKafkaConsumeOffset("middle", nil, nil); offsetErr == nil {
		t.Fatal("expected resolveKafkaConsumeOffset validation error")
	}
	if _, offsetErr = resolveKafkaConsumeOffset("absolute", nil, nil); offsetErr == nil {
		t.Fatal("expected absolute offset missing value error")
	}
	if _, offsetErr = resolveKafkaConsumeOffset("timestamp", nil, nil); offsetErr == nil {
		t.Fatal("expected timestamp offset missing value error")
	}

	if !topicPatternMatch("sandbox.>", "sandbox.jobs.created") {
		t.Fatal("expected topicPatternMatch with .> wildcard")
	}
	if !topicPatternMatch("sandbox.*.created", "sandbox.jobs.created") {
		t.Fatal("expected topicPatternMatch with * wildcard")
	}
	if topicPatternMatch("sandbox.", "prod.jobs") {
		t.Fatal("did not expect topicPatternMatch for disallowed topic")
	}
}
