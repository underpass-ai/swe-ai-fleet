#!/bin/bash
#
# Clear all test data from Neo4j and Valkey
#

set -e

NAMESPACE="swe-ai-fleet"

echo "================================================================================"
echo "  🧹 Clearing Test Data from Neo4j and Valkey"
echo "================================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# CLEAR NEO4J
# ============================================================================

echo -e "${YELLOW}🗄️  Clearing Neo4j Database...${NC}"
echo ""

# Delete all nodes and relationships
kubectl exec -n ${NAMESPACE} neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) DETACH DELETE n"

echo -e "${GREEN}✅ Neo4j cleared${NC}"
echo ""

# Verify
echo "Remaining nodes:"
kubectl exec -n ${NAMESPACE} neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) RETURN count(n) AS count"
echo ""

# ============================================================================
# CLEAR VALKEY
# ============================================================================

echo -e "${YELLOW}💾 Clearing Valkey Cache...${NC}"
echo ""

# Flush all keys
kubectl exec -n ${NAMESPACE} valkey-0 -- redis-cli FLUSHALL

echo -e "${GREEN}✅ Valkey cleared${NC}"
echo ""

# Verify
echo "Remaining keys:"
kubectl exec -n ${NAMESPACE} valkey-0 -- redis-cli DBSIZE
echo ""

echo "================================================================================"
echo -e "${GREEN}✅ All test data cleared!${NC}"
echo "================================================================================"
echo ""

