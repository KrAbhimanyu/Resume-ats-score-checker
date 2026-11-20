package com.resumeats.checker.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Explore
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp

private data class TabDestination(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

@Composable
fun CareerApp(viewModel: CareerViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.initializing -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        state.user == null -> AuthScreen(state, viewModel::authenticate, viewModel::clearMessages)
        else -> MainScaffold(state, viewModel)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MainScaffold(state: CareerUiState, viewModel: CareerViewModel) {
    val navController = rememberNavController()
    val careerActions = CareerActions(
        addApplication = viewModel::addApplication,
        updateApplication = viewModel::updateApplication,
        saveApplicationNotes = viewModel::saveApplicationNotes,
        loadApplicationHistory = viewModel::loadApplicationHistory,
        loadInterviewHistory = viewModel::loadInterviewHistory,
        scheduleInterview = viewModel::scheduleInterview,
        updateInterview = viewModel::updateInterview,
        addReminder = viewModel::addReminder,
        updateReminder = viewModel::updateReminder,
        savePreferences = viewModel::savePreferences,
        addGoal = viewModel::addCareerGoal,
        updateGoal = viewModel::updateCareerGoal,
        sendCoachMessage = viewModel::sendCoachMessage,
        generateCareerRoadmap = viewModel::generateRoadmap,
        updateMilestone = viewModel::updateMilestone,
        setCoachConsent = viewModel::setCoachConsent,
        loadSalary = viewModel::loadSalary,
        refreshSalaryOffers = viewModel::refreshSalaryOffers,
        createSalaryOffer = viewModel::createSalaryOffer,
        updateSalaryOffer = viewModel::editSalaryOffer,
        deleteSalaryOffer = viewModel::deleteSalaryOffer,
        calculateSalary = viewModel::calculateSalary,
        salaryGuidance = viewModel::requestSalaryGuidance,
        refreshBranding = viewModel::refreshBranding,
        saveBrandProfile = viewModel::saveBrandProfile,
        generateBrandContent = viewModel::generateBrandContent,
        saveBrandVersion = viewModel::saveBrandVersion,
        editBrandVersion = viewModel::editBrandVersion,
        loadAcademyTrack = viewModel::loadAcademyTrack,
        completeLesson = viewModel::completeAcademyLesson,
        submitAssessment = viewModel::submitAcademyAssessment,
        submitExercise = viewModel::submitAcademyExercise,
        refreshAcademyDetails = viewModel::refreshAcademyDetails,
        generateAcademyRoadmap = viewModel::generateAcademyRoadmap,
        submitProject = viewModel::submitAcademyProject,
        submitEvidence = viewModel::submitAcademyEvidence,
        issueCertificate = viewModel::issueAcademyCertificate,
        loadAcademyAssistantHistory = viewModel::loadAcademyAssistantHistory,
        askAcademyAssistant = viewModel::askAcademyAssistant,
        createSalaryComparison = viewModel::createSalaryComparison,
        updateSalaryComparison = viewModel::updateSalaryComparison,
        deleteSalaryComparison = viewModel::deleteSalaryComparison,
        matchJob = viewModel::matchJob,
        tailorResume = viewModel::tailorResume,
        updateTailoringReview = viewModel::updateTailoringReview,
        saveTailoredVersion = viewModel::saveTailoredVersion,
    )
    val destinations = listOf(
        TabDestination("dashboard", "Home", Icons.Default.Home),
        TabDestination("resume", "Resume", Icons.Default.Description),
        TabDestination("jobs", "Jobs", Icons.Default.Explore),
        TabDestination("career", "Career", Icons.Default.Work),
        TabDestination("account", "Account", Icons.Default.AccountCircle),
    )
    val backStack by navController.currentBackStackEntryAsState()
    val currentDestination = backStack?.destination

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Resume Career", style = MaterialTheme.typography.titleLarge) },
                actions = {
                    Text(state.user?.email.orEmpty(), modifier = Modifier.padding(end = 14.dp), style = MaterialTheme.typography.labelMedium)
                },
            )
        },
        bottomBar = {
            NavigationBar {
                destinations.forEach { destination ->
                    val selected = currentDestination?.hierarchy?.any { it.route == destination.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            viewModel.clearMessages()
                            navController.navigate(destination.route) {
                                popUpTo(navController.graph.startDestinationId) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { androidx.compose.material3.Icon(destination.icon, contentDescription = destination.label) },
                        label = { Text(destination.label) },
                    )
                }
            }
        },
    ) { padding ->
        Column(Modifier.padding(padding)) {
            if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            NavHost(
                navController = navController,
                startDestination = "dashboard",
                modifier = Modifier.weight(1f),
            ) {
                composable("dashboard") {
                    DashboardScreen(
                        state = state,
                        onRefresh = viewModel::refreshDashboard,
                        onNavigate = { navController.navigate(it) { launchSingleTop = true } },
                        onDismiss = viewModel::clearMessages,
                    )
                }
                composable("resume") {
                    ResumeScreen(
                        state,
                        viewModel::analyze,
                        viewModel::uploadResume,
                        viewModel::refreshResumes,
                        viewModel::clearMessages,
                    )
                }
                composable("jobs") {
                    JobsScreen(
                        state,
                        viewModel::searchJobs,
                        viewModel::saveJob,
                        { job -> viewModel.addApplication(job.title, job.companyName, job.id, job.location) },
                        viewModel::refreshSavedJobs,
                        viewModel::clearMessages,
                        viewModel::matchJob,
                        viewModel::tailorResume,
                        viewModel::updateTailoringReview,
                        viewModel::saveTailoredVersion,
                    )
                }
                composable("career") {
                    CareerScreen(
                        state,
                        careerActions,
                        viewModel::refreshCareer,
                        viewModel::clearMessages,
                    )
                }
                composable("account") {
                    AccountScreen(state, viewModel::refreshAccount, viewModel::logout, viewModel::clearMessages)
                }
            }
        }
    }
}
