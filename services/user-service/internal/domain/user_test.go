package domain

import "testing"

func TestNewUser_Success(t *testing.T) {
	u, err := NewUser("spiffe://fleet/user/alice", "device-1", "Alice", "alice@example.com", "operator")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u.UserID == "" {
		t.Fatal("expected non-empty UserID")
	}
	if u.ClientID != "spiffe://fleet/user/alice" {
		t.Fatalf("got ClientID %q", u.ClientID)
	}
	if u.Role != "operator" {
		t.Fatalf("got Role %q", u.Role)
	}
	if u.CreatedAt.IsZero() {
		t.Fatal("expected non-zero CreatedAt")
	}
}

func TestNewUser_DefaultRole(t *testing.T) {
	u, err := NewUser("cid", "did", "Name", "", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u.Role != "operator" {
		t.Fatalf("expected default role 'operator', got %q", u.Role)
	}
}

func TestNewUser_AllRoles(t *testing.T) {
	for _, role := range []string{"operator", "viewer", "admin"} {
		u, err := NewUser("cid", "did", "Name", "", role)
		if err != nil {
			t.Fatalf("unexpected error for role %q: %v", role, err)
		}
		if u.Role != role {
			t.Fatalf("expected role %q, got %q", role, u.Role)
		}
	}
}

func TestNewUser_InvalidRole(t *testing.T) {
	_, err := NewUser("cid", "did", "Name", "", "superuser")
	if err == nil {
		t.Fatal("expected error for invalid role")
	}
}

func TestNewUser_MissingClientID(t *testing.T) {
	_, err := NewUser("", "did", "Name", "", "operator")
	if err == nil {
		t.Fatal("expected error for missing client_id")
	}
}

func TestNewUser_MissingDeviceID(t *testing.T) {
	_, err := NewUser("cid", "", "Name", "", "operator")
	if err == nil {
		t.Fatal("expected error for missing device_id")
	}
}

func TestNewUser_MissingDisplayName(t *testing.T) {
	_, err := NewUser("cid", "did", "", "", "operator")
	if err == nil {
		t.Fatal("expected error for missing display_name")
	}
}
