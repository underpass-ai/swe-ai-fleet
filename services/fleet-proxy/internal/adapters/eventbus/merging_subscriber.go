package eventbus

import (
	"context"
	"sync"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// MergingSubscriber combines multiple EventSubscriber sources into a single
// channel. It implements ports.EventSubscriber.
type MergingSubscriber struct {
	sources []ports.EventSubscriber
}

// NewMerging creates a MergingSubscriber that merges events from all sources.
func NewMerging(sources ...ports.EventSubscriber) *MergingSubscriber {
	return &MergingSubscriber{sources: sources}
}

// Subscribe opens a subscription on each source and merges events into a
// single output channel. The output channel is closed when all sources are
// exhausted or ctx is cancelled.
func (m *MergingSubscriber) Subscribe(ctx context.Context, filter event.EventFilter) (<-chan event.FleetEvent, error) {
	merged := make(chan event.FleetEvent, 256)

	// Use a child context so we can cancel already-started goroutines if a
	// later source fails to subscribe.
	childCtx, cancelChild := context.WithCancel(ctx)

	var wg sync.WaitGroup
	for _, src := range m.sources {
		ch, err := src.Subscribe(childCtx, filter)
		if err != nil {
			// Cancel already-launched goroutines and wait for them to exit
			// before closing merged (prevents send-on-closed-channel panic).
			cancelChild()
			wg.Wait()
			close(merged)
			return nil, err
		}
		wg.Add(1)
		go func(ch <-chan event.FleetEvent) {
			defer wg.Done()
			for evt := range ch {
				select {
				case merged <- evt:
				case <-childCtx.Done():
					return
				}
			}
		}(ch)
	}

	go func() {
		wg.Wait()
		cancelChild()
		close(merged)
	}()

	return merged, nil
}

// Close tears down all underlying sources.
func (m *MergingSubscriber) Close() error {
	var firstErr error
	for _, src := range m.sources {
		if err := src.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}
