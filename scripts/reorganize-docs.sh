#!/bin/bash
# Reorganize documentation from chaos to professional structure

set -e

echo "📚 Starting documentation reorganization..."
echo ""

# Phase 1: Create structure
echo "1️⃣  Creating directory structure..."
mkdir -p docs/{normative,sessions/{2025-10-21,2025-10-20,2025-10-16,2025-10-14,2025-10-11,archive},investigations,evidence,planning,testing/reports,summaries}
mkdir -p archived-docs/{old-sessions,old-test-reports,superseded}
echo "   ✅ Directories created"

# Phase 2: Move Normative (CRITICAL)
echo ""
echo "2️⃣  Moving NORMATIVE documents..."
git mv HEXAGONAL_ARCHITECTURE_PRINCIPLES.md docs/normative/ 2>/dev/null || true
git mv TESTING_ARCHITECTURE.md docs/normative/ 2>/dev/null || true
git mv API_GENERATION_RULES.md docs/normative/ 2>/dev/null || true
git mv DOCUMENTATION_STANDARDS.md docs/normative/ 2>/dev/null || true
echo "   ✅ Normative docs moved"

# Phase 3: Move Sessions (2025-10-21)
echo ""
echo "3️⃣  Moving session docs (2025-10-21)..."
git mv SESSION_20251021_EPIC_COMPLETE.md docs/sessions/2025-10-21/ 2>/dev/null || true
git mv SESSION_FINAL_20251021_COMPLETE_SUCCESS.md docs/sessions/2025-10-21/ 2>/dev/null || true
git mv SESSION_20251021_vLLM_AGENTS_COMPLETE.md docs/sessions/2025-10-21/ 2>/dev/null || true
git mv SUCCESS_VLLM_AGENTS_WORKING_20251021.md docs/sessions/2025-10-21/ 2>/dev/null || true
git mv TEST_RESULTS_20251021.md docs/sessions/2025-10-21/ 2>/dev/null || true
git mv PARA_MAÑANA_20251021.md docs/sessions/2025-10-21/ 2>/dev/null || true
echo "   ✅ Session 2025-10-21 moved"

# Phase 4: Move Sessions (2025-10-20)
echo ""
echo "4️⃣  Moving session docs (2025-10-20)..."
git mv CLEAN_ARCHITECTURE_REFACTOR_20251020.md docs/sessions/2025-10-20/ 2>/dev/null || true
git mv ORCHESTRATOR_HEXAGONAL_CODE_ANALYSIS.md docs/sessions/2025-10-20/ 2>/dev/null || true
git mv ORCHESTRATOR_HEXAGONAL_DEPLOYMENT.md docs/sessions/2025-10-20/ 2>/dev/null || true
echo "   ✅ Session 2025-10-20 moved"

# Phase 5: Move Sessions (2025-10-14)
echo ""
echo "5️⃣  Moving session docs (2025-10-14)..."
git mv DOCUMENTATION_AUDIT_2025-10-14.md docs/sessions/2025-10-14/ 2>/dev/null || true
echo "   ✅ Session 2025-10-14 moved"

# Phase 6: Move Investigations
echo ""
echo "6️⃣  Moving investigation docs..."
git mv BUG_ASYNCIO_RUN_IN_VLLM_AGENT.md docs/investigations/ 2>/dev/null || true
git mv MOCK_AGENTS_ISSUE.md docs/investigations/ 2>/dev/null || true
git mv COUNCIL_PERSISTENCE_PROBLEM.md docs/investigations/ 2>/dev/null || true
git mv DELIBERATION_USECASES_ANALYSIS.md docs/investigations/ 2>/dev/null || true
git mv ORCHESTRATOR_HEXAGONAL_ANALYSIS.md docs/investigations/ 2>/dev/null || true
git mv ARCHIVED_TESTS_INVESTIGATION.md docs/investigations/ 2>/dev/null || true
echo "   ✅ Investigations moved"

# Phase 7: Move Evidence
echo ""
echo "7️⃣  Moving evidence docs..."
git mv ALL_AGENTS_REAL_VLLM_EVIDENCE.md docs/evidence/ 2>/dev/null || true
git mv CLUSTER_EXECUTION_EVIDENCE.md docs/evidence/ 2>/dev/null || true
git mv NEO4J_VALKEY_COMPLETE_EVIDENCE.md docs/evidence/ 2>/dev/null || true
git mv COMPLETE_SYSTEM_DEMONSTRATION.md docs/evidence/ 2>/dev/null || true
git mv FULL_E2E_DEMONSTRATION_COMPLETE.md docs/evidence/ 2>/dev/null || true
git mv DEPLOYMENT_COMPLETE.md docs/evidence/ 2>/dev/null || true
git mv VERIFICATION_RESULTS.md docs/evidence/ 2>/dev/null || true
echo "   ✅ Evidence moved"

# Phase 8: Move Planning
echo ""
echo "8️⃣  Moving planning docs..."
git mv PR_STRATEGY.md docs/planning/ 2>/dev/null || true
git mv ROADMAP.md docs/planning/ 2>/dev/null || true
git mv ROADMAP_DETAILED.md docs/planning/ 2>/dev/null || true
git mv TODO_*.md docs/planning/ 2>/dev/null || true
git mv *_TODO.md docs/planning/ 2>/dev/null || true
git mv REFACTOR_DIRECTORY_STRUCTURE_PROPOSAL.md docs/planning/ 2>/dev/null || true
git mv REORGANIZATION_PLAN.md docs/planning/ 2>/dev/null || true
git mv DOCS_REORGANIZATION_PLAN.md docs/planning/ 2>/dev/null || true
echo "   ✅ Planning moved"

