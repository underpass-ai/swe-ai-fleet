#!/bin/bash
# Run complete E2E demo with real-time monitoring

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}🚀 COMPLETE MONITORED E2E DEMONSTRATION${NC}"
echo -e "${BOLD}${CYAN}=======================================${NC}"
echo ""

# Step 1: Clean databases
echo -e "${YELLOW}Step 1: Cleaning databases...${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n) DETACH DELETE n" 2>/dev/null || true
kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli FLUSHALL 2>/dev/null || true
echo -e "${GREEN}✅ Databases cleaned${NC}"
echo ""

# Step 2: Verify initial state
echo -e "${YELLOW}Step 2: Verifying initial state...${NC}"
NEO4J_NODES=$(kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"')
VALKEY_KEYS=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli DBSIZE 2>/dev/null)
echo -e "${CYAN}  Neo4j nodes: $NEO4J_NODES${NC}"
echo -e "${GREEN}  ValKey keys: $VALKEY_KEYS${NC}"
echo ""

# Step 3: Start monitoring
echo -e "${YELLOW}Step 3: Starting real-time monitors...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/monitor_complete_system.sh" &
MONITOR_PID=$!
sleep 3
echo -e "${GREEN}✅ Monitors running (PID: $MONITOR_PID)${NC}"
echo ""

# Step 4: Show initial Ray state
echo -e "${YELLOW}Step 4: Ray cluster status...${NC}"
RAY_PODS=$(kubectl get pods -n swe-ai-fleet | grep -c "ray-" || echo "0")
echo -e "  Ray pods: $RAY_PODS"
echo ""

# Step 5: Show NATS streams
echo -e "${YELLOW}Step 5: NATS streams status...${NC}"
kubectl exec -n swe-ai-fleet nats-0 -- nats stream list 2>/dev/null | head -20 || echo "  NATS streams: Unable to list"
echo ""

# Step 6: Run E2E demo
echo -e "${BOLD}${GREEN}Step 6: Running full E2E demonstration...${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
sleep 2

cd "$(dirname "$SCRIPT_DIR")/$(dirname "$SCRIPT_DIR")"
python tests/e2e/full_system_demo.py 2>&1 | tee /tmp/monitored_demo_execution.log

# Step 7: Stop monitoring
echo ""
echo -e "${YELLOW}Step 7: Stopping monitors...${NC}"
kill $MONITOR_PID 2>/dev/null || true
sleep 2
echo -e "${GREEN}✅ Monitors stopped${NC}"
echo ""

# Step 8: Final state
echo -e "${YELLOW}Step 8: Verifying final state...${NC}"
NEO4J_NODES_FINAL=$(kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"')
VALKEY_KEYS_FINAL=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli DBSIZE 2>/dev/null)
echo -e "${CYAN}  Neo4j nodes: $NEO4J_NODES → $NEO4J_NODES_FINAL${NC}"
echo -e "${GREEN}  ValKey keys: $VALKEY_KEYS → $VALKEY_KEYS_FINAL${NC}"
echo ""

# Step 9: Query created data
echo -e "${YELLOW}Step 9: Querying created data...${NC}"
echo ""
echo -e "${BOLD}Neo4j - Story Structure:${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (s:ProjectCase) RETURN s.story_id, s.title, s.current_phase" 2>/dev/null
echo ""
echo -e "${BOLD}Neo4j - Decisions:${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (d:ProjectDecision) RETURN d.decision_id, d.made_by_role, d.title" 2>/dev/null
echo ""
echo -e "${BOLD}ValKey - Context Keys:${NC}"
kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli KEYS "context:*" 2>/dev/null
echo ""

# Step 10: Show Ray jobs that ran
echo -e "${YELLOW}Step 10: Ray jobs executed...${NC}"
kubectl get pods -n swe-ai-fleet | grep "ray-" || echo "  No active Ray pods (completed)"
echo ""

# Step 11: Show NATS final state
echo -e "${YELLOW}Step 11: NATS final state...${NC}"
kubectl exec -n swe-ai-fleet nats-0 -- nats stream info ORCHESTRATION 2>/dev/null | grep -E "Messages|Subjects" || true
kubectl exec -n swe-ai-fleet nats-0 -- nats stream info CONTEXT 2>/dev/null | grep -E "Messages|Subjects" || true
echo ""

echo -e "${BOLD}${GREEN}=========================================${NC}"
echo -e "${BOLD}${GREEN}✅ MONITORED DEMO COMPLETE!${NC}"
echo -e "${BOLD}${GREEN}=========================================${NC}"
echo ""
echo -e "${CYAN}Logs saved:${NC}"
echo -e "  - System monitor: $(ls -la /tmp/complete_system_monitor_*.log 2>/dev/null | tail -1 | awk '{print $NF}')"
echo -e "  - Demo execution: /tmp/monitored_demo_execution.log"
echo ""

