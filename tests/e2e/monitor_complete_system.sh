#!/bin/bash
# Monitor Neo4j, ValKey, Ray Jobs, and NATS in real-time during E2E test

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}🔍 COMPLETE SYSTEM REAL-TIME MONITORING${NC}"
echo -e "${BOLD}${BLUE}========================================${NC}"
echo ""

# Create monitoring log
MONITOR_LOG="/tmp/complete_system_monitor_$(date +%s).log"
echo -e "${CYAN}Monitor log: $MONITOR_LOG${NC}"
echo ""

# Function to monitor Neo4j
monitor_neo4j() {
    echo "$(date '+%H:%M:%S') [START] Neo4j monitoring" >> "$MONITOR_LOG"
    while true; do
        NODES=$(kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
        RELS=$(kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH ()-[r]->() RETURN count(r) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} [NEO4J] Nodes: ${NODES}, Relationships: ${RELS}" >> "$MONITOR_LOG"
        sleep 3
    done
}

# Function to monitor ValKey
monitor_valkey() {
    echo "$(date '+%H:%M:%S') [START] ValKey monitoring" >> "$MONITOR_LOG"
    while true; do
        DBSIZE=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli DBSIZE 2>/dev/null || echo "0")
        CONTEXT_KEYS=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli KEYS "context:*" 2>/dev/null | wc -l || echo "0")
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} [VALKEY] Total: ${DBSIZE}, Context: ${CONTEXT_KEYS}" >> "$MONITOR_LOG"
        sleep 3
    done
}

# Function to monitor Ray jobs
monitor_ray() {
    echo "$(date '+%H:%M:%S') [START] Ray jobs monitoring" >> "$MONITOR_LOG"
    while true; do
        RAY_PODS=$(kubectl get pods -n swe-ai-fleet 2>/dev/null | grep -c "ray-" || echo "0")
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} [RAY] Active pods: ${RAY_PODS}" >> "$MONITOR_LOG"
        sleep 3
    done
}

# Function to monitor NATS
monitor_nats() {
    echo "$(date '+%H:%M:%S') [START] NATS monitoring" >> "$MONITOR_LOG"
    while true; do
        # Get NATS stream info
        STREAM_INFO=$(kubectl exec -n swe-ai-fleet nats-0 -- nats stream info ORCHESTRATION --json 2>/dev/null || echo "{}")
        MESSAGES=$(echo "$STREAM_INFO" | grep -o '"messages":[0-9]*' | cut -d: -f2 || echo "0")
        
        STREAM_INFO2=$(kubectl exec -n swe-ai-fleet nats-0 -- nats stream info CONTEXT --json 2>/dev/null || echo "{}")
        MESSAGES2=$(echo "$STREAM_INFO2" | grep -o '"messages":[0-9]*' | cut -d: -f2 || echo "0")
        
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} [NATS] ORCHESTRATION: ${MESSAGES:-0} msgs, CONTEXT: ${MESSAGES2:-0} msgs" >> "$MONITOR_LOG"
        sleep 3
    done
}

# Function to tail and format monitor log
tail_monitor() {
    sleep 1  # Wait for monitors to start
    tail -f "$MONITOR_LOG" 2>/dev/null | while read line; do
        if [[ $line == *"[NEO4J]"* ]]; then
            echo -e "${CYAN}$line${NC}"
        elif [[ $line == *"[VALKEY]"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"[RAY]"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"[NATS]"* ]]; then
            echo -e "${MAGENTA}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Start monitors in background
echo -e "${BOLD}Starting monitors...${NC}"
monitor_neo4j &
NEO4J_PID=$!
monitor_valkey &
VALKEY_PID=$!
monitor_ray &
RAY_PID=$!
monitor_nats &
NATS_PID=$!

sleep 2

tail_monitor &
TAIL_PID=$!

echo -e "${GREEN}✅ All monitors started${NC}"
echo ""
echo -e "${CYAN}Legend:${NC}"
echo -e "  ${CYAN}[NEO4J]${NC}  - Graph database nodes/relationships"
echo -e "  ${GREEN}[VALKEY]${NC} - Cache keys"
echo -e "  ${YELLOW}[RAY]${NC}    - Ray job pods"
echo -e "  ${MAGENTA}[NATS]${NC}   - Message streams"
echo ""
echo -e "${YELLOW}⚠️  Now run E2E test in another terminal:${NC}"
echo -e "   ${BOLD}python tests/e2e/full_system_demo.py${NC}"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

# Wait for interrupt
trap "kill $NEO4J_PID $VALKEY_PID $RAY_PID $NATS_PID $TAIL_PID 2>/dev/null; echo ''; echo -e '${GREEN}Monitoring stopped${NC}'; echo ''; echo -e '${CYAN}Monitor log saved: $MONITOR_LOG${NC}'; exit 0" INT

wait