# Phase 9: Move Test Reports
echo ""
echo "9️⃣  Moving test reports..."
git mv FINAL_TEST_*.md docs/testing/reports/ 2>/dev/null || true
git mv TEST_*.md docs/testing/reports/ 2>/dev/null || true
git mv INTEGRATION_TESTS_AUDIT.md docs/testing/reports/ 2>/dev/null || true
git mv E2E_QUALITY_ANALYSIS.md docs/testing/reports/ 2>/dev/null || true
git mv UNIT_TESTS_TO_FIX.md docs/testing/reports/ 2>/dev/null || true
git mv E2E_TESTING_SESSION_SUMMARY.md docs/testing/reports/ 2>/dev/null || true
echo "   ✅ Test reports moved"

# Phase 10: Move Architecture
echo ""
echo "🔟 Moving architecture docs..."
git mv ARCHITECTURE_*.md docs/architecture/ 2>/dev/null || true
git mv API_VERSIONING_IMPLEMENTATION.md docs/architecture/ 2>/dev/null || true
git mv AGENTS_VS_MODELS_ARCHITECTURE.md docs/architecture/ 2>/dev/null || true
git mv SIMPLIFIED_CONTAINER_ARCHITECTURE.md docs/architecture/ 2>/dev/null || true
echo "   ✅ Architecture moved"

# Phase 11: Move Summaries
echo ""
echo "1️⃣1️⃣  Moving summary docs..."
git mv AGENT_TOOLS_COMPLETE.md docs/summaries/ 2>/dev/null || true
git mv TOOLS_IMPLEMENTATION_SUMMARY.md docs/summaries/ 2>/dev/null || true
git mv INTEGRATION_FINAL_SUMMARY.md docs/summaries/ 2>/dev/null || true
git mv MONITORING_DASHBOARD_*.md docs/summaries/ 2>/dev/null || true
git mv PERSISTENT_STREAMS_IMPLEMENTATION.md docs/summaries/ 2>/dev/null || true
echo "   ✅ Summaries moved"

# Phase 11b: Move Branding to investors
echo ""
echo "1️⃣1️⃣b Moving branding to investors..."
git mv BRANDING.md docs/investors/ 2>/dev/null || true
echo "   ✅ Branding moved to investors"

# Phase 12: Archive Obsolete
echo ""
echo "1️⃣2️⃣  Archiving obsolete docs..."
git mv COMMIT_*.md archived-docs/superseded/ 2>/dev/null || true
git mv COMMIT_*.txt archived-docs/superseded/ 2>/dev/null || true
git mv PR_MESSAGE.md archived-docs/superseded/ 2>/dev/null || true
git mv PR_ORCHESTRATOR_*.md archived-docs/superseded/ 2>/dev/null || true
git mv PR_RAY_*.md archived-docs/superseded/ 2>/dev/null || true
git mv PR_TEST_*.md archived-docs/superseded/ 2>/dev/null || true
git mv COMMUNICATION_AUDIT.md archived-docs/superseded/ 2>/dev/null || true
git mv E2E_REAL_AGENTS_PLAN.md archived-docs/superseded/ 2>/dev/null || true
git mv E2E_REAL_AGENTS_STATUS.md archived-docs/superseded/ 2>/dev/null || true
git mv NO_STUBS_AUDIT.md archived-docs/superseded/ 2>/dev/null || true
git mv ORCHESTRATOR_E2E_RESULTS.md archived-docs/old-test-reports/ 2>/dev/null || true
git mv ORCHESTRATOR_MOCKAGENT_TODO.md archived-docs/superseded/ 2>/dev/null || true
git mv E2E_RAY_VLLM_SETUP.md archived-docs/superseded/ 2>/dev/null || true
git mv MOCK_VS_REAL_AGENTS.md archived-docs/superseded/ 2>/dev/null || true
git mv ORCHESTRATOR_MICROSERVICE_*.md archived-docs/superseded/ 2>/dev/null || true
git mv SECURITY_REVIEW.md archived-docs/superseded/ 2>/dev/null || true
git mv DOCUMENTATION_DUE_DILIGENCE.md archived-docs/superseded/ 2>/dev/null || true
echo "   ✅ Obsolete docs archived"

# Phase 13: Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Reorganization Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   docs/normative:      $(find docs/normative -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/sessions:       $(find docs/sessions -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/investigations: $(find docs/investigations -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/evidence:       $(find docs/evidence -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/planning:       $(find docs/planning -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/testing:        $(find docs/testing -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/architecture:   $(find docs/architecture -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   docs/summaries:      $(find docs/summaries -type f -name "*.md" 2>/dev/null | wc -l) files"
echo "   archived-docs:       $(find archived-docs -type f -name "*.md" 2>/dev/null | wc -l) files"
echo ""
echo "   Root .md files:      $(ls -1 *.md 2>/dev/null | wc -l) (target: 6)"
echo ""
echo "✅ Documentation reorganization COMPLETE!"
echo ""

