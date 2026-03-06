package interceptors

import (
	"testing"
	"time"
)

func TestRateLimiter_Allow(t *testing.T) {
	t.Parallel()

	rl := &rateLimiter{
		buckets: make(map[string]*tokenBucket),
		rps:     2,
		stopCh:  make(chan struct{}),
	}

	// First two requests should be allowed.
	if !rl.allow("client-a") {
		t.Fatal("first request should be allowed")
	}
	if !rl.allow("client-a") {
		t.Fatal("second request should be allowed")
	}

	// Third request should be rate-limited (no time elapsed for refill).
	if rl.allow("client-a") {
		t.Fatal("third request should be rate-limited")
	}

	// Different identity should have its own bucket.
	if !rl.allow("client-b") {
		t.Fatal("different client should not be rate-limited")
	}
}

func TestRateLimiter_EvictStale(t *testing.T) {
	t.Parallel()

	rl := &rateLimiter{
		buckets: make(map[string]*tokenBucket),
		rps:     10,
		stopCh:  make(chan struct{}),
	}

	// Create a bucket and then backdate its lastRefill.
	rl.allow("stale-client")
	rl.mu.Lock()
	rl.buckets["stale-client"].lastRefill = time.Now().Add(-10 * time.Minute)
	rl.mu.Unlock()

	// Fresh bucket.
	rl.allow("fresh-client")

	rl.evictStale()

	rl.mu.Lock()
	defer rl.mu.Unlock()

	if _, exists := rl.buckets["stale-client"]; exists {
		t.Error("stale bucket should have been evicted")
	}
	if _, exists := rl.buckets["fresh-client"]; !exists {
		t.Error("fresh bucket should still exist")
	}
}

func TestRateLimiter_Refill(t *testing.T) {
	t.Parallel()

	rl := &rateLimiter{
		buckets: make(map[string]*tokenBucket),
		rps:     1,
		stopCh:  make(chan struct{}),
	}

	// Use the single token.
	if !rl.allow("client-c") {
		t.Fatal("first request should be allowed")
	}
	if rl.allow("client-c") {
		t.Fatal("second request should be rate-limited")
	}

	// Simulate time passing by backdating lastRefill.
	rl.mu.Lock()
	rl.buckets["client-c"].lastRefill = time.Now().Add(-2 * time.Second)
	rl.mu.Unlock()

	// After enough time, tokens should have refilled.
	if !rl.allow("client-c") {
		t.Fatal("request after refill should be allowed")
	}
}
