package auth

import (
	"errors"
	"fmt"
)

// Scope is a value object representing the authorization scope of an operation.
// Scopes are ordered by privilege level: watch < approve < start < manage.
type Scope uint8

const (
	// ScopeWatch allows reading data and subscribing to event streams.
	ScopeWatch Scope = 1
	// ScopeApprove allows approving or rejecting pending items.
	ScopeApprove Scope = 2
	// ScopeStart allows initiating ceremonies, sessions, and workflows.
	ScopeStart Scope = 3
	// ScopeManage allows full administrative operations.
	ScopeManage Scope = 4
)

// scopeNames maps each valid Scope to its string representation.
var scopeNames = map[Scope]string{
	ScopeWatch:   "watch",
	ScopeApprove: "approve",
	ScopeStart:   "start",
	ScopeManage:  "manage",
}

// scopeValues maps lowercase scope names to Scope values.
var scopeValues = map[string]Scope{
	"watch":   ScopeWatch,
	"approve": ScopeApprove,
	"start":   ScopeStart,
	"manage":  ScopeManage,
}

// String returns the lowercase name of the scope.
// It returns "unknown" for invalid scope values.
func (s Scope) String() string {
	if name, ok := scopeNames[s]; ok {
		return name
	}
	return "unknown"
}

// IsValid reports whether the scope is one of the defined constants.
func (s Scope) IsValid() bool {
	_, ok := scopeNames[s]
	return ok
}

// ParseScope converts a case-sensitive string ("watch", "approve", "start", "manage")
// into its corresponding Scope value.
func ParseScope(s string) (Scope, error) {
	if s == "" {
		return 0, errors.New("scope cannot be empty")
	}

	sc, ok := scopeValues[s]
	if !ok {
		return 0, fmt.Errorf("unknown scope %q: valid scopes are watch, approve, start, manage", s)
	}

	return sc, nil
}
