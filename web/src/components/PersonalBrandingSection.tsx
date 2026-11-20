import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import {
  BarChart3, BookOpen, Check, Download, ExternalLink, Github, Linkedin,
  Save, Sparkles, Trash2, UserRound, WandSparkles,
} from 'lucide-react';
import { careerRequest } from '../services/careerApi';
import { getApiBaseUrl } from '../services/analysisApi';
import '../styles/personal-branding.css';

type BrandTone = 'professional' | 'technical' | 'executive' | 'entry_level' | 'experienced' | 'concise';
type BrandContentType =
  | 'linkedin_headline' | 'linkedin_about' | 'linkedin_experience' | 'linkedin_skills'
  | 'profile_optimization' | 'branding_guidance' | 'professional_bio' | 'portfolio_project' | 'linkedin_post';

interface BrandProfile {
  personal_name: string;
  current_role: string;
  target_roles: string[];
  industry: string;
  skills: string[];
  about: string;
  experience: string[];
  projects: string[];
  linkedin_url: string | null;
  portfolio_url: string | null;
  github_username: string;
  tone: BrandTone;
}

interface BrandVersion {
  id: string;
  content_type: BrandContentType;
  title: string;
  tone: BrandTone;
  content: string;
  created_at: string;
  updated_at: string;
}

interface BrandAnalytics {
  id: string;
  platform: 'linkedin' | 'github' | 'portfolio';
  activity_date: string;
  title: string;
  impressions: number;
  reactions: number;
  comments: number;
  clicks: number;
  followers: number;
  source: 'user_reported';
}

interface BrandingDashboard {
  profile: BrandProfile;
  resume_skills: string[];
  profile_strength: {
    score: number;
    completed_signals: number;
    total_signals: number;
    signals: Array<{ section: string; complete: boolean }>;
    suggestions: string[];
    method: string;
  };
  ai_data_consent: boolean;
  versions: BrandVersion[];
  analytics: BrandAnalytics[];
  analytics_summary: Record<string, {
    activities: number;
    impressions: number;
    reactions: number;
    comments: number;
    clicks: number;
    followers: number;
  }>;
  analytics_notice: string;
}

interface GitHubProfile {
  source: string;
  source_url: string;
  retrieved_at: string;
  profile: Record<string, unknown>;
  public_repository_sample_size: number;
  languages_by_repository_count: Array<{ language: string; repositories: number }>;
  repositories: Array<{
    name: string;
    description?: string | null;
    language?: string | null;
    stars: number;
    forks: number;
    updated_at: string;
    url: string;
  }>;
  limitations: string;
}

const EMPTY_PROFILE: BrandProfile = {
  personal_name: '',
  current_role: '',
  target_roles: [],
  industry: '',
  skills: [],
  about: '',
  experience: [],
  projects: [],
  linkedin_url: null,
  portfolio_url: null,
  github_username: '',
  tone: 'professional',
};

const CONTENT_OPTIONS: Array<{ id: BrandContentType; label: string }> = [
  { id: 'linkedin_headline', label: 'LinkedIn headline' },
  { id: 'linkedin_about', label: 'LinkedIn About section' },
  { id: 'linkedin_experience', label: 'Experience descriptions' },
  { id: 'linkedin_skills', label: 'Skills recommendations' },
  { id: 'profile_optimization', label: 'Profile analysis and improvements' },
  { id: 'branding_guidance', label: 'Personal branding guidance' },
  { id: 'professional_bio', label: 'Professional bio' },
  { id: 'portfolio_project', label: 'Portfolio project description' },
  { id: 'linkedin_post', label: 'LinkedIn post draft' },
];

const TONES: Array<{ value: BrandTone; label: string }> = [
  { value: 'professional', label: 'Professional' },
  { value: 'technical', label: 'Technical' },
  { value: 'executive', label: 'Executive' },
  { value: 'entry_level', label: 'Entry-level' },
  { value: 'experienced', label: 'Experienced' },
  { value: 'concise', label: 'Concise' },
];

