// Package grpcapi provides the gRPC server adapter for the fleet-proxy.
// It configures mTLS, registers interceptors, and manages the server lifecycle.
package grpcapi

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net"
	"os"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi/interceptors"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
)

// Config holds the configuration for the gRPC server.
type Config struct {
	// Port is the TCP port to listen on.
	Port int

	// TLSCertPath is the path to the server's TLS certificate PEM file.
	TLSCertPath string

	// TLSKeyPath is the path to the server's TLS private key PEM file.
	TLSKeyPath string

	// ClientCACertPath is the path to the CA certificate PEM file used to
	// verify client certificates during mTLS.
	ClientCACertPath string

	// RateLimitRPS is the maximum requests per second per identity.
	// Set to 0 to disable rate limiting.
	RateLimitRPS int
}

// Server wraps the gRPC server with lifecycle management.
type Server struct {
	grpcServer *grpc.Server
	listener   net.Listener
	port       int
}

// NewServer creates a gRPC server with mTLS credentials and all interceptors
// wired. The server is not started until Start() is called.
func NewServer(
	cfg Config,
	policy auth.AuthorizationPolicy,
	resolver ports.IdentityResolver,
	audit ports.AuditLogger,
) (*Server, error) {
	tlsCfg, err := buildTLSConfig(cfg)
	if err != nil {
		return nil, err
	}

	// Build the interceptor chain.
	unaryInterceptors := []grpc.UnaryServerInterceptor{
		interceptors.AuthUnaryInterceptor(),
		interceptors.AuthzUnaryInterceptor(policy, resolver),
		interceptors.AuditUnaryInterceptor(audit),
	}
	if cfg.RateLimitRPS > 0 {
		unaryInterceptors = append(unaryInterceptors, interceptors.RateLimitUnaryInterceptor(cfg.RateLimitRPS))
	}

	streamInterceptors := []grpc.StreamServerInterceptor{
		interceptors.AuthStreamInterceptor(),
	}

	opts := []grpc.ServerOption{
		grpc.Creds(credentials.NewTLS(tlsCfg)),
		grpc.ChainUnaryInterceptor(unaryInterceptors...),
		grpc.ChainStreamInterceptor(streamInterceptors...),
	}

	gs := grpc.NewServer(opts...)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.Port))
	if err != nil {
		return nil, fmt.Errorf("grpcapi: listen on port %d: %w", cfg.Port, err)
	}

	return &Server{
		grpcServer: gs,
		listener:   lis,
		port:       cfg.Port,
	}, nil
}

// NewInsecureServer creates a gRPC server without TLS. This is intended for
// development and testing only.
func NewInsecureServer(
	port int,
	policy auth.AuthorizationPolicy,
	resolver ports.IdentityResolver,
	audit ports.AuditLogger,
) (*Server, error) {
	unaryInterceptors := []grpc.UnaryServerInterceptor{
		interceptors.AuditUnaryInterceptor(audit),
	}

	opts := []grpc.ServerOption{
		grpc.ChainUnaryInterceptor(unaryInterceptors...),
	}

	gs := grpc.NewServer(opts...)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return nil, fmt.Errorf("grpcapi: listen on port %d: %w", port, err)
	}

	return &Server{
		grpcServer: gs,
		listener:   lis,
		port:       port,
	}, nil
}

// GRPCServer returns the underlying grpc.Server for service registration.
// This is used by main.go to register generated proto service servers.
func (s *Server) GRPCServer() *grpc.Server {
	return s.grpcServer
}

// Start begins serving gRPC requests. It blocks until Stop() is called or
// an error occurs.
func (s *Server) Start() error {
	return s.grpcServer.Serve(s.listener)
}

// Stop gracefully stops the gRPC server, allowing in-flight RPCs to complete.
func (s *Server) Stop() {
	s.grpcServer.GracefulStop()
}

// Port returns the port the server is listening on.
func (s *Server) Port() int {
	return s.port
}

// buildTLSConfig constructs the TLS configuration for mTLS.
func buildTLSConfig(cfg Config) (*tls.Config, error) {
	cert, err := tls.LoadX509KeyPair(cfg.TLSCertPath, cfg.TLSKeyPath)
	if err != nil {
		return nil, fmt.Errorf("grpcapi: load server cert/key: %w", err)
	}

	caCertPEM, err := os.ReadFile(cfg.ClientCACertPath)
	if err != nil {
		return nil, fmt.Errorf("grpcapi: read client CA cert: %w", err)
	}

	caPool := x509.NewCertPool()
	if !caPool.AppendCertsFromPEM(caCertPEM) {
		return nil, fmt.Errorf("grpcapi: failed to parse client CA certificate")
	}

	return &tls.Config{
		Certificates: []tls.Certificate{cert},
		// VerifyClientCertIfGiven allows TLS-only connections (no client cert)
		// for the Enrollment RPC, while still verifying certs when presented
		// for mTLS-protected Command/Query services.
		ClientAuth: tls.VerifyClientCertIfGiven,
		ClientCAs:  caPool,
		MinVersion: tls.VersionTLS13,
	}, nil
}
