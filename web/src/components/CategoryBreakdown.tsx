import React from 'react';
import { CategoryScore } from '../types/analysis';
import { BarChart3 } from 'lucide-react';

interface CategoryBreakdownProps {
  categories: CategoryScore[];
}

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({ categories }) => {
  if (!categories || categories.length === 0) {
    return null;
  }

  const getProgressColor = (percentage: number) => {
    if (percentage >= 80) return 'var(--color-success)';
    if (percentage >= 60) return 'var(--color-primary)';
    if (percentage >= 40) return 'var(--color-warning)';
    return 'var(--color-danger)';
  };

  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <h3 className="section-title">
        <BarChart3 size={20} aria-hidden="true" />
        <span>Evaluation Categories Breakdown</span>
      </h3>

      <div className="categories-grid">
        {categories.map((cat) => {
          const pct = Math.min(100, Math.max(0, cat.percentage));
          const color = getProgressColor(pct);

          return (
            <div key={cat.category_id} className="category-card">
              <div className="category-card-header">
                <span className="category-card-name">{cat.category_name}</span>
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
                  className="progress-bar-fill"
                  style={{
                    width: `${pct}%`,
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

