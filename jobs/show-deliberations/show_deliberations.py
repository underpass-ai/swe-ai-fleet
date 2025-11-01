#!/usr/bin/env python3
"""Job to show recent deliberations with generated content from NATS events."""

import asyncio
import json
import os
from datetime import datetime

from nats.aio.client import Client as NATS


async def main():
    """Connect to NATS and show recent deliberation events."""
    
    nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
    
    print(f"🔗 Connecting to NATS at {nats_url}...")
    
    nc = NATS()
    try:
        await nc.connect(nats_url)
        print("✅ Connected to NATS")
        
        js = nc.jetstream()
        
        # Subscribe to deliberation completed events
        print("\n📥 Fetching recent deliberation.completed events...")
        
        try:
            # Try to get messages from the stream
            consumer_config = {
                "durable_name": None,  # Ephemeral consumer
                "deliver_policy": "last",
                "max_deliver": 1,
            }
            
            psub = await js.pull_subscribe(
                "orchestration.deliberation.completed",
                "show-deliberations-temp",
                stream="ORCHESTRATION_EVENTS"
            )
            
            print("📋 Recent Deliberations:\n")
            
            # Fetch last 5 messages
            for i in range(5):
                try:
                    msgs = await psub.fetch(1, timeout=2.0)
                    for msg in msgs:
                        data = json.loads(msg.data.decode())
                        
                        print(f"{'='*80}")
                        print(f"📌 Deliberation #{i+1}")
                        print(f"   Story ID: {data.get('story_id', 'N/A')}")
                        print(f"   Task ID: {data.get('task_id', 'N/A')}")
                        print(f"   Timestamp: {datetime.fromtimestamp(data.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        decisions = data.get('decisions', [])
                        print(f"\n   💡 Proposals Generated: {len(decisions)}")
                        
                        for idx, decision in enumerate(decisions, 1):
                            proposal = decision.get('proposal', {})
                            author = proposal.get('author', {})
                            content = proposal.get('content', 'N/A')
                            
                            print(f"\n   --- Proposal {idx} ---")
                            print(f"   Author: {author.get('agent_id', 'Unknown')} ({author.get('role', 'Unknown')})")
                            print(f"   Score: {decision.get('score', 0.0):.2f}")
                            print("\n   📝 Generated Content:")
                            print(f"   {'-'*70}")
                            
                            # Pretty print content (truncate if too long)
                            content_lines = content.split('\n')
                            for line in content_lines[:20]:  # Show first 20 lines
                                print(f"   {line}")
                            
                            if len(content_lines) > 20:
                                print(f"   ... ({len(content_lines) - 20} more lines)")
                            
                            print(f"   {'-'*70}")
                            
                            # Show checks info
                            checks = decision.get('checks', {})
                            if checks:
                                print("\n   ✓ Quality Checks:")
                                print(f"     - Overall Score: {checks.get('overall_score', 0.0):.2f}")
                        
                        await msg.ack()
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        print(f"\n⏱️  No more messages (fetched {i} deliberations)")
                        break
                    else:
                        print(f"⚠️  Error fetching message: {e}")
                        break
            
            print(f"\n{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Error accessing stream: {e}")
            print("\nTrying alternative: check if stream exists...")
            
            try:
                stream_info = await js.stream_info("ORCHESTRATION_EVENTS")
                print(f"✓ Stream exists: {stream_info.config.name}")
                print(f"  Messages: {stream_info.state.messages}")
                print(f"  Subjects: {stream_info.config.subjects}")
            except Exception as stream_err:
                print(f"❌ Stream not found: {stream_err}")
        
        print("\n✅ Query complete")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        await nc.close()
        print("🔌 Disconnected from NATS\n")


if __name__ == "__main__":
    asyncio.run(main())

