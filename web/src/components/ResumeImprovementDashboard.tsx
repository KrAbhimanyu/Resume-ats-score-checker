import React, { useState } from 'react';
import {
  ResumeImprovementAssistant,
  BulletImprovement,
  BulletImprovementResponse,
} from '../types/analysis';
import { improveBullet } from '../services/analysisApi';
import {
  Sparkles,
  CheckCircle2,
  Copy,
  Check,
  Edit2,
  RotateCcw,
  AlertCircle,
  ListChecks,
  Zap,
  Award,
  TrendingUp,
  Info,
  Send,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ResumeImprovementDashboardProps {
  assistant: ResumeImprovementAssistant;
}

export const ResumeImprovementDashboard: React.FC<ResumeImprovementDashboardProps> = ({
  assistant,
}) => {
  // Checklist local state
  const [completedItems, setCompletedItems] = useState<Record<string, boolean>>({});

  // Bullet edit and copy states
  const [editedBullets, setEditedBullets] = useState<Record<string, string>>({});
  const [isEditingBullet, setIsEditingBullet] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Custom bullet tester state
  const [customBulletInput, setCustomBulletInput] = useState<string>('');
  const [isAnalyzingCustom, setIsAnalyzingCustom] = useState<boolean>(false);
  const [customResult, setCustomResult] = useState<BulletImprovementResponse | null>(null);
  const [customError, setCustomError] = useState<string | null>(null);
  const [editedCustomRewrite, setEditedCustomRewrite] = useState<string>('');
  const [isEditingCustom, setIsEditingCustom] = useState<boolean>(false);

  // Active verb tab
  const [activeVerbCategoryIndex, setActiveVerbCategoryIndex] = useState<number>(0);

  // Accordion open/collapse states
  const [showMetricsGuide, setShowMetricsGuide] = useState<boolean>(true);
  const [showVerbsGuide, setShowVerbsGuide] = useState<boolean>(true);

  if (!assistant) {
    return null;
  }

  const toggleChecklist = (id: string) => {
    setCompletedItems((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleCopy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId((curr) => (curr === id ? null : curr));
      }, 2000);
    } catch {
      // Fallback if clipboard API is unavailable
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId((curr) => (curr === id ? null : curr));
      }, 2000);
    }
  };

  const handleCustomAnalyze = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!customBulletInput.trim()) {
      setCustomError('Please type or paste a bullet point to analyze.');
      return;
    }

    setCustomError(null);
    setIsAnalyzingCustom(true);
    try {
      const res = await improveBullet(customBulletInput, assistant.skill_alignment.matched_skills);
      setCustomResult(res);
      setEditedCustomRewrite(res.suggested_rewrite);
      setIsEditingCustom(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to analyze bullet point.';
      setCustomError(msg);
    } finally {
      setIsAnalyzingCustom(false);
    }
  };

  const checklistTotal = assistant.improvement_checklist.length;
  const checklistDoneCount = assistant.improvement_checklist.filter(
    (item) => completedItems[item.id]
  ).length;
  const progressPercent =
    checklistTotal > 0 ? Math.round((checklistDoneCount / checklistTotal) * 100) : 0;

  return (
    <div className="improvement-assistant-container" style={{ marginTop: '2.5rem', marginBottom: '2.5rem' }}>
      {/* 1. Header Banner */}
      <div className="assistant-header-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div className="assistant-icon-badge" aria-hidden="true">
            <Sparkles size={24} style={{ color: 'var(--color-primary)' }} />
          </div>
          <div>
            <h3 className="section-title" style={{ margin: 0 }}>
              Resume Improvement Assistant
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.925rem', marginTop: '0.15rem' }}>
              Personalized, actionable rewrites and guidance to maximize your resume's impact and job alignment.
            </p>
          </div>
        </div>

        {/* Ethical Transparency Advisory */}
        <div className="alert alert-info" style={{ marginTop: '1rem', marginBottom: '0.25rem' }}>
          <Info size={18} style={{ flexShrink: 0 }} aria-hidden="true" />
          <span style={{ fontSize: '0.875rem' }}>
            <strong>Authenticity & Ethical Guidance:</strong> {assistant.skill_alignment.ethical_guidance}
            {' '}Never invent skills, companies, tools, or performance metrics you did not achieve.
          </span>
        </div>
      </div>

      {/* 2. Resume Strengths */}
      {assistant.strengths && assistant.strengths.length > 0 && (
        <div style={{ marginTop: '1.75rem' }}>
          <h4 className="assistant-subheading">
            <Award size={18} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
            <span>Identified Resume Strengths</span>
          </h4>
          <div className="strengths-grid">
            {assistant.strengths.map((str, idx) => (
              <div key={idx} className="strength-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <CheckCircle2 size={16} style={{ color: 'var(--color-success)', flexShrink: 0 }} aria-hidden="true" />
                  <span className="strength-title">{str.title}</span>
                </div>
                <p className="strength-description">{str.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Bullet-Point Improvements */}
      <div style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <div>
            <h4 className="assistant-subheading" style={{ marginBottom: '0.25rem' }}>
              <Zap size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
              <span>Bullet-Point Enhancements</span>
            </h4>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
              Transform passive, vague duties into high-impact accomplishment statements.
            </p>
          </div>
          <div className="formula-pill">
            <strong>Formula:</strong> Action + Task + Method/Tech + [Measurable Result]
          </div>
        </div>

        {assistant.bullet_improvements && assistant.bullet_improvements.length > 0 ? (
          <div className="bullet-improvements-list">
            {assistant.bullet_improvements.map((bi: BulletImprovement) => {
              const isEditing = isEditingBullet[bi.id] || false;
              const currentRewrite =
                editedBullets[bi.id] !== undefined
                  ? editedBullets[bi.id]
                  : bi.suggested_rewrite;
              const isCopied = copiedId === bi.id;

              return (
                <div key={bi.id} className="bullet-improvement-card">
                  {/* Original Bullet */}
                  <div className="bullet-original-section">
                    <div className="bullet-badge-row">
                      <span className="badge badge-warning">Original Bullet</span>
                      {bi.action_verb && (
                        <span className="badge badge-neutral">Recommended Verb: {bi.action_verb}</span>
                      )}
                    </div>
                    <p className="bullet-original-text">"{bi.original_text}"</p>
                  </div>

                  {/* Why it could be improved */}
                  <div className="bullet-issue-section">
                    <AlertCircle size={15} style={{ color: 'var(--color-warning)', flexShrink: 0 }} aria-hidden="true" />
                    <span>
                      <strong>Why to improve:</strong> {bi.issue}
                    </span>
                  </div>

                  {/* Suggested Rewrite with Edit / Copy */}
                  <div className="bullet-rewrite-section">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span className="bullet-rewrite-label">
                        <strong>Suggested Rewritten Version:</strong>
                      </span>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-small"
                          onClick={() => {
                            if (!isEditing && editedBullets[bi.id] === undefined) {
                              setEditedBullets((prev) => ({
                                ...prev,
                                [bi.id]: bi.suggested_rewrite,
                              }));
                            }
                            setIsEditingBullet((prev) => ({
                              ...prev,
                              [bi.id]: !prev[bi.id],
                            }));
                          }}
                          aria-label={isEditing ? 'Done Editing' : 'Edit Suggestion'}
                        >
                          <Edit2 size={13} aria-hidden="true" />
                          <span>{isEditing ? 'Done Editing' : 'Edit Suggestion'}</span>
                        </button>

                        {editedBullets[bi.id] !== undefined && editedBullets[bi.id] !== bi.suggested_rewrite && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-small"
                            onClick={() => {
                              setEditedBullets((prev) => ({
                                ...prev,
                                [bi.id]: bi.suggested_rewrite,
                              }));
                            }}
                            title="Reset to default rewrite"
                            aria-label="Reset rewrite"
                          >
                            <RotateCcw size={13} aria-hidden="true" />
                          </button>
                        )}

                        <button
                          type="button"
                          className={`btn ${isCopied ? 'btn-success' : 'btn-primary'} btn-small`}
                          onClick={() => handleCopy(bi.id, currentRewrite)}
                          aria-label="Copy Suggested Rewrite"
                        >
                          {isCopied ? (
                            <>
                              <Check size={13} aria-hidden="true" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy size={13} aria-hidden="true" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {isEditing ? (
                      <textarea
                        className="bullet-edit-textarea"
                        value={currentRewrite}
                        onChange={(e) => {
                          const val = e.target.value;
                          setEditedBullets((prev) => ({
                            ...prev,
                            [bi.id]: val,
                          }));
                        }}
                        rows={3}
                        aria-label="Edit suggested rewrite"
                      />
                    ) : (
                      <div className="bullet-rewrite-display">
                        {currentRewrite}
                      </div>
                    )}

                    <div className="bullet-what-to-add">
                      <strong>Information to customize:</strong> {bi.what_to_add}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="card empty-state" style={{ padding: '1.5rem', textAlign: 'center' }}>
            <p>No weak bullet points were automatically detected in the extracted text.</p>
          </div>
        )}

        {/* Interactive Custom Bullet Tester */}
        <div className="custom-tester-card" style={{ marginTop: '1.5rem' }}>
          <h5 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Edit2 size={16} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
            <span>Test & Improve Any Other Resume Bullet Point</span>
          </h5>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '0.75rem' }}>
            Paste any line from your resume to evaluate its strength, detect missing metrics, and receive an instant rewrite suggestion.
          </p>

          <form onSubmit={handleCustomAnalyze} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <input
                type="text"
                className="input-text"
                style={{ flex: '1 1 300px' }}
                placeholder="e.g., Worked on API testing."
                value={customBulletInput}
                onChange={(e) => setCustomBulletInput(e.target.value)}
                disabled={isAnalyzingCustom}
                aria-label="Custom bullet point input"
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isAnalyzingCustom || !customBulletInput.trim()}
                aria-label="Analyze Bullet Point"
              >
                {isAnalyzingCustom ? (
                  <>
                    <Loader2 size={16} className="spin" aria-hidden="true" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Send size={15} aria-hidden="true" />
                    <span>Analyze Bullet</span>
                  </>
                )}
              </button>
            </div>
            {customError && (
              <p style={{ color: 'var(--color-danger)', fontSize: '0.85rem' }}>{customError}</p>
            )}
          </form>

          {/* Custom Analyzer Result */}
          {customResult && (
            <div className="custom-result-box" style={{ marginTop: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span className={`badge ${customResult.is_weak ? 'badge-warning' : 'badge-success'}`}>
                  {customResult.is_weak ? 'Needs Improvement' : 'Strong Structure'}
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => setIsEditingCustom(!isEditingCustom)}
                    aria-label="Edit Custom Rewrite"
                  >
                    <Edit2 size={13} aria-hidden="true" />
                    <span>{isEditingCustom ? 'Done' : 'Edit'}</span>
                  </button>
                  <button
                    type="button"
                    className={`btn ${copiedId === 'custom' ? 'btn-success' : 'btn-primary'} btn-small`}
                    onClick={() => handleCopy('custom', editedCustomRewrite)}
                    aria-label="Copy Custom Rewrite"
                  >
                    {copiedId === 'custom' ? (
                      <>
                        <Check size={13} aria-hidden="true" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={13} aria-hidden="true" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {customResult.issues.length > 0 && (
                <ul style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', paddingLeft: '1.25rem', marginBottom: '0.5rem' }}>
                  {customResult.issues.map((iss, i) => (
                    <li key={i}>{iss}</li>
                  ))}
                </ul>
              )}

              {isEditingCustom ? (
                <textarea
                  className="bullet-edit-textarea"
                  value={editedCustomRewrite}
                  onChange={(e) => setEditedCustomRewrite(e.target.value)}
                  rows={2}
                  aria-label="Edit custom rewrite"
                />
              ) : (
                <div className="bullet-rewrite-display">
                  {editedCustomRewrite}
                </div>
              )}

              <p style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', marginTop: '0.4rem' }}>
                <strong>Information to customize:</strong> {customResult.what_to_add}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 4. Job-Description Skill Alignment */}
      <div style={{ marginTop: '2.25rem' }}>
        <h4 className="assistant-subheading">
          <TrendingUp size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          <span>Job-Description Skill Alignment</span>
        </h4>

        <div className="skill-alignment-grid">
          {/* Matched Skills */}
          <div className="skill-alignment-card card-matched">
            <h5 className="skill-card-title">
              <span className="status-indicator status-green" aria-hidden="true" />
              <span>Skills Found in Both Resume & Job ({assistant.skill_alignment.matched_skills.length})</span>
            </h5>
            <div className="chips-wrapper" style={{ marginTop: '0.5rem' }}>
              {assistant.skill_alignment.matched_skills.length > 0 ? (
                assistant.skill_alignment.matched_skills.map((s, idx) => (
                  <span key={idx} className="chip chip-matched">
                    <Check size={12} aria-hidden="true" />
                    <span>{s}</span>
                  </span>
                ))
              ) : (
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                  No exact keyword skills matched yet.
                </p>
              )}
            </div>
          </div>

          {/* Missing from Resume */}
          <div className="skill-alignment-card card-missing">
            <h5 className="skill-card-title">
              <span className="status-indicator status-red" aria-hidden="true" />
              <span>Skills in Job Not Found in Resume ({assistant.skill_alignment.missing_from_resume_skills.length})</span>
            </h5>
            <div className="chips-wrapper" style={{ marginTop: '0.5rem' }}>
              {assistant.skill_alignment.missing_from_resume_skills.length > 0 ? (
                assistant.skill_alignment.missing_from_resume_skills.map((s, idx) => (
                  <span key={idx} className="chip chip-missing" title="Missing from resume - do not add if not possessed">
                    <span>{s}</span>
                  </span>
                ))
              ) : (
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                  All job technical skills were found in your resume!
                </p>
              )}
            </div>
          </div>

          {/* Weakly Evidenced */}
          <div className="skill-alignment-card card-weak">
            <h5 className="skill-card-title">
              <span className="status-indicator status-amber" aria-hidden="true" />
              <span>Mentioned Skills Lacking Experience Bullets ({assistant.skill_alignment.weakly_evidenced_skills.length})</span>
            </h5>
            <div className="chips-wrapper" style={{ marginTop: '0.5rem' }}>
              {assistant.skill_alignment.weakly_evidenced_skills.length > 0 ? (
                assistant.skill_alignment.weakly_evidenced_skills.map((s, idx) => (
                  <span key={idx} className="chip chip-weak" title="Listed in skills but missing project accomplishment bullets">
                    <span>{s}</span>
                  </span>
                ))
              ) : (
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                  All matched skills are supported by active experience bullets.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Recommended Action Verbs */}
      <div style={{ marginTop: '2.25rem' }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
          onClick={() => setShowVerbsGuide(!showVerbsGuide)}
        >
          <h4 className="assistant-subheading" style={{ margin: 0 }}>
            <Sparkles size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
            <span>Recommended High-Impact Action Verbs</span>
          </h4>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            style={{ border: 'none', background: 'transparent' }}
            aria-label={showVerbsGuide ? 'Collapse Action Verbs' : 'Expand Action Verbs'}
          >
            {showVerbsGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>

        {showVerbsGuide && (
          <div style={{ marginTop: '0.75rem' }}>
            <div className="verbs-tabs" role="tablist">
              {assistant.recommended_verbs.map((cat, idx) => (
                <button
                  key={idx}
                  type="button"
                  role="tab"
                  aria-selected={activeVerbCategoryIndex === idx}
                  className={`tab-btn ${activeVerbCategoryIndex === idx ? 'active' : ''}`}
                  onClick={() => setActiveVerbCategoryIndex(idx)}
                >
                  {cat.category_name}
                </button>
              ))}
            </div>

            <div className="verb-chips-grid">
              {assistant.recommended_verbs[activeVerbCategoryIndex]?.verbs.map((verb, i) => {
                const isCopied = copiedId === `verb-${verb}`;
                return (
                  <button
                    key={i}
                    type="button"
                    className="verb-pill"
                    onClick={() => handleCopy(`verb-${verb}`, verb)}
                    title={`Click to copy "${verb}"`}
                    aria-label={`Copy action verb ${verb}`}
                  >
                    <span>{verb}</span>
                    {isCopied ? <Check size={12} style={{ color: 'var(--color-success)' }} /> : <Copy size={11} style={{ opacity: 0.5 }} />}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 6. Measurable Achievements Guidance */}
      <div style={{ marginTop: '2.25rem' }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
          onClick={() => setShowMetricsGuide(!showMetricsGuide)}
        >
          <h4 className="assistant-subheading" style={{ margin: 0 }}>
            <TrendingUp size={18} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
            <span>Adding Measurable Achievements (Metric Discovery Guide)</span>
          </h4>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            style={{ border: 'none', background: 'transparent' }}
            aria-label={showMetricsGuide ? 'Collapse Metrics Guide' : 'Expand Metrics Guide'}
          >
            {showMetricsGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>

        {showMetricsGuide && (
          <div className="metrics-guidance-list" style={{ marginTop: '0.75rem' }}>
            {assistant.metric_guidance.map((item, idx) => {
              const isCopied = copiedId === `metric-${idx}`;
              return (
                <div key={idx} className="metric-guidance-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                    <span className="metric-type-badge">{item.metric_type}</span>
                    <button
                      type="button"
                      className="btn btn-secondary btn-small"
                      onClick={() => handleCopy(`metric-${idx}`, item.example_pattern)}
                      aria-label={`Copy pattern for ${item.metric_type}`}
                    >
                      {isCopied ? (
                        <>
                          <Check size={12} aria-hidden="true" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} aria-hidden="true" />
                          <span>Copy Pattern</span>
                        </>
                      )}
                    </button>
                  </div>
                  <p className="metric-question">
                    <strong>Reflection Question:</strong> "{item.guiding_question}"
                  </p>
                  <p className="metric-pattern">
                    <code>{item.example_pattern}</code>
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 7. Prioritized Improvement Checklist */}
      <div style={{ marginTop: '2.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <div>
            <h4 className="assistant-subheading" style={{ marginBottom: '0.25rem' }}>
              <ListChecks size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
              <span>Prioritized Improvement Checklist</span>
            </h4>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
              Track your revision progress before sending your resume to employers.
            </p>
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-primary)' }}>
            {checklistDoneCount} of {checklistTotal} completed ({progressPercent}%)
          </div>
        </div>

        {/* Progress Bar */}
        <div className="progress-bar-container" style={{ marginBottom: '1rem', height: '6px' }}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: progressPercent === 100 ? 'var(--color-success)' : 'var(--color-primary)',
            }}
          />
        </div>

        <div className="checklist-wrapper">
          {assistant.improvement_checklist.map((item) => {
            const isDone = completedItems[item.id] || false;
            const priorityClass =
              item.priority === 'high'
                ? 'badge-danger'
                : item.priority === 'medium'
                ? 'badge-warning'
                : 'badge-neutral';

            return (
              <div
                key={item.id}
                className={`checklist-item-card ${isDone ? 'checklist-item-completed' : ''}`}
                onClick={() => toggleChecklist(item.id)}
              >
                <input
                  type="checkbox"
                  className="checklist-checkbox"
                  checked={isDone}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleChecklist(item.id);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  aria-label={item.title}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span className={`checklist-item-title ${isDone ? 'completed-title' : ''}`}>
                      {item.title}
                    </span>
                    <span className={`badge ${priorityClass}`}>
                      {item.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="checklist-item-description">{item.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
