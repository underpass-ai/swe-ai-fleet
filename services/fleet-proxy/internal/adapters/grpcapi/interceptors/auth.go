// Package interceptors provides gRPC server interceptors for authentication,
// authorization, audit logging, and rate limiting.
package interceptors

import (
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/peer"
	"google.golang.org/grpc/status"
)

// contextKey is used for storing values in the request context.
type contextKey string

// ClientIDKey is the context key under which the authenticated client's
// SPIFFE URI (from the mTLS certificate SAN) is stored.
const ClientIDKey contextKey = "client_id"

// enrollmentMethods lists RPC methods that use API-key auth instead of mTLS.
// These methods are skipped by the auth interceptor (no client cert required).
var enrollmentMethods = map[string]bool{
	"/fleet.proxy.v1.EnrollmentService/Enroll": true,
}

// AuthUnaryInterceptor returns a gRPC unary interceptor that extracts the
// client identity from the mTLS peer certificate. It reads the first URI SAN
// from the verified client certificate and stores it in the context under
// ClientIDKey. Enrollment methods (API-key-based) are passed through without
// requiring a client certificate.
func AuthUnaryInterceptor() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req any,
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (any, error) {
		// Enrollment uses API-key auth, not mTLS — skip cert extraction.
		if enrollmentMethods[info.FullMethod] {
			return handler(ctx, req)
		}

		clientID, err := extractClientID(ctx)
		if err != nil {
			return nil, status.Errorf(codes.Unauthenticated, "auth: %v", err)
		}

		ctx = context.WithValue(ctx, ClientIDKey, clientID)
		return handler(ctx, req)
	}
}

// AuthStreamInterceptor returns a gRPC stream interceptor that extracts the
// client identity from the mTLS peer certificate. The client ID is stored
// in the wrapped stream's context.
func AuthStreamInterceptor() grpc.StreamServerInterceptor {
	return func(
		srv any,
		ss grpc.ServerStream,
		info *grpc.StreamServerInfo,
		handler grpc.StreamHandler,
	) error {
		clientID, err := extractClientID(ss.Context())
		if err != nil {
			return status.Errorf(codes.Unauthenticated, "auth: %v", err)
		}

		wrapped := &wrappedStream{
			ServerStream: ss,
			ctx:          context.WithValue(ss.Context(), ClientIDKey, clientID),
		}
		return handler(srv, wrapped)
	}
}

// ClientIDFromContext retrieves the authenticated client ID string from the
// context. Returns an empty string if not present.
func ClientIDFromContext(ctx context.Context) string {
	v, _ := ctx.Value(ClientIDKey).(string)
	return v
}

// extractClientID reads the peer's TLS info and extracts the first URI SAN
// from the verified client certificate chain.
func extractClientID(ctx context.Context) (string, error) {
	p, ok := peer.FromContext(ctx)
	if !ok {
		return "", fmt.Errorf("no peer info in context")
	}

	tlsInfo, ok := p.AuthInfo.(credentials.TLSInfo)
	if !ok {
		return "", fmt.Errorf("no TLS info in peer")
	}

	if len(tlsInfo.State.VerifiedChains) == 0 || len(tlsInfo.State.VerifiedChains[0]) == 0 {
		return "", fmt.Errorf("no verified certificate chain")
	}

	leaf := tlsInfo.State.VerifiedChains[0][0]

	if len(leaf.URIs) == 0 {
		return "", fmt.Errorf("client certificate has no URI SAN")
	}

	return leaf.URIs[0].String(), nil
}

// wrappedStream wraps a grpc.ServerStream to override its context.
type wrappedStream struct {
	grpc.ServerStream
	ctx context.Context
}

// Context returns the wrapped context containing the client ID.
func (w *wrappedStream) Context() context.Context {
	return w.ctx
}
