# Monitoring Service - Hexagonal Architecture Structure

## 📊 Directory Layout

```
services/monitoring/
├── domain/
│   ├── entities/          # Domain entities (no external deps)
│   │   ├── stream_info.py
│   │   ├── stream_message.py
│   │   ├── messages_collection.py
│   │   ├── monitoring_event.py
│   │   ├── fetch_request.py
│   │   ├── stream_name.py
│   │   └── ... (11 total)
│   └── ports/             # Abstractions (interfaces)
│       ├── connection_port.py
│       ├── stream_port.py
│       └── configuration_port.py
│
├── infrastructure/
│   ├── common/            # Shared infrastructure components
│   │   └── adapters/
│   │       └── environment_configuration_adapter.py
│   │
│   └── stream_connectors/ # Stream/message connector implementations
│       └── nats/          # NATS-specific implementation
│           ├── adapters/
│           │   ├── nats_connection_adapter.py
│           │   └── nats_stream_adapter.py
│           ├── dto/       # Data Transfer Objects
│           │   ├── stream_info_dto.py
│           │   ├── stream_message_dto.py
│           │   └── messages_collection_dto.py
│           └── mappers/   # DTO ↔ Entity converters
│               ├── stream_info_mapper.py
│               ├── stream_message_mapper.py
│               └── messages_collection_mapper.py
│
├── application/           # Use cases (TODO)
│   └── usecases/
│
├── sources/               # Legacy adapters (being refactored)
│   ├── nats_source.py
│   └── neo4j_source.py
│
└── server.py             # FastAPI entry point with DI
```

## 🎯 Layering Pattern

```
Layer 1: Domain (Pure Business Logic)
  └─ Entities (StreamMessage, MonitoringEvent)
  └─ Value Objects (StreamName)
  └─ Ports (Interfaces: ConnectionPort, StreamPort)

Layer 2: Infrastructure (External Dependencies)
  └─ Common Adapters (EnvironmentConfigurationAdapter)
  └─ Stream Connectors
     └─ NATS Implementation
        ├─ Adapters (NATSConnectionAdapter, NATSStreamAdapter)
        ├─ DTOs (StreamInfoDTO, StreamMessageDTO)
        └─ Mappers (Entity ↔ DTO conversion)

Layer 3: Application (Use Cases)
  └─ Orchestrate domain + infrastructure

Layer 4: Presentation (FastAPI)
  └─ server.py with Dependency Injection
```

## 🚀 Dependency Flow

```
FastAPI Server (server.py)
    ↓ injects
EnvironmentConfigurationAdapter
    ↓ provides NATS URL to
create_nats_source() factory
    ↓ injects
NATSConnectionAdapter + NATSStreamAdapter
    ↓ to
NATSSource (legacy adapter using ports)
    ↓ uses
ConnectionPort + StreamPort (interfaces)
    ↓ implements
NATS-specific adapters
    ↓ produces
DTOs → Mappers → Domain Entities
```

## 📝 Future Extensibility

To add a new stream connector (e.g., Kafka):

```
infrastructure/stream_connectors/kafka/
├── adapters/
│   ├── kafka_connection_adapter.py
│   └── kafka_stream_adapter.py
├── dto/
│   └── kafka_*.py
└── mappers/
    └── kafka_*_mapper.py
```

Same interfaces, different implementations = plug and play!

## ✅ Benefits of This Structure

1. **Clear Separation**: Domain, Infrastructure, Application layers clearly separated
2. **Testability**: Mock any adapter easily
3. **Scalability**: Add new connectors without modifying existing code
4. **Maintainability**: Each connector in its own directory
5. **Reusability**: Common adapters shared across connectors
6. **Type Safety**: Domain entities are the single source of truth
7. **Flexibility**: Swap NATS for Kafka with minimal changes
