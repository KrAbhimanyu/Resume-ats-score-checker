import { beforeEach, describe, expect, it } from 'vitest';
import {
  CAREER_PATHS,
  createCareerStarter,
  generateCoverLetter,
  generateLinkedInProfile,
  generatePortfolioDescriptions,
  loadResumeProfiles,
  makeProfileId,
  RESUME_TEMPLATES,
  saveResumeProfile,
  tailorResumeLocally,
} from '../services/resumeStudio';
import { ResumeProfile, StructuredResume } from '../types/builder';

const resume: StructuredResume = {
  contact_info: { full_name: 'Alex Example', email: 'alex@example.com' },
  summary: 'Experienced analyst.',
  skills: { 'Core Skills': ['SQL', 'Python', 'Excel'] },
  experience: [{
    id: 'exp-1',
    title: 'Analyst',
    company: 'Example Co',
    bullets: ['Built Python SQL reports for a 20-person team.', 'Presented quarterly findings.'],
  }],
  projects: [{
    id: 'project-1',
    title: 'Sales dashboard',
    technologies: ['Python', 'SQL'],
    bullets: ['Built dashboard for 3 teams.'],
  }],
  education: [],
  certifications: [],
};

describe('resume studio local helpers', () => {
  beforeEach(() => window.localStorage.clear());

  it('provides more than 50 ATS-safe templates with industry groups', () => {
    expect(RESUME_TEMPLATES.length).toBeGreaterThanOrEqual(50);
    expect(new Set(RESUME_TEMPLATES.map((template) => template.id)).size).toBe(RESUME_TEMPLATES.length);
    expect(new Set(RESUME_TEMPLATES.map((template) => template.industry)).size).toBeGreaterThan(5);
  });

  it('creates distinct career-path starting structures without inventing personal information', () => {
    expect(CAREER_PATHS).toHaveLength(4);
    expect(createCareerStarter('fresher').custom_sections).toHaveProperty('Relevant Coursework');
    expect(createCareerStarter('executive').custom_sections).toHaveProperty('Leadership Highlights');
    expect(createCareerStarter('career-change').contact_info.full_name).toBe('');
  });

  it('tailors by reordering existing evidence without inventing new qualifications', () => {
    const result = tailorResumeLocally(resume, 'Data Analyst', 'Data analyst SQL Python reporting');
    expect(result.resume.skills['Core Skills'].slice(0, 2)).toEqual(['SQL', 'Python']);
    expect(result.resume.experience[0].bullets).toHaveLength(2);
    expect(result.notes.join(' ')).toMatch(/No skills.*were added/i);
    expect(result.resume.skills['Core Skills']).toHaveLength(resume.skills['Core Skills'].length);
  });

  it('generates editable companion drafts from resume evidence', () => {
    const coverLetter = generateCoverLetter(resume, 'Data Analyst', 'Acme', 'SQL and Python experience.');
    const linkedIn = generateLinkedInProfile(resume, 'Data Analyst');
    const portfolio = generatePortfolioDescriptions(resume);
    expect(coverLetter).toContain('Built Python SQL reports');
    expect(coverLetter).toContain('Acme Hiring Team');
    expect(linkedIn).toContain('HEADLINE');
    expect(portfolio).toContain('Sales dashboard');
  });

  it('saves and reloads several isolated browser profiles', () => {
    const createProfile = (name: string): ResumeProfile => ({
      id: makeProfileId(),
      name,
      careerPath: 'experienced',
      industry: 'Technology',
      templateId: RESUME_TEMPLATES[0].id,
      internationalFormat: 'us',
      updatedAt: new Date().toISOString(),
      resume,
    });
    saveResumeProfile(createProfile('Backend'));
    saveResumeProfile(createProfile('Analyst'));
    expect(loadResumeProfiles().map((profile) => profile.name)).toEqual(['Analyst', 'Backend']);
  });
});
