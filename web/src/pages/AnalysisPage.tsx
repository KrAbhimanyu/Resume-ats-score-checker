import React, { useState } from 'react';
import { ResumeUploader } from '../components/ResumeUploader';
import { JobDescriptionInput } from '../components/JobDescriptionInput';
import { ScoreOverview } from '../components/ScoreOverview';
import { CategoryBreakdown } from '../components/CategoryBreakdown';
import { KeywordAnalysis } from '../components/KeywordAnalysis';
import { RecommendationsList } from '../components/RecommendationsList';
import { LoadingState } from '../components/LoadingState';
import { ErrorMessage } from '../components/ErrorMessage';
import { analyzeResume, AnalysisApiError } from '../services/analysisApi';
import { AnalysisResponse } from '../types/analysis';
import { ShieldCheck, AlertTriangle, Sparkles } from 'lucide-react';

export const AnalysisPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [formValidationErrors, setFormValidationErrors] = useState<{
    file?: string;
    job?: string;
  }>({});

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

    setIsLoading(true);

    try {
      const response = await analyzeResume(selectedFile, jobDescription);
      setResult(response);
      // Scroll to results
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err: unknown) {
      if (err instanceof AnalysisApiError) {
        setError({ message: err.message, code: err.code });
      } else {
        const msg = err instanceof Error ? err.message : 'An unexpected error occurred.';
        setError({ message: msg, code: 'CLIENT_ERROR' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setSelectedFile(null);
    setJobDescription('');
    setFormValidationErrors({});
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div id="workspace" className="container" style={{ paddingBottom: '4rem' }}>
      {/* If loading, render LoadingState */}
      {isLoading && <LoadingState />}

      {/* If results are ready, render Results Dashboard */}
      {!isLoading && result && (
        <div className="results-dashboard">
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
            scoreLabel={result.score_label}
            matchTier={result.match_tier}
            summary={result.summary}
            onReset={handleReset}
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

          {/* 5. Document Metadata & Limitations Disclaimer */}
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

          {error && (
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
                  <strong>Privacy guarantee:</strong> Resumes are processed in temporary memory and are never saved or retained.
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
