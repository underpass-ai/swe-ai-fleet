#!/bin/bash
# Enhanced Unit Test Runner with Smart Error Reporting
# Provides all necessary information in ONE execution
# Usage: ./scripts/test-unit-enhanced.sh [optional-test-path]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}${BOLD}🧪 Enhanced Unit Test Runner${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Generate gRPC stubs
echo -e "${YELLOW}📦 Generating gRPC stubs...${NC}"
python scripts/generate_stubs.py > /dev/null 2>&1

# Temp file for full output
TEMP_OUTPUT=$(mktemp)

# Run tests and capture output
echo -e "${YELLOW}🧪 Running tests...${NC}"
echo ""

TEST_PATH="${1:-tests/unit}"
pytest $TEST_PATH \
    --tb=short \
    --no-header \
    -v \
    --cov \
    --cov-report=term-missing:skip-covered \
    2>&1 | tee "$TEMP_OUTPUT"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${BLUE}${BOLD}📊 TEST ANALYSIS SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# Extract statistics
PASSED=$(grep -oP '\d+(?= passed)' "$TEMP_OUTPUT" | tail -1 || echo "0")
FAILED=$(grep -oP '\d+(?= failed)' "$TEMP_OUTPUT" | tail -1 || echo "0")
ERRORS=$(grep -oP '\d+(?= error)' "$TEMP_OUTPUT" | tail -1 || echo "0")
WARNINGS=$(grep -oP '\d+(?= warning)' "$TEMP_OUTPUT" | tail -1 || echo "0")

echo -e "${BOLD}Test Statistics:${NC}"
echo -e "  ${GREEN}✅ Passed:   $PASSED${NC}"
if [ "$FAILED" -gt 0 ]; then
    echo -e "  ${RED}❌ Failed:   $FAILED${NC}"
fi
if [ "$ERRORS" -gt 0 ]; then
    echo -e "  ${RED}🔥 Errors:   $ERRORS${NC}"
fi
if [ "$WARNINGS" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
fi
echo ""

# List all FAILED tests with their errors
if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}${BOLD}❌ FAILED TESTS:${NC}"
    echo -e "${RED}────────────────${NC}"

    grep "FAILED " "$TEMP_OUTPUT" | while read -r line; do
        test_name=$(echo "$line" | sed 's/FAILED //')
        echo -e "  ${RED}✗${NC} $test_name"
    done

    echo ""
    echo -e "${YELLOW}${BOLD}🔍 ERROR DETAILS:${NC}"
    echo -e "${YELLOW}─────────────────${NC}"

    # Extract short error summaries
    grep -A3 "AssertionError\|TypeError\|ValueError\|KeyError" "$TEMP_OUTPUT" | \
        head -40 | \
        sed 's/^/  /'

    echo ""
fi

# List all collection ERRORS
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}${BOLD}🔥 COLLECTION ERRORS:${NC}"
    echo -e "${RED}──────────────────────${NC}"

    grep "ERROR collecting" "$TEMP_OUTPUT" | while read -r line; do
        error_file=$(echo "$line" | sed 's/ERROR collecting //' | sed 's/ -$//')
        echo -e "  ${RED}⚠${NC} $error_file"
    done

    echo ""
    echo -e "${YELLOW}${BOLD}📋 ERROR CAUSES:${NC}"
    echo -e "${YELLOW}────────────────${NC}"

    # Extract import errors and reasons
    grep -E "ModuleNotFoundError|ImportError|IndentationError" "$TEMP_OUTPUT" | \
        head -20 | \
        sed 's/^E   //' | \
        sed 's/^/  /' | \
        sort -u

    echo ""
fi

# Coverage summary for new code (if available)
echo -e "${BLUE}${BOLD}📈 COVERAGE HIGHLIGHTS:${NC}"
echo -e "${BLUE}────────────────────────${NC}"

# Extract coverage for new code (Planning Service use cases)
grep -E "create_project_usecase|create_epic_usecase|create_task_usecase|project.py|epic.py|task.py" "$TEMP_OUTPUT" | \
    grep -v "test_" | \
    tail -10 | \
    sed 's/^/  /'

echo ""

# Final status
echo -e "${CYAN}═══════════════════════════════════════${NC}"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ ALL TESTS PASSED${NC}"
else
    echo -e "${RED}${BOLD}❌ TESTS FAILED${NC}"
    echo -e "${YELLOW}Run again with specific test:${NC}"
    echo -e "  ${CYAN}pytest services/planning/tests/unit/path/test_name.py::test_function -vv${NC}"
fi
echo -e "${CYAN}═══════════════════════════════════════${NC}"

# Cleanup
rm -f "$TEMP_OUTPUT"
python scripts/cleanup_stubs.py > /dev/null 2>&1

exit $EXIT_CODE

