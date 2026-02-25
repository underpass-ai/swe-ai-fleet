package interceptors

import (
	"context"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// AuthzUnaryInterceptor returns a gRPC unary interceptor that checks whether
// the authenticated caller has sufficient roles to invoke the requested method.
// It uses the AuthorizationPolicy domain service for the access decision and
// the IdentityResolver port to map the caller's ClientID to roles.
func AuthzUnaryInterceptor(policy auth.AuthorizationPolicy, resolver ports.IdentityResolver) grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req any,
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (any, error) {
		// Enrollment methods use API-key auth — no mTLS identity to check.
		if enrollmentMethods[info.FullMethod] {
			return handler(ctx, req)
		}

		clientIDStr := ClientIDFromContext(ctx)
		if clientIDStr == "" {
			return nil, status.Errorf(codes.Unauthenticated, "authz: no client identity in context")
		}

		clientID, err := identity.NewClientID(clientIDStr)
		if err != nil {
			return nil, status.Errorf(codes.Unauthenticated, "authz: invalid client ID: %v", err)
		}

		roles, _, err := resolver.Resolve(ctx, clientID)
		if err != nil {
			return nil, status.Errorf(codes.PermissionDenied, "authz: resolve identity: %v", err)
		}

		if !policy.IsAllowed(roles, info.FullMethod) {
			return nil, status.Errorf(codes.PermissionDenied,
				"authz: client %q not authorized for method %s", clientIDStr, info.FullMethod)
		}

		return handler(ctx, req)
	}
}
