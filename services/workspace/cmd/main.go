// Workspace Scoring Service
package main

import (
	"log"
	"net"
	"os"

	"google.golang.org/grpc"

	wsv1 "github.com/underpass-ai/swe-ai-fleet/services/workspace/gen/fleet/workspace/v1"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/scorer"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/svc"
)

func main() {
	// Load rigor config
	rigorPath := os.Getenv("RIGOR_CONFIG")
	if rigorPath == "" {
		rigorPath = "config/rigor.yaml"
	}

	rigorCfg, err := scorer.LoadRigorConfig(rigorPath)
	if err != nil {
		log.Fatalf("Failed to load rigor config: %v", err)
	}
	log.Printf("Loaded rigor config from %s", rigorPath)

	// Create gRPC server
	grpcServer := grpc.NewServer()
	wsService := svc.NewWorkspace(rigorCfg)
	wsv1.RegisterWorkspaceServiceServer(grpcServer, wsService)

	// Listen
	port := os.Getenv("PORT")
	if port == "" {
		port = "50053"
	}

	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	log.Printf("Workspace Scoring service listening on :%s", port)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}


