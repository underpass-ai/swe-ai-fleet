package tools

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	kafkago "github.com/segmentio/kafka-go"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type KafkaConsumeHandler struct {
	client kafkaClient
}

type KafkaTopicMetadataHandler struct {
	client kafkaClient
}

type kafkaClient interface {
	Consume(ctx context.Context, req kafkaConsumeRequest) ([]kafkaConsumedMessage, error)
	TopicMetadata(ctx context.Context, req kafkaTopicMetadataRequest) ([]kafkaTopicPartitionMetadata, error)
}

type kafkaConsumeRequest struct {
	Brokers     []string
	Topic       string
	Partition   int
	OffsetStart int64
	MaxMessages int
	Timeout     time.Duration
}

type kafkaTopicMetadataRequest struct {
	Brokers []string
	Topic   string
}

type kafkaConsumedMessage struct {
	Key       []byte
	Value     []byte
	Partition int
	Offset    int64
	Time      time.Time
}

type kafkaTopicPartitionMetadata struct {
	PartitionID int
	LeaderHost  string
	LeaderPort  int
	ReplicaIDs  []int
	ISRIDs      []int
}

type liveKafkaClient struct{}

func NewKafkaConsumeHandler(client kafkaClient) *KafkaConsumeHandler {
	return &KafkaConsumeHandler{client: ensureKafkaClient(client)}
}

func NewKafkaTopicMetadataHandler(client kafkaClient) *KafkaTopicMetadataHandler {
	return &KafkaTopicMetadataHandler{client: ensureKafkaClient(client)}
}

func (h *KafkaConsumeHandler) Name() string {
	return "kafka.consume"
}

func (h *KafkaConsumeHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ProfileID   string `json:"profile_id"`
		Topic       string `json:"topic"`
		Partition   int    `json:"partition"`
		Offset      string `json:"offset"`
		MaxMessages int    `json:"max_messages"`
		MaxBytes    int    `json:"max_bytes"`
		TimeoutMS   int    `json:"timeout_ms"`
	}{
		Partition:   0,
		Offset:      "latest",
		MaxMessages: 20,
		MaxBytes:    262144,
		TimeoutMS:   2000,
	}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid kafka.consume args",
				Retryable: false,
			}
		}
	}

	topic := strings.TrimSpace(request.Topic)
	if topic == "" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "topic is required",
			Retryable: false,
		}
	}
	if request.Partition < 0 {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "partition must be >= 0",
			Retryable: false,
		}
	}

	maxMessages := clampInt(request.MaxMessages, 1, 200, 20)
	maxBytes := clampInt(request.MaxBytes, 1, 1024*1024, 262144)
	timeoutMS := clampInt(request.TimeoutMS, 100, 10000, 2000)
	offsetStart, offsetErr := normalizeKafkaOffset(request.Offset)
	if offsetErr != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   offsetErr.Error(),
			Retryable: false,
		}
	}

	profile, brokers, profileErr := resolveKafkaProfile(session, request.ProfileID)
	if profileErr != nil {
		return app.ToolRunResult{}, profileErr
	}
	if !topicAllowedByProfile(topic, profile) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodePolicyDenied,
			Message:   "topic outside profile allowlist",
			Retryable: false,
		}
	}

	messages, err := h.client.Consume(ctx, kafkaConsumeRequest{
		Brokers:     brokers,
		Topic:       topic,
		Partition:   request.Partition,
		OffsetStart: offsetStart,
		MaxMessages: maxMessages,
		Timeout:     time.Duration(timeoutMS) * time.Millisecond,
	})
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   fmt.Sprintf("kafka consume failed: %v", err),
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

		keyBytes := msg.Key
		valueBytes := msg.Value
		keyTrimmed := false
		valueTrimmed := false

		remaining := maxBytes - totalBytes
		if len(keyBytes)+len(valueBytes) > remaining {
			if len(keyBytes) >= remaining {
				keyBytes = keyBytes[:remaining]
				valueBytes = []byte{}
				keyTrimmed = len(msg.Key) > len(keyBytes)
				valueTrimmed = len(msg.Value) > 0
			} else {
				valueRemaining := remaining - len(keyBytes)
				if len(valueBytes) > valueRemaining {
					valueBytes = valueBytes[:valueRemaining]
					valueTrimmed = true
				}
			}
			truncated = true
		}

		totalBytes += len(keyBytes) + len(valueBytes)
		outMessages = append(outMessages, map[string]any{
			"partition":      msg.Partition,
			"offset":         msg.Offset,
			"timestamp_unix": msg.Time.Unix(),
			"key_base64":     base64.StdEncoding.EncodeToString(keyBytes),
			"value_base64":   base64.StdEncoding.EncodeToString(valueBytes),
			"size_bytes":     len(keyBytes) + len(valueBytes),
			"key_trimmed":    keyTrimmed,
			"value_trimmed":  valueTrimmed,
		})
	}

	return app.ToolRunResult{
		Logs: []domain.LogLine{{
			At:      time.Now().UTC(),
			Channel: "stdout",
			Message: "kafka consume completed",
		}},
		Output: map[string]any{
			"profile_id":    profile.ID,
			"topic":         topic,
			"messages":      outMessages,
			"message_count": len(outMessages),
			"total_bytes":   totalBytes,
			"truncated":     truncated,
		},
	}, nil
}

