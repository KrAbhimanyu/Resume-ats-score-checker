import React, { useState, useEffect } from 'react';
import { HomePage } from './pages/HomePage';
import { AnalysisPage } from './pages/AnalysisPage';
import { TargetedResumeBuilderPage } from './pages/TargetedResumeBuilderPage';
import { checkHealth } from './services/analysisApi';
import { FileCheck, Activity, Sparkles, Target, X } from 'lucide-react';

export const App: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'healthy' | 'offline'>('checking');
  const [activeTab, setActiveTab] = useState<'ats-checker' | 'targeted-builder'>('ats-checker');
  const [bannerDismissed, setBannerDismissed] = useState(false);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then(() => {
        if (isMounted) setBackendStatus('healthy');
      })
      .catch(() => {
        if (isMounted) setBackendStatus('offline');
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleStartAnalysis = () => {
    setActiveTab('ats-checker');
    setTimeout(() => {
      const el = document.getElementById('workspace');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
        const dropzone = el.querySelector('[role="button"]') as HTMLElement | null;
        if (dropzone) {
          dropzone.focus();
        }
      }
    }, 100);
  };

  return (
    <>
      {/* Announcement Banner */}
      {!bannerDismissed && (
        <div className="announcement-banner" role="banner">
          <span className="announcement-banner-text">
            🎉 <strong>New:</strong> Targeted Resume Builder now supports custom employer profiles!
          </span>
          <button
            type="button"
            className="announcement-banner-close"
            aria-label="Dismiss announcement"
            onClick={() => setBannerDismissed(true)}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Header */}
      <header className="app-header">
        <div className="container header-inner">
          <div
            className="logo-wrapper"
            role="button"
            tabIndex={0}
            onClick={() => setActiveTab('ats-checker')}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') setActiveTab('ats-checker');
            }}
            aria-label="Resume ATS Score Checker Home"
            style={{ cursor: 'pointer' }}
          >
            <div className="logo-icon logo-icon-hover" aria-hidden="true">
              <FileCheck size={20} />
            </div>
            <span>Resume ATS Score Checker</span>
          </div>

          {/* Navigation Mode Switcher */}
          <nav className="header-nav-tabs" aria-label="Main Navigation">
            <button
              type="button"
              className={`nav-tab-btn ${activeTab === 'ats-checker' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('ats-checker')}
            >
              <Target size={15} aria-hidden="true" />
              <span>ATS Score Checker</span>
            </button>
            <button
              type="button"
              className={`nav-tab-btn ${activeTab === 'targeted-builder' ? 'nav-tab-active' : ''}`}
              onClick={() => setActiveTab('targeted-builder')}
            >
              <Sparkles size={15} aria-hidden="true" />
              <span>Targeted Resume Builder</span>
            </button>
          </nav>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              className="header-badge"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                backgroundColor:
                  backendStatus === 'healthy'
                    ? 'var(--color-success-subtle)'
                    : backendStatus === 'offline'
                    ? 'var(--color-danger-subtle)'
                    : 'var(--color-bg-subtle)',
                color:
                  backendStatus === 'healthy'
                    ? 'var(--color-success)'
                    : backendStatus === 'offline'
                    ? 'var(--color-danger)'
                    : 'var(--color-text-muted)',
                borderColor:
                  backendStatus === 'healthy'
                    ? 'var(--color-success-border)'
                    : backendStatus === 'offline'
                    ? 'var(--color-danger-border)'
                    : 'var(--color-border)',
              }}
              title={
                backendStatus === 'healthy'
                  ? 'FastAPI Analysis Backend Connected'
                  : backendStatus === 'offline'
                  ? 'Backend Server is Offline'
                  : 'Checking Backend Service...'
              }
            >
              <Activity size={12} aria-hidden="true" />
              <span>
                {backendStatus === 'healthy'
                  ? 'API Online'
                  : backendStatus === 'offline'
                  ? 'API Offline'
                  : 'Checking API...'}
              </span>
            </div>

            {activeTab === 'ats-checker' ? (
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}
                onClick={() => setActiveTab('targeted-builder')}
              >
                <Sparkles size={14} aria-hidden="true" />
                <span>Build Targeted Resume</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}
                onClick={() => setActiveTab('ats-checker')}
              >
                <Target size={14} aria-hidden="true" />
                <span>Standard ATS Checker</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1 }}>
        {activeTab === 'ats-checker' ? (
          <>
            <HomePage
              onStartAnalysis={handleStartAnalysis}
              onOpenTargetedBuilder={() => setActiveTab('targeted-builder')}
            />
            <AnalysisPage />
          </>
        ) : (
          <TargetedResumeBuilderPage onSwitchToAtsChecker={() => setActiveTab('ats-checker')} />
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="container footer-content">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            <FileCheck size={18} color="var(--color-primary)" />
            <span>Resume ATS Score Checker</span>
          </div>

          <p style={{ maxWidth: '720px', lineHeight: 1.6, fontSize: '0.825rem' }}>
            Estimated Resume–Job Match Score calculated via deterministic heuristic algorithms.
            Targeted Resume Builder tailored for Big Tech and specific company roles with verifiable single-column export.
            Built with ₹0 budget using modern open-source technology.
          </p>

          <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.775rem', color: 'var(--color-text-muted)' }}>
            <span>Zero Persistent File Retention</span>
            <span>•</span>
            <span>No Paid AI APIs</span>
            <span>•</span>
            <span>Strict Client-Side Privacy</span>
          </div>
        </div>
      </footer>
    </>
  );
};

export default App;
