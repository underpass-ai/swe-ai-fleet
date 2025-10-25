# Security Strategy: Internal vs External Communication

## 🔒 **Estrategia de Seguridad del Proyecto**

### **Decisión Arquitectónica: TLS por Capas**

El proyecto SWE AI Fleet implementa una **estrategia de seguridad por capas** donde:

- **✅ Servicios Internos**: Comunicación sin TLS (ClusterIP)
- **✅ Servicios Externos**: TLS completo (Ingress + cert-manager)

## 📊 **Comparación de Enfoques**

### **Enfoque Actual (Recomendado) ✅**

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS/TLS (Let's Encrypt)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Ingress Controller                         │
│              (nginx + cert-manager)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP (internal)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes Cluster (swe-ai-fleet)             │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Gateway   │◄──►│ Orchestrator│◄──►│   Context   │     │
│  │  (ClusterIP)│    │  (ClusterIP)│    │  (ClusterIP)│     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Planning  │◄──►│ StoryCoach │◄──►│  Workspace  │     │
│  │  (ClusterIP)│    │  (ClusterIP)│    │  (ClusterIP)│     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**Ventajas:**
- ✅ **Simplicidad**: No gestión de certificados internos
- ✅ **Performance**: Menos overhead de encriptación
- ✅ **Mantenimiento**: Certificados solo en Ingress
- ✅ **Seguridad**: Red privada de Kubernetes
- ✅ **Escalabilidad**: Fácil agregar servicios internos

### **Enfoque Alternativo (TLS Everywhere) ❌**

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS/TLS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Ingress Controller                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS/TLS (cert-manager)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes Cluster (swe-ai-fleet)             │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Gateway   │◄──►│ Orchestrator│◄──►│   Context   │     │
│  │  (TLS cert) │    │  (TLS cert) │    │  (TLS cert) │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**Desventajas:**
- ❌ **Complejidad**: Gestión de certificados para cada servicio
- ❌ **Performance**: Overhead de TLS en cada comunicación
- ❌ **Mantenimiento**: Rotación de certificados compleja
- ❌ **Debugging**: Más difícil diagnosticar problemas
- ❌ **Recursos**: CPU adicional para encriptación

## 🎯 **Justificación Técnica**

### **1. Modelo de Confianza**
```
Internet (No confiable) → Ingress TLS → Cluster (Confiable)
```

- **Internet**: Requiere TLS (cert-manager + Let's Encrypt)
- **Cluster**: Red privada, pods confiables, NetworkPolicy

### **2. Principio de Menor Privilegio**
- **Servicios internos**: Solo necesitan comunicación dentro del cluster
- **Servicios externos**: Expuestos vía Ingress con TLS

### **3. Separación de Responsabilidades**
- **Ingress**: Maneja TLS, autenticación, rate limiting
- **Microservicios**: Se enfocan en lógica de negocio

## 📋 **Implementación en Código**

### **Adapter gRPC (Correcto)**
```python
def __init__(self, orchestrator_address: str):
    """Initialize gRPC orchestrator query adapter.
    
    Note:
        Uses insecure_channel for internal cluster communication.
        TLS is handled at the Ingress level for external services.
        See: docs/microservices/ORCHESTRATOR_INTERACTIONS.md#security-considerations
    """
    self.orchestrator_address = orchestrator_address
    # Internal cluster communication - TLS handled at Ingress level
    self.channel = grpc.aio.insecure_channel(self.orchestrator_address)
```

### **Configuración Kubernetes**
```yaml
# Servicios internos (ClusterIP)
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
spec:
  type: ClusterIP  # ✅ Solo accesible dentro del cluster
  ports:
  - port: 50055
    targetPort: 50055

---
# Servicios externos (Ingress + TLS)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod-r53"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - gateway.underpassai.com
    secretName: gateway-tls
```

## 🔍 **Verificación de Seguridad**

### **1. NetworkPolicy (Opcional)**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: swe-ai-fleet-internal
spec:
  podSelector:
    matchLabels:
      app: orchestrator
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: gateway
    - podSelector:
        matchLabels:
          app: monitoring
```

### **2. Service Mesh (Futuro)**
Si en el futuro se requiere TLS interno:
- **Istio**: mTLS automático entre pods
- **Linkerd**: TLS transparente
- **Consul Connect**: Service mesh con TLS

## ✅ **Conclusión**

La estrategia actual es **correcta y recomendada** para:

1. **✅ Simplicidad**: Menos complejidad operacional
2. **✅ Performance**: Menos overhead de encriptación
3. **✅ Seguridad**: TLS donde es necesario (Ingress)
4. **✅ Mantenibilidad**: Certificados centralizados
5. **✅ Escalabilidad**: Fácil agregar servicios internos

**Referencia**: `docs/microservices/ORCHESTRATOR_INTERACTIONS.md#security-considerations`
