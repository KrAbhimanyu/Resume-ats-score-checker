package com.resumeats.checker.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.resumeats.checker.data.AcademyAssessmentRequest
import com.resumeats.checker.data.AcademyEvidenceRequest
import com.resumeats.checker.data.AcademyExerciseRequest
import com.resumeats.checker.data.AcademyProjectRequest
import com.resumeats.checker.data.AcademyRoadmapRequest
import com.resumeats.checker.data.AnalysisResponse
import com.resumeats.checker.data.ApplicationCreateRequest
import com.resumeats.checker.data.ApplicationEditRequest
import com.resumeats.checker.data.ApplicationUpdateRequest
import com.resumeats.checker.data.BrandGenerateRequest
import com.resumeats.checker.data.BrandVersionCreateRequest
import com.resumeats.checker.data.BrandVersionEditRequest
import com.resumeats.checker.data.BusinessPlan
import com.resumeats.checker.data.BusinessStatus
import com.resumeats.checker.data.CareerApplication
import com.resumeats.checker.data.CareerChatRequest
import com.resumeats.checker.data.CareerGoalRequest
import com.resumeats.checker.data.CareerGoalUpdateRequest
import com.resumeats.checker.data.CareerMilestoneUpdateRequest
import com.resumeats.checker.data.CareerRepository
import com.resumeats.checker.data.CareerRoadmapRequest
import com.resumeats.checker.data.CreditAccount
import com.resumeats.checker.data.InterviewCreateRequest
import com.resumeats.checker.data.InterviewEditRequest
import com.resumeats.checker.data.JobListing
import com.resumeats.checker.data.JobMatchRequest
import com.resumeats.checker.data.JobSearchRequest
import com.resumeats.checker.data.PersonalBrandProfile
import com.resumeats.checker.data.ReminderCreateRequest
import com.resumeats.checker.data.ReminderEditRequest
import com.resumeats.checker.data.ResumeProfile
import com.resumeats.checker.data.SalaryBenchmarks
import com.resumeats.checker.data.SalaryCalculatorRequest
import com.resumeats.checker.data.SalaryNegotiationRequest
import com.resumeats.checker.data.SalaryOfferComparisonRequest
import com.resumeats.checker.data.SalaryOfferRequest
import com.resumeats.checker.data.SearchPreferences
import com.resumeats.checker.data.SessionStore
import com.resumeats.checker.data.TailoringApprovalRequest
import com.resumeats.checker.data.UserSummary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.decodeFromJsonElement
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject

data class CareerUiState(
    val initializing: Boolean = true,
    val busy: Boolean = false,
    val user: UserSummary? = null,
    val error: String? = null,
    val notice: String? = null,
    val analysis: AnalysisResponse? = null,
    val analysisFileName: String? = null,
    val resumes: List<ResumeProfile> = emptyList(),
    val dashboard: JsonObject? = null,
    val jobs: List<JobListing> = emptyList(),
    val savedJobs: Set<String> = emptySet(),
    val savedJobListings: List<JobListing> = emptyList(),
    val jobPage: Int = 1,
    val jobsHaveMore: Boolean = false,
    val jobMatch: JsonObject? = null,
    val jobMatchId: String? = null,
    val tailoringReview: JsonObject? = null,
    val tailoringJobId: String? = null,
    val tailoredResumeVersion: JsonObject? = null,
    val applications: List<CareerApplication> = emptyList(),
    val applicationHistory: List<JsonObject> = emptyList(),
    val interviews: List<JsonObject> = emptyList(),
    val interviewHistory: List<JsonObject> = emptyList(),
    val reminders: JsonObject? = null,
    val preferences: SearchPreferences? = null,
    val coach: JsonObject? = null,
    val coachReply: JsonObject? = null,
    val academy: JsonObject? = null,
    val academyTrack: JsonObject? = null,
    val academyRoadmaps: List<JsonObject> = emptyList(),
    val academyProjects: List<JsonObject> = emptyList(),
    val academyAssistantHistory: List<JsonObject> = emptyList(),
    val academyAssistantReply: JsonObject? = null,
    val academyResult: JsonObject? = null,
    val branding: JsonObject? = null,
    val brandVersions: List<JsonObject> = emptyList(),
    val brandDraft: JsonObject? = null,
    val salary: SalaryBenchmarks? = null,
    val salaryOffers: List<JsonObject> = emptyList(),
    val salaryComparisons: List<JsonObject> = emptyList(),
    val salaryCalculation: JsonObject? = null,
    val salaryGuidance: JsonObject? = null,
    val plans: List<BusinessPlan> = emptyList(),
    val businessStatus: BusinessStatus? = null,
    val credits: CreditAccount? = null,
    val entitlements: JsonObject? = null,
)

