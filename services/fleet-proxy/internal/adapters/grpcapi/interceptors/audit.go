package interceptors

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// AuditUnaryInterceptor returns a gRPC unary interceptor that records an
// audit event for every RPC call. It captures the caller's identity,
// the method name, duration, and whether the call succeeded.
//
// If publisher is non-nil, a rpc.inbound FleetEvent is also published to
// the internal event bus for real-time observability.
func AuditUnaryInterceptor(logger ports.AuditLogger, publisher ports.EventPublisher) grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req any,
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (any, error) {
		start := time.Now()

		resp, err := handler(ctx, req)

		clientID := ClientIDFromContext(ctx)
		evt := ports.AuditEvent{
			ClientID:  clientID,
			Method:    info.FullMethod,
			Timestamp: start,
			Success:   err == nil,
		}
		if err != nil {
			evt.Error = err.Error()
		}

		logger.Record(ctx, evt)

		if publisher != nil {
			publishRPCInbound(publisher, info.FullMethod, clientID, req, resp, err, time.Since(start))
		}

		return resp, err
	}
}

// rpcPayload is the JSON structure for rpc.inbound event payloads.
type rpcPayload struct {
	Method     string          `json:"method"`
	ClientID   string          `json:"client_id,omitempty"`
	Success    bool            `json:"success"`
	Error      string          `json:"error,omitempty"`
	DurationMs int64           `json:"duration_ms"`
	Request    json.RawMessage `json:"request,omitempty"`
	Response   json.RawMessage `json:"response,omitempty"`
}

// protoJSONOpts configures compact protojson output for event payloads.
var protoJSONOpts = protojson.MarshalOptions{
	EmitDefaultValues: false,
	UseProtoNames:     true,
}

// marshalProto serialises a proto message to JSON for inclusion in event payloads.
// Returns nil on failure so the event is still published without the body.
func marshalProto(v any) json.RawMessage {
	if v == nil {
		return nil
	}
	pm, ok := v.(proto.Message)
	if !ok {
		return nil
	}
	data, err := protoJSONOpts.Marshal(pm)
	if err != nil {
		return nil
	}
	return data
}

func publishRPCInbound(pub ports.EventPublisher, method, clientID string, req, resp any, rpcErr error, dur time.Duration) {
	p := rpcPayload{
		Method:     method,
		ClientID:   clientID,
		Success:    rpcErr == nil,
		DurationMs: dur.Milliseconds(),
		Request:    marshalProto(req),
		Response:   marshalProto(resp),
	}
	if rpcErr != nil {
		p.Error = rpcErr.Error()
	}
	payload, _ := json.Marshal(p)

	corrID := method
	if clientID != "" {
		corrID = clientID
	}

	pub.Publish(event.FleetEvent{
		Type:           event.EventRPCInbound,
		IdempotencyKey: randomID(),
		CorrelationID:  corrID,
		Timestamp:      time.Now(),
		Producer:       "fleet-proxy",
		Payload:        payload,
	})
}

// AuditStreamInterceptor returns a gRPC stream interceptor that publishes
// rpc.inbound events for server-streaming RPCs (e.g. WatchEvents).
// It emits an event when the stream opens and another when it closes.
func AuditStreamInterceptor(logger ports.AuditLogger, publisher ports.EventPublisher) grpc.StreamServerInterceptor {
	return func(
		srv any,
		ss grpc.ServerStream,
		info *grpc.StreamServerInfo,
		handler grpc.StreamHandler,
	) error {
		start := time.Now()
		clientID := ClientIDFromContext(ss.Context())

		// Publish stream-open event.
		if publisher != nil {
			publishStreamEvent(publisher, info.FullMethod, clientID, "stream.opened", nil, 0)
		}

		err := handler(srv, ss)

		dur := time.Since(start)

		// Audit log.
		evt := ports.AuditEvent{
			ClientID:  clientID,
			Method:    info.FullMethod,
			Timestamp: start,
			Success:   err == nil,
		}
		if err != nil {
			evt.Error = err.Error()
		}
		logger.Record(ss.Context(), evt)

		// Publish stream-close event.
		if publisher != nil {
			publishStreamEvent(publisher, info.FullMethod, clientID, "stream.closed", err, dur)
		}

		return err
	}
}

func publishStreamEvent(pub ports.EventPublisher, method, clientID, phase string, rpcErr error, dur time.Duration) {
	type streamPayload struct {
		Method     string `json:"method"`
		ClientID   string `json:"client_id,omitempty"`
		Phase      string `json:"phase"`
		Success    bool   `json:"success"`
		Error      string `json:"error,omitempty"`
		DurationMs int64  `json:"duration_ms,omitempty"`
	}
	p := streamPayload{
		Method:   method,
		ClientID: clientID,
		Phase:    phase,
		Success:  rpcErr == nil,
	}
	if rpcErr != nil {
		p.Error = rpcErr.Error()
	}
	if dur > 0 {
		p.DurationMs = dur.Milliseconds()
	}
	data, _ := json.Marshal(p)

	corrID := method
	if clientID != "" {
		corrID = clientID
	}

	pub.Publish(event.FleetEvent{
		Type:           event.EventRPCInbound,
		IdempotencyKey: randomID(),
		CorrelationID:  corrID,
		Timestamp:      time.Now(),
		Producer:       "fleet-proxy",
		Payload:        data,
	})
}

// randomID generates a random hex string suitable for idempotency keys.
func randomID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	return fmt.Sprintf("%x", b)
}
