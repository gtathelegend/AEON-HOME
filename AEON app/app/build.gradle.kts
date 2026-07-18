import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

// The Sarvam key is read from local.properties (gitignored) or the environment.
// It must never be committed: the hackathon requires a PUBLIC repository, and a
// key in public source is a key that has to be rotated.
val localProps = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}
val sarvamKey: String = localProps.getProperty("sarvam.key")
    ?: System.getenv("SARVAM_KEY")
    ?: ""

// Where the hub lives. Baked in so the app never asks the user for an address.
// Optional: leave it unset and the app finds the hub by UDP discovery instead,
// which is the path that survives the laptop's IP changing between the bench
// and the venue. This is only the fallback for when discovery gets no answer.
val hubHost: String = localProps.getProperty("hub.host")
    ?: System.getenv("AEON_HUB_HOST")
    ?: ""
val hubPort: String = localProps.getProperty("hub.port")
    ?: System.getenv("AEON_HUB_PORT")
    ?: "8800"

android {
    namespace = "com.example.aeon"
    compileSdk {
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.example.aeon"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("String", "SARVAM_KEY", "\"$sarvamKey\"")
        buildConfigField("String", "HUB_HOST", "\"$hubHost\"")
        buildConfigField("int", "HUB_PORT", hubPort)
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.okhttp)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
