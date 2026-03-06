package identity

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"
)

func TestNewCertFingerprint(t *testing.T) {
	t.Parallel()

	t.Run("valid DER bytes", func(t *testing.T) {
		t.Parallel()

		der := []byte("fake-der-encoded-certificate")
		fp := NewCertFingerprint(der)

		// Verify SHA-256 matches.
		expected := sha256.Sum256(der)
		if fp.Bytes() != expected {
			t.Errorf("Bytes() = %x, want %x", fp.Bytes(), expected)
		}

		// Verify hex string matches.
		wantHex := hex.EncodeToString(expected[:])
		if fp.String() != wantHex {
			t.Errorf("String() = %q, want %q", fp.String(), wantHex)
		}

		if fp.IsZero() {
			t.Error("IsZero() = true for non-empty DER, want false")
		}
	})

	t.Run("empty DER bytes", func(t *testing.T) {
		t.Parallel()

		fp := NewCertFingerprint([]byte{})

		// SHA-256 of empty input is the well-known constant.
		expected := sha256.Sum256([]byte{})
		if fp.Bytes() != expected {
			t.Errorf("Bytes() = %x, want %x", fp.Bytes(), expected)
		}

		// SHA-256 of empty input is NOT all zeroes, so IsZero should be false.
		if fp.IsZero() {
			t.Error("IsZero() = true for SHA-256 of empty bytes, want false (hash is not zero)")
		}
	})

	t.Run("nil DER bytes", func(t *testing.T) {
		t.Parallel()

		fp := NewCertFingerprint(nil)

		// SHA-256 of nil is the same as SHA-256 of empty.
		expected := sha256.Sum256(nil)
		if fp.Bytes() != expected {
			t.Errorf("Bytes() = %x, want %x", fp.Bytes(), expected)
		}
	})
}

func TestCertFingerprint_IsZero(t *testing.T) {
	t.Parallel()

	var zero CertFingerprint
	if !zero.IsZero() {
		t.Error("IsZero() = false for zero-value CertFingerprint, want true")
	}

	if zero.String() != hex.EncodeToString(make([]byte, 32)) {
		t.Errorf("String() = %q for zero-value, want all-zeroes hex", zero.String())
	}
}
