package identity

import "testing"

func TestNewServerName_Valid(t *testing.T) {
	sn, err := NewServerName("fleet.example.com")
	if err != nil {
		t.Fatalf("NewServerName() unexpected error: %v", err)
	}
	if sn.String() != "fleet.example.com" {
		t.Errorf("String() = %q, want %q", sn.String(), "fleet.example.com")
	}
}

func TestNewServerName_Trimmed(t *testing.T) {
	sn, err := NewServerName("  fleet.example.com  ")
	if err != nil {
		t.Fatalf("NewServerName() unexpected error: %v", err)
	}
	if sn.String() != "fleet.example.com" {
		t.Errorf("String() = %q, want trimmed %q", sn.String(), "fleet.example.com")
	}
}

func TestNewServerName_Empty(t *testing.T) {
	_, err := NewServerName("")
	if err == nil {
		t.Fatal("NewServerName(\"\") expected error, got nil")
	}
}

func TestNewServerName_Whitespace(t *testing.T) {
	_, err := NewServerName("   ")
	if err == nil {
		t.Fatal("NewServerName(\"   \") expected error, got nil")
	}
}

func TestServerName_String_ZeroValue(t *testing.T) {
	var sn ServerName
	if sn.String() != "" {
		t.Errorf("zero-value String() = %q, want empty", sn.String())
	}
}
