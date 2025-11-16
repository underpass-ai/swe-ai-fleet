# Kubernetes Cluster State — 2025-10-30

This document captures the current state of the production Kubernetes cluster as observed on 2025-10-30.

## Control Plane & Nodes
- Topology: single control-plane node (`wrx80-node1`) with worker responsibilities
- Operating system: Arch Linux 6.17.5-arch1-1
- Kubernetes version: v1.34.1
- GPU capabilities: 4× NVIDIA RTX 3090 with NVIDIA GPU Operator v25.3.4 (time-slicing enabled, 8 virtual GPUs exposed)
- Container runtime: CRI-O/Podman stack; workloads pull from `registry.underpassai.com`
- Networking & ingress:
  - Calico CNI (calico-apiserver, tigera-operator namespaces)
  - MetalLB provides LoadBalancer services (metallb-system namespace)
  - `ingress-nginx` exposes HTTPS endpoints
  - TLS automation via cert-manager with Route53 DNS-01 challenge

## Core Infrastructure Services
- Messaging: NATS 2.10-alpine with JetStream in `swe-ai-fleet`
- Data stores:
  - Neo4j 5.14 (in `swe-ai-fleet`)
  - Valkey 8.0-alpine (Redis-compatible, in `swe-ai-fleet`)
- Compute: Ray cluster (`ray` namespace) with GPU workers managed by KubeRay operator (`ray-system`)
- Model serving: vLLM deployment (`llm` namespace) referenced by orchestrator agents
- Monitoring stack being refactored (`monitoring` namespace) with open issues on stream subscriptions

## Namespaces Snapshot
Extracted via `kubectl get ns` on the cluster.

| Namespace           | Status | Age  | Notes |
|---------------------|--------|------|-------|
| calico-apiserver    | Active | 29d | Calico API server for networking control-plane |
| calico-system       | Active | 29d | Calico data plane components |
| cert-manager        | Active | 29d | Cluster-wide certificate automation |
| container-registry  | Active | 23d | Internal registry (`registry.underpassai.com`) |
| default             | Active | 29d | Default namespace |
| gpu-operator        | Active | 28d | NVIDIA GPU Operator controllers |
| ingress-nginx       | Active | 29d | Public ingress controller |
| kube-node-lease     | Active | 29d | Node heartbeat leases |
| kube-public         | Active | 29d | Public configmaps (cluster info) |
| kube-system         | Active | 29d | Core Kubernetes system components |
| llm                 | Active | 27d | vLLM model serving workloads |
| llm-ui              | Active | 26d | UI components for LLM tooling |
| local-path-storage  | Active | 27d | Local path provisioner for dynamic PVs |
| logging             | Active | 21h | Centralized logging stack (recent rollout) |
| metallb-system      | Active | 29d | MetalLB load balancer controllers |
| monitoring          | Active | 21h | Monitoring dashboard refactor (v2.0.0 image) |
| nvidia              | Active | 28d | NVIDIA device plugin/time-slicing configs |
| ray                 | Active | 26d | Ray GPU workloads (agent execution) |
| ray-system          | Active | 26d | KubeRay operator managing Ray clusters |
| swe-ai-fleet        | Active | 23d | Application microservices (Planning, StoryCoach, Workspace, Orchestrator, etc.) |
| tigera-operator     | Active | 29d | Calico/Tigera operator controllers |

## Operational Highlights
- Monitoring dashboard pods currently fail to subscribe to `agent.results.>` and `vllm.streaming.>` JetStream streams; corrective actions pending.
- Logging stack freshly deployed (`logging` namespace) — verify log shipping once monitoring updates land.
- Ray GPU workers and vLLM endpoints are the primary dependencies for agent orchestration E2E tests and jobs.

## Active Kubernetes Jobs

| Namespace     | Job Name           | Status | Completions | Duration | Age |
|---------------|--------------------|--------|-------------|----------|-----|
| swe-ai-fleet  | test-ray-vllm-e2e  | Failed | 0/1         | 25m      | 25m |

The `test-ray-vllm-e2e` job corresponds to the in-cluster end-to-end suite for orchestrator + Ray + vLLM integration. Current failure indicates the job needs triage (likely due to missing councils before the recent fixture fix or dependent services not being ready).

## Namespace Resource Inventory

