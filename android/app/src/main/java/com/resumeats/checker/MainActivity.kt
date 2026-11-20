package com.resumeats.checker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.viewmodel.compose.viewModel
import com.resumeats.checker.ui.CareerApp
import com.resumeats.checker.ui.CareerViewModel
import com.resumeats.checker.ui.theme.CareerTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as CareerApplication).container
        setContent {
            CareerTheme {
                val viewModel: CareerViewModel = viewModel(
                    factory = CareerViewModel.factory(container.repository, container.sessionStore),
                )
                CareerApp(viewModel = viewModel)
            }
        }
    }
}
