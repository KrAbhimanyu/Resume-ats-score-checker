import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowDownToLine, ArrowDown, ArrowUp, BriefcaseBusiness, Copy, FileText, Languages, Plus, Save,
  Sparkles, Trash2, UserRound, WandSparkles, Check,
} from 'lucide-react';
import {
  StructuredResume, ResumeProfile, CareerPath, ResumeAIOperation, ResumeAIResponse, ResumeAITone,
} from '../types/builder';
import {
  CAREER_PATHS, createCareerStarter, downloadTextFile, generateCoverLetter,
  generateLinkedInProfile, generatePortfolioDescriptions, INDUSTRIES,
  INTERNATIONAL_FORMATS, loadResumeProfiles, makeProfileId, removeResumeProfile,
  RESUME_TEMPLATES, RESUME_TONES, saveResumeProfile, tailorResumeLocally, generateResumeAI,
} from '../services/resumeStudio';
import { exportResume } from '../services/analysisApi';
import {
  deleteCloudResumeDocument, getResumeSessionToken, loadCloudResumeDocuments,
  saveCloudResumeDocument,
} from '../services/resumeCloud';

const splitLines = (value: string): string[] =>
  value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

const downloadBlob = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

const initialResume = createCareerStarter('fresher');
const careerSectionOrder: Record<CareerPath, string[]> = {
  fresher: ['summary', 'education', 'projects', 'experience', 'skills', 'certifications'],
  experienced: ['summary', 'experience', 'skills', 'projects', 'education', 'certifications'],
  executive: ['summary', 'experience', 'custom', 'skills', 'education', 'projects', 'certifications'],
  'career-change': ['summary', 'skills', 'projects', 'experience', 'education', 'certifications'],
};

