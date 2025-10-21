#!/usr/bin/env python3
"""
Monitor NATS events in real-time
Shows all events published during E2E demo
"""
import asyncio
import json
from datetime import datetime
from nats.aio.client import Client as NATS


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    END = '\033[0m'


async def main():
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}🎧 NATS Event Monitor - Real-Time{Colors.END}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}===================================={Colors.END}\n")
    
    # Connect to NATS
    nc = NATS()
    try:
        await nc.connect("nats://localhost:4222")
        print(f"{Colors.GREEN}✅ Connected to NATS{Colors.END}\n")
    except Exception as e:
        print(f"{Colors.YELLOW}❌ Failed to connect to NATS: {e}{Colors.END}")
        print(f"{Colors.CYAN}Run: kubectl port-forward -n swe-ai-fleet svc/nats 4222:4222{Colors.END}\n")
        return
    
    # Get JetStream context
    js = nc.jetstream()
    
    event_count = {'total': 0}
    
    async def message_handler(msg):
        """Handle incoming NATS messages"""
        event_count['total'] += 1
        subject = msg.subject
        
        try:
            data = json.loads(msg.data.decode())
        except:
            data = msg.data.decode()
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Color by subject
        if 'orchestration' in subject:
            color = Colors.YELLOW
        elif 'context' in subject:
            color = Colors.CYAN
        elif 'agent' in subject:
            color = Colors.GREEN
        elif 'planning' in subject:
            color = Colors.BLUE
        else:
            color = Colors.MAGENTA
        
        print(f"{color}[{timestamp}] {subject}{Colors.END}")
        
        # Print relevant data
        if isinstance(data, dict):
            if 'story_id' in data:
                print(f"  Story: {data['story_id']}")
            if 'task_id' in data:
                print(f"  Task: {data['task_id']}")
            if 'agent_id' in data:
                print(f"  Agent: {data['agent_id']}")
            if 'role' in data:
                print(f"  Role: {data['role']}")
            if 'winner_id' in data:
                print(f"  Winner: {Colors.BOLD}{data['winner_id']}{Colors.END}")
            if 'duration_ms' in data:
                print(f"  Duration: {data['duration_ms']}ms")
        print()
        
        await msg.ack()
    
    # Subscribe to all subjects
    subjects = [
        "orchestration.>",
        "context.>",
        "agent.>",
        "planning.>",
        "deliberation.>",
    ]
    
    print(f"{Colors.BOLD}Subscribed to:{Colors.END}")
    for subject in subjects:
        await nc.subscribe(subject, cb=message_handler)
        print(f"  • {subject}")
    
    print(f"\n{Colors.GREEN}✅ Listening for events...{Colors.END}")
    print(f"{Colors.YELLOW}Run E2E test now to see events in real-time{Colors.END}\n")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
            if event_count['total'] % 10 == 0 and event_count['total'] > 0:
                print(f"{Colors.MAGENTA}  [{event_count['total']} events so far...]{Colors.END}")
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BOLD}Total events captured: {event_count['total']}{Colors.END}\n")
        await nc.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

