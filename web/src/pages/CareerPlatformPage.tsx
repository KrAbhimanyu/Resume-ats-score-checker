import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity, ArrowRight, Bell, BriefcaseBusiness, Building2, CalendarDays, Check,
  CircleDollarSign, ClipboardList, Compass, FileSearch, FileText, GraduationCap, LogOut,
  MapPin, Search, Share2, ShieldCheck, Sparkles, Target, TrendingUp, UserRound, Wallet, X,
} from 'lucide-react';
import { careerRequest, exportCareerResume } from '../services/careerApi';
import { CareerCoachSection } from '../components/CareerCoachSection';
import { CompanyIntelligenceSection } from '../components/CompanyIntelligenceSection';
import { LearningAcademySection } from '../components/LearningAcademySection';
import { PersonalBrandingSection } from '../components/PersonalBrandingSection';
import { SalaryIntelligenceSection } from '../components/SalaryIntelligenceSection';
import { BusinessRevenueSection } from '../components/BusinessRevenueSection';

type Section =
  | 'overview' | 'discover' | 'analyzer' | 'saved' | 'tracker' | 'coach' | 'academy' | 'branding'
  | 'interviews' | 'reminders' | 'research' | 'salary' | 'analytics' | 'profile' | 'business';
type ApiRecord = Record<string, unknown>;

interface CareerJob {
  id: string;
  title: string;
  company_name: string;
  location?: string | null;
  country?: string | null;
  remote_type?: string | null;
  employment_type?: string | null;
  experience_level?: string | null;
  original_url?: string | null;
  expires_at?: string | null;
  description?: string;
  source_label?: string;
  source?: string;
  posted_at?: string | null;
  availability?: string;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  saved_at?: string;
  recommendation_score?: number;
  recommendation_reason?: string;
  missing_skills?: string[];
}

interface CareerApplication {
  id: string;
  title: string;
  company_name: string;
  location?: string | null;
  description?: string;
  original_url?: string | null;
  status: string;
  notes?: string;
  resume_version_id?: string | null;
  applied_at?: string | null;
}

interface ApplicationEvent {
  id: string;
  from_status?: string | null;
  to_status: string;
  note?: string;
  created_at: string;
}

interface CareerInterview {
  id: string;
  application_id: string;
  scheduled_at: string;
  timezone: string;
  interview_type: string;
  meeting_url?: string | null;
  interviewer_details?: string;
  preparation_notes?: string;
  status: string;
  title: string;
  company_name: string;
}

interface CareerReminder {
  id: string;
  message: string;
  reminder_type: string;
  due_at: string;
  status: string;
  email_status?: string;
}

interface ResumeProfile {
  id: string;
  title: string;
  skills?: string[];
  is_primary: boolean;
}

interface ProviderStatus {
  provider: string;
  enabled: boolean;
  reason?: string | null;
}

interface TailoringChange {
  id: string;
  section: string;
  original_text: string;
  proposed_text: string;
  rationale: string;
  what_to_verify: string;
  is_accepted: boolean;
}

interface TailoringReview extends ApiRecord {
  id: string;
  status: string;
  job_title: string;
  changes: TailoringChange[];
  draft_resume: ApiRecord;
  disclaimer: string;
  method: string;
}

const SESSION_TOKEN_KEY = 'career-platform-token';
const APPLICATION_STATUSES = ['saved', 'applied', 'shortlisted', 'assessment', 'interview', 'offer', 'rejected', 'withdrawn'];
const CAREER_SCORE_WEIGHT_FIELDS = [
  { key: 'resume_profile', label: 'Resume profile' },
  { key: 'career_direction', label: 'Career direction' },
  { key: 'skills', label: 'Skills tracked' },
  { key: 'opportunity_activity', label: 'Opportunity activity' },
  { key: 'learning_or_milestones', label: 'Learning or milestones' },
];
const NAV_ITEMS: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Activity size={17} /> },
  { id: 'discover', label: 'Discover jobs', icon: <Search size={17} /> },
  { id: 'analyzer', label: 'Job analyzer', icon: <FileSearch size={17} /> },
  { id: 'saved', label: 'Saved jobs', icon: <BriefcaseBusiness size={17} /> },
  { id: 'tracker', label: 'Applications', icon: <ClipboardList size={17} /> },
  { id: 'interviews', label: 'Interviews', icon: <CalendarDays size={17} /> },
  { id: 'reminders', label: 'Reminders', icon: <Bell size={17} /> },
  { id: 'research', label: 'Company & salary', icon: <Building2 size={17} /> },
  { id: 'salary', label: 'Salary intelligence', icon: <CircleDollarSign size={17} /> },
  { id: 'analytics', label: 'Analytics', icon: <TrendingUp size={17} /> },
  { id: 'coach', label: 'AI Career Coach', icon: <Compass size={17} /> },
  { id: 'academy', label: 'Skills Academy', icon: <GraduationCap size={17} /> },
  { id: 'branding', label: 'Personal Branding', icon: <Share2 size={17} /> },
  { id: 'business', label: 'Plans & billing', icon: <Wallet size={17} /> },
  { id: 'profile', label: 'Resume & preferences', icon: <UserRound size={17} /> },
];

const display = (value: unknown, fallback = 'Not provided'): string =>
  typeof value === 'string' && value.trim() ? value : fallback;

const record = (value: unknown): ApiRecord =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as ApiRecord : {};

const records = (value: unknown): ApiRecord[] =>
  Array.isArray(value) ? value.map((item) => record(item)) : [];

const toCareerJob = (
  value: unknown,
  recommendationScore?: number,
  recommendationMatch?: unknown,
): CareerJob | null => {
  const item = record(value);
  const match = record(recommendationMatch);
  if (typeof item.id !== 'string' || typeof item.title !== 'string' || typeof item.company_name !== 'string') {
    return null;
  }
  return {
    id: item.id,
    title: item.title,
    company_name: item.company_name,
    location: typeof item.location === 'string' ? item.location : null,
    country: typeof item.country === 'string' ? item.country : null,
    remote_type: typeof item.remote_type === 'string' ? item.remote_type : null,
    employment_type: typeof item.employment_type === 'string' ? item.employment_type : null,
    experience_level: typeof item.experience_level === 'string' ? item.experience_level : null,
    original_url: typeof item.original_url === 'string' ? item.original_url : null,
    expires_at: typeof item.expires_at === 'string' ? item.expires_at : null,
    description: typeof item.description === 'string' ? item.description : undefined,
    source_label: typeof item.source_label === 'string' ? item.source_label : undefined,
    source: typeof item.source === 'string' ? item.source : undefined,
    posted_at: typeof item.posted_at === 'string' ? item.posted_at : null,
    availability: typeof item.availability === 'string' ? item.availability : undefined,
    salary_min: typeof item.salary_min === 'number' ? item.salary_min : null,
    salary_max: typeof item.salary_max === 'number' ? item.salary_max : null,
    salary_currency: typeof item.salary_currency === 'string' ? item.salary_currency : null,
    salary_period: typeof item.salary_period === 'string' ? item.salary_period : null,
    saved_at: typeof item.saved_at === 'string' ? item.saved_at : undefined,
    recommendation_score: recommendationScore,
    recommendation_reason: typeof match.reason === 'string' ? match.reason : undefined,
    missing_skills: Array.isArray(match.missing_required_skills)
      ? match.missing_required_skills.filter((skill): skill is string => typeof skill === 'string')
      : undefined,
  };
};

const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const parseList = (value: string): string[] =>
  value.split(',').map((item) => item.trim()).filter(Boolean);

function useCareerAction(setError: (value: string) => void, setNotice: (value: string) => void) {
  const [busy, setBusy] = useState(false);
  const run = useCallback(async <T,>(
    action: () => Promise<T>,
    successMessage?: string,
  ): Promise<T | undefined> => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await action();
      if (successMessage) setNotice(successMessage);
      return result;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'The career platform request failed.');
      return undefined;
    } finally {
      setBusy(false);
    }
  }, [setError, setNotice]);
  return { busy, run };
}

