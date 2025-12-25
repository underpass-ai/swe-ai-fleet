#!/usr/bin/env bash
# ============================================================================
# E2E Test Runner - Sequential Execution
# ============================================================================
#
# This script runs E2E tests sequentially (01-06), ensuring each test completes
# before starting the next one.
#
# All tests are treated as asynchronous: Monitors logs for completion conditions
# to ensure accurate detection of test completion.
#
# Usage:
#   ./run-e2e-tests.sh [OPTIONS]
#
# Options:
#   --start-from TEST_NUMBER    Start from a specific test (e.g., 05)
#   --skip-build                Skip building images (use existing)
#   --skip-push                 Skip pushing images (use local)
#   --cleanup                   Delete jobs after completion
#   --timeout SECONDS           Timeout per test (default: 1200)
#   --namespace NAMESPACE       Kubernetes namespace (default: swe-ai-fleet)
#
# Examples:
#   ./run-e2e-tests.sh                          # Run all tests
#   ./run-e2e-tests.sh --start-from 05          # Start from test 05
#   ./run-e2e-tests.sh --skip-build --cleanup   # Skip build, cleanup after
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NAMESPACE="${NAMESPACE:-swe-ai-fleet}"
START_FROM="${START_FROM:-01}"
SKIP_BUILD="${SKIP_BUILD:-false}"
SKIP_PUSH="${SKIP_PUSH:-false}"
CLEANUP="${CLEANUP:-false}"
TEST_TIMEOUT="${TEST_TIMEOUT:-1200}"  # 20 minutes default
REBUILD_TEST="${REBUILD_TEST:-}"  # Test number to rebuild (e.g., "01" or "06")
REBUILD_ALL="${REBUILD_ALL:-false}"  # Rebuild all tests
BUILD_ONLY="${BUILD_ONLY:-false}"  # Only build, don't execute

# Test definitions (all tests treated as async - monitor logs for completion)
declare -A TEST_CONFIGS=(
    ["00"]="00-cleanup-storage|e2e-cleanup-storage"
    ["01"]="01-planning-ui-get-node-relations|e2e-planning-ui-get-node-relations"
    ["02"]="02-create-test-data|e2e-create-test-data"
    ["04"]="04-start-backlog-review-ceremony|e2e-start-backlog-review-ceremony"
    ["05"]="05-validate-deliberations-and-tasks|e2e-validate-deliberations-and-tasks"
    ["06"]="06-approve-review-plan-and-validate-plan-creation|e2e-approve-review-plan-and-validate-plan-creation"
)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --start-from)
            START_FROM="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD="true"
            shift
            ;;
        --skip-push)
            SKIP_PUSH="true"
            shift
            ;;
        --cleanup)
            CLEANUP="true"
            shift
            ;;
        --timeout)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --rebuild-test)
            REBUILD_TEST="$2"
            BUILD_ONLY="true"
            shift 2
            ;;
        --rebuild-all)
            REBUILD_ALL="true"
            BUILD_ONLY="true"
            shift
            ;;
        --build-only)
            BUILD_ONLY="true"
            shift
            ;;
        --help|-h)
            cat <<EOF
E2E Test Runner - Sequential Execution

Usage: $0 [OPTIONS]

Options:
  --start-from TEST_NUMBER    Start from a specific test (01-06)
  --skip-build                 Skip building images (use existing)
  --skip-push                  Skip pushing images (use local)
  --cleanup                    Delete jobs after completion
  --timeout SECONDS            Timeout per test (default: 1200)
  --namespace NAMESPACE        Kubernetes namespace (default: swe-ai-fleet)
  --rebuild-test TEST_NUMBER   Rebuild a specific test (e.g., "01" or "06") and exit
  --rebuild-all                Rebuild all tests and exit
  --build-only                 Build images but don't execute tests
  --help, -h                   Show this help message