func (h *KafkaTopicMetadataHandler) Name() string {
	return "kafka.topic_metadata"
}

func (h *KafkaTopicMetadataHandler) Invoke(ctx context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		ProfileID string `json:"profile_id"`
		Topic     string `json:"topic"`
	}{}
	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "invalid kafka.topic_metadata args",
				Retryable: false,
			}
		}
	}

	topic := strings.TrimSpace(request.Topic)
	if topic == "" {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeInvalidArgument,
			Message:   "topic is required",
			Retryable: false,
		}
	}

	profile, brokers, profileErr := resolveKafkaProfile(session, request.ProfileID)
	if profileErr != nil {
		return app.ToolRunResult{}, profileErr
	}
	if !topicAllowedByProfile(topic, profile) {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodePolicyDenied,
			Message:   "topic outside profile allowlist",
			Retryable: false,
		}
	}

	partitions, err := h.client.TopicMetadata(ctx, kafkaTopicMetadataRequest{
		Brokers: brokers,
		Topic:   topic,
	})
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{
			Code:      app.ErrorCodeExecutionFailed,
			Message:   fmt.Sprintf("kafka topic metadata failed: %v", err),
			Retryable: true,
		}
	}

	outputPartitions := make([]map[string]any, 0, len(partitions))
	for _, partition := range partitions {
		outputPartitions = append(outputPartitions, map[string]any{
			"partition":     partition.PartitionID,
			"leader_host":   partition.LeaderHost,
			"leader_port":   partition.LeaderPort,
			"replica_ids":   partition.ReplicaIDs,
			"isr_ids":       partition.ISRIDs,
			"replica_count": len(partition.ReplicaIDs),
			"isr_count":     len(partition.ISRIDs),
		})
	}

	return app.ToolRunResult{
		Logs: []domain.LogLine{{
			At:      time.Now().UTC(),
			Channel: "stdout",
			Message: "kafka topic metadata completed",
		}},
		Output: map[string]any{
			"profile_id":      profile.ID,
			"topic":           topic,
			"partition_count": len(outputPartitions),
			"partitions":      outputPartitions,
		},
	}, nil
}

func ensureKafkaClient(client kafkaClient) kafkaClient {
	if client != nil {
		return client
	}
	return &liveKafkaClient{}
}

func (c *liveKafkaClient) Consume(ctx context.Context, req kafkaConsumeRequest) ([]kafkaConsumedMessage, error) {
	reader := kafkago.NewReader(kafkago.ReaderConfig{
		Brokers:   req.Brokers,
		Topic:     req.Topic,
		Partition: req.Partition,
		MinBytes:  1,
		MaxBytes:  1 << 20,
	})
	defer reader.Close()

	if err := reader.SetOffset(req.OffsetStart); err != nil {
		return nil, err
	}

	consumeCtx, cancel := context.WithTimeout(ctx, req.Timeout)
	defer cancel()

	out := make([]kafkaConsumedMessage, 0, req.MaxMessages)
	for len(out) < req.MaxMessages {
		msg, err := reader.ReadMessage(consumeCtx)
		if err != nil {
			if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
				break
			}
			return nil, err
		}
		out = append(out, kafkaConsumedMessage{
			Key:       msg.Key,
			Value:     msg.Value,
			Partition: msg.Partition,
			Offset:    msg.Offset,
			Time:      msg.Time,
		})
	}

	return out, nil
}

