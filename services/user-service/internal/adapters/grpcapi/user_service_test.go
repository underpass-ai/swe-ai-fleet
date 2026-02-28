package grpcapi

import (
	"context"
	"net"
	"testing"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"

	pb "github.com/underpass-ai/swe-ai-fleet/services/user-service/gen/userv1"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// fakeUserStore is a minimal in-memory store for gRPC integration tests.
type fakeUserStore struct {
	users     map[string]domain.User
	clientIdx map[string]string
}

func newFakeStore() *fakeUserStore {
	return &fakeUserStore{
		users:     make(map[string]domain.User),
		clientIdx: make(map[string]string),
	}
}

func (f *fakeUserStore) Create(_ context.Context, user domain.User) error {
	if _, ok := f.clientIdx[user.ClientID]; ok {
		return domain.ErrDuplicateClientID
	}
	f.users[user.UserID] = user
	f.clientIdx[user.ClientID] = user.UserID
	return nil
}

func (f *fakeUserStore) GetByID(_ context.Context, userID string) (domain.User, error) {
	u, ok := f.users[userID]
	if !ok {
		return domain.User{}, domain.ErrNotFound
	}
	return u, nil
}

func (f *fakeUserStore) GetByClientID(_ context.Context, clientID string) (domain.User, error) {
	uid, ok := f.clientIdx[clientID]
	if !ok {
		return domain.User{}, domain.ErrNotFound
	}
	return f.users[uid], nil
}

func (f *fakeUserStore) Update(_ context.Context, user domain.User) error {
	if _, ok := f.users[user.UserID]; !ok {
		return domain.ErrNotFound
	}
	f.users[user.UserID] = user
	return nil
}

func (f *fakeUserStore) List(_ context.Context, roleFilter string, limit, offset int32) ([]domain.User, int32, error) {
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

func startTestServer(t *testing.T) pb.UserServiceClient {
	t.Helper()

	store := newFakeStore()
	svc := NewUserServiceServer(
		command.NewCreateUserHandler(store),
		command.NewUpdateUserHandler(store),
		query.NewGetUserHandler(store),
		query.NewGetUserByClientIDHandler(store),
		query.NewListUsersHandler(store),
	)

	srv := grpc.NewServer()
	RegisterUserService(srv, svc)

	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}

	go func() { _ = srv.Serve(lis) }()
	t.Cleanup(func() { srv.Stop() })

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, lis.Addr().String(),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	t.Cleanup(func() { conn.Close() })

	return pb.NewUserServiceClient(conn)
}

func TestUserService_CreateAndGet(t *testing.T) {
	client := startTestServer(t)
	ctx := context.Background()

	// Create user.
	createResp, err := client.CreateUser(ctx, &pb.CreateUserRequest{
		ClientId:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceId:    "macbook",
		DisplayName: "Tirso",
		Email:       "tirso@example.com",
		Role:        "operator",
	})
	if err != nil {
		t.Fatalf("CreateUser: %v", err)
	}
	if !createResp.GetCreated() {
		t.Error("expected created=true")
	}
	userID := createResp.GetUser().GetUserId()
	if userID == "" {
		t.Fatal("user_id is empty")
	}

	// Get by ID.
	getResp, err := client.GetUser(ctx, &pb.GetUserRequest{UserId: userID})
	if err != nil {
		t.Fatalf("GetUser: %v", err)
	}
	if getResp.GetUser().GetDisplayName() != "Tirso" {
		t.Errorf("DisplayName = %q", getResp.GetUser().GetDisplayName())
	}

	// Get by ClientID.
	getByClientResp, err := client.GetUserByClientID(ctx, &pb.GetUserByClientIDRequest{
		ClientId: "spiffe://swe-ai-fleet/user/tirso/device/macbook",
	})
	if err != nil {
		t.Fatalf("GetUserByClientID: %v", err)
	}
	if getByClientResp.GetUser().GetUserId() != userID {
		t.Errorf("UserID = %q, want %q", getByClientResp.GetUser().GetUserId(), userID)
	}
}

func TestUserService_CreateIdempotent(t *testing.T) {
	client := startTestServer(t)
	ctx := context.Background()

	req := &pb.CreateUserRequest{
		ClientId:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceId:    "macbook",
		DisplayName: "Tirso",
		Role:        "operator",
	}

	resp1, err := client.CreateUser(ctx, req)
	if err != nil {
		t.Fatalf("first CreateUser: %v", err)
	}
	if !resp1.GetCreated() {
		t.Error("first call should return created=true")
	}

	resp2, err := client.CreateUser(ctx, req)
	if err != nil {
		t.Fatalf("second CreateUser: %v", err)
	}
	if resp2.GetCreated() {
		t.Error("second call should return created=false")
	}
	if resp2.GetUser().GetUserId() != resp1.GetUser().GetUserId() {
		t.Error("should return same user_id")
	}
}

func TestUserService_GetNotFound(t *testing.T) {
	client := startTestServer(t)

	_, err := client.GetUser(context.Background(), &pb.GetUserRequest{UserId: "nonexistent"})
	if err == nil {
		t.Fatal("expected error")
	}
	if s, ok := status.FromError(err); ok {
		if s.Code() != codes.NotFound {
			t.Errorf("code = %v, want NotFound", s.Code())
		}
	}
}

func TestUserService_UpdateUser(t *testing.T) {
	client := startTestServer(t)
	ctx := context.Background()

	// Create first.
	createResp, err := client.CreateUser(ctx, &pb.CreateUserRequest{
		ClientId:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceId:    "macbook",
		DisplayName: "Tirso",
		Role:        "operator",
	})
	if err != nil {
		t.Fatalf("CreateUser: %v", err)
	}

	// Update.
	updateResp, err := client.UpdateUser(ctx, &pb.UpdateUserRequest{
		UserId:      createResp.GetUser().GetUserId(),
		DisplayName: "Tirso Updated",
		Email:       "new@example.com",
	})
	if err != nil {
		t.Fatalf("UpdateUser: %v", err)
	}
	if updateResp.GetUser().GetDisplayName() != "Tirso Updated" {
		t.Errorf("DisplayName = %q", updateResp.GetUser().GetDisplayName())
	}
}

func TestUserService_ListUsers(t *testing.T) {
	client := startTestServer(t)
	ctx := context.Background()

	// Create two users.
	for _, name := range []string{"Alice", "Bob"} {
		_, err := client.CreateUser(ctx, &pb.CreateUserRequest{
			ClientId:    "spiffe://swe-ai-fleet/user/" + name,
			DeviceId:    "dev-" + name,
			DisplayName: name,
			Role:        "operator",
		})
		if err != nil {
			t.Fatalf("CreateUser %s: %v", name, err)
		}
	}

	resp, err := client.ListUsers(ctx, &pb.ListUsersRequest{Limit: 100})
	if err != nil {
		t.Fatalf("ListUsers: %v", err)
	}
	if resp.GetTotalCount() != 2 {
		t.Errorf("total = %d, want 2", resp.GetTotalCount())
	}
	if len(resp.GetUsers()) != 2 {
		t.Errorf("len(users) = %d, want 2", len(resp.GetUsers()))
	}
}
