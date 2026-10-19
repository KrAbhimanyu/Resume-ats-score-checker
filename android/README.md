# Android Client Foundation (Kotlin + Jetpack Compose)

This directory serves as the native Android application foundation for the **Resume ATS Score Checker**.

## Architectural Role

The Android application delivers an independent, mobile-first experience using native Android document storage access and modern Jetpack Compose declarative UI. It directly invokes the backend analysis API, completely decoupled from the web frontend.

## Technology Stack (Milestone 3 Target)

- **Language**: Kotlin 2.0+
- **UI Toolkit**: Jetpack Compose with Material 3 Design
- **Architecture**: MVVM / MVI (Clean Architecture with Repository pattern)
- **Networking**: Retrofit 2 + OkHttp 4 (Multipart support)
- **Serialization**: Kotlinx Serialization
- **Document Access**: Storage Access Framework (`ActivityResultContracts.OpenDocument()`)
- **Min SDK**: 26 (Android 8.0) | **Target SDK**: 35

## Architecture Blueprint

```text
app/src/main/java/com/resumeats/checker/
├── data/
│   ├── remote/
│   │   ├── AtsApiService.kt (POST /api/v1/analyze, GET /api/v1/health)
│   │   └── NetworkModels.kt (DTOs mirroring backend schemas)
│   └── repository/
│       └── AtsRepositoryImpl.kt
├── domain/
│   ├── model/ (Domain entities)
│   └── repository/ (Repository interfaces)
├── ui/
│   ├── components/
│   │   ├── ScoreGauge.kt
│   │   ├── CategoryScoreItem.kt
│   │   ├── RequirementItem.kt
│   │   └── RecommendationCard.kt
│   ├── screens/
│   │   ├── home/
│   │   │   ├── HomeScreen.kt (Document picker & JD input)
│   │   │   └── HomeViewModel.kt
│   │   └── result/
│   │       ├── ResultScreen.kt (Structured analysis report)
│   │       └── ResultViewModel.kt
│   └── theme/
│       ├── Color.kt
│       └── Theme.kt
└── MainActivity.kt
```

## Storage & Document Picker Strategy

- Uses standard Android Storage Access Framework:
  ```kotlin
  val launcher = rememberLauncherForActivityResult(
      contract = ActivityResultContracts.OpenDocument()
  ) { uri: Uri? ->
      // Read input stream safely, validate MIME types (pdf, docx)
  }
  launcher.launch(arrayOf("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
  ```
- Reads the file via `ContentResolver.openInputStream(uri)`, verifies size (<5 MB), and uploads via multipart without saving to unmanaged storage.

## Planned Milestone 3 Execution

Milestone 3 will scaffold the Gradle project, assemble Compose screens, and wire OkHttp network calls to the backend API.
