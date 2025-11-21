"""NATS consumers for Planning Service.

Consumers (Inbound Adapters):
- Listen to NATS events
- Convert DTO → VO/Entity via mappers
- Call use cases
- Handle errors and ACK/NAK

Following Hexagonal Architecture:
- Infrastructure layer (inbound adapters)
- Use mappers for conversions
- Depend on use cases (application layer)
"""

