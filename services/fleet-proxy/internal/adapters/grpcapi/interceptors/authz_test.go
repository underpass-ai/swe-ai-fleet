package interceptors

import (
	"context"
	"errors"
	"testing"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// ---------------------------------------------------------------------------
// Fakes
// ---------------------------------------------------------------------------

type fakeIdentityResolver struct {
	roles  []identity.Role
	scopes []auth.Scope
	err    error
}

func (f *fakeIdentityResolver) Resolve(_ context.Context, _ identity.ClientID) ([]identity.Role, []auth.Scope, error) {
	return f.roles, f.scopes, f.err
}

type fakeServerStream struct {
	grpc.ServerStream
	ctx context.Context
}

func (f *fakeServerStream) Context() context.Context { return f.ctx }
func (f *fakeServerStream) SendMsg(_ any) error      { return nil }
func (f *fakeServerStream) RecvMsg(_ any) error       { return nil }
func (f *fakeServerStream) SetHeader(_ metadata.MD) error { return nil }
func (f *fakeServerStream) SendHeader(_ metadata.MD) error { return nil }
func (f *fakeServerStream) SetTrailer(_ metadata.MD)       {}

// ---------------------------------------------------------------------------
// Unary interceptor tests
// ---------------------------------------------------------------------------

func TestAuthzUnaryInterceptor_EnrollmentBypass(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{}
	interceptor := AuthzUnaryInterceptor(policy, resolver)

	called := false
	handler := func(_ context.Context, _ any) (any, error) {
		called = true
		return "ok", nil
	}

	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.EnrollmentService/Enroll",
	}

	_, err := interceptor(context.Background(), nil, info, handler)
	if err != nil {
		t.Fatalf("enrollment should bypass authz, got: %v", err)
	}
	if !called {
		t.Error("handler should have been called for enrollment method")
	}
}

func TestAuthzUnaryInterceptor_NoClientID(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{}
	interceptor := AuthzUnaryInterceptor(policy, resolver)

	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject",
	}

	_, err := interceptor(context.Background(), nil, info, nil)
	if err == nil {
		t.Fatal("expected error for missing client ID")
	}
	if s, ok := status.FromError(err); !ok || s.Code() != codes.Unauthenticated {
		t.Errorf("expected Unauthenticated, got: %v", err)
	}
}

func TestAuthzUnaryInterceptor_InvalidClientID(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{}
	interceptor := AuthzUnaryInterceptor(policy, resolver)

	ctx := context.WithValue(context.Background(), ClientIDKey, "not-a-spiffe-uri")
	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject",
	}

	_, err := interceptor(ctx, nil, info, nil)
	if err == nil {
		t.Fatal("expected error for invalid client ID")
	}
	if s, ok := status.FromError(err); !ok || s.Code() != codes.Unauthenticated {
		t.Errorf("expected Unauthenticated, got: %v", err)
	}
}

func TestAuthzUnaryInterceptor_ResolveError(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{err: errors.New("resolver down")}
	interceptor := AuthzUnaryInterceptor(policy, resolver)

	ctx := context.WithValue(context.Background(), ClientIDKey, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject",
	}

	_, err := interceptor(ctx, nil, info, nil)
	if err == nil {
		t.Fatal("expected error for resolve failure")
	}
	if s, ok := status.FromError(err); !ok || s.Code() != codes.PermissionDenied {
		t.Errorf("expected PermissionDenied, got: %v", err)
	}
}

func TestAuthzUnaryInterceptor_Authorized(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{
		roles: []identity.Role{identity.RoleOperator},
	}
	interceptor := AuthzUnaryInterceptor(policy, resolver)

	called := false
	handler := func(_ context.Context, _ any) (any, error) {
		called = true
		return "ok", nil
	}

	ctx := context.WithValue(context.Background(), ClientIDKey, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject",
	}

	_, err := interceptor(ctx, nil, info, handler)
	if err != nil {
		t.Fatalf("authorized request should succeed: %v", err)
	}
	if !called {
		t.Error("handler should have been called")
	}
}

// ---------------------------------------------------------------------------
// Stream interceptor tests
// ---------------------------------------------------------------------------

func TestAuthzStreamInterceptor_NoClientID(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{}
	interceptor := AuthzStreamInterceptor(policy, resolver)

	ss := &fakeServerStream{ctx: context.Background()}
	info := &grpc.StreamServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetQueryService/WatchEvents",
	}

	err := interceptor(nil, ss, info, nil)
	if err == nil {
		t.Fatal("expected error for missing client ID")
	}
	if s, ok := status.FromError(err); !ok || s.Code() != codes.Unauthenticated {
		t.Errorf("expected Unauthenticated, got: %v", err)
	}
}

func TestAuthzStreamInterceptor_Authorized(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{
		roles: []identity.Role{identity.RoleViewer},
	}
	interceptor := AuthzStreamInterceptor(policy, resolver)

	ctx := context.WithValue(context.Background(), ClientIDKey, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	ss := &fakeServerStream{ctx: ctx}
	info := &grpc.StreamServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetQueryService/WatchEvents",
	}

	called := false
	handler := func(_ any, _ grpc.ServerStream) error {
		called = true
		return nil
	}

	err := interceptor(nil, ss, info, handler)
	if err != nil {
		t.Fatalf("authorized stream should succeed: %v", err)
	}
	if !called {
		t.Error("handler should have been called")
	}
}

func TestAuthzStreamInterceptor_Denied(t *testing.T) {
	t.Parallel()

	policy := auth.NewAuthorizationPolicy()
	resolver := &fakeIdentityResolver{
		roles: []identity.Role{}, // no roles
	}
	interceptor := AuthzStreamInterceptor(policy, resolver)

	ctx := context.WithValue(context.Background(), ClientIDKey, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	ss := &fakeServerStream{ctx: ctx}
	info := &grpc.StreamServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetQueryService/WatchEvents",
	}

	err := interceptor(nil, ss, info, nil)
	if err == nil {
		t.Fatal("expected error for denied access")
	}
	if s, ok := status.FromError(err); !ok || s.Code() != codes.PermissionDenied {
		t.Errorf("expected PermissionDenied, got: %v", err)
	}
}
