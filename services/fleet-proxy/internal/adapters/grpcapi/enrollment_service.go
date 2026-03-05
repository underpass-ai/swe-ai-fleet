package grpcapi

import (
	"context"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi/interceptors"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/command"
)

// EnrollmentService handles the enrollment and certificate renewal gRPC RPCs.
type EnrollmentService struct {
	proxyv1.UnimplementedEnrollmentServiceServer

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

// Enroll handles the Enroll RPC. It exchanges an API key for a client certificate.
func (s *EnrollmentService) Enroll(ctx context.Context, req *proxyv1.EnrollRequest) (*proxyv1.EnrollResponse, error) {
	apiKeyID, apiKeySecret := parseAPIKey(req.GetApiKey())

	result, err := s.enroll.Handle(ctx, command.EnrollCmd{
		APIKeyID:      apiKeyID,
		APIKeySecret:  apiKeySecret,
		CSRPEM:        req.GetCsrPem(),
		DeviceID:      req.GetDeviceId(),
		ClientVersion: req.GetClientVersion(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Unauthenticated, "enrollment failed: %v", err)
	}

	return &proxyv1.EnrollResponse{
		ClientCertPem: result.ClientCertPEM,
		CaChainPem:    result.CAChainPEM,
		ExpiresAt:     result.ExpiresAt,
		ClientId:      result.ClientID,
	}, nil
}

// Renew handles the Renew RPC. The caller's identity is extracted from the mTLS context.
func (s *EnrollmentService) Renew(ctx context.Context, req *proxyv1.RenewRequest) (*proxyv1.RenewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	if clientID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "renewal requires mTLS authentication")
	}

	result, err := s.renew.Handle(ctx, command.RenewCmd{
		CSRPEM:   req.GetCsrPem(),
		ClientID: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "certificate renewal failed: %v", err)
	}

	return &proxyv1.RenewResponse{
		ClientCertPem: result.ClientCertPEM,
		CaChainPem:    result.CAChainPEM,
		ExpiresAt:     result.ExpiresAt,
	}, nil
}

// parseAPIKey splits an API key string into ID and secret.
func parseAPIKey(apiKey string) (string, string) {
	for i, c := range apiKey {
		if c == ':' {
			return apiKey[:i], apiKey[i+1:]
		}
	}
	return apiKey, apiKey
}
