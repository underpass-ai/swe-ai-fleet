#!/bin/bash
# Manual Test Script for Backlog Review Flow
# 
# This script verifies the complete backlog review flow as described in:
# docs/architecture/BACKLOG_REVIEW_FLOW_NO_STYLES.md
#
# Flow Steps:
# 1. UI → Planning Service (gRPC): Get node relations
# 2. UI → Planning Service (gRPC): Deliberation request or list of stories
# 3. Planning → Context Service (gRPC): Get context rehydration by RBAC and StoryId
# 4. Planning → Ray Executor (gRPC): Trigger deliberation per RBAC agent and StoryId
# 5. Ray Executor → Ray Job: Create Ray job
# 6. Ray Job → vLLM Service (REST): Model invocation for rehydrated context
# 7. vLLM → NATS: VLLM response (StoryID, DeliberationId)
# 8. Backlog Review Processor → Context Service (gRPC): Save deliberation response
# 9. Backlog Review Processor → Planning Service (NATS): DELIBERATIONS COMPLETED
# 10. Backlog Review Processor → Ray Executor (gRPC): Trigger task creation
# 11. Ray Executor → Ray Job: Create Ray job for task creation
# 12. Ray Job → vLLM Service (REST): Model invocation with all deliberations
# 13. vLLM → NATS: VLLM response (TaskId, StoryID) - N events
# 14. Backlog Review Processor → Context Service (gRPC): Save TASK response (N times)
# 15. Backlog Review Processor → Planning Service (NATS): ALL TASK CREATED
# 16. Planning Service → UI (gRPC/WebSocket): Notify all tasks created

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLANNING_SERVICE_HOST="${PLANNING_SERVICE_HOST:-localhost:50051}"
CONTEXT_SERVICE_HOST="${CONTEXT_SERVICE_HOST:-localhost:50052}"
RAY_EXECUTOR_HOST="${RAY_EXECUTOR_HOST:-localhost:50053}"
NATS_HOST="${NATS_HOST:-localhost:4222}"
NEO4J_HOST="${NEO4J_HOST:-localhost:7687}"
VALKEY_HOST="${VALKEY_HOST:-localhost:6379}"

# Test data
CEREMONY_ID="BRC-TEST-$(date +%s)"
STORY_ID="${STORY_ID:-STORY-TEST-001}"
PROJECT_ID="${PROJECT_ID:-PROJECT-TEST-001}"
CREATED_BY="${CREATED_BY:-po@test.com}"

# Log file
LOG_FILE="/tmp/backlog-review-flow-test-$(date +%s).log"

echo "========================================="
echo "Backlog Review Flow - Manual Test Script"
echo "========================================="
echo ""
echo "Configuration:"
echo "  Planning Service: $PLANNING_SERVICE_HOST"
echo "  Context Service:  $CONTEXT_SERVICE_HOST"
echo "  Ray Executor:     $RAY_EXECUTOR_HOST"
echo "  NATS:             $NATS_HOST"
echo "  Neo4j:            $NEO4J_HOST"
echo "  Valkey:           $VALKEY_HOST"
echo ""
echo "Test Data:"
echo "  Ceremony ID:      $CEREMONY_ID"
echo "  Story ID:         $STORY_ID"
echo "  Project ID:       $PROJECT_ID"
echo "  Created By:        $CREATED_BY"
echo ""
echo "Log File:          $LOG_FILE"
echo ""

