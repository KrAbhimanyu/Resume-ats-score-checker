package com.resumeats.checker.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.resumeats.checker.data.AcademyEvidenceRequest
import com.resumeats.checker.data.AcademyProjectRequest
import com.resumeats.checker.data.AcademyRoadmapRequest
import com.resumeats.checker.data.ApplicationCreateRequest
import com.resumeats.checker.data.BrandGenerateRequest
import com.resumeats.checker.data.BrandVersionEditRequest
import com.resumeats.checker.data.CareerGoalRequest
import com.resumeats.checker.data.CareerRoadmapRequest
import com.resumeats.checker.data.InterviewCreateRequest
import com.resumeats.checker.data.InterviewEditRequest
import com.resumeats.checker.data.PersonalBrandProfile
import com.resumeats.checker.data.ReminderCreateRequest
import com.resumeats.checker.data.ReminderEditRequest
import com.resumeats.checker.data.SalaryCalculatorRequest
import com.resumeats.checker.data.SalaryNegotiationRequest
import com.resumeats.checker.data.SalaryOfferComparisonRequest
import com.resumeats.checker.data.SalaryOfferRequest
import com.resumeats.checker.data.SearchPreferences
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException

@Composable
fun CareerModulesScreen(state: CareerUiState, actions: CareerActions) {
    ApplicationsModule(state, actions)
    CoachModule(state, actions)
    AcademyModule(state, actions)
    BrandingModule(state, actions)
    SalaryModule(state, actions)
    PreferencesModule(state, actions)
}

@Composable
private fun ApplicationsModule(state: CareerUiState, actions: CareerActions) {
    var title by remember { mutableStateOf("") }
    var company by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var selectedHistory by remember { mutableStateOf<String?>(null) }
    var interviewApplicationId by remember { mutableStateOf("") }
    var interviewDate by remember { mutableStateOf("") }
    var interviewType by remember { mutableStateOf("Video") }
    var timezone by remember { mutableStateOf("UTC") }
    var interviewUrl by remember { mutableStateOf("") }
    var reminderApplicationId by remember { mutableStateOf("") }
    var reminderDate by remember { mutableStateOf("") }
    var reminderMessage by remember { mutableStateOf("") }

    SectionCard("Application tracker, notes and history") {
        OutlinedTextField(title, { title = it.take(200) }, Modifier.fillMaxWidth(), label = { Text("Role") }, singleLine = true)
        OutlinedTextField(company, { company = it.take(200) }, Modifier.fillMaxWidth(), label = { Text("Company") }, singleLine = true)
        OutlinedTextField(location, { location = it.take(200) }, Modifier.fillMaxWidth(), label = { Text("Location") }, singleLine = true)
        Button(
            onClick = {
                actions.addApplication(title.trim(), company.trim(), null, location.trim())
                title = ""; company = ""; location = ""
            },
            enabled = !state.busy && title.isNotBlank() && company.isNotBlank(),
        ) { Text("Add application") }
        if (state.applications.isEmpty()) EmptyState("No applications tracked", "Applications are private to your account.")
        state.applications.forEach { application ->
            var notes by remember(application.id, application.notes) { mutableStateOf(application.notes) }
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("${application.title} · ${application.companyName}", fontWeight = FontWeight.SemiBold)
                Text("${application.location} · ${application.status.replaceFirstChar { it.uppercase() }}")
                OutlinedTextField(
                    notes,
                    { notes = it.take(10_000) },
                    Modifier.fillMaxWidth(),
                    label = { Text("Private application notes") },
                    minLines = 2,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Button(onClick = { actions.saveApplicationNotes(application.id, notes) }, enabled = !state.busy) { Text("Save notes") }
                    OutlinedButton(onClick = {
                        selectedHistory = application.id
                        actions.loadApplicationHistory(application.id)
                    }, enabled = !state.busy) { Text("Status history") }
                }
                StatusSelector(application.status, state.busy) { actions.updateApplication(application.id, it) }
            }
        }
        if (selectedHistory != null) {
            Text("Status history", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            state.applicationHistory.forEach { event ->
                Text("${event.string("from_status")} → ${event.string("to_status")} · ${event.string("created_at")}")
                event.string("note").takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            }
        }
    }

    SectionCard("Interview schedule and reminders") {
        if (state.interviews.isEmpty()) EmptyState("No interviews scheduled", "Schedule an interview against one of your tracked applications.")
        state.interviews.forEach { interview ->
            val id = interview.string("id")
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("${interview.string("interview_type")} · ${interview.string("scheduled_at")}", fontWeight = FontWeight.Medium)
                Text("${interview.string("application_id")} · ${interview.string("status")}", style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (interview.string("status") == "scheduled") {
                        OutlinedButton(
                            onClick = { actions.updateInterview(id, InterviewEditRequest(status = "completed")) },
                            enabled = !state.busy,
                        ) { Text("Mark completed") }
                    }
                    OutlinedButton(
                        onClick = { actions.loadInterviewHistory(id) },
                        enabled = !state.busy,
                    ) { Text("View history") }
                }
            }
        }
        if (state.interviewHistory.isNotEmpty()) {
            Text("Interview history", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            state.interviewHistory.forEach { item ->
                Text("${item.string("status")} · ${item.string("scheduled_at")}")
            }
        }
        OutlinedTextField(
            interviewApplicationId,
            { interviewApplicationId = it },
            Modifier.fillMaxWidth(),
            label = { Text("Application ID for interview") },
            supportingText = { Text(state.applications.joinToString { "${it.title} (${it.id})" }.take(500)) },
        )
        OutlinedTextField(interviewDate, { interviewDate = it.take(40) }, Modifier.fillMaxWidth(), label = { Text("Date and time with offset (e.g. 2026-11-04T10:00:00+05:30)") })
        OutlinedTextField(interviewType, { interviewType = it.take(80) }, Modifier.fillMaxWidth(), label = { Text("Interview type") }, singleLine = true)
        OutlinedTextField(timezone, { timezone = it.take(64) }, Modifier.fillMaxWidth(), label = { Text("Timezone") }, singleLine = true)
        OutlinedTextField(interviewUrl, { interviewUrl = it.take(2048) }, Modifier.fillMaxWidth(), label = { Text("Meeting URL (optional)") }, singleLine = true)
        Button(
            onClick = {
                actions.scheduleInterview(
                    InterviewCreateRequest(
                        applicationId = interviewApplicationId.trim(),
                        scheduledAt = interviewDate.trim(),
                        timezone = timezone.trim(),
                        interviewType = interviewType.trim(),
                        meetingUrl = interviewUrl.trim().ifBlank { null },
                    ),
                )
            },
            enabled = !state.busy && interviewApplicationId.isNotBlank() && interviewType.isNotBlank() && timezone.isNotBlank() && isOffsetDateTime(interviewDate),
        ) { Text("Schedule interview") }
        OutlinedTextField(reminderApplicationId, { reminderApplicationId = it }, Modifier.fillMaxWidth(), label = { Text("Application ID for follow-up") })
        OutlinedTextField(reminderDate, { reminderDate = it.take(40) }, Modifier.fillMaxWidth(), label = { Text("Reminder due time with offset") })
        OutlinedTextField(reminderMessage, { reminderMessage = it.take(1000) }, Modifier.fillMaxWidth(), label = { Text("Reminder message") })
        Button(
            onClick = {
                actions.addReminder(
                    ReminderCreateRequest(
                        applicationId = reminderApplicationId.trim(),
                        reminderType = "follow_up",
                        dueAt = reminderDate.trim(),
                        message = reminderMessage.trim(),
                    ),
                )
            },
            enabled = !state.busy && reminderApplicationId.isNotBlank() && reminderMessage.isNotBlank() && isOffsetDateTime(reminderDate),
        ) { Text("Add follow-up reminder") }
        val reminders = state.reminders?.arrayValue("reminders").orEmpty()
        if (reminders.isEmpty()) EmptyState("No reminders", "Reminders are saved and scheduled by the backend.")
        reminders.take(30).forEach { element ->
            val reminder = element as? JsonObject ?: JsonObject(emptyMap())
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f)) {
                    Text(reminder.string("message"))
                    Text("${reminder.string("reminder_type")} · ${reminder.string("due_at")} · ${reminder.string("status")}", style = MaterialTheme.typography.bodySmall)
                }
                if (reminder.string("status") in setOf("scheduled", "triggered", "snoozed")) {
                    OutlinedButton(
                        onClick = { actions.updateReminder(reminder.string("id"), ReminderEditRequest(status = "completed")) },
                        enabled = !state.busy,
                    ) { Text("Done") }
                }
            }
        }
    }
}

