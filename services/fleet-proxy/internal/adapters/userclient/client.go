// Package userclient provides an adapter implementing ports.UserClient
// over gRPC, targeting the internal fleet.user.v1.UserService.
package userclient

import (
	"context"
	"fmt"
	"log/slog"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/userv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// Client is the user-service gRPC adapter.
type Client struct {
	conn *grpc.ClientConn
	rpc  pb.UserServiceClient
}

// NewClient dials the user-service and returns a ready Client.
// Uses insecure transport (internal cluster mesh).
func NewClient(addr string) (*Client, error) {
	conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("dial user-service %s: %w", addr, err)
	}
	slog.Info("user client connected", "addr", addr)
	return &Client{conn: conn, rpc: pb.NewUserServiceClient(conn)}, nil
}

// Close releases the underlying gRPC connection.
func (c *Client) Close() error {
	return c.conn.Close()
}

func (c *Client) CreateUser(ctx context.Context, clientID, deviceID, displayName, email, role string) (ports.UserResult, error) {
	resp, err := c.rpc.CreateUser(ctx, &pb.CreateUserRequest{
		ClientId:    clientID,
		DeviceId:    deviceID,
		DisplayName: displayName,
		Email:       email,
		Role:        role,
	})
	if err != nil {
		return ports.UserResult{}, fmt.Errorf("CreateUser RPC: %w", err)
	}
	return protoToResult(resp.GetUser()), nil
}

func (c *Client) GetUserByClientID(ctx context.Context, clientID string) (ports.UserResult, error) {
	resp, err := c.rpc.GetUserByClientID(ctx, &pb.GetUserByClientIDRequest{
		ClientId: clientID,
	})
	if err != nil {
		return ports.UserResult{}, fmt.Errorf("GetUserByClientID RPC: %w", err)
	}
	return protoToResult(resp.GetUser()), nil
}

func protoToResult(u *pb.User) ports.UserResult {
	if u == nil {
		return ports.UserResult{}
	}
	return ports.UserResult{
		UserID:      u.GetUserId(),
		ClientID:    u.GetClientId(),
		DeviceID:    u.GetDeviceId(),
		DisplayName: u.GetDisplayName(),
		Email:       u.GetEmail(),
		Role:        u.GetRole(),
	}
}
