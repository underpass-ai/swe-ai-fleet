/**
 * Type definitions for Planning Service entities
 * These match the protobuf definitions in specs/fleet/planning/v2/planning.proto
 */

export interface Project {
  project_id: string;
  name: string;
  description: string;
  status: 'active' | 'planning' | 'in_progress' | 'completed' | 'archived' | 'cancelled';
  owner: string;
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp
}

export interface Epic {
  epic_id: string;
  project_id: string;
  title: string;
  description: string;
  status: 'active' | 'planning' | 'in_progress' | 'completed' | 'archived' | 'cancelled';
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp
}

export interface Story {
  story_id: string;
  epic_id: string;
  title: string;
  brief: string;
  state: 'BACKLOG' | 'DRAFT' | 'DESIGN' | 'BUILD' | 'TEST' | 'DOCS' | 'DONE';
  dor_score: number; // 0-100
  created_by: string;
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp
}

export interface Task {
  task_id: string;
  plan_id?: string; // Optional - link to plan version
  story_id: string;
  title: string;
  description: string;
  type: string; // development, feature, refactor, testing, etc.
  status: 'todo' | 'in_progress' | 'in_review' | 'blocked' | 'completed' | 'cancelled';
  assigned_to: string;
  estimated_hours: number;
  priority: number; // 1 = highest
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp
}

export interface Plan {
  plan_id: string;
  story_id: string;
  ceremony_id: string;
  title: string;
  description: string;
  approved_by?: string;
  approved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface StoryReviewResult {
  story_id: string;
  plan_preliminary?: {
    title: string;
    description: string;
    tasks_outline?: string[];
    estimated_complexity?: string;
    roles?: string[];
  };
  architect_feedback?: string;
  qa_feedback?: string;
  devops_feedback?: string;
  recommendations?: string[];
  approval_status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewed_at?: string;
  approved_by?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  rejection_reason?: string;
  plan_id?: string; // Plan ID generated after approval
  po_notes?: string;
  po_concerns?: string;
  priority_adjustment?: string;
  po_priority_reason?: string;
}


