// Package nats implements ports.EventSubscriber using NATS JetStream.
// It provides both eager and lazy connection strategies and maps domain
// EventFilter criteria to JetStream subject filters for server-side routing.
package nats

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// streamName is the NATS JetStream stream that fleet events are published to.
const streamName = "FLEET_EVENTS"

// subjectPrefix is the NATS subject prefix for all fleet events.
const subjectPrefix = "fleet.events"

// wireEvent is the JSON envelope published to NATS. It mirrors FleetEvent
// but uses primitive types suitable for JSON serialization.
type wireEvent struct {
	Type           string          `json:"type"`
	IdempotencyKey string          `json:"idempotency_key"`
	CorrelationID  string          `json:"correlation_id"`
	Timestamp      time.Time       `json:"timestamp"`
	Producer       string          `json:"producer"`
	ProjectID      string          `json:"project_id,omitempty"`
	Payload        json.RawMessage `json:"payload,omitempty"`
}

// Subscriber implements ports.EventSubscriber using NATS JetStream.
type Subscriber struct {
	url    string
	nc     *nats.Conn
	js     jetstream.JetStream
	mu     sync.Mutex
	closed bool
}

// NewSubscriber creates a NATS Subscriber and connects eagerly to the given URL.
// It returns an error if the initial connection cannot be established.
func NewSubscriber(url string) (*Subscriber, error) {
	nc, err := nats.Connect(url,
		nats.RetryOnFailedConnect(true),
		nats.MaxReconnects(-1),
		nats.ReconnectWait(2*time.Second),
	)
	if err != nil {
		return nil, fmt.Errorf("nats subscriber: connect to %s: %w", url, err)
	}

	js, err := jetstream.New(nc)
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("nats subscriber: create jetstream context: %w", err)
	}

	return &Subscriber{url: url, nc: nc, js: js}, nil
}

// NewSubscriberFromConn creates a subscriber from an existing NATS connection.
// This is primarily useful for integration tests that manage their own server.
func NewSubscriberFromConn(nc *nats.Conn) (*Subscriber, error) {
	js, err := jetstream.New(nc)
	if err != nil {
		return nil, fmt.Errorf("nats subscriber: create jetstream from conn: %w", err)
	}
	return &Subscriber{nc: nc, js: js}, nil
}

// NewLazySubscriber creates a subscriber that defers the NATS connection until
// the first Subscribe call. This is useful when the NATS server may not be
// available at startup (e.g., during development or delayed dependency readiness).
func NewLazySubscriber(url string) *Subscriber {
	return &Subscriber{url: url}
}

// ensureConnected establishes the NATS connection and JetStream context if they
// are not already initialised. It is safe for concurrent callers.
func (s *Subscriber) ensureConnected() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.closed {
		return fmt.Errorf("nats subscriber: already closed")
	}
	if s.js != nil {
		return nil
	}

	nc, err := nats.Connect(s.url,
		nats.RetryOnFailedConnect(true),
		nats.MaxReconnects(-1),
		nats.ReconnectWait(2*time.Second),
	)
	if err != nil {
		return fmt.Errorf("nats subscriber: connect to %s: %w", s.url, err)
	}

	js, err := jetstream.New(nc)
	if err != nil {
		nc.Close()
		return fmt.Errorf("nats subscriber: create jetstream context: %w", err)
	}

	s.nc = nc
	s.js = js
	return nil
}

// Subscribe opens a filtered event stream. It creates an ephemeral JetStream
// consumer whose subject filters correspond to the EventFilter criteria.
// The returned channel delivers events until ctx is cancelled or Close is called.
func (s *Subscriber) Subscribe(ctx context.Context, filter event.EventFilter) (<-chan event.FleetEvent, error) {
	if err := s.ensureConnected(); err != nil {
		return nil, err
	}

	subjects := buildSubjectFilters(filter)

	// Create an ephemeral ordered consumer. Ordered consumers are
	// lightweight, server-managed, and automatically cleaned up.
	consumerCfg := jetstream.OrderedConsumerConfig{
		FilterSubjects: subjects,
	}

	stream, err := s.js.Stream(ctx, streamName)
	if err != nil {
		return nil, fmt.Errorf("nats subscriber: get stream %s: %w", streamName, err)
	}

	consumer, err := stream.OrderedConsumer(ctx, consumerCfg)
	if err != nil {
		return nil, fmt.Errorf("nats subscriber: create consumer: %w", err)
	}

	ch := make(chan event.FleetEvent, 64)

	go s.consumeLoop(ctx, consumer, filter, ch)

	return ch, nil
}

