package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

var errNotFound = errors.New("not found")

// fakeUserReader is a hand-written in-memory fake implementing ports.UserReader
// for testing query handlers.
type fakeUserReader struct {
	users     map[string]domain.User // keyed by user_id
	clientIdx map[string]string      // client_id → user_id
}

func newFakeUserReader() *fakeUserReader {
	return &fakeUserReader{
		users:     make(map[string]domain.User),
		clientIdx: make(map[string]string),
	}
}

// seed adds a user to the fake reader.
func (f *fakeUserReader) seed(user domain.User) {
	f.users[user.UserID] = user
	f.clientIdx[user.ClientID] = user.UserID
}

func (f *fakeUserReader) GetByID(_ context.Context, userID string) (domain.User, error) {
	u, ok := f.users[userID]
	if !ok {
		return domain.User{}, errNotFound
	}
	return u, nil
}

func (f *fakeUserReader) GetByClientID(_ context.Context, clientID string) (domain.User, error) {
	uid, ok := f.clientIdx[clientID]
	if !ok {
		return domain.User{}, errNotFound
	}
	return f.users[uid], nil
}

func (f *fakeUserReader) List(_ context.Context, roleFilter string, limit, offset int32) ([]domain.User, int32, error) {
	var result []domain.User
	for _, u := range f.users {
		if roleFilter != "" && u.Role != roleFilter {
			continue
		}
		result = append(result, u)
	}
	total := int32(len(result))
	if offset >= total {
		return nil, total, nil
	}
	end := offset + limit
	if end > total {
		end = total
	}
	return result[offset:end], total, nil
}
