package com.resumeats.checker.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class AuthRequest(val email: String, val password: String)

@Serializable
data class AuthResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("expires_at") val expiresAt: String,
    val user: UserSummary,
)

@Serializable
data class UserSummary(
    val id: String,
    val email: String,
    @SerialName("created_at") val createdAt: String = "",
)

@Serializable
data class AnalysisResponse(
    @SerialName("overall_score") val overallScore: Double,
    @SerialName("score_label") val scoreLabel: String = "Estimated Resume–Job Match Score",
    @SerialName("match_tier") val matchTier: String,
    val summary: String,
    @SerialName("category_scores") val categoryScores: List<CategoryScore> = emptyList(),
    @SerialName("matched_requirements") val matchedRequirements: List<RequirementMatch> = emptyList(),
    @SerialName("missing_requirements") val missingRequirements: List<MissingRequirement> = emptyList(),
    @SerialName("keywords_found") val keywordsFound: List<String> = emptyList(),
    val recommendations: List<Recommendation> = emptyList(),
    @SerialName("limitations_disclaimer") val limitationsDisclaimer: String = "",
)

@Serializable
data class CategoryScore(
    @SerialName("category_name") val name: String,
    val score: Double,
    @SerialName("max_score") val maxScore: Double,
    val explanation: String,
)

@Serializable
data class RequirementMatch(
    val requirement: String,
    val category: String = "",
    @SerialName("evidence_strength") val evidenceStrength: String = "",
)

@Serializable
data class MissingRequirement(
    val requirement: String,
    val category: String = "",
    val importance: String = "",
    val reason: String = "",
)

@Serializable
data class Recommendation(
    val title: String,
    val description: String,
    val priority: String = "",
)

@Serializable
data class ResumeProfile(
    val id: String,
    val title: String,
    val skills: List<String> = emptyList(),
    @SerialName("is_primary") val isPrimary: Boolean = false,
    @SerialName("updated_at") val updatedAt: String = "",
)

@Serializable
data class JobSearchRequest(
    val query: String,
    val country: String = "gb",
    val location: String = "",
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 20,
)

