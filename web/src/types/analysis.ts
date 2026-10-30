/**
 * Types mirroring the backend Pydantic schemas in backend/app/models/schemas.py
 */

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  service: string;
}

export interface CategoryScore {
  category_id: string;
  category_name: string;
  score: number;
  max_score: number;
  percentage: number;
  explanation: string;
  details: Record<string, unknown>;
}

export interface RequirementMatch {
  requirement: string;
  category: 'skill' | 'experience' | 'education' | 'keyword' | string;
  matched_terms: string[];
  evidence_strength: 'strong' | 'moderate' | 'weak' | string;
  is_mandatory: boolean;
}

export interface MissingRequirement {
  requirement: string;
  category: 'skill' | 'experience' | 'education' | 'keyword' | string;
  importance: 'mandatory' | 'preferred' | 'general' | string;
  reason: string;
  is_evidenced_elsewhere: boolean;
}

export interface Recommendation {
  id: string;
  category: string;
  title: string;
  description: string;
  action_type:
    | 'add_missing_keyword'
    | 'strengthen_evidence'
    | 'improve_formatting'
    | 'add_metrics'
    | 'education_clarity'
    | string;
  priority: 'high' | 'medium' | 'low' | string;
}

export interface DocumentMetadata {
  filename: string;
  file_type: string;
  file_size_bytes: number;
  character_count: number;
  word_count: number;
  extraction_warnings: string[];
}

export interface StrengthItem {
  title: string;
  description: string;
  category: 'formatting' | 'skills' | 'metrics' | 'structure' | 'clarity' | string;
}

export interface BulletImprovement {
  id: string;
  original_text: string;
  issue: string;
  suggested_rewrite: string;
  what_to_add: string;
  action_verb?: string;
  detected_skills: string[];
}

export interface JobSkillAlignment {
  matched_skills: string[];
  missing_from_resume_skills: string[];
  weakly_evidenced_skills: string[];
  ethical_guidance: string;
}

export interface ActionVerbCategory {
  category_name: string;
  verbs: string[];
}

export interface MetricGuidanceItem {
  metric_type: string;
  guiding_question: string;
  example_pattern: string;
}

export interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low' | string;
  completed: boolean;
}

export interface ResumeImprovementAssistant {
  strengths: StrengthItem[];
  bullet_improvements: BulletImprovement[];
  skill_alignment: JobSkillAlignment;
  recommended_verbs: ActionVerbCategory[];
  metric_guidance: MetricGuidanceItem[];
  improvement_checklist: ChecklistItem[];
}

export interface BulletImprovementRequest {
  bullet_text: string;
  target_skills?: string[];
}

export interface BulletImprovementResponse {
  original_text: string;
  is_weak: boolean;
  issues: string[];
  suggested_rewrite: string;
  what_to_add: string;
  recommended_action_verbs: string[];
}

export interface AnalysisResponse {
  overall_score: number;
  score_label: string;
  match_tier: string;
  summary: string;
  category_scores: CategoryScore[];
  matched_requirements: RequirementMatch[];
  missing_requirements: MissingRequirement[];
  keywords_found: string[];
  recommendations: Recommendation[];
  document_metadata: DocumentMetadata;
  improvement_assistant?: ResumeImprovementAssistant;
  limitations_disclaimer: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error?: ApiErrorDetail;
  detail?: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}
