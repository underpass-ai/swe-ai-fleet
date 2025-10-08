// Planning Service: Agile FSM + domain events
package main

import (
	"log"
	"net"
	"os"
	"time"

	"google.golang.org/grpc"

	"github.com/underpass-ai/swe-ai-fleet/services/pkg/natsx"
	planningv1 "github.com/underpass-ai/swe-ai-fleet/services/planning/gen/fleet/planning/v1"
	"github.com/underpass-ai/swe-ai-fleet/services/planning/internal/fsmx"
	"github.com/underpass-ai/swe-ai-fleet/services/planning/internal/svc"
)

func main() {
	// Load FSM config
	fsmPath := os.Getenv("FSM_CONFIG")
	if fsmPath == "" {
		fsmPath = "config/agile.fsm.yaml"
	}

	engine, err := fsmx.LoadFromFile(fsmPath)
	if err != nil {
		log.Fatalf("Failed to load FSM config: %v", err)
	}
	log.Printf("Loaded FSM config from %s", fsmPath)

	// Connect to NATS
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://nats:4222"
	}

	nc, err := natsx.Connect(natsx.ConnectOptions{
		URL:           natsURL,
		MaxReconnect:  10,
		ReconnectWait: 2 * time.Second,
	})
	if err != nil {
		log.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer nc.Close()
	log.Printf("Connected to NATS at %s", natsURL)

	// Ensure streams exist
	if err := nc.EnsureStream(natsx.StreamConfig{
		Name:      "AGILE",
		Subjects:  []string{"agile.events"},
		Retention: 0, // Limits (default)
		MaxAge:    7 * 24 * time.Hour,
	}); err != nil {
		log.Fatalf("Failed to ensure AGILE stream: %v", err)
	}
	log.Println("Ensured AGILE stream")

	// Get FSM config from engine
	fsmCfg := engine.GetConfig()

	// Create gRPC server
	grpcServer := grpc.NewServer()
	planningService := svc.NewPlanning(fsmCfg, nc.JS)
	planningv1.RegisterPlanningServiceServer(grpcServer, planningService)

	// Listen
	port := os.Getenv("PORT")
	if port == "" {
		port = "50051"
	}

	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	log.Printf("Planning service listening on :%s", port)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}
