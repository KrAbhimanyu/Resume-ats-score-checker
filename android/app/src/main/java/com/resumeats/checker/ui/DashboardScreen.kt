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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

@Composable
fun DashboardScreen(
    state: CareerUiState,
    onRefresh: () -> Unit,
    onNavigate: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val dashboard = state.dashboard
    val profile = dashboard?.objectValue("profile") ?: JsonObject(emptyMap())
    val progress = dashboard?.objectValue("progress") ?: JsonObject(emptyMap())
    val score = dashboard?.objectValue("career_score") ?: JsonObject(emptyMap())
    val timeline = dashboard?.arrayValue("timeline").orEmpty()
    val opportunities = dashboard?.arrayValue("opportunities").orEmpty()

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            PageTitle("Your career workspace", "Progress and next steps from your saved profile and activity.")
        }
        item {
            if (state.error != null) ErrorNotice(state.error, onDismiss)
            else if (!state.notice.isNullOrBlank()) NoticeText(state.notice)
        }
        item {
            if (dashboard == null) {
                SectionCard("Career dashboard") {
                    EmptyState(
                        "No dashboard data yet",
                        "The authenticated command-center API has not returned profile data.",
                    )
                    Button(onClick = onRefresh, enabled = !state.busy) { Text("Refresh career dashboard") }
                }
            } else {
                SectionCard("Career profile") {
                    Text(profile.string("primary_resume_title").ifBlank { "No primary resume saved" }, fontWeight = FontWeight.SemiBold)
                    Text("Documented skills: ${profile.string("documented_skills").ifBlank { "0" }}")
                    Text("Target roles: ${profile.arrayValue("target_roles").joinToString { it.textOrEmpty() }.ifBlank { "None saved" }}")
                    Text(
                        "Career workspace completeness: ${score.string("value").ifBlank { "0" }} / 100",
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
        item {
            SectionCard("Your activity") {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Metric("Applications", progress.string("applications"))
                    Metric("Saved jobs", progress.string("saved_jobs"))
                    Metric("Learning", progress.string("completed_learning"))
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Metric("Active goals", progress.string("active_goals"))
                    Metric("Tracked skills", progress.string("tracked_skills"))
                    Metric("Unread", progress.string("unread_notifications"))
                }
            }
        }
        item {
            SectionCard("Recommended next actions") {
                Text("Keep your profile current and use evidence-backed suggestions rather than adding skills you do not have.")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { onNavigate("resume") }) { Text("Analyze resume") }
                    OutlinedButton(onClick = { onNavigate("jobs") }) { Text("Find jobs") }
                }
                OutlinedButton(onClick = { onNavigate("career") }) { Text("Open career tools") }
            }
        }
        item {
            SectionCard("Recommended opportunities") {
                if (opportunities.isEmpty()) {
                    EmptyState("No recommendations returned", "Recommendations appear after authorized job listings are available and a profile can be matched.")
                    OutlinedButton(onClick = { onNavigate("jobs") }) { Text("Search authorized listings") }
                }
            }
        }
        items(opportunities.take(5)) { item ->
            val opportunity = item as? JsonObject ?: JsonObject(emptyMap())
            SectionCard(opportunity.string("title").ifBlank { "Opportunity" }) {
                Text(opportunity.string("company_name"))
                Text(opportunity.string("location"))
                Text("Resume match: ${opportunity.string("match_score").ifBlank { "Not available" }}")
                Text("Listing source: ${opportunity.string("source").ifBlank { "Not disclosed" }}", style = MaterialTheme.typography.bodySmall)
            }
        }
        item {
            SectionCard("Recent activity") {
                if (timeline.isEmpty()) {
                    EmptyState("No recent activity", "Your saved resume, applications, learning, and career actions will appear here.")
                }
            }
        }
        items(timeline.take(8)) { item ->
            val activity = item as? JsonObject ?: JsonObject(emptyMap())
            SectionCard(activity.string("title").ifBlank { activity.string("event_type").ifBlank { "Career activity" } }) {
                Text(activity.string("description").ifBlank { activity.string("message") })
                Text(activity.string("created_at"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Text(value.ifBlank { "0" }, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
