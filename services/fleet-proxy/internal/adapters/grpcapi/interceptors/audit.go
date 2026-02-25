package interceptors

import (
	"context"
	"time"

	"google.golang.org/grpc"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// AuditUnaryInterceptor returns a gRPC unary interceptor that records an
// audit event for every RPC call. It captures the caller's identity,
// the method name, duration, and whether the call succeeded.
func AuditUnaryInterceptor(logger ports.AuditLogger) grpc.UnaryServerInterceptor {
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

		return resp, err
	}
}
