package com.resumeats.checker.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.resumeats.checker.data.BusinessPlan

@Composable
fun AccountScreen(
    state: CareerUiState,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
    onDismiss: () -> Unit,
) {
    LaunchedEffect(Unit) { onRefresh() }
    val entitlements = state.entitlements
    val planInfo = entitlements?.objectValue("plan")
    val features = entitlements?.objectValue("features")
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("Account and subscription", "Subscription and credit information is sourced from your authenticated account APIs.") }
        item {
            if (state.error != null) ErrorNotice(state.error, onDismiss)
            else if (!state.notice.isNullOrBlank()) NoticeText(state.notice)
        }
        item {
            SectionCard("Profile") {
                Text(state.user?.email.orEmpty(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text("Account ID: ${state.user?.id.orEmpty()}", style = MaterialTheme.typography.bodySmall)
                Text("Created ${state.user?.createdAt.orEmpty()}", style = MaterialTheme.typography.bodySmall)
                OutlinedButton(onClick = onLogout, enabled = !state.busy) { Text("Sign out") }
            }
        }
        item {
            SectionCard("Current plan") {
                if (entitlements == null || planInfo == null) {
                    EmptyState("Subscription details not loaded", "Refresh to retrieve the plan and features active for this account.")
                    OutlinedButton(onClick = onRefresh, enabled = !state.busy) { Text("Refresh account") }
                } else {
                    Text(planInfo.string("name").ifBlank { "Free" }, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("Tier: ${planInfo.string("tier").ifBlank { "free" }}")
                    Text("Billing: ${planInfo.string("billing_interval").ifBlank { "free" }}")
                    Text("Status: ${entitlements.string("status").ifBlank { "active" }}")
                    entitlements.string("provider").takeIf { it.isNotBlank() }?.let { Text("Payment provider: $it") }
                    entitlements.string("current_period_end").takeIf { it.isNotBlank() }?.let { Text("Period ends: $it") }
                    if (entitlements["cancel_at_period_end"]?.toString() == "true") {
                        Text("Cancellation is scheduled at the end of the current billing period.")
                    }
                    if (features != null && features.isNotEmpty()) {
                        Text("Active features", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                        features.forEach { (name, enabled) ->
                            Text("${name.replace('_', ' ')}: ${enabled}")
                        }
                    }
                }
            }
        }
        item {
            SectionCard("AI credits") {
                if (state.credits == null) {
                    EmptyState("Credit balance not loaded", "Refresh to retrieve the current balance from the server.")
                } else {
                    Text("${state.credits.available} available", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text("${state.credits.balance} total · ${state.credits.reserved} reserved")
                    Text("The backend controls credit consumption and plan entitlements.", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        item {
            SectionCard("Available plans") {
                val business = state.businessStatus
                Text("${business?.activePlans ?: 0} active subscription plans")
                if (state.plans.isEmpty()) {
                    EmptyState("No purchasable plans returned", "Only active plans configured by the service are shown.")
                }
            }
        }
        items(state.plans, key = { it.id }) { plan -> PlanCard(plan) }
        item {
            SectionCard("Checkout availability") {
                val status = state.businessStatus
                Text(
                    if (status?.checkoutConfigured == true) {
                        "The server reports ${status.paymentProvider ?: "a configured provider"} checkout is configured."
                    } else {
                        "No payment provider is configured on the server."
                    },
                )
                Text(
                    "This Android client is read-only for subscriptions. Checkout currently returns web-provider flows; mobile checkout and callback verification are not implemented here. No payment is initiated or confirmed in this app.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (status?.admin == true) {
                    Text("Business administrator access is enabled for this account.")
                }
            }
        }
    }
}

@Composable
private fun PlanCard(plan: BusinessPlan) {
    SectionCard(plan.name) {
        Text("${plan.tier.replaceFirstChar { it.uppercase() }} · ${plan.billingInterval}")
        val price = plan.priceMinor?.let { amount ->
            "${plan.currency} %.2f".format(java.util.Locale.ROOT, amount / 100.0)
        } ?: "Price not configured"
        Text(price, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Text("${plan.creditsGrant} credits per billing period")
        if (plan.entitlements.isNotEmpty()) {
            plan.entitlements.forEach { (feature, enabled) ->
                Text("${feature.replace('_', ' ')}: $enabled")
            }
        }
    }
}
