#!/bin/bash
# Script para actualizar imports de VOs reorganizados en Planning Service

cd /home/tirso/ai/developents/swe-ai-fleet/services/planning

# Identifiers
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.epic_id import|from planning.domain.value_objects.identifiers.epic_id import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.project_id import|from planning.domain.value_objects.identifiers.project_id import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.story_id import|from planning.domain.value_objects.identifiers.story_id import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.plan_id import|from planning.domain.value_objects.identifiers.plan_id import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.task_id import|from planning.domain.value_objects.identifiers.task_id import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.decision_id import|from planning.domain.value_objects.identifiers.decision_id import|g' {} \;

# Statuses
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.epic_status import|from planning.domain.value_objects.statuses.epic_status import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.project_status import|from planning.domain.value_objects.statuses.project_status import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.story_state import|from planning.domain.value_objects.statuses.story_state import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.task_status import|from planning.domain.value_objects.statuses.task_status import|g' {} \;
find . -name "*.py" -type f -exec sed -i 's|from planning.domain.value_objects.task_type import|from planning.domain.value_objects.statuses.task_type import|g' {} \;

echo "✅ Imports actualizados"

