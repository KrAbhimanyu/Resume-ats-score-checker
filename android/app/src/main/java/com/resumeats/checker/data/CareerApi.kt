package com.resumeats.checker.data

import kotlinx.serialization.json.JsonObject
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface CareerApi {
    @POST("api/v1/career/auth/register")
    suspend fun register(@Body body: AuthRequest): AuthResponse

    @POST("api/v1/career/auth/login")
    suspend fun login(@Body body: AuthRequest): AuthResponse

    @POST("api/v1/career/auth/logout")
    suspend fun logout(): Response<Unit>

    @GET("api/v1/career/auth/me")
    suspend fun me(): UserSummary

    @Multipart
    @POST("api/v1/analyze")
    suspend fun analyzeResume(
        @Part resumeFile: MultipartBody.Part,
        @Part("job_description") jobDescription: RequestBody,
    ): AnalysisResponse

    @GET("api/v1/career/profile/resumes")
    suspend fun resumes(): List<ResumeProfile>

    @Multipart
    @POST("api/v1/career/profile/resumes/upload")
    suspend fun uploadResume(
        @Query("title") title: String,
        @Part resumeFile: MultipartBody.Part,
    ): ResumeProfile

    @GET("api/v1/career/command-center")
    suspend fun commandCenter(
        @Query("timeline_offset") timelineOffset: Int = 0,
        @Query("timeline_limit") timelineLimit: Int = 20,
    ): JsonObject

    @POST("api/v1/career/discover")
    suspend fun discover(@Body body: JobSearchRequest): JobSearchResponse

    @GET("api/v1/career/jobs/saved")
    suspend fun savedJobs(): List<JobListing>

    @POST("api/v1/career/jobs/{jobId}/save")
    suspend fun saveJob(@Path("jobId") jobId: String): JsonObject

    @DELETE("api/v1/career/jobs/{jobId}/save")
    suspend fun unsaveJob(@Path("jobId") jobId: String): Response<Unit>

    @GET("api/v1/career/applications")
    suspend fun applications(): List<CareerApplication>

    @POST("api/v1/career/applications")
    suspend fun createApplication(@Body body: ApplicationCreateRequest): CareerApplication

    @PATCH("api/v1/career/applications/{applicationId}")
    suspend fun updateApplication(
        @Path("applicationId") applicationId: String,
        @Body body: ApplicationUpdateRequest,
    ): CareerApplication

    @PATCH("api/v1/career/applications/{applicationId}")
    suspend fun editApplication(
        @Path("applicationId") applicationId: String,
        @Body body: ApplicationEditRequest,
    ): CareerApplication

    @GET("api/v1/career/applications/{applicationId}/history")
    suspend fun applicationHistory(@Path("applicationId") applicationId: String): List<JsonObject>

    @GET("api/v1/career/interviews")
    suspend fun interviews(@Query("upcoming_only") upcomingOnly: Boolean = false): List<JsonObject>

    @POST("api/v1/career/interviews")
    suspend fun createInterview(@Body body: InterviewCreateRequest): JsonObject

    @PATCH("api/v1/career/interviews/{interviewId}")
    suspend fun updateInterview(@Path("interviewId") interviewId: String, @Body body: InterviewEditRequest): JsonObject

    @GET("api/v1/career/interviews/{interviewId}/history")
    suspend fun interviewHistory(@Path("interviewId") interviewId: String): List<JsonObject>

    @GET("api/v1/career/reminders")
    suspend fun reminders(): JsonObject

    @POST("api/v1/career/reminders")
    suspend fun createReminder(@Body body: ReminderCreateRequest): JsonObject

    @PATCH("api/v1/career/reminders/{reminderId}")
    suspend fun updateReminder(@Path("reminderId") reminderId: String, @Body body: ReminderEditRequest): JsonObject

    @GET("api/v1/career/profile/preferences")
    suspend fun preferences(): JsonObject

    @PUT("api/v1/career/profile/preferences")
    suspend fun savePreferences(@Body body: SearchPreferences): JsonObject

    @GET("api/v1/career/coach/state")
    suspend fun coachState(): JsonObject

    @POST("api/v1/career/coach/goals")
    suspend fun createGoal(@Body body: CareerGoalRequest): CareerGoal

    @PATCH("api/v1/career/coach/goals/{goalId}")
    suspend fun updateGoal(@Path("goalId") goalId: String, @Body body: CareerGoalUpdateRequest): CareerGoal

    @POST("api/v1/career/coach/chat")
    suspend fun coachChat(@Body body: CareerChatRequest): JsonObject

    @POST("api/v1/career/coach/roadmaps/generate")
    suspend fun generateCareerRoadmap(@Body body: CareerRoadmapRequest): JsonObject

    @PATCH("api/v1/career/coach/milestones/{milestoneId}")
    suspend fun updateMilestone(@Path("milestoneId") milestoneId: String, @Body body: CareerMilestoneUpdateRequest): JsonObject

    @PUT("api/v1/career/coach/consent")
    suspend fun setCoachConsent(@Body body: JsonObject): JsonObject

    @POST("api/v1/career/jobs/match")
    suspend fun matchJob(@Body body: JobMatchRequest): JsonObject

    @GET("api/v1/career/jobs/matches")
    suspend fun jobMatches(@Query("limit") limit: Int = 30): List<JsonObject>

    @POST("api/v1/career/jobs/job/{jobId}/tailor")
    suspend fun tailorResume(@Path("jobId") jobId: String, @Query("resume_id") resumeId: String? = null): JsonObject

    @PATCH("api/v1/career/tailoring/{sessionId}")
    suspend fun updateTailoringReview(
        @Path("sessionId") sessionId: String,
        @Body body: TailoringApprovalRequest,
    ): JsonObject

    @POST("api/v1/career/tailoring/{sessionId}/save-version")
    suspend fun saveTailoredVersion(@Path("sessionId") sessionId: String): JsonObject

    @GET("api/v1/career/academy/dashboard")
    suspend fun academyDashboard(): JsonObject

    @GET("api/v1/career/academy/tracks/{trackId}")
    suspend fun academyTrack(@Path("trackId") trackId: String): JsonObject

    @POST("api/v1/career/academy/tracks/{trackId}/lessons/{lessonId}/complete")
    suspend fun completeLesson(@Path("trackId") trackId: String, @Path("lessonId") lessonId: String): JsonObject

    @POST("api/v1/career/academy/tracks/{trackId}/assessment")
    suspend fun submitAssessment(@Path("trackId") trackId: String, @Body body: AcademyAssessmentRequest): JsonObject

    @POST("api/v1/career/academy/tracks/{trackId}/exercises/{exerciseId}")
    suspend fun submitExercise(@Path("trackId") trackId: String, @Path("exerciseId") exerciseId: String, @Body body: AcademyExerciseRequest): JsonObject

    @GET("api/v1/career/academy/roadmaps")
    suspend fun academyRoadmaps(): List<JsonObject>

    @POST("api/v1/career/academy/roadmaps")
    suspend fun generateAcademyRoadmap(@Body body: AcademyRoadmapRequest): JsonObject

    @GET("api/v1/career/academy/assistant/history")
    suspend fun academyAssistantHistory(): List<JsonObject>

    @POST("api/v1/career/academy/assistant")
    suspend fun academyAssistant(@Body body: JsonObject): JsonObject

    @GET("api/v1/career/academy/projects")
    suspend fun academyProjects(): List<JsonObject>

    @POST("api/v1/career/academy/projects/evaluate")
    suspend fun evaluateProject(@Body body: AcademyProjectRequest): JsonObject

    @POST("api/v1/career/academy/skills/evidence")
    suspend fun submitSkillEvidence(@Body body: AcademyEvidenceRequest): JsonObject

    @POST("api/v1/career/academy/tracks/{trackId}/certificate")
    suspend fun issueCertificate(@Path("trackId") trackId: String): JsonObject

    @GET("api/v1/career/branding/dashboard")
    suspend fun brandingDashboard(): JsonObject

    @PUT("api/v1/career/branding/profile")
    suspend fun saveBrandProfile(@Body body: PersonalBrandProfile): JsonObject

    @POST("api/v1/career/branding/generate")
    suspend fun generateBrandContent(@Body body: BrandGenerateRequest): JsonObject

    @GET("api/v1/career/branding/versions")
    suspend fun brandVersions(): List<JsonObject>

    @POST("api/v1/career/branding/versions")
    suspend fun createBrandVersion(@Body body: BrandVersionCreateRequest): JsonObject

    @PATCH("api/v1/career/branding/versions/{versionId}")
    suspend fun editBrandVersion(@Path("versionId") versionId: String, @Body body: BrandVersionEditRequest): JsonObject

    @GET("api/v1/career/salary/intelligence")
    suspend fun salaryIntelligence(
        @Query("role") role: String,
        @Query("location") location: String = "",
        @Query("currency") currency: String? = null,
    ): SalaryBenchmarks

    @GET("api/v1/career/salary/offers")
    suspend fun salaryOffers(): List<JsonObject>

    @POST("api/v1/career/salary/offers")
    suspend fun createSalaryOffer(@Body body: SalaryOfferRequest): JsonObject

    @PUT("api/v1/career/salary/offers/{offerId}")
    suspend fun updateSalaryOffer(@Path("offerId") offerId: String, @Body body: SalaryOfferRequest): JsonObject

    @DELETE("api/v1/career/salary/offers/{offerId}")
    suspend fun deleteSalaryOffer(@Path("offerId") offerId: String): retrofit2.Response<Unit>

    @GET("api/v1/career/salary/comparisons")
    suspend fun salaryComparisons(): List<JsonObject>

    @POST("api/v1/career/salary/comparisons")
    suspend fun createSalaryComparison(@Body body: SalaryOfferComparisonRequest): JsonObject

    @PUT("api/v1/career/salary/comparisons/{comparisonId}")
    suspend fun updateSalaryComparison(
        @Path("comparisonId") comparisonId: String,
        @Body body: SalaryOfferComparisonRequest,
    ): JsonObject

    @DELETE("api/v1/career/salary/comparisons/{comparisonId}")
    suspend fun deleteSalaryComparison(@Path("comparisonId") comparisonId: String): retrofit2.Response<Unit>

    @POST("api/v1/career/salary/calculate")
    suspend fun calculateSalary(@Body body: SalaryCalculatorRequest): JsonObject

    @POST("api/v1/career/salary/negotiation-guidance")
    suspend fun salaryNegotiation(@Body body: SalaryNegotiationRequest): JsonObject

    @GET("api/v1/career/business/plans")
    suspend fun businessPlans(): List<BusinessPlan>

    @GET("api/v1/career/business/status")
    suspend fun businessStatus(): BusinessStatus

    @GET("api/v1/career/business/entitlements")
    suspend fun entitlements(): JsonObject

    @GET("api/v1/career/business/credits")
    suspend fun credits(): CreditAccount
}
