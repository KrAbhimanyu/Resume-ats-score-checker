import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle, Circle, LoaderCircle, Square, XCircle } from 'lucide-react';
import {
  AnalysisProgressLayer,
  AnalysisProgressStatus,
} from '../types/analysis';

export const ANALYSIS_PROGRESS_TEMPLATE: AnalysisProgressLayer[] = [
  {
    layer_id: 'resume_parsing',
    label: 'Resume Parsing',
    status: 'pending',
    steps: [
      { step_id: 'validate_file', label: 'Validate file and request', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'extract_text', label: 'Extract PDF or DOCX text', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'page_word_count', label: 'Count pages and words', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'normalize_text', label: 'Normalize extracted text', status: 'pending', progress_percent: 0, details: {} },
    ],
  },
  {
    layer_id: 'section_detection',
    label: 'Section Detection',
    status: 'pending',
    steps: ['Summary', 'Experience', 'Education', 'Skills', 'Projects', 'Certifications'].map((section) => ({
      step_id: `${section.toLowerCase()}_section`,
      label: `Detect ${section}`,
      status: 'pending',
      progress_percent: 0,
      details: {},
    })),
  },
  {
    layer_id: 'keyword_matching',
    label: 'Skills and Keyword Matching',
    status: 'pending',
    steps: [
      { step_id: 'skills_extraction', label: 'Extract resume skills', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'job_keyword_extraction', label: 'Extract job description keywords', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'matched_keywords', label: 'Match keywords', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'missing_keywords', label: 'Identify missing keywords', status: 'pending', progress_percent: 0, details: {} },
    ],
  },
  {
    layer_id: 'experience_impact',
    label: 'Experience and Impact Analysis',
    status: 'pending',
    steps: [
      { step_id: 'experience_extraction', label: 'Extract experience entries', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'achievement_bullets', label: 'Detect achievement bullets', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'action_verb_analysis', label: 'Analyze action verbs', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'quantified_achievements', label: 'Find quantified achievements', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'evidence_quality', label: 'Evaluate evidence quality', status: 'pending', progress_percent: 0, details: {} },
    ],
  },
  {
    layer_id: 'ats_recommendations',
    label: 'ATS Scoring and Recommendations',
    status: 'pending',
    steps: [
      { step_id: 'ats_score', label: 'Calculate ATS score', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'section_scoring', label: 'Calculate section-wise scores', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'recommendation_generation', label: 'Generate recommendations', status: 'pending', progress_percent: 0, details: {} },
      { step_id: 'final_report', label: 'Generate final report', status: 'pending', progress_percent: 0, details: {} },
    ],
  },
];

interface AnalysisProgressViewProps {
  layers: AnalysisProgressLayer[];
  createdAt: string;
  connected: boolean;
  error?: string | null;
  errorCode?: string;
  canStop: boolean;
  onStop: () => void;
}

const STATUS_LABEL: Record<AnalysisProgressStatus, string> = {
  pending: 'Waiting',
  in_progress: 'Running',
  completed: 'Complete',
  failed: 'Failed',
  skipped: 'Skipped',
};

const formatFinding = (key: string, value: unknown): string | null => {
  const label = key.replace(/_/g, ' ');
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return `${label}: ${value}`;
  }
  if (Array.isArray(value) && value.every((item) => typeof item === 'string' || typeof item === 'number')) {
    return `${label}: ${value.length ? value.join(', ') : 'none'}`;
  }
  if (Array.isArray(value) && value.every((item) => item && typeof item === 'object' && 'category_id' in item)) {
    return `${label}: ${value.map((item) => {
      const score = item as { category_id: string; score: number; max_score: number };
      return `${score.category_id} ${score.score}/${score.max_score}`;
    }).join('; ')}`;
  }
  if (key === 'explanation' && typeof value === 'string') return value;
  return null;
};

