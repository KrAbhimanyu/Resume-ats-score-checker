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
