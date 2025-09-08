# Patch Application Instructions

This patch updates documentation for **EdgeCrew / SWE AI Fleet**.

## Files Included
- `README.md` (updated)
- `docs/VISION.md` (new)
- `docs/AGILE_TEAM.md` (new)
- `docs/CONTEXT_MANAGEMENT.md` (new)
- `docs/USER_STORY_FLOW.md` (new)
- `docs/MEMORY_ARCH.md` (new)
- `docs/INVESTORS.md` (new)

## How to Apply
1. Place this patch at the root of your repo.
2. Unzip contents **overwriting existing files**:
   ```bash
   unzip swe-ai-fleet-docs-patch-final.zip -d /path/to/your/repo
   ```
   or manually copy the files into your repo root.
3. Commit the changes:
   ```bash
   cd /path/to/your/repo
   git add README.md docs/
   git commit -m "docs: update and add investor-ready documentation bundle"
   ```

## Notes
- This patch is vendor-neutral (no direct Redis/Neo4j mentions).
- It introduces documentation for **investors and vision**, positioning EdgeCrew as the industry reference.
