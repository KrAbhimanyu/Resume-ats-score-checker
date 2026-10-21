import React from 'react';
import { Target, Search, CheckCircle, Lightbulb, ShieldCheck, ArrowDown } from 'lucide-react';

interface HomePageProps {
  onStartAnalysis: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onStartAnalysis }) => {
  return (
    <div>
      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-pill">
            <ShieldCheck size={15} aria-hidden="true" />
            <span>Deterministic Heuristic Analysis • ₹0 Free & Open Source</span>
          </div>

          <h1 className="hero-title">
            Know How Well Your Resume <br />
            <span className="hero-title-accent">Matches the Job.</span>
          </h1>

          <p className="hero-subtitle">
            Upload your resume and paste the target job description to calculate a transparent,
            explainable match score. Identify matched skills, missing requirements, and receive
            grounded recommendations to improve your application.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary btn-large"
              onClick={onStartAnalysis}
            >
              <span>Check My Resume</span>
              <ArrowDown size={18} aria-hidden="true" />
            </button>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '1.25rem' }}>
            No account required • Instant local processing • Resumes are never permanently retained
          </p>
        </div>
      </section>

      {/* Feature Sections */}
      <section className="container">
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon-wrapper" style={{ background: '#eef2ff', color: 'var(--color-primary)' }}>
              <Target size={22} aria-hidden="true" />
            </div>
            <h3>Explainable Match Scoring</h3>
            <p>
              Calculates a transparent 0–100 score across 5 key dimensions: Keyword Coverage,
              Skills Match, Experience Evidence, Education, and Document Readability.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper" style={{ background: '#fef2f2', color: 'var(--color-danger)' }}>
              <Search size={22} aria-hidden="true" />
            </div>
            <h3>Missing Requirements</h3>
            <p>
              Instantly spots required and preferred qualifications present in the job description
              that are missing or weakly evidenced in your resume.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper" style={{ background: '#f0fdf4', color: 'var(--color-success)' }}>
              <CheckCircle size={22} aria-hidden="true" />
            </div>
            <h3>Smart Synonym Matching</h3>
            <p>
              Recognizes technology variations (e.g., JS vs JavaScript, K8s vs Kubernetes, Postgres vs PostgreSQL)
              without requiring artificial keyword repetition.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper" style={{ background: '#fffbeb', color: 'var(--color-warning)' }}>
              <Lightbulb size={22} aria-hidden="true" />
            </div>
            <h3>Actionable Suggestions</h3>
            <p>
              Provides ethical, grounded guidance to quantify accomplishments, strengthen verbs,
              and highlight genuine qualifications without misleading claims.
            </p>
          </div>
        </div>

        {/* Ethical / Disclaimer Notice */}
        <div className="disclaimer-card" style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
          <strong>Transparency Notice:</strong> The score provided by this tool is an{' '}
          <em>Estimated Resume–Job Match Score</em> based on deterministic heuristic parsing. It does not
          replicate any employer’s private recruitment system, guarantee interview selection, or validate
          hiring suitability.
        </div>
      </section>
    </div>
  );
};

