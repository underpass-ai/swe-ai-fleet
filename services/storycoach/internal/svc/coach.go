// Package svc implements the StoryCoachService gRPC server
package svc

import (
	"context"

	coachv1 "github.com/underpass-ai/swe-ai-fleet/services/storycoach/gen/fleet/storycoach/v1"
	"github.com/underpass-ai/swe-ai-fleet/services/storycoach/internal/scorer"
)

// Coach implements StoryCoachService
type Coach struct {
	coachv1.UnimplementedStoryCoachServiceServer
}

// NewCoach creates a new Coach service
func NewCoach() *Coach {
	return &Coach{}
}

// ScoreStory evaluates a story and returns findings
func (c *Coach) ScoreStory(ctx context.Context, req *coachv1.ScoreStoryRequest) (*coachv1.ScoreStoryResponse, error) {
	score, findings := scorer.ScoreStory(req.Title, req.Description, req.Ac)

	return &coachv1.ScoreStoryResponse{
		Total:    score,
		Findings: findings,
	}, nil
}

// RefineStory suggests improvements to a story
func (c *Coach) RefineStory(ctx context.Context, req *coachv1.RefineStoryRequest) (*coachv1.RefineStoryResponse, error) {
	title, desc, ac := scorer.RefineStory(req.Title, req.Description, req.Ac)

	return &coachv1.RefineStoryResponse{
		Title:       title,
		Description: desc,
		Ac:          ac,
	}, nil
}

// SuggestStory generates a story template from a goal
func (c *Coach) SuggestStory(ctx context.Context, req *coachv1.SuggestStoryRequest) (*coachv1.SuggestStoryResponse, error) {
	title, desc, ac := scorer.SuggestStory(req.Goal)

	return &coachv1.SuggestStoryResponse{
		Title:       title,
		Description: desc,
		Ac:          ac,
	}, nil
}


