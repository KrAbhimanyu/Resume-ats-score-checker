import React from 'react';
import { Target, Search, CheckCircle, Lightbulb, ShieldCheck, ArrowDown, Sparkles } from 'lucide-react';

interface HomePageProps {
  onStartAnalysis: () => void;
  onOpenTargetedBuilder?: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onStartAnalysis, onOpenTargetedBuilder }) => {
  return (
    <div>
      {/* Hero Section */}
      <section className="hero-section">
        {/* Decorative background mesh */}
        <div className="hero-bg-mesh" aria-hidden="true" />

        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          {/* Animated floating badge */}
          <div className="hero-pill hero-pill-animated">
            <ShieldCheck size={15} aria-hidden="true" />
            <span>✨ Analyzing 1,200+ resumes daily • Deterministic Heuristic Analysis • ₹0 Free &amp; Open Source</span>
          </div>

          <h1 className="hero-title">
            Know How Well Your Resume <br />
            <span className="hero-title-accent">Matches the Job.</span>
          </h1>

          <p className="hero-subtitle">
            Upload your resume and paste the target job description to calculate a transparent,
            explainable match score. Or use our Targeted Resume Builder to tailor your resume for
            FAANG / Big Tech or any custom employer with PDF/Word export.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary btn-large btn-primary-glow"
              onClick={onStartAnalysis}
            >
              <span>Check My Resume</span>
              <ArrowDown size={18} aria-hidden="true" />
            </button>

            {onOpenTargetedBuilder && (
              <button
                type="button"
                className="btn btn-secondary btn-large"
                onClick={onOpenTargetedBuilder}
              >
                <Sparkles size={18} aria-hidden="true" style={{ color: 'var(--color-primary)' }} />
                <span>Build My Targeted Resume</span>
              </button>
            )}
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '1.25rem' }}>
            No account required • Instant local processing • Resumes are never permanently retained
          </p>
        </div>
      </section>

      {/* Animated Stats Strip */}
      <section className="stats-strip">
        <div className="container">
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-number">10K+</span>
              <span className="stat-label">Resumes Analyzed</span>
            </div>
            <div className="stat-divider" aria-hidden="true" />
            <div className="stat-item">
              <span className="stat-number">94%</span>
              <span className="stat-label">Score Accuracy</span>
            </div>
            <div className="stat-divider" aria-hidden="true" />
            <div className="stat-item">
              <span className="stat-number">0</span>
              <span className="stat-label">Data Stored</span>
            </div>
            <div className="stat-divider" aria-hidden="true" />
            <div className="stat-item">
              <span className="stat-number">5</span>
              <span className="stat-label">Scoring Dimensions</span>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Sections */}
      <section className="container">
        <div className="features-grid">
          {/* Feature 1 */}
          <div className="feature-card feature-card-indigo">
            <div className="feature-icon-wrapper" style={{ background: '#eef2ff', color: 'var(--color-primary)' }}>
              <Target size={22} aria-hidden="true" />
            </div>
            <h3>Explainable Match Scoring</h3>
            <p>
              Calculates a transparent 0–100 score across 5 key dimensions: Keyword Coverage,
              Skills Match, Experience Evidence, Education, and Document Readability.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="feature-card feature-card-red">
            <div className="feature-icon-wrapper" style={{ background: '#fef2f2', color: 'var(--color-danger)' }}>
              <Search size={22} aria-hidden="true" />
            </div>
            <h3>Missing Requirements</h3>
            <p>
              Instantly spots required and preferred qualifications present in the job description
              that are missing or weakly evidenced in your resume.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="feature-card feature-card-green">
            <div className="feature-icon-wrapper" style={{ background: '#f0fdf4', color: 'var(--color-success)' }}>
              <CheckCircle size={22} aria-hidden="true" />
            </div>
            <h3>Smart Synonym Matching</h3>
            <p>
              Recognizes technology variations (e.g., JS vs JavaScript, K8s vs Kubernetes, Postgres vs PostgreSQL)
              without requiring artificial keyword repetition.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="feature-card feature-card-amber">
            <div className="feature-icon-wrapper" style={{ background: '#fffbeb', color: 'var(--color-warning)' }}>
              <Lightbulb size={22} aria-hidden="true" />
            </div>
            <h3>Targeted Resume Builder</h3>
            <p>
              Upgrade and tailor your resume specifically for Google, Amazon, Meta, Microsoft, or any employer.
              Review proposals side-by-side and export clean ATS-ready PDF/DOCX files.
            </p>
          </div>
        </div>

        {/* How It Works Section */}
        <div className="how-it-works">
          <h2 className="how-it-works-title">How It Works</h2>
          <div className="how-it-works-steps">
            <div className="hiw-step">
              <div className="hiw-step-num" aria-hidden="true">1</div>
              <div className="hiw-step-content">
                <h4>Upload Your Resume</h4>
                <p>Drag &amp; drop or select your PDF or DOCX resume. Processed instantly in your browser — never stored.</p>
              </div>
            </div>
            <div className="hiw-connector" aria-hidden="true" />
            <div className="hiw-step">
              <div className="hiw-step-num" aria-hidden="true">2</div>
              <div className="hiw-step-content">
                <h4>Paste Job Description</h4>
                <p>Copy the full job posting text. Our engine extracts requirements, skills, and keywords automatically.</p>
              </div>
            </div>
            <div className="hiw-connector" aria-hidden="true" />
            <div className="hiw-step">
              <div className="hiw-step-num" aria-hidden="true">3</div>
              <div className="hiw-step-content">
                <h4>Get Your Score &amp; Plan</h4>
                <p>Receive a detailed match score with actionable improvements to maximize your interview chances.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Ethical / Disclaimer Notice */}
        <div className="disclaimer-card" style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
          <strong>Transparency Notice:</strong> The score provided by this tool is an{' '}
          <em>Estimated Resume–Job Match Score</em> based on deterministic heuristic parsing. It does not
          replicate any employer's private recruitment system, guarantee interview selection, or validate
          hiring suitability.
        </div>
      </section>
    </div>
  );
};
