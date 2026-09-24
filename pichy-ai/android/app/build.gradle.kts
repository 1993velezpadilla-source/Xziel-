plugins {
    id("com.android.application")
}

android {
    namespace = "com.pichy.ai"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.pichy.ai"
        minSdk = 28
        targetSdk = 36
        versionCode = 7
        versionName = "0.3.1-lab"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
