// Package grpcapi provides the gRPC transport layer for the user-service.
package grpcapi

import (
	"fmt"
	"log/slog"
	"net"

	"google.golang.org/grpc"
)

// Server wraps a gRPC server with lifecycle management.
type Server struct {
	srv  *grpc.Server
	port int
}

// NewInsecureServer creates an insecure gRPC server (internal cluster use only).
func NewInsecureServer(port int) *Server {
	return &Server{
		srv:  grpc.NewServer(),
		port: port,
	}
}

// GRPCServer returns the underlying grpc.Server for service registration.
func (s *Server) GRPCServer() *grpc.Server {
	return s.srv
}

// Start begins listening and serving gRPC requests.
func (s *Server) Start() error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", s.port))
	if err != nil {
		return fmt.Errorf("listen on port %d: %w", s.port, err)
	}
	slog.Info("gRPC server listening", "port", s.port)
	return s.srv.Serve(lis)
}

// Stop gracefully stops the gRPC server.
func (s *Server) Stop() {
	s.srv.GracefulStop()
}
