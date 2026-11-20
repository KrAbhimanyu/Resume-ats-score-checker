export type TargetMode = 'faang_big_tech' | 'any_company';

export interface ContactInfo {
  full_name: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin?: string;
  github?: string;
}

export interface ExperienceItem {
  id: string;
  title: string;
  company: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  bullets: string[];
}

export interface ProjectItem {
  id: string;
  title: string;
  technologies: string[];
  bullets: string[];
}

export interface EducationItem {
  id: string;
  degree: string;
  institution: string;
  location?: string;
  graduation_date?: string;
  details?: string;
}

export interface StructuredResume {
  contact_info: ContactInfo;
  summary: string;
  skills: Record<string, string[]>;
  experience: ExperienceItem[];
  projects: ProjectItem[];
  education: EducationItem[];
  certifications: string[];
  custom_sections?: Record<string, string[]>;
}

export interface RequirementGapItem {
  name: string;
  category: string;
  status: 'matched' | 'missing' | 'weakly_evidenced' | string;
  reason: string;
  evidence_source: string;
  actionable_guidance: string;
  requires_user_confirmation: boolean;
}

export interface ProposedChange {
  id: string;
  section: 'summary' | 'skills' | 'experience' | 'projects' | 'certifications' | string;
  target_item_id?: string;
  bullet_index?: number;
  original_text: string;
  proposed_text: string;
  rationale: string;
  evidence_source: string;
  what_to_verify: string;
  is_accepted: boolean;
}

export interface PrioritizedImprovement {
  id: string;
  title: string;
  priority: 'high' | 'medium' | 'low' | string;
  reason: string;
  requires_confirmation: boolean;
}

export interface TargetedAnalysisResponse {
  target_mode: string;
  company_name: string;
  industry?: string;
  job_title: string;
  has_job_description: boolean;
  guidance_source: string;
  summary_overview: string;
  matched_skills: RequirementGapItem[];
  missing_requirements: RequirementGapItem[];
  weakly_evidenced: RequirementGapItem[];
  structure_feedback: string[];
  prioritized_improvements: PrioritizedImprovement[];
  proposed_changes: ProposedChange[];
  draft_resume: StructuredResume;
  disclaimer: string;
}

export interface ExportResumeRequest {
  format: 'pdf' | 'docx';
  resume: StructuredResume;
  filename?: string;
  template_id?: string;
  international_format?: string;
}

export type CareerPath = 'fresher' | 'experienced' | 'executive' | 'career-change';

export interface ResumeTemplate {
  id: string;
  name: string;
  family: string;
  industry: string;
  accent: string;
  font: string;
  description: string;
}

export interface ResumeProfile {
  id: string;
  name: string;
  careerPath: CareerPath;
  industry: string;
  templateId: string;
  fontFamily?: string;
  previewSections?: string[];
  hiddenSections?: string[];
  internationalFormat: string;
  updatedAt: string;
  resume: StructuredResume;
  coverLetter?: string;
  linkedInProfile?: string;
  portfolioDescription?: string;
}

export type ResumeAITone =
  | 'professional'
  | 'technical'
  | 'executive'
  | 'entry-level'
  | 'experienced'
  | 'concise';

export type ResumeAIOperation =
  | 'summary'
  | 'experience'
  | 'achievement'
  | 'skills'
  | 'project'
  | 'bullet'
  | 'optimize';

export interface ResumeAIResponse {
  operation: ResumeAIOperation;
  suggestion?: string | null;
  proposed_resume?: StructuredResume | null;
  skill_categories: Record<string, string[]>;
  suggested_missing_skills: string[];
  disclaimer: string;
}

export interface ResumeCloudDocument<T = unknown> {
  id: string;
  document_type: 'profile' | 'version';
  name: string;
  document: T;
  created_at: string;
  updated_at: string;
}
