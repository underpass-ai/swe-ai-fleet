#!/bin/bash

# Script simplificado para obtener issues de SonarCloud de una PR
# Uso: ./scripts/get-pr-issues.sh [PR_NUMBER]

set -e

# Configuración
SONAR_TOKEN_FILE="/tmp/sonarcloud-token.txt"
PROJECT_KEY="underpass-ai-swe-ai-fleet"
BASE_URL="https://sonarcloud.io/api"

# Colores para output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar token
if [ ! -f "$SONAR_TOKEN_FILE" ]; then
    echo -e "${RED}Error: Token no encontrado en $SONAR_TOKEN_FILE${NC}"
    exit 1
fi

SONAR_TOKEN=$(cat "$SONAR_TOKEN_FILE")

# Obtener número de PR
PR_NUMBER="${1:-86}"
echo -e "${BLUE}Obteniendo issues de SonarCloud para PR #$PR_NUMBER...${NC}"

# Obtener issues
API_URL="$BASE_URL/issues/search"
PARAMS="componentKeys=$PROJECT_KEY&pullRequest=$PR_NUMBER"

RESPONSE=$(curl -s -u "$SONAR_TOKEN:" "$API_URL?$PARAMS")

# Verificar respuesta
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: No se pudo conectar a SonarCloud${NC}"
    exit 1
fi

# Extraer datos
TOTAL=$(echo "$RESPONSE" | jq -r '.total')
CRITICAL=$(echo "$RESPONSE" | jq -r '[.issues[] | select(.severity == "CRITICAL")] | length')
MAJOR=$(echo "$RESPONSE" | jq -r '[.issues[] | select(.severity == "MAJOR")] | length')
MINOR=$(echo "$RESPONSE" | jq -r '[.issues[] | select(.severity == "MINOR")] | length')
INFO=$(echo "$RESPONSE" | jq -r '[.issues[] | select(.severity == "INFO")] | length')

# Mostrar resumen
echo -e "\n${BLUE}=== RESUMEN DE ISSUES ===${NC}"
echo -e "Total: $TOTAL"
echo -e "${RED}Críticos: $CRITICAL${NC}"
echo -e "${YELLOW}Mayores: $MAJOR${NC}"
echo -e "${GREEN}Menores: $MINOR${NC}"
echo -e "Info: $INFO"

# Mostrar issues críticos
if [ "$CRITICAL" -gt 0 ]; then
    echo -e "\n${RED}=== ISSUES CRÍTICOS ===${NC}"
    echo "$RESPONSE" | jq -r '[.issues[] | select(.severity == "CRITICAL")] | .[] | "\(.rule) | \(.message) | \(.component | split(":")[1]) | Línea: \(.textRange.startLine // "N/A")"'
fi

# Mostrar issues mayores
if [ "$MAJOR" -gt 0 ]; then
    echo -e "\n${YELLOW}=== ISSUES MAYORES ===${NC}"
    echo "$RESPONSE" | jq -r '[.issues[] | select(.severity == "MAJOR")] | .[] | "\(.rule) | \(.message) | \(.component | split(":")[1]) | Línea: \(.textRange.startLine // "N/A")"'
fi

# Guardar reporte
REPORT_FILE="sonar-pr-$PR_NUMBER-report.json"
echo "$RESPONSE" > "$REPORT_FILE"
echo -e "\n${GREEN}Reporte completo guardado en: $REPORT_FILE${NC}"

# Mostrar dashboard
echo -e "\n${BLUE}Dashboard: https://sonarcloud.io/dashboard?id=$PROJECT_KEY&pullRequest=$PR_NUMBER${NC}"
