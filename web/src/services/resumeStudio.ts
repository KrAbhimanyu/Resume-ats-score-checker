import {
  CareerPath, ResumeAIResponse, ResumeAITone, ResumeAIOperation, ResumeProfile,
  ResumeTemplate, StructuredResume,
} from '../types/builder';
import { getApiBaseUrl } from './analysisApi';
import { getResumeSessionToken } from './resumeCloud';

const templateFamilies = [
  { name: 'Essential', industry: 'General', description: 'Classic headings and compact spacing.' },
  { name: 'Modern', industry: 'IT & Software Development', description: 'Modern typography with a clear hierarchy.' },
  { name: 'QA', industry: 'Software Testing & QA', description: 'Quality engineering, test automation, and release evidence.' },
  { name: 'Professional', industry: 'Business & Management', description: 'Formal structure for corporate roles.' },
  { name: 'Academic', industry: 'Education', description: 'Education-forward structure for teaching and research.' },
  { name: 'Technical', industry: 'Engineering', description: 'Skills and project evidence are easy to scan.' },
  { name: 'Creative', industry: 'Design & Media', description: 'Restrained visual accent; still single-column.' },
  { name: 'Healthcare', industry: 'Healthcare', description: 'Credentials and clinical experience focused.' },
  { name: 'Finance', industry: 'Banking & Finance', description: 'Conservative formatting for financial roles.' },
  { name: 'Marketing', industry: 'Marketing', description: 'Campaign, audience, and verified growth outcomes.' },
  { name: 'Sales', industry: 'Sales', description: 'Customer relationships, pipeline, and verified outcomes.' },
  { name: 'HR', industry: 'Human Resources', description: 'People operations, talent, and workplace programs.' },
  { name: 'Operations', industry: 'Operations', description: 'Emphasizes delivery and operational scope.' },
  { name: 'Executive', industry: 'Leadership', description: 'Leadership summary and measurable outcomes.' },
];

const palettes = [
  { name: 'Navy', accent: '#1e3a8a' },
  { name: 'Teal', accent: '#0f766e' },
  { name: 'Graphite', accent: '#334155' },
  { name: 'Burgundy', accent: '#881337' },
  { name: 'Forest', accent: '#166534' },
  { name: 'Indigo', accent: '#4338ca' },
];

export const RESUME_TEMPLATES: ResumeTemplate[] = templateFamilies.flatMap((family) =>
  palettes.map((palette) => ({
    id: `ats-${family.name.toLowerCase()}-${palette.name.toLowerCase()}`,
    name: `${family.name} ${palette.name}`,
    family: family.name,
    industry: family.industry,
    accent: palette.accent,
    font: family.name === 'Academic' || family.name === 'Finance' ? 'Georgia' : 'Arial',
    description: `${family.description} ${palette.name} accent.`,
  }))
);

export const INTERNATIONAL_FORMATS = [
  { id: 'us', name: 'United States / Canada', details: 'Reverse-chronological, concise, no photo or sensitive personal details.' },
  { id: 'uk', name: 'United Kingdom', details: 'CV-style, concise, no photo or date of birth.' },
  { id: 'eu', name: 'European Union (general)', details: 'Clear dates and international contact conventions; requirements vary by country.' },
  { id: 'india', name: 'India', details: 'Education and experience order can be tailored; avoid unnecessary sensitive details.' },
  { id: 'japan', name: 'Japan (English resume)', details: 'English-language, structured career history; not a Japanese rirekisho translation.' },
] as const;

export const CAREER_PATHS: Array<{ id: CareerPath; name: string; guidance: string }> = [
  { id: 'fresher', name: 'Fresher / graduate', guidance: 'Prioritize education, projects, internships, coursework, and verified skills.' },
  { id: 'experienced', name: 'Experienced professional', guidance: 'Prioritize recent experience, ownership, outcomes, and relevant technical skills.' },
  { id: 'executive', name: 'Executive / leadership', guidance: 'Prioritize leadership scope, strategy, organization size, and measurable business outcomes.' },
  { id: 'career-change', name: 'Career change', guidance: 'Lead with transferable skills, relevant projects, and verified transition experience.' },
];

export const INDUSTRIES = [
  'IT & Software Development', 'Software Testing & QA', 'Banking & Finance',
  'Marketing', 'Sales', 'Human Resources', 'Business & Management', 'Engineering',
  'Healthcare', 'Education', 'Design & Media', 'Operations', 'Public Sector', 'General',
  'Technology', 'Finance', 'Education & Research', 'Sales & Marketing',
];

export const RESUME_TONES: Array<{ id: ResumeAITone; label: string }> = [
  { id: 'professional', label: 'Professional' },
  { id: 'technical', label: 'Technical' },
  { id: 'executive', label: 'Executive' },
  { id: 'entry-level', label: 'Entry-Level' },
  { id: 'experienced', label: 'Experienced' },
  { id: 'concise', label: 'Concise' },
];

