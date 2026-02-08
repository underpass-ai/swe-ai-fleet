#!/usr/bin/env bash
# Shared module catalog and helpers for scripts.

if [ -n "${SWE_AI_FLEET_MODULES_LOADED:-}" ]; then
    return 0
fi
SWE_AI_FLEET_MODULES_LOADED=1

CORE_MODULES_PY313=(
    "core/shared"
    "core/memory"
    "core/context"
    "core/ceremony_engine"
    "core/orchestrator"
    "core/agents_and_tools"
    "core/reports"
)

CORE_MODULES_PY311=(
    "core/ray_jobs"
)

SERVICE_MODULES_PY313=(
    "services/backlog_review_processor"
    "services/context"
    "services/orchestrator"
    "services/planning"
    "services/planning_ceremony_processor"
    "services/task_derivation"
    "services/workflow"
)

SERVICE_MODULES_PY311=(
    "services/ray_executor"
)

all_modules_for_python() {
    local py_minor="$1"
    if [ "$py_minor" = "3.11" ]; then
        printf '%s\n' "${CORE_MODULES_PY311[@]}" "${SERVICE_MODULES_PY311[@]}"
    else
        printf '%s\n' "${CORE_MODULES_PY313[@]}" "${SERVICE_MODULES_PY313[@]}"
    fi
}

all_non_ray_modules() {
    printf '%s\n' "${CORE_MODULES_PY313[@]}" "${SERVICE_MODULES_PY313[@]}"
}

all_ray_modules() {
    printf '%s\n' "${CORE_MODULES_PY311[@]}" "${SERVICE_MODULES_PY311[@]}"
}

module_has_tests() {
    local module_path="$1"

    if [ -d "$module_path/tests" ]; then
        return 0
    fi

    if find "$module_path" \( -name 'test_*.py' -o -name '*_test.py' \) -print -quit | grep -q .; then
        return 0
    fi

    return 1
}

list_proto_modules() {
    find services core -maxdepth 2 -type f -name 'generate-protos.sh' \
        | sed 's#/generate-protos\.sh$##' \
        | sort -u
}
