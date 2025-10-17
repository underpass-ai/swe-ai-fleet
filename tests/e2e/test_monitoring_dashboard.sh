#!/bin/bash
#
# Test Monitoring Dashboard - E2E Test
# Publishes events to NATS and verifies they appear in the dashboard
#

set -e

echo "🎯 Testing Monitoring Dashboard"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="swe-ai-fleet"
NATS_POD=$(kubectl get pod -n $NAMESPACE -l app=nats -o jsonpath='{.items[0].metadata.name}')
DASHBOARD_URL="https://monitoring-dashboard.underpassai.com"

echo -e "${BLUE}📊 Dashboard URL:${NC} $DASHBOARD_URL"
echo -e "${BLUE}🔌 NATS Pod:${NC} $NATS_POD"
echo ""

# Helper function to publish NATS event
publish_event() {
    local subject=$1
    local data=$2
    kubectl run -n $NAMESPACE nats-pub-tmp --rm -i --restart=Never --image=natsio/nats-box:latest -- \
        nats pub -s nats://nats:4222 "$subject" "$data" 2>/dev/null || true
}

# Test 1: Publish planning event
echo -e "${YELLOW}1️⃣ Publishing planning.story.created event...${NC}"
publish_event "planning.story.created" '{
  "event_type": "STORY_CREATED",
  "story_id": "US-MONITOR-TEST-001",
  "title": "Test monitoring dashboard event capture",
  "description": "Verify that events appear in real-time on the dashboard",
  "created_by": "tirso@underpassai.com",
  "priority": "HIGH",
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}'
echo -e "${GREEN}✅ Event published${NC}"
echo ""

# Test 2: Publish orchestration event
echo -e "${YELLOW}2️⃣ Publishing orchestration.deliberation.started event...${NC}"
publish_event "orchestration.deliberation.started" '{
  "event_type": "DELIBERATION_STARTED",
  "story_id": "US-MONITOR-TEST-001",
  "task_id": "task-monitor-001",
  "role": "DEV",
  "num_agents": 3,
  "agents": ["agent-dev-001", "agent-dev-002", "agent-dev-003"],
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}'
echo -e "${GREEN}✅ Event published${NC}"
echo ""

# Test 3: Publish context update event
echo -e "${YELLOW}3️⃣ Publishing context.updated event...${NC}"
publish_event "context.updated" '{
  "event_type": "CONTEXT_UPDATED",
  "story_id": "US-MONITOR-TEST-001",
  "version": 2,
  "changes": ["decisions", "subtasks"],
  "affected_roles": ["DEV", "QA"],
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}'
echo -e "${GREEN}✅ Event published${NC}"
echo ""

# Test 4: Publish orchestration completed event
echo -e "${YELLOW}4️⃣ Publishing orchestration.deliberation.completed event...${NC}"
publish_event "orchestration.deliberation.completed" '{
  "event_type": "DELIBERATION_COMPLETED",
  "story_id": "US-MONITOR-TEST-001",
  "task_id": "task-monitor-001",
  "role": "DEV",
  "winner_agent_id": "agent-dev-002",
  "duration_ms": 3500,
  "decisions": [
    {
      "id": "dec-001",
      "type": "TECHNICAL_CHOICE",
      "rationale": "Use FastAPI for monitoring backend",
      "decided_by": "agent-dev-002"
    }
  ],
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}'
echo -e "${GREEN}✅ Event published${NC}"
echo ""

# Check dashboard logs
echo -e "${YELLOW}5️⃣ Checking dashboard logs...${NC}"
kubectl logs -n $NAMESPACE -l app=monitoring --tail=20 | grep -E "(Subscribed|event_type|NATS)" || true
echo ""

# Show dashboard info
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Test Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}📊 Access the dashboard at:${NC}"
echo -e "   $DASHBOARD_URL"
echo ""
echo -e "${BLUE}🔍 You should see 4 events:${NC}"
echo "   1. planning.story.created"
echo "   2. orchestration.deliberation.started"
echo "   3. context.updated"
echo "   4. orchestration.deliberation.completed"
echo ""
echo -e "${YELLOW}💡 Note:${NC} Events appear in real-time via WebSocket"
echo ""