func (c *liveKafkaClient) TopicMetadata(ctx context.Context, req kafkaTopicMetadataRequest) ([]kafkaTopicPartitionMetadata, error) {
	conn, err := kafkago.DialContext(ctx, "tcp", req.Brokers[0])
	if err != nil {
		return nil, err
	}
	defer conn.Close()

	partitions, err := conn.ReadPartitions(req.Topic)
	if err != nil {
		return nil, err
	}

	out := make([]kafkaTopicPartitionMetadata, 0, len(partitions))
	for _, partition := range partitions {
		if partition.Topic != req.Topic {
			continue
		}
		replicaIDs := make([]int, 0, len(partition.Replicas))
		for _, broker := range partition.Replicas {
			replicaIDs = append(replicaIDs, broker.ID)
		}
		isrIDs := make([]int, 0, len(partition.Isr))
		for _, broker := range partition.Isr {
			isrIDs = append(isrIDs, broker.ID)
		}
		out = append(out, kafkaTopicPartitionMetadata{
			PartitionID: partition.ID,
			LeaderHost:  partition.Leader.Host,
			LeaderPort:  partition.Leader.Port,
			ReplicaIDs:  replicaIDs,
			ISRIDs:      isrIDs,
		})
	}

	return out, nil
}

func resolveKafkaProfile(session domain.Session, requestedProfileID string) (connectionProfile, []string, *domain.Error) {
	profileID := strings.TrimSpace(requestedProfileID)
	if profileID == "" {
		return connectionProfile{}, nil, &domain.Error{
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
		if strings.TrimSpace(strings.ToLower(profile.Kind)) != "kafka" {
			return connectionProfile{}, nil, &domain.Error{
				Code:      app.ErrorCodeInvalidArgument,
				Message:   "profile is not a kafka profile",
				Retryable: false,
			}
		}
		endpoint := resolveProfileEndpoint(session.Metadata, profileID)
		if endpoint == "" && profileID == "dev.kafka" {
			endpoint = "kafka.swe-ai-fleet.svc.cluster.local:9092"
		}
		brokers := splitKafkaBrokers(endpoint)
		if len(brokers) == 0 {
			return connectionProfile{}, nil, &domain.Error{
				Code:      app.ErrorCodeExecutionFailed,
				Message:   "kafka profile endpoint not configured",
				Retryable: false,
			}
		}
		return profile, brokers, nil
	}

	return connectionProfile{}, nil, &domain.Error{
		Code:      app.ErrorCodeNotFound,
		Message:   "connection profile not found",
		Retryable: false,
	}
}

func splitKafkaBrokers(raw string) []string {
	brokers := make([]string, 0, 2)
	for _, item := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(item)
		if candidate == "" {
			continue
		}
		candidate = strings.TrimPrefix(candidate, "kafka://")
		candidate = strings.TrimPrefix(candidate, "tcp://")
		brokers = append(brokers, candidate)
	}
	return brokers
}

func topicAllowedByProfile(topic string, profile connectionProfile) bool {
	raw, found := profile.Scopes["topics"]
	if !found {
		return false
	}

	patterns := make([]string, 0, 2)
	switch typed := raw.(type) {
	case []string:
		patterns = append(patterns, typed...)
	case []any:
		for _, entry := range typed {
			if asString, ok := entry.(string); ok {
				patterns = append(patterns, asString)
			}
		}
	default:
		return false
	}

	for _, pattern := range patterns {
		if topicPatternMatch(pattern, topic) {
			return true
		}
	}
	return false
}

func normalizeKafkaOffset(raw string) (int64, error) {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "", "latest":
		return kafkago.LastOffset, nil
	case "earliest":
		return kafkago.FirstOffset, nil
	default:
		return 0, fmt.Errorf("offset must be earliest or latest")
	}
}

func topicPatternMatch(pattern string, topic string) bool {
	pattern = strings.TrimSpace(pattern)
	topic = strings.TrimSpace(topic)
	if pattern == "" || topic == "" {
		return false
	}
	if pattern == "*" || pattern == topic {
		return true
	}
	if strings.HasSuffix(pattern, ".>") {
		return strings.HasPrefix(topic, strings.TrimSuffix(pattern, ">"))
	}
	if strings.Contains(pattern, "*") {
		parts := strings.Split(pattern, "*")
		if len(parts) == 2 {
			return strings.HasPrefix(topic, parts[0]) && strings.HasSuffix(topic, parts[1])
		}
	}
	if strings.HasSuffix(pattern, ".") || strings.HasSuffix(pattern, ":") || strings.HasSuffix(pattern, "/") {
		return strings.HasPrefix(topic, pattern)
	}
	return false
}
