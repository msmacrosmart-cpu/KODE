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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Apps
import androidx.compose.material.icons.rounded.Extension
import androidx.compose.material.icons.rounded.Folder
import androidx.compose.material.icons.rounded.Image
import androidx.compose.material.icons.rounded.LibraryMusic
import androidx.compose.material.icons.rounded.Movie
import androidx.compose.material.icons.rounded.Radio
import androidx.compose.material.icons.rounded.SportsEsports
import androidx.compose.material.icons.rounded.Star
import com.smarted.tv.ui.components.MediaItem
import com.smarted.tv.ui.components.SmartedScaffold
import com.smarted.tv.ui.screens.*

/**
 * Telas do app — inclui as do menu estilo Kodi.
 * As 4 primeiras aparecem no menu lateral; o resto no painel (hambúrguer / tecla MENU).
 */
enum class Screen {
    CANAIS, FILMES, SERIES, NAVEGAR,          // menu lateral
    VIDEOS, MUSICA, PROGRAMAS, RADIO, JOGOS, IMAGENS, CLIMA, FAVORITOS, // menu Kodi
    ADDONS, ARQUIVOS, CONFIGURACOES
}

private val sidebarScreens = listOf(Screen.CANAIS, Screen.FILMES, Screen.SERIES, Screen.NAVEGAR)

/** Dados vindos do ViewModel/repositório. Listas vazias mostram o estado vazio. */
data class SmartedData(
    val channels: List<MediaItem> = emptyList(),
    val movies: List<MediaItem> = emptyList(),
    val series: List<MediaItem> = emptyList(),
    val videos: List<MediaItem> = emptyList(),
    val music: List<MediaItem> = emptyList(),
    val programs: List<MediaItem> = emptyList(),
    val radio: List<MediaItem> = emptyList(),
    val games: List<MediaItem> = emptyList(),
    val images: List<MediaItem> = emptyList(),
    val addons: List<MediaItem> = emptyList(),
    val files: List<MediaItem> = emptyList(),
    val favorites: List<MediaItem> = emptyList(),
    val settings: SettingsInfo = SettingsInfo(),
    val climate: ClimateInfo = ClimateInfo(),
)

data class ClimateInfo(
    val city: String = "—",
    val temperature: String = "—",
    val description: String = "Clima não configurado",
)

data class SmartedActions(
    val onOpenItem: (Screen, MediaItem) -> Unit = { _, _ -> },
    val onSettingAction: (String) -> Unit = {},
)

@Composable
fun SmartedApp(data: SmartedData = SmartedData(), actions: SmartedActions = SmartedActions()) {
    var screen by rememberSaveable { mutableStateOf(Screen.CANAIS) }
    var confirmExit by remember { mutableStateOf(false) }
    val activity = LocalContext.current as? Activity

    // Menu lateral: VOLTAR leva para Canais. Nas telas do menu Kodi, também.
    BackHandler(enabled = screen != Screen.CANAIS) { screen = Screen.CANAIS }

    fun handle(action: String) = when (action) {
        "screen:videos" -> screen = Screen.VIDEOS
        "screen:musica" -> screen = Screen.MUSICA
        "screen:programas" -> screen = Screen.PROGRAMAS
        "screen:radio" -> screen = Screen.RADIO
        "screen:jogos" -> screen = Screen.JOGOS
        "screen:imagens" -> screen = Screen.IMAGENS
        "screen:clima" -> screen = Screen.CLIMA
        "screen:favoritos" -> screen = Screen.FAVORITOS
        "screen:addons" -> screen = Screen.ADDONS
        "screen:arquivos" -> screen = Screen.ARQUIVOS
        "screen:configuracoes" -> screen = Screen.CONFIGURACOES
        "screen:canais" -> screen = Screen.CANAIS
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
            // ── menu lateral ──
            Screen.CANAIS -> CanaisScreen(data.channels, open)
            Screen.FILMES -> FilmesScreen(data.movies, open)
            Screen.SERIES -> SeriesScreen(data.series, open)
            Screen.NAVEGAR -> NavegarScreen(::handle)

            // ── opções estilo Kodi ──
            Screen.VIDEOS -> PosterScreen("Vídeos", data.videos, "Nenhum vídeo na biblioteca", open, Icons.Rounded.Movie)
            Screen.MUSICA -> ListScreen("Música", data.music, "Nenhuma música na biblioteca", Icons.Rounded.LibraryMusic, open)
            Screen.PROGRAMAS -> ListScreen("Programas", data.programs, "Nenhum programa instalado", Icons.Rounded.Apps, open)
            Screen.RADIO -> ListScreen("Rádio", data.radio, "Nenhuma estação de rádio", Icons.Rounded.Radio, open)
            Screen.JOGOS -> PosterScreen("Jogos", data.games, "Nenhum jogo instalado", open, Icons.Rounded.SportsEsports)
            Screen.IMAGENS -> PosterScreen("Imagens", data.images, "Nenhuma imagem na biblioteca", open, Icons.Rounded.Image)
            Screen.CLIMA -> ClimaScreen(
                city = data.climate.city,
                temp = data.climate.temperature,
                desc = data.climate.description,
            )
            Screen.FAVORITOS -> ListScreen("Favoritos", data.favorites, "Nenhum favorito salvo", Icons.Rounded.Star, open)

            // ── sistema ──
            Screen.ADDONS -> AddonsScreen(data.addons, open)
            Screen.ARQUIVOS -> ArquivosScreen(data.files, open)
            Screen.CONFIGURACOES -> ConfiguracoesScreen(
                info = data.settings,
                onAction = actions.onSettingAction,
            )
        }
    }

    if (confirmExit) {
        SairDialog(onConfirm = { activity?.finishAffinity() }, onDismiss = { confirmExit = false })
    }
}
