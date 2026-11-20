package com.resumeats.checker.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun CareerScreen(
    state: CareerUiState,
    actions: CareerActions,
    onRefresh: () -> Unit,
    onDismiss: () -> Unit,
) {
    LaunchedEffect(Unit) { onRefresh() }
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("Career operating system", "Manage your applications, goals, learning, brand, and compensation using your account data.") }
        item {
            if (state.error != null) {
                ErrorNotice(state.error, onDismiss)
                androidx.compose.material3.OutlinedButton(onClick = onRefresh, enabled = !state.busy) {
                    androidx.compose.material3.Text("Retry career data")
                }
            } else if (!state.notice.isNullOrBlank()) {
                NoticeText(state.notice)
            }
        }
        item { CareerModulesScreen(state, actions) }
    }
}