const StatusIcon: React.FC<{ status: AnalysisProgressStatus }> = ({ status }) => {
  if (status === 'completed' || status === 'skipped') return <CheckCircle size={16} aria-hidden="true" />;
  if (status === 'failed') return <XCircle size={16} aria-hidden="true" />;
  if (status === 'in_progress') return <LoaderCircle size={16} aria-hidden="true" />;
  return <Circle size={16} aria-hidden="true" />;
};

export const AnalysisProgressView: React.FC<AnalysisProgressViewProps> = ({
  layers,
  createdAt,
  connected,
  error,
  errorCode,
  canStop,
  onStop,
}) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const currentOperation = useMemo(
    () => layers.flatMap((layer) => layer.steps).find((step) => step.status === 'in_progress'),
    [layers]
  );
  const overallProgress = layers.length
    ? Math.round(
      layers.flatMap((layer) => layer.steps)
        .reduce((total, step) => total + step.progress_percent, 0)
      / layers.flatMap((layer) => layer.steps).length
    )
    : 0;
  const elapsedSeconds = Math.max(0, Math.floor((now - Date.parse(createdAt)) / 1000));
  const elapsed = `${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, '0')}`;

  return (
    <section className="analysis-progress-card" aria-label="Live ATS analysis progress">
      <header className="analysis-progress-header">
        <div>
          <h2>Live 5-Layer ATS Scan</h2>
          <p>Analysis time {elapsed} · {connected ? 'Live backend updates' : 'Waiting for backend progress…'}</p>
        </div>
        <strong className="analysis-progress-total">{overallProgress}%</strong>
      </header>
      <div
        className="analysis-progress-track"
        role="progressbar"
        aria-label="Overall analysis progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={overallProgress}
      >
        <div className="analysis-progress-fill" style={{ width: `${overallProgress}%` }} />
      </div>
      <p className="analysis-current-operation" aria-live="polite">
        Currently running: <strong>{currentOperation?.label ?? (error ? 'Analysis stopped' : 'Preparing analysis')}</strong>
      </p>
      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
          {errorCode && <small className="analysis-progress-error-code">Error code: {errorCode}</small>}
        </div>
      )}
      {canStop && (
        <button type="button" className="analysis-stop-button" onClick={onStop}>
          <Square size={14} aria-hidden="true" />
          <span>Stop analysis and return to upload</span>
        </button>
      )}

      <div className="analysis-layers">
        {layers.map((layer, index) => {
          const layerPercent = layer.steps.length
            ? Math.round(layer.steps.reduce((total, step) => total + step.progress_percent, 0) / layer.steps.length)
            : 0;
          return (
            <section className="analysis-layer" key={layer.layer_id}>
              <div className={`analysis-layer-summary status-${layer.status}`}>
                <span className="analysis-status-icon"><StatusIcon status={layer.status} /></span>
                <span className="analysis-layer-title">Layer {index + 1}: {layer.label}</span>
                <span className="analysis-layer-progress">{layerPercent}% · {STATUS_LABEL[layer.status]}</span>
              </div>
              <ul className="analysis-progress-steps">
                {layer.steps.map((step) => {
                  const findings = Object.entries(step.details)
                    .map(([key, value]) => formatFinding(key, value))
                    .filter((finding): finding is string => Boolean(finding));
                  return (
                    <li className={`analysis-progress-step status-${step.status}`} key={step.step_id}>
                      <span className="analysis-status-icon"><StatusIcon status={step.status} /></span>
                      <span className="analysis-step-content">
                        <span className="analysis-step-title">{step.label}</span>
                        {findings.length > 0 && (
                          <span className="analysis-step-findings">{findings.join(' · ')}</span>
                        )}
                      </span>
                      <span className="analysis-step-percent">{step.progress_percent}%</span>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
      <p className="analysis-privacy-note">Progress findings contain counts and skill/keyword terms only, not resume text or contact details.</p>
    </section>
  );
};
