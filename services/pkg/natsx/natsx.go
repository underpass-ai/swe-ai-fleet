// Package natsx provides a lightweight wrapper around NATS JetStream
// for common pub/sub patterns used across services.
package natsx

import (
	"encoding/json"
	"fmt"
	"time"

	nats "github.com/nats-io/nats.go"
)

// Conn wraps a NATS connection with JetStream context
type Conn struct {
	nc *nats.Conn
	JS nats.JetStreamContext
}

// ConnectOptions configures the NATS connection
type ConnectOptions struct {
	URL           string
	MaxReconnect  int
	ReconnectWait time.Duration
}

// DefaultOptions returns sensible defaults
func DefaultOptions() ConnectOptions {
	return ConnectOptions{
		URL:           "nats://nats:4222",
		MaxReconnect:  10,
		ReconnectWait: 2 * time.Second,
	}
}

// Connect establishes a connection to NATS with JetStream enabled
func Connect(opts ConnectOptions) (*Conn, error) {
	if opts.URL == "" {
		opts.URL = "nats://nats:4222"
	}

	nc, err := nats.Connect(
		opts.URL,
		nats.MaxReconnects(opts.MaxReconnect),
		nats.ReconnectWait(opts.ReconnectWait),
	)
	if err != nil {
		return nil, fmt.Errorf("nats.Connect: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("nc.JetStream: %w", err)
	}

	return &Conn{nc: nc, JS: js}, nil
}

// Close drains and closes the connection
func (c *Conn) Close() error {
	if err := c.nc.Drain(); err != nil {
		return err
	}
	c.nc.Close()
	return nil
}

// StreamConfig holds stream configuration
type StreamConfig struct {
	Name      string
	Subjects  []string
	Retention nats.RetentionPolicy
	MaxAge    time.Duration
}

// EnsureStream creates or updates a stream (idempotent)
func (c *Conn) EnsureStream(cfg StreamConfig) error {
	if cfg.MaxAge == 0 {
		cfg.MaxAge = 7 * 24 * time.Hour // Default 7 days
	}

	_, err := c.JS.AddStream(&nats.StreamConfig{
		Name:      cfg.Name,
		Subjects:  cfg.Subjects,
		Retention: cfg.Retention,
		MaxAge:    cfg.MaxAge,
	})
	if err != nil {
		return fmt.Errorf("AddStream %s: %w", cfg.Name, err)
	}
	return nil
}

// EnsureWorkStream creates a WorkQueue stream (messages deleted after ack)
func (c *Conn) EnsureWorkStream(name string, subjects []string) error {
	return c.EnsureStream(StreamConfig{
		Name:      name,
		Subjects:  subjects,
		Retention: nats.WorkQueuePolicy,
	})
}

// Publish publishes a message to a subject with JetStream persistence
func (c *Conn) Publish(subject string, data interface{}) error {
	var payload []byte
	var err error

	switch v := data.(type) {
	case []byte:
		payload = v
	case string:
		payload = []byte(v)
	default:
		payload, err = json.Marshal(data)
		if err != nil {
			return fmt.Errorf("json.Marshal: %w", err)
		}
	}

	_, err = c.JS.Publish(subject, payload)
	return err
}

// PullSubscriber wraps a JetStream pull subscription
type PullSubscriber struct {
	sub *nats.Subscription
}

// CreatePullConsumer creates a durable pull consumer
func (c *Conn) CreatePullConsumer(stream, durable string) (*PullSubscriber, error) {
	// Use empty subject to subscribe to all subjects in the stream
	sub, err := c.JS.PullSubscribe(
		"",
		durable,
		nats.BindStream(stream),
		nats.Durable(durable),
	)
	if err != nil {
		return nil, fmt.Errorf("PullSubscribe: %w", err)
	}
	return &PullSubscriber{sub: sub}, nil
}

// Fetch fetches up to batch messages from the consumer
func (ps *PullSubscriber) Fetch(batch int, timeout time.Duration) ([]*nats.Msg, error) {
	if timeout == 0 {
		timeout = 5 * time.Second
	}
	msgs, err := ps.sub.Fetch(batch, nats.MaxWait(timeout))
	if err != nil {
		return nil, err
	}
	return msgs, nil
}

// Unsubscribe closes the subscription
func (ps *PullSubscriber) Unsubscribe() error {
	return ps.sub.Unsubscribe()
}


