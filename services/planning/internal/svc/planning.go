// Package svc implements the PlanningService gRPC server
package svc

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	nats "github.com/nats-io/nats.go"

	planningv1 "github.com/underpass-ai/swe-ai-fleet/services/planning/gen/fleet/planning/v1"
	"github.com/underpass-ai/swe-ai-fleet/services/planning/internal/fsmx"
)

// Story represents a story in memory (replace with DB in production)
type Story struct {
	StoryID  string
	Title    string
	Brief    string
	AC       []string
	State    string
	DorScore int32
	Engine   *fsmx.Engine // Each story has its own FSM instance
}

// Planning implements PlanningService gRPC server
type Planning struct {
	planningv1.UnimplementedPlanningServiceServer

	mu      sync.RWMutex
	stories map[string]*Story
	js      nats.JetStreamContext
	fsmCfg  fsmx.Config
}

// NewPlanning creates a new Planning service
func NewPlanning(fsmCfg fsmx.Config, js nats.JetStreamContext) *Planning {
	return &Planning{
		stories: make(map[string]*Story),
		js:      js,
		fsmCfg:  fsmCfg,
	}
}

// CreateStory creates a new story and initializes its FSM
func (s *Planning) CreateStory(ctx context.Context, req *planningv1.CreateStoryRequest) (*planningv1.CreateStoryResponse, error) {
	storyID := fmt.Sprintf("s-%s", uuid.New().String()[:8])

	// Compute DoR score (simplified - call story coach in production)
	dorScore := s.computeDoR(req.Title, req.Brief, req.Ac)

	// Create FSM engine for this story
	engine := fsmx.New(s.fsmCfg)

	story := &Story{
		StoryID:  storyID,
		Title:    req.Title,
		Brief:    req.Brief,
		AC:       req.Ac,
		State:    engine.Current(),
		DorScore: dorScore,
		Engine:   engine,
	}

	s.mu.Lock()
	s.stories[storyID] = story
	s.mu.Unlock()

	// Try to transition to DRAFT
	guardCtx := fsmx.GuardContext{
		StoryID:  storyID,
		DorScore: int(dorScore),
		Metadata: make(map[string]interface{}),
	}

	if err := engine.Try("create_story", guardCtx); err == nil {
		story.State = engine.Current()
	}

	// Publish AgileEvent
	s.publishEvent(storyID, "CASE_CREATED", "", story.State, "system")

	return &planningv1.CreateStoryResponse{
		StoryId:  storyID,
		State:    story.State,
		DorScore: dorScore,
	}, nil
}

// ListStories returns all stories
func (s *Planning) ListStories(ctx context.Context, req *planningv1.ListStoriesRequest) (*planningv1.ListStoriesResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	stories := make([]*planningv1.Story, 0, len(s.stories))
	for _, st := range s.stories {
		stories = append(stories, &planningv1.Story{
			StoryId:  st.StoryID,
			Title:    st.Title,
			State:    st.State,
			DorScore: st.DorScore,
			Brief:    st.Brief,
		})
	}

	return &planningv1.ListStoriesResponse{Stories: stories}, nil
}

// GetStory returns story details
func (s *Planning) GetStory(ctx context.Context, req *planningv1.GetStoryRequest) (*planningv1.GetStoryResponse, error) {
	s.mu.RLock()
	story, ok := s.stories[req.StoryId]
	s.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("story not found: %s", req.StoryId)
	}

	planJSON, _ := story.Engine.Marshal()

	return &planningv1.GetStoryResponse{
		Story: &planningv1.Story{
			StoryId:  story.StoryID,
			Title:    story.Title,
			State:    story.State,
			DorScore: story.DorScore,
			Brief:    story.Brief,
		},
		Ac:       story.AC,
		PlanJson: string(planJSON),
	}, nil
}

// Transition attempts a state transition
func (s *Planning) Transition(ctx context.Context, req *planningv1.TransitionRequest) (*planningv1.TransitionResponse, error) {
	s.mu.Lock()
	story, ok := s.stories[req.StoryId]
	s.mu.Unlock()

	if !ok {
		return nil, fmt.Errorf("story not found: %s", req.StoryId)
	}

	fromState := story.Engine.Current()

	// Build guard context
	guardCtx := fsmx.GuardContext{
		StoryID:    req.StoryId,
		DorScore:   int(story.DorScore),
		POApproved: req.Actor == "po", // Simplified: PO actor implies approval
		QAApproved: req.Actor == "qa",
		RigorLevel: "L1", // TODO: get from story metadata
		Metadata:   make(map[string]interface{}),
	}

	// Try transition
	err := story.Engine.Try(req.Event, guardCtx)
	if err != nil {
		return &planningv1.TransitionResponse{
			StoryId: req.StoryId,
			State:   story.Engine.Current(),
			Blocked: true,
			Reason:  err.Error(),
		}, nil
	}

	// Update story state
	s.mu.Lock()
	story.State = story.Engine.Current()
	s.mu.Unlock()

	// Publish AgileEvent
	s.publishEvent(req.StoryId, "TRANSITION", fromState, story.State, req.Actor)

	return &planningv1.TransitionResponse{
		StoryId: req.StoryId,
		State:   story.State,
		Blocked: false,
	}, nil
}

// GetPlan returns the FSM plan for a story
func (s *Planning) GetPlan(ctx context.Context, req *planningv1.GetPlanRequest) (*planningv1.GetPlanResponse, error) {
	s.mu.RLock()
	story, ok := s.stories[req.StoryId]
	s.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("story not found: %s", req.StoryId)
	}

	planJSON, err := story.Engine.Marshal()
	if err != nil {
		return nil, fmt.Errorf("marshal plan: %w", err)
	}

	return &planningv1.GetPlanResponse{
		Json: string(planJSON),
	}, nil
}

// computeDoR computes a simplified DoR score
func (s *Planning) computeDoR(title, brief string, ac []string) int32 {
	score := int32(0)

	// Title present
	if len(title) > 0 {
		score += 20
	}

	// Brief present and reasonable length
	if len(brief) > 20 && len(brief) < 500 {
		score += 30
	}

	// AC present
	if len(ac) > 0 {
		score += 40
	}

	// AC has Gherkin keywords
	hasGherkin := false
	for _, criterion := range ac {
		if len(criterion) > 10 {
			hasGherkin = true
			break
		}
	}
	if hasGherkin {
		score += 10
	}

	return score
}

// publishEvent publishes an AgileEvent to NATS
func (s *Planning) publishEvent(storyID, eventType, from, to, actor string) {
	event := map[string]interface{}{
		"event_id":   uuid.New().String(),
		"case_id":    storyID,
		"ts":         time.Now().Format(time.RFC3339),
		"producer":   "planning-service",
		"event_type": eventType,
		"from":       from,
		"to":         to,
		"actor":      actor,
	}

	payload, _ := json.Marshal(event)
	s.js.Publish("agile.events", payload)
}


