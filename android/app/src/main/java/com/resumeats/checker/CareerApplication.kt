package com.resumeats.checker

import android.app.Application
import com.resumeats.checker.data.CareerRepository
import com.resumeats.checker.data.SessionStore

class CareerApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}

class AppContainer(application: Application) {
    val sessionStore = SessionStore(application)
    val repository = CareerRepository.create(sessionStore)
}
