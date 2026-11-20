package com.resumeats.checker.data

import com.resumeats.checker.BuildConfig
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.ResponseBody
import retrofit2.Retrofit
import retrofit2.HttpException
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.io.IOException

class CareerRepository(
    private val api: CareerApi,
    private val sessionStore: SessionStore,
) {
    suspend fun authenticate(email: String, password: String, register: Boolean): AuthResponse {
        val response = safeCall {
            if (register) api.register(AuthRequest(email.trim(), password))
            else api.login(AuthRequest(email.trim(), password))
        }
        sessionStore.writeToken(response.accessToken)
        return response
    }

    suspend fun restoreSession(): UserSummary? = try {
        if (sessionStore.readToken() == null) null else safeCall { api.me() }
    } catch (error: Exception) {
        if (error is ApiException && error.code == 401) sessionStore.clear()
        throw error
    }

    suspend fun logout() {
        try {
            val response = api.logout()
            if (!response.isSuccessful) throw apiError(response.code(), response.errorBody())
        } finally {
            sessionStore.clear()
        }
    }

    suspend fun analyze(fileName: String, bytes: ByteArray, jobDescription: String): AnalysisResponse {
        val type = when {
            fileName.endsWith(".pdf", ignoreCase = true) -> "application/pdf"
            fileName.endsWith(".docx", ignoreCase = true) ->
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else -> throw ApiException("Choose a PDF or DOCX resume.")
        }
        if (bytes.isEmpty() || bytes.size > 5 * 1024 * 1024) {
            throw ApiException("Resume file must be between 1 byte and 5 MB.")
        }
        val fileBody = bytes.toRequestBody(type.toMediaType())
        val part = MultipartBody.Part.createFormData("resume_file", fileName, fileBody)
        return safeCall {
            api.analyzeResume(
                part,
                jobDescription.toRequestBody("text/plain; charset=utf-8".toMediaType()),
            )
        }
    }

    suspend fun uploadResume(fileName: String, bytes: ByteArray): ResumeProfile {
        val type = when {
            fileName.endsWith(".pdf", ignoreCase = true) -> "application/pdf"
            fileName.endsWith(".docx", ignoreCase = true) ->
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else -> throw ApiException("Choose a PDF or DOCX resume.")
        }
        if (bytes.isEmpty() || bytes.size > 5 * 1024 * 1024) {
            throw ApiException("Resume file must be between 1 byte and 5 MB.")
        }
        val part = MultipartBody.Part.createFormData(
            "resume_file",
            fileName,
            bytes.toRequestBody(type.toMediaType()),
        )
        return safeCall { api.uploadResume("Primary resume", part) }
    }

    suspend fun resumes() = safeCall { api.resumes() }
    suspend fun commandCenter() = safeCall { api.commandCenter() }
    suspend fun discover(body: JobSearchRequest) = safeCall { api.discover(body) }
    suspend fun savedJobs() = safeCall { api.savedJobs() }
    suspend fun saveJob(jobId: String) = safeCall { api.saveJob(jobId) }
    suspend fun applications() = safeCall { api.applications() }
    suspend fun createApplication(body: ApplicationCreateRequest) = safeCall { api.createApplication(body) }
    suspend fun updateApplication(id: String, body: ApplicationUpdateRequest) =
        safeCall { api.updateApplication(id, body) }
    suspend fun editApplication(id: String, body: ApplicationEditRequest) =
        safeCall { api.editApplication(id, body) }
    suspend fun applicationHistory(id: String) = safeCall { api.applicationHistory(id) }
    suspend fun interviews(upcomingOnly: Boolean = false) = safeCall { api.interviews(upcomingOnly) }
    suspend fun createInterview(body: InterviewCreateRequest) = safeCall { api.createInterview(body) }
    suspend fun updateInterview(id: String, body: InterviewEditRequest) = safeCall { api.updateInterview(id, body) }
    suspend fun interviewHistory(id: String) = safeCall { api.interviewHistory(id) }
    suspend fun reminders() = safeCall { api.reminders() }
    suspend fun createReminder(body: ReminderCreateRequest) = safeCall { api.createReminder(body) }
    suspend fun updateReminder(id: String, body: ReminderEditRequest) = safeCall { api.updateReminder(id, body) }
    suspend fun preferences() = safeCall { api.preferences() }
    suspend fun savePreferences(body: SearchPreferences) = safeCall { api.savePreferences(body) }
    suspend fun coachState() = safeCall { api.coachState() }
    suspend fun createGoal(body: CareerGoalRequest) = safeCall { api.createGoal(body) }
    suspend fun updateGoal(id: String, body: CareerGoalUpdateRequest) = safeCall { api.updateGoal(id, body) }
    suspend fun coachChat(body: CareerChatRequest) = safeCall { api.coachChat(body) }
    suspend fun generateCareerRoadmap(body: CareerRoadmapRequest) = safeCall { api.generateCareerRoadmap(body) }
    suspend fun updateMilestone(id: String, body: CareerMilestoneUpdateRequest) = safeCall { api.updateMilestone(id, body) }
    suspend fun setCoachConsent(enabled: Boolean) = safeCall {
        api.setCoachConsent(kotlinx.serialization.json.buildJsonObject { put("enabled", enabled) })
    }
    suspend fun matchJob(body: JobMatchRequest) = safeCall { api.matchJob(body) }
    suspend fun jobMatches() = safeCall { api.jobMatches() }
    suspend fun tailorResume(jobId: String, resumeId: String?) = safeCall { api.tailorResume(jobId, resumeId) }
    suspend fun updateTailoringReview(sessionId: String, body: TailoringApprovalRequest) =
        safeCall { api.updateTailoringReview(sessionId, body) }
    suspend fun saveTailoredVersion(sessionId: String) = safeCall { api.saveTailoredVersion(sessionId) }
    suspend fun academyDashboard() = safeCall { api.academyDashboard() }
    suspend fun academyTrack(id: String) = safeCall { api.academyTrack(id) }
    suspend fun completeLesson(trackId: String, lessonId: String) = safeCall { api.completeLesson(trackId, lessonId) }
    suspend fun submitAssessment(trackId: String, body: AcademyAssessmentRequest) = safeCall { api.submitAssessment(trackId, body) }
    suspend fun submitExercise(trackId: String, exerciseId: String, body: AcademyExerciseRequest) =
        safeCall { api.submitExercise(trackId, exerciseId, body) }
    suspend fun academyRoadmaps() = safeCall { api.academyRoadmaps() }
    suspend fun generateAcademyRoadmap(body: AcademyRoadmapRequest) = safeCall { api.generateAcademyRoadmap(body) }
    suspend fun academyAssistantHistory() = safeCall { api.academyAssistantHistory() }
    suspend fun academyAssistant(message: String, trackId: String?) = safeCall {
        api.academyAssistant(kotlinx.serialization.json.buildJsonObject {
            put("message", message)
            trackId?.let { put("track_id", it) }
        })
    }
    suspend fun academyProjects() = safeCall { api.academyProjects() }
    suspend fun evaluateProject(body: AcademyProjectRequest) = safeCall { api.evaluateProject(body) }
    suspend fun submitSkillEvidence(body: AcademyEvidenceRequest) = safeCall { api.submitSkillEvidence(body) }
    suspend fun issueCertificate(trackId: String) = safeCall { api.issueCertificate(trackId) }
    suspend fun brandingDashboard() = safeCall { api.brandingDashboard() }
    suspend fun saveBrandProfile(body: PersonalBrandProfile) = safeCall { api.saveBrandProfile(body) }
    suspend fun generateBrandContent(body: BrandGenerateRequest) = safeCall { api.generateBrandContent(body) }
    suspend fun brandVersions() = safeCall { api.brandVersions() }
    suspend fun createBrandVersion(body: BrandVersionCreateRequest) = safeCall { api.createBrandVersion(body) }
    suspend fun editBrandVersion(id: String, body: BrandVersionEditRequest) = safeCall { api.editBrandVersion(id, body) }
    suspend fun salaryIntelligence(role: String, location: String) =
        safeCall { api.salaryIntelligence(role, location) }
    suspend fun salaryOffers() = safeCall { api.salaryOffers() }
    suspend fun createSalaryOffer(body: SalaryOfferRequest) = safeCall { api.createSalaryOffer(body) }
    suspend fun updateSalaryOffer(id: String, body: SalaryOfferRequest) = safeCall { api.updateSalaryOffer(id, body) }
    suspend fun deleteSalaryOffer(id: String) = safeCall {
        val response = api.deleteSalaryOffer(id)
        if (!response.isSuccessful) throw apiError(response.code(), response.errorBody())
    }
    suspend fun salaryComparisons() = safeCall { api.salaryComparisons() }
    suspend fun createSalaryComparison(body: SalaryOfferComparisonRequest) = safeCall {
        api.createSalaryComparison(body)
    }
    suspend fun updateSalaryComparison(id: String, body: SalaryOfferComparisonRequest) = safeCall {
        api.updateSalaryComparison(id, body)
    }
    suspend fun deleteSalaryComparison(id: String) = safeCall {
        val response = api.deleteSalaryComparison(id)
        if (!response.isSuccessful) throw apiError(response.code(), response.errorBody())
    }
    suspend fun calculateSalary(body: SalaryCalculatorRequest) = safeCall { api.calculateSalary(body) }
    suspend fun salaryNegotiation(body: SalaryNegotiationRequest) = safeCall { api.salaryNegotiation(body) }
    suspend fun businessPlans() = safeCall { api.businessPlans() }
    suspend fun businessStatus() = safeCall { api.businessStatus() }
    suspend fun entitlements() = safeCall { api.entitlements() }
    suspend fun credits() = safeCall { api.credits() }

    private suspend fun <T> safeCall(block: suspend () -> T): T = try {
        block()
    } catch (error: HttpException) {
        val mapped = apiError(error.code(), error.response()?.errorBody())
        if (mapped.code == 401) sessionStore.clear()
        throw mapped
    }

    companion object {
        fun create(sessionStore: SessionStore): CareerRepository {
            val baseUrl = BuildConfig.API_BASE_URL.trim()
            require(baseUrl.endsWith("/")) { "API_BASE_URL must end with '/'." }
            require(BuildConfig.DEBUG || baseUrl.startsWith("https://")) {
                "Release builds require an HTTPS API_BASE_URL."
            }
            val json = Json {
                ignoreUnknownKeys = true
                explicitNulls = false
                coerceInputValues = true
            }
            val authorization = Interceptor { chain ->
                val builder = chain.request().newBuilder()
                sessionStore.readToken()?.let { builder.header("Authorization", "Bearer $it") }
                chain.proceed(builder.build())
            }
            val client = OkHttpClient.Builder()
                .addInterceptor(authorization)
                .build()
            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                .build()
            val api = retrofit.create(CareerApi::class.java)
            return CareerRepository(api, sessionStore)
        }
    }
}

class ApiException(
    override val message: String,
    val code: Int? = null,
) : IOException(message)

internal fun apiError(code: Int, body: ResponseBody?): ApiException {
    val content = body?.string().orEmpty()
    val detail = runCatching {
        Json.parseToJsonElement(content)
            .let { element ->
                element as? kotlinx.serialization.json.JsonObject
            }
            ?.get("detail")
            ?.let { it as? kotlinx.serialization.json.JsonPrimitive }
            ?.content
    }.getOrNull()
    return ApiException(
        detail ?: when (code) {
            401 -> "Your session expired. Please sign in again."
            403 -> "You are not allowed to perform this action."
            413 -> "The uploaded file is too large."
            else -> "The server could not complete this request (HTTP $code)."
        },
        code,
    )
}
