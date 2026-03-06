package identity

import (
	"errors"
	"fmt"
	"regexp"
)

// spiffePattern matches the SPIFFE URI format used by swe-ai-fleet.
// Format: spiffe://swe-ai-fleet/user/{userId}/device/{deviceId}
// userId and deviceId must be non-empty alphanumeric strings (plus hyphens and underscores).
var spiffePattern = regexp.MustCompile(
	`^spiffe://swe-ai-fleet/user/([a-zA-Z0-9_-]+)/device/([a-zA-Z0-9_-]+)$`,
)

// ClientID is a value object wrapping a SPIFFE URI that uniquely identifies
// a client in the swe-ai-fleet trust domain.
type ClientID struct {
	raw      string
	userID   string
	deviceID string
}

// NewClientID creates a ClientID from a raw SPIFFE URI string.
// It validates the format matches spiffe://swe-ai-fleet/user/{userId}/device/{deviceId}.
func NewClientID(raw string) (ClientID, error) {
	if raw == "" {
		return ClientID{}, errors.New("client ID cannot be empty")
	}

	matches := spiffePattern.FindStringSubmatch(raw)
	if matches == nil {
		return ClientID{}, fmt.Errorf(
			"invalid SPIFFE URI %q: must match spiffe://swe-ai-fleet/user/{userId}/device/{deviceId}",
			raw,
		)
	}

	return ClientID{
		raw:      raw,
		userID:   matches[1],
		deviceID: matches[2],
	}, nil
}

// String returns the full SPIFFE URI.
func (c ClientID) String() string {
	return c.raw
}

// UserID returns the user identifier extracted from the SPIFFE URI.
func (c ClientID) UserID() string {
	return c.userID
}

// DeviceID returns the device identifier extracted from the SPIFFE URI.
func (c ClientID) DeviceID() string {
	return c.deviceID
}

// IsZero reports whether the ClientID is the zero value.
func (c ClientID) IsZero() bool {
	return c.raw == ""
}
