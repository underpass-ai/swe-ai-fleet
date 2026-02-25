package identity

import (
	"errors"
	"fmt"
	"net/url"
)

// SANUri is a value object wrapping a Subject Alternative Name URI.
// It must be a syntactically valid URI with a scheme.
type SANUri struct {
	raw string
}

// NewSANUri creates a SANUri from a raw URI string.
// It validates that the string is a well-formed URI with a scheme.
func NewSANUri(raw string) (SANUri, error) {
	if raw == "" {
		return SANUri{}, errors.New("SAN URI cannot be empty")
	}

	u, err := url.Parse(raw)
	if err != nil {
		return SANUri{}, fmt.Errorf("invalid SAN URI %q: %w", raw, err)
	}

	if u.Scheme == "" {
		return SANUri{}, fmt.Errorf("invalid SAN URI %q: missing scheme", raw)
	}

	return SANUri{raw: raw}, nil
}

// String returns the URI string.
func (s SANUri) String() string {
	return s.raw
}

// IsZero reports whether the SANUri is the zero value.
func (s SANUri) IsZero() bool {
	return s.raw == ""
}
