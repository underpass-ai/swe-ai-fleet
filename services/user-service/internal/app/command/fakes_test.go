package command

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// fakeUserWriter is a hand-written in-memory fake implementing ports.UserWriter
// for testing command handlers.
type fakeUserWriter struct {
	users      map[string]domain.User // keyed by user_id
	clientIdx  map[string]string      // client_id → user_id
	createErr  error
	getByIDErr error
	updateErr  error
}

func newFakeUserWriter() *fakeUserWriter {
	return &fakeUserWriter{
		users:     make(map[string]domain.User),
		clientIdx: make(map[string]string),
	}
}

func (f *fakeUserWriter) Create(_ context.Context, user domain.User) error {
	if f.createErr != nil {
		return f.createErr
	}
	if _, exists := f.clientIdx[user.ClientID]; exists {
		return domain.ErrDuplicateClientID
	}
	f.users[user.UserID] = user
	f.clientIdx[user.ClientID] = user.UserID
	return nil
}

func (f *fakeUserWriter) GetByID(_ context.Context, userID string) (domain.User, error) {
	if f.getByIDErr != nil {
		return domain.User{}, f.getByIDErr
	}
	u, ok := f.users[userID]
	if !ok {
		return domain.User{}, domain.ErrNotFound
	}
	return u, nil
}

func (f *fakeUserWriter) GetByClientID(_ context.Context, clientID string) (domain.User, error) {
	uid, ok := f.clientIdx[clientID]
	if !ok {
		return domain.User{}, domain.ErrNotFound
	}
	return f.users[uid], nil
}

func (f *fakeUserWriter) Update(_ context.Context, user domain.User) error {
	if f.updateErr != nil {
		return f.updateErr
	}
	if _, ok := f.users[user.UserID]; !ok {
		return domain.ErrNotFound
	}
	f.users[user.UserID] = user
	return nil
}
