package com.smarted.tv

import android.content.pm.ActivityInfo
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.smarted.tv.ui.SmartedActions
import com.smarted.tv.ui.SmartedApp
import com.smarted.tv.ui.SmartedData
import com.smarted.tv.data.source.Crumb
import com.smarted.tv.ui.components.MediaItem
import com.smarted.tv.ui.player.PlayerActivity
import com.smarted.tv.ui.screens.SettingsInfo
import com.smarted.tv.data.plugin.PluginTarget
import com.smarted.tv.ui.player.MediaSourceSpec
import com.smarted.tv.viewmodel.AddonsViewModel
import com.smarted.tv.viewmodel.PluginViewModel
import com.smarted.tv.viewmodel.FilesViewModel
import com.smarted.tv.viewmodel.MainTvViewModel

/**
 * Activity principal — SEMPRE em paisagem (horizontal), tela cheia.
 * O layout é o do pacote de design (SmartedScaffold, referência 1672x941).
 */
class MainActivity : ComponentActivity() {

    private val vm: MainTvViewModel by viewModels()
    private val filesVm: FilesViewModel by viewModels()
    private val addonsVm: AddonsViewModel by viewModels()
    private val pluginVm: PluginViewModel by viewModels()

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
            val filesState by filesVm.state.collectAsState()
            val addonState by addonsVm.state.collectAsState()
            val repoState by addonsVm.repoState.collectAsState()
            val pluginState by pluginVm.state.collectAsState()

            // Mídia resolvida por um adaptador de plugin → player (com MIME/headers reais)
            LaunchedEffect(pluginState.media) {
                pluginState.media?.let { media ->
                    startActivity(
                        PlayerActivity.intent(
                            this@MainActivity,
                            MediaSourceSpec(
                                uri = media.uri,
                                mimeHint = media.mimeHint,
                                headers = media.headers,
                                title = media.title,
                                isLive = media.isLive,
                                subtitles = media.subtitles,
                            ),
                        )
                    )
                    pluginVm.consumeMedia()
                }
            }
            SmartedApp(
                data = data,
                actions = SmartedActions(
                    onOpenItem = { _, item ->
                        item.url?.let { url ->
                            startActivity(PlayerActivity.intent(this, url, item.title))
                        }
                    },
                    onSettingAction = { key -> vm.onSettingAction(key) },
                    files = filesState,
                    onFilesSource = { uri -> filesVm.open(Crumb(uri, filesVm.nameOf(uri))) },
                    onFilesEntry = { entry ->
                        if (entry.isArchive) filesVm.previewArchive(entry) else filesVm.openEntry(entry)
                    },
                    onFilesUp = filesVm::up,
                    onFilesGoTo = filesVm::goTo,
                    onFilesRefresh = filesVm::refresh,
                    onFilesSort = filesVm::setSort,
                    onFilesQuery = filesVm::setQuery,
                    onFilesFavorite = filesVm::toggleFavorite,
                    onFilesTreePicked = filesVm::onTreePicked,
                    onFilesPlay = { entry ->
                        startActivity(
                            PlayerActivity.intent(
                                this,
                                entry.uri,
                                entry.name,
                                mimeHint = com.smarted.tv.ui.player.MediaSourceSpec.mimeFromPath(entry.name),
                            )
                        )
                    },
                    onFilesCloseArchive = filesVm::closeArchive,
                    onFilesInfo = filesVm::showInfo,
                    onFilesDismiss = filesVm::clearNotice,
                    addons = addonState,
                    repos = repoState,
                    onAddonInstallZip = addonsVm::inspectAddonZip,
                    onAddonConfirmInstall = addonsVm::confirmInstall,
                    onAddonCancelPending = addonsVm::cancelPending,
                    onAddonUninstall = addonsVm::uninstall,
                    onAddonSelect = addonsVm::select,
                    onAddonCategory = addonsVm::setCategory,
                    onAddonRefresh = addonsVm::refresh,
                    onRepoAdd = addonsVm::addRepoByUrl,
                    onRepoLoad = addonsVm::loadRepo,
                    onRepoOpenNode = addonsVm::openRepoNode,
                    onRepoUp = addonsVm::repoUp,
                    onRepoNodeAt = addonsVm::repoNodeAt,
                    onRepoToggle = addonsVm::toggleRepo,
                    onRepoRemove = addonsVm::removeRepo,
                    onRepoSelectNode = addonsVm::selectRepoNode,
                    onAddonDismiss = addonsVm::clearMessage,
                    plugin = pluginState,
                    onPluginOpen = pluginVm::open,
                    onPluginBack = { pluginVm.back() },
                    onPluginActivate = pluginVm::activate,
                    onPluginClose = pluginVm::clear,
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
