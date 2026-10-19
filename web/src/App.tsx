import React, { useState, useEffect } from 'react';
import { HomePage } from './pages/HomePage';
import { AnalysisPage } from './pages/AnalysisPage';
import { checkHealth } from './services/analysisApi';
import { FileCheck, Activity } from 'lucide-react';

export const App: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'healthy' | 'offline'>('checking');

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
    const el = document.getElementById('workspace');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
      // Focus the dropzone or file input if possible
      const dropzone = el.querySelector('[role="button"]') as HTMLElement | null;
      if (dropzone) {
        dropzone.focus();
      }
    }
  };

  return (
    <>
      {/* Header */}
      <header className="app-header">
        <div className="container header-inner">
          <a href="/" className="logo-wrapper" aria-label="Resume ATS Score Checker Home">
            <div className="logo-icon" aria-hidden="true">
              <FileCheck size={20} />
            </div>
            <span>Resume ATS Score Checker</span>
          </a>

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

            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}
              onClick={handleStartAnalysis}
            >
              Check Resume
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1 }}>
        <HomePage onStartAnalysis={handleStartAnalysis} />
        <AnalysisPage />
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
            Not affiliated with or endorsed by any specific commercial ATS vendor.
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
