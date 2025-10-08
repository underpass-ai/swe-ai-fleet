// Story Coach Service: DoR/INVEST scoring and refinement
package main

import (
	"log"
	"net"
	"os"

	"google.golang.org/grpc"

	coachv1 "github.com/underpass-ai/swe-ai-fleet/services/storycoach/gen/fleet/storycoach/v1"
	"github.com/underpass-ai/swe-ai-fleet/services/storycoach/internal/svc"
)

func main() {
	// Create gRPC server
	grpcServer := grpc.NewServer()
	coachService := svc.NewCoach()
	coachv1.RegisterStoryCoachServiceServer(grpcServer, coachService)

	// Listen
	port := os.Getenv("PORT")
	if port == "" {
		port = "50052"
	}

	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	log.Printf("Story Coach service listening on :%s", port)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}