// consumeLoop pulls messages from the JetStream consumer, decodes them into
// FleetEvent values, applies the domain-level filter, and sends matching events
// on ch. It closes ch when done.
func (s *Subscriber) consumeLoop(ctx context.Context, consumer jetstream.Consumer, filter event.EventFilter, ch chan<- event.FleetEvent) {
	defer close(ch)

	for {
		// Fetch one message at a time with a short timeout so we can
		// check the context regularly without blocking indefinitely.
		msgs, err := consumer.Fetch(1, jetstream.FetchMaxWait(2*time.Second))
		if err != nil {
			if ctx.Err() != nil {
				return
			}
			slog.Warn("nats subscriber: fetch error", "error", err)
			continue
		}

		for msg := range msgs.Messages() {
			evt, decErr := DecodeWireEvent(msg.Data())
			if decErr != nil {
				slog.Warn("nats subscriber: decode error",
					"subject", msg.Subject(),
					"error", decErr,
				)
				_ = msg.Ack()
				continue
			}

			if !filter.Matches(evt) {
				_ = msg.Ack()
				continue
			}

			select {
			case ch <- evt:
				_ = msg.Ack()
			case <-ctx.Done():
				return
			}
		}

		if msgs.Error() != nil && ctx.Err() == nil {
			slog.Warn("nats subscriber: messages iteration error", "error", msgs.Error())
		}

		if ctx.Err() != nil {
			return
		}
	}
}

// Close drains the NATS connection, allowing in-flight messages to be processed,
// and then closes the underlying transport.
func (s *Subscriber) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.closed {
		return nil
	}
	s.closed = true

	if s.nc == nil {
		return nil
	}

	return s.nc.Drain()
}

// buildSubjectFilters converts an EventFilter into NATS subject patterns.
// The subject hierarchy is:
//
//	fleet.events.<type-segment>                         (all projects)
//	fleet.events.<type-segment>.project.<project-id>    (specific project)
//
// where <type-segment> replaces dots in the EventType with dashes so that
// "story.created" becomes "story-created" (a single NATS token).
func buildSubjectFilters(f event.EventFilter) []string {
	hasProject := f.ProjectID != nil

	// No type filter: wildcard on the type segment.
	if len(f.Types) == 0 {
		if hasProject {
			return []string{fmt.Sprintf("%s.*.project.%s", subjectPrefix, *f.ProjectID)}
		}
		return []string{subjectPrefix + ".>"}
	}

	subjects := make([]string, 0, len(f.Types))
	for _, t := range f.Types {
		seg := typeToSubjectSegment(t)
		if hasProject {
			subjects = append(subjects, fmt.Sprintf("%s.%s.project.%s", subjectPrefix, seg, *f.ProjectID))
		} else {
			subjects = append(subjects, fmt.Sprintf("%s.%s", subjectPrefix, seg))
		}
	}
	return subjects
}

// typeToSubjectSegment converts a dotted EventType like "story.created" into a
// single NATS subject token "story-created".
func typeToSubjectSegment(t event.EventType) string {
	return strings.ReplaceAll(string(t), ".", "-")
}

// DecodeWireEvent converts raw JSON bytes (as published to NATS) into a domain
// FleetEvent. It is exported so that tests and other adapters can reuse the
// deserialization logic without depending on a NATS connection.
func DecodeWireEvent(data []byte) (event.FleetEvent, error) {
	var w wireEvent
	if err := json.Unmarshal(data, &w); err != nil {
		return event.FleetEvent{}, fmt.Errorf("decode wire event: %w", err)
	}

	eventType := event.EventType(w.Type)
	if !eventType.IsValid() {
		return event.FleetEvent{}, fmt.Errorf("decode wire event: unknown type %q", w.Type)
	}

	return event.FleetEvent{
		Type:           eventType,
		IdempotencyKey: w.IdempotencyKey,
		CorrelationID:  w.CorrelationID,
		Timestamp:      w.Timestamp,
		Producer:       w.Producer,
		Payload:        []byte(w.Payload),
	}, nil
}
