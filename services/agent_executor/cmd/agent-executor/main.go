package main

import (
	"log"
)

func main() {
	// NOTE: Transport (gRPC) and integrations (NATS/vLLM) will be wired in a follow-up step.
	// This initial milestone focuses on domain-safe routing and validation logic with tests.
	log.Println("agent-executor: skeleton (routing core ready)")
}
