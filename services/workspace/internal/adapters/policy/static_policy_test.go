package policy

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestStaticPolicy_DeniesClusterScopeWithoutRole(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"developer"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:     domain.ScopeCluster,
			RiskLevel: domain.RiskLow,
		},
		Approved: true,
		Args:     json.RawMessage(`{}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected decision to deny cluster scope")
	}
}

func TestStaticPolicy_RequiresApproval(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"developer"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:            domain.ScopeWorkspace,
			RiskLevel:        domain.RiskMedium,
			RequiresApproval: true,
		},
		Approved: false,
		Args:     json.RawMessage(`{"path":"x.txt"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected decision to deny when approval is missing")
	}
	if decision.ErrorCode != app.ErrorCodeApprovalRequired {
		t.Fatalf("unexpected error code: %s", decision.ErrorCode)
	}
}

func TestStaticPolicy_DeniesPathOutsideAllowList(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"developer"}}, AllowedPaths: []string{"src"}},
		Capability: domain.Capability{
			Scope:     domain.ScopeWorkspace,
			RiskLevel: domain.RiskLow,
			Policy: domain.PolicyMetadata{
				PathFields: []domain.PolicyPathField{{Field: "path", WorkspaceRelative: true}},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"path":"../outside.txt"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected decision to deny path traversal")
	}
}
