#!/bin/bash

# Script para obtener issues de SonarCloud de una PR contra main
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

# Función para mostrar ayuda
show_help() {
    echo "Uso: $0 [PR_NUMBER]"
    echo ""
    echo "Obtiene los issues de SonarCloud para una PR específica contra main"
    echo ""
    echo "Argumentos:"
    echo "  PR_NUMBER    Número de la PR (opcional, usa la PR actual si no se especifica)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 86        # Issues de la PR #86"
    echo "  $0           # Issues de la PR actual"
    echo ""
    echo "Requisitos:"
    echo "  - Token de SonarCloud en $SONAR_TOKEN_FILE"
    echo "  - jq instalado para procesar JSON"
    echo "  - curl para hacer requests HTTP"
}

# Verificar dependencias
check_dependencies() {
    local missing_deps=()
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}Error: Faltan dependencias: ${missing_deps[*]}${NC}"
        echo "Instala las dependencias faltantes y vuelve a ejecutar el script."
        exit 1
    fi
}

# Verificar token de SonarCloud
check_token() {
    if [ ! -f "$SONAR_TOKEN_FILE" ]; then
        echo -e "${RED}Error: Token de SonarCloud no encontrado en $SONAR_TOKEN_FILE${NC}"
        echo "Crea el archivo con tu token de SonarCloud:"
        echo "echo 'TU_TOKEN_AQUI' > $SONAR_TOKEN_FILE"
        exit 1
    fi
    
    SONAR_TOKEN=$(cat "$SONAR_TOKEN_FILE")
    if [ -z "$SONAR_TOKEN" ]; then
        echo -e "${RED}Error: Token de SonarCloud vacío${NC}"
        exit 1
    fi
}

# Obtener número de PR actual si no se especifica
get_current_pr() {
    if command -v gh &> /dev/null; then
        local current_pr=$(gh pr view --json number --jq '.number' 2>/dev/null)
        if [ -n "$current_pr" ] && [ "$current_pr" != "null" ]; then
            echo "$current_pr"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Obtener issues de la PR
get_pr_issues() {
    local pr_number="$1"
    
    echo -e "${BLUE}Obteniendo issues de SonarCloud para PR #$pr_number...${NC}"
    
    local api_url="$BASE_URL/issues/search"
    local params="componentKeys=$PROJECT_KEY&pullRequest=$pr_number"
    
    local response=$(curl -s -u "$SONAR_TOKEN:" "$api_url?$params" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: No se pudo conectar a SonarCloud${NC}"
        exit 1
    fi
    
    # Verificar si hay errores en la respuesta
    local error=$(echo "$response" | jq -r '.errors[0].msg // empty' 2>/dev/null)
    if [ -n "$error" ]; then
        echo -e "${RED}Error de SonarCloud: $error${NC}"
        exit 1
    fi
    
    echo "$response"
}

# Mostrar resumen de issues
show_summary() {
    local response="$1"
    
    local total=$(echo "$response" | jq '.total')
    local critical=$(echo "$response" | jq '[.issues[] | select(.severity == "CRITICAL")] | length')
    local major=$(echo "$response" | jq '[.issues[] | select(.severity == "MAJOR")] | length')
    local minor=$(echo "$response" | jq '[.issues[] | select(.severity == "MINOR")] | length')
    local info=$(echo "$response" | jq '[.issues[] | select(.severity == "INFO")] | length')
    
    echo -e "\n${BLUE}=== RESUMEN DE ISSUES ===${NC}"
    echo -e "Total: $total"
    echo -e "${RED}Críticos: $critical${NC}"
    echo -e "${YELLOW}Mayores: $major${NC}"
    echo -e "${GREEN}Menores: $minor${NC}"
    echo -e "Info: $info"
}

# Mostrar issues por severidad
show_issues_by_severity() {
    local response="$1"
    local severity="$2"
    local color="$3"
    local title="$4"
    
    local issues=$(echo "$response" | jq --arg sev "$severity" '[.issues[] | select(.severity == $sev)]')
    local count=$(echo "$issues" | jq 'length')
    
    if [ "$count" -gt 0 ]; then
        echo -e "\n${color}=== $title ($count) ===${NC}"
        echo "$issues" | jq -r '.[] | "\(.rule) | \(.message) | \(.component | split(":")[1]) | Línea: \(.line // "N/A")"'
    fi
}

# Mostrar issues críticos con detalles
show_critical_details() {
    local response="$1"
    
    local critical_issues=$(echo "$response" | jq '[.issues[] | select(.severity == "CRITICAL")]')
    local count=$(echo "$critical_issues" | jq 'length')
    
    if [ "$count" -gt 0 ]; then
        echo -e "\n${RED}=== ISSUES CRÍTICOS DETALLADOS ===${NC}"
        echo "$critical_issues" | jq -r '.[] | "
Regla: \(.rule)
Archivo: \(.component | split(":")[1])
Mensaje: \(.message)
Línea: \(.line // "N/A")
Rango: \(.textRange.startLine // "N/A")-\(.textRange.endLine // "N/A")
---"'
    fi
}

# Generar reporte en archivo
generate_report() {
    local response="$1"
    local pr_number="$2"
    
    local report_file="sonar-pr-$pr_number-report.json"
    echo "$response" > "$report_file"
    echo -e "\n${GREEN}Reporte completo guardado en: $report_file${NC}"
}

# Función principal
main() {
    # Verificar argumentos
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_help
        exit 0
    fi
    
    # Verificar dependencias
    check_dependencies
    
    # Verificar token
    check_token
    
    # Obtener número de PR
    local pr_number="$1"
    if [ -z "$pr_number" ]; then
        pr_number=$(get_current_pr)
        if [ -z "$pr_number" ]; then
            echo -e "${RED}Error: No se pudo determinar la PR actual${NC}"
            echo "Especifica el número de PR como argumento: $0 [PR_NUMBER]"
            exit 1
        fi
        echo -e "${BLUE}Usando PR actual: #$pr_number${NC}"
    fi
    
    # Obtener issues
    local response=$(get_pr_issues "$pr_number")
    
    # Mostrar resultados
    show_summary "$response"
    show_issues_by_severity "$response" "CRITICAL" "$RED" "ISSUES CRÍTICOS"
    show_issues_by_severity "$response" "MAJOR" "$YELLOW" "ISSUES MAYORES"
    show_issues_by_severity "$response" "MINOR" "$GREEN" "ISSUES MENORES"
    
    # Mostrar detalles críticos
    show_critical_details "$response"
    
    # Generar reporte
    generate_report "$response" "$pr_number"
    
    echo -e "\n${BLUE}Dashboard de SonarCloud: https://sonarcloud.io/dashboard?id=$PROJECT_KEY&pullRequest=$pr_number${NC}"
}

# Ejecutar función principal
main "$@"
