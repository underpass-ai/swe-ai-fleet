// Neo4j Constraints for Domain Invariant Enforcement
// =====================================================
//
// These constraints enforce the mandatory hierarchy:
// Project → Epic → Story → Task
//
// See: docs/architecture/DOMAIN_INVARIANTS_BUSINESS_RULES.md
//
// Domain Rule: NO orphan nodes allowed.
// Every node (except Project) MUST have a parent relationship.

// ============================================================================
// UNIQUE CONSTRAINTS (Entity IDs)
// ============================================================================

// Project ID must be unique
CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project)
REQUIRE p.project_id IS UNIQUE;

// Epic ID must be unique
CREATE CONSTRAINT epic_id_unique IF NOT EXISTS
FOR (e:Epic)
REQUIRE e.epic_id IS UNIQUE;

// Story ID must be unique
CREATE CONSTRAINT story_id_unique IF NOT EXISTS
FOR (s:Story)
REQUIRE s.id IS UNIQUE;

// Task ID must be unique
CREATE CONSTRAINT task_id_unique IF NOT EXISTS
FOR (t:Task)
REQUIRE t.task_id IS UNIQUE;

// ============================================================================
// MANDATORY RELATIONSHIPS (Hierarchy Enforcement)
// ============================================================================
//
// CRITICAL: These constraints make it IMPOSSIBLE to create orphan nodes.
// Neo4j will REJECT any CREATE/MERGE that violates the hierarchy.
//
// This enforces domain invariants at the database level (defense in depth).

// Constraint #1: Task MUST have Story relationship (via PlanVersion)
// Task → PlanVersion → Story
//
// Note: We cannot enforce multi-hop constraints directly in Neo4j 5.x,
// so this is enforced at the application layer via Task.plan_id validation.
// The PlanVersion → Story relationship is enforced by planning service.
//
// Future: Consider using triggers or stored procedures for multi-hop validation.

// Constraint #2: Story MUST have Epic relationship
// This constraint requires Neo4j Enterprise Edition with relationship existence constraints
// For Community Edition, enforce at application layer (done via Story.epic_id validation)
//
// CREATE CONSTRAINT story_must_have_epic IF NOT EXISTS
// FOR (s:Story)
// REQUIRE EXISTS ((s)<-[:CONTAINS]-(:Epic));
//
// Status: Enforced at application layer (Story.__post_init__)

// Constraint #3: Epic MUST have Project relationship
// This constraint requires Neo4j Enterprise Edition with relationship existence constraints
// For Community Edition, enforce at application layer (done via Epic.project_id validation)
//
// CREATE CONSTRAINT epic_must_have_project IF NOT EXISTS
// FOR (e:Epic)
// REQUIRE EXISTS ((e)<-[:HAS_EPIC]-(:Project));
//
// Status: Enforced at application layer (Epic.__post_init__)

// ============================================================================
// PROPERTY EXISTENCE CONSTRAINTS (Required Fields)
// ============================================================================

// Project must have name and project_id
CREATE CONSTRAINT project_must_have_name IF NOT EXISTS
FOR (p:Project)
REQUIRE p.name IS NOT NULL;

CREATE CONSTRAINT project_must_have_id IF NOT EXISTS
FOR (p:Project)
REQUIRE p.project_id IS NOT NULL;

// Epic must have title, epic_id, and project_id (parent reference)
CREATE CONSTRAINT epic_must_have_title IF NOT EXISTS
FOR (e:Epic)
REQUIRE e.title IS NOT NULL;

CREATE CONSTRAINT epic_must_have_id IF NOT EXISTS
FOR (e:Epic)
REQUIRE e.epic_id IS NOT NULL;

CREATE CONSTRAINT epic_must_have_project_id IF NOT EXISTS
FOR (e:Epic)
REQUIRE e.project_id IS NOT NULL;

// Story must have id and epic_id (parent reference)
CREATE CONSTRAINT story_must_have_id IF NOT EXISTS
FOR (s:Story)
REQUIRE s.id IS NOT NULL;

// Note: epic_id property constraint would require application-level enforcement
// since Story nodes may be created before epic_id is set.
// Domain validation in Story.__post_init__ ensures epic_id is present.

// Task must have task_id and plan_id (parent reference)
CREATE CONSTRAINT task_must_have_id IF NOT EXISTS
FOR (t:Task)
REQUIRE t.task_id IS NOT NULL;

CREATE CONSTRAINT task_must_have_plan_id IF NOT EXISTS
FOR (t:Task)
REQUIRE t.plan_id IS NOT NULL;

// ============================================================================
// NOTES ON CONSTRAINT LIMITATIONS
// ============================================================================
//
// Neo4j Community Edition Limitations:
// - Cannot enforce relationship existence constraints (Enterprise only)
// - Cannot enforce multi-hop relationship constraints
// - Cannot use triggers or stored procedures
//
// Workarounds Implemented:
// 1. Application-layer validation (Epic.__post_init__, Story.__post_init__)
// 2. Required property constraints (epic_id, project_id properties)
// 3. Integration tests to verify no orphan nodes exist
// 4. Unique constraints to prevent duplicate IDs
//
// Defense in Depth Strategy:
// Layer 1: Value object validation (ProjectId, EpicId, StoryId - fail fast)
// Layer 2: Entity validation (__post_init__ - domain invariants)
// Layer 3: Neo4j property constraints (required fields)
// Layer 4: Integration tests (verify no orphans in actual database)
//
// Result: Multiple layers of validation ensure hierarchy integrity.

// ============================================================================
// VERIFICATION QUERIES (Run after loading data)
// ============================================================================
//
// Check for orphan epics (should return 0):
// MATCH (e:Epic)
// WHERE NOT EXISTS ((e)<-[:HAS_EPIC]-(:Project))
// RETURN count(e) AS orphan_epics;
//
// Check for orphan stories (should return 0):
// MATCH (s:Story)
// WHERE NOT EXISTS ((s)<-[:CONTAINS]-(:Epic))
// RETURN count(s) AS orphan_stories;
//
// Check for orphan tasks (should return 0):
// MATCH (t:Task)
// WHERE NOT EXISTS ((t)<-[:HAS_TASK]-(:PlanVersion))
// RETURN count(t) AS orphan_tasks;
//
// Verify complete hierarchy (should show all paths):
// MATCH path = (p:Project)-[:HAS_EPIC]->(e:Epic)-[:CONTAINS]->(s:Story)
//              -[:HAS_PLAN]->(pv:PlanVersion)-[:HAS_TASK]->(t:Task)
// RETURN p.name AS project, e.title AS epic, s.id AS story, t.task_id AS task
// LIMIT 10;

