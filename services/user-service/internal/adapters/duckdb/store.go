package duckdb

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// Store implements ports.UserWriter and ports.UserReader backed by DuckDB.
type Store struct {
	db *sql.DB
}

// NewStore creates a new DuckDB-backed UserStore.
func NewStore(db *sql.DB) *Store {
	return &Store{db: db}
}

func (s *Store) Create(ctx context.Context, user domain.User) error {
	_, err := s.db.ExecContext(ctx,
		`INSERT INTO users (user_id, client_id, device_id, display_name, email, role, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		user.UserID, user.ClientID, user.DeviceID, user.DisplayName, user.Email, user.Role, user.CreatedAt, user.UpdatedAt,
	)
	if err != nil {
		if isDuplicateErr(err) {
			return domain.ErrDuplicateClientID
		}
		return fmt.Errorf("insert user: %w", err)
	}
	return nil
}

func (s *Store) GetByID(ctx context.Context, userID string) (domain.User, error) {
	return s.scanUser(s.db.QueryRowContext(ctx,
		`SELECT user_id, client_id, device_id, display_name, email, role, created_at, updated_at
		 FROM users WHERE user_id = ?`, userID))
}

func (s *Store) GetByClientID(ctx context.Context, clientID string) (domain.User, error) {
	return s.scanUser(s.db.QueryRowContext(ctx,
		`SELECT user_id, client_id, device_id, display_name, email, role, created_at, updated_at
		 FROM users WHERE client_id = ?`, clientID))
}

func (s *Store) Update(ctx context.Context, user domain.User) error {
	res, err := s.db.ExecContext(ctx,
		`UPDATE users SET display_name = ?, email = ?, role = ?, updated_at = ?
		 WHERE user_id = ?`,
		user.DisplayName, user.Email, user.Role, user.UpdatedAt, user.UserID,
	)
	if err != nil {
		return fmt.Errorf("update user: %w", err)
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (s *Store) List(ctx context.Context, roleFilter string, limit, offset int32) ([]domain.User, int32, error) {
	// Build count query.
	countQuery := "SELECT COUNT(*) FROM users"
	var countArgs []any
	if roleFilter != "" {
		countQuery += " WHERE role = ?"
		countArgs = append(countArgs, roleFilter)
	}

	var total int32
	if err := s.db.QueryRowContext(ctx, countQuery, countArgs...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("count users: %w", err)
	}

	// Build list query.
	listQuery := `SELECT user_id, client_id, device_id, display_name, email, role, created_at, updated_at FROM users`
	var listArgs []any
	if roleFilter != "" {
		listQuery += " WHERE role = ?"
		listArgs = append(listArgs, roleFilter)
	}
	listQuery += " ORDER BY created_at ASC LIMIT ? OFFSET ?"
	listArgs = append(listArgs, limit, offset)

	rows, err := s.db.QueryContext(ctx, listQuery, listArgs...)
	if err != nil {
		return nil, 0, fmt.Errorf("list users: %w", err)
	}
	defer rows.Close()

	var users []domain.User
	for rows.Next() {
		var u domain.User
		var createdAt, updatedAt time.Time
		if err := rows.Scan(&u.UserID, &u.ClientID, &u.DeviceID, &u.DisplayName, &u.Email, &u.Role, &createdAt, &updatedAt); err != nil {
			return nil, 0, fmt.Errorf("scan user: %w", err)
		}
		u.CreatedAt = createdAt
		u.UpdatedAt = updatedAt
		users = append(users, u)
	}
	return users, total, rows.Err()
}

func (s *Store) scanUser(row *sql.Row) (domain.User, error) {
	var u domain.User
	var createdAt, updatedAt time.Time
	if err := row.Scan(&u.UserID, &u.ClientID, &u.DeviceID, &u.DisplayName, &u.Email, &u.Role, &createdAt, &updatedAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.User{}, domain.ErrNotFound
		}
		return domain.User{}, fmt.Errorf("scan user: %w", err)
	}
	u.CreatedAt = createdAt
	u.UpdatedAt = updatedAt
	return u, nil
}

// isDuplicateErr checks if a DuckDB error is a unique constraint violation.
func isDuplicateErr(err error) bool {
	return strings.Contains(err.Error(), "Duplicate key") ||
		strings.Contains(err.Error(), "UNIQUE constraint") ||
		strings.Contains(err.Error(), "duplicate key")
}
