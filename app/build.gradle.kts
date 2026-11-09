plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.smarted.tv"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.smarted.tv"
        // 21 = instala em TV Box / Android TV mais antigos (KitKat/Lollipop em diante)
        minSdk = 21
        targetSdk = 34
        versionCode = (System.getenv("VERSION_CODE") ?: "1").toInt()
        versionName = System.getenv("VERSION_NAME") ?: "1.0"
    }

    // Assinatura: usa o keystore de debug (gerado automaticamente pelo AGP) por padrão
    // e o keystore de release quando KEYSTORE_PATH existir (usado no CI/release).
    signingConfigs {
        create("release") {
            // v1 (JAR) é obrigatória em Android <= 6 e em várias TV Boxes antigas
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = true
            enableV4Signing = false
            val ksPath = System.getenv("KEYSTORE_PATH") ?: "${rootDir}/release-keystore.jks"
            storeFile = file(ksPath)
            storePassword = System.getenv("KEYSTORE_PASSWORD") ?: "smartedtv123"
            keyAlias = System.getenv("KEY_ALIAS") ?: "smartedtv"
            keyPassword = System.getenv("KEY_PASSWORD") ?: "smartedtv123"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = if (file(System.getenv("KEYSTORE_PATH") ?: "${rootDir}/release-keystore.jks").exists()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
        debug {
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    // Gera também um APK universal e variantes por ABI (menores, para TV Boxes antigas)
    splits {
        abi {
            isEnable = true
            reset()
            include("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
            isUniversalApk = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    // Gera também um APK universal (instala em qualquer TV Box) + variantes por ABI

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    lint {
        abortOnError = false
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
        // Some org.json (usado no registro de add-ons/repositórios)
        unitTests.isIncludeAndroidResources = false
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    // Media3 (player de vídeo para Canais/Filmes/Séries)
    implementation("androidx.media3:media3-exoplayer:1.4.1")
    implementation("androidx.media3:media3-exoplayer-hls:1.4.1")
    implementation("androidx.media3:media3-ui:1.4.1")

    // Rede e imagens
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("io.coil-kt:coil-compose:2.7.0")

    // Navegador de arquivos (SAF) — Fases C/D
    implementation("androidx.documentfile:documentfile:1.0.1")

    // Testes de unidade (JVM) — classificador, parsers, addon.xml, zip
    testImplementation("junit:junit:4.13.2")
}
