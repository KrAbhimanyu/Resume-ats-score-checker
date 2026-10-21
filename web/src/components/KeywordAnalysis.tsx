import React from 'react';
import { RequirementMatch, MissingRequirement } from '../types/analysis';
import { CheckCircle2, XCircle, AlertTriangle, Tag } from 'lucide-react';

interface KeywordAnalysisProps {
  matchedRequirements: RequirementMatch[];
  missingRequirements: MissingRequirement[];
  keywordsFound: string[];
}

export const KeywordAnalysis: React.FC<KeywordAnalysisProps> = ({
  matchedRequirements,
  missingRequirements,
  keywordsFound,
}) => {
  // Separate genuinely missing vs weakly evidenced
  const genuinelyMissing = missingRequirements.filter((req) => !req.is_evidenced_elsewhere);
  const weaklyEvidenced = missingRequirements.filter((req) => req.is_evidenced_elsewhere);

  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <h3 className="section-title">
        <Tag size={20} aria-hidden="true" />
        <span>Requirements & Keywords Analysis</span>
      </h3>

      {/* Keywords Found in Resume */}
      {keywordsFound && keywordsFound.length > 0 && (
        <div style={{ marginBottom: '1.5rem', background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '0.5rem' }}>
            Relevant Keywords & Technologies Identified in Resume ({keywordsFound.length})
          </h4>
          <div className="chips-container">
            {keywordsFound.map((kw) => (
              <span key={kw} className="chip chip-success">
                <CheckCircle2 size={13} aria-hidden="true" />
                <span>{kw}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="requirements-grid">
        {/* Matched Requirements Panel */}
        <div className="req-panel">
          <div className="req-panel-header">
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-success)', fontSize: '0.95rem' }}>
              <CheckCircle2 size={18} aria-hidden="true" />
              <span>Matched Requirements</span>
            </h4>
            <span className="count-badge" style={{ background: 'var(--color-success-subtle)', color: 'var(--color-success)' }}>
              {matchedRequirements.length}
            </span>
          </div>

          {matchedRequirements.length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
              No explicit requirements were detected as strongly matched.
            </p>
          ) : (
            <ul className="req-list">
              {matchedRequirements.map((req, idx) => (
                <li key={`matched-${idx}`} className="req-item">
                  <div className="req-item-title">{req.requirement}</div>
                  <div className="req-item-meta">
                    <span style={{ textTransform: 'capitalize' }}>Category: {req.category}</span>
                    <span>•</span>
                    <span>Evidence: {req.evidence_strength}</span>
                    {req.matched_terms.length > 0 && (
                      <>
                        <span>•</span>
                        <span>Terms: {req.matched_terms.join(', ')}</span>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Missing / Weakly Evidenced Requirements Panel */}
        <div className="req-panel">
          <div className="req-panel-header">
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-danger)', fontSize: '0.95rem' }}>
              <XCircle size={18} aria-hidden="true" />
              <span>Missing or Weakly Evidenced</span>
            </h4>
            <span className="count-badge" style={{ background: 'var(--color-danger-subtle)', color: 'var(--color-danger)' }}>
              {missingRequirements.length}
            </span>
          </div>

          {missingRequirements.length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
              Outstanding! No missing requirements detected.
            </p>
          ) : (
            <ul className="req-list">
              {/* Genuinely missing requirements */}
              {genuinelyMissing.map((req, idx) => (
                <li key={`missing-${idx}`} className="req-item" style={{ borderLeft: '3px solid var(--color-danger)' }}>
                  <div className="req-item-title">{req.requirement}</div>
                  <div className="req-item-meta">
                    <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>Missing ({req.importance})</span>
                    <span>•</span>
                    <span>{req.reason}</span>
                  </div>
                </li>
              ))}

              {/* Weakly evidenced requirements */}
              {weaklyEvidenced.map((req, idx) => (
                <li key={`weak-${idx}`} className="req-item" style={{ borderLeft: '3px solid var(--color-warning)' }}>
                  <div className="req-item-title">{req.requirement}</div>
                  <div className="req-item-meta">
                    <span style={{ color: '#b45309', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}>
                      <AlertTriangle size={13} aria-hidden="true" />
                      Weak Evidence
                    </span>
                    <span>•</span>
                    <span>{req.reason}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

