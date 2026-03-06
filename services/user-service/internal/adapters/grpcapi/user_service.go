package grpcapi

import (
	"context"
	"errors"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "github.com/underpass-ai/swe-ai-fleet/services/user-service/gen/userv1"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// UserServiceServer implements the fleet.user.v1.UserService gRPC interface.
type UserServiceServer struct {
	pb.UnimplementedUserServiceServer
	createUser         *command.CreateUserHandler
	updateUser         *command.UpdateUserHandler
	getUser            *query.GetUserHandler
	getUserByClientID  *query.GetUserByClientIDHandler
	listUsers          *query.ListUsersHandler
}

// NewUserServiceServer wires the gRPC handler to application-layer handlers.
func NewUserServiceServer(
	createUser *command.CreateUserHandler,
	updateUser *command.UpdateUserHandler,
	getUser *query.GetUserHandler,
	getUserByClientID *query.GetUserByClientIDHandler,
	listUsers *query.ListUsersHandler,
) *UserServiceServer {
	return &UserServiceServer{
		createUser:        createUser,
		updateUser:        updateUser,
		getUser:           getUser,
		getUserByClientID: getUserByClientID,
		listUsers:         listUsers,
	}
}

// RegisterUserService registers the UserService on a gRPC server.
func RegisterUserService(srv *grpc.Server, svc *UserServiceServer) {
	pb.RegisterUserServiceServer(srv, svc)
}

func (s *UserServiceServer) CreateUser(ctx context.Context, req *pb.CreateUserRequest) (*pb.CreateUserResponse, error) {
	result, err := s.createUser.Handle(ctx, command.CreateUserCmd{
		ClientID:    req.GetClientId(),
		DeviceID:    req.GetDeviceId(),
		DisplayName: req.GetDisplayName(),
		Email:       req.GetEmail(),
		Role:        req.GetRole(),
	})
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "%v", err)
	}

	return &pb.CreateUserResponse{
		User:    domainToProto(result.User),
		Created: result.Created,
	}, nil
}

func (s *UserServiceServer) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
	user, err := s.getUser.Handle(ctx, req.GetUserId())
	if err != nil {
		return nil, toGRPCError(err)
	}
	return &pb.GetUserResponse{User: domainToProto(user)}, nil
}

func (s *UserServiceServer) GetUserByClientID(ctx context.Context, req *pb.GetUserByClientIDRequest) (*pb.GetUserByClientIDResponse, error) {
	user, err := s.getUserByClientID.Handle(ctx, req.GetClientId())
	if err != nil {
		return nil, toGRPCError(err)
	}
	return &pb.GetUserByClientIDResponse{User: domainToProto(user)}, nil
}

func (s *UserServiceServer) UpdateUser(ctx context.Context, req *pb.UpdateUserRequest) (*pb.UpdateUserResponse, error) {
	user, err := s.updateUser.Handle(ctx, command.UpdateUserCmd{
		UserID:      req.GetUserId(),
		DisplayName: req.GetDisplayName(),
		Email:       req.GetEmail(),
		Role:        req.GetRole(),
	})
	if err != nil {
		return nil, toGRPCError(err)
	}
	return &pb.UpdateUserResponse{User: domainToProto(user)}, nil
}

func (s *UserServiceServer) ListUsers(ctx context.Context, req *pb.ListUsersRequest) (*pb.ListUsersResponse, error) {
	users, total, err := s.listUsers.Handle(ctx, req.GetRoleFilter(), req.GetLimit(), req.GetOffset())
	if err != nil {
		return nil, status.Errorf(codes.Internal, "%v", err)
	}

	pbUsers := make([]*pb.User, len(users))
	for i, u := range users {
		pbUsers[i] = domainToProto(u)
	}
	return &pb.ListUsersResponse{Users: pbUsers, TotalCount: total}, nil
}

func domainToProto(u domain.User) *pb.User {
	return &pb.User{
		UserId:      u.UserID,
		ClientId:    u.ClientID,
		DeviceId:    u.DeviceID,
		DisplayName: u.DisplayName,
		Email:       u.Email,
		Role:        u.Role,
		CreatedAt:   u.CreatedAt.Format("2006-01-02T15:04:05Z07:00"),
		UpdatedAt:   u.UpdatedAt.Format("2006-01-02T15:04:05Z07:00"),
	}
}

func toGRPCError(err error) error {
	if errors.Is(err, domain.ErrNotFound) {
		return status.Errorf(codes.NotFound, "%v", err)
	}
	return status.Errorf(codes.Internal, "%v", err)
}
