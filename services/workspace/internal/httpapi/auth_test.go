package httpapi

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAuthConfigFromEnv_DefaultPayload(t *testing.T) {
	t.Setenv("WORKSPACE_AUTH_MODE", "")
	t.Setenv("WORKSPACE_AUTH_SHARED_TOKEN", "")

	cfg, err := AuthConfigFromEnv()
	if err != nil {
		t.Fatalf("unexpected default auth config error: %v", err)
	}
	if cfg.Mode != authModePayload {
		t.Fatalf("expected default payload mode, got %q", cfg.Mode)
	}
}

func TestAuthConfigFromEnv_TrustedHeadersRequiresToken(t *testing.T) {
	t.Setenv("WORKSPACE_AUTH_MODE", authModeTrustedHeaders)
	t.Setenv("WORKSPACE_AUTH_SHARED_TOKEN", "")

	if _, err := AuthConfigFromEnv(); err == nil {
		t.Fatal("expected missing shared token error")
	}
}

func TestAuthConfigAuthenticatePrincipal(t *testing.T) {
	cfg := AuthConfig{
		Mode:         authModeTrustedHeaders,
		TenantHeader: "X-Workspace-Tenant-Id",
		ActorHeader:  "X-Workspace-Actor-Id",
		RolesHeader:  "X-Workspace-Roles",
		TokenHeader:  "X-Workspace-Auth-Token",
		SharedToken:  "shared-token",
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/sessions", nil)
	req.Header.Set("X-Workspace-Auth-Token", "shared-token")
	req.Header.Set("X-Workspace-Tenant-Id", "tenant-a")
	req.Header.Set("X-Workspace-Actor-Id", "actor-a")
	req.Header.Set("X-Workspace-Roles", "devops,developer,devops")

	principal, authErr := cfg.authenticatePrincipal(req)
	if authErr != nil {
		t.Fatalf("unexpected auth error: %#v", authErr)
	}
	if principal.TenantID != "tenant-a" || principal.ActorID != "actor-a" {
		t.Fatalf("unexpected principal: %#v", principal)
	}
	if len(principal.Roles) != 2 {
		t.Fatalf("expected deduped roles, got %#v", principal.Roles)
	}
}

func TestAuthConfigAuthenticatePrincipalRejectsInvalidToken(t *testing.T) {
	cfg := DefaultAuthConfig()
	cfg.Mode = authModeTrustedHeaders
	cfg.SharedToken = "expected-token"

	req := httptest.NewRequest(http.MethodPost, "/v1/sessions", nil)
	req.Header.Set(cfg.TokenHeader, "bad-token")
	req.Header.Set(cfg.TenantHeader, "tenant-a")
	req.Header.Set(cfg.ActorHeader, "actor-a")

	_, authErr := cfg.authenticatePrincipal(req)
	if authErr == nil {
		t.Fatal("expected auth failure")
	}
	if authErr.status != http.StatusUnauthorized {
		t.Fatalf("expected unauthorized, got %#v", authErr)
	}
}
