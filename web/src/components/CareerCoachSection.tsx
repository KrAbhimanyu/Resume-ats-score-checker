import React, { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight, Check, Compass, MessageCircle, RefreshCw, Save, ShieldCheck, Target, TrendingUp,
} from 'lucide-react';
import { careerRequest } from '../services/careerApi';
import '../styles/career-coach.css';

interface CareerGoal {
  id: string;
  title: string;
  description: string;
  target_role: string;
  goal_type: 'short_term' | 'long_term';
  target_date?: string | null;
  status: 'active' | 'completed' | 'paused' | 'archived';
  progress: number;
}

interface CareerAction {
  title: string;
  detail: string;
  timeframe: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
}

interface CareerPath {
  title: string;
  rationale: string;
  transition_steps: string[];
}

interface CareerMilestone {
  id: string;
  title: string;
  description: string;
  status: 'planned' | 'in_progress' | 'completed';
  due_date?: string | null;
}

interface RoadmapContent {
  summary: string;
  career_paths: CareerPath[];
  next_roles: string[];
  growth_insights: string[];
  strengths: string[];
  development_areas: string[];
  action_plan: CareerAction[];
  daily_tasks: string[];
  milestones: Array<{ title: string; description: string; weeks_from_now: number }>;
}

interface CareerRoadmap {
  id: string;
  goal_id?: string | null;
  content: RoadmapContent;
  readiness: {
    score: number | null;
    detail: Record<string, unknown>;
  };
  readiness_method: string;
  market_sample?: {
    source: string;
    observation_window_days: number;
    sample_size: number;
    target_role_mentions: number;
    profile_skills_in_sample: Array<{ skill: string; listing_count: number }>;
    limitation: string;
  } | null;
  milestones: CareerMilestone[];
  created_at: string;
  updated_at: string;
}

interface CoachMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface ResumeOption {
  id: string;
  title: string;
  is_primary: boolean;
}

interface CoachState {
  ai_data_consent: boolean;
  goals: CareerGoal[];
  roadmaps: CareerRoadmap[];
  messages: CoachMessage[];
}

const EMPTY_CONTENT: RoadmapContent = {
  summary: '',
  career_paths: [],
  next_roles: [],
  growth_insights: [],
  strengths: [],
  development_areas: [],
  action_plan: [],
  daily_tasks: [],
  milestones: [],
};

const formatDate = (value?: string | null): string => {
  if (!value) return 'No target date';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
};

