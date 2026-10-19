import React, { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';

const LOADING_STEPS = [
  'Validating document format and signature...',
  'Extracting readable text structure from resume...',
  'Parsing job description requirements and core skills...',
  'Evaluating keyword coverage and experience evidence...',
  'Calculating deterministic category scores and recommendations...',
];

export const LoadingState: React.FC = () => {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex((prev) => (prev + 1 < LOADING_STEPS.length ? prev + 1 : prev));
    }, 1200);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="loading-box" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.4rem' }}>
        Analyzing Your Resume
      </h3>
      <p style={{ color: 'var(--color-primary)', fontSize: '0.9rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <Sparkles size={16} aria-hidden="true" />
        <span>{LOADING_STEPS[stepIndex]}</span>
      </p>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>
        Processing locally without persistent document storage.
      </p>
    </div>
  );
};
