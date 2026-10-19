import React from 'react';
import { RefreshCw, Award } from 'lucide-react';

interface ScoreOverviewProps {
  score: number;
  scoreLabel: string;
  matchTier: string;
  summary: string;
  onReset: () => void;
}

export const ScoreOverview: React.FC<ScoreOverviewProps> = ({
  score,
  scoreLabel,
  matchTier,
  summary,
  onReset,
}) => {
  // Score gauge math
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  // Determine tier colors
  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'exceptional match':
        return { stroke: '#16a34a', bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' };
      case 'strong match':
        return { stroke: '#4f46e5', bg: '#eef2ff', text: '#4338ca', border: '#c7d2fe' };
      case 'good match':
        return { stroke: '#0284c7', bg: '#f0f9ff', text: '#0369a1', border: '#bae6fd' };
      case 'fair match':
        return { stroke: '#d97706', bg: '#fffbeb', text: '#b45309', border: '#fde68a' };
      default:
        return { stroke: '#dc2626', bg: '#fef2f2', text: '#b91c1c', border: '#fecaca' };
    }
  };

  const colors = getTierColor(matchTier);

  return (
    <div className="results-header-card">
      <div className="score-visual-col">
        <div className="score-circle-container" role="img" aria-label={`Match score: ${score} out of 100`}>
          <svg className="score-circle-svg" viewBox="0 0 130 130">
            <circle
              className="score-circle-bg"
              cx="65"
              cy="65"
              r={radius}
            />
            <circle
              className="score-circle-val"
              cx="65"
              cy="65"
              r={radius}
              stroke={colors.stroke}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
            />
          </svg>
          <div className="score-circle-text">
            <span className="score-number" style={{ color: colors.stroke }}>
              {Math.round(score)}
            </span>
            <span className="score-max">/100</span>
          </div>
        </div>

        <div className="score-info">
          <div
            className="score-tier-badge"
            style={{
              backgroundColor: colors.bg,
              color: colors.text,
              border: `1px solid ${colors.border}`,
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <Award size={14} aria-hidden="true" />
              {matchTier}
            </span>
          </div>
          <h2>{scoreLabel}</h2>
          <p className="score-summary-text">{summary}</p>
        </div>
      </div>

      <div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onReset}
          style={{ width: '100%', whiteSpace: 'nowrap' }}
          aria-label="Analyze another resume"
        >
          <RefreshCw size={16} aria-hidden="true" />
          <span>Analyze Another Resume</span>
        </button>
      </div>
    </div>
  );
};
