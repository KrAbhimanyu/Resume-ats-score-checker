import { beforeEach, describe, expect, it } from 'vitest';
import {
  deleteResumeVersion,
  loadResumeVersions,
  saveResumeVersion,
  ResumeVersion,
} from '../services/resumeVersions';
import { StructuredResume } from '../types/builder';

const resume: StructuredResume = {
  contact_info: { full_name: 'Alex Example' },
  summary: 'Backend engineer.',
  skills: { Languages: ['Python'] },
  experience: [],
  projects: [],
  education: [],
  certifications: [],
};

const createVersion = (id: string, summary = 'Backend engineer.'): ResumeVersion => ({
  id,
  name: `Version ${id}`,
  savedAt: new Date().toISOString(),
  targetRole: 'Backend Engineer',
  targetCompany: 'Example',
  resume: { ...resume, summary },
});

describe('resume version storage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('saves, reloads, and deletes a browser-local version', () => {
    saveResumeVersion(createVersion('one'));
    expect(loadResumeVersions()).toHaveLength(1);
    expect(loadResumeVersions()[0].resume.summary).toBe('Backend engineer.');

    expect(deleteResumeVersion('one')).toEqual([]);
    expect(loadResumeVersions()).toEqual([]);
  });

  it('reports corrupt history rather than silently discarding it', () => {
    window.localStorage.setItem('resume-ats-checker:resume-versions:v1', '{');
    expect(() => loadResumeVersions()).toThrow(/unreadable/i);
  });
});
