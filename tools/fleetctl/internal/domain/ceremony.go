package domain

// CeremonyStatus is a read-model representing the current state of a
// ceremony instance as returned by the fleet control plane.
type CeremonyStatus struct {
	InstanceID     string
	CeremonyID     string
	StoryID        string
	DefinitionName string
	CurrentState   string
	Status         string
	CorrelationID  string
	StepStatuses   map[string]string
	StepOutputs    map[string]string
	CreatedAt      string
	UpdatedAt      string
}
