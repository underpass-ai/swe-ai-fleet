"""NATS source for monitoring dashboard.

Adapter that connects to NATS and retrieves data using domain entities.
"""

import json
import logging
from typing import AsyncIterator

import nats

from ..domain.entities import (
    StreamInfo,
    StreamQuery,
    StreamMessage,
    MessagesCollection,
    SubscribeRequest,
    DurableConsumer,
    FetchRequest,
    PullSubscribeRequest,
)
from ..domain.ports.connection_port import ConnectionPort
from ..domain.ports.stream_port import StreamPort

logger = logging.getLogger(__name__)


class NATSSource:
    """NATS adapter for monitoring dashboard.
    
    Retrieves stream data as domain entities using injected ports.
    """
    
    def __init__(self, nats_connection: ConnectionPort, jetstream: StreamPort):
        """
        Initialize NATS source.
        
        Args:
            nats_connection: Injected NATSConnectionPort instance
            jetstream: Injected JetStreamPort instance
        """
        self.connection = nats_connection
        self.js = jetstream
    
    async def connect(self) -> bool:
        """
        Connect to NATS server via injected connection port.
        
        Returns:
            True if connected successfully
        """
        try:
            await self.connection.connect()
            # Set JetStream context via port
            self.js.set_context(self.connection.get_jetstream())
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
        collection = MessagesCollection.create()
        
        try:
            # Build query entity
            query = StreamQuery.create(
                stream_name=stream_name,
                subject=subject,
                limit=limit,
            )
            
            # Create ephemeral consumer via PullSubscribeRequest
            pull_request = PullSubscribeRequest.create(
                subject=query.get_subject_filter(),
                stream=stream_name
            )
            consumer = await self.js.pull_subscribe(pull_request)

            # Fetch messages
            msgs = await self.js.fetch_messages(consumer, limit, 2)
            
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
            
            # Create durable consumer via port
            consumer = await self.js.create_durable_consumer(
                consumer_config.get_subject_filter(),
                stream_name,
                consumer_config.get_consumer_name(),
            )

            while True:
                try:
                    fetch_req = FetchRequest.default_monitoring()
                    msgs = await self.js.fetch_messages(consumer, fetch_req.limit, fetch_req.timeout)
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

