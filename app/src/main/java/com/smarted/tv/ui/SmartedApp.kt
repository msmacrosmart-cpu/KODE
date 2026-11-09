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
import com.smarted.tv.data.addon.AddonInstaller
import com.smarted.tv.data.addon.AddonKind
import com.smarted.tv.data.addon.RepositoryNode
import com.smarted.tv.data.plugin.PluginItem
import com.smarted.tv.data.source.BrowseEntry
import com.smarted.tv.data.source.FilesState
import com.smarted.tv.data.source.SortKey
import com.smarted.tv.ui.components.MediaItem
import com.smarted.tv.ui.components.SmartedScaffold
import com.smarted.tv.ui.screens.*
import com.smarted.tv.viewmodel.AddonsViewModel
import com.smarted.tv.viewmodel.PluginViewModel
import com.smarted.tv.viewmodel.UpdateViewModel
import com.smarted.tv.viewmodel.RepositoriesViewModel

/**
 * Telas do app — inclui as do menu estilo Kodi.
 * As 4 primeiras aparecem no menu lateral; o resto no painel (hambúrguer / tecla MENU).
 */
enum class Screen {
    CANAIS, FILMES, SERIES, NAVEGAR,          // menu lateral
    VIDEOS, MUSICA, PROGRAMAS, RADIO, JOGOS, IMAGENS, CLIMA, FAVORITOS, // menu Kodi
    ADDONS, ARQUIVOS, CONFIGURACOES, PLUGIN, ATUALIZACOES
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
    // ── navegador de arquivos (Fase C) ──
    val files: FilesState = FilesState(),
    val onFilesSource: (String) -> Unit = {},
    val onFilesEntry: (BrowseEntry) -> Unit = {},
    val onFilesUp: () -> Unit = {},
    val onFilesGoTo: (Int) -> Unit = {},
    val onFilesRefresh: () -> Unit = {},
    val onFilesSort: (SortKey) -> Unit = {},
    val onFilesQuery: (String) -> Unit = {},
    val onFilesFavorite: () -> Unit = {},
    val onFilesTreePicked: (String) -> Unit = {},
    val onFilesPlay: (BrowseEntry) -> Unit = {},
    val onFilesCloseArchive: () -> Unit = {},
    val onFilesInfo: (BrowseEntry?) -> Unit = {},
    val onFilesDismiss: () -> Unit = {},
    // ── add-ons e repositórios (Fases D/E) ──
    val addons: AddonsViewModel.State = AddonsViewModel.State(),
    val repos: RepositoriesViewModel.State = RepositoriesViewModel.State(),
    val onAddonInstallZip: (String, String) -> Unit = { _, _ -> },
    val onAddonConfirmInstall: (Boolean) -> Unit = {},
    val onAddonCancelPending: () -> Unit = {},
    val onAddonUninstall: (String) -> Unit = {},
    val onAddonSelect: (AddonInstaller.Installed?) -> Unit = {},
    val onAddonCategory: (AddonKind?) -> Unit = {},
    val onAddonRefresh: () -> Unit = {},
    val onRepoAdd: (String) -> Unit = {},
    val onRepoLoad: (String) -> Unit = {},
    val onRepoOpenNode: (RepositoryNode) -> Unit = {},
    val onRepoUp: () -> Unit = {},
    val onRepoNodeAt: (Int) -> Unit = {},
    val onRepoToggle: (String, Boolean) -> Unit = { _, _ -> },
    val onRepoRemove: (String) -> Unit = {},
    val onRepoSelectNode: (RepositoryNode?) -> Unit = {},
    val onAddonDismiss: () -> Unit = {},
    // ── plugin:// (Fase F) ──
    val plugin: PluginViewModel.State = PluginViewModel.State(),
    val onPluginOpen: (String) -> Unit = {},
    val onPluginBack: () -> Unit = {},
    val onPluginActivate: (PluginItem) -> Unit = {},
    val onPluginClose: () -> Unit = {},
    // ── atualização do app ──
    val update: UpdateViewModel.State = UpdateViewModel.State(),
    val onUpdateCheck: () -> Unit = {},
    val onUpdateDownload: () -> Unit = {},
    val onUpdatePermission: () -> Unit = {},
    val onUpdateDismiss: () -> Unit = {},
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
        "screen:atualizacoes" -> screen = Screen.ATUALIZACOES
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
            Screen.PLUGIN -> PluginScreen(
                state = actions.plugin,
                onBack = actions.onPluginBack,
                onActivate = actions.onPluginActivate,
                onClose = actions.onPluginClose,
            )

            Screen.ADDONS -> AddonsScreen(
                addonState = actions.addons,
                repoState = actions.repos,
                onInstallZip = actions.onAddonInstallZip,
                onConfirmInstall = actions.onAddonConfirmInstall,
                onCancelPending = actions.onAddonCancelPending,
                onUninstall = actions.onAddonUninstall,
                onSelectAddon = actions.onAddonSelect,
                onSetCategory = actions.onAddonCategory,
                onRefreshAddons = actions.onAddonRefresh,
                onAddRepo = actions.onRepoAdd,
                onLoadRepo = actions.onRepoLoad,
                onOpenRepoNode = actions.onRepoOpenNode,
                onRepoUp = actions.onRepoUp,
                onRepoNodeAt = actions.onRepoNodeAt,
                onToggleRepo = actions.onRepoToggle,
                onRemoveRepo = actions.onRepoRemove,
                onSelectRepoNode = actions.onRepoSelectNode,
                onDismissMessage = actions.onAddonDismiss,
                onOpenPlugin = { uri ->
                    actions.onAddonSelect(null)
                    actions.onPluginOpen(uri)
                    screen = Screen.PLUGIN
                },
            )
            Screen.ARQUIVOS -> ArquivosScreen(
                state = actions.files,
                onOpenSource = actions.onFilesSource,
                onOpenEntry = actions.onFilesEntry,
                onUp = actions.onFilesUp,
                onGoTo = actions.onFilesGoTo,
                onRefresh = actions.onFilesRefresh,
                onSort = actions.onFilesSort,
                onQuery = actions.onFilesQuery,
                onToggleFavorite = actions.onFilesFavorite,
                onTreePicked = actions.onFilesTreePicked,
                onPlay = actions.onFilesPlay,
                onCloseArchive = actions.onFilesCloseArchive,
                onShowInfo = actions.onFilesInfo,
                onDismissMessage = actions.onFilesDismiss,
            )
            Screen.CONFIGURACOES -> ConfiguracoesScreen(
                info = data.settings,
                onAction = { key ->
                    if (key == "config:update") screen = Screen.ATUALIZACOES
                    else actions.onSettingAction(key)
                },
            )

            Screen.ATUALIZACOES -> UpdateScreen(
                state = actions.update,
                onCheck = actions.onUpdateCheck,
                onDownload = actions.onUpdateDownload,
                onOpenPermission = actions.onUpdatePermission,
                onDismiss = actions.onUpdateDismiss,
            )
        }
    }

    if (confirmExit) {
        SairDialog(onConfirm = { activity?.finishAffinity() }, onDismiss = { confirmExit = false })
    }
}
