#!/bin/bash
#
# View Test Data in Neo4j and Valkey
#

set -e

echo "================================================================================"
echo "  📊 SWE AI Fleet - View Test Data"
echo "================================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# NEO4J DATA
# ============================================================================

echo -e "${BLUE}🗄️  NEO4J DATABASE${NC}"
echo "================================================================================"
echo ""

echo -e "${GREEN}1. Node Types Summary:${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) RETURN labels(n) AS type, count(*) AS count ORDER BY count DESC"
echo ""

echo -e "${GREEN}2. ProjectCase Nodes (Stories):${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (p:ProjectCase) RETURN p.story_id, p.title, p.current_phase, p.status, p.created_at ORDER BY p.created_at DESC LIMIT 10" || echo "No ProjectCase nodes found"
echo ""

echo -e "${GREEN}3. Case Nodes (Legacy):${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (c:Case) RETURN c.id, c.case_id, c.name LIMIT 5" || echo "No Case nodes found"
echo ""

echo -e "${GREEN}4. PhaseTransition Nodes:${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (pt:PhaseTransition) RETURN pt.story_id, pt.from_phase, pt.to_phase, pt.timestamp LIMIT 10" || echo "No PhaseTransition nodes found"
echo ""

echo -e "${GREEN}5. Decision Nodes:${NC}"
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (d:Decision) RETURN d.id, d.title, d.decision_type LIMIT 5" || echo "No Decision nodes found"
echo ""

# ============================================================================
# VALKEY DATA
# ============================================================================

echo ""
echo -e "${BLUE}💾 VALKEY (Redis) CACHE${NC}"
echo "================================================================================"
echo ""

echo -e "${GREEN}1. Story Keys (with values):${NC}"
STORY_KEYS=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli KEYS "story:*")
if [ -z "$STORY_KEYS" ]; then
    echo "  (no story keys found)"
else
    echo "$STORY_KEYS" | while read -r key; do
        if [ -n "$key" ]; then
            echo ""
            echo "  📄 $key"
            kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli HGETALL "$key" | \
                awk 'NR%2==1{k=$0} NR%2==0{printf "     %-20s %s\n", k":", $0}'
        fi
    done
fi
echo ""

echo -e "${GREEN}2. Task Keys (with values):${NC}"
TASK_KEYS=$(kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli KEYS "task:*")
if [ -z "$TASK_KEYS" ]; then
    echo "  (no task keys found)"
else
    echo "$TASK_KEYS" | while read -r key; do
        if [ -n "$key" ]; then
            echo ""
            echo "  📋 $key"
            kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli HGETALL "$key" | \
                awk 'NR%2==1{k=$0} NR%2==0{printf "     %-20s %s\n", k":", $0}'
        fi
    done
fi
echo ""

echo -e "${GREEN}3. SWE Case Keys:${NC}"
kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli KEYS "swe:case:*" | head -5
echo ""

echo -e "${GREEN}4. Context Keys:${NC}"
kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli KEYS "context:*" | head -5
echo ""

echo -e "${GREEN}5. Database Info:${NC}"
kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli INFO keyspace
echo ""

# ============================================================================
# SAMPLE DATA VIEWER
# ============================================================================

echo ""
echo -e "${YELLOW}💡 To view a specific story hash:${NC}"
echo "   kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli HGETALL story:STORY_ID"
echo ""
echo -e "${YELLOW}💡 To view a specific Neo4j node:${NC}"
echo "   kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \\"
echo "     \"MATCH (p:ProjectCase {story_id: 'STORY_ID'}) RETURN p\""
echo ""
echo "================================================================================"

