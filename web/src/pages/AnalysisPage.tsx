import React, { useEffect, useRef, useState } from 'react';
import { ResumeUploader } from '../components/ResumeUploader';
import { JobDescriptionInput } from '../components/JobDescriptionInput';
import { ScoreOverview } from '../components/ScoreOverview';
import { CategoryBreakdown } from '../components/CategoryBreakdown';
import { KeywordAnalysis } from '../components/KeywordAnalysis';
import { RecommendationsList } from '../components/RecommendationsList';
import { ResumeImprovementDashboard } from '../components/ResumeImprovementDashboard';
import { ResumeQualityReport } from '../components/ResumeQualityReport';
import { AnalysisProgressView, ANALYSIS_PROGRESS_TEMPLATE } from '../components/AnalysisProgressView';
import { ErrorMessage } from '../components/ErrorMessage';
import {
  analyzeResume,
  AnalysisApiError,
  createAnalysisSession,
  failAnalysisSession,
  getAnalysisSession,
  streamAnalysisProgress,
} from '../services/analysisApi';
import { downloadAnalysisReport } from '../services/analysisReport';
import {
  AnalysisProgressEvent,
  AnalysisProgressLayer,
  AnalysisResponse,
  AnalysisSessionSnapshot,
} from '../types/analysis';
import { AlertTriangle, ShieldCheck, Sparkles } from 'lucide-react';

const ACTIVE_SESSION_STORAGE_KEY = 'resume-ats-active-analysis-session';

const applyProgressEvent = (
  snapshot: AnalysisSessionSnapshot,
  event: AnalysisProgressEvent
): AnalysisSessionSnapshot => {
  const layers: AnalysisProgressLayer[] = snapshot.layers.map((layer) => {
    if (layer.layer_id !== event.layer_id) return layer;
    const steps = layer.steps.map((step) => step.step_id === event.step_id
      ? {
        ...step,
        status: event.status,
        progress_percent: event.progress_percent,
        details: event.details,
      }
      : step);
    const statuses = steps.map((step) => step.status);
    const status = statuses.includes('failed')
      ? 'failed'
      : statuses.includes('in_progress')
        ? 'in_progress'
        : statuses.every((item) => item === 'completed' || item === 'skipped')
          ? 'completed'
          : 'pending';
    return { ...layer, status, steps };
  });
  return {
    ...snapshot,
    status: layers.some((layer) => layer.status === 'failed')
      ? 'failed'
      : layers.every((layer) => layer.status === 'completed')
        ? 'completed'
        : 'running',
    layers,
    events: [...snapshot.events, event],
  };
};

