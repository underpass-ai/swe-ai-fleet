"""NATS source for monitoring dashboard.

Adapter that connects to NATS and retrieves data using domain entities.
"""

import json
import logging
from typing import AsyncIterator

from nats.js import JetStreamContext

from ..domain.entities import (
    StreamInfo,
    StreamQuery,
    StreamMessage,
    MessagesCollection,
    SubscribeRequest,
    DurableConsumer,
)
from ..domain.ports.nats_connection_port import NATSConnectionPort

logger = logging.getLogger(__name__)


class NATSSource:
    """NATS adapter for monitoring dashboard.
    
    Connects to NATS JetStream and retrieves stream data as domain entities.
    Uses dependency injection for connection management.
    """
    
    def __init__(self, nats_connection: NATSConnectionPort):
        """
        Initialize NATS source.
        
        Args:
            nats_connection: Injected NATSConnectionPort instance
        """
        self.connection = nats_connection
        self.js: JetStreamContext | None = None
    
    async def connect(self) -> bool:
        """
        Connect to NATS server via injected connection port.
        
        Returns:
            True if connected successfully
        """
        try:
            await self.connection.connect()
            self.js = self.connection.get_jetstream()
            logger.info("Connected to NATS via connection port")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False
    
    async def get_stream_info(self, stream_name: str) -> StreamInfo | None:
        """
        Get information about a stream.
        
        Args:
            stream_name: Name of the stream
            
        Returns:
            StreamInfo entity or None if error
        """
        if not self.js:
            await self.connect()
        
        try:
            stream = await self.js.stream_info(stream_name)
            return StreamInfo(
                name=stream.config.name,
                subjects=stream.config.subjects,
                messages=stream.state.messages,
                bytes=stream.state.bytes,
                first_seq=stream.state.first_seq,
                last_seq=stream.state.last_seq,
                consumer_count=stream.state.consumer_count,
            )
        except Exception as e:
            logger.error(f"Failed to get stream info for {stream_name}: {e}")
            return None
    
    async def get_latest_messages(
        self,
        stream_name: str,
        subject: str | None = None,
        limit: int = 10,
    ) -> MessagesCollection:
        """
        Get latest messages from a stream.
        
        Args:
            stream_name: Name of the stream
            subject: Optional subject filter
            limit: Maximum number of messages to retrieve
            
        Returns:
            MessagesCollection with retrieved messages
        """
        if not self.js:
            await self.connect()
        
        collection = MessagesCollection.create()
        
        try:
            # Build query entity
            query = StreamQuery.create(
                stream_name=stream_name,
                subject=subject,
                limit=limit,
            )
            
            # Create ephemeral consumer
            consumer = await self.js.pull_subscribe(
                query.get_subject_filter(),
                stream=stream_name,
            )
            
            # Fetch messages
            msgs = await consumer.fetch(limit, timeout=2)
            
            for msg in msgs:
                try:
                    data = json.loads(msg.data.decode())
                    stream_msg = StreamMessage.create(
                        subject=msg.subject,
                        data=data,
                        sequence=msg.metadata.sequence.stream,
                        timestamp=msg.metadata.timestamp.isoformat(),
                    )
                    collection.add(stream_msg)
                    await msg.ack()
                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
            
            # Clean up consumer
            await consumer.unsubscribe()
            
        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
        
        return collection
    
    async def subscribe_to_stream(
        self,
        stream_name: str,
        subject: str | None = None,
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to stream and yield messages in real-time.
        
        Args:
            stream_name: Name of the stream
            subject: Optional subject filter
            
        Yields:
            StreamMessage entities as they arrive
        """
        if not self.js:
            await self.connect()
        
        try:
            # Build request entity
            subscribe_req = SubscribeRequest(
                stream_name=stream_name,
                subject=subject,
            )
            subscribe_req.validate()
            
            # Create durable consumer entity
            consumer_config = DurableConsumer.for_monitoring(
                stream_name=stream_name,
                subject=subject,
            )
            consumer_config.validate()
            
            # Create durable consumer for monitoring
            consumer = await self.js.pull_subscribe(
                consumer_config.get_subject_filter(),
                stream=stream_name,
                durable=consumer_config.get_consumer_name(),
            )
            
            while True:
                try:
                    msgs = await consumer.fetch(1, timeout=5)
                    for msg in msgs:
                        try:
                            data = json.loads(msg.data.decode())
                            stream_msg = StreamMessage(
                                subject=msg.subject,
                                data=data,
                                sequence=msg.metadata.sequence.stream,
                                timestamp=msg.metadata.timestamp.isoformat(),
                            )
                            yield stream_msg
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
        if self.connection:
            await self.connection.close()
            logger.info("NATS connection closed")