const text = (value: unknown): string => typeof value === 'string' ? value : '';
const listField = (value: string): string[] => value.split(/\r?\n/).map((part) => part.trim()).filter(Boolean);
const formatDate = (value: string): string => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const adjustAnalyticsSummary = (
  summary: BrandingDashboard['analytics_summary'],
  activity: BrandAnalytics,
  direction: 1 | -1,
): BrandingDashboard['analytics_summary'] => {
  const updated = { ...summary };
  const metrics = { ...(updated[activity.platform] || {
      activities: 0, impressions: 0, reactions: 0, comments: 0, clicks: 0, followers: 0,
    }) };
  metrics.activities += direction;
  metrics.impressions += activity.impressions * direction;
  metrics.reactions += activity.reactions * direction;
  metrics.comments += activity.comments * direction;
  metrics.clicks += activity.clicks * direction;
  if (direction > 0) metrics.followers = Math.max(metrics.followers, activity.followers);
  if (metrics.activities <= 0) delete updated[activity.platform];
  else updated[activity.platform] = metrics;
  return updated;
};

export const PersonalBrandingSection: React.FC<{ token: string }> = ({ token }) => {
  const [dashboard, setDashboard] = useState<BrandingDashboard | null>(null);
  const [profile, setProfile] = useState<BrandProfile>(EMPTY_PROFILE);
  const [targetRole, setTargetRole] = useState('');
  const [contentType, setContentType] = useState<BrandContentType>('linkedin_headline');
  const [tone, setTone] = useState<BrandTone>('professional');
  const [platform, setPlatform] = useState('LinkedIn');
  const [sourceText, setSourceText] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [customInstructions, setCustomInstructions] = useState('');
  const [versions, setVersions] = useState<BrandVersion[]>([]);
  const [editingVersion, setEditingVersion] = useState('');
  const [versionDrafts, setVersionDrafts] = useState<Record<string, { title: string; content: string }>>({});
  const [manualDraftOpen, setManualDraftOpen] = useState(false);
  const [manualTitle, setManualTitle] = useState('');
  const [manualContent, setManualContent] = useState('');
  const [manualContentType, setManualContentType] = useState<BrandContentType>('linkedin_about');
  const [github, setGithub] = useState<GitHubProfile | null>(null);
  const [portfolioApproved, setPortfolioApproved] = useState(false);
  const [portfolioTheme, setPortfolioTheme] = useState<'minimal' | 'classic' | 'midnight'>('minimal');
  const [portfolioAccent, setPortfolioAccent] = useState('#4F46E5');
  const [analyticsPlatform, setAnalyticsPlatform] = useState<'linkedin' | 'github' | 'portfolio'>('linkedin');
  const [analyticsDate, setAnalyticsDate] = useState(new Date().toISOString().slice(0, 10));
  const [analyticsTitle, setAnalyticsTitle] = useState('');
  const [analyticsNumbers, setAnalyticsNumbers] = useState({ impressions: '0', reactions: '0', comments: '0', clicks: '0', followers: '0' });
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await careerRequest<BrandingDashboard>(token, '/branding/dashboard');
      setDashboard(result);
      setProfile(result.profile);
      setTone(result.profile.tone || 'professional');
      setVersions(result.versions);
      setTargetRole(result.profile.target_roles[0] || '');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load personal-branding data.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadDashboard(); }, [loadDashboard]);

  const run = async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      return await action();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Personal branding request failed.');
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() => careerRequest<{ profile: BrandProfile; profile_strength: BrandingDashboard['profile_strength'] }>(
      token,
      '/branding/profile',
      { method: 'PUT', body: profile },
    ));
    if (result && dashboard) {
      setDashboard({ ...dashboard, profile: result.profile, profile_strength: result.profile_strength });
      setProfile(result.profile);
      setNotice('Professional brand profile saved securely.');
    }
  };

  const generateContent = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(async () => {
      const saved = await careerRequest<{ profile: BrandProfile; profile_strength: BrandingDashboard['profile_strength'] }>(
        token,
        '/branding/profile',
        { method: 'PUT', body: profile },
      );
      const generated = await careerRequest<BrandVersion>(token, '/branding/generate', {
        method: 'POST',
        body: {
          content_type: contentType,
          tone,
          target_role: targetRole,
          platform,
          job_description: jobDescription,
          source_text: sourceText,
          custom_instructions: customInstructions,
        },
      });
      return { saved, generated };
    });
    if (result && dashboard) {
      setProfile(result.saved.profile);
      setDashboard({
        ...dashboard,
        profile: result.saved.profile,
        profile_strength: result.saved.profile_strength,
        versions: [result.generated, ...dashboard.versions],
      });
      setVersions((current) => [result.generated, ...current]);
      setEditingVersion(result.generated.id);
      setVersionDrafts((current) => ({
        ...current,
        [result.generated.id]: { title: result.generated.title, content: result.generated.content },
      }));
      setNotice('Draft generated and saved to your private versions. Nothing was published.');
    }
  };

  const beginEdit = (version: BrandVersion) => {
    setEditingVersion(version.id);
    setVersionDrafts((current) => ({ ...current, [version.id]: { title: version.title, content: version.content } }));
  };

  const saveVersion = async (version: BrandVersion) => {
    const draft = versionDrafts[version.id];
    if (!draft) return;
    const result = await run(() => careerRequest<BrandVersion>(
      token,
      `/branding/versions/${encodeURIComponent(version.id)}`,
      { method: 'PATCH', body: draft },
    ));
    if (result) {
      setVersions((current) => current.map((item) => item.id === version.id ? result : item));
      setEditingVersion('');
      setNotice('Your editable content version was saved.');
    }
  };

  const createManualVersion = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() => careerRequest<BrandVersion>(token, '/branding/versions', {
      method: 'POST',
      body: {
        content_type: manualContentType,
        title: manualTitle,
        tone,
        content: manualContent,
      },
    }));
    if (result) {
      setVersions((current) => [result, ...current]);
      setManualTitle('');
      setManualContent('');
      setManualDraftOpen(false);
      setNotice('Your original content was saved as a private version.');
    }
  };

  const duplicateVersion = async (version: BrandVersion) => {
    const result = await run(() => careerRequest<BrandVersion>(
      token,
      `/branding/versions/${encodeURIComponent(version.id)}/duplicate`,
      { method: 'POST' },
    ));
    if (result) {
      setVersions((current) => [result, ...current]);
      setNotice('A separate copy was created.');
    }
  };

  const deleteVersion = async (version: BrandVersion) => {
    const result = await run(async () => {
      await careerRequest<void>(
        token,
        `/branding/versions/${encodeURIComponent(version.id)}`,
        { method: 'DELETE' },
      );
      return true;
    });
    if (result) {
      setVersions((current) => current.filter((item) => item.id !== version.id));
      setNotice('Saved version deleted.');
    }
  };

  const analyzeGitHub = async () => {
    const username = profile.github_username.trim();
    if (!username) {
      setError('Save or enter a GitHub username in your professional profile first.');
      return;
    }
    const result = await run(() => careerRequest<GitHubProfile>(
      token,
      `/branding/github/${encodeURIComponent(username)}`,
    ));
    if (result) setGithub(result);
  };

  const exportPortfolio = async () => {
    if (!portfolioApproved) {
      setError('Review and approve the saved information before downloading your portfolio page.');
      return;
    }
    const result = await run(async () => {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/career/branding/portfolio/export`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_approved_profile: portfolioApproved,
          theme: portfolioTheme,
          accent_color: portfolioAccent,
        }),
      });
      if (!response.ok) {
        let message = `Portfolio export failed (${response.status}).`;
        try {
          const payload = await response.json() as { detail?: string };
          if (payload.detail) message = payload.detail;
        } catch {
          // Error response may not be JSON.
        }
        throw new Error(message);
      }
      return response.blob();
    });
    if (result) {
      const url = URL.createObjectURL(result);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${profile.personal_name.trim().replace(/[^a-z0-9-]+/gi, '-').toLowerCase() || 'portfolio'}-portfolio.html`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setPortfolioApproved(false);
      setNotice('Standalone portfolio page downloaded. Review it before publishing to a hosting provider.');
    }
  };

  const saveAnalytics = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() => careerRequest<BrandAnalytics>(token, '/branding/analytics', {
      method: 'POST',
      body: {
        platform: analyticsPlatform,
        activity_date: analyticsDate,
        title: analyticsTitle,
        ...Object.fromEntries(Object.entries(analyticsNumbers).map(([key, value]) => [key, Number(value || 0)])),
      },
    }));
    if (result && dashboard) {
      const analytics = [result, ...dashboard.analytics];
      setDashboard({
        ...dashboard,
        analytics,
        analytics_summary: adjustAnalyticsSummary(dashboard.analytics_summary, result, 1),
      });
      setAnalyticsTitle('');
      setNotice('User-reported activity saved.');
    }
  };

  const deleteAnalytics = async (activity: BrandAnalytics) => {
    const result = await run(async () => {
      await careerRequest<void>(
        token,
        `/branding/analytics/${encodeURIComponent(activity.id)}`,
        { method: 'DELETE' },
      );
      return true;
    });
    if (result && dashboard) {
      const analytics = dashboard.analytics.filter((item) => item.id !== activity.id);
      setDashboard({
        ...dashboard,
        analytics,
        analytics_summary: adjustAnalyticsSummary(dashboard.analytics_summary, activity, -1),
      });
      if (activity.followers >= (dashboard.analytics_summary[activity.platform]?.followers ?? 0)) {
        await loadDashboard();
      }
      setNotice('Activity record deleted.');
    }
  };

  const updateList = (field: 'target_roles' | 'skills' | 'experience' | 'projects', value: string) => {
    setProfile((current) => ({ ...current, [field]: listField(value) }));
  };

  if (loading) return <div className="branding-loading" role="status">Loading your personal brand workspace…</div>;
  if (!dashboard) return <div className="branding-alert" role="alert">{error || 'Personal brand profile could not be loaded.'}</div>;

  const strength = dashboard.profile_strength;

  return (
    <div className="personal-branding">
      {error && <div className="branding-alert" role="alert">{error}</div>}
      {notice && <div className="branding-notice" role="status">{notice}</div>}
      {busy && <div className="branding-loading" role="status">Saving or generating…</div>}

      <section className="branding-hero">
        <div><p className="career-eyebrow">LINKEDIN & PERSONAL BRANDING</p><h2>Shape a professional presence you own</h2>
          <p>Analyze your supplied profile, draft editable content, and create a portfolio page from information you approve.</p>
        </div><div className="branding-hero-icons"><Linkedin size={28} /><Sparkles size={24} /></div>
      </section>

      <section className="career-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">PROFILE STRENGTH</p><h2>{strength.score}% completeness</h2></div><BarChart3 size={21} /></div>
        <div className="branding-score-track" role="img" aria-label={`${strength.score}% profile completeness`}><span style={{ width: `${strength.score}%` }} /></div>
        <p className="branding-muted">{strength.method}</p>
        <div className="branding-checklist">{strength.signals.map((signal) => <span key={signal.section} className={signal.complete ? 'is-complete' : ''}>
          {signal.complete ? <Check size={14} /> : <span aria-hidden="true">○</span>}{signal.section}
        </span>)}</div>
        {!!strength.suggestions.length && <p className="branding-suggestions"><strong>Suggested next steps:</strong> {strength.suggestions.join(' ')}</p>}
      </section>

      <div className="branding-columns">
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">UNIFIED PROFESSIONAL PROFILE</p><h2>Information you approve</h2></div><UserRound size={20} /></div>
          <p className="branding-muted">Resume skill matches: {dashboard.resume_skills.length ? dashboard.resume_skills.join(', ') : 'No saved resume skills yet.'} These are text matches, not independently verified skills.</p>
          <form className="branding-form" onSubmit={(event) => void saveProfile(event)}>
            <label>Professional name<input maxLength={120} value={profile.personal_name} onChange={(event) => setProfile({ ...profile, personal_name: event.target.value })} /></label>
            <label>Current role<input maxLength={160} value={profile.current_role} onChange={(event) => setProfile({ ...profile, current_role: event.target.value })} /></label>
            <label>Target roles <small>One per line</small><textarea rows={2} value={profile.target_roles.join('\n')} onChange={(event) => updateList('target_roles', event.target.value)} /></label>
            <label>Industry<input maxLength={120} value={profile.industry} onChange={(event) => setProfile({ ...profile, industry: event.target.value })} /></label>
            <label>Skills <small>One per line; only claim skills you can support</small><textarea rows={3} value={profile.skills.join('\n')} onChange={(event) => updateList('skills', event.target.value)} /></label>
            <label>About / summary<textarea maxLength={5000} rows={5} value={profile.about} onChange={(event) => setProfile({ ...profile, about: event.target.value })} /></label>
            <label>Experience evidence <small>One role or evidence item per line</small><textarea rows={4} value={profile.experience.join('\n')} onChange={(event) => updateList('experience', event.target.value)} /></label>
            <label>Project evidence <small>One project per line</small><textarea rows={3} value={profile.projects.join('\n')} onChange={(event) => updateList('projects', event.target.value)} /></label>
            <label>LinkedIn profile URL<input type="url" maxLength={2048} value={profile.linkedin_url || ''} onChange={(event) => setProfile({ ...profile, linkedin_url: event.target.value || null })} /></label>
            <label>Portfolio URL<input type="url" maxLength={2048} value={profile.portfolio_url || ''} onChange={(event) => setProfile({ ...profile, portfolio_url: event.target.value || null })} /></label>
            <label>GitHub username<input maxLength={39} value={profile.github_username} onChange={(event) => setProfile({ ...profile, github_username: event.target.value })} /></label>
            <label>Preferred tone<select value={profile.tone} onChange={(event) => { const next = event.target.value as BrandTone; setProfile({ ...profile, tone: next }); setTone(next); }}>{TONES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
            <button type="submit" className="btn btn-primary" disabled={busy}><Save size={15} /> Save profile</button>
          </form>
        </section>

        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">EDITABLE AI CONTENT</p><h2>Generate a draft</h2></div><WandSparkles size={20} /></div>
          <p className="career-disclaimer">
            {dashboard.ai_data_consent
              ? 'AI profile sharing is enabled in Career Coach. Relevant profile information and the text you provide are sent to the configured backend AI provider.'
              : 'AI profile sharing is off. Enable it in Career Coach settings before requesting generation. Your inputs are not sent until you submit a request.'}
            {' '}Generated content is saved as a draft and is never published automatically.
          </p>
          <form className="branding-form" onSubmit={(event) => void generateContent(event)}>
            <label>Content type<select value={contentType} onChange={(event) => setContentType(event.target.value as BrandContentType)}>{CONTENT_OPTIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
            <label>Tone<select value={tone} onChange={(event) => setTone(event.target.value as BrandTone)}>{TONES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label>Target role<input maxLength={160} value={targetRole} onChange={(event) => setTargetRole(event.target.value)} placeholder="e.g. Product designer" /></label>
            <label>Platform or audience<input maxLength={80} value={platform} onChange={(event) => setPlatform(event.target.value)} /></label>
            <label>Job description (optional)<textarea maxLength={12000} rows={4} value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} /></label>
            <label>Source facts / project or post material<textarea maxLength={12000} rows={5} value={sourceText} onChange={(event) => setSourceText(event.target.value)} placeholder="Add only information you approve for this draft." /></label>
            <label>Specific instructions (optional)<textarea maxLength={2000} rows={2} value={customInstructions} onChange={(event) => setCustomInstructions(event.target.value)} /></label>
            <button type="submit" className="btn btn-primary" disabled={busy || !dashboard.ai_data_consent}><Sparkles size={15} /> Generate and save draft</button>
          </form>

          <div className="branding-content-list">
            <div className="branding-version-list-heading"><h3>Saved content versions</h3>
              <button type="button" className="btn btn-secondary" onClick={() => setManualDraftOpen((open) => !open)}>Create a version</button>
            </div>
            {manualDraftOpen && <form className="branding-form branding-manual-draft" onSubmit={(event) => void createManualVersion(event)}>
              <label>Content type<select value={manualContentType} onChange={(event) => setManualContentType(event.target.value as BrandContentType)}>{CONTENT_OPTIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
              <label>Version name<input required minLength={1} maxLength={160} value={manualTitle} onChange={(event) => setManualTitle(event.target.value)} /></label>
              <label>Your content<textarea required minLength={1} maxLength={20000} rows={6} value={manualContent} onChange={(event) => setManualContent(event.target.value)} /></label>
              <div className="branding-actions"><button type="submit" className="btn btn-primary" disabled={busy}>Save original draft</button><button type="button" className="btn btn-secondary" onClick={() => setManualDraftOpen(false)}>Cancel</button></div>
            </form>}
            {!versions.length && <p className="branding-muted">Generated and edited drafts will appear here.</p>}
            {versions.map((version) => {
              const draft = versionDrafts[version.id] || { title: version.title, content: version.content };
              return <article className="branding-version" key={version.id}>
                {editingVersion === version.id ? (
                  <div className="branding-form">
                    <label>Version name<input maxLength={160} value={draft.title} onChange={(event) => setVersionDrafts((current) => ({ ...current, [version.id]: { ...draft, title: event.target.value } }))} /></label>
                    <label>Editable content<textarea rows={10} maxLength={20000} value={draft.content} onChange={(event) => setVersionDrafts((current) => ({ ...current, [version.id]: { ...draft, content: event.target.value } }))} /></label>
                    <div className="branding-actions">
                      <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void saveVersion(version)}><Save size={14} /> Save version</button>
                      <button type="button" className="btn btn-secondary" onClick={() => setEditingVersion('')}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="branding-version-heading"><div><strong>{version.title}</strong><small>{version.content_type.replace(/_/g, ' ')} · {version.tone} · updated {formatDate(version.updated_at)}</small></div></div>
                    <pre>{version.content}</pre>
                    <div className="branding-actions">
                      <button type="button" className="btn btn-secondary" onClick={() => beginEdit(version)}>Edit</button>
                      <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void duplicateVersion(version)}>Duplicate</button>
                      <button type="button" className="branding-delete" aria-label={`Delete ${version.title}`} disabled={busy} onClick={() => void deleteVersion(version)}><Trash2 size={15} /> Delete</button>
                    </div>
                  </>
                )}
              </article>;
            })}
          </div>
        </section>
      </div>

      <div className="branding-columns">
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">PUBLIC GITHUB PROFILE</p><h2>Repository overview</h2></div><Github size={20} /></div>
          <p className="branding-muted">Uses the public GitHub REST API only. No restricted scraping, private repositories, or code contents are accessed.</p>
          <button type="button" className="btn btn-secondary" disabled={busy || !profile.github_username.trim()} onClick={() => void analyzeGitHub()}>Analyze saved GitHub username</button>
          {github && <div className="branding-github-result">
            <div className="branding-panel-heading"><div><strong>{text(github.profile.name) || text(github.profile.login)}</strong><small>{text(github.profile.bio) || 'No public bio'}</small></div><a href={github.source_url} target="_blank" rel="noreferrer">View GitHub <ExternalLink size={13} /></a></div>
            <p>{String(github.profile.public_repos ?? '—')} public repos · {String(github.profile.followers ?? '—')} followers · {github.public_repository_sample_size} recently updated repos sampled</p>
            <p><strong>Languages by repository primary-language label:</strong> {github.languages_by_repository_count.map((item) => `${item.language} (${item.repositories})`).join(', ') || 'No language data in sampled repositories.'}</p>
            {github.repositories.map((repo) => <article className="branding-repo" key={repo.url}><a href={repo.url} target="_blank" rel="noreferrer"><strong>{repo.name}</strong> <ExternalLink size={12} /></a><p>{repo.description || 'No public description'}</p><small>{repo.language || 'Language not set'} · {repo.stars} stars · {repo.forks} forks · updated {formatDate(repo.updated_at)}</small></article>)}
            <small>{github.source} · Retrieved {formatDate(github.retrieved_at)} · {github.limitations}</small>
          </div>}
        </section>

        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">PORTFOLIO WEBSITE</p><h2>Download a personal portfolio page</h2></div><BookOpen size={20} /></div>
          <p className="branding-muted">Creates a self-contained HTML page from your saved, user-approved name, role, About, experience, skills, projects, and links. Review it before publishing; the service will not host or publish it.</p>
          <div className="branding-portfolio-options">
            <label>Visual theme<select value={portfolioTheme} onChange={(event) => setPortfolioTheme(event.target.value as typeof portfolioTheme)}><option value="minimal">Minimal</option><option value="classic">Classic</option><option value="midnight">Midnight</option></select></label>
            <label>Accent color<input type="color" value={portfolioAccent} onChange={(event) => setPortfolioAccent(event.target.value)} /></label>
          </div>
          <label className="branding-approval"><input type="checkbox" checked={portfolioApproved} onChange={(event) => setPortfolioApproved(event.target.checked)} /> I approve including my currently saved professional profile information in this downloadable file.</label>
          <button type="button" className="btn btn-primary" disabled={busy || !portfolioApproved} onClick={() => void exportPortfolio()}><Download size={15} /> Download portfolio HTML</button>
        </section>
      </div>

      <section className="career-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">PERSONAL BRAND GROWTH</p><h2>Record engagement you can access</h2></div><BarChart3 size={20} /></div>
        <p className="career-disclaimer">{dashboard.analytics_notice} Add metrics you can access from each platform's authorized dashboard. Records are labeled user-reported and are not independently validated.</p>
        <div className="branding-summary-grid">{Object.entries(dashboard.analytics_summary).map(([source, summary]) => <article key={source}>
          <strong>{source} summary</strong><span>{summary.activities} activities · {summary.impressions} impressions · {summary.reactions} reactions · {summary.comments} comments · {summary.clicks} clicks · {summary.followers} peak reported followers</span>
        </article>)}</div>
        <form className="branding-analytics-form" onSubmit={(event) => void saveAnalytics(event)}>
          <label>Platform<select value={analyticsPlatform} onChange={(event) => setAnalyticsPlatform(event.target.value as typeof analyticsPlatform)}><option value="linkedin">LinkedIn</option><option value="github">GitHub</option><option value="portfolio">Portfolio</option></select></label>
          <label>Date<input type="date" required value={analyticsDate} onChange={(event) => setAnalyticsDate(event.target.value)} /></label>
          <label>Activity / post name<input required maxLength={160} value={analyticsTitle} onChange={(event) => setAnalyticsTitle(event.target.value)} /></label>
          {(['impressions', 'reactions', 'comments', 'clicks', 'followers'] as const).map((metric) => <label key={metric}>{metric}<input type="number" min="0" max="1000000000" value={analyticsNumbers[metric]} onChange={(event) => setAnalyticsNumbers((current) => ({ ...current, [metric]: event.target.value }))} /></label>)}
          <button type="submit" className="btn btn-primary" disabled={busy}>Save reported metrics</button>
        </form>
        {!dashboard.analytics.length && <p className="branding-muted">No activity metrics recorded.</p>}
        <div className="branding-analytics-list">{dashboard.analytics.map((activity) => <article className="branding-analytics-row" key={activity.id}>
          <div><strong>{activity.title}</strong><span>{activity.platform} · {activity.activity_date} · source: {activity.source}</span><small>{activity.impressions} impressions · {activity.reactions} reactions · {activity.comments} comments · {activity.clicks} clicks · {activity.followers} followers</small></div>
          <button type="button" className="branding-delete" aria-label={`Delete ${activity.title}`} disabled={busy} onClick={() => void deleteAnalytics(activity)}><Trash2 size={15} /> Delete</button>
        </article>)}</div>
      </section>
    </div>
  );
};