export async function generateResumeAI(input: {
  operation: ResumeAIOperation;
  resume: StructuredResume;
  sourceText: string;
  targetRole: string;
  jobDescription: string;
  industry: string;
  experienceLevel: string;
  tone: ResumeAITone;
}): Promise<ResumeAIResponse> {
  const token = getResumeSessionToken();
  const response = await fetch(`${getApiBaseUrl()}/api/v1/builder/ai`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      operation: input.operation,
      resume: input.resume,
      source_text: input.sourceText,
      target_role: input.targetRole,
      job_description: input.jobDescription,
      industry: input.industry,
      experience_level: input.experienceLevel,
      tone: input.tone,
    }),
  });
  if (!response.ok) {
    let message = `AI writing failed with HTTP ${response.status}.`;
    try {
      const payload = await response.json() as { detail?: string };
      message = payload.detail || message;
    } catch {
      // Use the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }
  return await response.json() as ResumeAIResponse;
}

export const createEmptyResume = (): StructuredResume => ({
  contact_info: { full_name: '', email: '', phone: '', location: '', linkedin: '', github: '' },
  summary: '',
  skills: { 'Core Skills': [] },
  experience: [],
  projects: [],
  education: [],
  certifications: [],
  custom_sections: {},
});

export const createCareerStarter = (careerPath: CareerPath): StructuredResume => {
  const resume = createEmptyResume();
  if (careerPath === 'fresher') {
    resume.custom_sections = { 'Relevant Coursework': [], 'Internships': [] };
  } else if (careerPath === 'executive') {
    resume.custom_sections = { 'Leadership Highlights': [], 'Board & Advisory': [] };
  } else if (careerPath === 'career-change') {
    resume.custom_sections = { 'Transferable Skills': [], 'Relevant Projects': [] };
  }
  return resume;
};

export const generateCoverLetter = (
  resume: StructuredResume,
  role: string,
  company: string,
  jobDescription: string
): string => {
  const matchedSkills = Object.values(resume.skills).flat().filter((skill) =>
    jobDescription.toLowerCase().includes(skill.toLowerCase())
  );
  const firstExperience = resume.experience.find((item) => item.bullets.length > 0);
  const evidence = firstExperience?.bullets[0];
  return [
    `${resume.contact_info.full_name || '[Your name]'}`,
    `${resume.contact_info.email || '[Email]'}${resume.contact_info.phone ? ` | ${resume.contact_info.phone}` : ''}`,
    '',
    `Dear ${company ? `${company} Hiring Team` : 'Hiring Team'},`,
    '',
    `I am applying for the ${role || '[target role]'} position${company ? ` at ${company}` : ''}. My background includes ${matchedSkills.length ? matchedSkills.join(', ') : '[relevant skills supported by your experience]'}.`,
    '',
    evidence
      ? `In my role as ${firstExperience?.title} at ${firstExperience?.company}, I ${evidence.replace(/[.!?]+$/, '')}.`
      : 'One relevant example from my experience is [describe a verified achievement relevant to the role].',
    '',
    'I would welcome the opportunity to discuss how my verified experience can support your team. Thank you for your consideration.',
    '',
    `Sincerely,\n${resume.contact_info.full_name || '[Your name]'}`,
    '',
    'Draft only: verify every statement and replace bracketed placeholders before sending.',
  ].join('\n');
};

export const generateLinkedInProfile = (resume: StructuredResume, targetRole: string): string => {
  const skills = Object.values(resume.skills).flat().slice(0, 8);
  const recent = resume.experience[0];
  return [
    `HEADLINE\n${targetRole || '[Target role]'}${skills.length ? ` | ${skills.slice(0, 4).join(' | ')}` : ' | [Verified specialty]'}`,
    '',
    'ABOUT',
    resume.summary || `I am a professional focused on [your verified specialization]. Add a concise description of your experience and the work you want to do next.`,
    '',
    `EXPERIENCE STARTER\n${recent ? `${recent.title} at ${recent.company}` : '[Role] at [Organization]'}`,
    ...(recent?.bullets.slice(0, 3) ?? ['Add a verified accomplishment and outcome.']),
    '',
    'Review contact details and claims before publishing.',
  ].join('\n');
};

export const generatePortfolioDescriptions = (resume: StructuredResume): string =>
  resume.projects.length
    ? resume.projects.map((project) => [
        project.title,
        project.technologies.length ? `Tools: ${project.technologies.join(', ')}` : '',
        ...project.bullets,
        'Add a short description of your contribution and link to a public demo or repository if appropriate.',
      ].filter(Boolean).join('\n')).join('\n\n---\n\n')
    : 'Add a project to your resume to generate a portfolio description. Include your role, the problem, your approach, and verified outcomes.';

export const tailorResumeLocally = (
  resume: StructuredResume,
  role: string,
  jobDescription: string
): { resume: StructuredResume; notes: string[] } => {
  const terms = jobDescription.toLowerCase();
  const next = JSON.parse(JSON.stringify(resume)) as StructuredResume;
  const skills = Object.entries(next.skills);
  for (const [, values] of skills) {
    values.sort((a, b) => Number(terms.includes(b.toLowerCase())) - Number(terms.includes(a.toLowerCase())));
  }
  next.skills = Object.fromEntries(skills);
  next.experience = next.experience.map((item) => ({
    ...item,
    bullets: [...item.bullets].sort(
      (a, b) =>
        Number((b.match(/\w+/g) || []).filter((word) => terms.includes(word.toLowerCase())).length) -
        Number((a.match(/\w+/g) || []).filter((word) => terms.includes(word.toLowerCase())).length)
    ),
  }));
  const matchingSkills = Object.values(next.skills).flat().filter((skill) => terms.includes(skill.toLowerCase()));
  return {
    resume: next,
    notes: [
      `Reordered existing skills and experience bullets against the ${role || 'target role'} description.`,
      `${matchingSkills.length} existing skills appear in the job description.`,
      'No skills, experience, or metrics were added. Review the order and verify each claim.',
    ],
  };
};

const PROFILE_STORAGE_KEY = 'resume-ats-checker:studio-profiles:v1';

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value && typeof value === 'object' && !Array.isArray(value));