export const CareerPlatformPage: React.FC = () => {
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_TOKEN_KEY) || '');
  const [section, setSection] = useState<Section>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.has('business_checkout_session') || params.has('business_checkout_cancelled')
      ? 'business'
      : 'overview';
  });
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [jobs, setJobs] = useState<CareerJob[]>([]);
  const [applications, setApplications] = useState<CareerApplication[]>([]);
  const [applicationPriorities, setApplicationPriorities] = useState<ApiRecord[]>([]);
  const [interviews, setInterviews] = useState<CareerInterview[]>([]);
  const [reminders, setReminders] = useState<CareerReminder[]>([]);
  const [resumes, setResumes] = useState<ResumeProfile[]>([]);
  const [savedJobs, setSavedJobs] = useState<CareerJob[]>([]);
  const [analytics, setAnalytics] = useState<ApiRecord>({});
  const [commandCenter, setCommandCenter] = useState<ApiRecord>({});
  const [notificationPreferences, setNotificationPreferences] = useState<ApiRecord>({});
  const [careerScoreWeights, setCareerScoreWeights] = useState<ApiRecord>({
    resume_profile: 20,
    career_direction: 20,
    skills: 20,
    opportunity_activity: 20,
    learning_or_milestones: 20,
  });
  const [preferences, setPreferences] = useState<ApiRecord>({});
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [country, setCountry] = useState('gb');
  const [companyFilter, setCompanyFilter] = useState('');
  const [remoteTypeFilter, setRemoteTypeFilter] = useState('');
  const [employmentTypeFilter, setEmploymentTypeFilter] = useState('');
  const [experienceLevelFilter, setExperienceLevelFilter] = useState('');
  const [salaryMinimumFilter, setSalaryMinimumFilter] = useState('');
  const [salaryMaximumFilter, setSalaryMaximumFilter] = useState('');
  const [salaryCurrencyFilter, setSalaryCurrencyFilter] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const [page, setPage] = useState(1);
  const [hasMoreJobs, setHasMoreJobs] = useState(false);
  const [recommendations, setRecommendations] = useState(false);
  const [aiRecommendationConsent, setAiRecommendationConsent] = useState(false);
  const [similarJobTitle, setSimilarJobTitle] = useState('');
  const [marketDemand, setMarketDemand] = useState<ApiRecord | null>(null);
  const [matchResult, setMatchResult] = useState<ApiRecord | null>(null);
  const [skillStatuses, setSkillStatuses] = useState<Record<string, string>>({});
  const [analyzerText, setAnalyzerText] = useState('');
  const [analyzerTitle, setAnalyzerTitle] = useState('');
  const [analyzerCompany, setAnalyzerCompany] = useState('');
  const [analyzerResult, setAnalyzerResult] = useState<ApiRecord | null>(null);
  const [savedAnalysisJob, setSavedAnalysisJob] = useState<CareerJob | null>(null);
  const [authorizedAnalyzedJob, setAuthorizedAnalyzedJob] = useState<CareerJob | null>(null);
  const [authorizedJobUrl, setAuthorizedJobUrl] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [resumeTitle, setResumeTitle] = useState('Primary resume');
  const [preferenceTitles, setPreferenceTitles] = useState('');
  const [preferenceLocations, setPreferenceLocations] = useState('');
  const [preferenceIndustries, setPreferenceIndustries] = useState('');
  const [preferenceGoals, setPreferenceGoals] = useState('');
  const [salaryRole, setSalaryRole] = useState('');
  const [salaryLocation, setSalaryLocation] = useState('');
  const [salaryData, setSalaryData] = useState<ApiRecord | null>(null);
  const [manualTitle, setManualTitle] = useState('');
  const [manualCompany, setManualCompany] = useState('');
  const [manualNotes, setManualNotes] = useState('');
  const [manualDescription, setManualDescription] = useState('');
  const [interviewApplication, setInterviewApplication] = useState('');
  const [interviewDate, setInterviewDate] = useState('');
  const [interviewType, setInterviewType] = useState('technical');
  const [interviewNotes, setInterviewNotes] = useState('');
  const [interviewReschedules, setInterviewReschedules] = useState<Record<string, string>>({});
  const [openHistoryId, setOpenHistoryId] = useState('');
  const [applicationHistory, setApplicationHistory] = useState<ApplicationEvent[]>([]);
  const [followUpDraft, setFollowUpDraft] = useState<ApiRecord | null>(null);
  const [applicationDraftType, setApplicationDraftType] = useState('cover_letter');
  const [draftApplication, setDraftApplication] = useState<CareerApplication | null>(null);
  const [draftId, setDraftId] = useState('');
  const [applicationDrafts, setApplicationDrafts] = useState<Record<string, ApiRecord[]>>({});
  const [applicationHistoryNotes, setApplicationHistoryNotes] = useState<Record<string, string>>({});
  const [applicationNoteDrafts, setApplicationNoteDrafts] = useState<Record<string, string>>({});
  const [reminderApplication, setReminderApplication] = useState('');
  const [reminderMessage, setReminderMessage] = useState('');
  const [reminderDate, setReminderDate] = useState('');
  const [tailoringReview, setTailoringReview] = useState<TailoringReview | null>(null);
  const [savedVersion, setSavedVersion] = useState<ApiRecord | null>(null);
  const [searchSummary, setSearchSummary] = useState<ApiRecord>({});

  const { busy, run } = useCareerAction(setError, setNotice);

  const loadSection = useCallback(async (target: Section = section) => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      if (target === 'overview' || target === 'analytics') {
        const [result, dashboard] = await Promise.all([
          careerRequest<ApiRecord>(token, '/analytics'),
          target === 'overview'
            ? careerRequest<ApiRecord>(token, '/command-center')
            : Promise.resolve(null),
        ]);
        setAnalytics(result);
        setSearchSummary(record(result.job_search));
        if (dashboard) {
          setCommandCenter(dashboard);
          setNotificationPreferences(record(dashboard.notification_preferences));
          setCareerScoreWeights(record(record(dashboard.career_score).weights));
        }
      }
      if (target === 'discover') {
        setProviders(await careerRequest<ProviderStatus[]>(token, '/providers'));
        setMarketDemand(await careerRequest<ApiRecord>(token, '/market/demand?days=30&limit=8'));
        const progress = await careerRequest<ApiRecord[]>(token, '/skills/progress');
        setSkillStatuses(Object.fromEntries(progress.map((item) => [String(item.skill), String(item.status)])));
      }
      if (target === 'saved') setSavedJobs(await careerRequest<CareerJob[]>(token, '/jobs/saved'));
      if (target === 'tracker' || target === 'interviews' || target === 'reminders') {
        const [result, resumeList] = await Promise.all([
          careerRequest<CareerApplication[]>(token, '/applications'),
          careerRequest<ResumeProfile[]>(token, '/profile/resumes'),
        ]);
        setApplications(result);
        setApplicationNoteDrafts(Object.fromEntries(
          result.map((application) => [application.id, application.notes || '']),
        ));
        setResumes(resumeList);
        if (target === 'tracker') {
          const priorities = await careerRequest<ApiRecord>(token, '/applications/priorities');
          setApplicationPriorities(records(priorities.items));
        }
        if (target === 'interviews') setInterviews(await careerRequest<CareerInterview[]>(token, '/interviews?upcoming_only=false'));
        if (target === 'reminders') {
          const remindersResult = await careerRequest<ApiRecord>(token, '/reminders');
          setReminders((remindersResult.reminders as CareerReminder[]) || []);
        }
      }
      if (target === 'profile') {
        const [profileList, prefs] = await Promise.all([
          careerRequest<ResumeProfile[]>(token, '/profile/resumes'),
          careerRequest<ApiRecord>(token, '/profile/preferences'),
        ]);
        setResumes(profileList);
        const nextPreferences = record(prefs.preferences);
        setPreferences(nextPreferences);
        setPreferenceTitles(((nextPreferences.preferred_titles as string[]) || []).join(', '));
        setPreferenceLocations(((nextPreferences.preferred_locations as string[]) || []).join(', '));
        setPreferenceIndustries(((nextPreferences.industries as string[]) || []).join(', '));
        setPreferenceGoals(display(nextPreferences.career_goals, ''));
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load this career workspace.');
    } finally {
      setLoading(false);
    }
  }, [token, section]);

  useEffect(() => {
    if (token) void loadSection(section);
  }, [token, section, loadSection]);

  useEffect(() => {
    if (!token) return;
    void careerRequest<{ email: string }>(token, '/auth/me')
      .then((user) => setUserEmail(user.email))
      .catch(() => {
        sessionStorage.removeItem(SESSION_TOKEN_KEY);
        setToken('');
        setError('Your sign-in session has expired. Please sign in again.');
      });
  }, [token]);

  const refresh = async (target: Section = section) => loadSection(target);

  const saveNotificationPreferences = async () => {
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/command-center/notification-preferences', {
        method: 'PUT',
        body: notificationPreferences,
      }),
      'Notification preferences saved.',
    );
    if (result) setNotificationPreferences(result);
  };

  const saveCareerScoreWeights = async () => {
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/command-center/career-score-weights', {
        method: 'PUT',
        body: careerScoreWeights,
      }),
      'Career score weights saved.',
    );
    if (result) {
      setCareerScoreWeights(record(result.weights));
      await refresh('overview');
    }
  };

  const markNotificationRead = async (notificationId: string) => {
    const result = await run(
      () => careerRequest(token, `/command-center/notifications/${encodeURIComponent(notificationId)}/read`, {
        method: 'PATCH',
      }),
    );
    if (result !== undefined) await refresh('overview');
  };

  const loadMoreCareerTimeline = async () => {
    const offset = records(commandCenter.timeline).length;
    const result = await run(
      () => careerRequest<ApiRecord>(
        token,
        `/command-center?timeline_offset=${offset}&timeline_limit=50`,
      ),
    );
    if (result) {
      setCommandCenter((current) => ({
        ...current,
        timeline: [...records(current.timeline), ...records(result.timeline)],
        timeline_has_more: result.timeline_has_more,
      }));
    }
  };

  useEffect(() => {
    if (!googleClientId || !googleButtonRef.current) return;

    const initializeGoogle = () => {
      const googleApi = (window as typeof window & {
        google?: {
          accounts?: {
            id?: {
              initialize: (config: { client_id: string; callback: (response: { credential?: string }) => void }) => void;
              prompt: (callback?: (notification: { isNotDisplayed?: () => boolean; isSkipped?: () => boolean }) => void) => void;
              renderButton: (element: HTMLElement, options: Record<string, string | boolean>) => void;
            };
          };
        };
      }).google;

      if (!googleApi?.accounts?.id) return;

      googleApi.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          if (!response.credential) {
            setError('Google sign-in did not return a credential. Please try again.');
            return;
          }

          const signedIn = await run(
            () => careerRequest<{ access_token: string; user: { email: string } }>(
              '', '/auth/google', { method: 'POST', body: { credential: response.credential } },
            ),
            'Signed in with Google.',
          );
          if (signedIn) {
            sessionStorage.setItem(SESSION_TOKEN_KEY, signedIn.access_token);
            setUserEmail(signedIn.user.email);
            setToken(signedIn.access_token);
            setPassword('');
          }
        },
      });

      const googleButton = googleButtonRef.current;
      if (!googleButton) return;
      googleApi.accounts.id.renderButton(googleButton, {
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'pill',
        logo_alignment: 'left',
      });
    };

    const googleApi = (window as typeof window & { google?: unknown }).google;
    if (googleApi) {
      initializeGoogle();
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = initializeGoogle;
    document.body.appendChild(script);

    return () => {
      const existingScript = document.getElementById('google-gsi-script');
      if (existingScript && existingScript.parentNode) {
        existingScript.parentNode.removeChild(existingScript);
      }
    };
  }, [googleClientId, run]);

  const signIn = async (event: FormEvent) => {
    event.preventDefault();
    const response = await run(
      () => careerRequest<{ access_token: string; user: { email: string } }>(
        '', `/auth/${authMode}`, { method: 'POST', body: { email, password } },
      ),
      authMode === 'register' ? 'Account created.' : 'Signed in.',
    );
    if (response) {
      sessionStorage.setItem(SESSION_TOKEN_KEY, response.access_token);
      setUserEmail(response.user.email);
      setToken(response.access_token);
      setPassword('');
    }
  };

  const signOut = async () => {
    await run(() => careerRequest<void>(token, '/auth/logout', { method: 'POST' }), 'Signed out.');
    sessionStorage.removeItem(SESSION_TOKEN_KEY);
    setToken('');
    setUserEmail('');
  };

  const performJobSearch = async (targetPage: number) => {
    const salaryMinimum = salaryMinimumFilter ? Number(salaryMinimumFilter) : null;
    const salaryMaximum = salaryMaximumFilter ? Number(salaryMaximumFilter) : null;
    if ((salaryMinimum !== null || salaryMaximum !== null) && !salaryCurrencyFilter.trim()) {
      setError('Choose a currency when filtering job listings by salary.');
      return;
    }
    if (salaryMinimum !== null && salaryMaximum !== null && salaryMinimum > salaryMaximum) {
      setError('Minimum salary cannot exceed maximum salary.');
      return;
    }
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/discover', {
        method: 'POST',
        body: {
          query, location, country, company: companyFilter,
          remote_type: remoteTypeFilter || null,
          employment_type: employmentTypeFilter || null,
          experience_level: experienceLevelFilter || null,
          salary_min: salaryMinimum,
          salary_max: salaryMaximum,
          salary_currency: salaryCurrencyFilter || null,
          sort_by: sortBy, page: targetPage, page_size: 20,
        },
      }),
    );
    if (result) {
      setSection('discover');
      setRecommendations(false);
      setSimilarJobTitle('');
      setJobs(records(result.jobs).map((job) => toCareerJob(job))
        .filter((job): job is CareerJob => job !== null));
      setPage(targetPage);
      setHasMoreJobs(Boolean(result.has_more));
      setNotice(`${Number(result.count || 0)} provider listing(s) returned for page ${targetPage}.`);
      const warnings = Array.isArray(result.warnings)
        ? result.warnings.filter((warning): warning is string => typeof warning === 'string')
        : [];
      if (warnings.length) setError(warnings.join(' '));
    }
  };

  const searchJobs = async (event: FormEvent) => {
    event.preventDefault();
    await performJobSearch(1);
  };

  const loadRecommendations = async () => {
    const useAI = aiRecommendationConsent;
    const result = await run(() => careerRequest<ApiRecord>(
      token, `/jobs/recommendations?use_ai=${useAI}`,
    ));
    if (useAI) setAiRecommendationConsent(false);
    if (result) {
      setRecommendations(true);
      setSimilarJobTitle('');
      setHasMoreJobs(false);
      const items = records(result.recommendations);
      setJobs(items.map((item) => toCareerJob(item.job, Number(record(item.match).score ?? 0), item.match))
        .filter((job): job is CareerJob => job !== null));
      setNotice(result.recommendation_method === 'ai_reranked'
        ? 'AI reordered real provider listings; the compatibility evidence remains deterministic.'
        : 'Recommendations are ranked using local resume and preference evidence.');
    }
  };

  const loadSimilarJobs = async (job: CareerJob) => {
    const result = await run(
      () => careerRequest<ApiRecord>(token, `/jobs/job/${encodeURIComponent(job.id)}/similar`),
    );
    if (result) {
      setSection('discover');
      setRecommendations(false);
      setSimilarJobTitle(job.title);
      setHasMoreJobs(false);
      setJobs(records(result.jobs).map((item) =>
        toCareerJob(item.job, Number(item.similarity_score ?? 0), { reason: item.reason })
      ).filter((item): item is CareerJob => item !== null));
    }
  };

  const createDeadlineReminder = async (job: CareerJob) => {
    if (!job.expires_at) return;
    const deadline = new Date(job.expires_at);
    if (Number.isNaN(deadline.getTime()) || deadline.getTime() <= Date.now()) {
      setError('The provider deadline is missing, invalid, or has passed.');
      return;
    }
    const dueAt = new Date(Math.max(Date.now(), deadline.getTime() - 24 * 60 * 60 * 1000));
    const result = await run(
      () => careerRequest(token, '/reminders', {
        method: 'POST',
        body: {
          job_id: job.id,
          reminder_type: 'job_deadline',
          due_at: dueAt.toISOString(),
          message: `Application deadline for ${job.title} at ${job.company_name}.`,
          email_requested: Boolean(preferences.email_reminders),
        },
      }),
      `Deadline reminder set for ${job.title}.`,
    );
    if (result !== undefined) await refresh('reminders');
  };

  const saveJob = async (job: CareerJob) => {
    const result = await run(
      () => careerRequest(token, `/jobs/${encodeURIComponent(job.id)}/save`, { method: 'POST' }),
      'Job saved to your account.',
    );
    if (result !== undefined) await refresh('saved');
  };

  const unsaveJob = async (job: CareerJob) => {
    await run(
      () => careerRequest<void>(token, `/jobs/${encodeURIComponent(job.id)}/save`, { method: 'DELETE' }),
      'Job removed from Saved Jobs.',
    );
    await refresh('saved');
  };

  const applyTrack = async (job: CareerJob) => {
    const result = await run(
      () => careerRequest(token, '/applications', {
        method: 'POST',
        body: {
          job_id: job.id, title: job.title, company_name: job.company_name,
          location: job.location || '', status: 'saved', description: '',
        },
      }),
      'Job added to your application tracker.',
    );
    if (result !== undefined) {
      await refresh('tracker');
    }
  };

  const compareJob = async (job: CareerJob) => {
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/jobs/match', {
        method: 'POST', body: { job_id: job.id },
      }),
    );
    if (result) setMatchResult(result);
  };

  const dismissJob = async (job: CareerJob) => {
    const result = await run(
      () => careerRequest(token, `/jobs/${encodeURIComponent(job.id)}/dismiss`, { method: 'POST' }),
      'Recommendation dismissed.',
    );
    if (result !== undefined) setJobs((current) => current.filter((item) => item.id !== job.id));
  };

  const createTailoring = async (job: CareerJob) => {
    const result = await run(
      () => careerRequest<TailoringReview>(
        token, `/jobs/job/${encodeURIComponent(job.id)}/tailor`, { method: 'POST' },
      ),
      'Review the evidence-based suggestions before saving.',
    );
    if (result) {
      setTailoringReview(result);
      setSavedVersion(null);
    }
  };

  const setChangeAcceptance = async (change: TailoringChange, accepted: boolean) => {
    if (!tailoringReview) return;
    const result = await run(
      () => careerRequest<TailoringReview>(
        token,
        `/tailoring/${encodeURIComponent(tailoringReview.id)}`,
        { method: 'PATCH', body: { changes: [{ id: change.id, is_accepted: accepted }] } },
      ),
    );
    if (result) setTailoringReview(result);
  };

  const saveTailoredVersion = async () => {
    if (!tailoringReview) return;
    const result = await run(
      () => careerRequest<ApiRecord>(
        token, `/tailoring/${encodeURIComponent(tailoringReview.id)}/save-version`, { method: 'POST' },
      ),
      'Approved changes saved as a separate resume version.',
    );
    if (result) setSavedVersion(result);
  };

  const downloadTailored = async (format: 'pdf' | 'docx') => {
    const structured = savedVersion?.structured_resume;
    if (!structured) return;
    const blob = await run(() => exportCareerResume(token, structured, format));
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `tailored-resume.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const analyzeDescription = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/jobs/analyze', {
        method: 'POST',
        body: {
          description: analyzerText,
          title: analyzerTitle || undefined,
          company_name: analyzerCompany || undefined,
        },
      }),
      'Description analyzed using local, deterministic parsing.',
    );
    if (result) {
      setAnalyzerResult(result);
      setSavedAnalysisJob(null);
      setAuthorizedAnalyzedJob(null);
    }
  };

  const compareAnalyzedDescription = async () => {
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/jobs/match', {
        method: 'POST', body: { description: analyzerText },
      }),
    );
    if (result) setMatchResult(result);
  };

  const analyzeAuthorizedUrl = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(
      () => careerRequest<ApiRecord>(token, '/jobs/analyze-url', {
        method: 'POST', body: { url: authorizedJobUrl },
      }),
    );
    if (result) {
      setAnalyzerResult(record(result.analysis));
      setAuthorizedAnalyzedJob(toCareerJob(result.job));
    }
  };

  const saveAuthorizedJob = async () => {
    if (!authorizedAnalyzedJob) return;
    await saveJob(authorizedAnalyzedJob);
    setAuthorizedAnalyzedJob(null);
  };

  const saveAnalyzedJob = async () => {
    if (!analyzerText.trim()) return;
    if (!analyzerTitle.trim() || !analyzerCompany.trim()) {
      setError('Add the job title and company before saving this private job record.');
      return;
    }
    const created = await run(
      () => careerRequest<CareerJob>(token, '/jobs', {
        method: 'POST',
        body: {
          title: analyzerTitle, company_name: analyzerCompany, description: analyzerText,
        },
      }),
      'Private job record created.',
    );
    if (!created) return;
    const saved = await run(
      () => careerRequest(token, `/jobs/${encodeURIComponent(created.id)}/save`, { method: 'POST' }),
      'Job stored in Saved Jobs.',
    );
    if (saved !== undefined) setSavedAnalysisJob(created);
  };

  const uploadResume = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const file = (form.elements.namedItem('resume-file') as HTMLInputElement | null)?.files?.[0];
    if (!file) {
      setError('Choose a PDF or DOCX resume to upload.');
      return;
    }
    const formData = new FormData();
    formData.append('resume_file', file, file.name);
    const result = await run(
      () => careerRequest<ResumeProfile>(
        token, `/profile/resumes/upload?title=${encodeURIComponent(resumeTitle)}`,
        { method: 'POST', body: formData },
      ),
      'Resume securely saved and set as primary.',
    );
    if (result) {
      form.reset();
      await refresh('profile');
    }
  };

  const saveResumeText = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(
      () => careerRequest(token, '/profile/resumes', {
        method: 'POST', body: { title: resumeTitle, resume_text: resumeText },
      }),
      'Resume securely saved and set as primary.',
    );
    if (result !== undefined) {
      setResumeText('');
      await refresh('profile');
    }
  };

  const savePreferences = async (event: FormEvent) => {
    event.preventDefault();
    const body = {
      preferred_titles: parseList(preferenceTitles),
      preferred_locations: parseList(preferenceLocations),
      industries: parseList(preferenceIndustries),
      career_goals: preferenceGoals,
      work_modes: (preferences.work_modes as string[]) || [],
      employment_types: (preferences.employment_types as string[]) || [],
      salary_min: preferences.salary_min ?? null,
      salary_max: preferences.salary_max ?? null,
      salary_currency: preferences.salary_currency ?? null,
      experience_level: preferences.experience_level ?? null,
      application_follow_up_days: preferences.application_follow_up_days ?? 7,
      interview_reminder_hours: preferences.interview_reminder_hours ?? [24, 1],
      email_reminders: preferences.email_reminders ?? false,
    };
    const result = await run(
      () => careerRequest(token, '/profile/preferences', { method: 'PUT', body }),
      'Search and reminder preferences saved.',
    );
    if (result) setPreferences(body);
  };

  const changeApplicationStatus = async (application: CareerApplication, nextStatus: string) => {
    const result = await run(
      () => careerRequest(token, `/applications/${encodeURIComponent(application.id)}`, {
        method: 'PATCH',
        body: {
          status: nextStatus,
          note: applicationHistoryNotes[application.id] || '',
        },
      }),
      `Application moved to ${nextStatus}.`,
    );
    if (result !== undefined) await refresh('tracker');
  };

  const saveApplicationNotes = async (application: CareerApplication) => {
    const result = await run(
      () => careerRequest(token, `/applications/${encodeURIComponent(application.id)}`, {
        method: 'PATCH',
        body: {
          notes: applicationNoteDrafts[application.id] || '',
          note: 'Application notes updated.',
        },
      }),
      'Application notes saved to the activity history.',
    );
    if (result !== undefined) await refresh('tracker');
  };

  const loadApplicationHistory = async (application: CareerApplication) => {
    const result = await run(
      () => careerRequest<ApplicationEvent[]>(
        token, `/applications/${encodeURIComponent(application.id)}/history`,
      ),
    );
    if (result) {
      setApplicationHistory(result);
      setOpenHistoryId(application.id);
    }
  };

  const createApplicationDraft = async (application: CareerApplication, draftType = applicationDraftType) => {
    const result = await run(
      () => careerRequest<ApiRecord>(
        token, `/applications/${encodeURIComponent(application.id)}/draft`,
        { method: 'POST', body: { application_id: application.id, draft_type: draftType } },
      ),
      'AI draft generated for editing; it has not been sent.',
    );
    if (result) {
      setFollowUpDraft(result);
      setDraftApplication(application);
      setDraftId('');
    }
  };

  const updateApplicationResume = async (application: CareerApplication, resumeId: string) => {
    const result = await run(
      () => careerRequest(token, `/applications/${encodeURIComponent(application.id)}`, {
        method: 'PATCH',
        body: { resume_version_id: resumeId || null },
      }),
      'Application resume association updated.',
    );
    if (result !== undefined) await refresh('tracker');
  };

  const loadApplicationDrafts = async (application: CareerApplication) => {
    const result = await run(
      () => careerRequest<ApiRecord[]>(
        token, `/applications/${encodeURIComponent(application.id)}/drafts`,
      ),
    );
    if (result) setApplicationDrafts((current) => ({ ...current, [application.id]: result }));
  };

  const saveApplicationDraft = async () => {
    if (!draftApplication || !followUpDraft) return;
    const result = await run(() => careerRequest<ApiRecord>(
      token,
      `/applications/${encodeURIComponent(draftApplication.id)}/drafts${draftId ? `/${encodeURIComponent(draftId)}` : ''}`,
      {
        method: draftId ? 'PUT' : 'POST',
        body: {
          draft_type: String(followUpDraft.draft_type),
          subject: String(followUpDraft.subject || ''),
          body: String(followUpDraft.body || ''),
        },
      },
    ), 'Draft saved securely to this application.');
    if (result) {
      setDraftId(String(result.id));
      await loadApplicationDrafts(draftApplication);
    }
  };

  const openApplicationDraft = (application: CareerApplication, draft: ApiRecord) => {
    setDraftApplication(application);
    setDraftId(String(draft.id));
    setFollowUpDraft(draft);
  };

  const deleteApplicationDraft = async (application: CareerApplication, draft: ApiRecord) => {
    const result = await run(async () => {
      await careerRequest<void>(
        token,
        `/applications/${encodeURIComponent(application.id)}/drafts/${encodeURIComponent(String(draft.id))}`,
        { method: 'DELETE' },
      );
      return true;
    }, 'Saved draft deleted.');
    if (result) await loadApplicationDrafts(application);
  };

  const updateInterview = async (
    interview: CareerInterview,
    changes: { status?: 'completed' | 'cancelled'; scheduled_at?: string },
  ) => {
    const result = await run(
      () => careerRequest(token, `/interviews/${encodeURIComponent(interview.id)}`, {
        method: 'PATCH',
        body: {
          ...changes,
          ...(changes.scheduled_at ? {
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          } : {}),
        },
      }),
      changes.scheduled_at ? 'Interview rescheduled and reminders updated.' : `Interview ${changes.status}.`,
    );
    if (result !== undefined) await refresh('interviews');
  };

  const createManualApplication = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(
      () => careerRequest(token, '/applications', {
        method: 'POST',
        body: {
          title: manualTitle,
          company_name: manualCompany,
          notes: manualNotes,
          description: manualDescription,
          status: 'saved',
        },
      }),
      'Application added to your tracker.',
    );
    if (result !== undefined) {
      setManualTitle('');
      setManualCompany('');
      setManualNotes('');
      setManualDescription('');
      await refresh('tracker');
    }
  };

  const scheduleInterview = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(
      () => careerRequest(token, '/interviews', {
        method: 'POST',
        body: {
          application_id: interviewApplication,
          scheduled_at: new Date(interviewDate).toISOString(),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          interview_type: interviewType,
          preparation_notes: interviewNotes,
        },
      }),
      'Interview scheduled. Reminder intervals follow your saved preferences.',
    );
    if (result !== undefined) {
      setInterviewNotes('');
      await refresh('interviews');
    }
  };

  const createReminder = async (event: FormEvent) => {
    event.preventDefault();
    const result = await run(
      () => careerRequest(token, '/reminders', {
        method: 'POST',
        body: {
          application_id: reminderApplication,
          reminder_type: 'custom',
          due_at: new Date(reminderDate).toISOString(),
          message: reminderMessage,
        },
      }),
      'Reminder saved.',
    );
    if (result !== undefined) {
      setReminderMessage('');
      await refresh('reminders');
    }
  };

  const updateReminder = async (reminder: CareerReminder, status: 'completed' | 'snoozed') => {
    const body = status === 'completed'
      ? { status }
      : { status, snoozed_until: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() };
    const result = await run(
      () => careerRequest(token, `/reminders/${encodeURIComponent(reminder.id)}`, { method: 'PATCH', body }),
      status === 'completed' ? 'Reminder completed.' : 'Reminder snoozed for one day.',
    );
    if (result !== undefined) await refresh('reminders');
  };

  const loadSalary = async (event: FormEvent) => {
    event.preventDefault();
    const params = new URLSearchParams({ role: salaryRole, location: salaryLocation });
    const result = await run(
      () => careerRequest<ApiRecord>(token, `/salary/intelligence?${params.toString()}`),
    );
    if (result) setSalaryData(result);
  };

  const updateSkill = async (skill: string, value: string) => {
    const result = await run(() => careerRequest(
      token, `/skills/${encodeURIComponent(skill)}/progress`, {
        method: 'PUT', body: { status: value },
      },
    ), `Skill progress updated for ${skill}.`);
    if (result !== undefined) setSkillStatuses((current) => ({ ...current, [skill]: value }));
  };

  if (!token) {
    return (
      <div className="career-auth-shell">
        <section className="career-auth-card">
          <div className="career-icon-tile"><ShieldCheck size={24} /></div>
          <p className="career-eyebrow">Career intelligence workspace</p>
          <h1>{authMode === 'register' ? 'Create your career account' : 'Welcome back'}</h1>
          <p className="career-muted">
            Your resumes, application records, preferences, and reminders are account-scoped and stored encrypted.
          </p>
          {error && <div className="career-alert career-alert-error" role="alert">{error}</div>}
          {notice && <div className="career-alert career-alert-success" role="status">{notice}</div>}
          <form className="career-form" onSubmit={signIn}>
            <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Password<input type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} minLength={authMode === 'register' ? 12 : 1} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? 'Please wait…' : authMode === 'register' ? 'Create account' : 'Sign in'} <ArrowRight size={16} /></button>
          </form>
          {googleClientId && (
            <>
              <div className="career-divider"><span>or</span></div>
              <div ref={googleButtonRef} className="career-google-auth" aria-label="Continue with Google" />
            </>
          )}
          <button type="button" className="career-text-button" onClick={() => setAuthMode(authMode === 'register' ? 'login' : 'register')}>
            {authMode === 'register' ? 'Already have an account? Sign in' : 'New here? Create an account'}
          </button>
          <p className="career-security-note"><ShieldCheck size={14} /> Encrypted data storage requires the backend encryption key to be configured.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="career-platform-shell">
      <aside className="career-sidebar" aria-label="Career platform navigation">
        <div className="career-sidebar-brand"><div className="career-icon-tile"><Sparkles size={20} /></div><div><strong>Career OS</strong><small>JOB INTELLIGENCE</small></div></div>
        <nav className="career-nav">
          {NAV_ITEMS.map((item) => (
            <button key={item.id} type="button" className={section === item.id ? 'career-nav-active' : ''} onClick={() => { setSection(item.id); setError(''); setNotice(''); }}>
              {item.icon}<span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="career-sidebar-footer">
          <span className="career-user-avatar">{userEmail.slice(0, 1).toUpperCase() || 'U'}</span>
          <span className="career-user-email" title={userEmail}>{userEmail}</span>
          <button type="button" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={16} /></button>
        </div>
      </aside>

      <section className="career-main">
        <header className="career-topbar">
          <div><p className="career-eyebrow">YOUR CAREER WORKSPACE</p><h1>{NAV_ITEMS.find((item) => item.id === section)?.label}</h1></div>
          <div className="career-live-tag"><span /> Private workspace</div>
        </header>
        <div className="career-content">
          {error && <div className="career-alert career-alert-error" role="alert">{error}<button type="button" onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button></div>}
          {notice && <div className="career-alert career-alert-success" role="status">{notice}<button type="button" onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={15} /></button></div>}
          {loading && <div className="career-loading" role="status">Loading your saved career data…</div>}
          {busy && <div className="career-action-progress" role="status">Saving securely…</div>}

          {section === 'overview' && (
            <OverviewSection
              analytics={analytics}
              searchSummary={searchSummary}
              commandCenter={commandCenter}
              notificationPreferences={notificationPreferences}
              onNotificationPreferencesChange={setNotificationPreferences}
              onSaveNotificationPreferences={saveNotificationPreferences}
              careerScoreWeights={careerScoreWeights}
              onCareerScoreWeightsChange={setCareerScoreWeights}
              onSaveCareerScoreWeights={saveCareerScoreWeights}
              onMarkNotificationRead={markNotificationRead}
              onLoadMoreTimeline={loadMoreCareerTimeline}
              busy={busy}
              onNavigate={setSection}
            />
          )}

          {section === 'discover' && (
            <>
              <section className="career-panel">
                <div className="career-panel-heading"><div><p className="career-eyebrow">REAL LISTINGS ONLY</p><h2>{recommendations ? 'Your recommended opportunities' : similarJobTitle ? `Similar to ${similarJobTitle}` : 'Find your next opportunity'}</h2></div><button type="button" className="btn btn-secondary" onClick={loadRecommendations}>Personalized recommendations</button></div>
                <label className="career-checkbox career-ai-consent"><input type="checkbox" checked={aiRecommendationConsent} onChange={(event) => setAiRecommendationConsent(event.target.checked)} /> Opt in to AI re-ranking for one recommendation request</label>
                <p className="career-disclaimer">When enabled, your resume evidence, saved preferences, and up to 30 real listing summaries are sent to the configured backend AI provider. Leave unchecked to use local deterministic ranking.</p>
                <form className="career-search-form" onSubmit={searchJobs}>
                  <label><span>Role or skills</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. data analyst, Python" /></label>
                  <label><span>City, state, or location</span><input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="City, state, country, or remote" /></label>
                  <label className="career-country-field"><span>Adzuna country code</span><input maxLength={2} value={country} onChange={(event) => setCountry(event.target.value.toLowerCase())} /></label>
                  <button className="btn btn-primary" type="submit" disabled={busy}><Search size={16} /> Search providers</button>
                </form>
                <div className="career-search-filters">
                  <label><span>Company</span><input value={companyFilter} onChange={(event) => setCompanyFilter(event.target.value)} placeholder="Any company" /></label>
                  <label><span>Work mode</span><select value={remoteTypeFilter} onChange={(event) => setRemoteTypeFilter(event.target.value)}><option value="">Any mode</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="on_site">On-site</option></select></label>
                  <label><span>Experience level</span><select value={experienceLevelFilter} onChange={(event) => setExperienceLevelFilter(event.target.value)}><option value="">Any level</option><option value="fresher">Fresher / internship</option><option value="entry_level">Entry-level</option><option value="intermediate">Intermediate</option><option value="experienced">Experienced</option></select></label>
                  <label><span>Employment type</span><select value={employmentTypeFilter} onChange={(event) => setEmploymentTypeFilter(event.target.value)}><option value="">Any type</option><option value="full-time">Full-time</option><option value="part-time">Part-time</option><option value="contract">Contract</option><option value="internship">Internship</option><option value="temporary">Temporary</option></select></label>
                  <label><span>Min salary</span><input type="number" min="0" value={salaryMinimumFilter} onChange={(event) => setSalaryMinimumFilter(event.target.value)} placeholder="Any" /></label>
                  <label><span>Max salary</span><input type="number" min="0" value={salaryMaximumFilter} onChange={(event) => setSalaryMaximumFilter(event.target.value)} placeholder="Any" /></label>
                  <label><span>Currency for salary filter</span><input maxLength={3} value={salaryCurrencyFilter} onChange={(event) => setSalaryCurrencyFilter(event.target.value.toUpperCase())} placeholder="USD / INR / GBP" /></label>
                  <label><span>Sort by</span><select value={sortBy} onChange={(event) => setSortBy(event.target.value)}><option value="newest">Most recent</option><option value="salary_high">Salary: high to low</option><option value="salary_low">Salary: low to high</option><option value="company">Company name</option></select></label>
                </div>
                <p className="career-disclaimer">Only configured, permission-gated provider feeds appear here. A missing provider means credentials or usage authorization are not configured—not that listings were generated.</p>
                <p className="career-disclaimer">Country codes are applied by Adzuna. For configured employer boards, use the location field; country is shown only when the source provides it.</p>
                <div className="career-provider-list">
                  {providers.map((provider) => <span key={provider.provider} className={provider.enabled ? 'career-provider-enabled' : ''}>{provider.provider} · {provider.enabled ? 'available' : 'not configured'}</span>)}
                </div>
                {marketDemand && <MarketDemandSection data={marketDemand} />}
              </section>
              {jobs.length === 0 && !loading && <EmptyState title={recommendations ? 'No recommendations yet' : similarJobTitle ? 'No similar listings found' : 'No job listings loaded'} detail={recommendations ? 'Save a resume and set your job preferences to get matched recommendations.' : similarJobTitle ? 'No other currently available imported listing has enough role or skill overlap.' : 'Search an authorized provider. Results are never fabricated.'} />}
              <div className="career-job-grid">
                {jobs.map((job) => (
                  <JobCard key={job.id} job={job} onSave={saveJob} onApply={applyTrack} onCompare={compareJob} onDismiss={recommendations ? dismissJob : undefined} onTailor={createTailoring} onSimilar={loadSimilarJobs} onDeadlineReminder={createDeadlineReminder} />
                ))}
              </div>
              {!recommendations && !similarJobTitle && <div className="career-pagination"><button type="button" className="btn btn-secondary" disabled={page <= 1 || busy} onClick={() => void performJobSearch(page - 1)}>Previous</button><span>Provider page {page}</span><button type="button" className="btn btn-secondary" disabled={!hasMoreJobs || busy} onClick={() => void performJobSearch(page + 1)}>Next</button></div>}
              {matchResult && <MatchPanel result={matchResult} skillStatuses={skillStatuses} onSkillProgress={updateSkill} />}
              {tailoringReview && (
                <TailoringPanel
                  review={tailoringReview}
                  savedVersion={savedVersion}
                  onAccept={setChangeAcceptance}
                  onSave={saveTailoredVersion}
                  onDownload={downloadTailored}
                />
              )}
            </>
          )}

          {section === 'analyzer' && (
            <section className="career-panel career-analyzer">
              <div className="career-panel-heading"><div><p className="career-eyebrow">JOB DESCRIPTION ANALYZER</p><h2>Understand the role before you apply</h2></div><FileSearch size={22} /></div>
              <form className="career-form" onSubmit={analyzeDescription}>
                <div className="career-two-columns">
                  <label>Job title<input value={analyzerTitle} onChange={(event) => setAnalyzerTitle(event.target.value)} placeholder="Role title" /></label>
                  <label>Company<input value={analyzerCompany} onChange={(event) => setAnalyzerCompany(event.target.value)} placeholder="Company name" /></label>
                </div>
                <label>Job description<textarea rows={10} required minLength={30} value={analyzerText} onChange={(event) => setAnalyzerText(event.target.value)} placeholder="Paste an authorized job description. URLs are only analyzed when they came from an imported provider feed." /></label>
                <div className="career-inline-actions"><button className="btn btn-primary" disabled={busy}>Analyze description</button>{analyzerResult && <><button className="btn btn-secondary" type="button" disabled={busy} onClick={compareAnalyzedDescription}>Compare with saved resume</button><button className="btn btn-secondary" type="button" disabled={busy} onClick={saveAnalyzedJob}>Save job privately</button></>}</div>
              </form>
              {analyzerResult && <div className="career-analysis-result"><p className="career-eyebrow">EXTRACTED FACTS AND RULE-BASED INTERPRETATION</p><pre>{JSON.stringify(analyzerResult, null, 2)}</pre></div>}
              {matchResult && <MatchPanel result={matchResult} skillStatuses={skillStatuses} onSkillProgress={updateSkill} />}
              <form className="career-inline-form career-url-analysis" onSubmit={analyzeAuthorizedUrl}><input type="url" required value={authorizedJobUrl} onChange={(event) => setAuthorizedJobUrl(event.target.value)} placeholder="HTTPS URL from an imported provider listing" /><button className="btn btn-secondary">Analyze authorized listing URL</button></form>
              {authorizedAnalyzedJob && <button className="btn btn-secondary" type="button" onClick={saveAuthorizedJob}>Save {authorizedAnalyzedJob.title} to Saved Jobs</button>}
              {savedAnalysisJob && <p className="career-inline-success"><Check size={16} /> {savedAnalysisJob.title} is saved to your account's Saved Jobs.</p>}
            </section>
          )}

          {section === 'saved' && (
            <>
              <SectionIntro title="Saved jobs" detail="Your saved provider listings and private job records, with source and availability retained." />
              {savedJobs.length === 0 && <EmptyState title="Nothing saved yet" detail="Save a real listing from Discover or create a private record in Job Analyzer." />}
              <div className="career-job-grid">{savedJobs.map((job) => <JobCard key={job.id} job={job} onApply={applyTrack} onCompare={compareJob} onTailor={createTailoring} onUnsave={unsaveJob} onSimilar={loadSimilarJobs} onDeadlineReminder={createDeadlineReminder} />)}</div>
              {matchResult && <MatchPanel result={matchResult} skillStatuses={skillStatuses} onSkillProgress={updateSkill} />}
              {tailoringReview && <TailoringPanel review={tailoringReview} savedVersion={savedVersion} onAccept={setChangeAcceptance} onSave={saveTailoredVersion} onDownload={downloadTailored} />}
            </>
          )}

          {section === 'tracker' && (
            <>
              <section className="career-panel">
                <div className="career-panel-heading"><div><p className="career-eyebrow">APPLICATION PIPELINE</p><h2>Keep every opportunity moving</h2></div><span className="career-count">{applications.length} records</span></div>
                <form className="career-search-form career-manual-application" onSubmit={createManualApplication}>
                  <label><span>Role</span><input required value={manualTitle} onChange={(event) => setManualTitle(event.target.value)} placeholder="Job title" /></label>
                  <label><span>Company</span><input required value={manualCompany} onChange={(event) => setManualCompany(event.target.value)} placeholder="Company" /></label>
                  <label><span>Note (optional)</span><input value={manualNotes} onChange={(event) => setManualNotes(event.target.value)} placeholder="Next action" /></label>
                  <button className="btn btn-primary" disabled={busy}>Add application</button>
                  <label className="career-manual-description"><span>Job description (optional, for tailored drafts)</span><textarea rows={3} value={manualDescription} onChange={(event) => setManualDescription(event.target.value)} placeholder="Paste an authorized job description to personalize application materials." /></label>
                </form>
              </section>
              <section className="career-panel">
                <div className="career-panel-heading"><div><p className="career-eyebrow">NEXT BEST ACTION</p><h2>Prioritized applications</h2></div><span className="career-count">{applicationPriorities.length} active</span></div>
                <p className="career-disclaimer">Ranking is a transparent heuristic using application stage, saved match evidence, your preferences, and source-provided deadlines. It does not infer a deadline or guarantee an outcome.</p>
                {applicationPriorities.length === 0 ? <p className="career-muted">Add or track applications to see suggested priorities.</p> : <div className="career-priority-list">
                  {applicationPriorities.slice(0, 10).map((item, index) => <article key={String(item.application_id)}>
                    <span className="career-priority-rank">{index + 1}</span>
                    <div><strong>{String(item.title)} · {String(item.company_name)}</strong><small>{String(item.status)} · priority {String(item.priority_score)}/100</small>
                      {Boolean(item.deadline) && <small>Source deadline: {formatDate(String(item.deadline))}</small>}
                      <span>{records(item.factors).map((factor) => `${String(factor.factor)}: ${String(factor.evidence)}`).join(' · ') || 'No additional matching signals recorded.'}</span>
                    </div>
                  </article>)}
                </div>}
              </section>
              <div className="career-board">
                {APPLICATION_STATUSES.map((status) => {
                  const cards = applications.filter((application) => application.status === status);
                  return <section className="career-board-column" key={status}><h3>{status}<span>{cards.length}</span></h3>
                    {cards.map((application) => <article className="career-application-card" key={application.id}>
                      <strong>{application.title}</strong><p>{application.company_name}</p>{application.location && <small><MapPin size={12} /> {application.location}</small>}
                      {application.applied_at && <small>Applied {formatDate(application.applied_at)}</small>}
                      <label className="career-status-select">Application notes<textarea rows={2} value={applicationNoteDrafts[application.id] ?? application.notes ?? ''} onChange={(event) => setApplicationNoteDrafts((current) => ({ ...current, [application.id]: event.target.value }))} /></label>
                      <button type="button" className="career-link-button" disabled={busy} onClick={() => saveApplicationNotes(application)}>Save notes</button>
                      <label className="career-status-select">Resume used for this application<select value={application.resume_version_id || ''} onChange={(event) => updateApplicationResume(application, event.target.value)}><option value="">Use primary resume for AI drafts</option>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.title}{resume.is_primary ? ' (primary)' : ''}</option>)}</select></label>
                      <label className="career-status-select">Add a status history note<input value={applicationHistoryNotes[application.id] || ''} onChange={(event) => setApplicationHistoryNotes((current) => ({ ...current, [application.id]: event.target.value }))} placeholder="Optional note for this transition" /></label>
                      <label className="career-status-select">Move to<select value={status} onChange={(event) => changeApplicationStatus(application, event.target.value)}><option value={status}>{status}</option>{APPLICATION_STATUSES.filter((value) => value !== status).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                      <button className="career-link-button" type="button" onClick={() => { setInterviewApplication(application.id); setSection('interviews'); }}>Schedule interview <ArrowRight size={13} /></button>
                      <button className="career-link-button" type="button" onClick={() => openHistoryId === application.id ? setOpenHistoryId('') : loadApplicationHistory(application)}>Application history <ArrowRight size={13} /></button>
                      {openHistoryId === application.id && <div className="career-history-list">{applicationHistory.map((event) => <p key={event.id}><strong>{event.note || `${event.from_status || 'Created'} → ${event.to_status}`}</strong><span>{formatDate(event.created_at)} · {event.from_status === event.to_status ? event.to_status : `${event.from_status || 'Created'} → ${event.to_status}`}</span></p>)}</div>}
                      {application.original_url && <a className="career-link-button" href={application.original_url} target="_blank" rel="noreferrer">Open source application page <ArrowRight size={13} /></a>}
                      <div className="career-application-draft-actions">
                        <label>Application assistant / draft<select value={applicationDraftType} onChange={(event) => setApplicationDraftType(event.target.value)}><option value="application_assistant">Next-step assistant</option><option value="cover_letter">Cover letter</option><option value="application_email">Application email</option><option value="recruiter_follow_up">Recruiter follow-up</option><option value="interview_follow_up">Interview follow-up</option></select></label>
                        <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => createApplicationDraft(application)}>Generate AI draft</button>
                        <button className="career-link-button" type="button" onClick={() => loadApplicationDrafts(application)}>Saved drafts</button>
                      </div>
                      {(applicationDrafts[application.id] || []).map((draft) => <div className="career-saved-draft-row" key={String(draft.id)}>
                        <button type="button" className="career-link-button" onClick={() => openApplicationDraft(application, draft)}>{String(draft.draft_type).replaceAll('_', ' ')} · {formatDate(String(draft.updated_at || draft.created_at))}</button>
                        <button type="button" className="career-link-button" onClick={() => deleteApplicationDraft(application, draft)}>Delete</button>
                      </div>)}
                    </article>)}
                  </section>;
                })}
              </div>
              {followUpDraft && <section className="career-panel career-draft-panel">
                <div className="career-panel-heading"><div><p className="career-eyebrow">EDIT AND REVIEW BEFORE SENDING</p><h2>{display(followUpDraft.draft_type, 'Application draft').replaceAll('_', ' ')}</h2></div><button type="button" className="career-text-button" onClick={() => setFollowUpDraft(null)} aria-label="Close draft editor"><X size={16} /></button></div>
                <label className="career-field-label">Subject<input value={String(followUpDraft.subject || '')} onChange={(event) => setFollowUpDraft((current) => current ? { ...current, subject: event.target.value } : current)} /></label>
                <label className="career-field-label">Editable draft<textarea rows={14} value={String(followUpDraft.body || '')} onChange={(event) => setFollowUpDraft((current) => current ? { ...current, body: event.target.value } : current)} /></label>
                <div className="career-inline-actions"><button type="button" className="btn btn-primary" disabled={busy} onClick={() => void saveApplicationDraft()}>{draftId ? 'Save draft changes' : 'Save draft to application'}</button><p className="career-disclaimer">Drafts are private, encrypted, and never sent automatically. AI suggestions may need factual review.</p></div>
              </section>}
            </>
          )}

          {section === 'interviews' && (
            <div className="career-two-columns career-schedule-layout">
              <section className="career-panel">
                <p className="career-eyebrow">INTERVIEW CALENDAR</p><h2>Schedule and prepare</h2>
                <form className="career-form" onSubmit={scheduleInterview}>
                  <label>Application<select required value={interviewApplication} onChange={(event) => setInterviewApplication(event.target.value)}><option value="">Choose an application</option>{applications.map((application) => <option key={application.id} value={application.id}>{application.title} · {application.company_name}</option>)}</select></label>
                  <label>Date and time<input type="datetime-local" required value={interviewDate} onChange={(event) => setInterviewDate(event.target.value)} /></label>
                  <label>Interview type<input required value={interviewType} onChange={(event) => setInterviewType(event.target.value)} /></label>
                  <label>Preparation notes<textarea rows={4} value={interviewNotes} onChange={(event) => setInterviewNotes(event.target.value)} /></label>
                  <button className="btn btn-primary" disabled={busy || applications.length === 0}>Save interview</button>
                </form>
              </section>
              <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">UPCOMING & RECENT</p><h2>Interview schedule</h2></div><CalendarDays size={22} /></div>
                {interviews.length === 0 ? <EmptyState title="No interviews scheduled" detail="Schedule an interview from an application to track preparation and reminders." /> : interviews.map((interview) => <article className="career-list-row" key={interview.id}><div className="career-list-icon"><CalendarDays size={18} /></div><div className="career-list-main"><strong>{interview.title} · {interview.company_name}</strong><span>{formatDate(interview.scheduled_at)} · {interview.timezone} · {interview.interview_type}</span>{interview.preparation_notes && <small>{interview.preparation_notes}</small>}{interview.meeting_url && <a href={interview.meeting_url} target="_blank" rel="noreferrer">Open meeting link</a>}{interview.status === 'scheduled' && <div className="career-reschedule-controls"><input type="datetime-local" aria-label={`Reschedule ${interview.title}`} value={interviewReschedules[interview.id] || ''} onChange={(event) => setInterviewReschedules((current) => ({ ...current, [interview.id]: event.target.value }))} /><button type="button" onClick={() => { const date = interviewReschedules[interview.id]; if (date) void updateInterview(interview, { scheduled_at: new Date(date).toISOString() }); }}>Reschedule</button><button type="button" onClick={() => updateInterview(interview, { status: 'completed' })}>Complete</button><button type="button" onClick={() => updateInterview(interview, { status: 'cancelled' })}>Cancel</button></div>}</div><span className="career-pill">{interview.status}</span></article>)}
              </section>
            </div>
          )}

          {section === 'reminders' && (
            <div className="career-two-columns career-schedule-layout">
              <section className="career-panel"><p className="career-eyebrow">FOLLOW-UP REMINDERS</p><h2>Create a reminder</h2>
                <form className="career-form" onSubmit={createReminder}>
                  <label>Application<select required value={reminderApplication} onChange={(event) => setReminderApplication(event.target.value)}><option value="">Choose an application</option>{applications.map((application) => <option key={application.id} value={application.id}>{application.title} · {application.company_name}</option>)}</select></label>
                  <label>Reminder date and time<input type="datetime-local" required value={reminderDate} onChange={(event) => setReminderDate(event.target.value)} /></label>
                  <label>Reminder note<input required value={reminderMessage} onChange={(event) => setReminderMessage(event.target.value)} placeholder="What should you remember?" /></label>
                  <button className="btn btn-primary" disabled={busy || applications.length === 0}>Save reminder</button>
                </form>
                <p className="career-disclaimer">Email is only sent when you explicitly enable it in preferences and configure SMTP. Employer messages are never sent automatically.</p>
              </section>
              <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">REMINDER CENTER</p><h2>Upcoming and completed</h2></div><Bell size={22} /></div>
                {reminders.length === 0 ? <EmptyState title="No reminders yet" detail="Application follow-ups and interview reminders will appear here." /> : reminders.map((reminder) => <article className="career-list-row" key={reminder.id}><div className="career-list-icon"><Bell size={18} /></div><div className="career-list-main"><strong>{reminder.message}</strong><span>{formatDate(reminder.due_at)} · {reminder.reminder_type}</span><small>{reminder.status}{reminder.email_status ? ` · email: ${reminder.email_status}` : ''}</small></div>{['scheduled', 'snoozed'].includes(reminder.status) && <div className="career-row-actions"><button type="button" onClick={() => updateReminder(reminder, 'snoozed')}>Snooze</button><button type="button" onClick={() => updateReminder(reminder, 'completed')}>Complete</button></div>}</article>)}
              </section>
            </div>
          )}

          {section === 'research' && (
            <>
              <CompanyIntelligenceSection token={token} />
              <section className="career-panel"><p className="career-eyebrow">DISCLOSED SALARIES</p><h2>Salary range intelligence</h2>
                <form className="career-form" onSubmit={loadSalary}><label>Role<input required value={salaryRole} onChange={(event) => setSalaryRole(event.target.value)} placeholder="e.g. product designer" /></label><label>Location<input value={salaryLocation} onChange={(event) => setSalaryLocation(event.target.value)} placeholder="City or country" /></label><button className="btn btn-primary"><CircleDollarSign size={16} /> Find reported ranges</button></form>
                {salaryData && <div className="career-analysis-result"><p className="career-eyebrow">SOURCE-LINKED RESULTS</p><pre>{JSON.stringify(salaryData, null, 2)}</pre></div>}
                <p className="career-disclaimer">Salary ranges come only from listings that disclose them; these are not market-wide estimates.</p>
              </section>
            </>
          )}

          {section === 'analytics' && <AnalyticsSection analytics={analytics} searchSummary={searchSummary} />}

          {section === 'salary' && <SalaryIntelligenceSection token={token} />}

          {section === 'coach' && <CareerCoachSection token={token} />}

          {section === 'academy' && <LearningAcademySection token={token} />}

          {section === 'branding' && <PersonalBrandingSection token={token} />}

          {section === 'business' && <BusinessRevenueSection token={token} />}

          {section === 'profile' && (
            <div className="career-two-columns career-profile-layout">
              <section className="career-panel"><p className="career-eyebrow">RESUME PROFILE</p><h2>Securely store a resume version</h2>
                <label className="career-field-label">Resume version name<input value={resumeTitle} onChange={(event) => setResumeTitle(event.target.value)} /></label>
                <form className="career-form" onSubmit={uploadResume}><label>Upload PDF or DOCX<input name="resume-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required /></label><button className="btn btn-primary" disabled={busy}><FileText size={16} /> Upload and save</button></form>
                <div className="career-divider"><span>or paste plain text</span></div>
                <form className="career-form" onSubmit={saveResumeText}><label>Resume text<textarea rows={7} minLength={100} required value={resumeText} onChange={(event) => setResumeText(event.target.value)} placeholder="At least 30 words are required for matching." /></label><button className="btn btn-secondary" disabled={busy}>Save text resume</button></form>
                <p className="career-disclaimer">Resume text and parsed content are encrypted at rest using the configured backend key. Keep that key safe; losing it makes encrypted records unreadable.</p>
                <h3 className="career-subheading">Saved versions</h3>
                {resumes.map((resume) => <div className="career-resume-row" key={resume.id}><FileText size={16} /><div><strong>{resume.title}</strong><small>{resume.is_primary ? 'Primary version' : 'Saved version'} · {(resume.skills || []).length} detected skills</small></div><span>{resume.is_primary ? 'PRIMARY' : 'VERSION'}</span></div>)}
                {!resumes.length && <p className="career-muted">No resume profiles saved yet.</p>}
              </section>
              <section className="career-panel"><p className="career-eyebrow">SEARCH PREFERENCES</p><h2>Guide recommendations</h2>
                <form className="career-form" onSubmit={savePreferences}>
                  <label>Preferred job titles<input value={preferenceTitles} onChange={(event) => setPreferenceTitles(event.target.value)} placeholder="Comma-separated titles" /></label>
                  <label>Preferred locations<input value={preferenceLocations} onChange={(event) => setPreferenceLocations(event.target.value)} placeholder="City, country, or remote" /></label>
                  <label>Industries<input value={preferenceIndustries} onChange={(event) => setPreferenceIndustries(event.target.value)} placeholder="Comma-separated industries" /></label>
                  <label>Career goals<textarea rows={4} value={preferenceGoals} onChange={(event) => setPreferenceGoals(event.target.value)} /></label>
                  <label>Work modes<select multiple value={(preferences.work_modes as string[]) || []} onChange={(event) => setPreferences((current) => ({ ...current, work_modes: Array.from(event.target.selectedOptions, (option) => option.value) }))}><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="on_site">On-site</option></select></label>
                  <label>Employment types<select multiple value={(preferences.employment_types as string[]) || []} onChange={(event) => setPreferences((current) => ({ ...current, employment_types: Array.from(event.target.selectedOptions, (option) => option.value) }))}><option value="full-time">Full-time</option><option value="part-time">Part-time</option><option value="contract">Contract</option><option value="internship">Internship</option><option value="temporary">Temporary</option></select></label>
                  <label>Minimum salary<input type="number" min="0" value={String(preferences.salary_min ?? '')} onChange={(event) => setPreferences((current) => ({ ...current, salary_min: event.target.value ? Number(event.target.value) : null }))} /></label>
                  <label>Maximum salary<input type="number" min="0" value={String(preferences.salary_max ?? '')} onChange={(event) => setPreferences((current) => ({ ...current, salary_max: event.target.value ? Number(event.target.value) : null }))} /></label>
                  <label>Salary currency<input maxLength={3} value={String(preferences.salary_currency ?? '')} onChange={(event) => setPreferences((current) => ({ ...current, salary_currency: event.target.value.toUpperCase() || null }))} placeholder="INR / USD / GBP" /></label>
                  <label>Preferred experience level<select value={String(preferences.experience_level ?? '')} onChange={(event) => setPreferences((current) => ({ ...current, experience_level: event.target.value || null }))}><option value="">Any level</option><option value="fresher">Fresher / internship</option><option value="entry_level">Entry-level</option><option value="intermediate">Intermediate</option><option value="experienced">Experienced</option></select></label>
                  <label>Application follow-up interval (days)<input type="number" min="1" max="60" value={String(preferences.application_follow_up_days ?? 7)} onChange={(event) => setPreferences((current) => ({ ...current, application_follow_up_days: Number(event.target.value) }))} /></label>
                  <label>Interview reminder intervals (hours, comma-separated)<input value={((preferences.interview_reminder_hours as number[]) || [24, 1]).join(', ')} onChange={(event) => setPreferences((current) => ({ ...current, interview_reminder_hours: parseList(event.target.value).map(Number).filter(Number.isFinite) }))} placeholder="24, 1" /></label>
                  <label className="career-checkbox"><input type="checkbox" checked={Boolean(preferences.email_reminders)} onChange={(event) => setPreferences((current) => ({ ...current, email_reminders: event.target.checked }))} /> Send reminder emails when SMTP is configured</label>
                  <button className="btn btn-primary" disabled={busy}>Save preferences</button>
                </form>
              </section>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

function SectionIntro({ title, detail }: { title: string; detail: string }) {
  return <div className="career-section-intro"><div><p className="career-eyebrow">YOUR PRIVATE WORKSPACE</p><h2>{title}</h2><p>{detail}</p></div></div>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="career-empty"><div><BriefcaseBusiness size={20} /></div><strong>{title}</strong><p>{detail}</p></div>;
}

function JobCard({
  job, onSave, onUnsave, onApply, onCompare, onDismiss, onTailor, onSimilar, onDeadlineReminder,
}: {
  job: CareerJob;
  onSave?: (job: CareerJob) => void;
  onUnsave?: (job: CareerJob) => void;
  onApply: (job: CareerJob) => void;
  onCompare: (job: CareerJob) => void;
  onDismiss?: (job: CareerJob) => void;
  onTailor: (job: CareerJob) => void;
  onSimilar?: (job: CareerJob) => void;
  onDeadlineReminder?: (job: CareerJob) => void;
}) {
  return (
    <article className="career-job-card">
      <div className="career-job-card-top"><div className="career-company-mark">{job.company_name.slice(0, 1).toUpperCase()}</div><div className="career-job-badges">{job.recommendation_score != null && <span className="career-recommendation-score">{job.recommendation_score}% match</span>}<span className="career-pill">{display(job.source_label, display(job.source, 'Private entry'))}</span></div></div>
      <h3>{job.title}</h3><p className="career-job-company">{job.company_name}</p>
      <div className="career-job-meta"><span><MapPin size={13} /> {display(job.location || job.remote_type || job.country, 'Location not listed')}</span><span>{job.posted_at ? `Posted ${formatDate(job.posted_at)}` : `Saved ${formatDate(job.saved_at)}`}</span></div>
      {(job.remote_type || job.employment_type || job.experience_level) && <p className="career-job-attributes">{[job.remote_type && `work mode inferred: ${job.remote_type.replace('_', ' ')}`, job.employment_type, job.experience_level && `level inferred: ${job.experience_level.replace('_', ' ')}`].filter(Boolean).join(' · ')}</p>}
      {job.expires_at && <p className="career-job-deadline"><CalendarDays size={14} /> Application deadline: {formatDate(job.expires_at)}</p>}
      {(job.salary_min != null || job.salary_max != null) && <p className="career-salary-line"><CircleDollarSign size={14} /> {job.salary_currency || ''} {job.salary_min ?? '—'}–{job.salary_max ?? '—'} {job.salary_period || ''}</p>}
      <p className="career-job-description">{display(job.description, 'Open the source listing to review the complete job description.')}</p>
      {job.recommendation_reason && <p className="career-recommendation-reason">{job.recommendation_reason}</p>}
      {!!job.missing_skills?.length && <p className="career-missing-skills">Missing required skills: {job.missing_skills.slice(0, 5).join(', ')}</p>}
      <div className="career-job-actions">
        {job.original_url && <a className="career-link-button" href={job.original_url} target="_blank" rel="noreferrer">Original listing <ArrowRight size={13} /></a>}
        <button type="button" onClick={() => onCompare(job)}><Target size={14} /> Match resume</button>
        {onSimilar && <button type="button" onClick={() => onSimilar(job)}>Similar roles</button>}
        {job.expires_at && onDeadlineReminder && <button type="button" onClick={() => onDeadlineReminder(job)}><Bell size={14} /> Remind me</button>}
        <button type="button" onClick={() => onApply(job)}><ClipboardList size={14} /> Track</button>
        {onSave && <button type="button" onClick={() => onSave(job)}>Save job</button>}
        {onUnsave && <button type="button" onClick={() => onUnsave(job)}>Remove saved</button>}
        <button type="button" onClick={() => onTailor(job)}><Sparkles size={14} /> Tailor</button>
        {onDismiss && <button type="button" className="career-dismiss-button" onClick={() => onDismiss(job)}>Dismiss</button>}
      </div>
    </article>
  );
}

function MatchPanel({
  result, skillStatuses, onSkillProgress,
}: {
  result: ApiRecord;
  skillStatuses: Record<string, string>;
  onSkillProgress: (skill: string, value: string) => void;
}) {
  const matched = (result.matched_skills as ApiRecord[]) || [];
  const missing = (result.missing_required_skills as string[]) || [];
  const factors = record(result.factors);
  return <section className="career-panel career-match-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">TRANSPARENT RESUME MATCH</p><h2>Compatibility evidence</h2></div><div className="career-score">{String(result.score ?? '—')}<small>/100</small></div></div>
    <p className="career-disclaimer">A deterministic evidence comparison, not a hiring or interview guarantee. Unsupported factors are not scored.</p>
    <div className="career-factor-grid">{Object.entries(factors).map(([name, value]) => { const factor = record(value); return <div className="career-factor" key={name}><span>{name.replace(/_/g, ' ')}</span><strong>{factor.score == null ? 'Not scored' : `${String(factor.score)} / 100`}</strong><small>{display(factor.reason, display(factor.evidence, 'Evidence-based factor'))}</small></div>; })}</div>
    <div className="career-two-columns"><div><h3>Evidence found</h3>{matched.length ? matched.map((skill, index) => <p className="career-skill-positive" key={`${String(skill.skill)}-${index}`}><Check size={14} /> {display(skill.skill as string)}</p>) : <p className="career-muted">No matched skills were identified.</p>}</div><div><h3>Missing required skills</h3>{missing.length ? missing.map((skill) => <label className="career-skill-row" key={skill}><span>{skill}</span><select value={skillStatuses[skill] || 'not_started'} onChange={(event) => onSkillProgress(skill, event.target.value)}><option value="not_started">Not started</option><option value="learning">Learning</option><option value="practiced">Practiced</option><option value="proficient">Proficient</option></select></label>) : <p className="career-muted">No missing required skills detected.</p>}</div></div>
  </section>;
}

function TailoringPanel({
  review, savedVersion, onAccept, onSave, onDownload,
}: {
  review: TailoringReview;
  savedVersion: ApiRecord | null;
  onAccept: (change: TailoringChange, accepted: boolean) => void;
  onSave: () => void;
  onDownload: (format: 'pdf' | 'docx') => void;
}) {
  return <section className="career-panel career-tailoring-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">REVIEW BEFORE APPLYING</p><h2>Tailored resume suggestions · {review.job_title}</h2></div><Sparkles size={20} /></div>
    <p className="career-disclaimer">{review.disclaimer}</p>
    {review.changes.map((change) => <article className="career-change-card" key={change.id}><label className="career-checkbox"><input type="checkbox" checked={change.is_accepted} onChange={(event) => onAccept(change, event.target.checked)} /> Approve this edit</label><p className="career-change-label">{change.section} · {change.rationale}</p><div className="career-change-text"><del>{change.original_text || 'No existing summary'}</del><span>{change.proposed_text}</span></div><small>Verify: {change.what_to_verify}</small></article>)}
    <div className="career-inline-actions"><button type="button" className="btn btn-primary" onClick={onSave} disabled={Boolean(savedVersion)}>Save approved changes as a new version</button>{savedVersion && <><button type="button" className="btn btn-secondary" onClick={() => onDownload('pdf')}>Export PDF</button><button type="button" className="btn btn-secondary" onClick={() => onDownload('docx')}>Export DOCX</button></>}</div>
  </section>;
}

function OverviewSection({
  analytics,
  searchSummary,
  commandCenter,
  notificationPreferences,
  onNotificationPreferencesChange,
  onSaveNotificationPreferences,
  careerScoreWeights,
  onCareerScoreWeightsChange,
  onSaveCareerScoreWeights,
  onMarkNotificationRead,
  onLoadMoreTimeline,
  busy,
  onNavigate,
}: {
  analytics: ApiRecord;
  searchSummary: ApiRecord;
  commandCenter: ApiRecord;
  notificationPreferences: ApiRecord;
  onNotificationPreferencesChange: (value: ApiRecord | ((current: ApiRecord) => ApiRecord)) => void;
  onSaveNotificationPreferences: () => void;
  careerScoreWeights: ApiRecord;
  onCareerScoreWeightsChange: (value: ApiRecord | ((current: ApiRecord) => ApiRecord)) => void;
  onSaveCareerScoreWeights: () => void;
  onMarkNotificationRead: (notificationId: string) => void;
  onLoadMoreTimeline: () => void;
  busy: boolean;
  onNavigate: (section: Section) => void;
}) {
  const application = record(analytics.application_success);
  const careerScore = record(commandCenter.career_score);
  const trust = record(commandCenter.professional_trust);
  const coachRecommendation = record(commandCenter.career_coach);
  const progress = record(commandCenter.progress);
  const profile = record(commandCenter.profile);
  const careerFactors = records(careerScore.factors);
  const trustFactors = records(trust.factors);
  const achievements = records(commandCenter.achievements);
  const goals = records(commandCenter.goals);
  const milestones = records(commandCenter.milestones);
  const opportunities = records(commandCenter.opportunities);
  const timeline = records(commandCenter.timeline);
  const notifications = records(commandCenter.notifications);
  const notificationTypes = [
    { key: 'applications', label: 'Application reminders' },
    { key: 'interviews', label: 'Interview reminders' },
    { key: 'deadlines', label: 'Job deadline reminders' },
  ];
  const careerWeightsTotal = CAREER_SCORE_WEIGHT_FIELDS.reduce(
    (total, field) => total + Number(careerScoreWeights[field.key] || 0),
    0,
  );
  const metrics = [
    { label: 'Saved opportunities', value: progress.saved_jobs ?? searchSummary.jobs_saved ?? 0, icon: <BriefcaseBusiness size={17} /> },
    { label: 'Applications tracked', value: progress.applications ?? searchSummary.jobs_applied ?? 0, icon: <ClipboardList size={17} /> },
    { label: 'Skills tracked', value: progress.tracked_skills ?? 0, icon: <Target size={17} /> },
    { label: 'Learning completions', value: progress.completed_learning ?? 0, icon: <GraduationCap size={17} /> },
    { label: 'Milestones reached', value: progress.completed_milestones ?? 0, icon: <Check size={17} /> },
    { label: 'Learning streak', value: `${String(record(progress.learning_streak).current_days ?? 0)} days`, icon: <Activity size={17} /> },
  ];
  const updatePreference = (key: string, value: boolean) => {
    onNotificationPreferencesChange((current) => ({ ...current, [key]: value }));
  };
  return <><section className="career-welcome"><div><p className="career-eyebrow">YOUR PREMIUM CAREER COMMAND CENTER</p><h2>One view of your career progress.</h2><p>Resume profile: {display(profile.primary_resume_title, 'No resume saved')} · {String(profile.documented_skills ?? 0)} documented skills · {String(progress.active_goals ?? 0)} active goals</p>{(Array.isArray(profile.target_roles) && profile.target_roles.length > 0 || Boolean(profile.career_goals)) && <p>Career direction: {Array.isArray(profile.target_roles) ? profile.target_roles.map(String).join(', ') : ''}{Array.isArray(profile.target_roles) && profile.target_roles.length > 0 && Boolean(profile.career_goals) ? ' · ' : ''}{typeof profile.career_goals === 'string' ? profile.career_goals : ''}</p>}{Array.isArray(profile.top_skills) && profile.top_skills.length > 0 && <div className="career-profile-skill-list" aria-label="Skills documented in the selected resume">{profile.top_skills.slice(0, 8).map((skill) => <span key={String(skill)}>{String(skill)}</span>)}</div>}<div className="career-inline-actions"><button type="button" className="btn btn-primary" onClick={() => onNavigate('discover')}>Explore opportunities <ArrowRight size={15} /></button><button type="button" className="btn btn-secondary" onClick={() => onNavigate('profile')}>Edit professional profile</button><button type="button" className="btn btn-secondary" onClick={() => onNavigate('branding')}>Open portfolio tools</button></div></div><div className="career-welcome-mark"><Sparkles size={38} /></div></section>
    <div className="career-metric-grid">{metrics.map((metric) => <article className="career-metric-card" key={metric.label}><div>{metric.icon}</div><span>{metric.label}</span><strong>{String(metric.value)}</strong></article>)}</div>
    <div className="career-two-columns career-command-scores">
      <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">EXPLAINABLE CAREER SCORE</p><h2>{String(careerScore.value ?? 0)} / {String(careerScore.maximum ?? 100)}</h2></div><Target size={20} /></div><p className="career-disclaimer">{display(careerScore.disclaimer)}</p>{careerFactors.map((factor) => <div className="career-command-factor" key={String(factor.factor)}><span>{String(factor.factor)}</span><strong>{String(factor.points)}/{String(factor.weight)}</strong><small>{String(factor.evidence)}</small></div>)}<div className="career-score-settings"><h3>Customize factor weights · {careerWeightsTotal}/100</h3>{CAREER_SCORE_WEIGHT_FIELDS.map((field) => <label key={field.key}><span>{field.label}</span><input type="number" min="0" max="100" step="1" value={Number(careerScoreWeights[field.key] || 0)} onChange={(event) => onCareerScoreWeightsChange((current) => ({ ...current, [field.key]: Number(event.target.value) }))} /></label>)}<button type="button" className="btn btn-secondary" disabled={busy || careerWeightsTotal !== 100} onClick={onSaveCareerScoreWeights}>Save score weights</button><small>Weights must total 100. The score remains profile/activity completeness—not employability.</small></div></section>
      <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">PROFESSIONAL TRUST</p><h2>Evidence traceability · {String(trust.value ?? 0)}/100</h2></div><ShieldCheck size={20} /></div><p className="career-disclaimer">{display(trust.disclaimer)}</p>{trustFactors.map((factor) => <div className="career-command-factor" key={String(factor.factor)}><span>{String(factor.factor)}</span><strong>{String(factor.count)} recorded</strong><small>{String(factor.points)} indicator points</small></div>)}<button type="button" className="career-link-button" onClick={() => onNavigate('academy')}>Review skills evidence <ArrowRight size={14} /></button></section>
    </div>
    <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">AI CAREER COACH DASHBOARD</p><h2>Your saved career guidance</h2></div><button type="button" className="career-link-button" onClick={() => onNavigate('coach')}>Open Career Coach <ArrowRight size={14} /></button></div>{coachRecommendation.summary ? <><p className="career-muted">{String(coachRecommendation.summary)}</p>{Array.isArray(coachRecommendation.action_plan) && coachRecommendation.action_plan.slice(0, 3).map((action, index) => <p className="career-command-item" key={index}>{typeof action === 'string' ? action : display(record(action).action, display(record(action).title, 'Recommended action'))}</p>)}<p className="career-disclaimer">From your saved roadmap · updated {formatDate(String(coachRecommendation.updated_at))}</p></> : <p className="career-muted">Generate a personalized roadmap in Career Coach to surface saved guidance here. No recommendation is invented for an empty profile.</p>}</section>
    <section className="career-panel career-command-links"><div className="career-panel-heading"><div><p className="career-eyebrow">CONNECTED WORKSPACES</p><h2>Continue your career plan</h2></div></div><div className="career-quick-links"><button type="button" onClick={() => onNavigate('coach')}><Compass size={17} /><span>Career coach and roadmaps</span><ArrowRight size={14} /></button><button type="button" onClick={() => onNavigate('academy')}><GraduationCap size={17} /><span>Learning and skill evidence</span><ArrowRight size={14} /></button><button type="button" onClick={() => onNavigate('branding')}><Share2 size={17} /><span>Portfolio and professional brand</span><ArrowRight size={14} /></button><button type="button" onClick={() => onNavigate('analytics')}><TrendingUp size={17} /><span>Career analytics</span><ArrowRight size={14} /></button></div></section>
    <div className="career-two-columns">
      <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">EARNED FROM RECORDED ACTIVITY</p><h2>Achievements</h2></div><span className="career-count">{achievements.length}</span></div>{achievements.length ? achievements.map((item) => <article className="career-command-item" key={String(item.achievement_key)}><strong><Check size={14} /> {String(item.title)}</strong><span>{String(item.description)}</span><small>{String(item.evidence)} · {formatDate(String(item.awarded_at))}</small></article>) : <p className="career-muted">Achievements appear when recorded activity reaches a defined milestone. Nothing is awarded from unverified or mock activity.</p>}</section>
      <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">CAREER ROADMAP</p><h2>Goals and next milestones</h2></div><button type="button" className="career-link-button" onClick={() => onNavigate('coach')}>Manage <ArrowRight size={14} /></button></div>{goals.map((goal, index) => <article className="career-command-item" key={`${String(goal.goal_type)}-${index}`}><strong>{display(goal.title, 'Career goal')} · {String(goal.progress ?? 0)}%</strong><span>{String(goal.goal_type).replaceAll('_', ' ')}{goal.target_date ? ` · target ${formatDate(String(goal.target_date))}` : ''}</span></article>)}{milestones.map((milestone, index) => <article className="career-command-item" key={`milestone-${index}`}><strong>{display(milestone.title, 'Career milestone')}</strong><span>{String(milestone.status).replaceAll('_', ' ')}{milestone.due_date ? ` · due ${formatDate(String(milestone.due_date))}` : ''}</span></article>)}{goals.length + milestones.length === 0 && <p className="career-muted">Create a goal or roadmap milestone in Career Coach to track progress here.</p>}</section>
    </div>
    <div className="career-two-columns">
      <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">PERSONALIZED OPPORTUNITIES</p><h2>Recommended jobs</h2></div><button type="button" className="career-link-button" onClick={() => onNavigate('discover')}>Find opportunities <ArrowRight size={14} /></button></div>{opportunities.length ? opportunities.map((job) => <article className="career-command-item" key={String(job.id)}><strong>{String(job.title)} · {String(job.company_name)}</strong><span>{String(job.location || 'Location not provided')} · {String(job.match_score)} match evidence · {String(job.source)}{job.remote_type ? ` · ${String(job.remote_type)}` : ''}{job.employment_type ? ` · ${String(job.employment_type)}` : ''}</span>{job.salary_min != null && job.salary_max != null && <small>Source-reported salary: {String(job.salary_currency || '')} {String(job.salary_min)}–{String(job.salary_max)}</small>}{Boolean(job.url) && <a className="career-link-button" href={String(job.url)} target="_blank" rel="noreferrer">View original listing <ArrowRight size={13} /></a>}</article>) : <p className="career-muted">No current recommendations are stored yet. Search configured job providers to build a feed from real listings.</p>}</section>
      <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">CAREER PROGRESS TIMELINE</p><h2>Career activity</h2></div><span className="career-count">{timeline.length} loaded</span></div>{timeline.length ? timeline.map((item, index) => <article className="career-command-item career-timeline-item" key={`${String(item.type)}-${String(item.occurred_at)}-${index}`}><strong>{String(item.title)}</strong><span>{String(item.detail)}</span><small>{formatDate(String(item.occurred_at))}</small></article>) : <p className="career-muted">Your saved career activities and completed milestones will appear here in chronological order.</p>}{Boolean(commandCenter.timeline_has_more) && <button type="button" className="btn btn-secondary" disabled={busy} onClick={onLoadMoreTimeline}>Load older activity</button>}</section>
    </div>
    <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">PERSONALIZED NOTIFICATIONS</p><h2>Choose reminder channels</h2></div><Bell size={18} /></div><p className="career-disclaimer">Email reminders also require that email was requested for the individual reminder and that email delivery is configured.</p><div className="career-notification-grid">{notificationTypes.map((item) => <div className="career-notification-row" key={item.key}><strong>{item.label}</strong>{(['in_app', 'email'] as const).map((channel) => { const key = `${channel}_${item.key}`; return <label key={key}><input type="checkbox" checked={notificationPreferences[key] !== false} onChange={(event) => updatePreference(key, event.target.checked)} /> {channel === 'in_app' ? 'In app' : 'Email'}</label>; })}</div>)}</div><button type="button" className="btn btn-secondary" disabled={busy} onClick={onSaveNotificationPreferences}>Save notification preferences</button>{notifications.length > 0 && <div className="career-notification-list"><h3>Recent notifications · {String(progress.unread_notifications ?? 0)} unread</h3>{notifications.map((item, index) => <article className="career-command-item" key={`${String(item.created_at)}-${index}`}><strong>{String(item.message)}</strong><small>{item.read ? 'Read' : 'Unread'} · {formatDate(String(item.created_at))}</small>{!item.read && <button type="button" className="career-link-button" disabled={busy} onClick={() => onMarkNotificationRead(String(item.id))}>Mark as read</button>}</article>)}</div>}</section>
    <section className="career-panel"><div className="career-panel-heading"><div><p className="career-eyebrow">APPLICATION OUTCOMES</p><h2>Success analytics</h2></div><button type="button" className="career-link-button" onClick={() => onNavigate('analytics')}>View analytics <ArrowRight size={14} /></button></div>
      <div className="career-outcome-grid"><Outcome label="Application → interview" value={record(application.application_to_interview)} /><Outcome label="Interview → offer" value={record(application.interview_to_offer)} /><Outcome label="Overall response" value={record(application.overall_response_rate)} /><Outcome label="Rejection rate" value={record(application.rejection_rate)} /></div>
      <p className="career-disclaimer">Rates use completed outcomes only. Pending applications are excluded, and the dashboard identifies small samples.</p>
    </section>
  </>;
}

function Outcome({ label, value }: { label: string; value: ApiRecord }) {
  const rate = value.rate_percent;
  return <div className="career-outcome"><span>{label}</span><strong>{rate == null ? '—' : `${String(rate)}%`}</strong><small>{String(value.numerator ?? 0)} of {String(value.denominator ?? 0)} completed applications{value.message ? ` · ${String(value.message)}` : ''}</small></div>;
}

function MarketDemandSection({ data }: { data: ApiRecord }) {
  const skills = records(data.skills);
  const roles = records(data.roles);
  const industries = records(data.industries);
  return <section className="career-market-demand">
    <div><p className="career-eyebrow">LISTING-BASED MARKET SIGNAL</p><h3>Recent demand sample</h3><span>{String(data.sample_size ?? 0)} dated listings · last {String(data.window_days ?? 30)} days</span></div>
    <div className="career-market-columns">
      <div><strong>Frequently listed skills</strong>{skills.length ? skills.slice(0, 6).map((item) => <span key={String(item.name)}>{String(item.name)} · {String(item.postings)}</span>) : <small>No skill sample yet.</small>}</div>
      <div><strong>Common roles</strong>{roles.length ? roles.slice(0, 6).map((item) => <span key={String(item.name)}>{String(item.name)} · {String(item.postings)}</span>) : <small>No role sample yet.</small>}</div>
      {industries.length > 0 && <div><strong>Provider categories</strong>{industries.slice(0, 6).map((item) => <span key={String(item.name)}>{String(item.name)} · {String(item.postings)}</span>)}</div>}
    </div>
    <p className="career-disclaimer">{display(data.disclaimer, 'Counts come only from the available authorized listing sample and are not a complete labor-market census.')}</p>
  </section>;
}

function AnalyticsSection({ analytics, searchSummary }: { analytics: ApiRecord; searchSummary: ApiRecord }) {
  const application = record(analytics.application_success);
  const missing = record(searchSummary.missing_skills);
  const performanceByRole = records(application.performance_by_role);
  const performanceByCompany = records(application.performance_by_company);
  return <><SectionIntro title="Performance, not vanity metrics" detail="Every number below is derived from your saved searches, matches, saved jobs, and application events." />
    <div className="career-outcome-grid career-outcome-grid-large"><Outcome label="Application-to-interview rate" value={record(application.application_to_interview)} /><Outcome label="Interview-to-offer rate" value={record(application.interview_to_offer)} /><Outcome label="Overall response rate" value={record(application.overall_response_rate)} /><Outcome label="Rejection rate" value={record(application.rejection_rate)} /></div>
    <div className="career-metric-grid">{[['Jobs discovered', searchSummary.jobs_discovered], ['Jobs saved', searchSummary.jobs_saved], ['Jobs applied', searchSummary.jobs_applied], ['Match sample size', searchSummary.match_sample_size]].map(([label, value]) => <article className="career-metric-card" key={String(label)}><span>{String(label)}</span><strong>{value == null ? '0' : String(value)}</strong></article>)}</div>
    <div className="career-two-columns"><section className="career-panel"><p className="career-eyebrow">SKILL GAP SIGNALS</p><h2>Frequently missing required skills</h2>{Object.keys(missing).length ? Object.entries(missing).sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, 15).map(([skill, count]) => <div className="career-bar-row" key={skill}><span>{skill}</span><div><i style={{ width: `${Math.min(100, Number(count) * 12)}%` }} /></div><strong>{String(count)}</strong></div>) : <p className="career-muted">Match jobs against a saved resume to build skill-gap insights.</p>}</section>
      <section className="career-panel"><p className="career-eyebrow">INTERPRETATION</p><h2>Read the denominators</h2><p className="career-muted">{String(application.rate_definitions ? JSON.stringify(application.rate_definitions) : 'Pending applications do not count as rejections. Insufficient sample sizes are labeled by the API.')}</p><p className="career-disclaimer">Analytics describe activity in this account. They do not predict future hiring outcomes.</p></section></div>
    <div className="career-two-columns"><PerformanceList title="Performance by role" rows={performanceByRole} /><PerformanceList title="Performance by company" rows={performanceByCompany} /></div>
  </>;
}

function PerformanceList({ title, rows }: { title: string; rows: ApiRecord[] }) {
  return <section className="career-panel"><p className="career-eyebrow">COMPLETED APPLICATIONS ONLY</p><h2>{title}</h2>{rows.length ? rows.map((row) => {
    const interviewRate = record(row.application_to_interview);
    const offerRate = record(row.interview_to_offer);
    return <div className="career-performance-row" key={String(row.name)}><strong>{String(row.name)}</strong><span>{String(row.applications)} tracked</span><small>{String(row.completed_outcomes)} completed · interview {interviewRate.rate_percent == null ? '—' : `${String(interviewRate.rate_percent)}%`} · interview-to-offer {offerRate.rate_percent == null ? '—' : `${String(offerRate.rate_percent)}%`}</small></div>;
  }) : <p className="career-muted">Add application outcomes to compare performance.</p>}</section>;
}
