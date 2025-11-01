#!/bin/bash
#
# Generate grpcui deployments for all gRPC services
#
# Creates Kubernetes deployments, services, and ingresses for each service
# to provide interactive testing UI like Swagger for REST APIs.
#
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICES=(
    "context:50054"
    "orchestrator:50055"
    "planning:50051"
    "storycoach:50052"
    "workspace:50053"
    "ray_executor:50056"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/deploy/k8s"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Generate grpcui Deployments for All Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

for service_port in "${SERVICES[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    
    echo -e "${BLUE}Generating manifests for: $service${NC}"
    
    # Create deployment
    cat > "${DEPLOY_DIR}/14d-grpcui-${service}-deployment.yaml" << EOF
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grpcui-${service}
  namespace: swe-ai-fleet
  labels:
    app: grpcui-${service}
    component: interactive-testing
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grpcui-${service}
  template:
    metadata:
      labels:
        app: grpcui-${service}
        component: interactive-testing
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/"
    spec:
      automountServiceAccountToken: false
      containers:
      - name: grpcui
        image: registry.underpassai.com/swe-fleet/grpcui-server:latest
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        env:
        - name: GRPCUI_PORT
          value: "8080"
        - name: GRPCUI_TARGET
          value: "${service}.swe-ai-fleet.svc.cluster.local:${port}"
        - name: GRPCUI_SERVICE
          value: "${service}"
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 2
          failureThreshold: 2
      restartPolicy: Always

EOF

    # Create service
    cat > "${DEPLOY_DIR}/14e-grpcui-${service}-service.yaml" << EOF
---
apiVersion: v1
kind: Service
metadata:
  name: grpcui-${service}
  namespace: swe-ai-fleet
  labels:
    app: grpcui-${service}
    component: interactive-testing
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
  selector:
    app: grpcui-${service}

EOF

    # Create ingress
    cat > "${DEPLOY_DIR}/14f-grpcui-${service}-ingress.yaml" << EOF
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grpcui-${service}-ingress
  namespace: swe-ai-fleet
  labels:
    app: grpcui-${service}
    component: interactive-testing
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod-r53
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - grpcui-${service}.underpassai.com
    secretName: grpcui-${service}-tls
  rules:
  - host: grpcui-${service}.underpassai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grpcui-${service}
            port:
              number: 80

EOF

    echo -e "${GREEN}✓ Generated manifests for ${service}${NC}"
done

echo ""
echo -e "${GREEN}✓ All manifests generated${NC}"
echo ""
echo "Generated files:"
for service_port in "${SERVICES[@]}"; do
    IFS=':' read -r service <<< "$service_port"
    echo "  - 14d-grpcui-${service}-deployment.yaml"
    echo "  - 14e-grpcui-${service}-service.yaml"
    echo "  - 14f-grpcui-${service}-ingress.yaml"
done
echo ""
echo "Total: $(( ${#SERVICES[@]} * 3 )) files"

