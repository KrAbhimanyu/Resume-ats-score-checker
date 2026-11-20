import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import {
  Award, BookOpen, Check, ChevronLeft, Code2, ExternalLink, GraduationCap,
  MessageCircle, Send, Sparkles, Target, Upload,
} from 'lucide-react';
import { careerRequest } from '../services/careerApi';
import { getApiBaseUrl } from '../services/analysisApi';
import '../styles/learning-academy.css';

type ApiRecord = Record<string, unknown>;

interface AcademyDashboard {
  tracks: ApiRecord[];
  recommendations: ApiRecord[];
  resources: ApiRecord[];
  skill_progress: ApiRecord[];
  resume_skill_evidence: string[];
  assessments: ApiRecord[];
  evidence: ApiRecord[];
  projects: ApiRecord[];
  certificates: ApiRecord[];
  certificate_notice: string;
}

interface AcademyMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

interface RoadmapDraft {
  targetRole: string;
  goal: string;
  skillsToDevelop: string;
  trackIds: string[];
}

const record = (value: unknown): ApiRecord =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as ApiRecord : {};

const records = (value: unknown): ApiRecord[] =>
  Array.isArray(value) ? value.map(record) : [];

const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

const display = (value: unknown, fallback = 'Not provided'): string =>
  typeof value === 'string' && value.trim() ? value : fallback;

