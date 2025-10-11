# vLLM Agent Deployment Guide

This guide explains how to deploy and configure vLLM agents in the SWE AI Fleet system.

## 🎯 Overview

The vLLM Agent integration allows the Orchestrator Service to use real language models instead of mock agents for production workloads. This integration leverages the existing `models/` bounded context and provides multiple deployment options.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Orchestrator    │    │ vLLM Server      │    │ Model Profiles  │
│ Service         │◄──►│ (OpenAI Compat)  │◄──►│ (YAML Config)   │
│                 │    │                  │    │                 │
│ - CreateCouncil │    │ - Chat Completions│    │ - developer.yaml│
│ - RegisterAgent │    │ - Model Loading   │    │ - qa.yaml       │
│ - Deliberate    │    │ - GPU Management  │    │ - architect.yaml│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Deploy vLLM Server

#### Option A: Docker Compose (Recommended for Development)

```yaml
# docker-compose.vllm.yml
version: '3.8'
services:
  vllm-server:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    environment:
      - MODEL_NAME=deepseek-ai/deepseek-coder-6.7b-instruct
      - HOST=0.0.0.0
      - PORT=8000
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

```bash
# Start vLLM server
docker-compose -f docker-compose.vllm.yml up -d

# Verify server is running
curl http://localhost:8000/v1/models
```

#### Option B: Kubernetes Deployment

```yaml
# deploy/k8s/vllm-server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-server
  namespace: swe-ai-fleet
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-server
  template:
    metadata:
      labels:
        app: vllm-server
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_NAME
          value: "deepseek-ai/deepseek-coder-6.7b-instruct"
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        resources:
          requests:
            nvidia.com/gpu: 1
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
        - name: huggingface-cache
          mountPath: /root/.cache/huggingface
      volumes:
      - name: huggingface-cache
        persistentVolumeClaim:
          claimName: huggingface-cache-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: vllm-server-service
  namespace: swe-ai-fleet
spec:
  selector:
    app: vllm-server
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: huggingface-cache-pvc
  namespace: swe-ai-fleet
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
```

### 2. Configure Orchestrator Service

#### Environment Variables

```bash
# Set agent type to use vLLM
export AGENT_TYPE=vllm

# vLLM server configuration
export VLLM_URL=http://vllm-server-service:8000
export VLLM_MODEL=deepseek-ai/deepseek-coder-6.7b-instruct
export VLLM_TEMPERATURE=0.7
export VLLM_MAX_TOKENS=2048
export VLLM_TIMEOUT=30
```

#### Alternative: Use models/ bounded context

```bash
# Use the unified models/ bounded context
export AGENT_TYPE=model
export LLM_BACKEND=vllm
export VLLM_ENDPOINT=http://vllm-server-service:8000/v1
export VLLM_MODEL=deepseek-ai/deepseek-coder-6.7b-instruct
```

### 3. Deploy Updated Orchestrator Service

```bash
# Build and push new image
docker build -t registry.underpassai.com/swe-fleet/orchestrator:v0.4.0 \
  -f services/orchestrator/Dockerfile .

docker push registry.underpassai.com/swe-fleet/orchestrator:v0.4.0

# Update Kubernetes deployment
kubectl set image deployment/orchestrator-service \
  orchestrator=registry.underpassai.com/swe-fleet/orchestrator:v0.4.0 \
  -n swe-ai-fleet
```

## 🔧 Configuration Options

### Model Profiles

Configure different models for different roles using YAML profiles:

```yaml
# profiles/developer.yaml
name: "developer"
model: "deepseek-ai/deepseek-coder-6.7b-instruct"
context_window: 32768
temperature: 0.7
max_tokens: 4096

# profiles/architect.yaml
name: "architect"
model: "databricks/dbrx-instruct"
context_window: 128000
temperature: 0.3  # Lower temperature for precise decisions
max_tokens: 8192
```

### API Configuration

#### CreateCouncil with vLLM Agents

```python
# Using gRPC client
request = CreateCouncilRequest(
    role="DEV",
    num_agents=3,
    config=CouncilConfig(
        custom_params={
            "agent_type": "vllm",
            "vllm_url": "http://vllm-server:8000",
            "model": "deepseek-ai/deepseek-coder-6.7b-instruct",
            "temperature": "0.7"
        }
    )
)

response = orchestrator_stub.CreateCouncil(request)
```

#### RegisterAgent with vLLM

```python
# Register a new vLLM agent
request = RegisterAgentRequest(
    agent_id="agent-dev-004",
    role="DEV",
    capabilities=AgentCapabilities(
        supported_tasks=["coding", "testing", "documentation"],
        model_profile="vllm-coder"
    ),
    metadata={
        "agent_type": "vllm",
        "vllm_url": "http://vllm-server:8000",
        "model": "deepseek-ai/deepseek-coder-6.7b-instruct"
    }
)

response = orchestrator_stub.RegisterAgent(request)
```

## 📊 Monitoring and Observability

### Health Checks

```bash
# Check vLLM server health
curl http://localhost:8000/health

# Check Orchestrator Service health
kubectl exec -it deployment/orchestrator-service -n swe-ai-fleet -- \
  grpcurl -plaintext localhost:50055 orchestrator.v1.OrchestratorService/GetStatus
```

### Logs

```bash
# vLLM server logs
docker logs vllm-server
# or
kubectl logs deployment/vllm-server -n swe-ai-fleet

