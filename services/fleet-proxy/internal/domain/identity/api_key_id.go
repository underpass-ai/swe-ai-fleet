package identity

import (
	"errors"
	"fmt"
	"regexp"
)

// uuidPattern matches a standard UUID v4 format (case-insensitive).
var uuidPattern = regexp.MustCompile(
	`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`,
)

// ApiKeyID is a value object wrapping a UUID string that identifies an API key.
type ApiKeyID struct {
	raw string
}

// NewApiKeyID creates an ApiKeyID from a raw UUID string.
// It validates the string is non-empty and matches UUID format.
func NewApiKeyID(raw string) (ApiKeyID, error) {
	if raw == "" {
		return ApiKeyID{}, errors.New("API key ID cannot be empty")
	}

	if !uuidPattern.MatchString(raw) {
		return ApiKeyID{}, fmt.Errorf("invalid API key ID %q: must be a valid UUID", raw)
	}

	return ApiKeyID{raw: raw}, nil
}

// String returns the UUID string.
func (a ApiKeyID) String() string {
	return a.raw
}

// IsZero reports whether the ApiKeyID is the zero value.
func (a ApiKeyID) IsZero() bool {
	return a.raw == ""
}
