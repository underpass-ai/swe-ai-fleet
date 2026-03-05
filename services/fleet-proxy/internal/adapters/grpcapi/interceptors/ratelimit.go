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

// staleBucketTTL is the duration after which an idle bucket is evicted.
const staleBucketTTL = 5 * time.Minute

// evictionInterval controls how often the background goroutine sweeps stale buckets.
const evictionInterval = 1 * time.Minute

// rateLimiter manages per-identity token buckets.
type rateLimiter struct {
	mu      sync.Mutex
	buckets map[string]*tokenBucket
	rps     int
	stopCh  chan struct{}
}

// newRateLimiter creates a rate limiter with the given requests-per-second
// limit and starts a background goroutine that evicts stale buckets.
func newRateLimiter(rps int) *rateLimiter {
	rl := &rateLimiter{
		buckets: make(map[string]*tokenBucket),
		rps:     rps,
		stopCh:  make(chan struct{}),
	}
	go rl.evictLoop()
	return rl
}

// evictLoop periodically removes buckets that have been idle longer than staleBucketTTL.
func (r *rateLimiter) evictLoop() {
	ticker := time.NewTicker(evictionInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			r.evictStale()
		case <-r.stopCh:
			return
		}
	}
}

// evictStale removes buckets whose last activity was more than staleBucketTTL ago.
func (r *rateLimiter) evictStale() {
	r.mu.Lock()
	defer r.mu.Unlock()
	cutoff := time.Now().Add(-staleBucketTTL)
	for id, b := range r.buckets {
		if b.lastRefill.Before(cutoff) {
			delete(r.buckets, id)
		}
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
// a per-identity token bucket rate limit, and a stop function that shuts down
// the background eviction goroutine. The caller must invoke the returned
// stop function when the server shuts down to avoid goroutine leaks.
func RateLimitUnaryInterceptor(rps int) (grpc.UnaryServerInterceptor, func()) {
	limiter := newRateLimiter(rps)

	interceptor := func(
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

	stop := func() { close(limiter.stopCh) }
	return interceptor, stop
}
