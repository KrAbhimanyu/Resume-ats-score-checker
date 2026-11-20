import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import { CircleDollarSign, Download, FileSearch, Plus, Sparkles, Trash2 } from 'lucide-react';
import { careerRequest } from '../services/careerApi';
import '../styles/salary-intelligence.css';

type ApiRecord = Record<string, unknown>;

interface SalaryOffer extends ApiRecord {
  id: string;
  name: string;
  company: string;
  role: string;
  location: string;
  currency: string;
  annual_base: number;
  annual_variable: number;
  annual_bonus: number;
  annual_equity: number;
  annual_total: number;
  benefits: string[];
  conditions: string;
  growth_notes: string;
}

const EMPTY_OFFER = {
  name: '',
  company: '',
  role: '',
  location: '',
  currency: 'INR',
  annual_base: 0,
  annual_variable: 0,
  annual_bonus: 0,
  annual_equity: 0,
  benefits: '',
  conditions: '',
  growth_notes: '',
};

const record = (value: unknown): ApiRecord =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as ApiRecord : {};

const records = (value: unknown): ApiRecord[] =>
  Array.isArray(value) ? value.map(record) : [];

const formatAmount = (value: unknown, currency: string): string => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${currency} ${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value)}`;
};

const externalUrl = (value: unknown): string =>
  typeof value === 'string' && /^https?:\/\//i.test(value) ? value : '';

export const SalaryIntelligenceSection: React.FC<{ token: string }> = ({ token }) => {
  const [offers, setOffers] = useState<SalaryOffer[]>([]);
  const [offer, setOffer] = useState(EMPTY_OFFER);
  const [selectedOffers, setSelectedOffers] = useState<string[]>([]);
  const [benchmarkRole, setBenchmarkRole] = useState('');
  const [benchmarkLocation, setBenchmarkLocation] = useState('');
  const [benchmarkCurrency, setBenchmarkCurrency] = useState('');
  const [benchmarkCompany, setBenchmarkCompany] = useState('');
  const [benchmarkExperience, setBenchmarkExperience] = useState('');
  const [benchmarkSkills, setBenchmarkSkills] = useState('');
  const [targetSalary, setTargetSalary] = useState('');
  const [targetCurrency, setTargetCurrency] = useState('INR');
  const [benchmarkData, setBenchmarkData] = useState<ApiRecord | null>(null);
  const [estimateData, setEstimateData] = useState<ApiRecord | null>(null);
  const [offerExplanation, setOfferExplanation] = useState('');
  const [editingOfferId, setEditingOfferId] = useState('');
  const [calculator, setCalculator] = useState({
    currency: 'INR',
    annual_fixed: 0,
    annual_variable: 0,
    annual_bonus: 0,
    annual_equity: 0,
    annual_tax_rate_percent: 0,
    monthly_deductions: 0,
  });
  const [calculation, setCalculation] = useState<ApiRecord | null>(null);
  const [growth, setGrowth] = useState({
    currency: 'INR',
    current_annual_compensation: 0,
    annual_growth_rate_percent: 5,
    years: 5,
  });
  const [growthData, setGrowthData] = useState<ApiRecord | null>(null);
  const [readiness, setReadiness] = useState({
    has_written_offer: false,
    has_reliable_benchmark: false,
    has_documented_impact: false,
    has_target_and_floor: false,
    has_reviewed_total_compensation: false,
  });
  const [readinessData, setReadinessData] = useState<ApiRecord | null>(null);
  const [negotiation, setNegotiation] = useState({
    request_type: 'strategy',
    role: '',
    company: '',
    location: '',
    currency: 'INR',
    current_offer: '',
    target_compensation: '',
    experience: '',
    achievements: '',
    priorities: '',
  });
  const [guidance, setGuidance] = useState('');
  const [offerAnalysis, setOfferAnalysis] = useState<ApiRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingOffers, setLoadingOffers] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadOffers = useCallback(async () => {
    const result = await careerRequest<SalaryOffer[]>(token, '/salary/offers');
    setOffers(result);
  }, [token]);

  useEffect(() => {
    loadOffers().catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Saved offers could not be loaded.');
    }).finally(() => setLoadingOffers(false));
  }, [loadOffers]);

  const run = async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      return await action();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The salary request failed.');
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  const searchBenchmarks = async (event: FormEvent) => {
    event.preventDefault();
    const params = new URLSearchParams({ role: benchmarkRole });
    if (benchmarkLocation.trim()) params.set('location', benchmarkLocation.trim());
    if (benchmarkCurrency.trim()) params.set('currency', benchmarkCurrency.trim().toUpperCase());
    if (benchmarkCompany.trim()) params.set('company', benchmarkCompany.trim());
    if (benchmarkExperience.trim()) params.set('experience_level', benchmarkExperience.trim());
    const result = await run(() =>
      careerRequest<ApiRecord>(token, `/salary/benchmarks?${params.toString()}`),
    );
    if (result) {
      setBenchmarkData(result);
      setEstimateData(null);
    }
  };

  const interpretBenchmarks = async () => {
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/estimate', {
        method: 'POST',
        body: {
          role: benchmarkRole,
          location: benchmarkLocation,
          currency: benchmarkCurrency || null,
          company: benchmarkCompany,
          experience_level: benchmarkExperience,
          skills: benchmarkSkills.split(',').map((skill) => skill.trim()).filter(Boolean),
        },
      }),
    );
    if (result) setEstimateData(result);
  };

  const explainOfferTerms = async () => {
    if (!analyzedText) return;
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/offers/explain', {
        method: 'POST',
        body: { extracted_text: analyzedText },
      }),
    );
    if (result) setOfferExplanation(String(result.explanation || ''));
  };

  const saveOffer = async (event: FormEvent) => {
    event.preventDefault();
    const payload = {
      ...offer,
      currency: offer.currency.toUpperCase(),
      benefits: offer.benefits.split(',').map((item) => item.trim()).filter(Boolean),
    };
    const result = await run(() => careerRequest<SalaryOffer>(
      token,
      editingOfferId ? `/salary/offers/${encodeURIComponent(editingOfferId)}` : '/salary/offers',
      { method: editingOfferId ? 'PUT' : 'POST', body: payload },
    ));
    if (result) {
      setOffers((current) => editingOfferId
        ? current.map((item) => item.id === result.id ? result : item)
        : [result, ...current]);
      setOffer(EMPTY_OFFER);
      setEditingOfferId('');
      setNotice(editingOfferId ? 'Offer changes saved.' : 'Offer saved securely for comparison.');
    }
  };

  const deleteOffer = async (id: string) => {
    const result = await run(async () => {
      await careerRequest<void>(token, `/salary/offers/${encodeURIComponent(id)}`, { method: 'DELETE' });
      return true;
    });
    if (result) {
      setOffers((current) => current.filter((item) => item.id !== id));
      setSelectedOffers((current) => current.filter((item) => item !== id));
      setNotice('Saved offer deleted.');
    }
  };

  const editOffer = (saved: SalaryOffer) => {
    setOffer({
      name: saved.name,
      company: saved.company,
      role: saved.role,
      location: saved.location,
      currency: saved.currency,
      annual_base: saved.annual_base,
      annual_variable: saved.annual_variable,
      annual_bonus: saved.annual_bonus,
      annual_equity: saved.annual_equity,
      benefits: saved.benefits.join(', '),
      conditions: saved.conditions,
      growth_notes: saved.growth_notes,
    });
    setEditingOfferId(saved.id);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const calculateTakeHome = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/calculate', {
        method: 'POST',
        body: { ...calculator, currency: calculator.currency.toUpperCase() },
      }),
    );
    if (result) setCalculation(result);
  };

  const calculateGrowth = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/growth-scenario', {
        method: 'POST',
        body: { ...growth, currency: growth.currency.toUpperCase() },
      }),
    );
    if (result) setGrowthData(result);
  };

  const calculateReadiness = async () => {
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/readiness', { method: 'POST', body: readiness }),
    );
    if (result) setReadinessData(result);
  };

  const analyzeOfferLetter = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const file = (event.currentTarget.elements.namedItem('offer-file') as HTMLInputElement).files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('offer_file', file);
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/offers/analyze', { method: 'POST', body: formData }),
    );
    if (result) setOfferAnalysis(result);
  };

  const generateGuidance = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() =>
      careerRequest<ApiRecord>(token, '/salary/negotiation-guidance', {
        method: 'POST',
        body: {
          ...negotiation,
          currency: negotiation.currency.toUpperCase(),
          current_offer: negotiation.current_offer ? Number(negotiation.current_offer) : null,
          target_compensation: negotiation.target_compensation ? Number(negotiation.target_compensation) : null,
        },
      }),
    );
    if (result) setGuidance(String(result.guidance || ''));
  };

  const exportComparison = () => {
    const chosen = offers.filter((item) => selectedOffers.includes(item.id));
    if (chosen.length < 2) {
      setError('Select at least two offers to export a comparison.');
      return;
    }
    const csvRows = [
      ['Offer', 'Company', 'Role', 'Location', 'Currency', 'Base', 'Variable', 'Bonus', 'Equity', 'Annual total', 'Benefits', 'Conditions', 'Career growth notes'],
      ...chosen.map((item) => [
        item.name, item.company, item.role, item.location, item.currency,
        item.annual_base, item.annual_variable, item.annual_bonus, item.annual_equity,
        item.annual_total, item.benefits.join('; '), item.conditions, item.growth_notes,
      ]),
    ];
    const csv = csvRows.map((row) =>
      row.map((cell) => {
        const value = String(cell ?? '');
        const safeValue = /^[\s]*[=+\-@]/.test(value) ? `'${value}` : value;
        return `"${safeValue.replace(/"/g, '""')}"`;
      }).join(','),
    ).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'salary-offer-comparison.csv';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  const samples = records(benchmarkData?.samples);
  const observations: ApiRecord[] = samples.flatMap((sample) =>
    records(sample.observations).map((observation): ApiRecord => ({ ...observation, sample })),
  );
  const scenario = records(growthData?.scenario);
  const terms = Array.isArray(offerAnalysis?.financial_terms_found)
    ? offerAnalysis.financial_terms_found.filter((item): item is string => typeof item === 'string')
    : [];
  const analyzedText = typeof offerAnalysis?.extracted_text === 'string' ? offerAnalysis.extracted_text : '';

  return (
    <div className="salary-intelligence">
      {error && <div className="salary-alert" role="alert">{error}</div>}
      {notice && <div className="salary-notice" role="status">{notice}</div>}

      <section className="career-panel">
        <div className="career-panel-heading">
          <div><p className="career-eyebrow">MARKET DATA</p><h2>Salary benchmarks from disclosed listings</h2></div>
          <CircleDollarSign size={22} />
        </div>
        <form className="salary-benchmark-form" onSubmit={searchBenchmarks}>
          <label>Role<input required minLength={2} value={benchmarkRole} onChange={(event) => setBenchmarkRole(event.target.value)} placeholder="e.g. software engineer" /></label>
          <label>Location<input value={benchmarkLocation} onChange={(event) => setBenchmarkLocation(event.target.value)} placeholder="City or country" /></label>
          <label>Currency<input maxLength={3} value={benchmarkCurrency} onChange={(event) => setBenchmarkCurrency(event.target.value.toUpperCase())} placeholder="INR / USD" /></label>
          <label>Company<input value={benchmarkCompany} onChange={(event) => setBenchmarkCompany(event.target.value)} placeholder="Optional" /></label>
          <label>Experience level<input value={benchmarkExperience} onChange={(event) => setBenchmarkExperience(event.target.value)} placeholder="Optional" /></label>
          <label>Skills (for AI context)<input value={benchmarkSkills} onChange={(event) => setBenchmarkSkills(event.target.value)} placeholder="Comma-separated, optional" /></label>
          <label>Your target annual compensation<input type="number" min="0" step="any" value={targetSalary} onChange={(event) => setTargetSalary(event.target.value)} placeholder="Optional" /></label>
          <label>Target currency<input maxLength={3} value={targetCurrency} onChange={(event) => setTargetCurrency(event.target.value.toUpperCase())} /></label>
          <button className="btn btn-primary" disabled={busy}>Search sourced ranges</button>
        </form>
        {benchmarkData && (
          <div className="salary-results">
            <p>{String(benchmarkData.sample_size ?? 0)} matching listing(s) · data as of {String(benchmarkData.data_as_of || 'unknown')}</p>
            {samples.length > 0 && <div className="salary-benchmark-groups">{samples.map((sample, index) => (
              <article key={`${String(sample.currency)}-${String(sample.reporting_period)}-${index}`}>
                <strong>{String(sample.currency)} · {String(sample.reporting_period)}</strong>
                <span>Range: {formatAmount(sample.minimum, String(sample.currency))} – {formatAmount(sample.maximum, String(sample.currency))}</span>
                <span>Median of listing midpoints: {formatAmount(sample.median_of_listing_midpoints, String(sample.currency))}</span>
                <small>{String(sample.sample_size)} listing(s) · {String(sample.sample_strength)} sample strength</small>
              </article>
            ))}</div>}
            {targetSalary && Number(targetSalary) > 0 && samples.map((sample, index) => {
              const target = Number(targetSalary);
              const withinObserved = target >= Number(sample.minimum) && target <= Number(sample.maximum);
              const matchesCurrency = String(sample.currency).toUpperCase() === targetCurrency.trim().toUpperCase();
              return <p className="salary-target-comparison" key={`target-${index}`}>
                {matchesCurrency
                  ? `Your target ${formatAmount(target, String(sample.currency))} is ${withinObserved ? 'within' : target < Number(sample.minimum) ? 'below' : 'above'} the observed listing range for ${String(sample.currency)} (${String(sample.reporting_period)}).`
                  : `Target comparison unavailable for ${String(sample.currency)} because currencies are not converted.`}
              </p>;
            })}
            {observations.length === 0 ? <p>{String(benchmarkData.message || 'No disclosed ranges match these filters.')}</p> : (
              <div className="salary-table-wrap"><table className="salary-table"><thead><tr><th>Role / company</th><th>Location</th><th>Range</th><th>Source / updated</th></tr></thead>
                <tbody>{observations.map((item, index) => <tr key={`${String(item.source_url)}-${index}`}>
                  <td>{String(item.role)}<small>{String(item.company)}</small></td>
                  <td>{String(item.location || 'Not listed')}<small>{String(item.experience_level || 'Experience not listed')}</small></td>
                  <td>{formatAmount(item.minimum, String(item.currency))} – {formatAmount(item.maximum, String(item.currency))}<small>{String(item.reporting_period)}</small></td>
                  <td>{externalUrl(item.source_url)
                    ? <a href={externalUrl(item.source_url)} target="_blank" rel="noreferrer">{String(item.source || 'Listing source')}</a>
                    : String(item.source || 'Listing source')}
                    <small>{String(item.source_updated_at || '')}{item.salary_is_predicted === true ? ' · provider-predicted' : item.salary_is_predicted === null ? ' · prediction status unknown' : ''}</small>
                  </td>
                </tr>)}</tbody>
              </table></div>
            )}
            {observations.length > 0 && <button type="button" className="btn btn-secondary" disabled={busy} onClick={interpretBenchmarks}><Sparkles size={15} /> AI interpretation of these sources</button>}
            {estimateData && <div className="salary-result-box"><strong>AI-assisted estimate interpretation</strong><p>{String(estimateData.guidance || estimateData.message || '')}</p><p>{String(estimateData.notice || '')}</p></div>}
            {Array.isArray(benchmarkData.limitations) && <ul className="salary-small-list">{benchmarkData.limitations.map((item, index) => <li key={index}>{String(item)}</li>)}</ul>}
          </div>
        )}
      </section>

      <section className="career-panel">
        <div className="career-panel-heading">
          <div><p className="career-eyebrow">OFFER WORKSPACE</p><h2>Save and compare your offers</h2></div>
          <Plus size={22} />
        </div>
        <form className="salary-offer-form" onSubmit={saveOffer}>
          <label>Offer name<input required minLength={2} value={offer.name} onChange={(event) => setOffer({ ...offer, name: event.target.value })} /></label>
          <label>Company<input value={offer.company} onChange={(event) => setOffer({ ...offer, company: event.target.value })} /></label>
          <label>Role<input value={offer.role} onChange={(event) => setOffer({ ...offer, role: event.target.value })} /></label>
          <label>Location<input value={offer.location} onChange={(event) => setOffer({ ...offer, location: event.target.value })} /></label>
          <label>Currency<input required maxLength={3} value={offer.currency} onChange={(event) => setOffer({ ...offer, currency: event.target.value.toUpperCase() })} /></label>
          {([
            ['annual_base', 'Annual fixed / base'],
            ['annual_variable', 'Annual variable'],
            ['annual_bonus', 'Annual bonus'],
            ['annual_equity', 'Annualized equity value'],
          ] as const).map(([field, label]) => <label key={field}>{label}<input type="number" min="0" step="any" value={offer[field]} onChange={(event) => setOffer({ ...offer, [field]: Number(event.target.value) })} /></label>)}
          <label className="salary-wide">Benefits (comma-separated)<input value={offer.benefits} onChange={(event) => setOffer({ ...offer, benefits: event.target.value })} placeholder="Health cover, retirement match" /></label>
          <label className="salary-wide">Conditions / vesting / contingencies<textarea rows={2} value={offer.conditions} onChange={(event) => setOffer({ ...offer, conditions: event.target.value })} /></label>
          <label className="salary-wide">Career growth notes<textarea rows={2} value={offer.growth_notes} onChange={(event) => setOffer({ ...offer, growth_notes: event.target.value })} /></label>
          <div className="salary-offer-form-actions">
            <button className="btn btn-primary" disabled={busy}>{editingOfferId ? 'Save offer changes' : 'Save offer securely'}</button>
            {editingOfferId && <button type="button" className="btn btn-secondary" onClick={() => { setEditingOfferId(''); setOffer(EMPTY_OFFER); }}>Cancel edit</button>}
          </div>
        </form>
        {loadingOffers ? <p className="salary-muted" role="status">Loading saved offers…</p> : offers.length === 0 ? <p className="salary-muted">No saved offers yet. Offer details are private to your account.</p> : (
          <>
            <div className="salary-offer-list">{offers.map((item) => (
              <article key={item.id}>
                <label className="salary-compare-check"><input type="checkbox" checked={selectedOffers.includes(item.id)} onChange={(event) => setSelectedOffers((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span>Compare</span></label>
                <div><strong>{item.name}</strong><span>{item.company || 'Company not specified'} · {item.role || 'Role not specified'}</span><small>{item.location || 'Location not specified'} · {item.currency}</small></div>
                <strong>{formatAmount(item.annual_total, item.currency)}<small>entered annual components</small></strong>
                <button type="button" className="salary-icon-button salary-edit-button" aria-label={`Edit ${item.name}`} onClick={() => editOffer(item)} disabled={busy}>Edit</button>
                <button type="button" className="salary-icon-button" aria-label={`Delete ${item.name}`} onClick={() => deleteOffer(item.id)} disabled={busy}><Trash2 size={16} /></button>
              </article>
            ))}</div>
            {selectedOffers.length >= 2 && <><p className="salary-muted">Compare currencies individually; values are not converted. Totals include only components you entered.</p><div className="salary-table-wrap"><table className="salary-table"><thead><tr><th>Compensation</th>{offers.filter((item) => selectedOffers.includes(item.id)).map((item) => <th key={item.id}>{item.name}</th>)}</tr></thead>
              <tbody>{([
                ['Company', (item: SalaryOffer) => item.company || '—'],
                ['Role / location', (item: SalaryOffer) => `${item.role || '—'} · ${item.location || '—'}`],
                ['Base', (item: SalaryOffer) => formatAmount(item.annual_base, item.currency)],
                ['Variable', (item: SalaryOffer) => formatAmount(item.annual_variable, item.currency)],
                ['Bonus', (item: SalaryOffer) => formatAmount(item.annual_bonus, item.currency)],
                ['Annualized equity', (item: SalaryOffer) => formatAmount(item.annual_equity, item.currency)],
                ['Entered annual total', (item: SalaryOffer) => formatAmount(item.annual_total, item.currency)],
                ['Benefits', (item: SalaryOffer) => item.benefits.join(', ') || 'Not provided'],
                ['Conditions', (item: SalaryOffer) => item.conditions || 'Not provided'],
                ['Career growth notes', (item: SalaryOffer) => item.growth_notes || 'Not provided'],
              ] as [string, (item: SalaryOffer) => string][]).map(([label, value]) => <tr key={label}><th>{label}</th>{offers.filter((item) => selectedOffers.includes(item.id)).map((item) => <td key={item.id}>{value(item)}</td>)}</tr>)}</tbody>
            </table></div></>}
            <button type="button" className="btn btn-secondary" onClick={exportComparison} disabled={selectedOffers.length < 2}><Download size={15} /> Download comparison CSV</button>
          </>
        )}
      </section>

      <div className="salary-tool-grid">
        <section className="career-panel">
          <p className="career-eyebrow">CONFIGURABLE CALCULATOR</p><h2>CTC breakdown and take-home estimate</h2>
          <form className="salary-calculator-form" onSubmit={calculateTakeHome}>
            <label>Currency<input maxLength={3} value={calculator.currency} onChange={(event) => setCalculator({ ...calculator, currency: event.target.value.toUpperCase() })} /></label>
            <label>Annual fixed<input type="number" min="0" step="any" value={calculator.annual_fixed} onChange={(event) => setCalculator({ ...calculator, annual_fixed: Number(event.target.value) })} /></label>
            <label>Annual variable<input type="number" min="0" step="any" value={calculator.annual_variable} onChange={(event) => setCalculator({ ...calculator, annual_variable: Number(event.target.value) })} /></label>
            <label>Annual bonus<input type="number" min="0" step="any" value={calculator.annual_bonus} onChange={(event) => setCalculator({ ...calculator, annual_bonus: Number(event.target.value) })} /></label>
            <label>Annualized equity<input type="number" min="0" step="any" value={calculator.annual_equity} onChange={(event) => setCalculator({ ...calculator, annual_equity: Number(event.target.value) })} /></label>
            <label>Assumed annual tax rate (%)<input type="number" min="0" max="75" step="any" value={calculator.annual_tax_rate_percent} onChange={(event) => setCalculator({ ...calculator, annual_tax_rate_percent: Number(event.target.value) })} /></label>
            <label>Other monthly deductions<input type="number" min="0" step="any" value={calculator.monthly_deductions} onChange={(event) => setCalculator({ ...calculator, monthly_deductions: Number(event.target.value) })} /></label>
            <button className="btn btn-primary" disabled={busy}>Calculate estimate</button>
          </form>
          {calculation && <div className="salary-result-box"><strong>Estimated monthly take-home: {formatAmount(calculation.estimated_monthly_take_home, String(calculation.currency))}</strong><span>Annual total (including equity): {formatAmount(calculation.annual_total_compensation, String(calculation.currency))} · annual cash compensation: {formatAmount(calculation.annual_cash_compensation, String(calculation.currency))} · gross monthly equivalent: {formatAmount(calculation.monthly_gross, String(calculation.currency))}</span><p>{String(record(calculation.assumptions).tax_notice)}</p><p>{String(record(calculation.assumptions).monthly_notice)}</p><p>{String(record(calculation.assumptions).equity_notice)}</p></div>}
        </section>

        <section className="career-panel">
          <p className="career-eyebrow">ILLUSTRATIVE ONLY</p><h2>Salary growth scenario</h2>
          <form className="salary-calculator-form" onSubmit={calculateGrowth}>
            <label>Currency<input maxLength={3} value={growth.currency} onChange={(event) => setGrowth({ ...growth, currency: event.target.value.toUpperCase() })} /></label>
            <label>Current annual compensation<input type="number" min="1" step="any" value={growth.current_annual_compensation} onChange={(event) => setGrowth({ ...growth, current_annual_compensation: Number(event.target.value) })} /></label>
            <label>Assumed annual growth (%)<input type="number" min="0" max="100" step="any" value={growth.annual_growth_rate_percent} onChange={(event) => setGrowth({ ...growth, annual_growth_rate_percent: Number(event.target.value) })} /></label>
            <label>Years<input type="number" min="1" max="10" value={growth.years} onChange={(event) => setGrowth({ ...growth, years: Number(event.target.value) })} /></label>
            <button className="btn btn-secondary" disabled={busy}>Calculate scenario</button>
          </form>
          {scenario.length > 0 && <ol className="salary-small-list">{scenario.map((item, index) => <li key={index}>Year {String(item.year)}: {formatAmount(item.illustrative_annual_compensation, String(growthData?.currency || growth.currency))}</li>)}</ol>}
          {growthData && <p className="salary-muted">{String(growthData.notice)}</p>}
        </section>
      </div>

      <div className="salary-tool-grid">
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">DOCUMENT REVIEW</p><h2>Analyze an offer letter</h2></div><FileSearch size={22} /></div>
          <form className="salary-upload-form" onSubmit={analyzeOfferLetter}>
            <label>Upload a text-based PDF or DOCX<input name="offer-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required /></label>
            <button className="btn btn-secondary" disabled={busy}>Extract compensation terms</button>
          </form>
          {offerAnalysis && <div className="salary-result-box">
            <p>{String(offerAnalysis.filename)} · {String(offerAnalysis.file_type)} · document is not stored</p>
            {terms.length > 0 ? <ul className="salary-small-list">{terms.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>No obvious compensation keywords were found; review the extracted text manually.</p>}
            <details><summary>Review extracted text</summary><pre>{analyzedText}</pre></details>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={explainOfferTerms}><Sparkles size={15} /> Explain extracted terms with AI</button>
          </div>}
          {offerExplanation && <div className="salary-result-box"><strong>AI explanation</strong><p>{offerExplanation}</p><p>AI profile-sharing consent is required; the uploaded file is not stored.</p></div>}
          <p className="salary-muted">Extraction highlights relevant lines, not legal or tax advice. Verify terms and amounts against the original offer.</p>
        </section>

        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">AI NEGOTIATION ASSISTANT</p><h2>Prepare a strategy or script</h2></div><Sparkles size={22} /></div>
          <form className="salary-negotiation-form" onSubmit={generateGuidance}>
            <label>Draft type<select value={negotiation.request_type} onChange={(event) => setNegotiation({ ...negotiation, request_type: event.target.value })}><option value="strategy">Negotiation strategy</option><option value="recruiter_script">Recruiter script</option><option value="manager_script">Hiring manager script</option></select></label>
            <label>Target role<input required minLength={2} value={negotiation.role} onChange={(event) => setNegotiation({ ...negotiation, role: event.target.value })} /></label>
            <label>Company<input value={negotiation.company} onChange={(event) => setNegotiation({ ...negotiation, company: event.target.value })} /></label>
            <label>Location<input value={negotiation.location} onChange={(event) => setNegotiation({ ...negotiation, location: event.target.value })} /></label>
            <label>Currency<input maxLength={3} value={negotiation.currency} onChange={(event) => setNegotiation({ ...negotiation, currency: event.target.value.toUpperCase() })} /></label>
            <label>Current offer<input type="number" min="0" value={negotiation.current_offer} onChange={(event) => setNegotiation({ ...negotiation, current_offer: event.target.value })} /></label>
            <label>Target compensation<input type="number" min="0" value={negotiation.target_compensation} onChange={(event) => setNegotiation({ ...negotiation, target_compensation: event.target.value })} /></label>
            <label className="salary-wide">Relevant experience<textarea rows={2} value={negotiation.experience} onChange={(event) => setNegotiation({ ...negotiation, experience: event.target.value })} /></label>
            <label className="salary-wide">Documented impact / achievements<textarea rows={2} value={negotiation.achievements} onChange={(event) => setNegotiation({ ...negotiation, achievements: event.target.value })} /></label>
            <label className="salary-wide">Priorities (base, flexibility, benefits, etc.)<textarea rows={2} value={negotiation.priorities} onChange={(event) => setNegotiation({ ...negotiation, priorities: event.target.value })} /></label>
            <button className="btn btn-primary" disabled={busy}>Generate editable draft</button>
          </form>
          {guidance && <label className="salary-guidance-label">Editable AI draft<textarea rows={9} value={guidance} onChange={(event) => setGuidance(event.target.value)} /></label>}
          <p className="salary-muted">Requires AI profile-sharing consent in Career Coach settings. AI uses the details supplied here and does not have a salary benchmark unless you provide one.</p>
        </section>
      </div>

      <section className="career-panel">
        <p className="career-eyebrow">PREPARATION CHECKLIST</p><h2>Negotiation readiness</h2>
        <div className="salary-readiness-options">
          {([
            ['has_written_offer', 'I have a written offer'],
            ['has_reliable_benchmark', 'I have a relevant sourced benchmark'],
            ['has_documented_impact', 'I have documented impact examples'],
            ['has_target_and_floor', 'I have a target and walk-away floor'],
            ['has_reviewed_total_compensation', 'I reviewed total compensation and conditions'],
          ] as const).map(([key, label]) => <label key={key}><input type="checkbox" checked={readiness[key]} onChange={(event) => setReadiness({ ...readiness, [key]: event.target.checked })} />{label}</label>)}
        </div>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={calculateReadiness}>Calculate checklist score</button>
        {readinessData && <div className="salary-result-box"><strong>{String(readinessData.score)}/100 readiness checklist</strong><p>{String(readinessData.label)}</p><ul className="salary-small-list">{(Array.isArray(readinessData.next_steps) ? readinessData.next_steps : []).map((item, index) => <li key={index}>{String(item)}</li>)}</ul></div>}
      </section>
    </div>
  );
};
