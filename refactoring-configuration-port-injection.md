# Refactoring: Inyección de Dependencias con ConfigurationPort

## ✅ **Cambio Implementado**

### **Antes (Acoplamiento Directo):**
```python
import os

class GrpcOrchestratorQueryAdapter(OrchestratorQueryPort):
    def __init__(self, orchestrator_address: str | None = None):
        self.orchestrator_address = (
            orchestrator_address or
            os.getenv(
                "ORCHESTRATOR_ADDRESS",
                "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
            )
        )
```

### **Después (Inyección de Dependencias):**
```python
from services.monitoring.domain.ports.configuration.configuration_port import ConfigurationPort

class GrpcOrchestratorQueryAdapter(OrchestratorQueryPort):
    def __init__(self, config_port: ConfigurationPort):
        self.config_port = config_port
        self.orchestrator_address = config_port.get_orchestrator_address()
```

## 🎯 **Beneficios del Refactoring**

### **1. Principio de Inversión de Dependencias (DIP)**
- ✅ **Antes**: Dependía de `os.getenv` (implementación concreta)
- ✅ **Después**: Depende de `ConfigurationPort` (abstracción)

### **2. Testabilidad Mejorada**
```python
# ✅ Ahora es fácil hacer mocks para testing
class MockConfigurationPort(ConfigurationPort):
    def get_orchestrator_address(self) -> str:
        return "localhost:50055"  # Para tests locales
    
    def get_nats_url(self) -> str:
        return "nats://localhost:4222"
    
    def get_port(self) -> int:
        return 8080
    
    def get_config_value(self, key: str, default: str = None) -> str:
        return "test_value"

# Uso en tests
adapter = GrpcOrchestratorQueryAdapter(MockConfigurationPort())
```

### **3. Flexibilidad de Configuración**
```python
# ✅ Diferentes fuentes de configuración
class FileConfigurationAdapter(ConfigurationPort):
    def get_orchestrator_address(self) -> str:
        return self.config_file.get("orchestrator.address")

class DatabaseConfigurationAdapter(ConfigurationPort):
    def get_orchestrator_address(self) -> str:
        return self.db.get_config("orchestrator_address")

class EnvironmentConfigurationAdapter(ConfigurationPort):
    def get_orchestrator_address(self) -> str:
        return os.getenv("ORCHESTRATOR_ADDRESS", "default")
```

### **4. Arquitectura Hexagonal Completa**
- **Domain**: `ConfigurationPort` (abstracción)
- **Infrastructure**: `EnvironmentConfigurationAdapter` (implementación)
- **Application**: `GrpcOrchestratorQueryAdapter` (usa el puerto)

## 📋 **Uso en el Servidor**

### **Antes:**
```python
# ❌ Acoplamiento directo
adapter = GrpcOrchestratorQueryAdapter()
```

### **Después:**
```python
# ✅ Inyección de dependencias
config_adapter = EnvironmentConfigurationAdapter()
adapter = GrpcOrchestratorQueryAdapter(config_adapter)
```

## 🔧 **Configuración del Puerto**

### **ConfigurationPort Actualizado:**
```python
class ConfigurationPort(ABC):
    @abstractmethod
    def get_orchestrator_address(self) -> str:
        """Get orchestrator service address."""
        pass
    
    @abstractmethod
    def get_nats_url(self) -> str:
        """Get NATS server URL."""
        pass
    
    @abstractmethod
    def get_port(self) -> int:
        """Get application port."""
        pass
    
    @abstractmethod
    def get_config_value(self, key: str, default: str = None) -> str:
        """Get a configuration value."""
        pass
```

### **EnvironmentConfigurationAdapter:**
```python
class EnvironmentConfigurationAdapter(ConfigurationPort):
    def get_orchestrator_address(self) -> str:
        return os.getenv(
            "ORCHESTRATOR_ADDRESS",
            "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
        )
```

## ✅ **Resultado**

- **Code Smell Eliminado**: Sin `os.getenv` directo
- **Arquitectura Hexagonal**: Dependencias inyectadas correctamente
- **Testabilidad**: Fácil mocking para tests
- **Flexibilidad**: Múltiples fuentes de configuración posibles
- **Mantenibilidad**: Cambios de configuración centralizados
