package identity

import (
	"errors"
	"strings"
)

// ServerName is a value object that represents a validated TLS server name.
type ServerName struct {
	value string
}

// NewServerName creates a ServerName after validating that the input is
// non-empty and trimmed. It is used wherever a TLS server name override
// is required (e.g. connecting through kubectl port-forward).
func NewServerName(s string) (ServerName, error) {
	trimmed := strings.TrimSpace(s)
	if trimmed == "" {
		return ServerName{}, errors.New("server name must not be empty")
	}
	return ServerName{value: trimmed}, nil
}

// String returns the underlying server name string.
func (s ServerName) String() string {
	return s.value
}
