package keystore

import (
	"context"
	"testing"
)

func TestStaticStore_Validate(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		config    string
		keyID     string
		secret    string
		wantID    string
		wantErr   bool
		errSubstr string
	}{
		{
			name:   "valid single entry",
			config: "k1:s1:alice:laptop",
			keyID:  "k1",
			secret: "s1",
			wantID: "spiffe://swe-ai-fleet/user/alice/device/laptop",
		},
		{
			name:   "valid with multiple entries",
			config: "k1:s1:alice:laptop;k2:s2:bob:desktop",
			keyID:  "k2",
			secret: "s2",
			wantID: "spiffe://swe-ai-fleet/user/bob/device/desktop",
		},
		{
			name:      "unknown key ID",
			config:    "k1:s1:alice:laptop",
			keyID:     "unknown",
			secret:    "s1",
			wantErr:   true,
			errSubstr: "unknown API key ID",
		},
		{
			name:      "wrong secret",
			config:    "k1:s1:alice:laptop",
			keyID:     "k1",
			secret:    "wrong",
			wantErr:   true,
			errSubstr: "invalid secret",
		},
		{
			name:   "entry with hyphens and underscores",
			config: "e2e-key:e2e-secret:e2e_user:e2e-device",
			keyID:  "e2e-key",
			secret: "e2e-secret",
			wantID: "spiffe://swe-ai-fleet/user/e2e_user/device/e2e-device",
		},
		{
			name:   "trailing semicolon ignored",
			config: "k1:s1:alice:laptop;",
			keyID:  "k1",
			secret: "s1",
			wantID: "spiffe://swe-ai-fleet/user/alice/device/laptop",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			store, err := NewStaticStore(tt.config)
			if err != nil {
				t.Fatalf("NewStaticStore(%q) unexpected error: %v", tt.config, err)
			}

			got, err := store.Validate(context.Background(), tt.keyID, tt.secret)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error containing %q, got nil", tt.errSubstr)
				}
				if tt.errSubstr != "" && !containsSubstr(err.Error(), tt.errSubstr) {
					t.Fatalf("expected error containing %q, got %q", tt.errSubstr, err.Error())
				}
				return
			}

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.String() != tt.wantID {
				t.Errorf("ClientID = %q, want %q", got.String(), tt.wantID)
			}
		})
	}
}

func TestNewStaticStore_Errors(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		config    string
		errSubstr string
	}{
		{
			name:      "empty config",
			config:    "",
			errSubstr: "empty",
		},
		{
			name:      "whitespace only",
			config:    "   ",
			errSubstr: "empty",
		},
		{
			name:      "too few fields",
			config:    "k1:s1:alice",
			errSubstr: "malformed",
		},
		{
			name:      "empty field in entry",
			config:    "k1::alice:laptop",
			errSubstr: "non-empty",
		},
		{
			name:      "only semicolons",
			config:    ";;;",
			errSubstr: "no valid entries",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			_, err := NewStaticStore(tt.config)
			if err == nil {
				t.Fatalf("expected error containing %q, got nil", tt.errSubstr)
			}
			if !containsSubstr(err.Error(), tt.errSubstr) {
				t.Fatalf("expected error containing %q, got %q", tt.errSubstr, err.Error())
			}
		})
	}
}

func TestStaticStore_Entries(t *testing.T) {
	t.Parallel()

	store, err := NewStaticStore("k1:s1:alice:laptop;k2:s2:bob:desktop")
	if err != nil {
		t.Fatalf("NewStaticStore unexpected error: %v", err)
	}

	entries := store.Entries()
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(entries))
	}

	found := make(map[string]bool)
	for _, e := range entries {
		found[e.KeyID] = true
	}
	if !found["k1"] || !found["k2"] {
		t.Errorf("expected entries for k1 and k2, got %v", found)
	}
}

func containsSubstr(s, substr string) bool {
	return len(s) >= len(substr) && searchSubstring(s, substr)
}

func searchSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
