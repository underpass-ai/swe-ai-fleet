package policy

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestStaticPolicy_AllowsClusterScopeForDevops(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"devops"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:     domain.ScopeCluster,
			RiskLevel: domain.RiskLow,
		},
		Approved: true,
		Args:     json.RawMessage(`{"path":"valid.txt"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !decision.Allow {
		t.Fatalf("expected allow for devops role: %#v", decision)
	}
}

func TestStaticPolicy_DeniesHighRiskWithoutPlatformAdmin(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"devops"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:     domain.ScopeCluster,
			RiskLevel: domain.RiskHigh,
		},
		Approved: true,
		Args:     json.RawMessage(`{"path":"valid.txt"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected high-risk denial without platform_admin")
	}
}

func TestStaticPolicy_PathParsingPayloadErrors(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"developer"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:     domain.ScopeWorkspace,
			RiskLevel: domain.RiskLow,
			Policy: domain.PolicyMetadata{
				PathFields: []domain.PolicyPathField{{Field: "path", WorkspaceRelative: true}},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"path":`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected invalid args payload to be denied")
	}
}

func TestStaticPolicy_DeniesDisallowedArgPrefix(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"developer"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:     domain.ScopeRepo,
			RiskLevel: domain.RiskMedium,
			Policy: domain.PolicyMetadata{
				ArgFields: []domain.PolicyArgField{
					{
						Field:         "extra_args",
						Multi:         true,
						MaxItems:      4,
						MaxLength:     32,
						AllowedPrefix: []string{"-v", "-run=", "-count=", "-timeout="},
						DeniedPrefix:  []string{"-exec", "-toolexec"},
					},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"extra_args":["-exec=cat"]}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected policy denial for disallowed arg prefix")
	}
}

func TestStaticPolicy_AllowsApprovedArgPrefixes(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{Principal: domain.Principal{Roles: []string{"developer"}}, AllowedPaths: []string{"."}},
		Capability: domain.Capability{
			Scope:     domain.ScopeRepo,
			RiskLevel: domain.RiskMedium,
			Policy: domain.PolicyMetadata{
				ArgFields: []domain.PolicyArgField{
					{
						Field:         "extra_args",
						Multi:         true,
						MaxItems:      3,
						MaxLength:     24,
						AllowedPrefix: []string{"-v", "-run=", "-count=", "-timeout="},
					},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"extra_args":["-v","-run=TestTodo"]}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !decision.Allow {
		t.Fatalf("expected allow decision, got %#v", decision)
	}
}
