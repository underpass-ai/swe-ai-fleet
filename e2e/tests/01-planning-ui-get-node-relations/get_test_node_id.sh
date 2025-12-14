#!/bin/bash
# Helper script to get a test node ID from Neo4j

set -e

NAMESPACE="${KUBERNETES_NAMESPACE:-swe-ai-fleet}"
NEO4J_POD=$(kubectl get pods -n "$NAMESPACE" -l app=neo4j -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$NEO4J_POD" ]; then
    echo "❌ Neo4j pod not found in namespace $NAMESPACE"
    exit 1
fi

echo "🔍 Finding test node IDs in Neo4j..."
echo ""

# Get Neo4j password from secret
NEO4J_PASSWORD=$(kubectl get secret -n "$NAMESPACE" neo4j-auth -o jsonpath='{.data.NEO4J_PASSWORD}' 2>/dev/null | base64 -d 2>/dev/null || echo "testpassword")

echo "📊 Available Stories:"
kubectl exec -n "$NAMESPACE" "$NEO4J_POD" -- cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (s:Story) RETURN s.id AS story_id LIMIT 5" 2>/dev/null || echo "  (none found)"

echo ""
echo "📊 Available Projects:"
kubectl exec -n "$NAMESPACE" "$NEO4J_POD" -- cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (p:Project) RETURN p.id AS project_id LIMIT 5" 2>/dev/null || echo "  (none found)"

echo ""
echo "📊 Available Epics:"
kubectl exec -n "$NAMESPACE" "$NEO4J_POD" -- cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (e:Epic) RETURN e.id AS epic_id LIMIT 5" 2>/dev/null || echo "  (none found)"

echo ""
echo "📊 Available Tasks:"
kubectl exec -n "$NAMESPACE" "$NEO4J_POD" -- cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (t:Task) RETURN t.id AS task_id LIMIT 5" 2>/dev/null || echo "  (none found)"

echo ""
echo "💡 Use one of these IDs as TEST_NODE_ID in job.yaml"
