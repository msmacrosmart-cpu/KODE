package com.smarted.tv.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smarted.tv.data.addon.AddonInstaller
import com.smarted.tv.data.plugin.PluginItem
import com.smarted.tv.data.plugin.PluginRouter
import com.smarted.tv.data.plugin.PluginTarget
import com.smarted.tv.data.plugin.PluginUri
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Navegação em `plugin://` (Fase F).
 *
 * Mantém a pilha real de navegação (a URI anterior é a de verdade, não um
 * caminho fabricado). Quando não há adaptador, a tela mostra o motivo — não
 * existe listagem simulada.
 */
class PluginViewModel(app: Application) : AndroidViewModel(app) {

    private val installer = AddonInstaller(app)
    private val router = PluginRouter(installed = { installer.installed() })

    data class State(
        val uri: String? = null,
        val title: String = "",
        val items: List<PluginItem> = emptyList(),
        val stack: List<String> = emptyList(),
        val loading: Boolean = false,
        val error: String? = null,
        val details: List<String> = emptyList(),
        val warnings: List<String> = emptyList(),
        val media: PluginTarget.Media? = null,
    ) {
        val canGoBack: Boolean get() = stack.isNotEmpty()
        val hasContent: Boolean get() = items.isNotEmpty()
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    /** Abre uma URI `plugin://` (vinda de favorito, item ou adaptador). */
    fun open(uri: String) {
        val previous = _state.value.uri
        _state.value = _state.value.copy(
            loading = true,
            error = null,
            details = emptyList(),
            warnings = emptyList(),
            uri = uri,
            stack = if (previous != null && previous != uri) _state.value.stack + previous else _state.value.stack,
        )
        viewModelScope.launch {
            when (val result = router.route(uri)) {
                is PluginRouter.Result.Listing -> _state.value = _state.value.copy(
                    loading = false,
                    title = result.listing.title.ifBlank { PluginUri.parse(uri)?.addonId ?: uri },
                    items = result.listing.items,
                    warnings = result.listing.warnings,
                )
                is PluginRouter.Result.Unsupported -> _state.value = _state.value.copy(
                    loading = false,
                    items = emptyList(),
                    error = result.reason,
                    details = result.detail,
                )
                is PluginRouter.Result.Invalid -> _state.value = _state.value.copy(
                    loading = false,
                    items = emptyList(),
                    error = "\"$uri\" não é uma URI plugin:// válida",
                    details = listOf("Formato esperado: plugin://<id-do-addon>/<caminho>?<parâmetros>"),
                )
                is PluginRouter.Result.Media -> _state.value = _state.value.copy(
                    loading = false,
                    media = result.media,
                )
            }
        }
    }

    /** Clique em item: pasta → navega; mídia → player; resto → motivo. */
    fun activate(item: PluginItem) {
        when (val target = item.target) {
            is PluginTarget.Virtual -> open(target.uri.rebuild())
            is PluginTarget.Media -> _state.value = _state.value.copy(media = target)
            is PluginTarget.Unsupported -> _state.value = _state.value.copy(
                error = "Item não reproduzível",
                details = listOfNotNull(target.reason, target.rawTarget?.let { "Destino: $it" }),
            )
            null -> _state.value = _state.value.copy(
                error = "Item sem destino",
                details = listOf("Este adaptador não informou para onde o item leva."),
            )
        }
    }

    fun back(): Boolean {
        val stack = _state.value.stack
        if (stack.isEmpty()) return false
        val previous = stack.last()
        _state.value = _state.value.copy(stack = stack.dropLast(1))
        open(previous)
        return true
    }

    fun consumeMedia() {
        _state.value = _state.value.copy(media = null)
    }

    fun clear() {
        _state.value = State()
    }
}
