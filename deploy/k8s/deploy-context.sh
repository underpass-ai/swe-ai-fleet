#!/bin/bash
# Script para desplegar el Context Service y sus dependencias en Kubernetes

set -e

NAMESPACE="swe-ai-fleet"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Desplegando Context Service en Kubernetes"
echo "=============================================="
echo ""

# Verificar que kubectl está disponible
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl no encontrado"
    exit 1
fi

# Verificar cluster
echo "📋 Estado del cluster:"
kubectl cluster-info | head -2
echo ""

# Verificar namespace
echo "🔍 Verificando namespace: $NAMESPACE"
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "❌ Namespace $NAMESPACE no existe"
    echo "   Ejecuta: kubectl apply -f 00-namespace.yaml"
    exit 1
fi
echo "✅ Namespace existe"
echo ""

# 1. Desplegar Neo4j
echo "📦 1. Desplegando Neo4j..."
kubectl apply -f "$SCRIPT_DIR/09-neo4j.yaml"
echo "   Esperando a que Neo4j esté listo..."
kubectl wait --for=condition=ready pod -l app=neo4j -n $NAMESPACE --timeout=300s || true
echo "✅ Neo4j desplegado"
echo ""

# 2. Desplegar Valkey (Redis-compatible)
echo "📦 2. Desplegando Valkey..."
kubectl apply -f "$SCRIPT_DIR/10-valkey.yaml"
echo "   Esperando a que Valkey esté listo..."
kubectl wait --for=condition=ready pod -l app=valkey -n $NAMESPACE --timeout=180s || true
echo "✅ Valkey desplegado"
echo ""

# Esperar un poco para que los servicios se estabilicen
echo "⏳ Esperando estabilización de dependencias (10s)..."
sleep 10
echo ""

# 3. Desplegar Context Service
echo "📦 3. Desplegando Context Service..."
kubectl apply -f "$SCRIPT_DIR/08-context-service.yaml"
echo "   Esperando a que Context esté listo..."
kubectl wait --for=condition=available deployment/context -n $NAMESPACE --timeout=300s || true
echo "✅ Context Service desplegado"
echo ""

# Mostrar estado final
echo "📊 Estado final de los servicios:"
echo "================================="
kubectl get pods -n $NAMESPACE -l app=neo4j
kubectl get pods -n $NAMESPACE -l app=valkey
kubectl get pods -n $NAMESPACE -l app=context
echo ""

echo "📝 Servicios disponibles:"
kubectl get svc -n $NAMESPACE | grep -E "(neo4j|valkey|redis|context)"
echo ""

echo "✅ Deployment completado!"
echo ""
echo "📋 Comandos útiles:"
echo "   Ver logs Context:  kubectl logs -n $NAMESPACE -l app=context --tail=100 -f"
echo "   Ver logs Neo4j:    kubectl logs -n $NAMESPACE -l app=neo4j --tail=100 -f"
echo "   Ver logs Valkey:   kubectl logs -n $NAMESPACE -l app=valkey --tail=100 -f"
echo "   Port-forward Neo4j: kubectl port-forward -n $NAMESPACE svc/neo4j 7474:7474 7687:7687"
echo "   Port-forward Valkey: kubectl port-forward -n $NAMESPACE svc/valkey 6379:6379"
echo "   Ver estado: kubectl get all -n $NAMESPACE | grep -E '(neo4j|valkey|context)'"

