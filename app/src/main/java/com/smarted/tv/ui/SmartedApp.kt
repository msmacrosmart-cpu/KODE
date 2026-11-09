package com.smarted.tv.ui

import android.app.Activity
import androidx.activity.compose.BackHandler
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.LocalContext
import com.smarted.tv.ui.components.MediaItem
import com.smarted.tv.ui.components.SmartedScaffold
import com.smarted.tv.ui.screens.*

enum class Screen { CANAIS, FILMES, SERIES, NAVEGAR, ADDONS, ARQUIVOS, CONFIGURACOES }

private val sidebarScreens = listOf(Screen.CANAIS, Screen.FILMES, Screen.SERIES, Screen.NAVEGAR)

/** Dados vindos do seu ViewModel/repositório. Listas vazias mostram o estado vazio. */
data class SmartedData(
    val channels: List<MediaItem> = emptyList(),
    val movies: List<MediaItem> = emptyList(),
    val series: List<MediaItem> = emptyList(),
    val addons: List<MediaItem> = emptyList(),
    val files: List<MediaItem> = emptyList(),
    val settings: SettingsInfo = SettingsInfo(),
)

data class SmartedActions(
    val onOpenItem: (Screen, MediaItem) -> Unit = { _, _ -> },
    val onUpdateEpg: () -> Unit = {},
)

@Composable
fun SmartedApp(data: SmartedData = SmartedData(), actions: SmartedActions = SmartedActions()) {
    var screen by rememberSaveable { mutableStateOf(Screen.CANAIS) }
    var confirmExit by remember { mutableStateOf(false) }
    val activity = LocalContext.current as? Activity

    BackHandler(enabled = screen != Screen.CANAIS) { screen = Screen.CANAIS }

    fun handle(action: String) = when (action) {
        "screen:addons" -> screen = Screen.ADDONS
        "screen:arquivos" -> screen = Screen.ARQUIVOS
        "screen:configuracoes" -> screen = Screen.CONFIGURACOES
        "exit" -> confirmExit = true
        else -> Unit
    }

    SmartedScaffold(
        selected = sidebarScreens.indexOf(screen).takeIf { it >= 0 },
        onSelect = { screen = sidebarScreens[it] },
        onKodiOption = ::handle,
    ) {
        val open = { m: MediaItem -> actions.onOpenItem(screen, m) }
        when (screen) {
            Screen.CANAIS -> CanaisScreen(data.channels, open)
            Screen.FILMES -> FilmesScreen(data.movies, open)
            Screen.SERIES -> SeriesScreen(data.series, open)
            Screen.NAVEGAR -> NavegarScreen(::handle)
            Screen.ADDONS -> AddonsScreen(data.addons, open)
            Screen.ARQUIVOS -> ArquivosScreen(data.files, open)
            Screen.CONFIGURACOES -> ConfiguracoesScreen(data.settings, actions.onUpdateEpg)
        }
    }

    if (confirmExit) SairDialog(onConfirm = { activity?.finishAffinity() }, onDismiss = { confirmExit = false })
}
