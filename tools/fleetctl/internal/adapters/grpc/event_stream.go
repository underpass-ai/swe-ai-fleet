package grpc

import (
	"context"
	"fmt"
	"io"
	"log/slog"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// WatchEvents opens a server-streaming subscription for fleet events via
// fleet-proxy's FleetQueryService.WatchEvents RPC. The returned channel
// delivers domain.FleetEvent values until the context is cancelled, the
// server terminates the stream, or a receive error occurs.
func (c *FleetClient) WatchEvents(ctx context.Context, eventTypes []string, projectID string) (<-chan domain.FleetEvent, error) {
	ch := make(chan domain.FleetEvent, 64)

	stream, err := c.qryClient.WatchEvents(ctx, &proxyv1.WatchEventsRequest{
		EventTypes: eventTypes,
		ProjectId:  projectID,
	})
	if err != nil {
		close(ch)
		return nil, fmt.Errorf("watch events: open stream: %w", err)
	}

	go func() {
		defer close(ch)
		for {
			msg, err := stream.Recv()
			if err != nil {
				if err != io.EOF && ctx.Err() == nil {
					slog.Warn("event stream ended", "error", err)
				}
				return
			}
			evt := domain.FleetEvent{
				Type:           msg.GetEventType(),
				IdempotencyKey: msg.GetIdempotencyKey(),
				CorrelationID:  msg.GetCorrelationId(),
				Timestamp:      msg.GetTimestamp(),
				Producer:       msg.GetProducer(),
				Payload:        msg.GetPayload(),
			}
			select {
			case ch <- evt:
			case <-ctx.Done():
				return
			}
		}
	}()

	return ch, nil
}
