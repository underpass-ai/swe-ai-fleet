package grpc

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// WatchEvents opens a server-streaming subscription for fleet events.
// The returned channel delivers domain.FleetEvent values until the context
// is cancelled or the server terminates the stream.
//
// When the proto-generated stubs are available this will use a
// server-streaming RPC (WatchEvents on FleetQueryService). Until then
// the goroutine keeps the channel open and closes it cleanly on context
// cancellation so callers can safely range over it.
func (c *FleetClient) WatchEvents(ctx context.Context, eventTypes []string, projectID string) (<-chan domain.FleetEvent, error) {
	ch := make(chan domain.FleetEvent, 64)

	// When proto stubs are available, this will use a server-streaming RPC:
	//
	//   stream, err := c.queryClient.WatchEvents(ctx, &proxyv1.WatchEventsRequest{
	//       EventTypes: eventTypes,
	//       ProjectId:  projectID,
	//   })
	//   if err != nil {
	//       close(ch)
	//       return nil, fmt.Errorf("watch events: %w", err)
	//   }
	//
	//   go func() {
	//       defer close(ch)
	//       for {
	//           resp, err := stream.Recv()
	//           if err != nil {
	//               return
	//           }
	//           ch <- domain.FleetEvent{
	//               Type:           resp.GetType(),
	//               IdempotencyKey: resp.GetIdempotencyKey(),
	//               CorrelationID:  resp.GetCorrelationId(),
	//               Timestamp:      resp.GetTimestamp(),
	//               Producer:       resp.GetProducer(),
	//               Payload:        resp.GetPayload(),
	//           }
	//       }
	//   }()

	// Placeholder: keep the channel open until the caller cancels.
	go func() {
		defer close(ch)
		<-ctx.Done()
	}()

	return ch, nil
}
