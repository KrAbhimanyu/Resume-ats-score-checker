import React from 'react';
import { Recommendation } from '../types/analysis';
import { Lightbulb, Info } from 'lucide-react';

interface RecommendationsListProps {
  recommendations: Recommendation[];
}

export const RecommendationsList: React.FC<RecommendationsListProps> = ({ recommendations }) => {
  if (!recommendations || recommendations.length === 0) {
    return null;
  }

  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return {
          cardClass: 'rec-high',
          badgeBg: 'var(--color-danger-subtle)',
          badgeColor: 'var(--color-danger)',
        };
      case 'medium':
        return {
          cardClass: 'rec-medium',
          badgeBg: 'var(--color-warning-subtle)',
          badgeColor: '#b45309',
        };
      default:
        return {
          cardClass: 'rec-low',
          badgeBg: 'var(--color-primary-subtle)',
          badgeColor: 'var(--color-primary)',
        };
    }
  };

  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <h3 className="section-title">
        <Lightbulb size={20} aria-hidden="true" />
        <span>Actionable Improvement Recommendations</span>
      </h3>

      <div className="alert alert-info" style={{ marginBottom: '1.25rem' }}>
        <Info size={18} style={{ flexShrink: 0 }} aria-hidden="true" />
        <span>
          <strong>Ethical Guidance:</strong> Add qualifications, technologies, or metrics only if you
          genuinely have hands-on experience with them. Do not engage in keyword stuffing or misrepresent
          your professional background.
        </span>
      </div>

      <div className="recommendations-list">
        {recommendations.map((rec) => {
          const style = getPriorityStyle(rec.priority);

          return (
            <div key={rec.id} className={`recommendation-card ${style.cardClass}`}>
              <div className="rec-header">
                <span className="rec-title">{rec.title}</span>
                <span
                  className="rec-priority-badge"
                  style={{
                    backgroundColor: style.badgeBg,
                    color: style.badgeColor,
                  }}
                >
                  {rec.priority} Priority
                </span>
              </div>
              <p className="rec-description">{rec.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

