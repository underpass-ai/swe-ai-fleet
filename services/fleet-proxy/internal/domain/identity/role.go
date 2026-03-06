package identity

import (
	"errors"
	"fmt"
)

// Role is a value object representing a client role in the fleet.
// It is stored as a uint8 for compact representation.
type Role uint8

const (
	// RoleViewer can read data and watch streams.
	RoleViewer Role = 1
	// RoleOperator can execute commands and queries.
	RoleOperator Role = 2
	// RoleAdmin has full access to all operations.
	RoleAdmin Role = 3
)

// roleNames maps each valid Role to its string representation.
var roleNames = map[Role]string{
	RoleViewer:   "viewer",
	RoleOperator: "operator",
	RoleAdmin:    "admin",
}

// roleValues maps lowercase role names to Role values.
var roleValues = map[string]Role{
	"viewer":   RoleViewer,
	"operator": RoleOperator,
	"admin":    RoleAdmin,
}

// String returns the lowercase name of the role.
// It returns "unknown" for invalid role values.
func (r Role) String() string {
	if name, ok := roleNames[r]; ok {
		return name
	}
	return "unknown"
}

// IsValid reports whether the role is one of the defined constants.
func (r Role) IsValid() bool {
	_, ok := roleNames[r]
	return ok
}

// ParseRole converts a case-sensitive string ("viewer", "operator", "admin")
// into its corresponding Role value.
func ParseRole(s string) (Role, error) {
	if s == "" {
		return 0, errors.New("role cannot be empty")
	}

	r, ok := roleValues[s]
	if !ok {
		return 0, fmt.Errorf("unknown role %q: valid roles are viewer, operator, admin", s)
	}

	return r, nil
}