Examples:
  $0                                    # Run all tests
  $0 --start-from 05                   # Start from test 05
  $0 --skip-build --cleanup            # Skip build, cleanup after
  $0 --rebuild-test 06                 # Rebuild only test 06
  $0 --rebuild-all                     # Rebuild all tests
  $0 --build-only                      # Build all tests without executing
EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}===============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===============================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    print_success "kubectl found"

    # Check namespace
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        print_error "Namespace ${NAMESPACE} not found"
        exit 1
    fi
    print_success "Namespace ${NAMESPACE} exists"

    # Check container builder
    if [[ "${SKIP_BUILD}" == "false" ]]; then
        if command -v podman &> /dev/null; then
            BUILDER="podman"
        elif command -v docker &> /dev/null; then
            BUILDER="docker"
        else
            print_error "No container builder found (podman or docker)"
            exit 1
        fi
        print_success "Container builder: ${BUILDER}"
    fi

    print_success "Prerequisites check passed"
}

# Get test configuration
get_test_config() {
    local test_num=$1
    local config="${TEST_CONFIGS[$test_num]}"
    if [[ -z "$config" ]]; then
        return 1
    fi
    echo "$config"
}

# Build and push test image
build_and_push_test() {
    local test_num=$1
    local test_dir=$2
    local test_name=$3

    print_info "Building test ${test_num}: ${test_name}"

    if [[ "${SKIP_BUILD}" == "false" ]]; then
        # Use Makefile principal para construir
        if ! make -C "${PROJECT_ROOT}" e2e-build-test TEST="${test_dir}"; then
            print_error "Failed to build test ${test_num}"
            return 1
        fi
    fi

    if [[ "${SKIP_PUSH}" == "false" ]]; then
        # Use Makefile principal para hacer push
        if ! make -C "${PROJECT_ROOT}" e2e-push-test TEST="${test_dir}"; then
            print_error "Failed to push test ${test_num}"
            return 1
        fi
    fi

    print_success "Test ${test_num} image ready"
    return 0
}

# Rebuild a specific test
rebuild_single_test() {
    local test_num=$1
    local config=$(get_test_config "$test_num")

    if [[ -z "$config" ]]; then
        print_error "Test ${test_num} not found in configuration"
        return 1
    fi

    IFS='|' read -r test_dir job_name <<< "$config"

    print_header "Rebuilding Test ${test_num}: ${test_dir}"

    # Temporarily disable skip flags for rebuild
    local original_skip_build="${SKIP_BUILD}"
    local original_skip_push="${SKIP_PUSH}"
    SKIP_BUILD="false"
    SKIP_PUSH="false"

    if build_and_push_test "${test_num}" "${test_dir}" "${job_name}"; then
        print_success "Test ${test_num} rebuilt successfully"
        SKIP_BUILD="${original_skip_build}"
        SKIP_PUSH="${original_skip_push}"
        return 0
    else
        print_error "Failed to rebuild test ${test_num}"
        SKIP_BUILD="${original_skip_build}"
        SKIP_PUSH="${original_skip_push}"
        return 1
    fi
}

