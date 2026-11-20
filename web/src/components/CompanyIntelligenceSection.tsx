import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { Building2, CircleDollarSign, ExternalLink, Search, Sparkles } from 'lucide-react';
import { careerRequest, exportCareerResume } from '../services/careerApi';
import '../styles/company-intelligence.css';

type ApiRecord = Record<string, unknown>;

interface CompanySearchResult {
  entity_id: string;
  name: string;
  description?: string | null;
  source: string;
  source_url: string;
  retrieved_at: string;
}

interface TailoringChange {
  id: string;
  section: string;
  original_text: string;
  proposed_text: string;
  rationale: string;
  what_to_verify: string;
  is_accepted: boolean;
}

interface CompanyReview {
  id: string;
  company: string;
  role_title: string;
  changes: TailoringChange[];
  disclaimer: string;
  job_source: ApiRecord;
  specialization: string;
  match_score: number | null;
  missing_skills: string[];
}

const record = (value: unknown): ApiRecord =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as ApiRecord : {};

const records = (value: unknown): ApiRecord[] =>
  Array.isArray(value) ? value.map(record) : [];

const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

const tailoringChanges = (value: unknown): TailoringChange[] =>
  records(value)
    .filter((item) => typeof item.id === 'string' && typeof item.section === 'string')
    .map((item) => ({
      id: String(item.id),
      section: String(item.section),
      original_text: String(item.original_text || ''),
      proposed_text: String(item.proposed_text || ''),
      rationale: String(item.rationale || ''),
      what_to_verify: String(item.what_to_verify || ''),
      is_accepted: Boolean(item.is_accepted),
    }));

const text = (value: unknown, fallback = 'Not available'): string =>
  typeof value === 'string' && value.trim() ? value : fallback;

