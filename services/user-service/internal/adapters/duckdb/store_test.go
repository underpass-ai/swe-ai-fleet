package duckdb

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"

	_ "github.com/marcboeker/go-duckdb"
)

func openTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("duckdb", "")
	if err != nil {
		t.Fatalf("open duckdb: %v", err)
	}
	if err := EnsureSchema(db); err != nil {
		t.Fatalf("ensure schema: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return db
}

func TestStore_CreateAndGetByID(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)
	ctx := context.Background()

	now := time.Now().UTC().Truncate(time.Microsecond)
	user := domain.User{
		UserID:      "user-1",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceID:    "macbook",
		DisplayName: "Tirso",
		Email:       "tirso@example.com",
		Role:        "operator",
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := store.Create(ctx, user); err != nil {
		t.Fatalf("Create: %v", err)
	}

	got, err := store.GetByID(ctx, "user-1")
	if err != nil {
		t.Fatalf("GetByID: %v", err)
	}
	if got.DisplayName != "Tirso" {
		t.Errorf("DisplayName = %q, want Tirso", got.DisplayName)
	}
	if got.Email != "tirso@example.com" {
		t.Errorf("Email = %q, want tirso@example.com", got.Email)
	}
}

func TestStore_CreateDuplicate(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)
	ctx := context.Background()

	now := time.Now().UTC().Truncate(time.Microsecond)
	user := domain.User{
		UserID:      "user-1",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceID:    "macbook",
		DisplayName: "Tirso",
		Role:        "operator",
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := store.Create(ctx, user); err != nil {
		t.Fatalf("first Create: %v", err)
	}

	user.UserID = "user-2" // different ID but same client_id
	err := store.Create(ctx, user)
	if !errors.Is(err, domain.ErrDuplicateClientID) {
		t.Fatalf("expected ErrDuplicateClientID, got %v", err)
	}
}

func TestStore_GetByClientID(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)
	ctx := context.Background()

	now := time.Now().UTC().Truncate(time.Microsecond)
	user := domain.User{
		UserID:      "user-1",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceID:    "macbook",
		DisplayName: "Tirso",
		Role:        "operator",
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := store.Create(ctx, user); err != nil {
		t.Fatalf("Create: %v", err)
	}

	got, err := store.GetByClientID(ctx, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	if err != nil {
		t.Fatalf("GetByClientID: %v", err)
	}
	if got.UserID != "user-1" {
		t.Errorf("UserID = %q, want user-1", got.UserID)
	}
}

func TestStore_GetByID_NotFound(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)

	_, err := store.GetByID(context.Background(), "nonexistent")
	if !errors.Is(err, domain.ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestStore_GetByClientID_NotFound(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)

	_, err := store.GetByClientID(context.Background(), "nonexistent")
	if !errors.Is(err, domain.ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestStore_Update(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)
	ctx := context.Background()

	now := time.Now().UTC().Truncate(time.Microsecond)
	user := domain.User{
		UserID:      "user-1",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceID:    "macbook",
		DisplayName: "Tirso",
		Email:       "old@example.com",
		Role:        "operator",
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := store.Create(ctx, user); err != nil {
		t.Fatalf("Create: %v", err)
	}

	user.DisplayName = "Tirso Updated"
	user.Email = "new@example.com"
	user.UpdatedAt = time.Now().UTC().Truncate(time.Microsecond)

	if err := store.Update(ctx, user); err != nil {
		t.Fatalf("Update: %v", err)
	}

	got, err := store.GetByID(ctx, "user-1")
	if err != nil {
		t.Fatalf("GetByID after update: %v", err)
	}
	if got.DisplayName != "Tirso Updated" {
		t.Errorf("DisplayName = %q, want Tirso Updated", got.DisplayName)
	}
	if got.Email != "new@example.com" {
		t.Errorf("Email = %q, want new@example.com", got.Email)
	}
}

func TestStore_Update_NotFound(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)

	err := store.Update(context.Background(), domain.User{UserID: "nonexistent", UpdatedAt: time.Now()})
	if !errors.Is(err, domain.ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestStore_List(t *testing.T) {
	db := openTestDB(t)
	store := NewStore(db)
	ctx := context.Background()

	now := time.Now().UTC().Truncate(time.Microsecond)
	users := []domain.User{
		{UserID: "u1", ClientID: "c1", DeviceID: "d1", DisplayName: "Alice", Role: "operator", CreatedAt: now, UpdatedAt: now},
		{UserID: "u2", ClientID: "c2", DeviceID: "d2", DisplayName: "Bob", Role: "admin", CreatedAt: now.Add(time.Second), UpdatedAt: now.Add(time.Second)},
		{UserID: "u3", ClientID: "c3", DeviceID: "d3", DisplayName: "Charlie", Role: "operator", CreatedAt: now.Add(2 * time.Second), UpdatedAt: now.Add(2 * time.Second)},
	}
	for _, u := range users {
		if err := store.Create(ctx, u); err != nil {
			t.Fatalf("seed Create: %v", err)
		}
	}

	// All users.
	result, total, err := store.List(ctx, "", 100, 0)
	if err != nil {
		t.Fatalf("List all: %v", err)
	}
	if total != 3 {
		t.Errorf("total = %d, want 3", total)
	}
	if len(result) != 3 {
		t.Errorf("len = %d, want 3", len(result))
	}

	// Filter by role.
	result, total, err = store.List(ctx, "operator", 100, 0)
	if err != nil {
		t.Fatalf("List operator: %v", err)
	}
	if total != 2 {
		t.Errorf("total = %d, want 2", total)
	}
	if len(result) != 2 {
		t.Errorf("len = %d, want 2", len(result))
	}

	// Pagination.
	result, total, err = store.List(ctx, "", 2, 0)
	if err != nil {
		t.Fatalf("List page 1: %v", err)
	}
	if total != 3 {
		t.Errorf("total = %d, want 3", total)
	}
	if len(result) != 2 {
		t.Errorf("len = %d, want 2", len(result))
	}

	// Page 2.
	result, _, err = store.List(ctx, "", 2, 2)
	if err != nil {
		t.Fatalf("List page 2: %v", err)
	}
	if len(result) != 1 {
		t.Errorf("len = %d, want 1", len(result))
	}
}
