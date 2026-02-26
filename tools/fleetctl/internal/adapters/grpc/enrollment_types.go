package grpc

import "fmt"

// ---------------------------------------------------------------------------
// Hand-crafted proto message types for fleet.proxy.v1.EnrollmentService.
// These match the wire format defined in specs/fleet/proxy/v1/fleet_proxy.proto
// and avoid a build-time proto-gen dependency for the CLI tool.
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
