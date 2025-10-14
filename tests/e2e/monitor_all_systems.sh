#!/bin/bash
# Monitor Neo4j, ValKey, and Ray Jobs in real-time during E2E test

set -e

echo "🔍 Starting Real-Time System Monitoring"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create monitoring log
MONITOR_LOG="/tmp/system_monitor_$(date +%s).log"
echo "Monitor log: $MONITOR_LOG"
echo ""

# Function to monitor Neo4j node count
monitor_neo4j() {
    while true; do
        COUNT=$(kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"')
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} Neo4j nodes: ${COUNT}" >> "$MONITOR_LOG"
        sleep 2
    done
}

# Function to monitor ValKey key count
monitor_valkey() {
    while true; do
        COUNT=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli DBSIZE 2>/dev/null)
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} ValKey keys: ${COUNT}" >> "$MONITOR_LOG"
        sleep 2
    done
}

# Function to monitor Ray jobs
monitor_ray() {
    while true; do
        JOBS=$(kubectl get pods -n swe-ai-fleet -o wide 2>/dev/null | grep -c "ray-" || echo "0")
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "${TIMESTAMP} Ray jobs: ${JOBS}" >> "$MONITOR_LOG"
        sleep 2
    done
}

# Function to tail monitor log
tail_monitor() {
    tail -f "$MONITOR_LOG" 2>/dev/null | while read line; do
        if [[ $line == *"Neo4j"* ]]; then
            echo -e "${CYAN}$line${NC}"
        elif [[ $line == *"ValKey"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"Ray"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Start monitors in background
echo "Starting monitors..."
monitor_neo4j &
NEO4J_PID=$!
monitor_valkey &
VALKEY_PID=$!
monitor_ray &
RAY_PID=$!
tail_monitor &
TAIL_PID=$!

echo -e "${GREEN}✅ Monitors started${NC}"
echo "   Neo4j monitor: PID $NEO4J_PID"
echo "   ValKey monitor: PID $VALKEY_PID"
echo "   Ray jobs monitor: PID $RAY_PID"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

# Wait for interrupt
trap "kill $NEO4J_PID $VALKEY_PID $RAY_PID $TAIL_PID 2>/dev/null; echo ''; echo 'Monitoring stopped'; exit 0" INT

wait