export const ResumeStudioPage: React.FC = () => {
  const [resume, setResume] = useState<StructuredResume>(initialResume);
  const [careerPath, setCareerPath] = useState<CareerPath>('fresher');
  const [industry, setIndustry] = useState('IT & Software Development');
  const [templateId, setTemplateId] = useState(RESUME_TEMPLATES[0].id);
  const [fontFamily, setFontFamily] = useState('Arial');
  const [sectionOrder, setSectionOrder] = useState<string[]>(careerSectionOrder.fresher);
  const [hiddenSections, setHiddenSections] = useState<string[]>([]);
  const [sectionToAdd, setSectionToAdd] = useState('');
  const [internationalFormat, setInternationalFormat] = useState('us');
  const [profileName, setProfileName] = useState('My Resume');
  const [profiles, setProfiles] = useState<ResumeProfile[]>([]);
  const [activeProfileId, setActiveProfileId] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [tailoringNotes, setTailoringNotes] = useState<string[]>([]);
  const [role, setRole] = useState('');
  const [company, setCompany] = useState('');
  const [coverLetter, setCoverLetter] = useState('');
  const [linkedInProfile, setLinkedInProfile] = useState('');
  const [portfolioDescription, setPortfolioDescription] = useState('');
  const [customSectionTitle, setCustomSectionTitle] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [isExporting, setIsExporting] = useState<'pdf' | 'docx' | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiOperation, setAiOperation] = useState<ResumeAIOperation>('summary');
  const [aiTone, setAiTone] = useState<ResumeAITone>('professional');
  const [aiSourceText, setAiSourceText] = useState('');
  const [aiExperienceIndex, setAiExperienceIndex] = useState(0);
  const [aiProjectIndex, setAiProjectIndex] = useState(0);
  const [aiResult, setAiResult] = useState<ResumeAIResponse | null>(null);
  const [cloudStatus, setCloudStatus] = useState('');
  const [cloudLoading, setCloudLoading] = useState(false);

  useEffect(() => {
    let active = true;
    try {
      const saved = loadResumeProfiles();
      setProfiles(saved);
      if (saved.length) {
        setActiveProfileId(saved[0].id);
        setProfileName(saved[0].name);
        setCareerPath(saved[0].careerPath);
        setIndustry(saved[0].industry);
        setTemplateId(saved[0].templateId);
        setFontFamily(saved[0].fontFamily || RESUME_TEMPLATES.find((item) => item.id === saved[0].templateId)?.font || 'Arial');
        setSectionOrder(saved[0].previewSections || careerSectionOrder[saved[0].careerPath]);
        setHiddenSections(saved[0].hiddenSections || []);
        setInternationalFormat(saved[0].internationalFormat);
        setResume(saved[0].resume);
        setCoverLetter(saved[0].coverLetter || '');
        setLinkedInProfile(saved[0].linkedInProfile || '');
        setPortfolioDescription(saved[0].portfolioDescription || '');
      }
    } catch (loadError: unknown) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load saved profiles.');
    }
    const token = getResumeSessionToken();
    if (token) {
      setCloudLoading(true);
      loadCloudResumeDocuments<ResumeProfile>(token, 'profile')
        .then((documents) => {
          if (!active) return;
          const remoteProfiles = documents
            .map((item) => item.document)
            .filter((item): item is ResumeProfile =>
              Boolean(item && typeof item.id === 'string' && typeof item.name === 'string' && item.resume)
            );
          const mergedById = new Map(loadResumeProfiles().map((profile) => [profile.id, profile]));
          remoteProfiles.forEach((remote) => {
            const local = mergedById.get(remote.id);
            if (!local || remote.updatedAt >= local.updatedAt) mergedById.set(remote.id, remote);
          });
          remoteProfiles.forEach((remote) => {
            const local = loadResumeProfiles().find((item) => item.id === remote.id);
            if (!local || remote.updatedAt >= local.updatedAt) saveResumeProfile(remote);
          });
          const merged = [...mergedById.values()].sort((first, second) =>
            second.updatedAt.localeCompare(first.updatedAt)
          );
          setProfiles(merged);
          if (merged.length) {
            const profile = merged[0];
            setActiveProfileId(profile.id);
            setProfileName(profile.name);
            setCareerPath(profile.careerPath);
            setIndustry(profile.industry);
            setTemplateId(profile.templateId);
            setFontFamily(profile.fontFamily || RESUME_TEMPLATES.find((item) => item.id === profile.templateId)?.font || 'Arial');
            setSectionOrder(profile.previewSections || careerSectionOrder[profile.careerPath]);
            setHiddenSections(profile.hiddenSections || []);
            setInternationalFormat(profile.internationalFormat);
            setResume(profile.resume);
            setCoverLetter(profile.coverLetter || '');
            setLinkedInProfile(profile.linkedInProfile || '');
            setPortfolioDescription(profile.portfolioDescription || '');
          }
          setCloudStatus('Account profiles loaded. Local-only drafts are preserved; select and save them to sync.');
          setCloudLoading(false);
        })
        .catch((cloudError: unknown) => {
          if (active) {
            setCloudStatus(cloudError instanceof Error ? cloudError.message : 'Unable to load cloud profiles.');
            setCloudLoading(false);
          }
        });
    } else {
      setCloudStatus('Local browser storage is active. Sign in through Career Platform to enable encrypted cloud sync.');
    }
    return () => { active = false; };
  }, []);

  const selectedTemplate = useMemo(
    () => RESUME_TEMPLATES.find((template) => template.id === templateId) || RESUME_TEMPLATES[0],
    [templateId]
  );
  const filteredTemplates = useMemo(
    () => RESUME_TEMPLATES.filter(
      (template) =>
        industry === 'General' ||
        template.industry === industry ||
        template.industry === 'General' ||
        (industry === 'Technology' && template.industry === 'IT & Software Development') ||
        (industry === 'Finance' && template.industry === 'Banking & Finance') ||
        (industry === 'Education & Research' && template.industry === 'Education') ||
        (industry === 'Sales & Marketing' && ['Sales', 'Marketing'].includes(template.industry))
    ),
    [industry]
  );
  const formatPreset = INTERNATIONAL_FORMATS.find((format) => format.id === internationalFormat);

  const updateContact = (field: keyof StructuredResume['contact_info'], value: string) => {
    setResume((current) => ({
      ...current,
      contact_info: { ...current.contact_info, [field]: value },
    }));
  };

  const updateExperience = (index: number, patch: Partial<StructuredResume['experience'][number]>) => {
    setResume((current) => ({
      ...current,
      experience: current.experience.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
    }));
  };

  const updateEducation = (index: number, patch: Partial<StructuredResume['education'][number]>) => {
    setResume((current) => ({
      ...current,
      education: current.education.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
    }));
  };

  const addCustomSection = () => {
    const title = customSectionTitle.trim();
    if (!title) {
      setError('Enter a title for the custom section.');
      return;
    }
    if (Object.keys(resume.custom_sections || {}).some((item) => item.toLowerCase() === title.toLowerCase())) {
      setError('A section with that title already exists.');
      return;
    }
    setResume((current) => ({
      ...current,
      custom_sections: { ...current.custom_sections, [title]: [] },
    }));
    if (!sectionOrder.includes('custom')) setSectionOrder((current) => [...current, 'custom']);
    setCustomSectionTitle('');
    setError('');
  };

  const saveProfile = async () => {
    const profile: ResumeProfile = {
      id: activeProfileId || makeProfileId(),
      name: profileName.trim() || resume.contact_info.full_name.trim() || 'Untitled profile',
      careerPath,
      industry,
      templateId,
      fontFamily,
      previewSections: sectionOrder,
      hiddenSections,
      internationalFormat,
      updatedAt: new Date().toISOString(),
      resume: JSON.parse(JSON.stringify(resume)) as StructuredResume,
      coverLetter,
      linkedInProfile,
      portfolioDescription,
    };
    try {
      setProfiles(saveResumeProfile(profile));
      setActiveProfileId(profile.id);
      setProfileName(profile.name);
      const token = getResumeSessionToken();
      if (token) {
        await saveCloudResumeDocument(token, {
          id: profile.id, document_type: 'profile', name: profile.name, document: profile,
        });
        setCloudStatus('Profile saved locally and synced with your account.');
      }
      setNotice(`Saved “${profile.name}”${token ? ' on this device and to your account.' : ' on this device.'}`);
      setError('');
    } catch (saveError: unknown) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save profile.');
    }
  };

  const createNewProfile = () => {
    const id = makeProfileId();
    setActiveProfileId(id);
    setProfileName('New profile');
    setCareerPath('fresher');
    setIndustry('IT & Software Development');
    setTemplateId(RESUME_TEMPLATES[0].id);
    setFontFamily('Arial');
    setSectionOrder(careerSectionOrder.fresher);
    setHiddenSections([]);
    setInternationalFormat('us');
    setResume(createCareerStarter('fresher'));
    setCoverLetter('');
    setLinkedInProfile('');
    setPortfolioDescription('');
    setTailoringNotes([]);
    setNotice('Started a new profile. Save it to keep it in this browser.');
    setError('');
  };

  const selectProfile = (id: string) => {
    if (!id) {
      setActiveProfileId('');
      setProfileName('My Resume');
      setNotice('Working on the current draft. Saving will create a separate profile.');
      setError('');
      return;
    }
    const profile = profiles.find((item) => item.id === id);
    if (!profile) return;
    setActiveProfileId(profile.id);
    setProfileName(profile.name);
    setCareerPath(profile.careerPath);
    setIndustry(profile.industry);
    setTemplateId(profile.templateId);
    setFontFamily(profile.fontFamily || RESUME_TEMPLATES.find((item) => item.id === profile.templateId)?.font || 'Arial');
    setSectionOrder(profile.previewSections || careerSectionOrder[profile.careerPath]);
    setHiddenSections(profile.hiddenSections || []);
    setInternationalFormat(profile.internationalFormat);
    setResume(profile.resume);
    setCoverLetter(profile.coverLetter || '');
    setLinkedInProfile(profile.linkedInProfile || '');
    setPortfolioDescription(profile.portfolioDescription || '');
    setNotice(`Loaded “${profile.name}”.`);
    setError('');
  };

  const duplicateProfile = async () => {
    const source = profiles.find((item) => item.id === activeProfileId);
    if (!source) {
      setError('Save a profile before duplicating it.');
      return;
    }
    const duplicate = {
      ...source,
      id: makeProfileId(),
      name: `${source.name} copy`,
      updatedAt: new Date().toISOString(),
      resume: JSON.parse(JSON.stringify(source.resume)) as StructuredResume,
    };
    try {
      setProfiles(saveResumeProfile(duplicate));
      const token = getResumeSessionToken();
      if (token) {
        await saveCloudResumeDocument(token, {
          id: duplicate.id, document_type: 'profile', name: duplicate.name, document: duplicate,
        });
        setCloudStatus('Duplicated profile synced with your account.');
      }
      setActiveProfileId(duplicate.id);
      setProfileName(duplicate.name);
      setResume(duplicate.resume);
      setNotice(`Duplicated “${source.name}”.`);
      setError('');
    } catch (duplicateError: unknown) {
      setError(duplicateError instanceof Error ? duplicateError.message : 'Unable to duplicate profile.');
    }
  };

  const deleteProfile = async () => {
    const profile = profiles.find((item) => item.id === activeProfileId);
    if (!profile || !window.confirm(`Delete “${profile.name}”${getResumeSessionToken() ? ' from this browser and your account' : ' from this browser'}?`)) return;
    try {
      const updated = removeResumeProfile(profile.id);
      setProfiles(updated);
      const token = getResumeSessionToken();
      if (token) {
        await deleteCloudResumeDocument(token, profile.id);
        setCloudStatus('Profile deleted from this device and your account.');
      }
      setActiveProfileId('');
      setProfileName('My Resume');
      setCareerPath('fresher');
      setResume(createCareerStarter('fresher'));
      setSectionOrder(careerSectionOrder.fresher);
      setHiddenSections([]);
      setNotice(`Deleted “${profile.name}”${token ? ' from this device and your account.' : ' from this browser.'}`);
      setError('');
    } catch (deleteError: unknown) {
      setError(deleteError instanceof Error ? deleteError.message : 'Unable to delete profile.');
    }
  };

  const handleTailor = () => {
    if (!jobDescription.trim() || !jobTitle.trim()) {
      setError('Enter both a target role and a job description before tailoring.');
      return;
    }
    const tailored = tailorResumeLocally(resume, jobTitle, jobDescription);
    setResume(tailored.resume);
    setTailoringNotes(tailored.notes);
    setNotice('Reordered existing resume content for this role. No new qualifications were invented.');
    setError('');
  };

  const handleExport = async (format: 'pdf' | 'docx') => {
    setIsExporting(format);
    setError('');
    try {
      const base = (resume.contact_info.full_name || 'resume').trim().replace(/[^a-zA-Z0-9_-]+/g, '_');
      const blob = await exportResume(
        resume,
        format,
        `${base}_${selectedTemplate.id}`,
        undefined,
        {
          templateId: selectedTemplate.id,
          internationalFormat,
          fontFamily,
          sectionOrder,
          hiddenSections,
        }
      );
      downloadBlob(blob, `${base}_${selectedTemplate.id}.${format}`);
      setNotice(`Exported the ${selectedTemplate.name} ${format.toUpperCase()} resume.`);
    } catch (exportError: unknown) {
      setError(exportError instanceof Error ? exportError.message : 'Resume export failed.');
    } finally {
      setIsExporting(null);
    }
  };

  const generateDocuments = () => {
    setCoverLetter(generateCoverLetter(resume, role || jobTitle, company, jobDescription));
    setLinkedInProfile(generateLinkedInProfile(resume, role || jobTitle));
    setPortfolioDescription(generatePortfolioDescriptions(resume));
    setNotice('Created editable document drafts from your profile. Review every claim before publishing.');
    setError('');
  };

  const downloadDocument = (filename: string, value: string) => {
    if (!value.trim()) {
      setError('Generate or write the document before downloading it.');
      return;
    }
    downloadTextFile(filename, value);
  };

  const setCareerStarter = (value: CareerPath) => {
    if (!window.confirm('Start this career-path layout? Existing resume content in the current draft will be replaced.')) return;
    setCareerPath(value);
    setResume(createCareerStarter(value));
    setSectionOrder(careerSectionOrder[value]);
    setHiddenSections([]);
    setTailoringNotes([]);
    setNotice(`${CAREER_PATHS.find((item) => item.id === value)?.name} layout started. Add only accurate information.`);
    setError('');
  };

  const renderPreviewSection = (section: string): React.ReactNode => {
    if (section === 'summary') {
      return resume.summary ? <section key={section}><h4>Professional Summary</h4><p>{resume.summary}</p></section> : null;
    }
    if (section === 'skills') {
      const skills = Object.values(resume.skills).flat();
      return skills.length ? <section key={section}><h4>Skills</h4><p>{skills.join(' · ')}</p></section> : null;
    }
    if (section === 'experience') {
      return resume.experience.length ? <section key={section}><h4>Experience</h4>{resume.experience.map((item) => <div key={item.id}><strong>{item.title || 'Job title'} — {item.company || 'Organization'}</strong><ul>{item.bullets.map((bullet, index) => <li key={`${item.id}-${index}`}>{bullet}</li>)}</ul></div>)}</section> : null;
    }
    if (section === 'projects') {
      return resume.projects.length ? <section key={section}><h4>Projects</h4>{resume.projects.map((project) => <div key={project.id}><strong>{project.title || 'Project title'}</strong>{project.technologies.length > 0 && <p>{project.technologies.join(', ')}</p>}<ul>{project.bullets.map((bullet, index) => <li key={`${project.id}-${index}`}>{bullet}</li>)}</ul></div>)}</section> : null;
    }
    if (section === 'education') {
      return resume.education.length ? <section key={section}><h4>Education</h4>{resume.education.map((item) => <p key={item.id}><strong>{item.degree || 'Qualification'}</strong> — {item.institution || 'Institution'} {item.graduation_date}</p>)}</section> : null;
    }
    if (section === 'certifications') {
      return resume.certifications.length ? <section key={section}><h4>Certifications</h4><ul>{resume.certifications.map((item) => <li key={item}>{item}</li>)}</ul></section> : null;
    }
    if (section === 'custom') {
      return <section key="custom">{Object.entries(resume.custom_sections || {}).map(([title, entries]) => <div key={title}><h4>{title}</h4><ul>{entries.map((entry) => <li key={entry}>{entry}</li>)}</ul></div>)}</section>;
    }
    return null;
  };

  const movePreviewSection = (section: string, direction: -1 | 1) => {
    const index = sectionOrder.indexOf(section);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= sectionOrder.length) return;
    setSectionOrder((current) => {
      const reordered = [...current];
      [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
      return reordered;
    });
  };

  const sectionLabels: Record<string, string> = {
    summary: 'Professional summary',
    experience: 'Work experience',
    skills: 'Skills',
    projects: 'Projects',
    education: 'Education',
    certifications: 'Certifications',
    custom: 'Custom sections',
  };
  const availableSections = Object.keys(sectionLabels).filter(
    (section) => !sectionOrder.includes(section) && (section !== 'custom' || Object.keys(resume.custom_sections || {}).length > 0)
  );

  if (cloudLoading) {
    return <div className="container resume-studio-page" role="status">Loading encrypted resume profiles…</div>;
  }

  const generateWithAI = async () => {
    if (aiOperation === 'optimize' && (!jobTitle.trim() || !jobDescription.trim())) {
      setError('Enter a target role and job description before optimizing the complete resume.');
      return;
    }
    if (aiOperation !== 'summary' && aiOperation !== 'skills' && aiOperation !== 'optimize' && !aiSourceText.trim()) {
      setError('Add the original experience, achievement, project, or bullet text before generating a rewrite.');
      return;
    }
    setIsGenerating(true);
    setAiResult(null);
    setError('');
    setNotice('');
    try {
      const result = await generateResumeAI({
        operation: aiOperation,
        resume,
        sourceText: aiSourceText,
        targetRole: jobTitle || role,
        jobDescription,
        industry,
        experienceLevel: CAREER_PATHS.find((item) => item.id === careerPath)?.name || careerPath,
        tone: aiTone,
      });
      setAiResult(result);
      setNotice('AI suggestion is ready. Review it carefully before applying.');
    } catch (aiError: unknown) {
      setError(aiError instanceof Error ? aiError.message : 'AI generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  const applyAiResult = () => {
    if (!aiResult) return;
    if (aiResult.proposed_resume) {
      setResume(aiResult.proposed_resume);
      setNotice('Reviewed AI optimization applied. Verify all statements before exporting.');
      setAiResult(null);
      return;
    }
    const suggestion = aiResult.suggestion?.trim();
    if (!suggestion) return;
    if (aiOperation === 'summary') {
      setResume((current) => ({ ...current, summary: suggestion }));
    } else if (aiOperation === 'experience' || aiOperation === 'achievement' || aiOperation === 'bullet') {
      const index = Math.min(aiExperienceIndex, Math.max(resume.experience.length - 1, 0));
      if (!resume.experience[index]) {
        setError('Add an experience entry before applying this suggestion.');
        return;
      }
      setResume((current) => ({
        ...current,
        experience: current.experience.map((item, itemIndex) =>
          itemIndex === index ? { ...item, bullets: [...item.bullets, suggestion] } : item
        ),
      }));
    } else if (aiOperation === 'project') {
      const index = Math.min(aiProjectIndex, Math.max(resume.projects.length - 1, 0));
      if (!resume.projects[index]) {
        setError('Add a project entry before applying this suggestion.');
        return;
      }
      setResume((current) => ({
        ...current,
        projects: current.projects.map((item, itemIndex) =>
          itemIndex === index ? { ...item, bullets: [...item.bullets, suggestion] } : item
        ),
      }));
    } else {
      setNotice('Skills remain recommendations only. Verify each skill and add it manually if accurate.');
      return;
    }
    setNotice('Suggestion added to the editor. Review and edit the updated content.');
    setAiResult(null);
    setError('');
  };

  return (
    <div className="container resume-studio-page">
      <header className="studio-hero">
        <span className="badge badge-primary"><Sparkles size={14} /> Resume Studio</span>
        <h1>Build, tailor, and manage your resume</h1>
        <p>Draft from scratch, choose an ATS-safe design, save multiple profiles, and create companion career documents.</p>
        <div className="studio-local-note">
          <strong>AI writing is optional:</strong> generated suggestions use your configured backend AI provider and are not applied until you review them.
          {` ${cloudStatus}`}
        </div>
      </header>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {notice && <div className="alert alert-success" role="status">{notice}</div>}

      <section className="studio-card" aria-labelledby="profile-title">
        <div className="studio-section-heading">
          <UserRound size={20} />
          <div><h2 id="profile-title">Resume profiles</h2><p>Keep separate drafts for different companies, roles, industries, or career paths.</p></div>
        </div>
        <div className="studio-form-grid">
          <label>Profile name
            <input value={profileName} maxLength={80} onChange={(event) => setProfileName(event.target.value)} />
          </label>
          <label>Saved profile
            <select value={activeProfileId} onChange={(event) => selectProfile(event.target.value)}>
              <option value="">Current unsaved draft</option>
              {profiles.map((profile) => <option value={profile.id} key={profile.id}>{profile.name}</option>)}
            </select>
          </label>
          <div className="studio-actions">
            <button type="button" className="btn btn-primary" onClick={saveProfile}><Save size={16} /> Save profile</button>
            <button type="button" className="btn btn-secondary" onClick={createNewProfile}><Plus size={16} /> New profile</button>
            {activeProfileId && profiles.some((profile) => profile.id === activeProfileId) && (
              <>
                <button type="button" className="btn btn-secondary" onClick={duplicateProfile} aria-label="Duplicate saved profile"><Copy size={16} /> Duplicate</button>
                <button type="button" className="btn btn-secondary" onClick={deleteProfile} aria-label="Delete saved profile"><Trash2 size={16} /></button>
              </>
            )}
          </div>
        </div>
        <p className="studio-privacy-warning">Local browser storage is not encrypted. Sign in through Career Platform to sync profiles using encrypted account storage; cloud sync requires backend encryption configuration.</p>
      </section>

      <section className="studio-card" aria-labelledby="career-title">
        <div className="studio-section-heading">
          <BriefcaseBusiness size={20} />
          <div><h2 id="career-title">Career path & industry</h2><p>Choose a structure that puts relevant evidence first—nothing is fabricated.</p></div>
        </div>
        <div className="studio-form-grid">
          <label>Career stage
            <select value={careerPath} onChange={(event) => setCareerStarter(event.target.value as CareerPath)}>
              {CAREER_PATHS.map((path) => <option value={path.id} key={path.id}>{path.name}</option>)}
            </select>
          </label>
          <label>Industry
            <select value={industry} onChange={(event) => setIndustry(event.target.value)}>
              {INDUSTRIES.map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label>International resume format
            <select value={internationalFormat} onChange={(event) => setInternationalFormat(event.target.value)}>
              {INTERNATIONAL_FORMATS.map((format) => <option value={format.id} key={format.id}>{format.name}</option>)}
            </select>
          </label>
        </div>
        <p className="studio-guidance">{CAREER_PATHS.find((path) => path.id === careerPath)?.guidance}</p>
        <p className="studio-guidance">{formatPreset?.details} Local format presets only adjust date display and presentation; confirm local hiring conventions.</p>
      </section>

      <section className="studio-card" aria-labelledby="template-title">
        <div className="studio-section-heading">
          <FileText size={20} />
          <div><h2 id="template-title">ATS-friendly templates <span className="studio-count">{RESUME_TEMPLATES.length}</span></h2><p>All templates export as readable, single-column documents with selectable text.</p></div>
        </div>
        <label className="studio-template-filter">Filter by industry
          <select value={industry} onChange={(event) => setIndustry(event.target.value)}>
            {INDUSTRIES.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
        <div className="studio-template-grid">
          {filteredTemplates.map((template) => (
            <button
              type="button"
              key={template.id}
              className={`studio-template-option ${template.id === templateId ? 'studio-template-selected' : ''}`}
              onClick={() => {
                setTemplateId(template.id);
                setFontFamily(template.font);
              }}
              aria-pressed={template.id === templateId}
            >
              <span className="template-sample" style={{ borderTopColor: template.accent, fontFamily: template.font }}>
                <i style={{ backgroundColor: template.accent }} />
                <i /><i /><i />
              </span>
              <strong>{template.name}</strong>
              <small>{template.industry} · {template.description}</small>
            </button>
          ))}
        </div>
        <p className="studio-guidance">Selected: <strong>{selectedTemplate.name}</strong>. The catalog contains {RESUME_TEMPLATES.length} family-and-accent combinations; all preserve standard headings and one-column ATS reading order.</p>
        <label className="studio-template-filter">Resume font
          <select value={fontFamily} onChange={(event) => setFontFamily(event.target.value)}>
            {['Arial', 'Calibri', 'Georgia', 'Times New Roman'].map((font) => <option value={font} key={font}>{font}</option>)}
          </select>
        </label>
      </section>

      <section className="studio-card" aria-labelledby="ai-writing-title">
        <div className="studio-section-heading">
          <WandSparkles size={20} />
          <div>
            <h2 id="ai-writing-title">AI resume writing & optimization</h2>
            <p>Generate grounded summaries, experience and project descriptions, achievements, skills guidance, bullet rewrites, or a full job-targeted draft.</p>
          </div>
        </div>
        <div className="studio-form-grid">
          <label>Target job role
            <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} placeholder="e.g. Senior Software Engineer" />
          </label>
          <label>AI writing task
            <select value={aiOperation} onChange={(event) => {
              setAiOperation(event.target.value as ResumeAIOperation);
              setAiResult(null);
            }}>
              <option value="summary">Professional summary</option>
              <option value="experience">Work experience</option>
              <option value="achievement">Achievement</option>
              <option value="skills">Skills and missing-skill suggestions</option>
              <option value="project">Project description</option>
              <option value="bullet">Optimize a bullet point</option>
              <option value="optimize">Optimize complete resume for job</option>
            </select>
          </label>
          <label>Resume tone
            <select value={aiTone} onChange={(event) => setAiTone(event.target.value as ResumeAITone)}>
              {RESUME_TONES.map((tone) => <option value={tone.id} key={tone.id}>{tone.label}</option>)}
            </select>
          </label>
          {['experience', 'achievement', 'bullet'].includes(aiOperation) && (
            <label>Experience entry
              <select value={aiExperienceIndex} onChange={(event) => setAiExperienceIndex(Number(event.target.value))}>
                {resume.experience.map((item, index) => <option value={index} key={item.id}>{item.title || `Experience ${index + 1}`}</option>)}
              </select>
            </label>
          )}
          {aiOperation === 'project' && (
            <label>Project entry
              <select value={aiProjectIndex} onChange={(event) => setAiProjectIndex(Number(event.target.value))}>
                {resume.projects.map((item, index) => <option value={index} key={item.id}>{item.title || `Project ${index + 1}`}</option>)}
              </select>
            </label>
          )}
        </div>
        {aiOperation !== 'summary' && aiOperation !== 'skills' && aiOperation !== 'optimize' && (
          <label className="studio-full-field">Original experience, achievement, project, or bullet evidence
            <textarea rows={4} maxLength={12000} value={aiSourceText} onChange={(event) => setAiSourceText(event.target.value)} placeholder="Provide the facts to rewrite. Include only verified responsibilities, technologies, outcomes, and metrics." />
          </label>
        )}
        <p className="studio-guidance">
          AI uses your resume, target role, industry, experience level, tone, and job description. Candidate content is sent to the backend-configured AI provider only when you request generation. Never include confidential employer information.
        </p>
        <button type="button" className="btn btn-primary" onClick={generateWithAI} disabled={isGenerating}>
          <Sparkles size={16} /> {isGenerating ? 'Generating suggestion…' : aiOperation === 'optimize' ? 'Optimize resume for this job' : 'Generate AI suggestion'}
        </button>
        {aiResult && (
          <div className="studio-ai-result" aria-live="polite">
            <h3>Review generated suggestion</h3>
            {aiResult.suggestion && <p className="studio-ai-suggestion">{aiResult.suggestion}</p>}
            {aiOperation === 'skills' && (
              <div>
                <strong>Skills supported by your resume</strong>
                {Object.entries(aiResult.skill_categories).map(([category, skills]) => (
                  <p key={category}><strong>{category}:</strong> {skills.join(', ')}</p>
                ))}
                {aiResult.suggested_missing_skills.length > 0 && (
                  <p><strong>Suggested to verify, not claimed:</strong> {aiResult.suggested_missing_skills.join(', ')}</p>
                )}
                {Object.keys(aiResult.skill_categories).length === 0 && aiResult.suggested_missing_skills.length === 0 && (
                  <p>No evidence-supported skills or additional suggestions were returned.</p>
                )}
              </div>
            )}
            {aiResult.proposed_resume && (
              <details>
                <summary>Review the complete proposed resume before applying</summary>
                <pre>{JSON.stringify(aiResult.proposed_resume, null, 2)}</pre>
              </details>
            )}
            <p className="studio-guidance">{aiResult.disclaimer}</p>
            <button type="button" className="btn btn-secondary btn-small" onClick={() => setAiResult(null)}>Discard suggestion</button>
            {aiOperation === 'skills' ? (
              <p className="studio-guidance">Skill recommendations are not inserted into your resume. Verify proficiency and add accurate skills manually.</p>
            ) : (
              <button type="button" className="btn btn-primary" onClick={applyAiResult}>
                <Check size={16} /> {aiResult.proposed_resume ? 'Apply reviewed resume' : 'Add suggestion to editor'}
              </button>
            )}
          </div>
        )}
      </section>

      <section className="studio-card" aria-labelledby="resume-content-title">
        <div className="studio-section-heading">
          <UserRound size={20} />
          <div><h2 id="resume-content-title">Build your resume from scratch</h2><p>Fields are editable. New entry controls never add invented achievements or credentials.</p></div>
        </div>
        <h3>Contact details</h3>
        <div className="studio-form-grid">
          <label>Full name<input value={resume.contact_info.full_name} onChange={(event) => updateContact('full_name', event.target.value)} /></label>
          <label>Email<input type="email" value={resume.contact_info.email || ''} onChange={(event) => updateContact('email', event.target.value)} /></label>
          <label>Phone<input value={resume.contact_info.phone || ''} onChange={(event) => updateContact('phone', event.target.value)} /></label>
          <label>Location<input value={resume.contact_info.location || ''} onChange={(event) => updateContact('location', event.target.value)} /></label>
          <label>LinkedIn URL<input value={resume.contact_info.linkedin || ''} onChange={(event) => updateContact('linkedin', event.target.value)} /></label>
          <label>Portfolio / GitHub URL<input value={resume.contact_info.github || ''} onChange={(event) => updateContact('github', event.target.value)} /></label>
        </div>

        <label className="studio-full-field">Professional summary
          <textarea rows={4} value={resume.summary} onChange={(event) => setResume((current) => ({ ...current, summary: event.target.value }))} placeholder="Summarize your verified background, strengths, and target." />
        </label>

        <label className="studio-full-field">Skills (one per line)
          <textarea rows={4} value={Object.values(resume.skills).flat().join('\n')} onChange={(event) => setResume((current) => ({ ...current, skills: { 'Core Skills': splitLines(event.target.value) } }))} placeholder={'Python\nProject management\nClinical research'} />
        </label>

        <div className="studio-list-heading">
          <h3>Experience</h3>
          <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => ({ ...current, experience: [...current.experience, { id: makeProfileId(), title: '', company: '', start_date: '', end_date: '', bullets: [] }] }))}><Plus size={15} /> Add experience</button>
        </div>
        {resume.experience.map((item, index) => (
          <fieldset className="studio-entry" key={item.id}>
            <legend>Experience {index + 1}</legend>
            <div className="studio-form-grid">
              <label>Job title<input value={item.title} onChange={(event) => updateExperience(index, { title: event.target.value })} /></label>
              <label>Organization<input value={item.company} onChange={(event) => updateExperience(index, { company: event.target.value })} /></label>
              <label>Start date<input value={item.start_date || ''} onChange={(event) => updateExperience(index, { start_date: event.target.value })} placeholder="YYYY-MM" /></label>
              <label>End date<input value={item.end_date || ''} onChange={(event) => updateExperience(index, { end_date: event.target.value })} placeholder="Present or YYYY-MM" /></label>
            </div>
            <label className="studio-full-field">Achievement bullets (one per line)
              <textarea rows={4} value={item.bullets.join('\n')} onChange={(event) => updateExperience(index, { bullets: splitLines(event.target.value) })} placeholder="Describe what you personally did and add verified outcomes." />
            </label>
            <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => ({ ...current, experience: current.experience.filter((_, itemIndex) => itemIndex !== index) }))}>Remove experience</button>
          </fieldset>
        ))}

        <div className="studio-list-heading">
          <h3>Education</h3>
          <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => ({ ...current, education: [...current.education, { id: makeProfileId(), degree: '', institution: '', graduation_date: '' }] }))}><Plus size={15} /> Add education</button>
        </div>
        {resume.education.map((item, index) => (
          <div className="studio-entry" key={item.id}>
            <div className="studio-form-grid">
              <label>Qualification<input value={item.degree} onChange={(event) => updateEducation(index, { degree: event.target.value })} /></label>
              <label>Institution<input value={item.institution} onChange={(event) => updateEducation(index, { institution: event.target.value })} /></label>
              <label>Graduation date<input value={item.graduation_date || ''} onChange={(event) => updateEducation(index, { graduation_date: event.target.value })} /></label>
              <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => ({ ...current, education: current.education.filter((_, itemIndex) => itemIndex !== index) }))}>Remove education</button>
            </div>
          </div>
        ))}

        <div className="studio-list-heading">
          <h3>Projects</h3>
          <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => ({ ...current, projects: [...current.projects, { id: makeProfileId(), title: '', technologies: [], bullets: [] }] }))}><Plus size={15} /> Add project</button>
        </div>
        {resume.projects.map((project, index) => (
          <fieldset className="studio-entry" key={project.id}>
            <legend>Project {index + 1}</legend>
            <label>Project title<input value={project.title} onChange={(event) => setResume((current) => ({ ...current, projects: current.projects.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.target.value } : item) }))} /></label>
            <label className="studio-full-field">Tools and technologies (comma-separated)
              <input value={project.technologies.join(', ')} onChange={(event) => setResume((current) => ({ ...current, projects: current.projects.map((item, itemIndex) => itemIndex === index ? { ...item, technologies: splitLines(event.target.value.replace(/,/g, '\n')) } : item) }))} />
            </label>
            <label className="studio-full-field">Project details (one per line)
              <textarea rows={3} value={project.bullets.join('\n')} onChange={(event) => setResume((current) => ({ ...current, projects: current.projects.map((item, itemIndex) => itemIndex === index ? { ...item, bullets: splitLines(event.target.value) } : item) }))} />
            </label>
            <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => ({ ...current, projects: current.projects.filter((_, itemIndex) => itemIndex !== index) }))}>Remove project</button>
          </fieldset>
        ))}

        <label className="studio-full-field">Certifications (one per line)
          <textarea rows={3} value={resume.certifications.join('\n')} onChange={(event) => setResume((current) => ({ ...current, certifications: splitLines(event.target.value) }))} />
        </label>

        <div className="studio-list-heading">
          <h3>Custom sections</h3>
          <div className="studio-custom-add">
            <input aria-label="Custom section title" value={customSectionTitle} onChange={(event) => setCustomSectionTitle(event.target.value)} placeholder="e.g. Publications" />
            <button type="button" className="btn btn-secondary btn-small" onClick={addCustomSection}><Plus size={15} /> Add section</button>
          </div>
        </div>
        {Object.entries(resume.custom_sections || {}).map(([title, entries]) => (
          <div className="studio-custom-section" key={title}>
            <div className="studio-list-heading">
              <h4>{title}</h4>
              <button type="button" className="btn btn-secondary btn-small" onClick={() => setResume((current) => {
                const custom = { ...current.custom_sections };
                delete custom[title];
                return { ...current, custom_sections: custom };
              })}>Remove section</button>
            </div>
            <textarea aria-label={`${title} entries`} rows={3} value={entries.join('\n')} onChange={(event) => setResume((current) => ({ ...current, custom_sections: { ...current.custom_sections, [title]: splitLines(event.target.value) } }))} placeholder="One entry per line" />
          </div>
        ))}

        <div className="studio-actions studio-export-actions">
          <button type="button" className="btn btn-primary" disabled={isExporting !== null} onClick={() => handleExport('pdf')}><ArrowDownToLine size={16} />{isExporting === 'pdf' ? 'Creating PDF…' : 'Export PDF'}</button>
          <button type="button" className="btn btn-secondary" disabled={isExporting !== null} onClick={() => handleExport('docx')}><ArrowDownToLine size={16} />{isExporting === 'docx' ? 'Creating Word file…' : 'Export DOCX'}</button>
        </div>
        <div className="studio-section-order" aria-label="Manage resume preview sections">
          <div className="studio-list-heading">
            <h3>Preview section order</h3>
            {availableSections.length > 0 && (
              <div className="studio-custom-add">
                <select aria-label="Add section to preview" value={sectionToAdd} onChange={(event) => setSectionToAdd(event.target.value)}>
                  <option value="">Add a section</option>
                  {availableSections.map((section) => <option value={section} key={section}>{sectionLabels[section]}</option>)}
                </select>
                <button
                  type="button"
                  className="btn btn-secondary btn-small"
                  disabled={!sectionToAdd}
                  onClick={() => {
                    if (sectionToAdd) setSectionOrder((current) => [...current, sectionToAdd]);
                    setSectionToAdd('');
                  }}
                ><Plus size={14} /> Add</button>
              </div>
            )}
          </div>
          {sectionOrder.map((section, index) => (
            <div className="studio-section-order-row" key={section}>
              <span>{sectionLabels[section] || section}</span>
              <button type="button" className="btn btn-secondary btn-small" disabled={index === 0} onClick={() => movePreviewSection(section, -1)} aria-label={`Move ${sectionLabels[section]} up`}><ArrowUp size={14} /></button>
              <button type="button" className="btn btn-secondary btn-small" disabled={index === sectionOrder.length - 1} onClick={() => movePreviewSection(section, 1)} aria-label={`Move ${sectionLabels[section]} down`}><ArrowDown size={14} /></button>
              <button
                type="button"
                className="btn btn-secondary btn-small"
                onClick={() => setHiddenSections((current) => [...current, section])}
              >Hide</button>
            </div>
          ))}
          {hiddenSections.length > 0 && (
            <div className="studio-guidance">
              Hidden: {hiddenSections.map((section) => (
                <button type="button" className="btn btn-secondary btn-small" key={section} onClick={() => setHiddenSections((current) => current.filter((item) => item !== section))}>
                  Show {sectionLabels[section] || section}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="studio-resume-preview" style={{ fontFamily, borderTopColor: selectedTemplate.accent }}>
          <h3 style={{ color: selectedTemplate.accent }}>{resume.contact_info.full_name || 'Your Name'}</h3>
          <p>{[resume.contact_info.email, resume.contact_info.phone, resume.contact_info.location].filter(Boolean).join(' · ') || 'Contact information'}</p>
          {sectionOrder.filter((section) => !hiddenSections.includes(section)).map(renderPreviewSection)}
        </div>
      </section>

      <section className="studio-card" aria-labelledby="tailor-title">
        <div className="studio-section-heading">
          <WandSparkles size={20} />
          <div><h2 id="tailor-title">One-click local resume tailoring</h2><p>Reorders existing skills and bullets using job-description overlap; it does not add new claims.</p></div>
        </div>
        <div className="studio-form-grid">
          <label>Target role<input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} placeholder="e.g. Data Analyst" /></label>
        </div>
        <label className="studio-full-field">Job description
          <textarea rows={6} value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste a target job description. This local sorting action does not send it to an AI service." />
        </label>
        <button type="button" className="btn btn-primary" onClick={handleTailor}><Sparkles size={16} /> Tailor existing content</button>
        {tailoringNotes.length > 0 && <ul className="studio-guidance">{tailoringNotes.map((item) => <li key={item}>{item}</li>)}</ul>}
      </section>

      <section className="studio-card" aria-labelledby="documents-title">
        <div className="studio-section-heading">
          <FileText size={20} />
          <div><h2 id="documents-title">Career document drafts</h2><p>Generate editable cover letter, LinkedIn, and portfolio drafts from this profile.</p></div>
        </div>
        <div className="studio-form-grid">
          <label>Target role<input value={role} onChange={(event) => setRole(event.target.value)} placeholder="e.g. Product Designer" /></label>
          <label>Company<input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Company name" /></label>
        </div>
        <button type="button" className="btn btn-primary" onClick={generateDocuments}><Sparkles size={16} /> Generate document drafts</button>
        <label className="studio-full-field">Cover letter
          <textarea rows={10} value={coverLetter} onChange={(event) => setCoverLetter(event.target.value)} placeholder="Generate a cover-letter starter, then review and edit it." />
          <button type="button" className="btn btn-secondary btn-small" onClick={() => downloadDocument('cover-letter.txt', coverLetter)}><Copy size={14} /> Download text</button>
        </label>
        <label className="studio-full-field">LinkedIn headline and About draft
          <textarea rows={9} value={linkedInProfile} onChange={(event) => setLinkedInProfile(event.target.value)} placeholder="Generate a headline and About starter." />
          <button type="button" className="btn btn-secondary btn-small" onClick={() => downloadDocument('linkedin-profile.txt', linkedInProfile)}><Copy size={14} /> Download text</button>
        </label>
        <label className="studio-full-field">Portfolio project descriptions
          <textarea rows={8} value={portfolioDescription} onChange={(event) => setPortfolioDescription(event.target.value)} placeholder="Add projects to your resume, then generate editable descriptions." />
          <button type="button" className="btn btn-secondary btn-small" onClick={() => downloadDocument('portfolio-descriptions.txt', portfolioDescription)}><Copy size={14} /> Download text</button>
        </label>
        <div className="studio-guidance">These are rule-based writing starters, not generated by an AI model. Replace every placeholder and verify all claims before publishing.</div>
      </section>

      <section className="studio-card" aria-labelledby="translation-title">
        <div className="studio-section-heading">
          <Languages size={20} />
          <div><h2 id="translation-title">Resume translation</h2><p>English, Spanish, French, German, Hindi, and Japanese requested.</p></div>
        </div>
        <div className="studio-translation-notice">
          <strong>Translation is unavailable in local-only mode.</strong>
          <p>Reliable translation needs a translation model or service. To honor your privacy choice, this app does not send resume content to an outside provider or pretend a glossary is a complete translation. You can export your resume and translate it with a service you trust.</p>
          <button type="button" className="btn btn-secondary" disabled aria-disabled="true" title="No local translation model is configured"><Languages size={16} /> Translate resume unavailable</button>
        </div>
      </section>
    </div>
  );
};