@Composable
private fun StatusSelector(current: String, busy: Boolean, onSelect: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("Status: $current")
        OutlinedButton(onClick = { expanded = true }, enabled = !busy) { Text("Change") }
        DropdownMenu(expanded, { expanded = false }) {
            listOf("saved", "applied", "shortlisted", "assessment", "interview", "offer", "rejected", "withdrawn").forEach { status ->
                DropdownMenuItem(
                    text = { Text(status) },
                    onClick = { expanded = false; if (status != current) onSelect(status) },
                )
            }
        }
    }
}

@Composable
private fun CoachModule(state: CareerUiState, actions: CareerActions) {
    var goalTitle by remember { mutableStateOf("") }
    var targetRole by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var roadmapRole by remember { mutableStateOf("") }
    val coach = state.coach
    val messages = coach?.arrayValue("messages").orEmpty()
    val roadmaps = coach?.arrayValue("roadmaps").orEmpty()
    val consent = coach?.get("ai_data_consent")?.let { (it as? JsonPrimitive)?.contentOrNull == "true" } ?: false

    SectionCard("AI Career Coach, goals and roadmaps") {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Allow AI to use profile context", modifier = Modifier.weight(1f))
            Switch(checked = consent, onCheckedChange = actions.setCoachConsent, enabled = !state.busy)
        }
        Text(
            "Personalized Coach/branding/salary AI requires explicit backend consent and consumes account credits. Turning consent off prevents future AI requests.",
            style = MaterialTheme.typography.bodySmall,
        )
        OutlinedTextField(goalTitle, { goalTitle = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Career goal") })
        OutlinedTextField(targetRole, { targetRole = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Target role") })
        OutlinedTextField(description, { description = it.take(2000) }, Modifier.fillMaxWidth(), label = { Text("Goal details") })
        Button(
            onClick = {
                actions.addGoal(goalTitle.trim(), targetRole.trim(), description.trim())
                goalTitle = ""; targetRole = ""; description = ""
            },
            enabled = !state.busy && goalTitle.trim().length >= 2 && targetRole.trim().length >= 2,
        ) { Text("Save goal") }
        coach?.arrayValue("goals").orEmpty().forEach { element ->
            val goal = element as? JsonObject ?: JsonObject(emptyMap())
            val goalId = goal.string("id")
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(goal.string("title"), fontWeight = FontWeight.SemiBold)
                Text("${goal.string("target_role")} · ${goal.string("goal_type")} · ${goal.string("status")}")
                val progress = goal.string("progress").toDoubleOrNull() ?: 0.0
                LinearProgressIndicator({ (progress / 100).toFloat().coerceIn(0f, 1f) }, Modifier.fillMaxWidth())
                Text("${progress.toInt()}% complete")
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    OutlinedButton(
                        onClick = { actions.updateGoal(goalId, goal.string("status").takeUnless { it == "completed" } ?: "active", (progress + 10).coerceAtMost(100.0)) },
                        enabled = !state.busy && goalId.isNotBlank(),
                    ) { Text("Add progress") }
                    OutlinedButton(
                        onClick = { actions.updateGoal(goalId, "completed", 100.0) },
                        enabled = !state.busy && goalId.isNotBlank() && goal.string("status") != "completed",
                    ) { Text("Complete") }
                }
            }
        }

        OutlinedTextField(roadmapRole, { roadmapRole = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Roadmap target role") })
        Button(
            onClick = {
                actions.generateCareerRoadmap(CareerRoadmapRequest(targetRole = roadmapRole.trim()))
            },
            enabled = !state.busy && roadmapRole.trim().length >= 2 && consent,
        ) { Text("Generate personalized roadmap") }
        roadmaps.forEach { element ->
            val roadmap = element as? JsonObject ?: JsonObject(emptyMap())
            val content = roadmap.objectValue("content")
            Text(content.string("summary"), style = MaterialTheme.typography.bodyMedium)
            content.arrayValue("action_plan").take(5).forEach { Text(it.toString(), style = MaterialTheme.typography.bodySmall) }
            roadmap.arrayValue("milestones").forEach { item ->
                val milestone = item as? JsonObject ?: JsonObject(emptyMap())
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("${milestone.string("title")} · ${milestone.string("status")}", Modifier.weight(1f))
                    if (milestone.string("status") != "completed") {
                        OutlinedButton(onClick = { actions.updateMilestone(milestone.string("id"), "completed") }, enabled = !state.busy) {
                            Text("Done")
                        }
                    }
                }
            }
        }
        if (roadmaps.isEmpty()) EmptyState("No roadmap saved", "Generate a roadmap after enabling AI profile sharing.")

        OutlinedTextField(message, { message = it.take(5000) }, Modifier.fillMaxWidth(), label = { Text("Ask your career coach") }, minLines = 2)
        Button(
            onClick = { actions.sendCoachMessage(message.trim(), null); message = "" },
            enabled = !state.busy && message.trim().isNotEmpty() && consent,
        ) { Text("Send") }
        state.coachReply?.string("response")?.takeIf { it.isNotBlank() }?.let { Text(it) }
        messages.takeLast(16).forEach { element ->
            val item = element as? JsonObject ?: JsonObject(emptyMap())
            Text("${item.string("role").replaceFirstChar { it.uppercase() }}: ${item.string("content")}")
        }
        if (messages.isEmpty()) EmptyState("No conversation history", "Messages are saved by the backend to your account.")
    }
}

@Composable
private fun AcademyModule(state: CareerUiState, actions: CareerActions) {
    var selectedTrack by remember { mutableStateOf("") }
    var roadmapRole by remember { mutableStateOf("") }
    var skillNames by remember { mutableStateOf("") }
    var academyAssistantPrompt by remember { mutableStateOf("") }
    var projectTitle by remember { mutableStateOf("") }
    var projectDescription by remember { mutableStateOf("") }
    var projectSkills by remember { mutableStateOf("") }
    var projectUrl by remember { mutableStateOf("") }
    var evidenceSkill by remember { mutableStateOf("") }
    var evidenceDescription by remember { mutableStateOf("") }
    var evidenceUrl by remember { mutableStateOf("") }
    val answers = remember { mutableStateMapOf<String, String>() }
    val codeByExercise = remember { mutableStateMapOf<String, String>() }
    val tracks = state.academy?.arrayValue("tracks").orEmpty()

    SectionCard("Learning Academy") {
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedButton(onClick = actions.refreshAcademyDetails, enabled = !state.busy) { Text("Refresh Academy") }
        }
        if (tracks.isEmpty()) EmptyState("No learning tracks returned", "Track content is supplied by the existing Academy API.")
        tracks.forEach { element ->
            val track = element as? JsonObject ?: JsonObject(emptyMap())
            val id = track.string("id")
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(track.string("title"), fontWeight = FontWeight.SemiBold)
                Text("${track.string("category")} · ${track.string("level")}")
                val progress = track.objectValue("progress").string("percent").toDoubleOrNull() ?: 0.0
                LinearProgressIndicator({ (progress / 100).toFloat().coerceIn(0f, 1f) }, Modifier.fillMaxWidth())
                Text("${progress.toInt()}% complete")
                OutlinedButton(onClick = { selectedTrack = id; actions.loadAcademyTrack(id) }, enabled = !state.busy && id.isNotBlank()) {
                    Text(if (id == selectedTrack) "Selected track" else "Open track")
                }
            }
        }
        val trackData = state.academyTrack
        if (trackData != null && trackData.string("id") == selectedTrack) {
            Text(trackData.string("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            trackData.arrayValue("lessons").forEach { element ->
                val lesson = element as? JsonObject ?: JsonObject(emptyMap())
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(Modifier.weight(1f)) {
                        Text(lesson.string("title"))
                        Text(lesson.string("summary").ifBlank { lesson.string("description") }, style = MaterialTheme.typography.bodySmall)
                    }
                    if (lesson["completed_at"] == null || lesson["completed_at"].toString() == "null") {
                        OutlinedButton(
                            onClick = { actions.completeLesson(selectedTrack, lesson.string("id")) },
                            enabled = !state.busy,
                        ) { Text("Complete") }
                    } else Text("Done")
                }
            }
            val assessmentQuestions = trackData.objectValue("assessment").arrayValue("questions")
            if (assessmentQuestions.isNotEmpty()) {
                Text("Knowledge assessment", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                assessmentQuestions.forEach { element ->
                    val question = element as? JsonObject ?: JsonObject(emptyMap())
                    val id = question.string("id")
                    Text(question.string("prompt"))
                    question.arrayValue("options").forEach { option ->
                        val choice = option.textOrEmpty()
                        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                            Checkbox(checked = answers[id] == choice, onCheckedChange = { if (it) answers[id] = choice })
                            Text(choice)
                        }
                    }
                }
                Button(
                    onClick = { actions.submitAssessment(selectedTrack, answers.toMap()) },
                    enabled = !state.busy && answers.size == assessmentQuestions.size,
                ) { Text("Submit assessment") }
            }
            trackData.arrayValue("exercises").forEach { element ->
                val exercise = element as? JsonObject ?: JsonObject(emptyMap())
                val exerciseId = exercise.string("id")
                Text(exercise.string("title"), fontWeight = FontWeight.Medium)
                Text(exercise.string("prompt"))
                OutlinedTextField(
                    value = codeByExercise[exerciseId].orEmpty(),
                    onValueChange = { codeByExercise[exerciseId] = it.take(12_000) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Python solution") },
                    minLines = 5,
                )
                Button(
                    onClick = { actions.submitExercise(selectedTrack, exerciseId, codeByExercise[exerciseId].orEmpty()) },
                    enabled = !state.busy && codeByExercise[exerciseId].orEmpty().isNotBlank(),
                ) { Text("Run restricted exercise") }
            }
            val progress = trackData.objectValue("progress")
            if (progress["certificate_eligible"]?.toString() == "true") {
                Button(onClick = { actions.issueCertificate(selectedTrack) }, enabled = !state.busy) {
                    Text("Issue platform activity certificate")
                }
            }
        }
        state.academyResult?.let {
            Text("Latest result: ${it.string("score").ifBlank { it.string("rubric_score") }} · ${it.string("passed")}")
            it.string("evaluation_scope").takeIf(String::isNotBlank)?.let { scope -> Text(scope, style = MaterialTheme.typography.bodySmall) }
        }
        OutlinedTextField(roadmapRole, { roadmapRole = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Learning roadmap target role") })
        OutlinedTextField(skillNames, { skillNames = it.take(1000) }, Modifier.fillMaxWidth(), label = { Text("Skills to develop (comma separated)") })
        Button(
            onClick = {
                actions.generateAcademyRoadmap(
                    AcademyRoadmapRequest(
                        targetRole = roadmapRole.trim(),
                        skillsToDevelop = skillNames.split(",").map(String::trim).filter(String::isNotBlank).take(30),
                    ),
                )
            },
            enabled = !state.busy && roadmapRole.trim().length >= 2,
        ) { Text("Generate learning roadmap") }
        state.academyRoadmaps.forEach { roadmap ->
            Text("${roadmap.string("target_role")} · ${roadmap.string("updated_at")}")
            Text(roadmap.objectValue("roadmap").toString(), style = MaterialTheme.typography.bodySmall)
        }
        Text("Academy assistant", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedButton(onClick = actions.loadAcademyAssistantHistory, enabled = !state.busy) { Text("Load assistant history") }
        }
        OutlinedTextField(academyAssistantPrompt, { academyAssistantPrompt = it.take(4000) }, Modifier.fillMaxWidth(), label = { Text("Ask the Academy assistant") }, minLines = 2)
        Button(
            onClick = {
                actions.askAcademyAssistant(academyAssistantPrompt.trim(), selectedTrack.takeIf(String::isNotBlank))
                academyAssistantPrompt = ""
            },
            enabled = !state.busy && academyAssistantPrompt.trim().isNotEmpty(),
        ) { Text("Ask assistant") }
        state.academyAssistantReply?.string("answer")?.takeIf(String::isNotBlank)?.let { Text(it) }
        state.academyAssistantHistory.take(8).forEach { item ->
            Text("${item.string("role").replaceFirstChar { it.uppercase() }}: ${item.string("content")}")
        }

        Text("Project-based learning", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
        OutlinedTextField(projectTitle, { projectTitle = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Project title") })
        OutlinedTextField(projectDescription, { projectDescription = it.take(12_000) }, Modifier.fillMaxWidth(), label = { Text("Project description (min 40 characters)") }, minLines = 4)
        OutlinedTextField(projectSkills, { projectSkills = it.take(1000) }, Modifier.fillMaxWidth(), label = { Text("Skills (comma separated)") })
        OutlinedTextField(projectUrl, { projectUrl = it.take(2048) }, Modifier.fillMaxWidth(), label = { Text("Public project URL (optional)") })
        Button(
            onClick = {
                actions.submitProject(
                    AcademyProjectRequest(
                        title = projectTitle.trim(),
                        description = projectDescription.trim(),
                        skills = projectSkills.split(",").map(String::trim).filter(String::isNotBlank).take(20),
                        projectUrl = projectUrl.trim().ifBlank { null },
                    ),
                )
            },
            enabled = !state.busy && projectTitle.trim().length >= 2 && projectDescription.trim().length >= 40,
        ) { Text("Evaluate and save project description") }
        state.academyProjects.take(10).forEach { Text("Saved project: ${it.string("title")}") }

        Text("Submit skill evidence", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
        OutlinedTextField(evidenceSkill, { evidenceSkill = it.take(100) }, Modifier.fillMaxWidth(), label = { Text("Skill") })
        OutlinedTextField(evidenceDescription, { evidenceDescription = it.take(2000) }, Modifier.fillMaxWidth(), label = { Text("Evidence description (min 20 characters)") })
        OutlinedTextField(evidenceUrl, { evidenceUrl = it.take(2048) }, Modifier.fillMaxWidth(), label = { Text("Public evidence URL (required for portfolio/project)") })
        Button(
            onClick = {
                actions.submitEvidence(
                    AcademyEvidenceRequest(
                        skill = evidenceSkill.trim(),
                        evidenceType = if (evidenceUrl.isBlank()) "external_certificate" else "project",
                        description = evidenceDescription.trim(),
                        evidenceUrl = evidenceUrl.trim().ifBlank { null },
                    ),
                )
            },
            enabled = !state.busy && evidenceSkill.isNotBlank() && evidenceDescription.trim().length >= 20
                && (evidenceUrl.isBlank() || evidenceUrl.trim().startsWith("https://")),
        ) { Text("Submit evidence (marked unverified)") }
        Text(
            "Assessment and project evaluations are platform activity only. User-submitted evidence is not independently verified, and certificates are not external accreditation.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun BrandingModule(state: CareerUiState, actions: CareerActions) {
    var name by remember { mutableStateOf("") }
    var currentRole by remember { mutableStateOf("") }
    var targetRoles by remember { mutableStateOf("") }
    var industry by remember { mutableStateOf("") }
    var skills by remember { mutableStateOf("") }
    var about by remember { mutableStateOf("") }
    var experience by remember { mutableStateOf("") }
    var projects by remember { mutableStateOf("") }
    var linkedinUrl by remember { mutableStateOf("") }
    var portfolioUrl by remember { mutableStateOf("") }
    var github by remember { mutableStateOf("") }
    var tone by remember { mutableStateOf("professional") }
    var contentType by remember { mutableStateOf("linkedin_headline") }
    var generationRole by remember { mutableStateOf("") }
    var sourceText by remember { mutableStateOf("") }
    val profile = state.branding?.objectValue("profile")
    val consent = state.branding?.get("ai_data_consent")?.toString() == "true"

    SectionCard("Personal branding") {
        OutlinedButton(onClick = actions.refreshBranding, enabled = !state.busy) { Text("Load saved brand profile") }
        if (profile != null) {
            Text("Profile completeness ${state.branding?.objectValue("profile_strength")?.string("score").ifNullBlank("—")}/100")
            if (!consent) Text("AI brand generation requires enabling profile-sharing consent in Career Coach.", color = MaterialTheme.colorScheme.error)
        }
        OutlinedTextField(name.ifBlank { profile?.string("personal_name").orEmpty() }, { name = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Professional name") })
        OutlinedTextField(currentRole.ifBlank { profile?.string("current_role").orEmpty() }, { currentRole = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Current role") })
        OutlinedTextField(targetRoles.ifBlank { profile?.arrayValue("target_roles").orEmpty().joinToString { it.textOrEmpty() } }, { targetRoles = it.take(1000) }, Modifier.fillMaxWidth(), label = { Text("Target roles, comma separated") })
        OutlinedTextField(industry.ifBlank { profile?.string("industry").orEmpty() }, { industry = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Industry") })
        OutlinedTextField(skills.ifBlank { profile?.arrayValue("skills").orEmpty().joinToString { it.textOrEmpty() } }, { skills = it.take(2000) }, Modifier.fillMaxWidth(), label = { Text("Evidence-backed skills, comma separated") })
        OutlinedTextField(about.ifBlank { profile?.string("about").orEmpty() }, { about = it.take(5000) }, Modifier.fillMaxWidth(), label = { Text("About section") }, minLines = 4)
        OutlinedTextField(experience.ifBlank { profile?.arrayValue("experience").orEmpty().joinToString("\n") { it.textOrEmpty() } }, { experience = it.take(3000) }, Modifier.fillMaxWidth(), label = { Text("Experience facts, one per line") }, minLines = 3)
        OutlinedTextField(projects.ifBlank { profile?.arrayValue("projects").orEmpty().joinToString("\n") { it.textOrEmpty() } }, { projects = it.take(3000) }, Modifier.fillMaxWidth(), label = { Text("Project facts, one per line") }, minLines = 3)
        OutlinedTextField(linkedinUrl.ifBlank { profile?.string("linkedin_url").orEmpty() }, { linkedinUrl = it.take(2048) }, Modifier.fillMaxWidth(), label = { Text("LinkedIn URL (optional)") })
        OutlinedTextField(portfolioUrl.ifBlank { profile?.string("portfolio_url").orEmpty() }, { portfolioUrl = it.take(2048) }, Modifier.fillMaxWidth(), label = { Text("Portfolio URL (optional)") })
        OutlinedTextField(github.ifBlank { profile?.string("github_username").orEmpty() }, { github = it.take(39) }, Modifier.fillMaxWidth(), label = { Text("GitHub username") })
        Button(
            onClick = {
                actions.saveBrandProfile(
                    PersonalBrandProfile(
                        personalName = name.ifBlank { profile?.string("personal_name").orEmpty() },
                        currentRole = currentRole.ifBlank { profile?.string("current_role").orEmpty() },
                        targetRoles = targetRoles.ifBlank { profile?.arrayValue("target_roles").orEmpty().joinToString { it.textOrEmpty() } }.split(",").map(String::trim).filter(String::isNotBlank),
                        industry = industry.ifBlank { profile?.string("industry").orEmpty() },
                        skills = skills.ifBlank { profile?.arrayValue("skills").orEmpty().joinToString { it.textOrEmpty() } }.split(",").map(String::trim).filter(String::isNotBlank),
                        about = about.ifBlank { profile?.string("about").orEmpty() },
                        experience = experience.ifBlank { profile?.arrayValue("experience").orEmpty().joinToString("\n") { it.textOrEmpty() } }.lines().map(String::trim).filter(String::isNotBlank),
                        projects = projects.ifBlank { profile?.arrayValue("projects").orEmpty().joinToString("\n") { it.textOrEmpty() } }.lines().map(String::trim).filter(String::isNotBlank),
                        linkedinUrl = linkedinUrl.ifBlank { profile?.string("linkedin_url").orEmpty() }.ifBlank { null },
                        portfolioUrl = portfolioUrl.ifBlank { profile?.string("portfolio_url").orEmpty() }.ifBlank { null },
                        githubUsername = github.ifBlank { profile?.string("github_username").orEmpty() },
                        tone = tone,
                    ),
                )
            },
            enabled = !state.busy,
        ) { Text("Save branding profile") }

        Text("Generate an editable profile draft", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
        ChoiceField("Content type", contentType, listOf("linkedin_headline", "linkedin_about", "linkedin_experience", "linkedin_skills", "profile_optimization", "branding_guidance", "professional_bio", "portfolio_project", "linkedin_post")) { contentType = it }
        ChoiceField("Tone", tone, listOf("professional", "technical", "executive", "entry_level", "experienced", "concise")) { tone = it }
        OutlinedTextField(generationRole, { generationRole = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Target role") })
        OutlinedTextField(sourceText, { sourceText = it.take(12_000) }, Modifier.fillMaxWidth(), label = { Text("Source facts for generation") }, minLines = 3)
        Button(
            onClick = { actions.generateBrandContent(BrandGenerateRequest(contentType, tone, generationRole.trim(), sourceText = sourceText.trim())) },
            enabled = !state.busy && consent && (name.isNotBlank() || profile?.string("personal_name").orEmpty().isNotBlank() || generationRole.trim().length >= 2 || sourceText.trim().length >= 2),
        ) { Text("Generate and save draft") }
        state.brandDraft?.let { draft ->
            Text(draft.string("title"), fontWeight = FontWeight.SemiBold)
            Text(draft.string("content"))
        }
        state.brandVersions.forEach { version ->
            var editTitle by remember(version.string("id"), version.string("updated_at")) { mutableStateOf(version.string("title")) }
            var editContent by remember(version.string("id"), version.string("updated_at")) { mutableStateOf(version.string("content")) }
            OutlinedTextField(editTitle, { editTitle = it.take(160) }, Modifier.fillMaxWidth(), label = { Text("Saved version title") })
            OutlinedTextField(editContent, { editContent = it.take(20_000) }, Modifier.fillMaxWidth(), label = { Text(version.string("content_type")) }, minLines = 3)
            OutlinedButton(
                onClick = { actions.editBrandVersion(version.string("id"), BrandVersionEditRequest(editTitle.trim(), editContent.trim())) },
                enabled = !state.busy && editTitle.isNotBlank() && editContent.isNotBlank(),
            ) { Text("Save version edits") }
        }
    }
}

@Composable
private fun SalaryModule(state: CareerUiState, actions: CareerActions) {
    var role by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var offerName by remember { mutableStateOf("") }
    var company by remember { mutableStateOf("") }
    var currency by remember { mutableStateOf("USD") }
    var base by remember { mutableStateOf("") }
    var variable by remember { mutableStateOf("") }
    var bonus by remember { mutableStateOf("") }
    var equity by remember { mutableStateOf("") }
    var selectedOffers by remember { mutableStateOf(setOf<String>()) }
    var comparisonTitle by remember { mutableStateOf("") }
    var taxRate by remember { mutableStateOf("0") }
    var monthlyDeduction by remember { mutableStateOf("0") }
    var targetCompensation by remember { mutableStateOf("") }
    var achievements by remember { mutableStateOf("") }
    var priorities by remember { mutableStateOf("") }

    SectionCard("Salary intelligence and offer comparison") {
        OutlinedTextField(role, { role = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Role for listing benchmarks") })
        OutlinedTextField(location, { location = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Location") })
        Button(onClick = { actions.loadSalary(role.trim(), location.trim()) }, enabled = !state.busy && role.trim().length >= 2) { Text("Load disclosed listing benchmarks") }
        state.salary?.groups?.forEach { group ->
            Text("${group.currency} / ${group.reportingPeriod}: ${group.minimum} – ${group.maximum}; median ${group.median} · n=${group.sampleSize}")
        }
        if (state.salary?.groups.isNullOrEmpty() && state.salary != null) {
            EmptyState("No disclosed salary listings", state.salary.message ?: "No salary estimate is available for this search.")
        }
        OutlinedButton(onClick = actions.refreshSalaryOffers, enabled = !state.busy) { Text("Load saved offers") }
        OutlinedTextField(offerName, { offerName = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Offer name") })
        OutlinedTextField(company, { company = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Company") })
        OutlinedTextField(currency, { currency = it.take(3).uppercase() }, Modifier.fillMaxWidth(), label = { Text("Currency (ISO 3-letter)") })
        OutlinedTextField(base, { base = it.take(18) }, Modifier.fillMaxWidth(), label = { Text("Annual base") })
        OutlinedTextField(variable, { variable = it.take(18) }, Modifier.fillMaxWidth(), label = { Text("Annual variable") })
        OutlinedTextField(bonus, { bonus = it.take(18) }, Modifier.fillMaxWidth(), label = { Text("Annual bonus") })
        OutlinedTextField(equity, { equity = it.take(18) }, Modifier.fillMaxWidth(), label = { Text("Annualized equity value") })
        val offerRequest = SalaryOfferRequest(
            name = offerName.trim(),
            company = company.trim(),
            role = role.trim(),
            location = location.trim(),
            currency = currency.trim(),
            annualBase = base.toDoubleOrNull() ?: 0.0,
            annualVariable = variable.toDoubleOrNull() ?: 0.0,
            annualBonus = bonus.toDoubleOrNull() ?: 0.0,
            annualEquity = equity.toDoubleOrNull() ?: 0.0,
        )
        Button(
            onClick = {
                actions.createSalaryOffer(offerRequest)
                offerName = ""; base = ""; variable = ""; bonus = ""; equity = ""
            },
            enabled = !state.busy && offerName.trim().length >= 2 && currency.length == 3 && listOf(base, variable, bonus, equity).any { (it.toDoubleOrNull() ?: 0.0) > 0 },
        ) { Text("Save offer") }
        state.salaryOffers.forEach { offer ->
            val id = offer.string("id")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Checkbox(checked = id in selectedOffers, onCheckedChange = { checked ->
                    selectedOffers = if (checked && selectedOffers.size < 2) selectedOffers + id
                    else if (!checked) selectedOffers - id else selectedOffers
                })
                Column(Modifier.weight(1f)) {
                    Text("${offer.string("name")} · ${offer.string("company")}", fontWeight = FontWeight.Medium)
                    Text("${offer.string("currency")} ${offer.string("annual_total")} annual total")
                    Text("Base ${offer.string("annual_base")} · variable ${offer.string("annual_variable")} · bonus ${offer.string("annual_bonus")} · equity ${offer.string("annual_equity")}")
                }
                OutlinedButton(onClick = { actions.deleteSalaryOffer(id) }, enabled = !state.busy) { Text("Remove") }
            }
        }
        if (selectedOffers.size == 2) {
            val pair = state.salaryOffers.filter { it.string("id") in selectedOffers }
            if (pair.size == 2) {
                val first = pair[0]
                val second = pair[1]
                val firstCurrency = first.string("currency")
                val secondCurrency = second.string("currency")
                Text(
                    if (firstCurrency == secondCurrency) {
                        "Comparison (same currency): ${first.string("name")} ${first.string("annual_total")} vs ${second.string("name")} ${second.string("annual_total")} ${firstCurrency}. No tax, benefits, or liquidity assumptions included."
                    } else {
                        "Selected offers use different currencies ($firstCurrency and $secondCurrency); totals are shown separately with no invented exchange rate."
                    },
                )
                OutlinedTextField(comparisonTitle, { comparisonTitle = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Comparison title") })
                Button(
                    onClick = {
                        val comparisonIds = selectedOffers.toList().sorted()
                        if (comparisonIds.size == 2) {
                            actions.createSalaryComparison(SalaryOfferComparisonRequest(title = comparisonTitle.ifBlank { "Offer comparison" }, offerIds = comparisonIds))
                            comparisonTitle = ""
                        }
                    },
                    enabled = !state.busy && comparisonTitle.isNotBlank() && selectedOffers.size == 2,
                ) { Text("Save comparison") }
            }
        }
        state.salaryComparisons.forEach { comparison ->
            Text("${comparison.string("title")} · ${comparison.arrayValue("offer_ids").joinToString { it.toString() }}")
        }
    }
    SectionCard("Compensation breakdown and negotiation preparation") {
        OutlinedTextField(taxRate, { taxRate = it.take(5) }, Modifier.fillMaxWidth(), label = { Text("Illustrative tax rate (%)") })
        OutlinedTextField(monthlyDeduction, { monthlyDeduction = it.take(18) }, Modifier.fillMaxWidth(), label = { Text("Monthly deductions") })
        Button(
            onClick = {
                actions.calculateSalary(
                    SalaryCalculatorRequest(
                        currency = currency,
                        annualFixed = offerRequest.annualBase,
                        annualVariable = offerRequest.annualVariable,
                        annualBonus = offerRequest.annualBonus,
                        annualEquity = offerRequest.annualEquity,
                        annualTaxRatePercent = taxRate.toDoubleOrNull() ?: 0.0,
                        monthlyDeductions = monthlyDeduction.toDoubleOrNull() ?: 0.0,
                    ),
                )
            },
            enabled = !state.busy && currency.length == 3 && offerRequest.annualBase > 0,
        ) { Text("Calculate entered compensation") }
        state.salaryCalculation?.let { result ->
            Text("Annual total ${result.string("currency")} ${result.string("annual_total_compensation")}")
            Text("Illustrative monthly take-home ${result.string("estimated_monthly_take_home")}")
            Text(result.objectValue("assumptions").string("tax_notice"), style = MaterialTheme.typography.bodySmall)
        }
        OutlinedTextField(targetCompensation, { targetCompensation = it.take(18) }, Modifier.fillMaxWidth(), label = { Text("Target compensation (optional)") })
        OutlinedTextField(achievements, { achievements = it.take(3000) }, Modifier.fillMaxWidth(), label = { Text("Documented achievements") })
        OutlinedTextField(priorities, { priorities = it.take(1500) }, Modifier.fillMaxWidth(), label = { Text("Negotiation priorities") })
        Button(
            onClick = {
                actions.salaryGuidance(
                    SalaryNegotiationRequest(
                        requestType = "strategy",
                        role = role.trim(),
                        company = company.trim(),
                        location = location.trim(),
                        currency = currency,
                        currentOffer = offerRequest.annualBase.takeIf { it > 0 },
                        targetCompensation = targetCompensation.toDoubleOrNull(),
                        achievements = achievements.trim(),
                        priorities = priorities.trim(),
                    ),
                )
            },
            enabled = !state.busy && role.trim().length >= 2 && currency.length == 3 && (state.coach?.get("ai_data_consent")?.toString() == "true"),
        ) { Text("Request negotiation guidance") }
        state.salaryGuidance?.let { result ->
            Text(result.string("guidance"))
            Text(result.string("notice"), style = MaterialTheme.typography.bodySmall)
        }
        Text("Comparisons use only saved user-entered offers. Benchmarks reflect salary-disclosed listings, not market-wide estimates; compensation calculations are not tax advice.", style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun PreferencesModule(state: CareerUiState, actions: CareerActions) {
    val current = state.preferences ?: SearchPreferences()
    var titles by remember(current) { mutableStateOf(current.preferredTitles.joinToString(", ")) }
    var locations by remember(current) { mutableStateOf(current.preferredLocations.joinToString(", ")) }
    var followUpDays by remember(current) { mutableStateOf(current.applicationFollowUpDays.toString()) }
    var reminderHours by remember(current) { mutableStateOf(current.interviewReminderHours.joinToString(", ")) }
    var emailReminders by remember(current) { mutableStateOf(current.emailReminders) }
    SectionCard("Account settings and job preferences") {
        OutlinedTextField(titles, { titles = it.take(2000) }, Modifier.fillMaxWidth(), label = { Text("Preferred role titles") })
        OutlinedTextField(locations, { locations = it.take(2000) }, Modifier.fillMaxWidth(), label = { Text("Preferred locations") })
        OutlinedTextField(followUpDays, { followUpDays = it.filter(Char::isDigit).take(2) }, Modifier.fillMaxWidth(), label = { Text("Default follow-up days (1–60)") })
        OutlinedTextField(reminderHours, { reminderHours = it.filter { char -> char.isDigit() || char == ',' }.take(40) }, Modifier.fillMaxWidth(), label = { Text("Interview reminder hours (comma-separated, 0–720)") })
        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Checkbox(checked = emailReminders, onCheckedChange = { emailReminders = it })
            Text("Request reminder emails (delivery depends on backend configuration)")
        }
        Button(
            onClick = {
                actions.savePreferences(
                    current.copy(
                        preferredTitles = titles.split(",").map(String::trim).filter(String::isNotBlank).take(20),
                        preferredLocations = locations.split(",").map(String::trim).filter(String::isNotBlank).take(20),
                        applicationFollowUpDays = followUpDays.toIntOrNull()?.coerceIn(1, 60) ?: 7,
                        interviewReminderHours = reminderHours.split(",").mapNotNull { it.trim().toIntOrNull()?.takeIf { hour -> hour in 0..720 } }.distinct().take(8),
                        emailReminders = emailReminders,
                    ),
                )
            },
            enabled = !state.busy,
        ) { Text("Save account settings") }
        Text(
            "The backend exposes career search/reminder preferences, but no general personal-account profile edit endpoint. Email and identity are read-only here.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun ChoiceField(label: String, value: String, choices: List<String>, onSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) { Text("$label: $value") }
        DropdownMenu(expanded, { expanded = false }) {
            choices.forEach { choice ->
                DropdownMenuItem(text = { Text(choice.replace('_', ' ')) }, onClick = { expanded = false; onSelected(choice) })
            }
        }
    }
}

private fun isOffsetDateTime(value: String): Boolean = try {
    OffsetDateTime.parse(value.trim())
    true
} catch (_: DateTimeParseException) {
    false
}

private fun String?.ifNullBlank(default: String): String = if (this.isNullOrBlank()) default else this
