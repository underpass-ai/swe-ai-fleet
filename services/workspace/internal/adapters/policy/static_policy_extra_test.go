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

func TestStaticPolicy_DeniesProfileOutsideAllowlist(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{
			Principal:    domain.Principal{Roles: []string{"developer"}},
			AllowedPaths: []string{"."},
			Metadata: map[string]string{
				"allowed_profiles": "dev.redis,dev.nats",
			},
		},
		Capability: domain.Capability{
			Scope:     domain.ScopeWorkspace,
			RiskLevel: domain.RiskLow,
			Policy: domain.PolicyMetadata{
				ProfileFields: []domain.PolicyProfileField{
					{Field: "profile_id"},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"profile_id":"prod.redis"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected policy denial for disallowed profile")
	}
}

func TestStaticPolicy_AllowsProfileWhenAllowlistNotConfigured(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{
			Principal:    domain.Principal{Roles: []string{"developer"}},
			AllowedPaths: []string{"."},
		},
		Capability: domain.Capability{
			Scope:     domain.ScopeWorkspace,
			RiskLevel: domain.RiskLow,
			Policy: domain.PolicyMetadata{
				ProfileFields: []domain.PolicyProfileField{
					{Field: "profile_id"},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"profile_id":"any.profile"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !decision.Allow {
		t.Fatalf("expected allow without configured profile allowlist, got %#v", decision)
	}
}

func TestStaticPolicy_DeniesSubjectOutsideAllowlist(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{
			Principal:    domain.Principal{Roles: []string{"devops"}},
			AllowedPaths: []string{"."},
			Metadata: map[string]string{
				"allowed_nats_subjects": "sandbox.>,dev.>",
			},
		},
		Capability: domain.Capability{
			Scope:     domain.ScopeExternal,
			RiskLevel: domain.RiskMedium,
			Policy: domain.PolicyMetadata{
				SubjectFields: []domain.PolicySubjectField{
					{Field: "subject"},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"subject":"prod.orders"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected subject deny")
	}
}

func TestStaticPolicy_AllowsWildcardSubject(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{
			Principal:    domain.Principal{Roles: []string{"devops"}},
			AllowedPaths: []string{"."},
			Metadata: map[string]string{
				"allowed_nats_subjects": "sandbox.>",
			},
		},
		Capability: domain.Capability{
			Scope:     domain.ScopeExternal,
			RiskLevel: domain.RiskMedium,
			Policy: domain.PolicyMetadata{
				SubjectFields: []domain.PolicySubjectField{
					{Field: "subject"},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"subject":"sandbox.worker.jobs"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !decision.Allow {
		t.Fatalf("expected allow, got %#v", decision)
	}
}

func TestStaticPolicy_DeniesTopicOutsideAllowlist(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{
			Principal:    domain.Principal{Roles: []string{"devops"}},
			AllowedPaths: []string{"."},
			Metadata: map[string]string{
				"allowed_kafka_topics": "sandbox.,dev.",
			},
		},
		Capability: domain.Capability{
			Scope:     domain.ScopeExternal,
			RiskLevel: domain.RiskMedium,
			Policy: domain.PolicyMetadata{
				TopicFields: []domain.PolicyTopicField{
					{Field: "topic"},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"topic":"prod.payments"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.Allow {
		t.Fatal("expected topic deny")
	}
}

func TestStaticPolicy_AllowsKeyWithinAllowedPrefix(t *testing.T) {
	engine := NewStaticPolicy()
	decision, err := engine.Authorize(context.Background(), app.PolicyInput{
		Session: domain.Session{
			Principal:    domain.Principal{Roles: []string{"devops"}},
			AllowedPaths: []string{"."},
			Metadata: map[string]string{
				"allowed_redis_key_prefixes": "sandbox:,dev:",
			},
		},
		Capability: domain.Capability{
			Scope:     domain.ScopeExternal,
			RiskLevel: domain.RiskMedium,
			Policy: domain.PolicyMetadata{
				KeyPrefixFields: []domain.PolicyKeyPrefixField{
					{Field: "key"},
				},
			},
		},
		Approved: true,
		Args:     json.RawMessage(`{"key":"sandbox:todo:123"}`),
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !decision.Allow {
		t.Fatalf("expected key allow, got %#v", decision)
	}
}