For each namespace the tables below capture the services, deployments, configmaps, and secrets currently present in the cluster (snapshot time: 2025-10-30).

### Namespace: calico-apiserver
- **Services:** `calico-api`
- **Deployments:** `calico-apiserver`
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `calico-apiserver-certs`

### Namespace: calico-system
- **Services:** `calico-kube-controllers-metrics`, `calico-typha`
- **Deployments:** `calico-kube-controllers`, `calico-typha`
- **ConfigMaps:** `active-operator`, `cni-config`, `kube-root-ca.crt`, `tigera-ca-bundle`
- **Secrets:** `node-certs`, `typha-certs`, `typha-certs-noncluster-host`

### Namespace: cert-manager
- **Services:** `cert-manager`, `cert-manager-cainjector`, `cert-manager-webhook`
- **Deployments:** `cert-manager`, `cert-manager-cainjector`, `cert-manager-webhook`
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `cert-manager-webhook-ca`, `letsencrypt-prod-account-key`, `letsencrypt-staging-account-key`, `prod-route53-credentials-secret`, `sh.helm.release.v1.cert-manager.v1`

### Namespace: container-registry
- **Services:** `docker-registry`
- **Deployments:** `docker-registry`
- **ConfigMaps:** `kube-root-ca.crt`, `registry-config`
- **Secrets:** `registry-tls`

### Namespace: default
- **Services:** `echo`, `kubernetes`
- **Deployments:** `echo`
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `echo-tls-prod`, `wildcard-underpassai-tls`

### Namespace: gpu-operator
- **Services:** _none_
- **Deployments:** _none_
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** _none_

### Namespace: ingress-nginx
- **Services:** `ingress-nginx-controller`, `ingress-nginx-controller-admission`
- **Deployments:** `ingress-nginx-controller`
- **ConfigMaps:** `ingress-nginx-controller`, `kube-root-ca.crt`
- **Secrets:** `ingress-nginx-admission`, `sh.helm.release.v1.ingress-nginx.v1`, `sh.helm.release.v1.ingress-nginx.v2`, `sh.helm.release.v1.ingress-nginx.v3`

### Namespace: kube-node-lease
- **Services:** _none_
- **Deployments:** _none_
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** _none_

### Namespace: kube-public
- **Services:** _none_
- **Deployments:** _none_
- **ConfigMaps:** `cluster-info`, `kube-root-ca.crt`
- **Secrets:** _none_

### Namespace: kube-system
- **Services:** `kube-dns`, `kube-prometheus-stack-coredns`, `kube-prometheus-stack-kube-controller-manager`, `kube-prometheus-stack-kube-etcd`, `kube-prometheus-stack-kube-proxy`, `kube-prometheus-stack-kube-scheduler`, `kube-prometheus-stack-kubelet`
- **Deployments:** `coredns`
- **ConfigMaps:** `coredns`, `extension-apiserver-authentication`, `kube-apiserver-legacy-service-account-token-tracking`, `kube-proxy`, `kube-root-ca.crt`, `kubeadm-config`, `kubelet-config`
- **Secrets:** _none_

### Namespace: llm
- **Services:** `open-webui`, `open-webui-ollama`, `open-webui-pipelines`, `vllm-qwen3-32b`
- **Deployments:** `open-webui-ollama`, `open-webui-pipelines`, `vllm-qwen3-32b`
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `hf-token`, `openwebui-tls`, `sh.helm.release.v1.openwebui.v2`, `sh.helm.release.v1.openwebui.v3`, `sh.helm.release.v1.openwebui.v4`, `sh.helm.release.v1.openwebui.v5`, `sh.helm.release.v1.openwebui.v6`, `sh.helm.release.v1.openwebui.v7`, `sh.helm.release.v1.openwebui.v8`, `sh.helm.release.v1.openwebui.v9`, `sh.helm.release.v1.openwebui.v10`, `sh.helm.release.v1.openwebui.v11`

### Namespace: llm-ui
- **Services:** _none_
- **Deployments:** _none_
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** _none_

### Namespace: local-path-storage
- **Services:** _none_
- **Deployments:** `local-path-provisioner`
- **ConfigMaps:** `kube-root-ca.crt`, `local-path-config`
- **Secrets:** _none_

