package grpc

import (
	"context"
	"fmt"
	"io"
	"log/slog"

	"google.golang.org/grpc"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// watchEventsStreamDesc describes the server-streaming WatchEvents RPC.
var watchEventsStreamDesc = &grpc.StreamDesc{
	StreamName:    "WatchEvents",
	ServerStreams:  true,
	ClientStreams:  false,
}

// WatchEvents opens a server-streaming subscription for fleet events via
// fleet-proxy's FleetQueryService.WatchEvents RPC. The returned channel
// delivers domain.FleetEvent values until the context is cancelled, the
// server terminates the stream, or a receive error occurs.
func (c *FleetClient) WatchEvents(ctx context.Context, eventTypes []string, projectID string) (<-chan domain.FleetEvent, error) {
	ch := make(chan domain.FleetEvent, 64)

	stream, err := c.conn.Conn().NewStream(
		ctx,
		watchEventsStreamDesc,
		"/fleet.proxy.v1.FleetQueryService/WatchEvents",
	)
	if err != nil {
		close(ch)
		return nil, fmt.Errorf("watch events: open stream: %w", err)
	}

	req := &WatchEventsRequest{
		EventTypes: eventTypes,
		ProjectID:  projectID,
	}
	if err := stream.SendMsg(req); err != nil {
		close(ch)
		return nil, fmt.Errorf("watch events: send request: %w", err)
	}
	if err := stream.CloseSend(); err != nil {
		close(ch)
		return nil, fmt.Errorf("watch events: close send: %w", err)
	}

	go func() {
		defer close(ch)
		for {
			msg := &FleetEventMsg{}
			if err := stream.RecvMsg(msg); err != nil {
				if err != io.EOF && ctx.Err() == nil {
					slog.Warn("event stream ended", "error", err)
				}
				return
			}
			evt := domain.FleetEvent{
				Type:           msg.EventType,
				IdempotencyKey: msg.IdempotencyKey,
				CorrelationID:  msg.CorrelationID,
				Timestamp:      msg.Timestamp,
				Producer:       msg.Producer,
				Payload:        msg.Payload,
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
