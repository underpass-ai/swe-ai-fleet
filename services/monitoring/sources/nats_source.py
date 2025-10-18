"""NATS source for monitoring dashboard."""

import json
import logging
from typing import Any, AsyncIterator

import nats
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class NATSSource:
    """Source para monitorear streams de NATS."""
    
    def __init__(self, nats_url: str = "nats://nats.swe-ai-fleet.svc.cluster.local:4222"):
        """
        Initialize NATS source.
        
        Args:
            nats_url: URL del servidor NATS
        """
        self.nats_url = nats_url
        self.nc = None
        self.js: JetStreamContext | None = None
    
    async def connect(self) -> bool:
        """
        Connect to NATS server.
        
        Returns:
            True if connected successfully
        """
        try:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Connected to NATS at {self.nats_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False
    
    async def get_stream_info(self, stream_name: str) -> dict[str, Any] | None:
        """
        Get information about a stream.
        
        Args:
            stream_name: Name of the stream
            
        Returns:
            Stream info dict or None if error
        """
        if not self.js:
            await self.connect()
        
        try:
            stream = await self.js.stream_info(stream_name)
            return {
                "name": stream.config.name,
                "subjects": stream.config.subjects,
                "messages": stream.state.messages,
                "bytes": stream.state.bytes,
                "first_seq": stream.state.first_seq,
                "last_seq": stream.state.last_seq,
                "consumer_count": stream.state.consumer_count,
            }
        except Exception as e:
            logger.error(f"Failed to get stream info for {stream_name}: {e}")
            return None
    
    async def get_latest_messages(
        self,
        stream_name: str,
        subject: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get latest messages from a stream.
        
        Args:
            stream_name: Name of the stream
            subject: Optional subject filter
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dicts
        """
        if not self.js:
            await self.connect()
        
        messages = []
        
        try:
            # Create ephemeral consumer
            consumer = await self.js.pull_subscribe(
                subject or f"{stream_name}.>",
                stream=stream_name,
            )
            
            # Fetch messages
            msgs = await consumer.fetch(limit, timeout=2)
            
            for msg in msgs:
                try:
                    data = json.loads(msg.data.decode())
                    messages.append({
                        "subject": msg.subject,
                        "data": data,
                        "sequence": msg.metadata.sequence.stream,
                        "timestamp": msg.metadata.timestamp.isoformat(),
                    })
                    await msg.ack()
                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
            
            # Clean up consumer
            await consumer.unsubscribe()
            
        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
        
        return messages
    
    async def subscribe_to_stream(
        self,
        stream_name: str,
        subject: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Subscribe to stream and yield messages in real-time.
        
        Args:
            stream_name: Name of the stream
            subject: Optional subject filter
            
        Yields:
            Message dicts as they arrive
        """
        if not self.js:
            await self.connect()
        
        try:
            # Create durable consumer for monitoring
            consumer = await self.js.pull_subscribe(
                subject or f"{stream_name}.>",
                stream=stream_name,
                durable="monitoring-dashboard",
            )
            
            while True:
                try:
                    msgs = await consumer.fetch(1, timeout=5)
                    for msg in msgs:
                        try:
                            data = json.loads(msg.data.decode())
                            yield {
                                "subject": msg.subject,
                                "data": data,
                                "sequence": msg.metadata.sequence.stream,
                                "timestamp": msg.metadata.timestamp.isoformat(),
                            }
                            await msg.ack()
                        except Exception as e:
                            logger.warning(f"Failed to parse message: {e}")
                except nats.errors.TimeoutError:
                    # No messages, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in subscription: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Failed to subscribe to stream: {e}")
    
    async def close(self):
        """Close NATS connection."""
        if self.nc:
            await self.nc.close()
            logger.info("NATS connection closed")