export const AnalysisPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [progress, setProgress] = useState<AnalysisSessionSnapshot | null>(null);
  const [progressConnected, setProgressConnected] = useState(false);
  const [reportDownloadError, setReportDownloadError] = useState<string | null>(null);
  const progressController = useRef<AbortController | null>(null);
  const [formValidationErrors, setFormValidationErrors] = useState<{
    file?: string;
    job?: string;
  }>({});

  useEffect(() => {
    const savedSessionId = window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    if (!savedSessionId) return undefined;

    const controller = new AbortController();
    progressController.current = controller;
    const resumeSession = async () => {
      try {
        const snapshot = await getAnalysisSession(savedSessionId, controller.signal);
        if (controller.signal.aborted) return;
        setProgress(snapshot);
        if (snapshot.result) setResult(snapshot.result);
        if (snapshot.status === 'failed') {
          setError({
            message: 'This analysis did not finish. You can review its progress and run it again.',
            code: snapshot.error_code ?? 'ANALYSIS_FAILED',
          });
          return;
        }
        if (snapshot.status === 'completed') return;

        setIsLoading(true);
        await streamAnalysisProgress(
          savedSessionId,
          (event) => setProgress((current) => current ? applyProgressEvent(current, event) : current),
          (current) => {
            setProgress(current);
            if (current.result) setResult(current.result);
            if (current.status === 'failed') {
              setError({
                message: 'The analysis failed before its report was ready. Run a new analysis to retry.',
                code: current.error_code ?? 'ANALYSIS_FAILED',
              });
            }
          },
          setProgressConnected,
          controller.signal,
          snapshot.events.reduce((latest, event) => Math.max(latest, event.event_id), 0)
        );
      } catch (err: unknown) {
        if (controller.signal.aborted) return;
        if (err instanceof AnalysisApiError && err.statusCode === 404) {
          window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
          setProgress(null);
        }
        const message = err instanceof Error ? err.message : 'Unable to reconnect to analysis progress.';
        setError({ message, code: 'PROGRESS_RECONNECT_FAILED' });
        setProgressConnected(false);
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    };

    void resumeSession();
    return () => {
      controller.abort();
      if (progressController.current === controller) progressController.current = null;
    };
  }, []);

  const validateForm = (): boolean => {
    const errors: { file?: string; job?: string } = {};

    if (!selectedFile) {
      errors.file = 'Please upload your resume (.pdf or .docx).';
    }

    if (!jobDescription || !jobDescription.trim()) {
      errors.job = 'Please paste the target job description.';
    } else if (jobDescription.trim().split(/\s+/).length < 5) {
      errors.job = 'Job description contains insufficient content (at least 5 words required).';
    }

    setFormValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleAnalyze = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    // Prevent duplicate submission while already running
    if (isLoading) return;

    setError(null);
    if (!validateForm() || !selectedFile) {
      return;
    }

    progressController.current?.abort();
    setProgress({
      session_id: '',
      status: 'pending',
      created_at: new Date().toISOString(),
      layers: ANALYSIS_PROGRESS_TEMPLATE,
      events: [],
      report_available: false,
    });
    setProgressConnected(false);
    setIsLoading(true);
    const controller = new AbortController();
    progressController.current = controller;
    let activeSessionId: string | null = null;

    try {
      const session = await createAnalysisSession(controller.signal);
      activeSessionId = session.session_id;
      window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, session.session_id);
      setProgress({
        session_id: session.session_id,
        status: 'pending',
        created_at: session.created_at,
        layers: session.layers,
        events: [],
        report_available: false,
      });

      void streamAnalysisProgress(
        session.session_id,
        (event) => setProgress((current) => current ? applyProgressEvent(current, event) : current),
        (snapshot) => {
          setProgress(snapshot);
          if (snapshot.result) setResult(snapshot.result);
          if (snapshot.status === 'failed') {
            setError({
              message: 'The analysis failed before its report was ready.',
              code: snapshot.error_code ?? 'ANALYSIS_FAILED',
            });
          }
        },
        setProgressConnected,
        controller.signal
      ).catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : 'Unable to receive live analysis progress.';
        setError({ message, code: 'PROGRESS_STREAM_FAILED' });
        setProgressConnected(false);
      });

      const response = await analyzeResume(
        selectedFile,
        jobDescription,
        controller.signal,
        session.session_id
      );
      setResult(response);
      // Scroll to results
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      let cleanupFailure: string | null = null;
      if (activeSessionId) {
        try {
          const snapshot = await failAnalysisSession(activeSessionId);
          setProgress(snapshot);
        } catch (cleanupError: unknown) {
          cleanupFailure = cleanupError instanceof Error
            ? cleanupError.message
            : 'The progress session could not be closed.';
        }
      }
      if (err instanceof AnalysisApiError) {
        setError({
          message: cleanupFailure ? `${err.message} Progress session cleanup failed: ${cleanupFailure}` : err.message,
          code: err.code,
        });
      } else {
        const msg = err instanceof Error ? err.message : 'An unexpected error occurred.';
        setError({
          message: cleanupFailure ? `${msg} Progress session cleanup failed: ${cleanupFailure}` : msg,
          code: 'CLIENT_ERROR',
        });
      }
    } finally {
      controller.abort();
      setIsLoading(false);
    }
  };

  const handleStopAnalysis = async () => {
    const sessionId = progress?.session_id;
    progressController.current?.abort();
    progressController.current = null;
    window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    setProgress(null);
    setProgressConnected(false);
    setIsLoading(false);
    setError(null);
    if (sessionId) {
      try {
        await failAnalysisSession(sessionId);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'The interrupted analysis session could not be closed.';
        setError({ message, code: 'PROGRESS_SESSION_ERROR' });
      }
    }
  };

  const handleReset = () => {
    progressController.current?.abort();
    progressController.current = null;
    window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    setResult(null);
    setError(null);
    setProgress(null);
    setProgressConnected(false);
    setReportDownloadError(null);
    setSelectedFile(null);
    setJobDescription('');
    setFormValidationErrors({});
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDownloadReport = () => {
    if (!result) {
      setReportDownloadError('No analysis report is available to download.');
      return;
    }
    try {
      downloadAnalysisReport(result);
      setReportDownloadError(null);
    } catch {
      setReportDownloadError('Unable to generate the report download. Please try again.');
    }
  };

  return (
    <div id="workspace" className="container" style={{ paddingBottom: '4rem' }}>
      {(isLoading || (progress && !result)) && (
        <AnalysisProgressView
          layers={progress?.layers ?? ANALYSIS_PROGRESS_TEMPLATE}
          createdAt={progress?.created_at ?? new Date().toISOString()}
          connected={progressConnected}
          error={error?.message}
          errorCode={error?.code}
          canStop={Boolean(progress?.session_id && progress.status !== 'completed' && progress.status !== 'failed')}
          onStop={handleStopAnalysis}
        />
      )}

      {/* If results are ready, render Results Dashboard */}
      {!isLoading && result && (
        <div className="results-dashboard">
          {reportDownloadError && (
            <div className="alert alert-warning" role="alert">
              {reportDownloadError}
            </div>
          )}

          {/* Document Extraction Warnings Banner */}
          {result.document_metadata.extraction_warnings &&
            result.document_metadata.extraction_warnings.length > 0 && (
              <div className="alert alert-warning" role="alert" style={{ marginBottom: '1.5rem' }}>
                <AlertTriangle size={20} style={{ flexShrink: 0 }} aria-hidden="true" />
                <div>
                  <strong>Document Parsing Notice:</strong>
                  <ul style={{ marginTop: '0.35rem', paddingLeft: '1.25rem' }}>
                    {result.document_metadata.extraction_warnings.map((warn, i) => (
                      <li key={i}>{warn}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

          {/* 1. Score Overview */}
          <ScoreOverview
            score={result.overall_score}
            categoryScores={result.category_scores}
            scoreLabel={result.score_label}
            matchTier={result.match_tier}
            summary={result.summary}
            onReset={handleReset}
            onDownload={handleDownloadReport}
          />

          {/* 2. Category Breakdown */}
          <CategoryBreakdown categories={result.category_scores} />

          {/* 3. Keyword and Requirements Analysis */}
          <KeywordAnalysis
            matchedRequirements={result.matched_requirements}
            missingRequirements={result.missing_requirements}
            keywordsFound={result.keywords_found}
          />

          {/* 4. Actionable Recommendations */}
          <RecommendationsList recommendations={result.recommendations} />

          {result.quality_report && <ResumeQualityReport report={result.quality_report} />}

          {/* 5. Resume Improvement Assistant */}
          {result.improvement_assistant && (
            <ResumeImprovementDashboard assistant={result.improvement_assistant} />
          )}

          {/* 6. Document Metadata & Limitations Disclaimer */}
          <div className="disclaimer-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--color-border)' }}>
              <span>Document: <strong>{result.document_metadata.filename}</strong> ({result.document_metadata.file_type})</span>
              <span>Words parsed: <strong>{result.document_metadata.word_count}</strong></span>
              <span>Size: <strong>{(result.document_metadata.file_size_bytes / 1024).toFixed(1)} KB</strong></span>
            </div>
            <p>
              <strong>Methodology Disclaimer:</strong> {result.limitations_disclaimer}
            </p>
          </div>
        </div>
      )}

      {/* If not loading and no result, render Analysis Workspace Form */}
      {!isLoading && !result && (
        <div className="workspace-card">
          <div className="workspace-header">
            <h2 className="workspace-title">Resume Analysis Workspace</h2>
            <p className="workspace-subtitle">
              Upload your resume and paste the job description to run deterministic heuristic analysis.
            </p>
          </div>

          {error && !progress && (
            <ErrorMessage
              message={error.message}
              code={error.code}
              onRetry={handleAnalyze}
            />
          )}

          <form onSubmit={handleAnalyze} noValidate>
            <div className="form-grid">
              {/* Left Column: File Upload */}
              <ResumeUploader
                selectedFile={selectedFile}
                onFileSelect={(file) => {
                  setSelectedFile(file);
                  if (file) {
                    setFormValidationErrors((prev) => ({ ...prev, file: undefined }));
                  }
                }}
                error={formValidationErrors.file}
                disabled={isLoading}
              />

              {/* Right Column: Job Description Textarea */}
              <JobDescriptionInput
                value={jobDescription}
                onChange={(val) => {
                  setJobDescription(val);
                  if (val.trim()) {
                    setFormValidationErrors((prev) => ({ ...prev, job: undefined }));
                  }
                }}
                error={formValidationErrors.job}
                disabled={isLoading}
              />
            </div>

            <div className="workspace-actions">
              <div className="privacy-notice">
                <ShieldCheck size={16} aria-hidden="true" style={{ color: 'var(--color-success)' }} />
                <span>
                  <strong>Privacy:</strong> Uploaded resumes are processed ephemerally by this backend and are not retained there.
                  Browser-local resume history is available only when you explicitly save a version in the builder.
                </span>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-large"
                disabled={isLoading}
                aria-label="Analyze Resume"
              >
                <Sparkles size={18} aria-hidden="true" />
                <span>Analyze Resume</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
