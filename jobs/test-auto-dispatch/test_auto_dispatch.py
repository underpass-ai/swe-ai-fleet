#!/usr/bin/env python3
"""Test auto-dispatch by publishing a plan.approved event to NATS."""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

from nats.aio.client import Client as NATS


async def test_auto_dispatch():
    """Test auto-dispatch by publishing a plan.approved event."""
    nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
    
    print(f"🔗 Connecting to NATS at {nats_url}...")
    
    nc = NATS()
    
    try:
        # Connect to NATS
        await nc.connect(nats_url)
        js = nc.jetstream()
        
        print("✅ Connected to NATS JetStream")
        
        # Create a test event
        event = {
            "story_id": "story-test-auto-dispatch",
            "plan_id": "plan-test-clean-arch",
            "approved_by": "test-automation@underpassai.com",
            "roles": ["DEV"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print("\n📤 Publishing plan.approved event:")
        print(json.dumps(event, indent=2))
        
        # Publish to planning.plan.approved
        ack = await js.publish(
            "planning.plan.approved",
            json.dumps(event).encode()
        )
        
        print(f"\n✅ Event published successfully!")
        print(f"   Stream: {ack.stream}")
        print(f"   Sequence: {ack.seq}")
        
        print("\n🔍 Expected behavior:")
        print("   1. PlanningConsumer receives event")
        print("   2. AutoDispatchService.dispatch_deliberations_for_plan() called")
        print("   3. DeliberateUseCase executes for DEV role")
        print("   4. Deliberation results logged")
        
        print("\n📋 Check orchestrator logs:")
        print("   kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=50")
        print("   Look for: '🚀 Auto-dispatching', '🎭 Starting deliberation', '✅ Deliberation completed'")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await nc.close()
        print("\n🔌 Disconnected from NATS")


if __name__ == "__main__":
    exit_code = asyncio.run(test_auto_dispatch())
    sys.exit(exit_code)