const formatDate = (value: unknown): string => {
  if (typeof value !== 'string' || !value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const EMPTY_DASHBOARD: AcademyDashboard = {
  tracks: [], recommendations: [], resources: [], skill_progress: [],
  resume_skill_evidence: [], assessments: [], evidence: [], projects: [],
  certificates: [], certificate_notice: '',
};

export const LearningAcademySection: React.FC<{ token: string }> = ({ token }) => {
  const [dashboard, setDashboard] = useState<AcademyDashboard>(EMPTY_DASHBOARD);
  const [activeTrack, setActiveTrack] = useState<ApiRecord | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [assessmentResult, setAssessmentResult] = useState<ApiRecord | null>(null);
  const [codeByExercise, setCodeByExercise] = useState<Record<string, string>>({});
  const [codeResults, setCodeResults] = useState<Record<string, ApiRecord>>({});
  const [targetRole, setTargetRole] = useState('');
  const [goal, setGoal] = useState('');
  const [skillsToDevelop, setSkillsToDevelop] = useState('');
  const [roadmaps, setRoadmaps] = useState<ApiRecord[]>([]);
  const [roadmapEdits, setRoadmapEdits] = useState<Record<string, RoadmapDraft>>({});
  const [selectedTracks, setSelectedTracks] = useState<string[]>([]);
  const [messages, setMessages] = useState<AcademyMessage[]>([]);
  const [chatMessage, setChatMessage] = useState('');
  const [projectTitle, setProjectTitle] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [projectSkills, setProjectSkills] = useState('');
  const [projectUrl, setProjectUrl] = useState('');
  const [projectReview, setProjectReview] = useState<ApiRecord | null>(null);
  const [evidenceSkill, setEvidenceSkill] = useState('');
  const [evidenceType, setEvidenceType] = useState('portfolio');
  const [evidenceDescription, setEvidenceDescription] = useState('');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const request = useCallback(async <T,>(
    path: string,
    options?: { method?: string; body?: unknown },
  ): Promise<T> => careerRequest<T>(token, `/academy${path}`, options), [token]);

  const run = async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      return await action();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Learning Academy request failed.');
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await careerRequest<AcademyDashboard>(token, '/academy/dashboard');
      setDashboard(result);
      setSelectedTracks((current) => current.length
        ? current
        : records(result.recommendations).slice(0, 2).map((item) => String(item.track_id)));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load learning progress.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  const loadProjects = useCallback(async () => {
    const result = await careerRequest<ApiRecord[]>(token, '/academy/projects');
    setDashboard((current) => ({ ...current, projects: result }));
  }, [token]);

  useEffect(() => {
    let active = true;
    void Promise.all([
      careerRequest<AcademyDashboard>(token, '/academy/dashboard'),
      careerRequest<ApiRecord[]>(token, '/academy/roadmaps'),
      careerRequest<ApiRecord[]>(token, '/academy/projects'),
      careerRequest<AcademyMessage[]>(token, '/academy/assistant/history'),
    ]).then(([home, savedRoadmaps, savedProjects, history]) => {
      if (!active) return;
      setDashboard({ ...home, projects: savedProjects });
      setRoadmaps(savedRoadmaps);
      setMessages(history);
      setSelectedTracks(records(home.recommendations).slice(0, 2).map((item) => String(item.track_id)));
    }).catch((requestError: unknown) => {
      if (active) setError(requestError instanceof Error ? requestError.message : 'Could not load the Learning Academy.');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [token]);

  const openTrack = async (trackId: string) => {
    const result = await run(() => request<ApiRecord>(`/tracks/${encodeURIComponent(trackId)}`));
    if (result) {
      setActiveTrack(result);
      setAnswers({});
      const latestAssessment = record(result.latest_assessment);
      setAssessmentResult(Object.keys(record(latestAssessment.result)).length
        ? record(latestAssessment.result)
        : null);
      setCodeResults(records(result.exercises).reduce<Record<string, ApiRecord>>((saved, exercise) => {
        const exerciseResult = record(exercise.saved_result);
        if (Object.keys(exerciseResult).length) saved[String(exercise.id)] = exerciseResult;
        return saved;
      }, {}));
      const starters = records(result.exercises).reduce<Record<string, string>>((all, exercise) => {
        const exerciseId = String(exercise.id);
        const signature = String(exercise.signature || '');
        all[exerciseId] = `${signature}\n    return 0`;
        return all;
      }, {});
      setCodeByExercise(starters);
    }
  };

  const completeLesson = async (lessonId: string) => {
    if (!activeTrack) return;
    const result = await run(() => request<ApiRecord>(
      `/tracks/${encodeURIComponent(String(activeTrack.id))}/lessons/${encodeURIComponent(lessonId)}/complete`,
      { method: 'POST' },
    ));
    if (result) {
      setNotice('Lesson marked complete.');
      await openTrack(String(activeTrack.id));
      await loadDashboard();
    }
  };

  const submitAssessment = async (event: FormEvent) => {
    event.preventDefault();
    if (!activeTrack) return;
    const questions = records(record(activeTrack.assessment).questions);
    if (questions.some((question) => !answers[String(question.id)])) {
      setError('Answer each question before submitting the assessment.');
      return;
    }
    const result = await run(() => request<ApiRecord>(
      `/tracks/${encodeURIComponent(String(activeTrack.id))}/assessment`,
      { method: 'POST', body: { answers } },
    ));
    if (result) {
      setAssessmentResult(result);
      setNotice(`Assessment submitted: ${String(result.score)}%.`);
      await loadDashboard();
    }
  };

  const submitExercise = async (exerciseId: string) => {
    if (!activeTrack) return;
    const result = await run(() => request<ApiRecord>(
      `/tracks/${encodeURIComponent(String(activeTrack.id))}/exercises/${encodeURIComponent(exerciseId)}`,
      { method: 'POST', body: { code: codeByExercise[exerciseId] || '' } },
    ));
    if (result) {
      setCodeResults((current) => ({ ...current, [exerciseId]: result }));
      setNotice(result.passed ? 'All restricted-evaluator cases passed.' : 'Review the case results and try again.');
      await loadDashboard();
    }
  };

  const makeRoadmap = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedTracks.length) {
      setError('Select at least one learning track.');
      return;
    }
    const result = await run(() => request<ApiRecord>('/roadmaps', {
      method: 'POST',
      body: {
        target_role: targetRole,
        goal,
        skills_to_develop: skillsToDevelop.split(',').map((skill) => skill.trim()).filter(Boolean),
        track_ids: selectedTracks,
      },
    }));
    if (result) {
      setRoadmaps((current) => [result, ...current]);
      setNotice('AI-personalized roadmap saved. Courses and lessons are selected from the Academy catalog.');
    }
  };

  const beginRoadmapEdit = (item: ApiRecord) => {
    const id = String(item.id);
    const roadmap = record(item.roadmap);
    setRoadmapEdits((current) => ({
      ...current,
      [id]: {
        targetRole: String(item.target_role || roadmap.target_role || ''),
        goal: String(roadmap.goal || ''),
        skillsToDevelop: strings(roadmap.skills_to_develop).join(', '),
        trackIds: records(roadmap.sequence).map((step) => String(step.track_id)),
      },
    }));
  };

  const moveRoadmapTrack = (roadmapId: string, index: number, offset: number) => {
    setRoadmapEdits((current) => {
      const draft = current[roadmapId];
      if (!draft) return current;
      const destination = index + offset;
      if (destination < 0 || destination >= draft.trackIds.length) return current;
      const trackIds = [...draft.trackIds];
      [trackIds[index], trackIds[destination]] = [trackIds[destination], trackIds[index]];
      return { ...current, [roadmapId]: { ...draft, trackIds } };
    });
  };

  const saveRoadmapEdit = async (event: FormEvent, roadmapId: string) => {
    event.preventDefault();
    const draft = roadmapEdits[roadmapId];
    if (!draft?.trackIds.length) {
      setError('Keep at least one learning track in the roadmap.');
      return;
    }
    const result = await run(() => request<ApiRecord>(
      `/roadmaps/${encodeURIComponent(roadmapId)}`,
      {
        method: 'PATCH',
        body: {
          target_role: draft.targetRole,
          goal: draft.goal,
          skills_to_develop: draft.skillsToDevelop.split(',').map((skill) => skill.trim()).filter(Boolean),
          track_ids: draft.trackIds,
        },
      },
    ));
    if (result) {
      setRoadmaps((current) => current.map((item) => item.id === roadmapId ? result : item));
      setRoadmapEdits((current) => {
        const updated = { ...current };
        delete updated[roadmapId];
        return updated;
      });
      setNotice('Roadmap changes saved. Its original AI guidance is retained and labeled; generate a new roadmap to refresh it.');
    }
  };

  const askLearningAssistant = async (event: FormEvent) => {
    event.preventDefault();
    if (!chatMessage.trim()) return;
    const prompt = chatMessage.trim();
    const result = await run(() => request<ApiRecord>('/assistant', {
      method: 'POST',
      body: { message: prompt, track_id: activeTrack?.id || null },
    }));
    if (result) {
      setMessages((current) => [
        ...current,
        { role: 'user', content: prompt },
        { role: 'assistant', content: String(result.response), created_at: String(result.created_at) },
      ]);
      setChatMessage('');
    }
  };

  const evaluateProject = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() => request<ApiRecord>('/projects/evaluate', {
      method: 'POST',
      body: {
        title: projectTitle,
        description: projectDescription,
        skills: projectSkills.split(',').map((skill) => skill.trim()).filter(Boolean),
        project_url: projectUrl || null,
      },
    }));
    if (result) {
      setProjectReview(record(result.evaluation));
      setNotice('Project review saved. It evaluates the description only; no linked work was fetched or run.');
      setProjectTitle('');
      setProjectDescription('');
      setProjectSkills('');
      setProjectUrl('');
      await loadProjects();
      await loadDashboard();
    }
  };

  const submitEvidence = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(() => request<ApiRecord>('/skills/evidence', {
      method: 'POST',
      body: {
        skill: evidenceSkill,
        evidence_type: evidenceType,
        description: evidenceDescription,
        evidence_url: evidenceUrl || null,
      },
    }));
    if (result) {
      setNotice('Evidence recorded as user-submitted. It has not been independently verified.');
      setEvidenceSkill('');
      setEvidenceDescription('');
      setEvidenceUrl('');
      await loadDashboard();
    }
  };

  const issueCertificate = async (trackId: string) => {
    const result = await run(() => request<ApiRecord>(
      `/tracks/${encodeURIComponent(trackId)}/certificate`,
      { method: 'POST' },
    ));
    if (result) {
      setNotice('Platform completion certificate issued. It is not an external accreditation.');
      await loadDashboard();
    }
  };

  const fetchCertificate = async (serial: string) => {
    const result = await run(async () => {
      const response = await fetch(
        `${getApiBaseUrl()}/api/v1/career/academy/certificates/${encodeURIComponent(serial)}/download`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        let detail = `Certificate download failed (${response.status}).`;
        try {
          const payload = await response.json() as { detail?: string };
          if (payload.detail) detail = payload.detail;
        } catch {
          // The server may return a non-JSON error body.
        }
        throw new Error(detail);
      }
      return response.blob();
    });
    if (!result) return;
    const url = URL.createObjectURL(result);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${serial}.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  if (loading) return <div className="learning-loading" role="status">Loading your learning progress…</div>;

  const lessons = records(activeTrack?.lessons);
  const exercises = records(activeTrack?.exercises);
  const questions = records(record(activeTrack?.assessment).questions);
  const progress = record(activeTrack?.progress);

  return (
    <div className="learning-academy">
      {error && <div className="learning-alert" role="alert">{error}</div>}
      {notice && <div className="learning-notice" role="status">{notice}</div>}
      {busy && <div className="learning-loading" role="status">Saving your learning activity…</div>}

      {activeTrack ? (
        <section className="career-panel learning-track-panel">
          <button type="button" className="learning-back" onClick={() => setActiveTrack(null)}><ChevronLeft size={16} /> Academy dashboard</button>
          <div className="career-panel-heading">
            <div><p className="career-eyebrow">{String(activeTrack.category).replace(/_/g, ' ')} · {String(activeTrack.level)}</p><h2>{String(activeTrack.title)}</h2></div>
            <span className="learning-progress-badge">{String(progress.percent || 0)}% complete</span>
          </div>
          <p>{String(activeTrack.summary)}</p>
          <div className="learning-skills"><strong>Skills covered</strong>{strings(activeTrack.skills).map((skill) => <span key={skill}>{skill}</span>)}</div>

          <h3>Lessons</h3>
          {lessons.map((lesson) => {
            const completed = Boolean(lesson.completed_at);
            return <article className="learning-lesson" key={String(lesson.id)}>
              <div><p className="career-eyebrow">{String(lesson.minutes)} minutes</p><h4>{String(lesson.title)}</h4><p>{String(lesson.content)}</p></div>
              <button type="button" className="btn btn-secondary" disabled={busy || completed} onClick={() => void completeLesson(String(lesson.id))}>
                {completed ? <><Check size={15} /> Completed</> : 'Mark lesson complete'}
              </button>
            </article>;
          })}

          {exercises.map((exercise) => {
            const id = String(exercise.id);
            const result = codeResults[id];
            return <article className="learning-exercise" key={id}>
              <p className="career-eyebrow">INTERACTIVE CODING PRACTICE · PYTHON</p>
              <h3>{String(exercise.title)}</h3>
              <p>{String(exercise.prompt)}</p>
              <p><strong>Allowed approach:</strong> {String(exercise.allowed_constructs)}</p>
              <label>Python function
                <textarea spellCheck={false} rows={7} maxLength={12000} value={codeByExercise[id] || ''} onChange={(event) => setCodeByExercise((current) => ({ ...current, [id]: event.target.value }))} />
              </label>
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void submitExercise(id)}><Code2 size={15} /> Evaluate against cases</button>
              {result && <div className={result.passed ? 'learning-assessment-result is-passed' : 'learning-assessment-result'}>
                <strong>{String(result.passed_cases || 0)} / {String(result.total_cases || 0)} cases passed · {String(result.score || 0)}%</strong>
                <p>{String(result.evaluation_mode)}</p>
                {records(result.cases).map((item) => <span key={String(item.case)}>Case {String(item.case)}: {item.passed ? 'passed' : `not passed${item.feedback ? ` — ${String(item.feedback)}` : ''}`}</span>)}
                {!Boolean(result.passed) && Boolean(result.error) && <p>{String(result.error)}</p>}
                <small>{String(result.limits || '')}</small>
              </div>}
            </article>;
          })}

          <h3>Knowledge assessment</h3>
          <form className="learning-assessment" onSubmit={(event) => void submitAssessment(event)}>
            {questions.map((question) => <fieldset key={String(question.id)}>
              <legend>{String(question.prompt)}</legend>
              {records(question.options).map((option) => <label key={String(option.id)}>
                <input type="radio" name={String(question.id)} value={String(option.id)} checked={answers[String(question.id)] === String(option.id)} onChange={(event) => setAnswers((current) => ({ ...current, [String(question.id)]: event.target.value }))} />
                {String(option.label)}
              </label>)}
            </fieldset>)}
            <button type="submit" className="btn btn-primary" disabled={busy}>Submit assessment</button>
          </form>
          {assessmentResult && <div className="learning-assessment-result">
            <strong>Score: {String(assessmentResult.score)}% · {assessmentResult.passed ? 'Passed' : 'Keep practicing'}</strong>
            <p>{String(assessmentResult.evidence_label)}</p>
            {records(assessmentResult.results).map((item) => <p key={String(item.question_id)}>{item.correct ? 'Correct' : 'Review'}: {String(item.explanation)}</p>)}
          </div>}
          {record(activeTrack.latest_assessment).score != null && !assessmentResult && (
            <p className="learning-muted">Latest saved score: {String(record(activeTrack.latest_assessment).score)}%</p>
          )}

          <h3>Learning resources and external certification routes</h3>
          <div className="learning-resource-list">
            {records(activeTrack.resources).map((resource) => <a key={String(resource.url)} href={String(resource.url)} target="_blank" rel="noreferrer">
              <BookOpen size={16} /><span><strong>{String(resource.title)}</strong><small>{String(resource.provider)} · {String(resource.kind)}</small></span><ExternalLink size={14} />
            </a>)}
          </div>
          {records(activeTrack.certifications).length > 0 && <div className="learning-external-certifications">
            <h4>External certifications (separate provider assessments)</h4>
            <p>The Academy recommends these official certification pages; it does not issue or verify their credentials.</p>
            {records(activeTrack.certifications).map((certificate) => <a key={String(certificate.url)} href={String(certificate.url)} target="_blank" rel="noreferrer">{String(certificate.title)} · {String(certificate.provider)} <ExternalLink size={13} /></a>)}
          </div>}
          {strings(activeTrack.projects).length > 0 && <div className="learning-project-prompts">
            <h4>Practical project ideas</h4>
            {strings(activeTrack.projects).map((project) => <p key={project}>{project}</p>)}
          </div>}
          {Boolean(progress.certificate_eligible) && <div className="learning-certificate-eligibility">
            <p>All lessons, exercises, and the passing assessment are complete. You are eligible for a platform completion certificate.</p>
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void issueCertificate(String(activeTrack.id))}><Award size={15} /> Issue platform certificate</button>
          </div>}
        </section>
      ) : (
        <>
          <section className="learning-hero">
            <div><p className="career-eyebrow">AI SKILLS & LEARNING ACADEMY</p><h2>Build skills with evidence-based practice</h2><p>Structured learning, assessments, interactive coding evaluation, and progress saved to your account.</p></div>
            <GraduationCap size={34} />
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">PERSONALIZED LEARNING</p><h2>Recommended tracks</h2></div><Target size={20} /></div>
            {!dashboard.recommendations.length && <p>No track recommendations are available yet. Explore the curated tracks below.</p>}
            <div className="learning-track-grid">
              {dashboard.recommendations.map((item) => {
                const track = dashboard.tracks.find((candidate) => candidate.id === item.track_id);
                const trackProgress = record(record(track).progress);
                return <article className="learning-track-card" key={String(item.track_id)}>
                  <p className="career-eyebrow">{String(item.category).replace(/_/g, ' ')}</p>
                  <h3>{String(item.title)}</h3>
                  <p>Skills to develop: {strings(item.skills_to_develop).join(', ') || 'Explore this track'}</p>
                  {!!strings(item.matched_gap_skills).length && <p className="learning-gap-label">Matches your identified skill gap: {strings(item.matched_gap_skills).join(', ')}</p>}
                  <p className="learning-muted">{String(trackProgress.percent || 0)}% complete</p>
                  <button type="button" className="btn btn-primary" onClick={() => void openTrack(String(item.track_id))} disabled={busy}>Open learning track <BookOpen size={15} /></button>
                </article>;
              })}
            </div>
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">YOUR LEARNING DASHBOARD</p><h2>All tracks</h2></div><BookOpen size={20} /></div>
            <div className="learning-track-grid">
              {dashboard.tracks.map((track) => {
                const trackProgress = record(track.progress);
                return <article className="learning-track-card" key={String(track.id)}>
                  <p className="career-eyebrow">{String(track.category).replace(/_/g, ' ')} · {String(track.level)}</p>
                  <h3>{String(track.title)}</h3><p>{String(track.summary)}</p>
                  <div className="learning-progress" aria-label={`${String(trackProgress.percent || 0)} percent complete`}>
                    <span style={{ width: `${Number(trackProgress.percent || 0)}%` }} />
                  </div>
                  <p className="learning-muted">{String(trackProgress.completed_activities || 0)} / {String(trackProgress.total_activities || 0)} lessons and exercises complete</p>
                  <button type="button" className="btn btn-secondary" onClick={() => void openTrack(String(track.id))} disabled={busy}>Continue</button>
                </article>;
              })}
            </div>
            {!!dashboard.resume_skill_evidence.length && <p className="learning-profile-context"><strong>Resume-derived skills:</strong> {dashboard.resume_skill_evidence.slice(0, 25).join(', ')}. These are text matches, not independently verified proficiencies.</p>}
            {!!dashboard.skill_progress.length && <div className="learning-progress-skills"><strong>Tracked skills</strong>{dashboard.skill_progress.map((item) => <span key={String(item.skill)}>{String(item.skill)} · {String(item.status)}</span>)}</div>}
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">AI-PERSONALIZED ROADMAP</p><h2>Plan your next learning steps</h2></div><Sparkles size={20} /></div>
            <p className="career-disclaimer">Uses the existing Career Coach AI consent setting. If enabled, limited resume skill evidence and your stated learning goals are sent to the configured AI provider. Roadmaps use only tracks and lessons in this Academy.</p>
            <form className="learning-form" onSubmit={(event) => void makeRoadmap(event)}>
              <label>Target role<input required minLength={2} maxLength={160} value={targetRole} onChange={(event) => setTargetRole(event.target.value)} placeholder="e.g. Junior cloud engineer" /></label>
              <label>Learning goal<textarea maxLength={2000} rows={2} value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="What are you preparing to do?" /></label>
              <label>Skills to develop<input value={skillsToDevelop} onChange={(event) => setSkillsToDevelop(event.target.value)} placeholder="Comma-separated skill gaps from target roles" /></label>
              <div className="learning-track-selection"><strong>Available tracks</strong>{dashboard.tracks.map((track) => {
                const id = String(track.id);
                return <label key={id}><input type="checkbox" checked={selectedTracks.includes(id)} onChange={(event) => setSelectedTracks((current) => event.target.checked ? [...current, id] : current.filter((value) => value !== id))} />{String(track.title)}</label>;
              })}</div>
              <button type="submit" className="btn btn-primary" disabled={busy}>Generate and save roadmap</button>
            </form>
            {roadmaps.map((item) => {
              const roadmapId = String(item.id);
              const roadmap = record(item.roadmap);
              const edit = roadmapEdits[roadmapId];
              return <article className="learning-roadmap" key={String(item.id)}>
                <h3>{String(item.target_role)}</h3><small>Updated {formatDate(item.updated_at || item.created_at)}</small>
                <p>{String(roadmap.ai_guidance)}</p>
                <p className="learning-muted">{String(roadmap.personalization_method)}</p>
                <div className="learning-roadmap-sequence">{records(roadmap.sequence).map((step) => <div key={String(step.track_id)}>
                  <strong>{String(step.title)}</strong><span>{strings(step.skills).join(', ')}</span>
                  {records(step.lessons).map((lesson) => <small key={String(lesson.id)}>{String(lesson.title)} · {String(lesson.minutes)} min</small>)}
                </div>)}</div>
                {edit ? (
                  <form className="learning-form" onSubmit={(event) => void saveRoadmapEdit(event, roadmapId)}>
                    <label>Target role<input required minLength={2} maxLength={160} value={edit.targetRole} onChange={(event) => setRoadmapEdits((current) => ({ ...current, [roadmapId]: { ...edit, targetRole: event.target.value } }))} /></label>
                    <label>Learning goal<textarea maxLength={2000} rows={2} value={edit.goal} onChange={(event) => setRoadmapEdits((current) => ({ ...current, [roadmapId]: { ...edit, goal: event.target.value } }))} /></label>
                    <label>Skills to develop<input value={edit.skillsToDevelop} onChange={(event) => setRoadmapEdits((current) => ({ ...current, [roadmapId]: { ...edit, skillsToDevelop: event.target.value } }))} /></label>
                    <div className="learning-track-selection"><strong>Track sequence — selected order</strong>
                      {dashboard.tracks.map((track) => {
                        const trackId = String(track.id);
                        return <label key={trackId}><input type="checkbox" checked={edit.trackIds.includes(trackId)} onChange={(event) => setRoadmapEdits((current) => ({
                          ...current,
                          [roadmapId]: {
                            ...edit,
                            trackIds: event.target.checked
                              ? [...edit.trackIds, trackId]
                              : edit.trackIds.filter((value) => value !== trackId),
                          },
                        }))} />{String(track.title)}</label>;
                      })}
                      {edit.trackIds.map((trackId, index) => <div className="learning-roadmap-order" key={trackId}>
                        <span>{index + 1}. {display(dashboard.tracks.find((track) => track.id === trackId)?.title, trackId)}</span>
                        <button type="button" className="btn btn-secondary" disabled={index === 0} onClick={() => moveRoadmapTrack(roadmapId, index, -1)} aria-label={`Move ${trackId} up`}>Move up</button>
                        <button type="button" className="btn btn-secondary" disabled={index === edit.trackIds.length - 1} onClick={() => moveRoadmapTrack(roadmapId, index, 1)} aria-label={`Move ${trackId} down`}>Move down</button>
                      </div>)}
                    </div>
                    <div className="learning-roadmap-actions">
                      <button type="submit" className="btn btn-primary" disabled={busy}>Save roadmap</button>
                      <button type="button" className="btn btn-secondary" onClick={() => setRoadmapEdits((current) => {
                        const updated = { ...current };
                        delete updated[roadmapId];
                        return updated;
                      })}>Cancel</button>
                    </div>
                  </form>
                ) : <button type="button" className="btn btn-secondary" onClick={() => beginRoadmapEdit(item)}>Edit roadmap</button>}
              </article>;
            })}
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">LEGITIMATE LEARNING RESOURCES</p><h2>Courses, references, and certifications</h2></div><ExternalLink size={19} /></div>
            <div className="learning-resource-grid">{dashboard.resources.map((resource) => <a key={String(resource.id)} href={String(resource.url)} target="_blank" rel="noreferrer">
              <span><strong>{String(resource.title)}</strong><small>{String(resource.provider)} · {String(resource.kind)}</small><small>Skills: {strings(resource.skills).join(', ')}</small></span><ExternalLink size={14} />
            </a>)}</div>
            <p className="learning-muted">External providers control course access, pricing, availability, exams, and credentials. Academy progress does not imply completion of external courses.</p>
          </section>

          <section className="career-panel learning-ai-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">AI LEARNING ASSISTANT</p><h2>Ask about a concept or next step</h2></div><MessageCircle size={20} /></div>
            <p className="career-disclaimer">Personalized AI requests require AI profile sharing enabled in Career Coach. Conversation history is encrypted at rest.</p>
            <div className="learning-chat-history">
              {messages.map((message, index) => <article className={`learning-chat-message ${message.role === 'user' ? 'is-user' : ''}`} key={`${message.created_at || 'message'}-${index}`}>
                <small>{message.role === 'user' ? 'You' : 'Learning Assistant'}</small><p>{message.content}</p>
              </article>)}
            </div>
            <form className="learning-chat-form" onSubmit={(event) => void askLearningAssistant(event)}>
              <label className="learning-sr-only" htmlFor="learning-assistant-question">Ask the learning assistant</label>
              <textarea id="learning-assistant-question" required minLength={2} maxLength={4000} rows={3} value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} placeholder="What would you like to understand or practice?" />
              <button type="submit" className="btn btn-primary" disabled={busy}><Send size={15} /> Ask</button>
            </form>
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">PRACTICAL PROJECTS</p><h2>Get feedback on a project</h2></div><Code2 size={20} /></div>
            <p className="career-disclaimer">AI feedback and the completeness rubric are based on your description only. The Academy does not fetch or run project URLs or verify code, deployment, results, or authorship.</p>
            <form className="learning-form" onSubmit={(event) => void evaluateProject(event)}>
              <label>Project title<input required minLength={2} maxLength={160} value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} /></label>
              <label>Project description<textarea required minLength={40} maxLength={12000} rows={5} value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} placeholder="Describe the problem, users, your contribution, implementation, testing, and observed outcomes." /></label>
              <label>Skills demonstrated<input value={projectSkills} onChange={(event) => setProjectSkills(event.target.value)} placeholder="Comma-separated; self-reported" /></label>
              <label>Portfolio or project link (optional)<input type="url" value={projectUrl} onChange={(event) => setProjectUrl(event.target.value)} /></label>
              <button type="submit" className="btn btn-primary" disabled={busy}><Sparkles size={15} /> Evaluate project description</button>
            </form>
            {projectReview && <div className="learning-assessment-result">
              <strong>Evidence completeness: {String(projectReview.rubric_score)} / {String(projectReview.maximum_score)}</strong>
              {records(projectReview.criteria).map((criterion) => <p key={String(criterion.criterion)}>{String(criterion.criterion)}: {String(criterion.score)}/{String(criterion.maximum)} · {String(criterion.feedback)}</p>)}
              <p>{String(projectReview.ai_feedback)}</p><small>{String(projectReview.evaluation_scope)}</small>
            </div>}
            {dashboard.projects.map((project) => <details className="learning-saved-project" key={String(project.id)}>
              <summary>{String(project.title)} · updated {formatDate(project.updated_at)}</summary>
              <p>{String(project.description)}</p><p>{String(record(project.evaluation).ai_feedback)}</p>
            </details>)}
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">SKILL EVIDENCE</p><h2>Record your work and assessments</h2></div><Upload size={19} /></div>
            <p className="career-disclaimer">External evidence is self-submitted and is not independently verified. Passing Academy exercises and quizzes are labeled as platform assessment evidence, not professional or accredited certification.</p>
            <form className="learning-form" onSubmit={(event) => void submitEvidence(event)}>
              <label>Skill<input required minLength={1} maxLength={100} value={evidenceSkill} onChange={(event) => setEvidenceSkill(event.target.value)} /></label>
              <label>Evidence type<select value={evidenceType} onChange={(event) => setEvidenceType(event.target.value)}><option value="portfolio">Portfolio item</option><option value="project">Project</option><option value="external_certificate">External certificate record</option></select></label>
              <label>Evidence summary<textarea required minLength={20} maxLength={2000} rows={3} value={evidenceDescription} onChange={(event) => setEvidenceDescription(event.target.value)} /></label>
              {evidenceType !== 'external_certificate' && <label>Public evidence URL<input type="url" required value={evidenceUrl} onChange={(event) => setEvidenceUrl(event.target.value)} /></label>}
              <button type="submit" className="btn btn-secondary" disabled={busy}>Record user-submitted evidence</button>
            </form>
            {dashboard.evidence.map((item) => <div className="learning-evidence-row" key={String(item.id)}>
              <strong>{String(item.skill)} · {String(item.evidence_type).replace(/_/g, ' ')}</strong>
              <span>{String(item.verification_status).replace(/_/g, ' ')} · {formatDate(item.created_at)}</span>
              {Boolean(item.evidence_url) && <a href={String(item.evidence_url)} target="_blank" rel="noreferrer">Open evidence <ExternalLink size={13} /></a>}
              <small>{String(item.evidence_description)}</small>
            </div>)}
          </section>

          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">PLATFORM COMPLETION CERTIFICATES</p><h2>Certificates you've earned</h2></div><Award size={20} /></div>
            <p className="learning-muted">{dashboard.certificate_notice}</p>
            {dashboard.certificates.map((certificate) => <article className="learning-certificate" key={String(certificate.id)}>
              <div><strong>{display(dashboard.tracks.find((item) => item.id === certificate.track_id)?.title, String(certificate.track_id))}</strong><span>{String(certificate.serial_number)} · score {String(certificate.score)}% · issued {formatDate(certificate.issued_at)}</span></div>
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void fetchCertificate(String(certificate.serial_number))}>Download PDF</button>
            </article>)}
            {!dashboard.certificates.length && <p>No platform certificates earned yet. Complete a track's lessons, coding practice, and passing assessment to become eligible.</p>}
          </section>
        </>
      )}
    </div>
  );
};