class CareerViewModel(
    private val repository: CareerRepository,
    private val sessionStore: SessionStore,
) : ViewModel() {
    private val mutableState = MutableStateFlow(CareerUiState())
    val state: StateFlow<CareerUiState> = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            runRequest {
                val user = repository.restoreSession()
                mutableState.value = mutableState.value.copy(initializing = false, user = user)
                if (user != null) refreshDashboardData()
            }
        }
    }

    fun authenticate(email: String, password: String, register: Boolean) {
        viewModelScope.launch {
            runRequest {
                val response = repository.authenticate(email, password, register)
                mutableState.value = mutableState.value.copy(
                    user = response.user,
                    notice = "Signed in as ${response.user.email}.",
                )
                refreshDashboardData()
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            runRequest {
                try {
                    repository.logout()
                } finally {
                    mutableState.value = CareerUiState(initializing = false, notice = "You have signed out.")
                }
            }
        }
    }

    fun analyze(fileName: String, bytes: ByteArray, jobDescription: String) {
        viewModelScope.launch {
            runRequest {
                val report = repository.analyze(fileName, bytes, jobDescription)
                mutableState.value = mutableState.value.copy(
                    analysis = report,
                    analysisFileName = fileName,
                    notice = "Resume analysis completed. The uploaded file was processed by the API.",
                )
            }
        }
    }

    fun refreshResumes() {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(resumes = repository.resumes()) }
        }
    }

    fun uploadResume(fileName: String, bytes: ByteArray) {
        viewModelScope.launch {
            runRequest {
                repository.uploadResume(fileName, bytes)
                mutableState.value = mutableState.value.copy(
                    resumes = repository.resumes(),
                    notice = "Resume saved to your encrypted career profile.",
                )
            }
        }
    }

    fun searchJobs(query: String, location: String, country: String, page: Int = 1) {
        viewModelScope.launch {
            runRequest {
                val response = repository.discover(
                    JobSearchRequest(query = query, location = location, country = country, page = page),
                )
                mutableState.value = mutableState.value.copy(
                    jobs = if (page == 1) response.jobs else mutableState.value.jobs + response.jobs,
                    jobPage = response.page,
                    jobsHaveMore = response.hasMore,
                    notice = response.warnings.takeIf { it.isNotEmpty() }?.joinToString("\n")
                        ?: if (response.jobs.isEmpty()) "No listings were returned by the configured job providers." else null,
                )
            }
        }
    }

    fun refreshSavedJobs() {
        viewModelScope.launch {
            runRequest {
                val listings = repository.savedJobs()
                mutableState.value = mutableState.value.copy(
                    savedJobListings = listings,
                    savedJobs = listings.map { it.id }.toSet(),
                )
            }
        }
    }

    fun saveJob(job: JobListing) {
        viewModelScope.launch {
            runRequest {
                repository.saveJob(job.id)
                mutableState.value = mutableState.value.copy(
                    savedJobs = mutableState.value.savedJobs + job.id,
                    savedJobListings = (mutableState.value.savedJobListings + job).distinctBy { it.id },
                    notice = "Saved ${job.title}.",
                )
            }
        }
    }

    fun refreshCareer() {
        viewModelScope.launch {
            runRequest {
                val coach = repository.coachState()
                val academy = repository.academyDashboard()
                val preferences = repository.preferences().objectValue("preferences")
                mutableState.value = mutableState.value.copy(
                    applications = repository.applications(),
                    coach = coach,
                    academy = academy,
                    interviews = repository.interviews(),
                    reminders = repository.reminders(),
                    preferences = Json.decodeFromJsonElement<SearchPreferences>(preferences),
                    academyRoadmaps = repository.academyRoadmaps(),
                    academyProjects = repository.academyProjects(),
                    branding = repository.brandingDashboard(),
                    brandVersions = repository.brandVersions(),
                    salaryOffers = repository.salaryOffers(),
                )
            }
        }
    }

    fun addApplication(title: String, company: String, jobId: String? = null, location: String = "") {
        viewModelScope.launch {
            runRequest {
                repository.createApplication(
                    ApplicationCreateRequest(jobId = jobId, title = title, companyName = company, location = location),
                )
                mutableState.value = mutableState.value.copy(
                    applications = repository.applications(),
                    notice = "Application added to your tracker.",
                )
            }
        }
    }

    fun updateApplication(applicationId: String, status: String) {
        viewModelScope.launch {
            runRequest {
                repository.updateApplication(applicationId, ApplicationUpdateRequest(status))
                mutableState.value = mutableState.value.copy(
                    applications = repository.applications(),
                    notice = "Application status updated.",
                )
            }
        }
    }

    fun saveApplicationNotes(applicationId: String, notes: String) {
        viewModelScope.launch {
            runRequest {
                repository.editApplication(applicationId, ApplicationEditRequest(notes = notes))
                mutableState.value = mutableState.value.copy(
                    applications = repository.applications(),
                    notice = "Application notes saved.",
                )
            }
        }
    }

    fun loadApplicationHistory(applicationId: String) {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(applicationHistory = repository.applicationHistory(applicationId)) }
        }
    }

    fun loadInterviewHistory(interviewId: String) {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(interviewHistory = repository.interviewHistory(interviewId)) }
        }
    }

    fun scheduleInterview(body: InterviewCreateRequest) {
        viewModelScope.launch {
            runRequest {
                repository.createInterview(body)
                mutableState.value = mutableState.value.copy(
                    interviews = repository.interviews(),
                    reminders = repository.reminders(),
                    applications = repository.applications(),
                    notice = "Interview scheduled. Server-configured interview reminders were also created.",
                )
            }
        }
    }

    fun updateInterview(id: String, body: InterviewEditRequest) {
        viewModelScope.launch {
            runRequest {
                repository.updateInterview(id, body)
                mutableState.value = mutableState.value.copy(interviews = repository.interviews())
            }
        }
    }

    fun addReminder(body: ReminderCreateRequest) {
        viewModelScope.launch {
            runRequest {
                repository.createReminder(body)
                mutableState.value = mutableState.value.copy(reminders = repository.reminders(), notice = "Reminder saved.")
            }
        }
    }

    fun updateReminder(id: String, body: ReminderEditRequest) {
        viewModelScope.launch {
            runRequest {
                repository.updateReminder(id, body)
                mutableState.value = mutableState.value.copy(reminders = repository.reminders())
            }
        }
    }

    fun savePreferences(preferences: SearchPreferences) {
        viewModelScope.launch {
            runRequest {
                repository.savePreferences(preferences)
                mutableState.value = mutableState.value.copy(preferences = preferences, notice = "Account preferences saved.")
            }
        }
    }

    fun addCareerGoal(title: String, targetRole: String, description: String) {
        viewModelScope.launch {
            runRequest {
                repository.createGoal(CareerGoalRequest(title, description, targetRole))
                mutableState.value = mutableState.value.copy(coach = repository.coachState(), notice = "Career goal saved.")
            }
        }
    }

    fun updateCareerGoal(goalId: String, status: String, progress: Double) {
        viewModelScope.launch {
            runRequest {
                repository.updateGoal(goalId, CareerGoalUpdateRequest(status, progress))
                mutableState.value = mutableState.value.copy(coach = repository.coachState(), notice = "Career goal updated.")
            }
        }
    }

    fun sendCoachMessage(message: String, roadmapId: String? = null) {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    coachReply = repository.coachChat(CareerChatRequest(message, roadmapId)),
                    coach = repository.coachState(),
                )
            }
        }
    }

    fun generateRoadmap(body: CareerRoadmapRequest) {
        viewModelScope.launch {
            runRequest {
                val roadmap = repository.generateCareerRoadmap(body)
                mutableState.value = mutableState.value.copy(
                    coach = repository.coachState(),
                    coachReply = roadmap,
                    notice = "Career roadmap generated and saved to your account.",
                )
            }
        }
    }

    fun updateMilestone(id: String, status: String) {
        viewModelScope.launch {
            runRequest {
                repository.updateMilestone(id, CareerMilestoneUpdateRequest(status))
                mutableState.value = mutableState.value.copy(coach = repository.coachState())
            }
        }
    }

    fun setCoachConsent(enabled: Boolean) {
        viewModelScope.launch {
            runRequest {
                repository.setCoachConsent(enabled)
                mutableState.value = mutableState.value.copy(
                    coach = repository.coachState(),
                    notice = if (enabled) "AI profile-sharing consent enabled." else "AI profile-sharing consent disabled.",
                )
            }
        }
    }

    fun matchJob(jobId: String) {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    jobMatch = repository.matchJob(JobMatchRequest(jobId = jobId)),
                    jobMatchId = jobId,
                    tailoringReview = null,
                    tailoringJobId = null,
                    tailoredResumeVersion = null,
                )
            }
        }
    }

    fun tailorResume(jobId: String, resumeId: String?) {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    tailoringReview = repository.tailorResume(jobId, resumeId),
                    tailoringJobId = jobId,
                    tailoredResumeVersion = null,
                )
            }
        }
    }

    fun updateTailoringReview(sessionId: String, body: TailoringApprovalRequest) {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    tailoringReview = repository.updateTailoringReview(sessionId, body),
                )
            }
        }
    }

    fun saveTailoredVersion(sessionId: String) {
        viewModelScope.launch {
            runRequest {
                val version = repository.saveTailoredVersion(sessionId)
                mutableState.value = mutableState.value.copy(
                    tailoredResumeVersion = version,
                    resumes = repository.resumes(),
                    notice = "Approved edits saved as a new resume version; the original resume remains unchanged.",
                )
            }
        }
    }

    fun loadSalary(role: String, location: String) {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(salary = repository.salaryIntelligence(role, location)) }
        }
    }

    fun refreshSalaryOffers() {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    salaryOffers = repository.salaryOffers(),
                    salaryComparisons = repository.salaryComparisons(),
                )
            }
        }
    }

    fun createSalaryOffer(body: SalaryOfferRequest) {
        viewModelScope.launch {
            runRequest {
                repository.createSalaryOffer(body)
                mutableState.value = mutableState.value.copy(salaryOffers = repository.salaryOffers(), notice = "Offer saved securely.")
            }
        }
    }

    fun editSalaryOffer(id: String, body: SalaryOfferRequest) {
        viewModelScope.launch {
            runRequest {
                repository.updateSalaryOffer(id, body)
                mutableState.value = mutableState.value.copy(
                    salaryOffers = repository.salaryOffers(),
                    notice = "Saved offer updated.",
                )
            }
        }
    }

    fun deleteSalaryOffer(id: String) {
        viewModelScope.launch {
            runRequest {
                repository.deleteSalaryOffer(id)
                mutableState.value = mutableState.value.copy(
                    salaryOffers = repository.salaryOffers(),
                    notice = "Saved offer removed.",
                )
            }
        }
    }

    fun createSalaryComparison(body: SalaryOfferComparisonRequest) {
        viewModelScope.launch {
            runRequest {
                repository.createSalaryComparison(body)
                mutableState.value = mutableState.value.copy(
                    salaryComparisons = repository.salaryComparisons(),
                    notice = "Offer comparison saved.",
                )
            }
        }
    }

    fun updateSalaryComparison(id: String, body: SalaryOfferComparisonRequest) {
        viewModelScope.launch {
            runRequest {
                repository.updateSalaryComparison(id, body)
                mutableState.value = mutableState.value.copy(
                    salaryComparisons = repository.salaryComparisons(),
                    notice = "Saved comparison updated.",
                )
            }
        }
    }

    fun deleteSalaryComparison(id: String) {
        viewModelScope.launch {
            runRequest {
                repository.deleteSalaryComparison(id)
                mutableState.value = mutableState.value.copy(
                    salaryComparisons = repository.salaryComparisons(),
                    notice = "Saved comparison removed.",
                )
            }
        }
    }

    fun calculateSalary(body: SalaryCalculatorRequest) {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(salaryCalculation = repository.calculateSalary(body)) }
        }
    }

    fun requestSalaryGuidance(body: SalaryNegotiationRequest) {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(salaryGuidance = repository.salaryNegotiation(body)) }
        }
    }

    fun refreshBranding() {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    branding = repository.brandingDashboard(),
                    brandVersions = repository.brandVersions(),
                )
            }
        }
    }

    fun saveBrandProfile(profile: PersonalBrandProfile) {
        viewModelScope.launch {
            runRequest {
                repository.saveBrandProfile(profile)
                mutableState.value = mutableState.value.copy(branding = repository.brandingDashboard(), notice = "Brand profile saved.")
            }
        }
    }

    fun generateBrandContent(body: BrandGenerateRequest) {
        viewModelScope.launch {
            runRequest {
                val draft = repository.generateBrandContent(body)
                mutableState.value = mutableState.value.copy(
                    brandDraft = draft,
                    brandVersions = repository.brandVersions(),
                    notice = "Draft generated and saved. Review for accuracy before using it.",
                )
            }
        }
    }

    fun saveBrandVersion(body: BrandVersionCreateRequest) {
        viewModelScope.launch {
            runRequest {
                repository.createBrandVersion(body)
                mutableState.value = mutableState.value.copy(brandVersions = repository.brandVersions(), notice = "Brand content version saved.")
            }
        }
    }

    fun editBrandVersion(id: String, body: BrandVersionEditRequest) {
        viewModelScope.launch {
            runRequest {
                repository.editBrandVersion(id, body)
                mutableState.value = mutableState.value.copy(brandVersions = repository.brandVersions())
            }
        }
    }

    fun loadAcademyTrack(trackId: String) {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(academyTrack = repository.academyTrack(trackId)) }
        }
    }

    fun completeAcademyLesson(trackId: String, lessonId: String) {
        viewModelScope.launch {
            runRequest {
                repository.completeLesson(trackId, lessonId)
                mutableState.value = mutableState.value.copy(
                    academyTrack = repository.academyTrack(trackId),
                    academy = repository.academyDashboard(),
                    notice = "Lesson progress saved.",
                )
            }
        }
    }

    fun submitAcademyAssessment(trackId: String, answers: Map<String, String>) {
        viewModelScope.launch {
            runRequest {
                val result = repository.submitAssessment(trackId, AcademyAssessmentRequest(answers))
                mutableState.value = mutableState.value.copy(
                    academyResult = result,
                    academyTrack = repository.academyTrack(trackId),
                    academy = repository.academyDashboard(),
                )
            }
        }
    }

    fun submitAcademyExercise(trackId: String, exerciseId: String, code: String) {
        viewModelScope.launch {
            runRequest {
                val result = repository.submitExercise(trackId, exerciseId, AcademyExerciseRequest(code))
                mutableState.value = mutableState.value.copy(
                    academyResult = result,
                    academyTrack = repository.academyTrack(trackId),
                    academy = repository.academyDashboard(),
                )
            }
        }
    }

    fun refreshAcademyDetails() {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    academy = repository.academyDashboard(),
                    academyRoadmaps = repository.academyRoadmaps(),
                    academyProjects = repository.academyProjects(),
                    academyAssistantHistory = repository.academyAssistantHistory(),
                )
            }
        }
    }

    fun loadAcademyAssistantHistory() {
        viewModelScope.launch {
            runRequest { mutableState.value = mutableState.value.copy(academyAssistantHistory = repository.academyAssistantHistory()) }
        }
    }

    fun askAcademyAssistant(message: String, trackId: String?) {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    academyAssistantReply = repository.academyAssistant(message, trackId),
                    academyAssistantHistory = repository.academyAssistantHistory(),
                )
            }
        }
    }

    fun generateAcademyRoadmap(body: AcademyRoadmapRequest) {
        viewModelScope.launch {
            runRequest {
                repository.generateAcademyRoadmap(body)
                mutableState.value = mutableState.value.copy(academyRoadmaps = repository.academyRoadmaps())
            }
        }
    }

    fun submitAcademyProject(body: AcademyProjectRequest) {
        viewModelScope.launch {
            runRequest {
                val result = repository.evaluateProject(body)
                mutableState.value = mutableState.value.copy(
                    academyResult = result,
                    academyProjects = repository.academyProjects(),
                    notice = "Description-only project review saved. It did not inspect the submitted project URL.",
                )
            }
        }
    }

    fun submitAcademyEvidence(body: AcademyEvidenceRequest) {
        viewModelScope.launch {
            runRequest {
                repository.submitSkillEvidence(body)
                mutableState.value = mutableState.value.copy(
                    academy = repository.academyDashboard(),
                    notice = "Evidence saved as user-submitted.",
                )
            }
        }
    }

    fun issueAcademyCertificate(trackId: String) {
        viewModelScope.launch {
            runRequest {
                val certificate = repository.issueCertificate(trackId)
                mutableState.value = mutableState.value.copy(
                    academyResult = certificate,
                    academy = repository.academyDashboard(),
                    notice = "Platform activity certificate issued.",
                )
            }
        }
    }

    fun refreshAccount() {
        viewModelScope.launch {
            runRequest {
                mutableState.value = mutableState.value.copy(
                    businessStatus = repository.businessStatus(),
                    plans = repository.businessPlans(),
                    entitlements = repository.entitlements(),
                    credits = repository.credits(),
                )
            }
        }
    }

    fun clearMessages() {
        mutableState.value = mutableState.value.copy(error = null, notice = null)
    }

    fun refreshDashboard() {
        viewModelScope.launch {
            runRequest { refreshDashboardData() }
        }
    }

    private suspend fun refreshDashboardData() {
        val savedJobs = repository.savedJobs()
        mutableState.value = mutableState.value.copy(
            dashboard = repository.commandCenter(),
            resumes = repository.resumes(),
            applications = repository.applications(),
            savedJobListings = savedJobs,
            savedJobs = savedJobs.map { it.id }.toSet(),
        )
    }

    private suspend fun runRequest(block: suspend () -> Unit) {
        mutableState.value = mutableState.value.copy(busy = true, error = null, notice = null)
        try {
            withContext(Dispatchers.IO) { block() }
        } catch (error: Exception) {
            if (error is com.resumeats.checker.data.ApiException && error.code == 401) {
                sessionStore.clear()
                mutableState.value = mutableState.value.copy(user = null)
            }
            mutableState.value = mutableState.value.copy(
                error = error.message ?: "The request could not be completed.",
            )
        } finally {
            mutableState.value = mutableState.value.copy(busy = false, initializing = false)
        }
    }

    companion object {
        fun factory(repository: CareerRepository, sessionStore: SessionStore) =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    if (modelClass.isAssignableFrom(CareerViewModel::class.java)) {
                        return CareerViewModel(repository, sessionStore) as T
                    }
                    throw IllegalArgumentException("Unknown ViewModel class.")
                }
            }
    }
}