export const CareerCoachSection: React.FC<{ token: string }> = ({ token }) => {
  const [coachState, setCoachState] = useState<CoachState>({
    ai_data_consent: false, goals: [], roadmaps: [], messages: [],
  });
  const [resumes, setResumes] = useState<ResumeOption[]>([]);
  const [preferences, setPreferences] = useState<Record<string, unknown>>({});
  const [selectedResume, setSelectedResume] = useState('');
  const [selectedGoalId, setSelectedGoalId] = useState('');
  const [selectedRoadmapId, setSelectedRoadmapId] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [currentRole, setCurrentRole] = useState('');
  const [industry, setIndustry] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('');
  const [interests, setInterests] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [customization, setCustomization] = useState('');
  const [goalTitle, setGoalTitle] = useState('');
  const [goalRole, setGoalRole] = useState('');
  const [goalType, setGoalType] = useState<'short_term' | 'long_term'>('short_term');
  const [goalDate, setGoalDate] = useState('');
  const [goalDescription, setGoalDescription] = useState('');
  const [editingGoal, setEditingGoal] = useState('');
  const [goalEditTitle, setGoalEditTitle] = useState('');
  const [goalEditRole, setGoalEditRole] = useState('');
  const [goalProgress, setGoalProgress] = useState<Record<string, number>>({});
  const [milestoneEdits, setMilestoneEdits] = useState<Record<string, { title: string; description: string; due_date: string }>>({});
  const [roadmapEdits, setRoadmapEdits] = useState<RoadmapContent | null>(null);
  const [newMilestoneTitle, setNewMilestoneTitle] = useState('');
  const [newMilestoneDate, setNewMilestoneDate] = useState('');
  const [chatText, setChatText] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadState = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [nextState, resumeList, preferencesResponse] = await Promise.all([
        careerRequest<CoachState>(token, '/coach/state'),
        careerRequest<ResumeOption[]>(token, '/profile/resumes'),
        careerRequest<{ preferences?: Record<string, unknown> }>(token, '/profile/preferences'),
      ]);
      setCoachState(nextState);
      setResumes(resumeList);
      const nextPreferences = preferencesResponse.preferences || {};
      setPreferences(nextPreferences);
      setSelectedResume((current) =>
        current || resumeList.find((resume) => resume.is_primary)?.id || resumeList[0]?.id || '',
      );
      setTargetRole((current) =>
        current || (nextPreferences.preferred_titles as string[] | undefined)?.[0] || '',
      );
      setSelectedRoadmapId((current) =>
        current || nextState.roadmaps[0]?.id || '',
      );
      setGoalProgress(Object.fromEntries(nextState.goals.map((goal) => [goal.id, goal.progress])));
      setMilestoneEdits(Object.fromEntries(nextState.roadmaps.flatMap((roadmap) =>
        roadmap.milestones.map((milestone) => [milestone.id, {
          title: milestone.title,
          description: milestone.description,
          due_date: milestone.due_date?.slice(0, 10) || '',
        }] as const),
      )));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load career coach data.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  const selectedRoadmap = useMemo(
    () => coachState.roadmaps.find((item) => item.id === selectedRoadmapId),
    [coachState.roadmaps, selectedRoadmapId],
  );
  const content = roadmapEdits || selectedRoadmap?.content || EMPTY_CONTENT;

  const run = async <T,>(action: () => Promise<T>, success?: string): Promise<T | undefined> => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await action();
      if (success) setNotice(success);
      return result;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The career coach request failed.');
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  const setAIConsent = async (enabled: boolean) => {
    const result = await run(
      () => careerRequest<{ ai_data_consent: boolean }>(
        token, '/coach/consent', { method: 'PUT', body: { enabled } },
      ),
      enabled ? 'AI profile sharing enabled.' : 'AI profile sharing disabled.',
    );
    if (result) setCoachState((current) => ({ ...current, ai_data_consent: result.ai_data_consent }));
  };

  const createGoal = async (event: FormEvent) => {
    event.preventDefault();
    const goal = await run(
      () => careerRequest<CareerGoal>(token, '/coach/goals', {
        method: 'POST',
        body: {
          title: goalTitle,
          description: goalDescription,
          target_role: goalRole,
          goal_type: goalType,
          target_date: goalDate || null,
        },
      }),
      'Career goal saved.',
    );
    if (goal) {
      setGoalTitle('');
      setGoalDescription('');
      setGoalRole('');
      setGoalDate('');
      await loadState();
    }
  };

  const updateGoal = async (goal: CareerGoal, changes: Record<string, unknown>, message: string) => {
    const updated = await run(
      () => careerRequest<CareerGoal>(
        token, `/coach/goals/${encodeURIComponent(goal.id)}`, { method: 'PATCH', body: changes },
      ),
      message,
    );
    if (updated) {
      await loadState();
      return true;
    }
    return false;
  };

  const generateRoadmap = async (event: FormEvent) => {
    event.preventDefault();
    const roadmap = await run(
      () => careerRequest<CareerRoadmap>(token, '/coach/roadmaps/generate', {
        method: 'POST',
        body: {
          resume_id: selectedResume || undefined,
          goal_id: selectedGoalId || undefined,
          target_role: targetRole,
          current_role: currentRole,
          industry,
          experience_level: experienceLevel,
          interests: interests.split(',').map((item) => item.trim()).filter(Boolean),
          job_description: jobDescription,
          customization,
        },
      }),
      'A new roadmap was generated and saved to your career history.',
    );
    if (roadmap) {
      setSelectedRoadmapId(roadmap.id);
      setRoadmapEdits(null);
      await loadState();
      setSelectedRoadmapId(roadmap.id);
    }
  };

  const saveRoadmap = async () => {
    if (!selectedRoadmap || !roadmapEdits) return;
    const saved = await run(
      () => careerRequest<CareerRoadmap>(
        token,
        `/coach/roadmaps/${encodeURIComponent(selectedRoadmap.id)}`,
        { method: 'PUT', body: roadmapEdits },
      ),
      'Your roadmap edits were saved.',
    );
    if (saved) {
      setRoadmapEdits(null);
      await loadState();
    }
  };

  const updateMilestone = async (milestone: CareerMilestone, status: CareerMilestone['status']) => {
    const updated = await run(
      () => careerRequest<CareerMilestone>(
        token, `/coach/milestones/${encodeURIComponent(milestone.id)}`,
        { method: 'PATCH', body: { status } },
      ),
      'Milestone progress updated.',
    );
    if (updated) await loadState();
  };

  const saveMilestone = async (milestone: CareerMilestone) => {
    const changes = milestoneEdits[milestone.id];
    if (!changes) return;
    const updated = await run(
      () => careerRequest<CareerMilestone>(
        token, `/coach/milestones/${encodeURIComponent(milestone.id)}`,
        { method: 'PATCH', body: { ...changes, due_date: changes.due_date || null } },
      ),
      'Milestone details saved.',
    );
    if (updated) await loadState();
  };

  const addMilestone = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedRoadmap) return;
    const result = await run(
      () => careerRequest<CareerMilestone>(
        token,
        `/coach/roadmaps/${encodeURIComponent(selectedRoadmap.id)}/milestones`,
        {
          method: 'POST',
          body: { title: newMilestoneTitle, due_date: newMilestoneDate || null },
        },
      ),
      'Milestone added to your roadmap.',
    );
    if (result) {
      setNewMilestoneTitle('');
      setNewMilestoneDate('');
      await loadState();
    }
  };

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const message = chatText.trim();
    if (!message) return;
    const result = await run(
      () => careerRequest<{ response: string }>(token, '/coach/chat', {
        method: 'POST',
        body: { message, roadmap_id: selectedRoadmapId || undefined },
      }),
    );
    if (result) {
      setChatText('');
      await loadState();
    }
  };

  const updateAction = (index: number, patch: Partial<CareerAction>) => {
    const current = roadmapEdits || selectedRoadmap?.content || EMPTY_CONTENT;
    const actions = [...current.action_plan];
    actions[index] = { ...actions[index], ...patch };
    setRoadmapEdits({ ...current, action_plan: actions });
  };

  if (loading) return <div className="career-loading" role="status">Loading your private career-coaching workspace…</div>;

  return (
    <div className="coach-workspace">
      {error && <div className="career-alert career-alert-error" role="alert">{error}</div>}
      {notice && <div className="career-alert career-alert-success" role="status">{notice}</div>}
      {busy && <div className="career-action-progress" role="status">Working on your career plan…</div>}

      <section className="career-panel coach-consent-panel">
        <div className="career-panel-heading">
          <div><p className="career-eyebrow">PRIVATE BY DEFAULT</p><h2>AI data-sharing control</h2></div>
          <ShieldCheck size={22} />
        </div>
        <label className="career-checkbox">
          <input
            type="checkbox"
            checked={coachState.ai_data_consent}
            disabled={busy}
            onChange={(event) => void setAIConsent(event.target.checked)}
          />
          Allow personalized career profile context to be sent to the configured AI provider when I request coaching
        </label>
        <p className="career-disclaimer">
          Your profile and resume remain account-scoped and encrypted in this app. When enabled, a resume excerpt,
          stated goals, skill progress, relevant application history, and your request may be sent to the backend-configured
          AI provider for the requested response. Revoke consent here at any time. AI responses are suggestions, not guarantees.
        </p>
      </section>

      <div className="coach-layout">
        <div className="coach-primary-column">
          <section className="career-panel">
            <div className="career-panel-heading">
              <div><p className="career-eyebrow">PERSONALIZED ROADMAP</p><h2>Plan your next career move</h2></div>
              <Compass size={22} />
            </div>
            <form className="career-form" onSubmit={generateRoadmap}>
              <div className="career-two-columns">
                <label>Target position<input required minLength={2} maxLength={160} value={targetRole} onChange={(event) => setTargetRole(event.target.value)} placeholder="e.g. Senior Data Analyst" /></label>
                <label>Current position<input maxLength={160} value={currentRole} onChange={(event) => setCurrentRole(event.target.value)} placeholder="Your current or most recent role" /></label>
                <label>Target industry<input maxLength={120} value={industry} onChange={(event) => setIndustry(event.target.value)} placeholder="e.g. healthcare, fintech" /></label>
                <label>Experience level<input maxLength={80} value={experienceLevel} onChange={(event) => setExperienceLevel(event.target.value)} placeholder="e.g. 3 years, mid-career" /></label>
                <label>Resume profile<select value={selectedResume} onChange={(event) => setSelectedResume(event.target.value)}><option value="">No resume selected</option>{resumes.map((resume) => <option value={resume.id} key={resume.id}>{resume.title}{resume.is_primary ? ' · primary' : ''}</option>)}</select></label>
                <label>Connect a career goal<select value={selectedGoalId} onChange={(event) => setSelectedGoalId(event.target.value)}><option value="">No saved goal</option>{coachState.goals.filter((goal) => goal.status !== 'archived').map((goal) => <option value={goal.id} key={goal.id}>{goal.title}</option>)}</select></label>
              </div>
              <label>Interests and preferred work (comma-separated)<input value={interests} onChange={(event) => setInterests(event.target.value)} placeholder="e.g. mentoring, distributed systems, healthcare" /></label>
              <label>Target job requirements (optional)<textarea rows={5} value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste requirements from a role you are targeting to ground readiness and gap analysis." /></label>
              <label>Customize this roadmap<input maxLength={2000} value={customization} onChange={(event) => setCustomization(event.target.value)} placeholder="Prioritize a domain transition, schedule, or skill area" /></label>
              <button className="btn btn-primary" type="submit" disabled={busy || !coachState.ai_data_consent}>
                <RefreshCw size={15} /> {selectedRoadmap ? 'Generate another version' : 'Generate personalized roadmap'}
              </button>
              {!coachState.ai_data_consent && <p className="career-disclaimer">Enable AI profile sharing above to generate a personalized roadmap.</p>}
            </form>
          </section>

          <section className="career-panel">
            <div className="career-panel-heading">
              <div><p className="career-eyebrow">GOAL SETTING</p><h2>Career goals and progress</h2></div>
              <Target size={22} />
            </div>
            <form className="career-form" onSubmit={createGoal}>
              <div className="career-two-columns">
                <label>Goal name<input required minLength={2} maxLength={160} value={goalTitle} onChange={(event) => setGoalTitle(event.target.value)} placeholder="e.g. Move into people leadership" /></label>
                <label>Target role<input required minLength={2} maxLength={160} value={goalRole} onChange={(event) => setGoalRole(event.target.value)} placeholder="Role or career outcome" /></label>
                <label>Goal horizon<select value={goalType} onChange={(event) => setGoalType(event.target.value as 'short_term' | 'long_term')}><option value="short_term">Short-term</option><option value="long_term">Long-term</option></select></label>
                <label>Target date<input type="date" value={goalDate} onChange={(event) => setGoalDate(event.target.value)} /></label>
              </div>
              <label>Goal details<textarea rows={2} maxLength={2000} value={goalDescription} onChange={(event) => setGoalDescription(event.target.value)} placeholder="What would achieving this career goal mean to you?" /></label>
              <button className="btn btn-secondary" type="submit" disabled={busy}>Save career goal</button>
            </form>
            {coachState.goals.length === 0 ? (
              <p className="career-muted">Add a goal to track progress and connect it to future roadmaps.</p>
            ) : (
              <div className="coach-goal-list">
                {coachState.goals.map((goal) => (
                  <article className="coach-goal-card" key={goal.id}>
                    <div className="coach-goal-heading">
                      <div><strong>{goal.title}</strong><span>{goal.goal_type === 'short_term' ? 'Short-term' : 'Long-term'} · {goal.target_role}</span><small>{formatDate(goal.target_date)}</small></div>
                      <select aria-label={`Status for ${goal.title}`} value={goal.status} onChange={(event) => void updateGoal(goal, { status: event.target.value }, 'Goal status updated.')}>
                        <option value="active">Active</option><option value="paused">Paused</option><option value="completed">Completed</option><option value="archived">Archived</option>
                      </select>
                    </div>
                    {editingGoal === goal.id ? (
                      <div className="coach-goal-editor">
                        <input aria-label="Edit goal title" value={goalEditTitle} onChange={(event) => setGoalEditTitle(event.target.value)} />
                        <input aria-label="Edit target role" value={goalEditRole} onChange={(event) => setGoalEditRole(event.target.value)} />
                        <button className="btn btn-secondary" type="button" disabled={busy} onClick={async () => {
                          if (await updateGoal(goal, { title: goalEditTitle, target_role: goalEditRole }, 'Career goal updated.')) setEditingGoal('');
                        }}>Save goal details</button>
                      </div>
                    ) : (
                      <button className="career-link-button" type="button" onClick={() => { setGoalEditTitle(goal.title); setGoalEditRole(goal.target_role); setEditingGoal(goal.id); }}>Edit goal details</button>
                    )}
                    <div className="coach-progress-row">
                      <label htmlFor={`goal-progress-${goal.id}`}>Progress · {goalProgress[goal.id] ?? goal.progress}%</label>
                      <input id={`goal-progress-${goal.id}`} type="range" min="0" max="100" step="5" value={goalProgress[goal.id] ?? goal.progress} onChange={(event) => setGoalProgress((current) => ({ ...current, [goal.id]: Number(event.target.value) }))} />
                      <button type="button" className="career-link-button" disabled={busy} onClick={() => void updateGoal(goal, { progress: goalProgress[goal.id] ?? goal.progress }, 'Goal progress saved.')}>Save progress</button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="coach-secondary-column">
          <section className="career-panel">
            <div className="career-panel-heading"><div><p className="career-eyebrow">CAREER HISTORY</p><h2>Saved roadmap versions</h2></div></div>
            {coachState.roadmaps.length === 0 ? (
              <p className="career-muted">Generated plans are saved here so you can compare and revisit previous versions.</p>
            ) : (
              <label className="coach-roadmap-select">Choose a saved roadmap
                <select value={selectedRoadmapId} onChange={(event) => { setSelectedRoadmapId(event.target.value); setRoadmapEdits(null); }}>
                  {coachState.roadmaps.map((roadmap) => <option key={roadmap.id} value={roadmap.id}>{roadmap.content.summary.slice(0, 72)} · {formatDate(roadmap.created_at)}</option>)}
                </select>
              </label>
            )}
          </section>

          {selectedRoadmap && (
            <>
              <section className="career-panel coach-readiness-card">
                <div className="career-panel-heading"><div><p className="career-eyebrow">CAREER READINESS</p><h2>{selectedRoadmap.readiness.score === null ? 'Needs a saved resume' : `${selectedRoadmap.readiness.score}%`}</h2></div><TrendingUp size={22} /></div>
                <p>{String(selectedRoadmap.readiness.detail.message || 'Readiness is not available for this profile.')}</p>
                {selectedRoadmap.readiness_method.startsWith('deterministic_job_match') && <ul>{((selectedRoadmap.readiness.detail.missing_required_skills as string[]) || []).slice(0, 5).map((skill) => <li key={skill}>Gap to explore: {skill}</li>)}{((selectedRoadmap.readiness.detail.qualification_gaps as string[]) || []).map((gap) => <li key={gap}>Qualification to verify: {gap}</li>)}</ul>}
              </section>

              <section className="career-panel">
                <div className="career-panel-heading"><div><p className="career-eyebrow">YOUR PLAN</p><h2>Roadmap overview</h2></div></div>
                <label className="coach-editor-label">Edit the roadmap summary<textarea rows={4} value={content.summary} onChange={(event) => setRoadmapEdits({ ...content, summary: event.target.value })} /></label>
                {content.career_paths.length > 0 && <div className="coach-content-group"><h3>Recommended paths and transitions</h3>{content.career_paths.map((path) => <article className="coach-path-card" key={path.title}><strong>{path.title}</strong><p>{path.rationale}</p>{path.transition_steps.length > 0 && <ol>{path.transition_steps.map((step) => <li key={step}>{step}</li>)}</ol>}</article>)}</div>}
                {content.next_roles.length > 0 && <div className="coach-content-group"><h3>Possible next roles</h3><div className="coach-chip-list">{content.next_roles.map((role) => <span key={role}>{role}</span>)}</div></div>}
                {selectedRoadmap.market_sample && <div className="coach-market-sample"><strong>Recent listing sample</strong><p>{selectedRoadmap.market_sample.sample_size} authorized listings observed in {selectedRoadmap.market_sample.observation_window_days} days; {selectedRoadmap.market_sample.target_role_mentions} mentioned the target role.</p>{selectedRoadmap.market_sample.profile_skills_in_sample.map((item) => <span key={item.skill}>{item.skill}: {item.listing_count}</span>)}<small>{selectedRoadmap.market_sample.limitation}</small></div>}
                {content.growth_insights.length > 0 && <div className="coach-content-group"><h3>Growth outlook</h3><ul>{content.growth_insights.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul><p className="career-disclaimer">Market insights use a limited sample of configured job listings; career outcomes are uncertain and are not guaranteed.</p></div>}
                {content.strengths.length > 0 && <div className="coach-content-group"><h3>Evidence-based strengths</h3><ul>{content.strengths.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div>}
                {content.development_areas.length > 0 && <div className="coach-content-group"><h3>Gaps and development areas</h3><ul>{content.development_areas.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div>}
                {content.action_plan.length > 0 && (
                  <div className="coach-content-group">
                    <h3>Action plan · edit before saving</h3>
                    {content.action_plan.map((action, index) => (
                      <div className="coach-action-editor" key={`${index}-${action.title}`}>
                        <label>Action<input value={action.title} onChange={(event) => updateAction(index, { title: event.target.value })} /></label>
                        <label>Details<textarea rows={2} value={action.detail} onChange={(event) => updateAction(index, { detail: event.target.value })} /></label>
                        <small>{action.timeframe} · {action.category} · {action.priority} priority</small>
                      </div>
                    ))}
                  </div>
                )}
                {content.daily_tasks.length > 0 && <div className="coach-content-group"><h3>Daily improvement tasks</h3><ul className="coach-daily-list">{content.daily_tasks.map((task, index) => <li key={`${index}-${task}`}><Check size={15} />{task}</li>)}</ul></div>}
                {roadmapEdits && <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => void saveRoadmap()}><Save size={15} /> Save roadmap edits</button>}
              </section>

              <section className="career-panel">
                <div className="career-panel-heading"><div><p className="career-eyebrow">MILESTONES</p><h2>Track roadmap progress</h2></div></div>
                {selectedRoadmap.milestones.map((milestone) => (
                  <article className="coach-milestone" key={milestone.id}>
                    <div className="coach-milestone-fields">
                      <label>Milestone<input value={milestoneEdits[milestone.id]?.title || ''} onChange={(event) => setMilestoneEdits((current) => ({ ...current, [milestone.id]: { ...current[milestone.id], title: event.target.value } }))} /></label>
                      <label>Details<textarea rows={2} value={milestoneEdits[milestone.id]?.description || ''} onChange={(event) => setMilestoneEdits((current) => ({ ...current, [milestone.id]: { ...current[milestone.id], description: event.target.value } }))} /></label>
                      <label>Target date<input type="date" value={milestoneEdits[milestone.id]?.due_date || ''} onChange={(event) => setMilestoneEdits((current) => ({ ...current, [milestone.id]: { ...current[milestone.id], due_date: event.target.value } }))} /></label>
                      <button type="button" className="career-link-button" disabled={busy} onClick={() => void saveMilestone(milestone)}>Save milestone</button>
                    </div>
                    <select aria-label={`Progress for ${milestone.title}`} value={milestone.status} disabled={busy} onChange={(event) => void updateMilestone(milestone, event.target.value as CareerMilestone['status'])}>
                      <option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option>
                    </select>
                  </article>
                ))}
                <form className="coach-add-milestone" onSubmit={addMilestone}>
                  <label>Add a milestone<input required minLength={2} maxLength={180} value={newMilestoneTitle} onChange={(event) => setNewMilestoneTitle(event.target.value)} /></label>
                  <label>Target date<input type="date" value={newMilestoneDate} onChange={(event) => setNewMilestoneDate(event.target.value)} /></label>
                  <button className="btn btn-secondary" type="submit" disabled={busy}>Add milestone</button>
                </form>
              </section>
            </>
          )}
        </aside>
      </div>

      <section className="career-panel coach-chat-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">AI CAREER CHAT</p><h2>Ask for guidance or compare your options</h2></div><MessageCircle size={22} /></div>
        <p className="career-disclaimer">The assistant can help structure a decision by comparing fit, trade-offs, unknowns, and a reversible next step. It uses only your authorized profile, saved career history, and this conversation.</p>
        <div className="coach-chat-history" aria-live="polite">
          {coachState.messages.length === 0 ? <p className="career-muted">Your private coaching conversation will appear here.</p> : coachState.messages.map((message) => (
            <article className={`coach-message coach-message-${message.role}`} key={message.id}><strong>{message.role === 'assistant' ? 'Career Coach' : 'You'}</strong><p>{message.content}</p><small>{formatDate(message.created_at)}</small></article>
          ))}
        </div>
        <form className="coach-chat-form" onSubmit={sendMessage}>
          <label htmlFor="coach-chat-input">Your question</label>
          <textarea id="coach-chat-input" rows={3} maxLength={5000} required value={chatText} onChange={(event) => setChatText(event.target.value)} placeholder="Ask about a role transition, skill gap, career choice, or your next practical step." />
          <button className="btn btn-primary" type="submit" disabled={busy || !coachState.ai_data_consent}><span>Ask Career Coach</span><ArrowRight size={16} /></button>
        </form>
      </section>
      {Boolean(preferences.career_goals) && <p className="career-disclaimer">Your saved profile goal was included as context: {String(preferences.career_goals)}</p>}
    </div>
  );
};
