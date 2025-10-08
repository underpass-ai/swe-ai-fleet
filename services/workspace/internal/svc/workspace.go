// Package svc implements the WorkspaceService gRPC server
package svc

import (
	"context"

	wsv1 "github.com/underpass-ai/swe-ai-fleet/services/workspace/gen/fleet/workspace/v1"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/scorer"
)

// Workspace implements WorkspaceService
type Workspace struct {
	wsv1.UnimplementedWorkspaceServiceServer
	rigorCfg *scorer.RigorConfig
}

// NewWorkspace creates a new Workspace service
func NewWorkspace(rigorCfg *scorer.RigorConfig) *Workspace {
	return &Workspace{
		rigorCfg: rigorCfg,
	}
}

// ScoreWorkspace evaluates workspace results against rigor profile
func (w *Workspace) ScoreWorkspace(ctx context.Context, req *wsv1.ScoreWorkspaceRequest) (*wsv1.ScoreWorkspaceResponse, error) {
	rigorLevel := req.RigorLevel
	if rigorLevel == "" {
		rigorLevel = "L1" // Default
	}

	score, reasons, gating := scorer.ScoreWorkspace(req.Report, rigorLevel, w.rigorCfg)

	return &wsv1.ScoreWorkspaceResponse{
		Score:          score,
		Rigor:          rigorLevel,
		Reasons:        reasons,
		GatingDecision: gating,
	}, nil
}


