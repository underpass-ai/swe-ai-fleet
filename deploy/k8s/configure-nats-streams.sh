#!/bin/bash
# Configure NATS JetStream Streams for SWE AI Fleet
# See: docs/architecture/NATS_CONSUMERS_DESIGN.md

set -e

NAMESPACE="swe-ai-fleet"
NATS_POD="nats-0"

echo "======================================"
echo "NATS JetStream Streams Configuration"
echo "======================================"
echo ""

# Check if NATS pod is ready
echo "🔍 Checking NATS pod..."
if ! kubectl get pod $NATS_POD -n $NAMESPACE &> /dev/null; then
    echo "❌ NATS pod not found in namespace $NAMESPACE"
    exit 1
fi

echo "✅ NATS pod found"
echo ""

# Function to create stream
create_stream() {
    local stream_name=$1
    local subjects=$2
    local max_age=$3
    local max_msgs=$4
    
    echo "📦 Creating stream: $stream_name"
    echo "   Subjects: $subjects"
    echo "   Max Age: $max_age"
    echo "   Max Messages: $max_msgs"
    
    kubectl exec -n $NAMESPACE $NATS_POD -- /bin/sh -c "cat <<'EOF' | nats stream add $stream_name --config=-
{
  \"name\": \"$stream_name\",
  \"subjects\": [\"$subjects\"],
  \"retention\": \"limits\",
  \"max_age\": $max_age,
  \"max_msgs\": $max_msgs,
  \"storage\": \"file\",
  \"num_replicas\": 1,
  \"discard\": \"old\"
}
EOF" 2>&1 || echo "   (Stream may already exist)"
    
    echo ""
}

# Create streams
echo "🚀 Creating JetStream streams..."
echo ""

# Stream 1: PLANNING_EVENTS
create_stream "PLANNING_EVENTS" "planning.>" $((30 * 24 * 60 * 60 * 1000000000)) 1000000

# Stream 2: CONTEXT_EVENTS  
create_stream "CONTEXT_EVENTS" "context.>" $((7 * 24 * 60 * 60 * 1000000000)) 100000

# Stream 3: ORCHESTRATOR_EVENTS
create_stream "ORCHESTRATOR_EVENTS" "orchestration.>" $((7 * 24 * 60 * 60 * 1000000000)) 50000

# Stream 4: AGENT_COMMANDS
create_stream "AGENT_COMMANDS" "agent.cmd.>" $((1 * 60 * 60 * 1000000000)) 10000

# Stream 5: AGENT_RESPONSES
create_stream "AGENT_RESPONSES" "agent.response.>" $((1 * 60 * 60 * 1000000000)) 10000

# List all streams
echo "======================================"
echo "📊 Current Streams"
echo "======================================"
echo ""
kubectl exec -n $NAMESPACE $NATS_POD -- nats stream ls 2>/dev/null || echo "⚠️  nats CLI not available in pod"
echo ""

echo "======================================"
echo "✅ Stream Configuration Complete"
echo "======================================"
echo ""
echo "💡 Next steps:"
echo "   1. Deploy Context Service consumers"
echo "   2. Deploy Orchestrator Service consumers"
echo "   3. Monitor with: kubectl exec -n $NAMESPACE $NATS_POD -- nats stream info STREAM_NAME"
echo ""

