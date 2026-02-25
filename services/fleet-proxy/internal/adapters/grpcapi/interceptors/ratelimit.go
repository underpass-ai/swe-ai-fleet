package interceptors

import (
	"context"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// tokenBucket implements a simple token bucket rate limiter per identity.
type tokenBucket struct {
	tokens     float64
	maxTokens  float64
	refillRate float64 // tokens per second
	lastRefill time.Time
}

// rateLimiter manages per-identity token buckets.
type rateLimiter struct {
	mu      sync.Mutex
	buckets map[string]*tokenBucket
	rps     int
}

// newRateLimiter creates a rate limiter with the given requests-per-second limit.
func newRateLimiter(rps int) *rateLimiter {
	return &rateLimiter{
		buckets: make(map[string]*tokenBucket),
		rps:     rps,
	}
}

// allow checks whether the identity is allowed to make a request. Returns
// true if a token is available, false if rate-limited.
func (r *rateLimiter) allow(identity string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now()
	bucket, ok := r.buckets[identity]
	if !ok {
		bucket = &tokenBucket{
			tokens:     float64(r.rps),
			maxTokens:  float64(r.rps),
			refillRate: float64(r.rps),
			lastRefill: now,
		}
		r.buckets[identity] = bucket
	}

	// Refill tokens based on elapsed time.
	elapsed := now.Sub(bucket.lastRefill).Seconds()
	bucket.tokens += elapsed * bucket.refillRate
	if bucket.tokens > bucket.maxTokens {
		bucket.tokens = bucket.maxTokens
	}
	bucket.lastRefill = now

	if bucket.tokens < 1 {
		return false
	}

	bucket.tokens--
	return true
}

// RateLimitUnaryInterceptor returns a gRPC unary interceptor that applies
// a per-identity token bucket rate limit. Requests exceeding the limit are
// rejected with ResourceExhausted.
func RateLimitUnaryInterceptor(rps int) grpc.UnaryServerInterceptor {
	limiter := newRateLimiter(rps)

	return func(
		ctx context.Context,
		req any,
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (any, error) {
		clientID := ClientIDFromContext(ctx)
		if clientID == "" {
			clientID = "anonymous"
		}

		if !limiter.allow(clientID) {
			return nil, status.Errorf(codes.ResourceExhausted,
				"rate limit exceeded for %q: max %d req/s", clientID, rps)
		}

		return handler(ctx, req)
	}
}
