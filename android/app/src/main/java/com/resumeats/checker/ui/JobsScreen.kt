package com.resumeats.checker.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.resumeats.checker.data.JobListing
import com.resumeats.checker.data.TailoringApprovalRequest
import com.resumeats.checker.data.TailoringChangeApproval
import kotlinx.serialization.json.JsonObject

@Composable
fun JobsScreen(
    state: CareerUiState,
    onSearch: (String, String, String, Int) -> Unit,
    onSave: (JobListing) -> Unit,
    onTrack: (JobListing) -> Unit,
    onRefreshSaved: () -> Unit,
    onDismiss: () -> Unit,
    onMatch: (String) -> Unit,
    onTailor: (String, String?) -> Unit,
    onUpdateTailoring: (String, TailoringApprovalRequest) -> Unit,
    onSaveTailoredVersion: (String) -> Unit,
) {
    var query by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var country by remember { mutableStateOf("gb") }
    var showSaved by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { onRefreshSaved() }

    val visibleJobs = if (showSaved) state.savedJobListings else state.jobs
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("Job intelligence", "Search only configured, authorized job providers. Results are real source listings.") }
        item {
            if (state.error != null) ErrorNotice(state.error, onDismiss)
            else if (!state.notice.isNullOrBlank()) NoticeText(state.notice)
        }
        item {
            SectionCard("Search authorized listings") {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it.take(160) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Role or keyword") },
                    singleLine = true,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = location,
                        onValueChange = { location = it.take(120) },
                        modifier = Modifier.weight(1f),
                        label = { Text("Location") },
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = country,
                        onValueChange = { country = it.trim().take(2).lowercase() },
                        modifier = Modifier.weight(0.55f),
                        label = { Text("Country") },
                        singleLine = true,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = { showSaved = false; onSearch(query, location, country, 1) },
                        enabled = !state.busy && query.isNotBlank() && country.length == 2,
                    ) {
                        Text("Search")
                    }
                    OutlinedButton(onClick = { showSaved = true; onRefreshSaved() }, enabled = !state.busy) {
                        Text("Saved jobs")
                    }
                }
            }
        }
        if (visibleJobs.isEmpty()) {
            item {
                SectionCard(if (showSaved) "Saved jobs" else "Search results") {
                    EmptyState(
                        if (showSaved) "No saved jobs" else "No job listings to show",
                        if (showSaved) "Run a search and save an opportunity, or try a different role."
                        else "Search for a role. Listings appear only when configured providers return current results.",
                    )
                }
            }
        }
        items(visibleJobs, key = { it.id }) { job ->
            JobCard(
                job = job,
                saved = job.id in state.savedJobs,
                onSave = { onSave(job) },
                onTrack = { onTrack(job) },
                busy = state.busy,
                match = state.jobMatch.takeIf { state.jobMatchId == job.id },
                tailoring = state.tailoringReview.takeIf { state.tailoringJobId == job.id },
                versionSaved = state.tailoredResumeVersion != null && state.tailoringJobId == job.id,
                savedVersionTitle = state.tailoredResumeVersion?.string("title"),
                onMatch = { onMatch(job.id) },
                onTailor = { onTailor(job.id, null) },
                onUpdateTailoring = onUpdateTailoring,
                onSaveTailoredVersion = onSaveTailoredVersion,
            )
        }
        if (!showSaved && state.jobsHaveMore && state.jobPage < 50) {
            item {
                OutlinedButton(
                    onClick = { onSearch(query, location, country, state.jobPage + 1) },
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Load next page") }
            }
        }
    }
}

