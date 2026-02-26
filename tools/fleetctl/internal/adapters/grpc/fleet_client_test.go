package grpc

import (
	"context"
	"net"
	"strings"
	"testing"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

const testBufSize = 1 << 20

// fakeProjectServer provides configurable responses for project RPCs.
type fakeProjectServer struct {
	createResp *CreateProjectResponse
	createErr  error
	listResp   *ListProjectsResponse
	listErr    error
}

func (f *fakeProjectServer) commandServiceDesc() grpc.ServiceDesc {
	return grpc.ServiceDesc{
		ServiceName: "fleet.proxy.v1.FleetCommandService",
		HandlerType: (*any)(nil),
		Methods: []grpc.MethodDesc{
			{
				MethodName: "CreateProject",
				Handler: func(_ any, _ context.Context, dec func(any) error, _ grpc.UnaryServerInterceptor) (any, error) {
					req := new(CreateProjectRequest)
					if err := dec(req); err != nil {
						return nil, err
					}
					if f.createErr != nil {
						return nil, f.createErr
					}
					return f.createResp, nil
				},
			},
		},
		Streams: []grpc.StreamDesc{},
	}
}

func (f *fakeProjectServer) queryServiceDesc() grpc.ServiceDesc {
	return grpc.ServiceDesc{
		ServiceName: "fleet.proxy.v1.FleetQueryService",
		HandlerType: (*any)(nil),
		Methods: []grpc.MethodDesc{
			{
				MethodName: "ListProjects",
				Handler: func(_ any, _ context.Context, dec func(any) error, _ grpc.UnaryServerInterceptor) (any, error) {
					req := new(ListProjectsRequest)
					if err := dec(req); err != nil {
						return nil, err
					}
					if f.listErr != nil {
						return nil, f.listErr
					}
					return f.listResp, nil
				},
			},
		},
		Streams: []grpc.StreamDesc{},
	}
}

func startTestServer(t *testing.T, fake *fakeProjectServer) *FleetClient {
	t.Helper()
	lis := bufconn.Listen(testBufSize)
	srv := grpc.NewServer()

	cmdDesc := fake.commandServiceDesc()
	srv.RegisterService(&cmdDesc, struct{}{})

	qryDesc := fake.queryServiceDesc()
	srv.RegisterService(&qryDesc, struct{}{})

	go func() { _ = srv.Serve(lis) }()
	t.Cleanup(srv.Stop)

	cc, err := grpc.NewClient(
		"passthrough:///bufnet",
		grpc.WithContextDialer(func(_ context.Context, _ string) (net.Conn, error) {
			return lis.Dial()
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatalf("dial bufconn: %v", err)
	}
	t.Cleanup(func() { cc.Close() })

	return NewFleetClient(&Connection{conn: cc, target: "bufnet"})
}

func TestFleetClient_CreateProject(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *CreateProjectResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantID     string
	}{
		{
			name:   "success",
			resp:   &CreateProjectResponse{ProjectID: "proj-123", Success: true},
			wantID: "proj-123",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "db failure"),
			wantErr:    true,
			wantSubstr: "create_project RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t, &fakeProjectServer{
				createResp: tt.resp,
				createErr:  tt.serverErr,
			})

			got, err := client.CreateProject(context.Background(), "req-1", "My Project", "A test project")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.ID != tt.wantID {
				t.Errorf("ID = %q, want %q", got.ID, tt.wantID)
			}
			if got.Name != "My Project" {
				t.Errorf("Name = %q, want %q", got.Name, "My Project")
			}
			if got.Description != "A test project" {
				t.Errorf("Description = %q, want %q", got.Description, "A test project")
			}
		})
	}
}

func TestFleetClient_ListProjects(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *ListProjectsResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &ListProjectsResponse{},
			wantLen: 0,
		},
		{
			name: "multiple projects with full field mapping",
			resp: &ListProjectsResponse{
				Projects: []*ProjectMsg{
					{
						ProjectID:   "p1",
						Name:        "Alpha",
						Description: "First project",
						Status:      "active",
						Owner:       "alice",
						CreatedAt:   "2025-01-01T00:00:00Z",
						UpdatedAt:   "2025-01-02T00:00:00Z",
					},
					{
						ProjectID:   "p2",
						Name:        "Beta",
						Description: "Second project",
						Status:      "draft",
						Owner:       "bob",
						CreatedAt:   "2025-02-01T00:00:00Z",
						UpdatedAt:   "2025-02-02T00:00:00Z",
					},
				},
				TotalCount: 2,
			},
			wantLen: 2,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Unavailable, "service down"),
			wantErr:    true,
			wantSubstr: "list_projects RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t, &fakeProjectServer{
				listResp: tt.resp,
				listErr:  tt.serverErr,
			})

			got, err := client.ListProjects(context.Background())
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen < 2 {
				return
			}
			p := got[0]
			if p.ID != "p1" {
				t.Errorf("projects[0].ID = %q, want %q", p.ID, "p1")
			}
			if p.Name != "Alpha" {
				t.Errorf("projects[0].Name = %q, want %q", p.Name, "Alpha")
			}
			if p.Description != "First project" {
				t.Errorf("projects[0].Description = %q, want %q", p.Description, "First project")
			}
			if p.Status != "active" {
				t.Errorf("projects[0].Status = %q, want %q", p.Status, "active")
			}
			if p.Owner != "alice" {
				t.Errorf("projects[0].Owner = %q, want %q", p.Owner, "alice")
			}
			if p.CreatedAt != "2025-01-01T00:00:00Z" {
				t.Errorf("projects[0].CreatedAt = %q, want %q", p.CreatedAt, "2025-01-01T00:00:00Z")
			}
			if p.UpdatedAt != "2025-01-02T00:00:00Z" {
				t.Errorf("projects[0].UpdatedAt = %q, want %q", p.UpdatedAt, "2025-01-02T00:00:00Z")
			}
		})
	}
}