### Namespace: logging
- **Services:** _none_
- **Deployments:** _none_
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `promtail`, `sh.helm.release.v1.promtail.v1`, `sh.helm.release.v1.promtail.v2`, `sh.helm.release.v1.promtail.v3`

### Namespace: metallb-system
- **Services:** `metallb-webhook-service`
- **Deployments:** `controller`
- **ConfigMaps:** `kube-root-ca.crt`, `metallb-excludel2`
- **Secrets:** `memberlist`, `metallb-webhook-cert`

### Namespace: monitoring
- **Services:** `alertmanager-operated`, `kube-prometheus-stack-alertmanager`, `kube-prometheus-stack-kube-state-metrics`, `kube-prometheus-stack-operator`, `kube-prometheus-stack-prometheus`, `kube-prometheus-stack-prometheus-node-exporter`, `prometheus-operated`
- **Deployments:** `kube-prometheus-stack-kube-state-metrics`, `kube-prometheus-stack-operator`
- **ConfigMaps:** `kube-root-ca.crt`, `prometheus-kube-prometheus-stack-prometheus-rulefiles-0`
- **Secrets:** `alertmanager-kube-prometheus-stack-alertmanager`, `alertmanager-kube-prometheus-stack-alertmanager-cluster-tls-config`, `alertmanager-kube-prometheus-stack-alertmanager-generated`, `alertmanager-kube-prometheus-stack-alertmanager-tls-assets-0`, `alertmanager-kube-prometheus-stack-alertmanager-web-config`, `kube-prometheus-stack-admission`, `prometheus-kube-prometheus-stack-prometheus`, `prometheus-kube-prometheus-stack-prometheus-thanos-prometheus-http-client-file`, `prometheus-kube-prometheus-stack-prometheus-tls-assets-0`, `prometheus-kube-prometheus-stack-prometheus-web-config`, `sh.helm.release.v1.kube-prometheus-stack.v1`

### Namespace: nvidia
- **Services:** `gpu-operator`, `nvidia-dcgm-exporter`
- **Deployments:** `gpu-operator`, `gpu-operator-node-feature-discovery-gc`, `gpu-operator-node-feature-discovery-master`
- **ConfigMaps:** `default-gpu-clients`, `default-mig-parted-config`, `gpu-operator-node-feature-discovery-master-conf`, `gpu-operator-node-feature-discovery-worker-conf`, `kube-root-ca.crt`, `nvidia-container-toolkit-entrypoint`, `nvidia-device-plugin-entrypoint`, `nvidia-mig-manager-entrypoint`, `time-slicing-config`
- **Secrets:** `sh.helm.release.v1.gpu-operator.v1`

### Namespace: ray-system
- **Services:** `kuberay-operator`
- **Deployments:** `kuberay-operator`
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `sh.helm.release.v1.kuberay-operator.v1`

### Namespace: ray
- **Services:** `ray-gpu-head-svc`
- **Deployments:** _none_
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** _none_

### Namespace: swe-ai-fleet
- **Services:** `context`, `grafana`, `internal-context`, `internal-nats`, `internal-neo4j`, `internal-planning`, `internal-registry`, `internal-storycoach`, `internal-valkey`, `internal-workspace`, `loki`, `monitoring`, `monitoring-dashboard`, `nats`, `neo4j`, `orchestrator`, `planning`, `po-ui`, `ray-executor`, `redis`, `storycoach`, `valkey`, `vllm-server-service`, `workspace`
- **Deployments:** `context`, `grafana`, `loki`, `monitoring-dashboard`, `orchestrator`, `planning`, `po-ui`, `ray-executor`, `storycoach`, `vllm-server`, `workspace`
- **ConfigMaps:** `app-config`, `fleet-config`, `kube-root-ca.crt`, `loki-config`, `orchestrator-config`, `service-urls`
- **Secrets:** `grafana-admin`, `grafana-tls`, `huggingface-token`, `monitoring-dashboard-tls`, `monitoring-tls`, `nats-tls`, `neo4j-auth`, `po-ui-tls`

### Namespace: tigera-operator
- **Services:** _none_
- **Deployments:** `tigera-operator`
- **ConfigMaps:** `kube-root-ca.crt`
- **Secrets:** `calico-apiserver-certs`, `node-certs`, `tigera-ca-private`, `typha-certs`, `typha-certs-noncluster-host`