# Orchestrator Service logs
kubectl logs deployment/orchestrator-service -n swe-ai-fleet -f
```

### Metrics

The Orchestrator Service exposes metrics for:
- Agent response times
- Model inference latency
- Error rates by agent type
- Council utilization

```bash
# Get metrics
kubectl exec -it deployment/orchestrator-service -n swe-ai-fleet -- \
  grpcurl -plaintext localhost:50055 orchestrator.v1.OrchestratorService/GetMetrics
```

## 🔄 Migration from Mock Agents

### Step 1: Test with Single Council

```bash
# Create a test council with vLLM agents
export AGENT_TYPE=vllm
kubectl apply -f deploy/k8s/orchestrator-service.yaml

# Test deliberation
grpcurl -plaintext -d '{
  "task_description": "Implement user authentication",
  "role": "DEV",
  "constraints": {
    "rubric": "security: Secure implementation\ntesting: Comprehensive tests",
    "requirements": ["JWT tokens", "Password hashing", "Input validation"]
  }
}' orchestrator-service.swe-ai-fleet.svc.cluster.local:50055 \
  orchestrator.v1.OrchestratorService/Deliberate
```

### Step 2: Gradual Rollout

```bash
# Create councils for different roles
for role in DEV QA ARCHITECT DEVOPS DATA; do
  grpcurl -plaintext -d "{
    \"role\": \"$role\",
    \"num_agents\": 3,
    \"config\": {
      \"custom_params\": {
        \"agent_type\": \"vllm\"
      }
    }
  }" orchestrator-service.swe-ai-fleet.svc.cluster.local:50055 \
    orchestrator.v1.OrchestratorService/CreateCouncil
done
```

### Step 3: Monitor Performance

```bash
# Check council status
grpcurl -plaintext orchestrator-service.swe-ai-fleet.svc.cluster.local:50055 \
  orchestrator.v1.OrchestratorService/ListCouncils

# Monitor metrics
kubectl exec -it deployment/orchestrator-service -n swe-ai-fleet -- \
  grpcurl -plaintext localhost:50055 orchestrator.v1.OrchestratorService/GetMetrics
```

## 🐛 Troubleshooting

### Common Issues

#### 1. vLLM Server Not Accessible

```bash
# Check if vLLM server is running
kubectl get pods -n swe-ai-fleet -l app=vllm-server

# Check service endpoints
kubectl get svc -n swe-ai-fleet vllm-server-service

# Test connectivity from orchestrator pod
kubectl exec -it deployment/orchestrator-service -n swe-ai-fleet -- \
  curl -s http://vllm-server-service:8000/v1/models
```

#### 2. Model Loading Failures

```bash
# Check vLLM server logs for model loading errors
kubectl logs deployment/vllm-server -n swe-ai-fleet

# Verify model name is correct
curl http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000/v1/models
```

#### 3. Agent Creation Failures

```bash
# Check orchestrator logs
kubectl logs deployment/orchestrator-service -n swe-ai-fleet | grep -i "createcouncil\|error"

# Verify environment variables
kubectl exec -it deployment/orchestrator-service -n swe-ai-fleet -- env | grep -E "(AGENT_TYPE|VLLM_)"
```

#### 4. Performance Issues

```bash
# Check GPU utilization
kubectl exec -it deployment/vllm-server -n swe-ai-fleet -- nvidia-smi

# Check memory usage
kubectl top pods -n swe-ai-fleet

# Monitor response times
kubectl exec -it deployment/orchestrator-service -n swe-ai-fleet -- \
  grpcurl -plaintext localhost:50055 orchestrator.v1.OrchestratorService/GetMetrics
```

### Fallback to Mock Agents

If vLLM agents fail, you can quickly fallback to mock agents:

```bash
# Update environment to use mock agents
kubectl set env deployment/orchestrator-service AGENT_TYPE=mock -n swe-ai-fleet

# Restart orchestrator service
kubectl rollout restart deployment/orchestrator-service -n swe-ai-fleet
```

## 📈 Performance Tuning

### GPU Optimization

```yaml
# vllm-server.yaml - Optimized configuration
env:
- name: CUDA_VISIBLE_DEVICES
  value: "0"
- name: VLLM_ATTENTION_BACKEND
  value: "FLASHINFER"  # or "FLASH_ATTN"
- name: VLLM_USE_MODELSCOPE
  value: "False"
- name: VLLM_WORKER_MULTIPROC_METHOD
  value: "spawn"
```

### Model Configuration

```yaml
# Optimize for throughput vs latency
env:
- name: VLLM_MAX_MODEL_LEN
  value: "32768"
- name: VLLM_GPU_MEMORY_UTILIZATION
  value: "0.9"
- name: VLLM_MAX_NUM_BATCHED_TOKENS
  value: "8192"
```

### Orchestrator Tuning

```yaml
# orchestrator-service.yaml
env:
- name: VLLM_TIMEOUT
  value: "60"  # Increase timeout for large models
- name: VLLM_MAX_TOKENS
  value: "4096"  # Adjust based on model capabilities
```

## 🔒 Security Considerations

### Network Security

```yaml
# NetworkPolicy for vLLM server
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-server-netpol
  namespace: swe-ai-fleet
spec:
  podSelector:
    matchLabels:
      app: vllm-server
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: swe-ai-fleet
    ports:
    - protocol: TCP
      port: 8000
```

### Model Security

- Use trusted model repositories (Hugging Face, official model providers)
- Verify model checksums before deployment
- Consider model quantization for reduced attack surface
- Monitor model inference for anomalous outputs

## 📚 Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [OpenAI Compatible API](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [Model Profiles Configuration](../models/profiles/)
- [Orchestrator Service API](../microservices/ORCHESTRATOR_SERVICE.md)
