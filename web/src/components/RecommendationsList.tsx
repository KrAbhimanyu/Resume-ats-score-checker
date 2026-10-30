import React, { useState } from 'react';
import { Recommendation } from '../types/analysis';
import { Lightbulb, Info, AlertCircle, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

interface RecommendationsListProps {
  recommendations: Recommendation[];
}

export const RecommendationsList: React.FC<RecommendationsListProps> = ({ recommendations }) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  if (!recommendations || recommendations.length === 0) {
    return null;
  }

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return {
          cardClass: 'rec-high',
          badgeBg: 'var(--color-danger-subtle)',
          badgeColor: 'var(--color-danger)',
          Icon: AlertCircle,
          iconColor: 'var(--color-danger)',
        };
      case 'medium':
        return {
          cardClass: 'rec-medium',
          badgeBg: 'var(--color-warning-subtle)',
          badgeColor: '#b45309',
          Icon: AlertTriangle,
          iconColor: 'var(--color-warning)',
        };
      default:
        return {
          cardClass: 'rec-low',
          badgeBg: 'var(--color-primary-subtle)',
          badgeColor: 'var(--color-primary)',
          Icon: Info,
          iconColor: 'var(--color-primary)',
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
          const { Icon } = style;
          const isExpanded = expandedIds.has(rec.id);

          return (
            <div key={rec.id} className={`recommendation-card ${style.cardClass}`}>
              {/* Clickable header row */}
              <button
                type="button"
                className="rec-accordion-btn"
                onClick={() => toggleExpand(rec.id)}
                aria-expanded={isExpanded}
                aria-controls={`rec-body-${rec.id}`}
              >
                <div className="rec-header">
                  <span className="rec-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Icon size={16} aria-hidden="true" style={{ color: style.iconColor, flexShrink: 0 }} />
                    {rec.title}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                    <span
                      className="rec-priority-badge"
                      style={{
                        backgroundColor: style.badgeBg,
                        color: style.badgeColor,
                      }}
                    >
                      {rec.priority} Priority
                    </span>
                    <span className="rec-toggle-icon" aria-hidden="true">
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </span>
                  </div>
                </div>
              </button>

              {/* Collapsible body */}
              {isExpanded && (
                <div
                  id={`rec-body-${rec.id}`}
                  className="rec-body"
                >
                  <p className="rec-description">{rec.description}</p>
                </div>
              )}

              {/* Always show a short preview when collapsed */}
              {!isExpanded && (
                <p className="rec-description rec-description-preview">
                  {rec.description.length > 120
                    ? `${rec.description.slice(0, 120)}…`
                    : rec.description}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