const formatDate = (value: unknown): string => {
  if (typeof value !== 'string' || !value) return 'Date unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const sourceLink = (url: unknown, label: string) =>
  typeof url === 'string' && /^https?:\/\//i.test(url)
    ? <a href={url} target="_blank" rel="noreferrer">{label} <ExternalLink size={13} /></a>
    : <span>{label}: source link unavailable</span>;

export const CompanyIntelligenceSection: React.FC<{ token: string }> = ({ token }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [company, setCompany] = useState<ApiRecord | null>(null);
  const [savedCompanies, setSavedCompanies] = useState<ApiRecord[]>([]);
  const [comparisonIds, setComparisonIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<ApiRecord | null>(null);
  const [assistantRole, setAssistantRole] = useState('');
  const [assistantResult, setAssistantResult] = useState<ApiRecord | null>(null);
  const [jobId, setJobId] = useState('');
  const [review, setReview] = useState<CompanyReview | null>(null);
  const [savedVersion, setSavedVersion] = useState<ApiRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const companyData = record(company);
  const profile = record(companyData.profile);
  const hiring = record(companyData.hiring);
  const openings = records(hiring.recent_openings);
  const skills = records(hiring.commonly_requested_skills);
  const salaries = records(hiring.salary_listings);
  const companyName = text(companyData.company, '');
  const savedEntityIds = useMemo(
    () => new Set(savedCompanies.map((item) => String(item.entity_id))),
    [savedCompanies],
  );

  const run = async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      return await action();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Company intelligence request failed.');
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    let active = true;
    void careerRequest<ApiRecord[]>(token, '/companies/saved')
      .then((saved) => {
        if (active) setSavedCompanies(saved);
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : 'Saved companies could not be loaded.');
      });
    return () => { active = false; };
  }, [token]);

  const search = async (event: FormEvent) => {
    event.preventDefault();
    setCompany(null);
    setResults([]);
    setComparison(null);
    setAssistantResult(null);
    setReview(null);
    setHasSearched(false);
    const params = new URLSearchParams({ q: query });
    const found = await run(() =>
      careerRequest<CompanySearchResult[]>(token, `/companies/search?${params.toString()}`),
    );
    if (found) {
      setResults(found);
      setHasSearched(true);
    }
  };

  const selectCompany = async (item: CompanySearchResult) => {
    setCompany(null);
    setReview(null);
    setAssistantResult(null);
    setQuery(item.name);
    const result = await run(() =>
      careerRequest<ApiRecord>(token, `/companies/profile/${encodeURIComponent(item.entity_id)}`),
    );
    if (result) {
      setCompany(result);
      setJobId('');
      setNotice(`Loaded source-attributed profile for ${item.name}.`);
    }
  };

  const saveCompany = async () => {
    if (!profile.entity_id || !companyName) return;
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/companies/saved', {
        method: 'POST',
        body: { entity_id: profile.entity_id, company_name: companyName },
      }),
    );
    if (result) {
      setSavedCompanies((current) => [
        result,
        ...current.filter((item) => item.entity_id !== result.entity_id),
      ]);
      setNotice(`${companyName} saved to your target companies.`);
    }
  };

  const removeCompany = async (entityId: string) => {
    const result = await run(async () => {
      await careerRequest<void>(token, `/companies/saved/${encodeURIComponent(entityId)}`, { method: 'DELETE' });
      return true;
    });
    if (result) {
      setSavedCompanies((current) => current.filter((item) => item.entity_id !== entityId));
      setComparisonIds((current) => current.filter((id) => id !== entityId));
    }
  };

  const compareCompanies = async () => {
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/companies/compare', {
        method: 'POST',
        body: { entity_ids: comparisonIds },
      }),
    );
    if (result) setComparison(result);
  };

  const askAssistant = async (event: FormEvent) => {
    event.preventDefault();
    if (!profile.entity_id || !companyName) return;
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/companies/research-assistant', {
        method: 'POST',
        body: {
          entity_id: profile.entity_id,
          company_name: companyName,
          role_title: assistantRole,
        },
      }),
    );
    if (result) setAssistantResult(result);
  };

  const optimizeResume = async () => {
    const selectedJob = openings.find((item) => item.job_id === jobId);
    if (!selectedJob || !companyName) return;
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/companies/role/optimize', {
        method: 'POST',
        body: {
          company_name: companyName,
          role_title: selectedJob.title,
          job_id: jobId,
        },
      }),
    );
    if (result) {
      const analysis = record(result.analysis);
      setReview({
        id: String(result.id),
        company: String(result.company),
        role_title: String(result.role_title),
        changes: tailoringChanges(analysis.changes),
        disclaimer: String(analysis.disclaimer || ''),
        job_source: record(result.job_source),
        specialization: String(result.specialization || ''),
        match_score: typeof record(analysis.match).score === 'number'
          ? Number(record(analysis.match).score)
          : null,
        missing_skills: Array.isArray(analysis.missing_skills)
          ? analysis.missing_skills.filter((skill): skill is string => typeof skill === 'string')
          : [],
      });
      setSavedVersion(null);
      setNotice('Evidence-based suggestions are ready. Review and approve each change before saving.');
    }
  };

  const updateChange = async (change: TailoringChange, accepted: boolean) => {
    if (!review) return;
    const result = await run(() =>
      careerRequest<ApiRecord>(token, `/tailoring/${encodeURIComponent(review.id)}`, {
        method: 'PATCH',
        body: {
          changes: [{ id: change.id, is_accepted: accepted }],
        },
      }),
    );
    if (result) {
      setReview({ ...review, changes: tailoringChanges(result.changes) });
    }
  };

  const saveApprovedVersion = async () => {
    if (!review) return;
    const saved = await run(() =>
      careerRequest<ApiRecord>(
        token,
        `/tailoring/${encodeURIComponent(review.id)}/save-version`,
        { method: 'POST' },
      ),
    );
    if (saved) {
      setSavedVersion(saved);
      setNotice('Approved changes were saved as a new resume version.');
    }
  };

  const downloadVersion = async (format: 'pdf' | 'docx') => {
    const structured = savedVersion?.structured_resume;
    if (!structured) return;
    const blob = await run(() => exportCareerResume(token, structured, format));
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${review?.company || 'company'}-${review?.role_title || 'resume'}.${format}`
      .toLowerCase().replace(/[^a-z0-9.-]+/g, '-');
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const toggleComparison = (entityId: string) => {
    setComparison(null);
    setComparisonIds((current) => current.includes(entityId)
      ? current.filter((id) => id !== entityId)
      : current.length < 4 ? [...current, entityId] : current);
  };

  return (
    <div className="company-intelligence-workspace">
      {error && <div className="company-intelligence-alert" role="alert">{error}</div>}
      {notice && <div className="company-intelligence-notice" role="status">{notice}</div>}
      {busy && <div className="company-intelligence-notice" role="status">Loading company intelligence…</div>}

      <div className="company-intelligence-columns">
        <section className="career-panel">
          <div className="career-panel-heading">
            <div><p className="career-eyebrow">COMPANY RESEARCH</p><h2>Verified company profile</h2></div>
            <Building2 size={22} />
          </div>
          <form className="career-inline-form" onSubmit={search}>
            <input required minLength={2} maxLength={160} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a company" aria-label="Company name" />
            <button type="submit" className="btn btn-primary" disabled={busy}><Search size={15} /> Search</button>
          </form>
          {results.length > 0 && (
            <div className="company-intelligence-results" aria-label="Company search results">
              {results.map((item) => (
                <button key={item.entity_id} type="button" onClick={() => void selectCompany(item)} disabled={busy}>
                  <strong>{item.name}</strong><span>{item.description || 'Wikidata company entity'}</span>
                  <small>{sourceLink(item.source_url, `Wikidata · ${formatDate(item.retrieved_at)}`)}</small>
                </button>
              ))}
            </div>
          )}
          {hasSearched && results.length === 0 && <p>No company entities with a company/organization description matched that search.</p>}
          {company && (
            <>
              <div className="company-intelligence-profile">
                <div className="career-panel-heading">
                  <div><p className="career-eyebrow">COMPANY PROFILE</p><h3>{companyName}</h3></div>
                  <button type="button" className="btn btn-secondary" disabled={busy || savedEntityIds.has(String(profile.entity_id))} onClick={() => void saveCompany()}>
                    {savedEntityIds.has(String(profile.entity_id)) ? 'Saved' : 'Save target'}
                  </button>
                </div>
                <p>{text(profile.description)}</p>
                <dl>
                  <div><dt>Industry</dt><dd>{records(profile.industry).map((item) => text(item.name)).join(', ') || 'Not reported'}</dd></div>
                  <div><dt>Headquarters</dt><dd>{records(profile.headquarters).map((item) => text(item.name)).join(', ') || 'Not reported'}</dd></div>
                  <div><dt>Employees</dt><dd>{typeof profile.employee_count === 'number' ? profile.employee_count.toLocaleString() : 'Not reported'}{profile.employee_count_as_of ? ` · as of ${String(profile.employee_count_as_of)}` : ''}</dd></div>
                  <div><dt>Founded</dt><dd>{records(profile.inception_dates).map((item) => String(item.date || '')).filter(Boolean).join(', ') || 'Not reported'}</dd></div>
                  <div><dt>Official website</dt><dd>{strings(profile.official_websites).length
                    ? strings(profile.official_websites).map((website, index) => sourceLink(website, `Website ${index + 1}`))
                    : 'Not reported'}</dd></div>
                </dl>
                <div className="company-intelligence-source">
                  {sourceLink(profile.source_url, 'Wikidata source')}
                  <span>Retrieved {formatDate(profile.retrieved_at)}</span>
                  {Boolean(profile.source_modified_at) && <span>Source updated {formatDate(profile.source_modified_at)}</span>}
                </div>
              </div>

              <div className="company-intelligence-subsection">
                <h3>Hiring and skills from authorized listings</h3>
                <p className="career-disclaimer">{String(hiring.sample_size || 0)} source listings with posted dates in the last 90 days. {text(hiring.limitation, '')}</p>
                <ul className="company-intelligence-periods">
                  {records(hiring.listing_counts_by_period).map((item) =>
                    <li key={String(item.period)}>{String(item.period).replace(/_/g, ' ')}: {String(item.count || 0)}</li>,
                  )}
                </ul>
                <h4>Requested skills in the sample</h4>
                {skills.length ? <div className="company-intelligence-chips">{skills.map((item) =>
                  <span key={String(item.skill)}>{String(item.skill)} <small>({String(item.listing_count)})</small></span>,
                )}</div> : <p>No dated job listings provide extractable skills.</p>}
                <h4>Disclosed salary ranges</h4>
                {salaries.length ? salaries.map((item, index) => (
                  <article className="company-intelligence-listing" key={`${String(item.role)}-${index}`}>
                    <strong><CircleDollarSign size={15} /> {String(item.role)} · {String(item.currency)} {String(item.minimum)}–{String(item.maximum)} {String(item.period)}</strong>
                    <span>{String(item.salary_source_type)} · {String(item.source)} · posted {formatDate(item.posted_at)} · retrieved {formatDate(item.retrieved_at)}</span>
                    {sourceLink(item.source_url, 'Original listing')}
                    {sourceLink(item.source_provider_url, 'Provider source')}
                  </article>
                )) : <p>No salary ranges were disclosed in the available company listings.</p>}
                <h4>Recent source-attributed openings</h4>
                {openings.length ? openings.map((item) => (
                  <article className="company-intelligence-listing" key={String(item.job_id)}>
                    <strong>{String(item.title)} · {text(item.location, 'Location not listed')}</strong>
                    <span>{String(item.source)} · posted {formatDate(item.posted_at)}</span>
                    {sourceLink(item.url, 'View listing')}
                  </article>
                )) : <p>No current, dated openings from configured authorized providers were found.</p>}
                <div className="company-intelligence-unavailable">
                  <h4>Unavailable without an authorized provider</h4>
                  <p>Culture and employee reviews, company-specific interview experiences/questions, and verified promotion paths are not available. Job-description topics below are not confirmed interview questions.</p>
                  <p><strong>Listing-based preparation topics:</strong> {skills.slice(0, 10).map((item) => String(item.skill)).join(', ') || 'Not available'}</p>
                </div>
              </div>
            </>
          )}
        </section>

        <div className="company-intelligence-side">
          <section className="career-panel">
            <p className="career-eyebrow">SAVED TARGET COMPANIES</p><h2>Compare employers</h2>
            {!savedCompanies.length ? <p>Save a company profile to build a comparison.</p> : savedCompanies.map((item) => {
              const id = String(item.entity_id);
              const savedName = String(item.company_name);
              return <div className="company-intelligence-saved-row" key={id}>
                <input type="checkbox" aria-label={`Select ${savedName} for comparison`} checked={comparisonIds.includes(id)} onChange={() => toggleComparison(id)} />
                <span>{String(item.company_name)}</span>
                <div className="company-intelligence-saved-actions">
                  <button type="button" onClick={() => void selectCompany({
                    entity_id: id,
                    name: savedName,
                    source: 'Wikidata',
                    source_url: `https://www.wikidata.org/wiki/${id}`,
                    retrieved_at: String(item.created_at),
                  })} disabled={busy}>Open</button>
                  <button type="button" onClick={() => void removeCompany(id)} aria-label={`Remove ${savedName}`} disabled={busy}>Remove</button>
                </div>
              </div>;
            })}
            <button type="button" className="btn btn-secondary" onClick={() => void compareCompanies()} disabled={busy || comparisonIds.length < 2}>
              Compare selected ({comparisonIds.length}/4)
            </button>
            {comparison && <div className="company-intelligence-comparison">
              {records(comparison.companies).map((item) => {
                const itemProfile = record(item.profile);
                const itemHiring = record(item.hiring);
                const itemSalary = records(itemHiring.salary_listings);
                const itemSkills = records(itemHiring.commonly_requested_skills);
                return <article key={String(item.entity_id)}>
                  <h3>{String(item.company)}</h3>
                  <p>{records(itemProfile.industry).map((entry) => String(entry.name)).join(', ') || 'Industry not reported'}</p>
                  <p>{records(itemProfile.headquarters).map((entry) => String(entry.name)).join(', ') || 'Headquarters not reported'}</p>
                  <p>Employees: {typeof itemProfile.employee_count === 'number' ? itemProfile.employee_count.toLocaleString() : 'Not reported'}</p>
                  <p>{String(itemHiring.sample_size || 0)} dated openings in sample</p>
                  <p>Common listing skills: {itemSkills.slice(0, 8).map((entry) => String(entry.skill)).join(', ') || 'Not reported'}</p>
                  <p>Disclosed salary listings: {itemSalary.length}</p>
                  {itemSalary.slice(0, 3).map((salary, index) => <div key={`${String(salary.role)}-${index}`}>
                    <p>{String(salary.role)} · {String(salary.currency)} {String(salary.minimum)}–{String(salary.maximum)} {String(salary.period)}</p>
                    {sourceLink(salary.source_url, `Salary source · ${formatDate(salary.posted_at)}`)}
                  </div>)}
                  {sourceLink(itemProfile.source_url, 'Source')}
                </article>;
              })}
              <p className="career-disclaimer">Culture, sentiment, reviews, and interview data are unavailable; listing counts are not a complete hiring census.</p>
            </div>}
          </section>

          {company && <>
            <section className="career-panel">
              <p className="career-eyebrow">PERSONALIZED APPLICATION STRATEGY</p><h2>Company research assistant</h2>
              <p className="career-disclaimer">Uses your resume evidence only after AI profile sharing is enabled in Career Coach settings.</p>
              <form className="company-intelligence-form" onSubmit={askAssistant}>
                <label>Target role (optional)<input maxLength={160} value={assistantRole} onChange={(event) => setAssistantRole(event.target.value)} placeholder="e.g. Software Engineer" /></label>
                <button type="submit" className="btn btn-primary" disabled={busy}><Sparkles size={15} /> Generate strategy</button>
              </form>
              {assistantResult && <div className="company-intelligence-ai">
                <p>{String(assistantResult.response)}</p>
                <p className="career-disclaimer">{String(assistantResult.disclaimer)}</p>
                <div className="company-intelligence-source">{records(assistantResult.sources).map((source, index) =>
                  <span key={`${String(source.url)}-${index}`}>{sourceLink(source.url, String(source.name || 'Source'))} · {formatDate(source.retrieved_at)}</span>,
                )}</div>
              </div>}
            </section>

            <section className="career-panel">
              <p className="career-eyebrow">EVIDENCE-BASED RESUME REVIEW</p><h2>Optimize for a company role</h2>
              <p className="career-disclaimer">Select an actual authorized job listing. Suggestions use your saved resume and do not invent experience, skills, or metrics.</p>
              <label className="company-intelligence-form">Company listing
                <select value={jobId} onChange={(event) => setJobId(event.target.value)}>
                  <option value="">Select a role</option>
                  {openings.map((item) => <option key={String(item.job_id)} value={String(item.job_id)}>{String(item.title)} · {text(item.location, 'Location not listed')}</option>)}
                </select>
              </label>
              <button type="button" className="btn btn-primary" disabled={busy || !jobId} onClick={() => void optimizeResume()}>
                <Sparkles size={15} /> Generate resume review
              </button>
              {review && <div className="company-intelligence-review">
                <h3>{review.role_title} · {review.company}</h3>
                <p>{review.disclaimer}</p>
                <p>{review.specialization}</p>
                <p>Resume-to-listing match: {review.match_score == null ? 'Not scored' : `${review.match_score} / 100`}</p>
                <p>Unmatched required skills: {review.missing_skills.join(', ') || 'None detected by the text-matching heuristic.'}</p>
                <p>{sourceLink(review.job_source.url, 'Job listing')} · {text(review.job_source.name)} · {formatDate(review.job_source.posted_at)}</p>
                {review.changes.map((change) => <article key={change.id} className="company-intelligence-change">
                  <label><input type="checkbox" checked={change.is_accepted} onChange={(event) => void updateChange(change, event.target.checked)} /> Approve this change</label>
                  <small>{change.section} · {change.rationale}</small>
                  <del>{change.original_text || 'No existing summary'}</del>
                  <strong>{change.proposed_text}</strong>
                  <small>Verify: {change.what_to_verify}</small>
                </article>)}
                {!savedVersion ? <button type="button" className="btn btn-primary" onClick={() => void saveApprovedVersion()} disabled={busy || !review.changes.some((change) => change.is_accepted)}>Save approved changes as a new version</button>
                  : <div className="company-intelligence-downloads">
                    <span>Saved version: {String(savedVersion.title)}</span>
                    <button type="button" className="btn btn-secondary" onClick={() => void downloadVersion('pdf')} disabled={busy}>Export PDF</button>
                    <button type="button" className="btn btn-secondary" onClick={() => void downloadVersion('docx')} disabled={busy}>Export DOCX</button>
                  </div>}
              </div>}
            </section>
          </>}
        </div>
      </div>
    </div>
  );
};