@Serializable
data class JobSearchResponse(
    val jobs: List<JobListing> = emptyList(),
    val count: Int = 0,
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 20,
    @SerialName("has_more") val hasMore: Boolean = false,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class JobListing(
    val id: String,
    val title: String,
    @SerialName("company_name") val companyName: String,
    val location: String = "",
    @SerialName("remote_type") val remoteType: String? = null,
    @SerialName("employment_type") val employmentType: String? = null,
    @SerialName("original_url") val originalUrl: String? = null,
    @SerialName("source_label") val sourceLabel: String? = null,
    val description: String = "",
    @SerialName("salary_min") val salaryMin: Double? = null,
    @SerialName("salary_max") val salaryMax: Double? = null,
    @SerialName("salary_currency") val salaryCurrency: String? = null,
)

@Serializable
data class ApplicationCreateRequest(
    @SerialName("job_id") val jobId: String? = null,
    val title: String,
    @SerialName("company_name") val companyName: String,
    val location: String = "",
    val status: String = "saved",
)

@Serializable
data class ApplicationUpdateRequest(val status: String)

@Serializable
data class ApplicationEditRequest(
    val status: String? = null,
    val notes: String? = null,
    val note: String = "",
)

@Serializable
data class CareerApplication(
    val id: String,
    val title: String,
    @SerialName("company_name") val companyName: String,
    val location: String = "",
    val status: String,
    @SerialName("applied_at") val appliedAt: String? = null,
    @SerialName("updated_at") val updatedAt: String = "",
    val notes: String = "",
)

@Serializable
data class CareerGoalRequest(
    val title: String,
    val description: String = "",
    @SerialName("target_role") val targetRole: String,
    @SerialName("goal_type") val goalType: String = "short_term",
)

@Serializable
data class CareerGoal(
    val id: String,
    val title: String,
    @SerialName("target_role") val targetRole: String = "",
    val status: String = "active",
    val progress: Double = 0.0,
)

@Serializable
data class CareerGoalUpdateRequest(
    val status: String? = null,
    val progress: Double? = null,
)

@Serializable
data class CareerChatRequest(val message: String, @SerialName("roadmap_id") val roadmapId: String? = null)

@Serializable
data class CareerRoadmapRequest(
    @SerialName("resume_id") val resumeId: String? = null,
    @SerialName("goal_id") val goalId: String? = null,
    @SerialName("target_role") val targetRole: String,
    @SerialName("current_role") val currentRole: String = "",
    val industry: String = "",
    @SerialName("experience_level") val experienceLevel: String = "",
    val interests: List<String> = emptyList(),
    @SerialName("job_description") val jobDescription: String = "",
    val customization: String = "",
)

@Serializable
data class CareerMilestoneUpdateRequest(val status: String)

@Serializable
data class JobMatchRequest(
    @SerialName("job_id") val jobId: String? = null,
    val description: String? = null,
    @SerialName("resume_id") val resumeId: String? = null,
)

@Serializable
data class TailoringChangeApproval(
    val id: String,
    @SerialName("is_accepted") val isAccepted: Boolean,
    @SerialName("proposed_text") val proposedText: String? = null,
)

@Serializable
data class TailoringApprovalRequest(val changes: List<TailoringChangeApproval>)

@Serializable
data class AcademyRoadmapRequest(
    @SerialName("target_role") val targetRole: String,
    @SerialName("skills_to_develop") val skillsToDevelop: List<String> = emptyList(),
    @SerialName("track_ids") val trackIds: List<String> = emptyList(),
    val goal: String = "",
)

@Serializable
data class AcademyAssessmentRequest(val answers: Map<String, String>)

@Serializable
data class AcademyExerciseRequest(val code: String)

@Serializable
data class AcademyEvidenceRequest(
    val skill: String,
    @SerialName("evidence_type") val evidenceType: String,
    val description: String,
    @SerialName("evidence_url") val evidenceUrl: String? = null,
)

@Serializable
data class AcademyProjectRequest(
    val title: String,
    val description: String,
    val skills: List<String> = emptyList(),
    @SerialName("project_url") val projectUrl: String? = null,
)

@Serializable
data class PersonalBrandProfile(
    @SerialName("personal_name") val personalName: String = "",
    @SerialName("current_role") val currentRole: String = "",
    @SerialName("target_roles") val targetRoles: List<String> = emptyList(),
    val industry: String = "",
    val skills: List<String> = emptyList(),
    val about: String = "",
    val experience: List<String> = emptyList(),
    val projects: List<String> = emptyList(),
    @SerialName("linkedin_url") val linkedinUrl: String? = null,
    @SerialName("portfolio_url") val portfolioUrl: String? = null,
    @SerialName("github_username") val githubUsername: String = "",
    val tone: String = "professional",
)

@Serializable
data class BrandGenerateRequest(
    @SerialName("content_type") val contentType: String,
    val tone: String = "professional",
    @SerialName("target_role") val targetRole: String = "",
    val platform: String = "",
    @SerialName("job_description") val jobDescription: String = "",
    @SerialName("source_text") val sourceText: String = "",
    @SerialName("custom_instructions") val customInstructions: String = "",
)

@Serializable
data class BrandVersionCreateRequest(
    @SerialName("content_type") val contentType: String,
    val title: String,
    val tone: String,
    val content: String,
)

@Serializable
data class BrandVersionEditRequest(val title: String, val content: String)

@Serializable
data class SalaryOfferRequest(
    val name: String,
    val company: String = "",
    val role: String = "",
    val location: String = "",
    val currency: String,
    @SerialName("annual_base") val annualBase: Double = 0.0,
    @SerialName("annual_variable") val annualVariable: Double = 0.0,
    @SerialName("annual_bonus") val annualBonus: Double = 0.0,
    @SerialName("annual_equity") val annualEquity: Double = 0.0,
    val benefits: List<String> = emptyList(),
    val conditions: String = "",
    @SerialName("growth_notes") val growthNotes: String = "",
)

@Serializable
data class SalaryOfferComparisonRequest(
    val title: String,
    @SerialName("offer_ids") val offerIds: List<String>,
)

@Serializable
data class SalaryCalculatorRequest(
    val currency: String,
    @SerialName("annual_fixed") val annualFixed: Double,
    @SerialName("annual_variable") val annualVariable: Double = 0.0,
    @SerialName("annual_bonus") val annualBonus: Double = 0.0,
    @SerialName("annual_equity") val annualEquity: Double = 0.0,
    @SerialName("annual_tax_rate_percent") val annualTaxRatePercent: Double = 0.0,
    @SerialName("monthly_deductions") val monthlyDeductions: Double = 0.0,
)

@Serializable
data class SalaryNegotiationRequest(
    @SerialName("request_type") val requestType: String,
    val role: String,
    val company: String = "",
    val location: String = "",
    val currency: String,
    @SerialName("current_offer") val currentOffer: Double? = null,
    @SerialName("target_compensation") val targetCompensation: Double? = null,
    val experience: String = "",
    val achievements: String = "",
    val priorities: String = "",
)

@Serializable
data class InterviewCreateRequest(
    @SerialName("application_id") val applicationId: String,
    @SerialName("scheduled_at") val scheduledAt: String,
    val timezone: String,
    @SerialName("interview_type") val interviewType: String,
    @SerialName("meeting_url") val meetingUrl: String? = null,
    @SerialName("interviewer_details") val interviewerDetails: String = "",
    @SerialName("preparation_notes") val preparationNotes: String = "",
)

@Serializable
data class InterviewEditRequest(
    val status: String? = null,
    @SerialName("scheduled_at") val scheduledAt: String? = null,
    val timezone: String? = null,
)

@Serializable
data class ReminderCreateRequest(
    @SerialName("application_id") val applicationId: String? = null,
    @SerialName("interview_id") val interviewId: String? = null,
    @SerialName("job_id") val jobId: String? = null,
    @SerialName("reminder_type") val reminderType: String,
    @SerialName("due_at") val dueAt: String,
    val message: String,
    @SerialName("email_requested") val emailRequested: Boolean = false,
)

@Serializable
data class ReminderEditRequest(
    val status: String,
    @SerialName("snoozed_until") val snoozedUntil: String? = null,
)

@Serializable
data class SearchPreferences(
    @SerialName("preferred_titles") val preferredTitles: List<String> = emptyList(),
    @SerialName("preferred_locations") val preferredLocations: List<String> = emptyList(),
    @SerialName("work_modes") val workModes: List<String> = emptyList(),
    @SerialName("employment_types") val employmentTypes: List<String> = emptyList(),
    val industries: List<String> = emptyList(),
    @SerialName("salary_min") val salaryMin: Double? = null,
    @SerialName("salary_max") val salaryMax: Double? = null,
    @SerialName("salary_currency") val salaryCurrency: String? = null,
    @SerialName("experience_level") val experienceLevel: String? = null,
    @SerialName("career_goals") val careerGoals: String = "",
    @SerialName("application_follow_up_days") val applicationFollowUpDays: Int = 7,
    @SerialName("interview_reminder_hours") val interviewReminderHours: List<Int> = listOf(24, 1),
    @SerialName("email_reminders") val emailReminders: Boolean = false,
)

@Serializable
data class BusinessPlan(
    val id: String,
    val name: String,
    val tier: String,
    @SerialName("billing_interval") val billingInterval: String,
    @SerialName("price_minor") val priceMinor: Long? = null,
    val currency: String,
    @SerialName("credits_grant") val creditsGrant: Int = 0,
    val entitlements: Map<String, JsonElement> = emptyMap(),
)

@Serializable
data class BusinessStatus(
    val admin: Boolean = false,
    @SerialName("checkout_configured") val checkoutConfigured: Boolean = false,
    @SerialName("payment_provider") val paymentProvider: String? = null,
    @SerialName("active_plans") val activePlans: Int = 0,
)

@Serializable
data class CreditAccount(
    val balance: Int = 0,
    val reserved: Int = 0,
    val available: Int = 0,
)

@Serializable
data class SalaryBenchmarks(
    val role: String,
    val location: String? = null,
    @SerialName("sample_size") val sampleSize: Int = 0,
    val groups: List<SalaryGroup> = emptyList(),
    val message: String? = null,
)

@Serializable
data class SalaryGroup(
    val currency: String,
    @SerialName("reporting_period") val reportingPeriod: String = "",
    @SerialName("sample_size") val sampleSize: Int = 0,
    val minimum: Double,
    val median: Double,
    val maximum: Double,
    val confidence: String = "",
)
