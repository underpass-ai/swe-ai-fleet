package store

import "testing"

func TestStatuses_AreStableStrings(t *testing.T) {
	if DeliberationStatusRunning != "running" {
		t.Fatalf("running changed")
	}
	if DeliberationStatusCompleted != "completed" {
		t.Fatalf("completed changed")
	}
	if DeliberationStatusFailed != "failed" {
		t.Fatalf("failed changed")
	}
}
