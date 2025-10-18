#!/bin/bash
# Monitor Ray Jobs - Tiempo real
# Monitorea RayJobs, RayCluster, y workers de KubeRay

NAMESPACE="swe-ai-fleet"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║            MONITOR: KubeRay Jobs en Tiempo Real                  ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar estado inicial del cluster
echo "🔍 ESTADO INICIAL DEL CLUSTER RAY:"
echo "═══════════════════════════════════════════════════════════════════"

RAY_CLUSTER=$(kubectl get raycluster -n $NAMESPACE -o name 2>/dev/null | wc -l)
if [ "$RAY_CLUSTER" -eq 0 ]; then
    echo "⚠️  NO HAY RAYCLUSTER DESPLEGADO"
    echo ""
    echo "Para desplegar Ray cluster:"
    echo "  kubectl apply -f deploy/k8s/09-kuberay-cluster.yaml"
    echo ""
else
    echo "✅ RayCluster desplegado:"
    kubectl get raycluster -n $NAMESPACE -o wide
fi

echo ""
echo "Ray Head:"
kubectl get pods -n $NAMESPACE -l ray.io/node-type=head -o wide 2>/dev/null || echo "  No head pods"

echo ""
echo "Ray Workers:"
kubectl get pods -n $NAMESPACE -l ray.io/node-type=worker -o wide 2>/dev/null || echo "  No worker pods"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📊 MONITOREO CONTINUO (Ctrl+C para salir)"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Contadores
TOTAL_JOBS=0
LAST_JOB_COUNT=0

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Count actual de jobs
    CURRENT_JOB_COUNT=$(kubectl get rayjobs -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    
    # Si hay cambios, mostrar info completa
    if [ "$CURRENT_JOB_COUNT" -ne "$LAST_JOB_COUNT" ]; then
        echo ""
        echo "[$TIMESTAMP] 🔄 CAMBIO DETECTADO: $LAST_JOB_COUNT → $CURRENT_JOB_COUNT jobs"
        echo "─────────────────────────────────────────────────────────────"
        
        if [ "$CURRENT_JOB_COUNT" -gt 0 ]; then
            echo ""
            echo "RayJobs activos:"
            kubectl get rayjobs -n $NAMESPACE -o custom-columns=\
NAME:.metadata.name,\
STATUS:.status.jobStatus,\
AGE:.metadata.creationTimestamp,\
SUBMISSION:.status.jobDeploymentStatus
            
            echo ""
            echo "Ray Workers activos:"
            kubectl get pods -n $NAMESPACE -l ray.io/node-type=worker -o custom-columns=\
NAME:.metadata.name,\
STATUS:.status.phase,\
NODE:.spec.nodeName,\
AGE:.metadata.creationTimestamp
            
            # Logs recientes de Orchestrator (para ver qué disparó el job)
            echo ""
            echo "Logs recientes de Orchestrator (últimos 10 eventos):"
            kubectl logs -n $NAMESPACE deployment/orchestrator --tail=10 | grep -E "(Deliberate|Ray|job)" || echo "  No logs relevantes"
        else
            echo "✓ No hay RayJobs activos"
        fi
        
        LAST_JOB_COUNT=$CURRENT_JOB_COUNT
        echo ""
    else
        # Heartbeat cada 10 segundos
        echo -ne "[$TIMESTAMP] ⏱️  Monitoring... (Jobs: $CURRENT_JOB_COUNT) \r"
    fi
    
    sleep 5
done