@Composable
private fun JobCard(
    job: JobListing,
    saved: Boolean,
    onSave: () -> Unit,
    onTrack: () -> Unit,
    busy: Boolean,
    match: JsonObject?,
    tailoring: JsonObject?,
    versionSaved: Boolean,
    savedVersionTitle: String?,
    onMatch: () -> Unit,
    onTailor: () -> Unit,
    onUpdateTailoring: (String, TailoringApprovalRequest) -> Unit,
    onSaveTailoredVersion: (String) -> Unit,
) {
    var showDetails by remember(job.id) { mutableStateOf(false) }
    SectionCard(job.title) {
        Text(job.companyName)
        if (job.location.isNotBlank()) Text(job.location)
        val salary = if (job.salaryMin != null && job.salaryMax != null) {
            "Disclosed salary: ${job.salaryMin}–${job.salaryMax} ${job.salaryCurrency.orEmpty()}"
        } else null
        salary?.let { Text(it) }
        val attributes = listOfNotNull(job.remoteType, job.employmentType).filter { it.isNotBlank() }
        if (attributes.isNotEmpty()) Text(attributes.joinToString(" · "))
        Text("Source: ${job.sourceLabel ?: "Not available"}")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onSave, enabled = !saved) { Text(if (saved) "Saved" else "Save job") }
            OutlinedButton(onClick = onTrack) { Text("Track application") }
            OutlinedButton(onClick = { showDetails = true }) { Text("Details") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onMatch, enabled = !busy) { Text("Match resume") }
            OutlinedButton(onClick = onTailor, enabled = !busy) { Text("Tailor resume") }
        }
        match?.let { result ->
            val matchedSkills = result.arrayValue("matched_skills").mapNotNull { skill ->
                (skill as? JsonObject)?.string("skill") ?: skill.textOrEmpty().takeIf { it.isNotBlank() }
            }
            Text(
                "Compatibility estimate: ${result.string("score")}% — ${result.string("score_label")}",
                style = androidx.compose.material3.MaterialTheme.typography.titleSmall,
            )
            Text("Matched skills: ${matchedSkills.joinToString().ifBlank { "None returned" }}")
            Text("Missing required skills: ${result.arrayValue("missing_required_skills").joinToString { it.textOrEmpty() }.ifBlank { "None returned" }}")
            Text("Recommended actions: ${result.arrayValue("recommendations").joinToString { it.textOrEmpty() }.ifBlank { "No recommendations returned" }}")
            Text(result.string("disclaimer"), style = androidx.compose.material3.MaterialTheme.typography.bodySmall)
        }
        tailoring?.let { review ->
            val sessionId = review.string("id")
            val changes = review.arrayValue("changes").mapNotNull { it as? JsonObject }
            val accepted = remember(sessionId) { mutableStateMapOf<String, Boolean>() }
            val proposed = remember(sessionId) { mutableStateMapOf<String, String>() }
            Text("Tailoring suggestions (review each edit)", style = androidx.compose.material3.MaterialTheme.typography.titleSmall)
            changes.forEach { change ->
                val id = change.string("id")
                val initialAccepted = change.string("is_accepted") == "true"
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Checkbox(
                        checked = accepted[id] ?: initialAccepted,
                        onCheckedChange = { accepted[id] = it },
                        enabled = !busy && !versionSaved && id.isNotBlank(),
                    )
                    Column {
                        Text(change.string("rationale"))
                        OutlinedTextField(
                            value = proposed[id] ?: change.string("proposed_text"),
                            onValueChange = { proposed[id] = it.take(4000) },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text(change.string("section").ifBlank { "Suggested edit" }) },
                            minLines = 2,
                            enabled = !busy && !versionSaved,
                        )
                    }
                }
            }
            val approvals = changes.map { change ->
                val id = change.string("id")
                TailoringChangeApproval(
                    id = id,
                    isAccepted = accepted[id] ?: (change.string("is_accepted") == "true"),
                    proposedText = proposed[id]?.takeIf { it != change.string("proposed_text") },
                )
            }
            OutlinedButton(
                onClick = { onUpdateTailoring(sessionId, TailoringApprovalRequest(approvals)) },
                enabled = !busy && !versionSaved && sessionId.isNotBlank() && approvals.isNotEmpty(),
            ) { Text("Save review decisions") }
            OutlinedButton(
                onClick = { onSaveTailoredVersion(sessionId) },
                enabled = !busy && !versionSaved && approvals.any { it.isAccepted },
            ) { Text(if (versionSaved) "New resume version saved" else "Save approved edits as a new resume version") }
            if (versionSaved) {
                Text("Saved version: ${savedVersionTitle.orEmpty()}")
            }
            Text(review.string("disclaimer"), style = androidx.compose.material3.MaterialTheme.typography.bodySmall)
        }
    }
    if (showDetails) JobDetailsDialog(job, onDismiss = { showDetails = false })
}

@Composable
private fun JobDetailsDialog(job: JobListing, onDismiss: () -> Unit) {
    val uriHandler = LocalUriHandler.current
    var linkError by remember(job.id) { mutableStateOf<String?>(null) }
    androidx.compose.material3.AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(job.title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(job.companyName)
                Text(job.location)
                Text("Source: ${job.sourceLabel ?: "Not available"}")
                Text(job.description.ifBlank { "The provider did not include a job description." })
                linkError?.let { Text(it, color = androidx.compose.material3.MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = {
            androidx.compose.material3.TextButton(
                enabled = !job.originalUrl.isNullOrBlank(),
                onClick = {
                    val url = job.originalUrl.orEmpty()
                    if (url.startsWith("https://", true) || url.startsWith("http://", true)) {
                        try {
                            uriHandler.openUri(url)
                        } catch (_: android.content.ActivityNotFoundException) {
                            linkError = "No browser is available to open this listing."
                        } catch (_: IllegalArgumentException) {
                            linkError = "This listing link could not be opened."
                        }
                    } else {
                        linkError = "The source did not provide a valid web link."
                    }
                },
            ) { Text("Open original listing") }
        },
        dismissButton = {
            androidx.compose.material3.TextButton(onClick = onDismiss) { Text("Close") }
        },
    )
}
