import React, { useEffect, useState, useRef } from 'react';
import { RefreshCw, Award, Download } from 'lucide-react';
import { CategoryScore } from '../types/analysis';

interface ScoreOverviewProps {
  score: number;
  categoryScores: CategoryScore[];
  scoreLabel: string;
  matchTier: string;
  summary: string;
  onReset: () => void;
  onDownload: () => void;
}

export const ScoreOverview: React.FC<ScoreOverviewProps> = ({
  score,
  categoryScores,
  scoreLabel,
  matchTier,
  summary,
  onReset,
  onDownload,
}) => {
  // Animated score counter
  const target = Math.round(score);
  const isTest = import.meta.env.MODE === 'test';
  const [displayScore, setDisplayScore] = useState<number>(() => (isTest ? target : 0));
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    if (isTest) {
      setDisplayScore(target);
      return;
    }

    const duration = 1000; // ms
    let startTime: number | null = null;

    const animate = (currentTime: number) => {
      if (startTime === null) startTime = currentTime;
      const elapsed = currentTime - startTime;
      const progress = Math.min(Math.max(elapsed / duration, 0), 1);
      // easeOutQuart
      const eased = 1 - Math.pow(1 - progress, 4);
      setDisplayScore(Math.round(eased * target));
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    };
  }, [target, isTest]);

  // Score gauge math
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  // Determine tier colors
  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'exceptional match':
        return { stroke: '#16a34a', bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0', glow: 'rgba(22,163,74,0.35)' };
      case 'strong match':
        return { stroke: '#4f46e5', bg: '#eef2ff', text: '#4338ca', border: '#c7d2fe', glow: 'rgba(79,70,229,0.35)' };
      case 'good match':
        return { stroke: '#0284c7', bg: '#f0f9ff', text: '#0369a1', border: '#bae6fd', glow: 'rgba(2,132,199,0.35)' };
      case 'fair match':
        return { stroke: '#d97706', bg: '#fffbeb', text: '#b45309', border: '#fde68a', glow: 'rgba(217,119,6,0.35)' };
      default:
        return { stroke: '#dc2626', bg: '#fef2f2', text: '#b91c1c', border: '#fecaca', glow: 'rgba(220,38,38,0.35)' };
    }
  };

  const colors = getTierColor(matchTier);

  return (
    <div className="results-header-card">
      <div className="score-visual-col">
        {/* Glow ring + SVG circle */}
        <div
          className="score-circle-container"
          role="img"
          aria-label={`Match score: ${Math.round(score)} out of 100`}
        >
          {/* Pulsing glow ring behind the SVG */}
          <div
            className="score-ring-glow"
            style={{ '--glow-color': colors.glow } as React.CSSProperties}
            aria-hidden="true"
          />
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
              style={{ filter: `drop-shadow(0 0 6px ${colors.glow})` }}
            />
          </svg>
          <div className="score-circle-text">
            <span className="score-number" style={{ color: colors.stroke }}>
              {displayScore}
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

          {/* Score breakdown mini bars */}
          <div className="score-breakdown-mini" aria-label="Score breakdown by dimension">
            {categoryScores.map((category) => (
              <div key={category.category_id} className="score-breakdown-row">
                <span className="score-breakdown-label">{category.category_name}</span>
                <div className="score-breakdown-track">
                  <div
                    className="score-breakdown-fill"
                    style={{
                      width: `${Math.min(100, Math.max(0, category.percentage))}%`,
                      backgroundColor: colors.stroke,
                    }}
                  />
                </div>
                <span className="score-breakdown-pct">{Math.round(category.percentage)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="score-actions-col">
        <button
          type="button"
          className="btn btn-primary"
          onClick={onReset}
          style={{ width: '100%', whiteSpace: 'nowrap' }}
          aria-label="Analyze another resume"
        >
          <RefreshCw size={16} aria-hidden="true" />
          <span>Analyze Another Resume</span>
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={onDownload}
          style={{ width: '100%', whiteSpace: 'nowrap' }}
          aria-label="Download Analysis Report"
        >
          <Download size={16} aria-hidden="true" />
          <span>Download Report</span>
        </button>
      </div>
    </div>
  );
};
