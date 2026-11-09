package com.smarted.tv

import android.content.pm.ActivityInfo
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.smarted.tv.ui.SmartedActions
import com.smarted.tv.ui.SmartedApp
import com.smarted.tv.ui.SmartedData
import com.smarted.tv.ui.components.MediaItem
import com.smarted.tv.ui.player.PlayerActivity
import com.smarted.tv.ui.screens.SettingsInfo
import com.smarted.tv.viewmodel.MainTvViewModel

/**
 * Activity principal — SEMPRE em paisagem (horizontal), tela cheia.
 * O layout é o do pacote de design (SmartedScaffold, referência 1672x941).
 */
class MainActivity : ComponentActivity() {

    private val vm: MainTvViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // ── Horizontal (paisagem) garantido em qualquer aparelho ──
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // Tela cheia imersiva (sem barra de status/navegação)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, window.decorView).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }

        setContent {
            val data by vm.data.collectAsState()
            SmartedApp(
                data = data,
                actions = SmartedActions(
                    onOpenItem = { _, item ->
                        item.url?.let { url ->
                            startActivity(PlayerActivity.intent(this, url, item.title))
                        }
                    },
                    onSettingAction = { key -> vm.onSettingAction(key) },
                ),
            )
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            WindowInsetsControllerCompat(window, window.decorView).apply {
                hide(WindowInsetsCompat.Type.systemBars())
            }
        }
    }
}
