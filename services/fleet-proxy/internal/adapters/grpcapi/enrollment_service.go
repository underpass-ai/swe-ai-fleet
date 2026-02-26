package grpcapi

import (
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi/interceptors"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/command"
)

// ---------------------------------------------------------------------------
// Request / Response types matching fleet.proxy.v1.EnrollmentService proto.
// ---------------------------------------------------------------------------

// EnrollRequest mirrors fleet.proxy.v1.EnrollRequest.
type EnrollRequest struct {
	APIKey        string `protobuf:"bytes,1,opt,name=api_key,json=apiKey" json:"api_key,omitempty"`
	CSRPEM        []byte `protobuf:"bytes,2,opt,name=csr_pem,json=csrPem" json:"csr_pem,omitempty"`
	DeviceID      string `protobuf:"bytes,3,opt,name=device_id,json=deviceId" json:"device_id,omitempty"`
	ClientVersion string `protobuf:"bytes,4,opt,name=client_version,json=clientVersion" json:"client_version,omitempty"`
}

func (m *EnrollRequest) Reset()         { *m = EnrollRequest{} }
func (m *EnrollRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *EnrollRequest) ProtoMessage()  {}

// EnrollResponse mirrors fleet.proxy.v1.EnrollResponse.
type EnrollResponse struct {
	ClientCertPEM []byte `protobuf:"bytes,1,opt,name=client_cert_pem,json=clientCertPem" json:"client_cert_pem,omitempty"`
	CAChainPEM    []byte `protobuf:"bytes,2,opt,name=ca_chain_pem,json=caChainPem" json:"ca_chain_pem,omitempty"`
	ExpiresAt     string `protobuf:"bytes,3,opt,name=expires_at,json=expiresAt" json:"expires_at,omitempty"`
	ClientID      string `protobuf:"bytes,4,opt,name=client_id,json=clientId" json:"client_id,omitempty"`
}

func (m *EnrollResponse) Reset()         { *m = EnrollResponse{} }
func (m *EnrollResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *EnrollResponse) ProtoMessage()  {}

// RenewRequest mirrors fleet.proxy.v1.RenewRequest.
type RenewRequest struct {
	CSRPEM []byte `protobuf:"bytes,1,opt,name=csr_pem,json=csrPem" json:"csr_pem,omitempty"`
}

func (m *RenewRequest) Reset()         { *m = RenewRequest{} }
func (m *RenewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RenewRequest) ProtoMessage()  {}

// RenewResponse mirrors fleet.proxy.v1.RenewResponse.
type RenewResponse struct {
	ClientCertPEM []byte `protobuf:"bytes,1,opt,name=client_cert_pem,json=clientCertPem" json:"client_cert_pem,omitempty"`
	CAChainPEM    []byte `protobuf:"bytes,2,opt,name=ca_chain_pem,json=caChainPem" json:"ca_chain_pem,omitempty"`
	ExpiresAt     string `protobuf:"bytes,3,opt,name=expires_at,json=expiresAt" json:"expires_at,omitempty"`
}

func (m *RenewResponse) Reset()         { *m = RenewResponse{} }
func (m *RenewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RenewResponse) ProtoMessage()  {}

// ---------------------------------------------------------------------------
// EnrollmentService implementation
// ---------------------------------------------------------------------------

// EnrollmentService handles the enrollment and certificate renewal gRPC RPCs.
// Enrollment uses TLS only (no client cert required), while renewal requires
// an existing mTLS identity.
type EnrollmentService struct {
	enroll *command.EnrollHandler
	renew  *command.RenewHandler
}

// NewEnrollmentService creates an EnrollmentService wired to the enrollment
// and renewal command handlers.
func NewEnrollmentService(
	enroll *command.EnrollHandler,
	renew *command.RenewHandler,
) *EnrollmentService {
	return &EnrollmentService{
		enroll: enroll,
		renew:  renew,
	}
}

// HandleEnroll handles the Enroll RPC. It exchanges an API key for a client
// certificate. The API key is sent as a single string in the format
// "keyID:secret" or just as the key value (the handler parses it).
func (s *EnrollmentService) HandleEnroll(ctx context.Context, req *EnrollRequest) (*EnrollResponse, error) {
	// The proto EnrollRequest has a single api_key field. The EnrollCmd
	// expects separate APIKeyID and APIKeySecret. We parse the api_key
	// as "keyID:secret" for structured credentials, or use it as both
	// ID and secret for simple key-based auth.
	apiKeyID, apiKeySecret := parseAPIKey(req.APIKey)

	result, err := s.enroll.Handle(ctx, command.EnrollCmd{
		APIKeyID:      apiKeyID,
		APIKeySecret:  apiKeySecret,
		CSRPEM:        req.CSRPEM,
		DeviceID:      req.DeviceID,
		ClientVersion: req.ClientVersion,
	})
	if err != nil {
		return nil, status.Errorf(codes.Unauthenticated, "enrollment failed: %v", err)
	}

	return &EnrollResponse{
		ClientCertPEM: result.ClientCertPEM,
		CAChainPEM:    result.CAChainPEM,
		ExpiresAt:     result.ExpiresAt,
		ClientID:      result.ClientID,
	}, nil
}

// HandleRenew handles the Renew RPC. The caller's identity is extracted from
// the mTLS context (they must already have a valid client certificate).
func (s *EnrollmentService) HandleRenew(ctx context.Context, req *RenewRequest) (*RenewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	if clientID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "renewal requires mTLS authentication")
	}

	result, err := s.renew.Handle(ctx, command.RenewCmd{
		CSRPEM:   req.CSRPEM,
		ClientID: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "certificate renewal failed: %v", err)
	}

	return &RenewResponse{
		ClientCertPEM: result.ClientCertPEM,
		CAChainPEM:    result.CAChainPEM,
		ExpiresAt:     result.ExpiresAt,
	}, nil
}

// parseAPIKey splits an API key string into ID and secret. It supports
// the format "keyID:secret". If no colon is present, the entire string
// is used as both the ID and secret (for backwards compatibility with
// simple key-based auth).
func parseAPIKey(apiKey string) (string, string) {
	for i, c := range apiKey {
		if c == ':' {
			return apiKey[:i], apiKey[i+1:]
		}
	}
	return apiKey, apiKey
}

// ---------------------------------------------------------------------------
// gRPC service registration
// ---------------------------------------------------------------------------

// RegisterEnrollmentService registers the EnrollmentService with the gRPC
// server using a manually constructed ServiceDesc.
func RegisterEnrollmentService(gs *grpc.Server, svc *EnrollmentService) {
	gs.RegisterService(&enrollmentServiceDesc, svc)
}

// enrollmentServer is the interface required by gRPC's ServiceDesc.HandlerType.
type enrollmentServer interface{}

// enrollmentServiceDesc is the grpc.ServiceDesc for the EnrollmentService.
var enrollmentServiceDesc = grpc.ServiceDesc{
	ServiceName: "fleet.proxy.v1.EnrollmentService",
	HandlerType: (*enrollmentServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "Enroll", Handler: enrollHandler},
		{MethodName: "Renew", Handler: renewHandler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "fleet/proxy/v1/fleet_proxy.proto",
}

func enrollHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(EnrollRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*EnrollmentService).HandleEnroll(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.EnrollmentService/Enroll"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*EnrollmentService).HandleEnroll(ctx, r.(*EnrollRequest))
	})
}

func renewHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(RenewRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*EnrollmentService).HandleRenew(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.EnrollmentService/Renew"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*EnrollmentService).HandleRenew(ctx, r.(*RenewRequest))
	})
}
