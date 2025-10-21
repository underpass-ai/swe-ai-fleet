#!/bin/bash
#
# Create NATS Streams for Monitoring Dashboard
#

set -e

NAMESPACE="swe-ai-fleet"
NATS_POD="nats-0"

echo "🚀 Creating NATS Streams for Monitoring Dashboard"
echo "=================================================="
echo ""

# Create PLANNING_EVENTS stream
echo "📊 Creating PLANNING_EVENTS stream..."
kubectl exec -n $NAMESPACE $NATS_POD -- nats stream add PLANNING_EVENTS \
  --subjects "planning.>" \
  --retention limits \
  --storage file \
  --replicas 1 \
  --max-age 7d \
  --max-msgs=-1 \
  --max-bytes=-1 \
  --discard old \
  --defaults 2>/dev/null || echo "Stream already exists"

echo "✅ PLANNING_EVENTS created"
echo ""

# Create ORCHESTRATOR_EVENTS stream  
echo "📊 Creating ORCHESTRATOR_EVENTS stream..."
kubectl exec -n $NAMESPACE $NATS_POD -- nats stream add ORCHESTRATOR_EVENTS \
  --subjects "orchestration.>" \
  --retention limits \
  --storage file \
  --replicas 1 \
  --max-age 7d \
  --max-msgs=-1 \
  --max-bytes=-1 \
  --discard old \
  --defaults 2>/dev/null || echo "Stream already exists"

echo "✅ ORCHESTRATOR_EVENTS created"
echo ""

# Create CONTEXT_EVENTS stream
echo "📊 Creating CONTEXT_EVENTS stream..."
kubectl exec -n $NAMESPACE $NATS_POD -- nats stream add CONTEXT_EVENTS \
  --subjects "context.>" \
  --retention limits \
  --storage file \
  --replicas 1 \
  --max-age 7d \
  --max-msgs=-1 \
  --max-bytes=-1 \
  --discard old \
  --defaults 2>/dev/null || echo "Stream already exists"

echo "✅ CONTEXT_EVENTS created"
echo ""

# List streams
echo "📋 Current streams:"
kubectl exec -n $NAMESPACE $NATS_POD -- nats stream list

echo ""
echo "✅ All streams created successfully!"

