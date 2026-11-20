package com.resumeats.checker.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.resumeats.checker.data.AnalysisResponse
import com.resumeats.checker.data.ResumeProfile
import kotlinx.coroutines.launch

@Composable
fun ResumeScreen(
    state: CareerUiState,
    onAnalyze: (String, ByteArray, String) -> Unit,
    onUpload: (String, ByteArray) -> Unit,
    onRefresh: () -> Unit,
    onDismiss: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var selectedResume by remember { mutableStateOf<PickedResume?>(null) }
    var jobDescription by remember { mutableStateOf("") }
    var pickerError by remember { mutableStateOf<String?>(null) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            scope.launch {
                try {
                    selectedResume = readResumeDocument(context, uri)
                    pickerError = null
                } catch (error: Exception) {
                    pickerError = error.message ?: "The selected file could not be read."
                }
            }
        }
    }

    LaunchedEffect(Unit) { onRefresh() }
    val analysis = state.analysis
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("Resume intelligence", "Your document is sent securely to the configured backend for analysis.") }
        item {
            if (state.error != null) ErrorNotice(state.error, onDismiss)
            else if (!state.notice.isNullOrBlank()) NoticeText(state.notice)
            pickerError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        }
        item {
            SectionCard("Analyze resume against a role") {
                OutlinedButton(onClick = { picker.launch(arrayOf("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")) }) {
                    Text(selectedResume?.fileName ?: "Choose PDF or DOCX")
                }
                OutlinedTextField(
                    value = jobDescription,
                    onValueChange = { jobDescription = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Job description") },
                    minLines = 5,
                )
                Text("The backend requires at least five words in the job description and validates the uploaded document.", style = MaterialTheme.typography.bodySmall)
                Button(
                    enabled = !state.busy && selectedResume != null && jobDescription.trim().split(Regex("\\s+")).size >= 5,
                    onClick = {
                        selectedResume?.let { onAnalyze(it.fileName, it.bytes, jobDescription) }
                    },
                ) { Text("Analyze resume") }
            }
        }
        if (analysis != null && state.analysisFileName == selectedResume?.fileName) {
            item { AnalysisResult(analysis) }
        }
        item {
            SectionCard("Saved resume history") {
                if (state.resumes.isEmpty()) {
                    EmptyState("No saved resume versions", "Save a selected document to your authenticated profile to build its version history.")
                }
                selectedResume?.let { document ->
                    Button(
                        onClick = { onUpload(document.fileName, document.bytes) },
                        enabled = !state.busy,
                    ) { Text("Save selected resume to profile") }
                }
                if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            }
        }
        items(state.resumes) { resume -> ResumeHistoryItem(resume) }
    }
}

@Composable
private fun AnalysisResult(report: AnalysisResponse) {
    SectionCard("Estimated match score") {
        Text("${report.overallScore.toInt()} / 100", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Text("${report.scoreLabel} · ${report.matchTier}")
        Text(report.summary)
        report.categoryScores.forEach { category ->
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(category.name, fontWeight = FontWeight.Medium)
                    Text("${category.score.toInt()} / ${category.maxScore.toInt()}")
                }
                LinearProgressIndicator(
                    progress = { (category.score / category.maxScore).toFloat().coerceIn(0f, 1f) },
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(category.explanation, style = MaterialTheme.typography.bodySmall)
            }
        }
        if (report.keywordsFound.isNotEmpty()) {
            Text("Relevant keywords found", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text(report.keywordsFound.take(30).joinToString(" · "))
        }
        if (report.matchedRequirements.isNotEmpty()) {
            Text("Requirements supported by resume evidence", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            report.matchedRequirements.take(12).forEach {
                Text(
                    listOf(it.requirement, it.category, it.evidenceStrength).filter { value -> value.isNotBlank() }.joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        if (report.missingRequirements.isNotEmpty()) {
            Text("Missing or weak evidence", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            report.missingRequirements.take(12).forEach { requirement ->
                val classification = listOf(requirement.category, requirement.importance)
                    .filter { it.isNotBlank() }
                    .joinToString(" · ")
                Text(
                    "• ${requirement.requirement} ($classification): ${requirement.reason}",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        if (report.recommendations.isNotEmpty()) {
            Text("Recommended improvements", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            report.recommendations.take(8).forEach {
                Text("${it.title}: ${it.description}", style = MaterialTheme.typography.bodySmall)
            }
        }
        Text(report.limitationsDisclaimer, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ResumeHistoryItem(resume: ResumeProfile) {
    SectionCard(resume.title) {
        Text(if (resume.isPrimary) "Primary resume" else "Saved version", color = MaterialTheme.colorScheme.primary)
        if (resume.skills.isNotEmpty()) Text("Detected skills: ${resume.skills.take(10).joinToString()}")
        Text("Updated ${resume.updatedAt}", style = MaterialTheme.typography.bodySmall)
    }
}
