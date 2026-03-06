package grpc

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain/identity"
)

// Connection wraps a gRPC client connection and tracks the dial target.
type Connection struct {
	conn   *grpc.ClientConn
	target string
}

// Dial establishes a gRPC connection to target using full mTLS. The
// Credentials value provides the client certificate, CA chain, and
// server-name override required for the handshake.
func Dial(ctx context.Context, target string, creds identity.Credentials) (*Connection, error) {
	tlsCfg := creds.TLSConfig()
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(credentials.NewTLS(tlsCfg)),
	}
	conn, err := grpc.NewClient(target, opts...)
	if err != nil {
		return nil, fmt.Errorf("grpc dial %s: %w", target, err)
	}
	return &Connection{conn: conn, target: target}, nil
}

// DialInsecure establishes a gRPC connection using TLS (server-verified)
// but without a client certificate. This is used during enrollment when
// the device does not yet have an mTLS identity.
func DialInsecure(ctx context.Context, target string) (*Connection, error) {
	tlsCfg := &tls.Config{
		MinVersion: tls.VersionTLS13,
	}
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(credentials.NewTLS(tlsCfg)),
	}
	conn, err := grpc.NewClient(target, opts...)
	if err != nil {
		return nil, fmt.Errorf("grpc dial insecure %s: %w", target, err)
	}
	return &Connection{conn: conn, target: target}, nil
}

// DialEnrollment establishes a TLS-only gRPC connection for enrollment.
// It supports custom CA certificates (for self-signed PKI) and a server
// name override (needed when connecting through port-forward).
// If skipVerify is true, server certificate verification is skipped (dev only).
func DialEnrollment(ctx context.Context, target string, caCertPEM []byte, serverName string, skipVerify bool) (*Connection, error) {
	tlsCfg := &tls.Config{
		MinVersion:         tls.VersionTLS13,
		InsecureSkipVerify: skipVerify,
	}
	if serverName != "" && !skipVerify {
		tlsCfg.ServerName = serverName
	}
	if len(caCertPEM) > 0 {
		pool := x509.NewCertPool()
		if !pool.AppendCertsFromPEM(caCertPEM) {
			return nil, fmt.Errorf("failed to parse CA certificate")
		}
		tlsCfg.RootCAs = pool
	}
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(credentials.NewTLS(tlsCfg)),
	}
	conn, err := grpc.NewClient(target, opts...)
	if err != nil {
		return nil, fmt.Errorf("grpc dial enrollment %s: %w", target, err)
	}
	return &Connection{conn: conn, target: target}, nil
}

// Close releases the underlying gRPC transport.
func (c *Connection) Close() error {
	if c.conn == nil {
		return nil
	}
	return c.conn.Close()
}

// Conn returns the raw *grpc.ClientConn so that generated stubs can be
// attached to it.
func (c *Connection) Conn() *grpc.ClientConn {
	return c.conn
}
