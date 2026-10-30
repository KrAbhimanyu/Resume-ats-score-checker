import React, { useEffect, useState } from 'react';
import { CategoryScore } from '../types/analysis';
import { BarChart3, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

interface CategoryBreakdownProps {
  categories: CategoryScore[];
}

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({ categories }) => {
  const [animatedWidths, setAnimatedWidths] = useState<Record<string, number>>({});

  // Animate progress bars from 0 to their value on mount
  useEffect(() => {
    if (!categories || categories.length === 0) return;

    // Start from zero
    const initial: Record<string, number> = {};
    categories.forEach((cat) => {
      initial[cat.category_id] = 0;
    });
    setAnimatedWidths(initial);

    // Trigger animation after a brief delay so the CSS transition fires
    const raf = requestAnimationFrame(() => {
      setTimeout(() => {
        const target: Record<string, number> = {};
        categories.forEach((cat) => {
          target[cat.category_id] = Math.min(100, Math.max(0, cat.percentage));
        });
        setAnimatedWidths(target);
      }, 80);
    });

    return () => cancelAnimationFrame(raf);
  }, [categories]);

  if (!categories || categories.length === 0) {
    return null;
  }

  const getProgressColor = (percentage: number) => {
    if (percentage >= 80) return 'var(--color-success)';
    if (percentage >= 60) return 'var(--color-primary)';
    if (percentage >= 40) return 'var(--color-warning)';
    return 'var(--color-danger)';
  };

  const getBorderColor = (percentage: number) => {
    if (percentage >= 80) return 'var(--color-success)';
    if (percentage >= 60) return 'var(--color-primary)';
    if (percentage >= 40) return 'var(--color-warning)';
    return 'var(--color-danger)';
  };

  const getTierIcon = (percentage: number) => {
    if (percentage >= 70) return <CheckCircle size={15} style={{ color: 'var(--color-success)' }} aria-hidden="true" />;
    if (percentage >= 40) return <AlertTriangle size={15} style={{ color: 'var(--color-warning)' }} aria-hidden="true" />;
    return <XCircle size={15} style={{ color: 'var(--color-danger)' }} aria-hidden="true" />;
  };

  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <h3 className="section-title">
        <BarChart3 size={20} aria-hidden="true" />
        <span>Evaluation Categories Breakdown</span>
      </h3>

      <div className="categories-grid">
        {categories.map((cat, index) => {
          const pct = Math.min(100, Math.max(0, cat.percentage));
          const color = getProgressColor(pct);
          const borderColor = getBorderColor(pct);
          const animatedPct = animatedWidths[cat.category_id] ?? 0;

          return (
            <div
              key={cat.category_id}
              className="category-card category-card-accented"
              style={{
                borderLeftColor: borderColor,
                animationDelay: `${index * 80}ms`,
              }}
            >
              <div className="category-card-header">
                <span className="category-card-name" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  {getTierIcon(pct)}
                  {cat.category_name}
                </span>
                <span className="category-card-points" style={{ color }}>
                  {cat.score} / {cat.max_score} pts ({Math.round(pct)}%)
                </span>
              </div>

              <div
                className="progress-bar-track"
                role="progressbar"
                aria-valuenow={cat.score}
                aria-valuemin={0}
                aria-valuemax={cat.max_score}
                aria-label={`${cat.category_name} score`}
              >
                <div
                  className="progress-bar-fill progress-bar-animated"
                  style={{
                    width: `${animatedPct}%`,
                    backgroundColor: color,
                  }}
                />
              </div>

              <p className="category-card-explanation">{cat.explanation}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
