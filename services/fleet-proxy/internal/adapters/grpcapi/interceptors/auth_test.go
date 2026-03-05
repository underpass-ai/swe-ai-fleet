package interceptors

import (
	"context"
	"testing"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func TestClientIDFromContext(t *testing.T) {
	t.Parallel()

	t.Run("present", func(t *testing.T) {
		ctx := context.WithValue(context.Background(), ClientIDKey, "spiffe://test/user/1/device/a")
		got := ClientIDFromContext(ctx)
		if got != "spiffe://test/user/1/device/a" {
			t.Errorf("ClientIDFromContext = %q, want %q", got, "spiffe://test/user/1/device/a")
		}
	})

	t.Run("absent", func(t *testing.T) {
		got := ClientIDFromContext(context.Background())
		if got != "" {
			t.Errorf("ClientIDFromContext = %q, want empty", got)
		}
	})

	t.Run("wrong_type", func(t *testing.T) {
		ctx := context.WithValue(context.Background(), ClientIDKey, 42)
		got := ClientIDFromContext(ctx)
		if got != "" {
			t.Errorf("ClientIDFromContext = %q, want empty for wrong type", got)
		}
	})
}

func TestRateLimitUnaryInterceptor(t *testing.T) {
	t.Parallel()

	interceptor, stop := RateLimitUnaryInterceptor(1)
	defer stop()

	handler := func(_ context.Context, _ any) (any, error) {
		return "ok", nil
	}

	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject",
	}

	// Inject a client ID into context.
	ctx := context.WithValue(context.Background(), ClientIDKey, "spiffe://swe-ai-fleet/user/test/device/dev")

	// First request should succeed.
	resp, err := interceptor(ctx, nil, info, handler)
	if err != nil {
		t.Fatalf("first request should succeed: %v", err)
	}
	if resp != "ok" {
		t.Errorf("response = %v, want %q", resp, "ok")
	}

	// Second request should be rate-limited (1 rps, no time elapsed).
	_, err = interceptor(ctx, nil, info, handler)
	if err == nil {
		t.Fatal("second request should be rate-limited")
	}
	if s, ok := status.FromError(err); !ok || s.Code() != codes.ResourceExhausted {
		t.Errorf("expected ResourceExhausted, got: %v", err)
	}
}

func TestRateLimitUnaryInterceptor_Anonymous(t *testing.T) {
	t.Parallel()

	interceptor, stop := RateLimitUnaryInterceptor(1)
	defer stop()

	handler := func(_ context.Context, _ any) (any, error) {
		return "ok", nil
	}

	info := &grpc.UnaryServerInfo{
		FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject",
	}

	// No client ID — should fall back to "anonymous".
	_, err := interceptor(context.Background(), nil, info, handler)
	if err != nil {
		t.Fatalf("anonymous request should succeed: %v", err)
	}
}