# Rebuild all tests
rebuild_all_tests() {
    print_header "Rebuilding All E2E Tests"

    local failed_tests=()
    local passed_tests=()

    # Rebuild cleanup first
    if [[ -n "${TEST_CONFIGS[00]:-}" ]]; then
        if rebuild_single_test "00"; then
            passed_tests+=("00")
        else
            failed_tests+=("00")
        fi
    fi

    # Rebuild all numbered tests
    for test_num in 01 02 03 04 05 06; do
        if rebuild_single_test "$test_num"; then
            passed_tests+=("$test_num")
        else
            failed_tests+=("$test_num")
        fi
    done

    # Summary
    print_header "Rebuild Summary"
    echo "Passed: ${#passed_tests[@]}"
    for test_num in "${passed_tests[@]}"; do
        print_success "Test ${test_num}"
    done

    if [[ ${#failed_tests[@]} -gt 0 ]]; then
        echo ""
        echo "Failed: ${#failed_tests[@]}"
        for test_num in "${failed_tests[@]}"; do
            print_error "Test ${test_num}"
        done
        return 1
    fi

    print_success "All tests rebuilt successfully"
    return 0
}

# Deploy test job
deploy_test() {
    local test_num=$1
    local test_dir=$2
    local job_name=$3

    print_info "Deploying test ${test_num}: ${job_name}"

    # Use make -C to run from project root, so Makefile paths work correctly
    # Some Makefiles use paths relative to project root (like test 01)
    if ! make -C "${PROJECT_ROOT}" -f "${PROJECT_ROOT}/e2e/tests/${test_dir}/Makefile" deploy 2>/dev/null; then
        # Fallback: try running from test directory (for Makefiles that use job.yaml directly)
        cd "${PROJECT_ROOT}/e2e/tests/${test_dir}"
        if ! make deploy; then
            print_error "Failed to deploy test ${test_num}"
            return 1
        fi
    fi

    # Wait a moment for job to be created
    sleep 2

    print_success "Test ${test_num} deployed"
    return 0
}

# Wait for test completion (monitors logs for all tests)
wait_for_test() {
    local job_name=$1
    local timeout=$2

    print_info "Waiting for test ${job_name} to complete (timeout: ${timeout}s)..."
    print_info "Monitoring logs for completion conditions..."

    local start_time=$(date +%s)
    local end_time=$((start_time + timeout))
    local poll_interval=5  # Reduced to 5 seconds for more responsive updates
    local last_log_line=""
    local last_progress_time=$start_time
    local progress_interval=10  # Show progress every 10 seconds
    local last_stage=""
    local log_count=0

    while [[ $(date +%s) -lt $end_time ]]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local remaining=$((end_time - current_time))

        # Get pod name
        local pod_name=$(kubectl get pods -n "${NAMESPACE}" \
            -l app="${job_name}" \
            --field-selector=status.phase=Running \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

        # If no running pod, check for completed/failed
        if [[ -z "$pod_name" ]]; then
            # Check if job completed
            if kubectl wait --for=condition=complete \
                --timeout=1s \
                job/"${job_name}" \
                -n "${NAMESPACE}" &> /dev/null; then
                print_success "Job ${job_name} completed"
                return 0
            fi

            # Check if job failed
            if kubectl wait --for=condition=failed \
                --timeout=1s \
                job/"${job_name}" \
                -n "${NAMESPACE}" &> /dev/null; then
                print_error "Job ${job_name} failed"
                return 1
            fi

            # Pod might be pending
            local pending_pod=$(kubectl get pods -n "${NAMESPACE}" \
                -l app="${job_name}" \
                --field-selector=status.phase=Pending \
                -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

            if [[ -n "$pending_pod" ]]; then
                if [[ $((current_time - last_progress_time)) -ge $progress_interval ]]; then
                    print_info "[${elapsed}s/${timeout}s] Pod pending, waiting for start..."
                    last_progress_time=$current_time
                fi
            fi

            sleep $poll_interval
            continue
        fi

        # Get pod status
        local pod_phase=$(kubectl get pod -n "${NAMESPACE}" "${pod_name}" \
            -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

        # Get recent logs (last 3 lines for context)
        local recent_logs=$(kubectl logs -n "${NAMESPACE}" \
            "${pod_name}" \
            --tail=3 2>/dev/null || echo "")

        # Get latest log line
        local current_log_line=$(echo "$recent_logs" | tail -1)

        # Detect stage/etapa in logs
        local detected_stage=""
        if echo "$recent_logs" | grep -qiE "\[Etapa [0-9]+\]|Stage [0-9]+|ETAPA [0-9]+"; then
            detected_stage=$(echo "$recent_logs" | grep -iE "\[Etapa [0-9]+\]|Stage [0-9]+|ETAPA [0-9]+" | tail -1 | sed 's/.*\([Ee]tapa [0-9]\+\|Stage [0-9]\+\|ETAPA [0-9]\+\)/\1/i' | sed 's/^[[:space:]]*//' | cut -d: -f1)
        fi

        # Check for completion indicators in logs (multiple patterns)
        if echo "$recent_logs" | grep -qiE "(Test Completed Successfully|Test.*PASSED|✅.*Test.*completed|All tests passed|✅.*Todas las etapas)"; then
            print_success "Test ${job_name} completed successfully (detected in logs)"
            return 0
        fi

        # Check for failure indicators in logs
        if echo "$recent_logs" | grep -qiE "(Test.*FAILED|✗.*Error|Test.*failed|Some tests failed|✗.*Unexpected error)"; then
            print_error "Test ${job_name} failed (detected in logs)"
            return 1
        fi

        # Check pod phase
        if [[ "$pod_phase" == "Succeeded" ]]; then
            # Pod succeeded, check exit code
            local exit_code=$(kubectl get pod -n "${NAMESPACE}" "${pod_name}" \
                -o jsonpath='{.status.containerStatuses[0].state.terminated.exitCode}' 2>/dev/null || echo "")

            if [[ "$exit_code" == "0" ]]; then
                print_success "Test ${job_name} completed successfully (pod exited with code 0)"
                return 0
            else
                print_error "Test ${job_name} failed (pod exited with code ${exit_code})"
                return 1
            fi
        fi

        if [[ "$pod_phase" == "Failed" ]]; then
            print_error "Test ${job_name} failed (pod phase: Failed)"
            return 1
        fi

        # Show progress regularly
        if [[ $((current_time - last_progress_time)) -ge $progress_interval ]]; then
            # Progress bar calculation
            local progress_percent=$((elapsed * 100 / timeout))
            if [[ $progress_percent -gt 100 ]]; then
                progress_percent=100
            fi

            # Build progress message
            local progress_msg="[${elapsed}s/${timeout}s] ${progress_percent}%"

            # Add stage info if detected
            if [[ -n "$detected_stage" ]] && [[ "$detected_stage" != "$last_stage" ]]; then
                progress_msg="${progress_msg} | ${detected_stage}"
                last_stage="$detected_stage"
            fi

            # Add pod phase
            progress_msg="${progress_msg} | Pod: ${pod_phase}"

            # Add log count
            log_count=$((log_count + 1))
            if [[ $log_count -gt 0 ]]; then
                progress_msg="${progress_msg} | Logs: ${log_count}"
            fi

            print_info "$progress_msg"

            # Show latest log line if available and different
            if [[ -n "$current_log_line" ]] && [[ "$current_log_line" != "$last_log_line" ]]; then
                # Clean ANSI codes for display
                local clean_log=$(echo "$current_log_line" | sed 's/\x1b\[[0-9;]*m//g')
                if [[ ${#clean_log} -gt 100 ]]; then
                    clean_log="${clean_log:0:97}..."
                fi
                print_info "  → ${clean_log}"
                last_log_line="$current_log_line"
            fi

            last_progress_time=$current_time
        fi

        sleep $poll_interval
    done

    print_error "Test ${job_name} timed out after ${timeout}s"
    print_info "Final pod status:"
    kubectl get pods -n "${NAMESPACE}" -l app="${job_name}" 2>/dev/null || true
    return 1
}

# Get test logs
show_test_logs() {
    local job_name=$1
    local lines="${2:-50}"

    print_info "Showing last ${lines} lines of logs for ${job_name}..."

    local pod_name=$(kubectl get pods -n "${NAMESPACE}" \
        -l app="${job_name}" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [[ -n "$pod_name" ]]; then
        kubectl logs -n "${NAMESPACE}" "${pod_name}" --tail="${lines}" || true
    else
        print_warning "No pod found for ${job_name}"
    fi
}

# Cleanup test job
cleanup_test() {
    local test_dir=$1
    local job_name=$2

    if [[ "${CLEANUP}" == "true" ]]; then
        print_info "Cleaning up ${job_name}..."

        # Try from project root first (for Makefiles with relative paths)
        if ! make -C "${PROJECT_ROOT}" -f "${PROJECT_ROOT}/e2e/tests/${test_dir}/Makefile" delete &> /dev/null; then
            # Fallback: try from test directory
            cd "${PROJECT_ROOT}/e2e/tests/${test_dir}"
            make delete &> /dev/null || true
        fi

        print_success "Cleaned up ${job_name}"
    fi
}

# Rebuild a specific test
rebuild_single_test() {
    local test_num=$1
    local config=$(get_test_config "$test_num")

    if [[ -z "$config" ]]; then
        print_error "Test ${test_num} not found in configuration"
        return 1
    fi

    IFS='|' read -r test_dir job_name <<< "$config"

    print_header "Rebuilding Test ${test_num}: ${test_dir}"

    # Temporarily disable skip flags for rebuild
    local original_skip_build="${SKIP_BUILD}"
    local original_skip_push="${SKIP_PUSH}"
    SKIP_BUILD="false"
    SKIP_PUSH="false"

    if build_and_push_test "${test_num}" "${test_dir}" "${job_name}"; then
        print_success "Test ${test_num} rebuilt successfully"
        SKIP_BUILD="${original_skip_build}"
        SKIP_PUSH="${original_skip_push}"
        return 0
    else
        print_error "Failed to rebuild test ${test_num}"
        SKIP_BUILD="${original_skip_build}"
        SKIP_PUSH="${original_skip_push}"
        return 1
    fi
}

# Rebuild all tests
rebuild_all_tests() {
    print_header "Rebuilding All E2E Tests"

    local failed_tests=()
    local passed_tests=()

    # Rebuild cleanup first
    if [[ -n "${TEST_CONFIGS[00]:-}" ]]; then
        if rebuild_single_test "00"; then
            passed_tests+=("00")
        else
            failed_tests+=("00")
        fi
    fi

    # Rebuild all numbered tests
    for test_num in 01 02 03 04 05 06; do
        if rebuild_single_test "$test_num"; then
            passed_tests+=("$test_num")
        else
            failed_tests+=("$test_num")
        fi
    done

    # Summary
    print_header "Rebuild Summary"
    echo "Passed: ${#passed_tests[@]}"
    for test_num in "${passed_tests[@]}"; do
        print_success "Test ${test_num}"
    done

    if [[ ${#failed_tests[@]} -gt 0 ]]; then
        echo ""
        echo "Failed: ${#failed_tests[@]}"
        for test_num in "${failed_tests[@]}"; do
            print_error "Test ${test_num}"
        done
        return 1
    fi

    print_success "All tests rebuilt successfully"
    return 0
}

# Wait for ceremony to reach REVIEWING status (after test 04 completes)
wait_for_ceremony_reviewing() {
    local timeout=${1:-300}  # Default 5 minutes
    local poll_interval=10
    local start_time=$(date +%s)
    local end_time=$((start_time + timeout))

    print_info "Waiting for ceremony to transition to REVIEWING (timeout: ${timeout}s)..."

    local neo4j_pod=$(kubectl get pods -n "${NAMESPACE}" -o name | grep neo4j | head -1 | cut -d/ -f2)
    if [[ -z "$neo4j_pod" ]]; then
        print_warning "Cannot wait for ceremony: Neo4j pod not found"
        return 0
    fi

    local neo4j_user=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_USER}' 2>/dev/null | base64 -d 2>/dev/null || echo "neo4j")
    local neo4j_password=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_PASSWORD}' 2>/dev/null | base64 -d 2>/dev/null || echo "password")

    local attempt=0
    while [[ $(date +%s) -lt $end_time ]]; do
        attempt=$((attempt + 1))
        local elapsed=$(( $(date +%s) - start_time ))

        # Check for ceremonies in REVIEWING status
        local reviewing_count=$(kubectl exec -n "${NAMESPACE}" "$neo4j_pod" -- cypher-shell -u "$neo4j_user" -p "$neo4j_password" \
            "MATCH (c:BacklogReviewCeremony) WHERE c.status = 'REVIEWING' RETURN count(c) as count;" 2>/dev/null | \
            grep -v "^$" | grep -v "password change" | tail -1 | grep -oE '[0-9]+' || echo "0")

        if [[ "$reviewing_count" -gt 0 ]]; then
            print_success "Found ${reviewing_count} ceremony(ies) in REVIEWING status (elapsed: ${elapsed}s)"
            return 0
        fi

        if [[ $((elapsed % 30)) -eq 0 ]]; then
            print_info "[${elapsed}s/${timeout}s] Waiting for ceremony to reach REVIEWING... (attempt ${attempt})"
        fi

        sleep $poll_interval
    done

    print_warning "Timeout waiting for ceremony to reach REVIEWING (elapsed: ${timeout}s)"
    print_info "Ceremonies may still be processing. Continuing anyway..."
    return 0  # Don't fail, just warn
}

# Inspect test data from test 02
inspect_test_data() {
    print_header "📊 Inspecting Test Data (Test 02) - Neo4j + Valkey"

    local neo4j_pod=$(kubectl get pods -n "${NAMESPACE}" -o name | grep neo4j | head -1 | cut -d/ -f2)
    local valkey_pod=$(kubectl get pods -n "${NAMESPACE}" -o name | grep valkey | head -1 | cut -d/ -f2)

    if [[ -z "$neo4j_pod" ]] || [[ -z "$valkey_pod" ]]; then
        print_warning "Cannot inspect: Neo4j or Valkey pods not found"
        return 0
    fi

    # Get Neo4j credentials from secret
    local neo4j_user=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_USER}' 2>/dev/null | base64 -d 2>/dev/null || echo "neo4j")
    local neo4j_password=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_PASSWORD}' 2>/dev/null | base64 -d 2>/dev/null || echo "password")

    # Projects
    print_info "Projects (Neo4j):"
    kubectl exec -n "${NAMESPACE}" "$neo4j_pod" -- cypher-shell -u "$neo4j_user" -p "$neo4j_password" \
        "MATCH (p:Project) RETURN p.id as project_id, p.name as name ORDER BY p.created_at DESC LIMIT 3;" 2>&1 | grep -v "^$" | grep -v "password change" | head -5 || true

    # Stories
    print_info "Stories (Neo4j):"
    kubectl exec -n "${NAMESPACE}" "$neo4j_pod" -- cypher-shell -u "$neo4j_user" -p "$neo4j_password" \
        "MATCH (s:Story) RETURN s.id as story_id, s.title as title, s.state as state ORDER BY s.created_at DESC LIMIT 5;" 2>&1 | grep -v "^$" | grep -v "password change" | head -7 || true
    echo ""
}

# Inspect backlog review ceremony and deliberations from test 04
inspect_ceremony() {
    print_header "📊 Inspecting Backlog Review Ceremony (Test 04) - Logs"

    # Planning service logs for ceremonies
    print_info "Recent Ceremony Events:"
    kubectl logs -n "${NAMESPACE}" -l app=planning --tail=200 2>&1 | \
        grep -E "(ceremony|Ceremony|BacklogReview)" | tail -10 || true

    # Planning service logs for deliberations
    print_info "Recent Deliberations:"
    kubectl logs -n "${NAMESPACE}" -l app=planning --tail=200 2>&1 | \
        grep -E "(AddAgentDeliberation|Saved deliberation)" | tail -10 || true

    # Neo4j ceremony data
    local neo4j_pod=$(kubectl get pods -n "${NAMESPACE}" -o name | grep neo4j | head -1 | cut -d/ -f2)
    if [[ -n "$neo4j_pod" ]]; then
        local neo4j_user=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_USER}' 2>/dev/null | base64 -d 2>/dev/null || echo "neo4j")
        local neo4j_password=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_PASSWORD}' 2>/dev/null | base64 -d 2>/dev/null || echo "password")

        print_info "Ceremonies in Neo4j:"
        kubectl exec -n "${NAMESPACE}" "$neo4j_pod" -- cypher-shell -u "$neo4j_user" -p "$neo4j_password" \
            "MATCH (c:BacklogReviewCeremony) RETURN c.id as ceremony_id, c.status as status ORDER BY c.created_at DESC LIMIT 3;" 2>&1 | grep -v "^$" | grep -v "password change" | head -5 || true
    fi
    echo ""
}

# Inspect tasks created in test 05
inspect_tasks() {
    print_header "📊 Inspecting Tasks (Test 05) - Neo4j + Valkey"

    local neo4j_pod=$(kubectl get pods -n "${NAMESPACE}" -o name | grep neo4j | head -1 | cut -d/ -f2)
    local valkey_pod=$(kubectl get pods -n "${NAMESPACE}" -o name | grep valkey | head -1 | cut -d/ -f2)

    if [[ -z "$neo4j_pod" ]] || [[ -z "$valkey_pod" ]]; then
        print_warning "Cannot inspect: Neo4j or Valkey pods not found"
        return 0
    fi

    # Get Neo4j credentials from secret
    local neo4j_user=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_USER}' 2>/dev/null | base64 -d 2>/dev/null || echo "neo4j")
    local neo4j_password=$(kubectl get secret -n "${NAMESPACE}" neo4j-auth -o jsonpath='{.data.NEO4J_PASSWORD}' 2>/dev/null | base64 -d 2>/dev/null || echo "password")

    # Tasks in Neo4j
    print_info "Recent Tasks (Neo4j):"
    kubectl exec -n "${NAMESPACE}" "$neo4j_pod" -- cypher-shell -u "$neo4j_user" -p "$neo4j_password" \
        "MATCH (t:Task) RETURN t.id as task_id, t.type as type, t.status as status, t.plan_id as plan_id ORDER BY t.created_at DESC LIMIT 10;" 2>&1 | grep -v "^$" | grep -v "password change" | head -12 || true

    # Tasks with plan_id
    print_info "Tasks with Plan ID:"
    kubectl exec -n "${NAMESPACE}" "$neo4j_pod" -- cypher-shell -u "$neo4j_user" -p "$neo4j_password" \
        "MATCH (t:Task) WHERE t.plan_id IS NOT NULL RETURN count(t) as count;" 2>&1 | grep -v "^$" | grep -v "password change" | head -3 || true

    # Task count in Valkey
    local task_count=$(kubectl exec -n "${NAMESPACE}" "$valkey_pod" -- redis-cli --no-auth-warning KEYS "planning:task:*" 2>/dev/null | grep -v ":state$" | grep -v ":by_story:" | wc -l || echo "0")
    print_info "Tasks in Valkey: ${task_count}"
    echo ""
}

# Run a single test
run_test() {
    local test_num=$1
    local config=$2

    IFS='|' read -r test_dir job_name <<< "$config"

    print_header "Running Test ${test_num}: ${test_dir}"

    # Build and push (only if not skipping build)
    if [[ "${SKIP_BUILD}" == "false" ]]; then
        if ! build_and_push_test "${test_num}" "${test_dir}" "${job_name}"; then
            return 1
        fi
    else
        print_info "Skipping build (using existing images)"
    fi

    # Deploy
    if ! deploy_test "${test_num}" "${test_dir}" "${job_name}"; then
        return 1
    fi

    # Wait for completion (all tests use async monitoring)
    wait_for_test "${job_name}" "${TEST_TIMEOUT}"
    local wait_result=$?

    # Show logs if failed
    if [[ $wait_result -ne 0 ]]; then
        print_error "Test ${test_num} failed"
        show_test_logs "${job_name}" 100
        cleanup_test "${test_dir}" "${job_name}"
        return 1
    fi

    # Show final logs
    show_test_logs "${job_name}" 50

    # Wait for async processes to complete (for tests that trigger async work)
    case "${test_num}" in
        04)
            # Test 04 starts ceremony but deliberations are async
            # Wait for ceremony to reach REVIEWING status before continuing
            print_info "Waiting for ceremony to complete deliberations (async process)..."
            wait_for_ceremony_reviewing 300  # 5 minutes timeout
            inspect_ceremony
            ;;
        05)
            # Test 05 validates deliberations and tasks - already waits internally
            # Just verify it completed successfully
            inspect_tasks
            ;;
        02)
            inspect_test_data
            ;;
    esac

    # Cleanup
    cleanup_test "${test_dir}" "${job_name}"

    print_success "Test ${test_num} completed successfully"
    return 0
}

# Main execution
main() {
    # Handle rebuild-only modes
    if [[ "${REBUILD_ALL}" == "true" ]]; then
        rebuild_all_tests
        return $?
    fi

    if [[ -n "${REBUILD_TEST}" ]]; then
        rebuild_single_test "${REBUILD_TEST}"
        return $?
    fi

    # Normal execution mode
    print_header "E2E Test Runner - Sequential Execution"
    echo "Configuration:"
    echo "  Namespace: ${NAMESPACE}"
    echo "  Start From: Test ${START_FROM}"
    echo "  Skip Build: ${SKIP_BUILD}"
    echo "  Skip Push: ${SKIP_PUSH}"
    echo "  Cleanup: ${CLEANUP}"
    echo "  Timeout: ${TEST_TIMEOUT}s per test"
    echo "  Build Only: ${BUILD_ONLY}"
    echo ""

    # If build-only mode, rebuild all tests and exit
    if [[ "${BUILD_ONLY}" == "true" ]]; then
        rebuild_all_tests
        return $?
    fi

    # Always run cleanup (test 00) first, unless explicitly skipped
    if [[ "${START_FROM}" != "00" ]]; then
        print_header "Running Storage Cleanup (Test 00) - Required before all tests"
        if [[ -n "${TEST_CONFIGS[00]:-}" ]]; then
            if run_test "00" "${TEST_CONFIGS[00]}"; then
                print_success "Storage cleanup completed successfully"
                echo ""
            else
                print_error "Storage cleanup failed. Continuing anyway..."
                echo ""
            fi
        fi
    fi

    check_prerequisites

    # Track results
    local failed_tests=()
    local passed_tests=()
    local start_time=$(date +%s)

    # Run tests sequentially
    for test_num in 01 02 03 04 05 06; do
        # Skip tests before start_from
        if [[ "$test_num" < "$START_FROM" ]]; then
            print_info "Skipping test ${test_num} (before start-from: ${START_FROM})"
            continue
        fi

        # Get test config
        local config=$(get_test_config "$test_num")
        if [[ -z "$config" ]]; then
            print_warning "Test ${test_num} not found in configuration, skipping"
            continue
        fi

        # Run test (skip build if BUILD_ONLY is true, but we already handled that)
        if run_test "$test_num" "$config"; then
            passed_tests+=("$test_num")
        else
            failed_tests+=("$test_num")
            print_error "Test ${test_num} failed. Stopping execution."
            break
        fi

        # Small delay between tests
        sleep 2
    done

    # Summary
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))

    print_header "Test Execution Summary"
    echo "Total Time: ${total_time}s ($(($total_time / 60))m $(($total_time % 60))s)"
    echo ""
    echo "Passed Tests: ${#passed_tests[@]}"
    for test_num in "${passed_tests[@]}"; do
        print_success "Test ${test_num}"
    done
    echo ""
    echo "Failed Tests: ${#failed_tests[@]}"
    for test_num in "${failed_tests[@]}"; do
        print_error "Test ${test_num}"
    done
    echo ""

    if [[ ${#failed_tests[@]} -eq 0 ]]; then
        print_success "All tests passed!"
        return 0
    else
        print_error "Some tests failed"
        return 1
    fi
}

# Run main
main "$@"

