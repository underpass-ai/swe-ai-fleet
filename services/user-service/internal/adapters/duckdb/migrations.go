// Package duckdb provides the DuckDB-backed UserStore adapter.
package duckdb

import "database/sql"

// EnsureSchema creates the users table and indexes if they don't exist.
func EnsureSchema(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS users (
			user_id      VARCHAR PRIMARY KEY,
			client_id    VARCHAR NOT NULL UNIQUE,
			device_id    VARCHAR NOT NULL,
			display_name VARCHAR NOT NULL,
			email        VARCHAR DEFAULT '',
			role         VARCHAR NOT NULL DEFAULT 'operator',
			created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
		CREATE INDEX IF NOT EXISTS idx_users_client_id ON users(client_id);
	`)
	return err
}
