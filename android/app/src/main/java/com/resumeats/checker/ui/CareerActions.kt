package com.resumeats.checker.ui

import com.resumeats.checker.data.AcademyAssessmentRequest
import com.resumeats.checker.data.AcademyEvidenceRequest
import com.resumeats.checker.data.AcademyProjectRequest
import com.resumeats.checker.data.AcademyRoadmapRequest
import com.resumeats.checker.data.ApplicationEditRequest
import com.resumeats.checker.data.BrandGenerateRequest
import com.resumeats.checker.data.BrandVersionCreateRequest
import com.resumeats.checker.data.BrandVersionEditRequest
import com.resumeats.checker.data.CareerGoalRequest
import com.resumeats.checker.data.CareerRoadmapRequest
import com.resumeats.checker.data.InterviewCreateRequest
import com.resumeats.checker.data.InterviewEditRequest
import com.resumeats.checker.data.JobListing
import com.resumeats.checker.data.PersonalBrandProfile
import com.resumeats.checker.data.ReminderCreateRequest
import com.resumeats.checker.data.ReminderEditRequest
import com.resumeats.checker.data.SalaryCalculatorRequest
import com.resumeats.checker.data.SalaryNegotiationRequest
import com.resumeats.checker.data.SalaryOfferRequest
import com.resumeats.checker.data.SalaryOfferComparisonRequest
import com.resumeats.checker.data.SearchPreferences
import com.resumeats.checker.data.TailoringApprovalRequest

data class CareerActions(
    val addApplication: (String, String, String?, String) -> Unit,
    val updateApplication: (String, String) -> Unit,
    val saveApplicationNotes: (String, String) -> Unit,
    val loadApplicationHistory: (String) -> Unit,
    val loadInterviewHistory: (String) -> Unit,
    val scheduleInterview: (InterviewCreateRequest) -> Unit,
    val updateInterview: (String, InterviewEditRequest) -> Unit,
    val addReminder: (ReminderCreateRequest) -> Unit,
    val updateReminder: (String, ReminderEditRequest) -> Unit,
    val savePreferences: (SearchPreferences) -> Unit,
    val addGoal: (String, String, String) -> Unit,
    val updateGoal: (String, String, Double) -> Unit,
    val sendCoachMessage: (String, String?) -> Unit,
    val generateCareerRoadmap: (CareerRoadmapRequest) -> Unit,
    val updateMilestone: (String, String) -> Unit,
    val setCoachConsent: (Boolean) -> Unit,
    val loadSalary: (String, String) -> Unit,
    val refreshSalaryOffers: () -> Unit,
    val createSalaryOffer: (SalaryOfferRequest) -> Unit,
    val updateSalaryOffer: (String, SalaryOfferRequest) -> Unit,
    val deleteSalaryOffer: (String) -> Unit,
    val calculateSalary: (SalaryCalculatorRequest) -> Unit,
    val salaryGuidance: (SalaryNegotiationRequest) -> Unit,
    val refreshBranding: () -> Unit,
    val saveBrandProfile: (PersonalBrandProfile) -> Unit,
    val generateBrandContent: (BrandGenerateRequest) -> Unit,
    val saveBrandVersion: (BrandVersionCreateRequest) -> Unit,
    val editBrandVersion: (String, BrandVersionEditRequest) -> Unit,
    val loadAcademyTrack: (String) -> Unit,
    val completeLesson: (String, String) -> Unit,
    val submitAssessment: (String, Map<String, String>) -> Unit,
    val submitExercise: (String, String, String) -> Unit,
    val refreshAcademyDetails: () -> Unit,
    val generateAcademyRoadmap: (AcademyRoadmapRequest) -> Unit,
    val submitProject: (AcademyProjectRequest) -> Unit,
    val submitEvidence: (AcademyEvidenceRequest) -> Unit,
    val issueCertificate: (String) -> Unit,
    val loadAcademyAssistantHistory: () -> Unit,
    val askAcademyAssistant: (String, String?) -> Unit,
    val createSalaryComparison: (SalaryOfferComparisonRequest) -> Unit,
    val updateSalaryComparison: (String, SalaryOfferComparisonRequest) -> Unit,
    val deleteSalaryComparison: (String) -> Unit,
    val matchJob: (String) -> Unit,
    val tailorResume: (String, String?) -> Unit,
    val updateTailoringReview: (String, TailoringApprovalRequest) -> Unit,
    val saveTailoredVersion: (String) -> Unit,
)
