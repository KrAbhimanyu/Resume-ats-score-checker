package com.resumeats.checker.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun AuthScreen(state: CareerUiState, onAuthenticate: (String, String, Boolean) -> Unit, onDismiss: () -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var registering by remember { mutableStateOf(false) }
    var showRecoveryNote by remember { mutableStateOf(false) }
    var validation by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text("Resume Career", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text(
                    if (registering) "Create an account to save your career profile." else "Sign in to your career workspace.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                if (state.error != null) ErrorNotice(state.error, onDismiss)
                if (validation != null) Text(validation!!, color = MaterialTheme.colorScheme.error)
                if (showRecoveryNote) {
                    Text(
                        "Password reset is unavailable because the backend does not provide a recovery endpoint. No password will be collected here.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it; validation = null },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Email") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    )
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it; validation = null },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Password") },
                        singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    )
                    if (registering) {
                        Text(
                            "Use at least 12 characters. Passwords are hashed by the backend and never stored on this device.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Button(
                        onClick = {
                            when {
                                email.isBlank() -> validation = "Enter your email address."
                                password.isBlank() -> validation = "Enter your password."
                                registering && password.length < 12 -> validation = "Registration passwords must contain at least 12 characters."
                                else -> onAuthenticate(email, password, registering)
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = !state.busy,
                    ) {
                        if (state.busy) CircularProgressIndicator()
                        else Text(if (registering) "Create account" else "Sign in")
                    }
                    if (!registering) {
                        TextButton(onClick = { showRecoveryNote = true }) { Text("Forgot password?") }
                    }
                }
                OutlinedButton(
                    modifier = Modifier.fillMaxWidth(),
                    onClick = {
                        showRecoveryNote = false
                        validation = null
                        registering = !registering
                    },
                ) {
                    Text(if (registering) "I already have an account" else "Create a new account")
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Career workspace API", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