# Function to print step header
print_step() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Step $1: $2${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Function to wait for user confirmation
wait_for_user() {
    echo ""
    read -p "Press Enter to continue to next step (or Ctrl+C to abort)..."
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local host=$2
    print_info "Checking $service_name health at $host..."
    
    # This is a placeholder - implement actual health check based on service type
    if command -v grpc_health_probe &> /dev/null; then
        if grpc_health_probe -addr="$host" &> /dev/null; then
            print_success "$service_name is healthy"
            return 0
        else
            print_error "$service_name is not healthy"
            return 1
        fi
    else
        print_warning "grpc_health_probe not found, skipping health check"
        return 0
    fi
}

# Function to verify NATS event
verify_nats_event() {
    local subject=$1
    local expected_content=$2
    print_info "Verifying NATS event on subject: $subject"
    print_warning "Manual verification required - check NATS logs or use nats CLI:"
    echo "  nats sub '$subject'"
    wait_for_user
}

# Function to verify Neo4j data
verify_neo4j() {
    local query=$1
    local description=$2
    print_info "Verifying Neo4j: $description"
    print_warning "Manual verification required - run Cypher query:"
    echo "  $query"
    wait_for_user
}

# Function to verify Valkey data
verify_valkey() {
    local key=$1
    local description=$2
    print_info "Verifying Valkey: $description"
    print_warning "Manual verification required - check key:"
    echo "  redis-cli GET '$key'"
    wait_for_user
}

# ============================================
# STEP 1: Create Backlog Review Ceremony
# ============================================
print_step "1" "Create Backlog Review Ceremony"

print_info "Creating ceremony via gRPC..."
print_warning "Execute this command manually:"
echo ""
echo "grpcurl -plaintext -d '{"
echo "  \"created_by\": \"$CREATED_BY\","
echo "  \"story_ids\": [\"$STORY_ID\"]"
echo "}' $PLANNING_SERVICE_HOST planning.v2.PlanningService/CreateBacklogReviewCeremony"
echo ""

wait_for_user

# Verify ceremony was created
verify_neo4j \
    "MATCH (c:BacklogReviewCeremony {id: '$CEREMONY_ID'}) RETURN c" \
    "Ceremony node exists in Neo4j"

verify_valkey \
    "ceremony:$CEREMONY_ID" \
    "Ceremony cached in Valkey"

print_success "Step 1 completed: Ceremony created"

# ============================================
# STEP 2: Get Node Relations (UI → Planning)
# ============================================
print_step "2" "Get Node Relations (UI → Planning Service)"

print_info "Getting node relations via gRPC..."
print_warning "Execute this command manually:"
echo ""
echo "grpcurl -plaintext -d '{"
echo "  \"project_id\": \"$PROJECT_ID\""
echo "}' $PLANNING_SERVICE_HOST planning.v2.PlanningService/GetNodeRelations"
echo ""

wait_for_user

print_success "Step 2 completed: Node relations retrieved"

# ============================================
# STEP 3: Start Backlog Review Ceremony
# ============================================
print_step "3" "Start Backlog Review Ceremony"

print_info "Starting ceremony via gRPC..."
print_warning "Execute this command manually:"
echo ""
echo "grpcurl -plaintext -d '{"
echo "  \"ceremony_id\": \"$CEREMONY_ID\","
echo "  \"started_by\": \"$CREATED_BY\""
echo "}' $PLANNING_SERVICE_HOST planning.v2.PlanningService/StartBacklogReviewCeremony"
echo ""

wait_for_user

# Verify ceremony status changed to IN_PROGRESS
verify_neo4j \
    "MATCH (c:BacklogReviewCeremony {id: '$CEREMONY_ID'}) RETURN c.status AS status" \
    "Ceremony status is IN_PROGRESS"

print_success "Step 3 completed: Ceremony started"

# ============================================
# STEP 4: Verify Context Service Call
# ============================================
print_step "4" "Verify Context Service Call (Planning → Context Service)"

print_info "Planning Service should call Context Service for context rehydration..."
print_warning "Check Planning Service logs for:"
echo "  'Get context rehydration by RBAC and StoryId'"
echo "  Context Service gRPC call to: $CONTEXT_SERVICE_HOST"
echo ""

wait_for_user

print_success "Step 4 completed: Context Service called"

# ============================================
# STEP 5: Verify Ray Executor Call
# ============================================
print_step "5" "Verify Ray Executor Call (Planning → Ray Executor)"

print_info "Planning Service should call Ray Executor to trigger deliberations..."
print_warning "Check Planning Service logs for:"
echo "  'Trigger deliberation per RBAC agent and StoryId'"
echo "  Ray Executor gRPC call to: $RAY_EXECUTOR_HOST"
echo "  Expected: 3 deliberations per story (ARCHITECT, QA, DEVOPS)"
echo ""

wait_for_user

# Verify Ray jobs were created
print_info "Check Ray dashboard or logs for created jobs"
wait_for_user

print_success "Step 5 completed: Ray Executor called"

# ============================================
# STEP 6: Verify Ray Job → vLLM Call
# ============================================
print_step "6" "Verify Ray Job → vLLM Service (REST)"

print_info "Ray jobs should invoke vLLM Service..."
print_warning "Check Ray job logs for:"
echo "  'Model invocation (OpenAI) for rehydrated context'"
echo "  vLLM REST API calls"
echo ""

wait_for_user

print_success "Step 6 completed: vLLM Service invoked"

# ============================================
# STEP 7: Verify NATS Event (vLLM Response)
# ============================================
print_step "7" "Verify NATS Event (vLLM → NATS → Backlog Review Processor)"

verify_nats_event \
    "agent.response.completed" \
    "VLLM response with StoryID and DeliberationId"

print_info "Backlog Review Processor should consume this event..."
print_warning "Check Backlog Review Processor logs for:"
echo "  'Received agent.response.completed event'"
echo "  'StoryID: $STORY_ID, DeliberationId: ...'"
echo ""

wait_for_user

print_success "Step 7 completed: NATS event published and consumed"

# ============================================
# STEP 8: Verify Context Service Save
# ============================================
print_step "8" "Verify Context Service Save (Backlog Review Processor → Context Service)"

print_info "Backlog Review Processor should save deliberation response..."
print_warning "Check Backlog Review Processor logs for:"
echo "  'Save deliberation response'"
echo "  Context Service gRPC call to save deliberation"
echo ""

wait_for_user

# Verify deliberation saved in Context Service
verify_neo4j \
    "MATCH (d:Deliberation {story_id: '$STORY_ID'}) RETURN d" \
    "Deliberation saved in Context Service"

print_success "Step 8 completed: Deliberation saved"

# ============================================
# STEP 9: Verify Deliberations Complete Event
# ============================================
print_step "9" "Verify Deliberations Complete (Backlog Review Processor → Planning Service)"

verify_nats_event \
    "planning.backlog_review.deliberations.complete" \
    "All deliberations completed for story"

print_info "Planning Service should receive this event..."
print_warning "Check Planning Service logs for:"
echo "  'DELIBERATIONS COMPLETED'"
echo "  Ceremony status transition: IN_PROGRESS → REVIEWING"
echo ""

wait_for_user

# Verify ceremony status changed to REVIEWING
verify_neo4j \
    "MATCH (c:BacklogReviewCeremony {id: '$CEREMONY_ID'}) RETURN c.status AS status" \
    "Ceremony status is REVIEWING"

print_success "Step 9 completed: Deliberations completed"

# ============================================
# STEP 10: Verify Task Creation Trigger
# ============================================
print_step "10" "Verify Task Creation Trigger (Backlog Review Processor → Ray Executor)"

print_info "Backlog Review Processor should trigger task creation..."
print_warning "Check Backlog Review Processor logs for:"
echo "  'Trigger task creation to TASK CREATOR agent and StoryId'"
echo "  Ray Executor gRPC call for task extraction"
echo ""

wait_for_user

print_success "Step 10 completed: Task creation triggered"

# ============================================
# STEP 11: Verify Task Creation Ray Job
# ============================================
print_step "11" "Verify Task Creation Ray Job (Ray Executor → Ray Job)"

print_info "Ray Executor should create Ray job for task creation..."
print_warning "Check Ray dashboard or logs for:"
echo "  New Ray job for task extraction"
echo ""

wait_for_user

print_success "Step 11 completed: Task creation Ray job created"

# ============================================
# STEP 12: Verify Task Creation vLLM Call
# ============================================
print_step "12" "Verify Task Creation vLLM Call (Ray Job → vLLM Service)"

print_info "Ray job should invoke vLLM Service with all deliberations..."
print_warning "Check Ray job logs for:"
echo "  'Model invocation (OpenAI) with all deliberations'"
echo "  vLLM REST API call with task extraction prompt"
echo ""

wait_for_user

print_success "Step 12 completed: vLLM Service invoked for task creation"

# ============================================
# STEP 13: Verify Task NATS Events (Loop)
# ============================================
print_step "13" "Verify Task NATS Events (vLLM → NATS) - N events"

verify_nats_event \
    "agent.response.completed" \
    "VLLM response with TaskId and StoryID (N events, one per task)"

print_info "Backlog Review Processor should consume these events..."
print_warning "Check Backlog Review Processor logs for:"
echo "  Multiple 'Received agent.response.completed event' entries"
echo "  'TaskId: ..., StoryID: $STORY_ID'"
echo ""

wait_for_user

print_success "Step 13 completed: Task NATS events published"

# ============================================
# STEP 14: Verify Task Saving Loop
# ============================================
print_step "14" "Verify Task Saving Loop (Backlog Review Processor → Context Service) - N times"

print_info "Backlog Review Processor should save each task..."
print_warning "Check Backlog Review Processor logs for:"
echo "  Multiple 'Save TASK response' entries (N times)"
echo "  Context Service gRPC calls to save tasks"
echo ""

wait_for_user

# Verify tasks saved in Context Service
verify_neo4j \
    "MATCH (t:Task {story_id: '$STORY_ID'}) RETURN t" \
    "Tasks saved in Context Service"

print_success "Step 14 completed: Tasks saved"

# ============================================
# STEP 15: Verify All Tasks Created Event
# ============================================
print_step "15" "Verify All Tasks Created Event (Backlog Review Processor → Planning Service)"

verify_nats_event \
    "planning.backlog_review.tasks.complete" \
    "All tasks created (after all N tasks saved)"

print_info "Planning Service should receive this event..."
print_warning "Check Planning Service logs for:"
echo "  'ALL TASK CREATED'"
echo "  Notification to UI"
echo ""

wait_for_user

print_success "Step 15 completed: All tasks created event published"

# ============================================
# STEP 16: Verify UI Notification
# ============================================
print_step "16" "Verify UI Notification (Planning Service → UI)"

print_info "Planning Service should notify UI..."
print_warning "Check Planning Service logs for:"
echo "  'Notify all tasks created'"
echo "  gRPC/WebSocket notification to UI"
echo ""

print_warning "Check UI (Planning UI) for:"
echo "  Ceremony status updated"
echo "  Tasks displayed"
echo ""

wait_for_user

print_success "Step 16 completed: UI notified"

# ============================================
# Final Summary
# ============================================
echo ""
echo "========================================="
echo -e "${GREEN}Backlog Review Flow Test - Summary${NC}"
echo "========================================="
echo ""
echo "Test Data Used:"
echo "  Ceremony ID: $CEREMONY_ID"
echo "  Story ID:    $STORY_ID"
echo "  Project ID:  $PROJECT_ID"
echo ""
echo "Verification Checklist:"
echo "  [ ] Ceremony created in Neo4j and Valkey"
echo "  [ ] Ceremony started (status: IN_PROGRESS)"
echo "  [ ] Context Service called for context rehydration"
echo "  [ ] Ray Executor called for deliberations (3 per story)"
echo "  [ ] Ray jobs created and executed"
echo "  [ ] vLLM Service invoked for deliberations"
echo "  [ ] NATS events published (agent.response.completed)"
echo "  [ ] Deliberations saved in Context Service"
echo "  [ ] Deliberations complete event published"
echo "  [ ] Ceremony status changed to REVIEWING"
echo "  [ ] Task creation triggered"
echo "  [ ] Task creation Ray job created"
echo "  [ ] vLLM Service invoked for task extraction"
echo "  [ ] Task NATS events published (N events)"
echo "  [ ] Tasks saved in Context Service"
echo "  [ ] All tasks created event published"
echo "  [ ] UI notified"
echo ""
echo "Log File: $LOG_FILE"
echo ""
echo -e "${GREEN}Manual test completed!${NC}"
echo ""