const isStringList = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string');

const isStructuredResume = (value: unknown): value is StructuredResume => {
  if (!isRecord(value) || typeof value.summary !== 'string') return false;
  const contact = value.contact_info;
  const skills = value.skills;
  const customSections = value.custom_sections;
  return (
    isRecord(contact) &&
    typeof contact.full_name === 'string' &&
    isRecord(skills) &&
    Object.values(skills).every(isStringList) &&
    Array.isArray(value.experience) &&
    value.experience.every((entry) =>
      isRecord(entry) &&
      typeof entry.id === 'string' &&
      typeof entry.title === 'string' &&
      typeof entry.company === 'string' &&
      isStringList(entry.bullets)
    ) &&
    Array.isArray(value.projects) &&
    value.projects.every((entry) =>
      isRecord(entry) &&
      typeof entry.id === 'string' &&
      typeof entry.title === 'string' &&
      isStringList(entry.technologies) &&
      isStringList(entry.bullets)
    ) &&
    Array.isArray(value.education) &&
    value.education.every((entry) =>
      isRecord(entry) &&
      typeof entry.id === 'string' &&
      typeof entry.degree === 'string' &&
      typeof entry.institution === 'string'
    ) &&
    isStringList(value.certifications) &&
    (customSections === undefined ||
      (isRecord(customSections) && Object.values(customSections).every(isStringList)))
  );
};

const isProfile = (value: unknown): value is ResumeProfile => {
  if (!value || typeof value !== 'object') return false;
  const profile = value as Partial<ResumeProfile>;
  return (
    typeof profile.id === 'string' &&
    typeof profile.name === 'string' &&
    typeof profile.updatedAt === 'string' &&
    typeof profile.industry === 'string' &&
    typeof profile.templateId === 'string' &&
    typeof profile.internationalFormat === 'string' &&
    ['fresher', 'experienced', 'executive', 'career-change'].includes(profile.careerPath || '') &&
    isStructuredResume(profile.resume)
  );
};

export const loadResumeProfiles = (): ResumeProfile[] => {
  let value: string | null;
  try {
    value = window.localStorage.getItem(PROFILE_STORAGE_KEY);
  } catch {
    throw new Error('Browser storage is unavailable; check privacy settings before saving profiles.');
  }
  if (!value) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error('Saved profiles are unreadable. Export important work before clearing browser site data.');
  }
  if (!Array.isArray(parsed) || !parsed.every(isProfile)) {
    throw new Error('Saved profiles have an unexpected format and cannot be loaded safely.');
  }
  return parsed;
};

export const saveResumeProfile = (profile: ResumeProfile): ResumeProfile[] => {
  const profiles = loadResumeProfiles();
  const updated = [profile, ...profiles.filter((item) => item.id !== profile.id)];
  try {
    window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(updated));
  } catch {
    throw new Error('Browser storage is full or unavailable. Export your profile and free storage before retrying.');
  }
  return updated;
};

export const removeResumeProfile = (id: string): ResumeProfile[] => {
  const updated = loadResumeProfiles().filter((profile) => profile.id !== id);
  try {
    if (updated.length) window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(updated));
    else window.localStorage.removeItem(PROFILE_STORAGE_KEY);
  } catch {
    throw new Error('Could not update browser profile storage.');
  }
  return updated;
};

export const makeProfileId = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

export const downloadTextFile = (name: string, text: string): void => {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

export const careerPathLabel = (careerPath: CareerPath): string =>
  CAREER_PATHS.find((path) => path.id === careerPath)?.name ?? careerPath;
