# Deployment Guide

This guide covers deploying SWE AI Fleet in various environments, from local development to production cloud deployments.

## 🚀 Deployment Options

### 1. Local Development
- **Single machine** with Docker containers
- **kind cluster** for Kubernetes simulation
- **Direct Python installation**

### 2. Production Deployment
- **Kubernetes cluster** (on-premises or cloud)
- **Docker Compose** for simple deployments
- **Helm charts** for Kubernetes

## 🏠 Local Development Setup

### Prerequisites
```bash
# Install required tools
pip install -e .
docker --version
kind version
kubectl version
helm version
```

### Quick Start Script
```bash
# Use the provided script
./scripts/start_local_stack.sh

# Or manually start services
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:5
kind create cluster --name swe-ai-fleet
```

## ☁️ Production Deployment

### Kubernetes Deployment

#### 1. Install Helm Charts
```bash
# Add the repository
helm repo add swe-ai-fleet https://charts.swe-ai-fleet.com

# Install the main chart
helm install swe-ai-fleet swe-ai-fleet/swe-ai-fleet \
  --namespace swe-ai-fleet \
  --create-namespace \
  --values values.yaml
```

#### 2. Configuration Values
```yaml
# values.yaml
agents:
  developer:
    replicas: 3
    resources:
      requests:
        memory: "2Gi"
        cpu: "1"
      limits:
        memory: "4Gi"
        cpu: "2"
  
  devops:
    replicas: 2
    resources:
      requests:
        memory: "4Gi"
        cpu: "2"

memory:
  redis:
    enabled: true
    persistence:
      enabled: true
      size: "10Gi"
  
  neo4j:
    enabled: true
    persistence:
      enabled: true
      size: "20Gi"

orchestrator:
  replicas: 2
  resources:
    requests:
      memory: "1Gi"
      cpu: "0.5"
```

### Docker Compose Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_apoc_export_file_enabled: "true"
    volumes:
      - neo4j_data:/data
    restart: unless-stopped

  swe-ai-fleet:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
    depends_on:
      - redis
      - neo4j
    restart: unless-stopped

volumes:
  redis_data:
  neo4j_data:
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Core Configuration
SWE_AI_FLEET_ENV=production
SWE_AI_FLEET_LOG_LEVEL=INFO
SWE_AI_FLEET_SECRET_KEY=your-secret-key

# Memory Configuration
REDIS_HOST=redis-service
REDIS_PORT=6379
NEO4J_URI=bolt://neo4j-service:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure-password

# Ray Configuration
RAY_HEAD_HOST=ray-head-service
RAY_HEAD_PORT=10001
```

### Configuration Files
```yaml
# config/production.yaml
agents:
  developer:
    max_instances: 10
    memory_limit: "4Gi"
    cpu_limit: "2"
  
  devops:
    max_instances: 5
    memory_limit: "8Gi"
    cpu_limit: "4"

security:
  allowed_hosts: ["your-domain.com"]
  cors_origins: ["https://your-domain.com"]
  rate_limiting:
    enabled: true
    requests_per_minute: 100

monitoring:
  prometheus:
    enabled: true
    port: 9090
  grafana:
    enabled: true
    port: 3000
```

## 📊 Monitoring and Observability

### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'swe-ai-fleet'
    static_configs:
      - targets: ['swe-ai-fleet:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Grafana Dashboards
```json
{
  "dashboard": {
    "title": "SWE AI Fleet Metrics",
    "panels": [
      {
        "title": "Active Agents",
        "type": "stat",
        "targets": [
          {
            "expr": "swe_ai_fleet_active_agents_total"
          }
        ]
      },
      {
        "title": "Task Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(swe_ai_fleet_tasks_completed_total[5m])"
          }
        ]
      }
    ]
  }
}
```

## 🔒 Security Configuration

### Network Policies
```yaml
# security/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: swe-ai-fleet-network-policy
spec:
  podSelector:
    matchLabels:
      app: swe-ai-fleet
  
  policyTypes:
    - Ingress
    - Egress
  
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: swe-ai-fleet
      ports:
        - protocol: TCP
          port: 6379
        - protocol: TCP
          port: 7687
```

### RBAC Configuration
```yaml
# security/rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: swe-ai-fleet-role
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: swe-ai-fleet-binding
subjects:
  - kind: ServiceAccount
    name: swe-ai-fleet
    namespace: swe-ai-fleet
roleRef:
  kind: ClusterRole
  name: swe-ai-fleet-role
  apiGroup: rbac.authorization.k8s.io
```

## 🚀 Scaling and Performance

### Horizontal Pod Autoscaler
```yaml
# scaling/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: swe-ai-fleet-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: swe-ai-fleet
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Resource Quotas
```yaml
# scaling/resource-quotas.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: swe-ai-fleet-quota
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    persistentvolumeclaims: "10"
```

## 🔄 Backup and Recovery

### Backup Strategy
```bash
#!/bin/bash
# scripts/backup.sh

# Backup Redis
redis-cli --rdb /backup/redis-$(date +%Y%m%d-%H%M%S).rdb

# Backup Neo4j
neo4j-admin database backup neo4j --to-path=/backup/neo4j-$(date +%Y%m%d-%H%M%S)

# Backup configuration
tar -czf /backup/config-$(date +%Y%m%d-%H%M%S).tar.gz /etc/swe-ai-fleet/
```

### Recovery Procedures
```bash
#!/bin/bash
# scripts/recovery.sh

# Restore Redis
redis-cli --rdb /backup/redis-latest.rdb

# Restore Neo4j
neo4j-admin database restore neo4j --from-path=/backup/neo4j-latest

# Restart services
kubectl rollout restart deployment/swe-ai-fleet
```

## 🧪 Testing Deployment

### Health Checks
```bash
# Check service health
curl -f http://localhost:8000/health

# Check Redis connection
redis-cli ping

# Check Neo4j connection
curl -u neo4j:password http://localhost:7474/browser/

# Check Kubernetes resources
kubectl get pods -n swe-ai-fleet
kubectl get services -n swe-ai-fleet
```

### Load Testing
```bash
# Install load testing tool
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Pod Startup Failures
```bash
# Check pod logs
kubectl logs -n swe-ai-fleet deployment/swe-ai-fleet

# Check pod events
kubectl describe pod -n swe-ai-fleet <pod-name>

# Check resource usage
kubectl top pods -n swe-ai-fleet
```

#### 2. Memory Issues
```bash
# Check Redis memory usage
redis-cli info memory

# Check Neo4j memory usage
curl -u neo4j:password http://localhost:7474/browser/

# Check Kubernetes resource limits
kubectl describe nodes | grep -A 5 "Allocated resources"
```

#### 3. Network Connectivity
```bash
# Test service connectivity
kubectl run test-pod --image=busybox --rm -it --restart=Never -- nslookup swe-ai-fleet-service

# Check network policies
kubectl get networkpolicies -n swe-ai-fleet

# Test port connectivity
telnet swe-ai-fleet-service 8000
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

---

*This deployment guide covers the essential aspects of deploying SWE AI Fleet. For specific environment requirements or advanced configurations, refer to the architecture documentation or contact the development team.*