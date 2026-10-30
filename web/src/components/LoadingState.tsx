import React, { useEffect, useState } from 'react';
import { CheckCircle, Circle } from 'lucide-react';

const LOADING_STEPS = [
  'Validating document format and signature...',
  'Extracting readable text structure from resume...',
  'Parsing job description requirements and core skills...',
  'Evaluating keyword coverage and experience evidence...',
  'Calculating deterministic category scores and recommendations...',
];

export const LoadingState: React.FC = () => {
  const [stepIndex, setStepIndex] = useState(0);
  const [fakeProgress, setFakeProgress] = useState(0);

  // Advance steps every 1200ms
  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex((prev) => (prev + 1 < LOADING_STEPS.length ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(timer);
  }, []);

  // Fake progress bar that fills over ~6 seconds
  useEffect(() => {
    let frame: number;
    const startTime = performance.now();
    const duration = 6000;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const raw = elapsed / duration;
      // Ease out: approach 95% but never quite reach 100% until done
      const eased = 1 - Math.pow(1 - Math.min(raw, 0.98), 2.5);
      setFakeProgress(Math.min(95, Math.round(eased * 100)));
      if (elapsed < duration * 0.98) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="loading-box" role="status" aria-live="polite">
      {/* Multi-dot pulse animation */}
      <div className="loading-dots" aria-hidden="true">
        <span className="loading-dot" />
        <span className="loading-dot" />
        <span className="loading-dot" />
      </div>

      <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.4rem' }}>
        Analyzing Your Resume
      </h3>

      {/* Fake progress bar */}
      <div className="loading-progress-track" aria-hidden="true">
        <div
          className="loading-progress-fill"
          style={{ width: `${fakeProgress}%` }}
        />
      </div>
      <p className="loading-progress-label" aria-hidden="true">{fakeProgress}% complete</p>

      {/* Steps checklist */}
      <ul className="loading-steps-list" aria-label="Analysis steps">
        {LOADING_STEPS.map((step, idx) => {
          const isDone = idx < stepIndex;
          const isActive = idx === stepIndex;
          return (
            <li
              key={step}
              className={`loading-step-item ${isDone ? 'loading-step-done' : ''} ${isActive ? 'loading-step-active' : ''}`}
            >
              <span className="loading-step-icon" aria-hidden="true">
                {isDone ? (
                  <CheckCircle size={15} />
                ) : (
                  <Circle size={15} />
                )}
              </span>
              <span className="loading-step-text">{step}</span>
            </li>
          );
        })}
      </ul>

      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>
        Processing locally without persistent document storage.
      </p>
    </div>
  );
};
