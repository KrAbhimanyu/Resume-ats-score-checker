import { StructuredResume } from '../types/builder';

const STORAGE_KEY = 'resume-ats-checker:resume-versions:v1';

export interface ResumeVersion {
  id: string;
  name: string;
  savedAt: string;
  targetRole: string;
  targetCompany: string;
  resume: StructuredResume;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value && typeof value === 'object' && !Array.isArray(value));

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string');

const isStructuredResume = (value: unknown): value is StructuredResume => {
  if (!isRecord(value) || typeof value.summary !== 'string') return false;
  const contact = value.contact_info;
  const skills = value.skills;
  return (
    isRecord(contact) &&
    typeof contact.full_name === 'string' &&
    isRecord(skills) &&
    Object.values(skills).every(isStringArray) &&
    Array.isArray(value.experience) &&
    value.experience.every(
      (item) =>
        isRecord(item) &&
        typeof item.id === 'string' &&
        typeof item.title === 'string' &&
        typeof item.company === 'string' &&
        isStringArray(item.bullets)
    ) &&
    Array.isArray(value.projects) &&
    value.projects.every(
      (item) =>
        isRecord(item) &&
        typeof item.id === 'string' &&
        typeof item.title === 'string' &&
        isStringArray(item.technologies) &&
        isStringArray(item.bullets)
    ) &&
    Array.isArray(value.education) &&
    value.education.every(
      (item) =>
        isRecord(item) &&
        typeof item.id === 'string' &&
        typeof item.degree === 'string' &&
        typeof item.institution === 'string'
    ) &&
    isStringArray(value.certifications)
  );
};

const isResumeVersion = (value: unknown): value is ResumeVersion => {
  if (!value || typeof value !== 'object') return false;
  const version = value as Partial<ResumeVersion>;
  return (
    typeof version.id === 'string' &&
    typeof version.name === 'string' &&
    typeof version.savedAt === 'string' &&
    typeof version.targetRole === 'string' &&
    typeof version.targetCompany === 'string' &&
    isStructuredResume(version.resume)
  );
};

export const loadResumeVersions = (): ResumeVersion[] => {
  let stored: string | null;
  try {
    stored = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    throw new Error('Browser storage is unavailable. Check your browser privacy settings and try again.');
  }
  if (!stored) return [];

  let parsed: unknown;
  try {
    parsed = JSON.parse(stored);
  } catch {
    throw new Error('Saved resume history is unreadable. Export any needed files before clearing browser storage.');
  }
  if (!Array.isArray(parsed) || !parsed.every(isResumeVersion)) {
    throw new Error('Saved resume history has an unexpected format and cannot be loaded safely.');
  }
  return parsed.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
};

export const saveResumeVersion = (version: ResumeVersion): ResumeVersion[] => {
  const versions = loadResumeVersions();
  const updated = [version, ...versions];
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    throw new Error('The browser could not save this version. Free storage space or remove older site data and try again.');
  }
  return updated;
};

export const updateResumeVersion = (version: ResumeVersion): ResumeVersion[] => {
  const versions = loadResumeVersions();
  if (!versions.some((item) => item.id === version.id)) {
    throw new Error('The saved resume version no longer exists.');
  }
  const updated = versions.map((item) => item.id === version.id ? version : item);
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    throw new Error('The browser could not update this version. Check browser storage availability and try again.');
  }
  return updated.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
};

export const deleteResumeVersion = (versionId: string): ResumeVersion[] => {
  const updated = loadResumeVersions().filter((version) => version.id !== versionId);
  try {
    if (updated.length === 0) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    }
  } catch {
    throw new Error('The browser could not update saved versions. Check browser storage availability and try again.');
  }
  return updated;
};
