package com.smarted.tv.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smarted.tv.data.archive.ZipInspector
import com.smarted.tv.data.source.ArchivePreview
import com.smarted.tv.data.source.BrowseEntry
import com.smarted.tv.data.source.Crumb
import com.smarted.tv.data.source.FileBrowser
import com.smarted.tv.data.source.FilesState
import com.smarted.tv.data.source.SafFileSystem
import com.smarted.tv.data.source.SortKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Navegador de arquivos real.
 *
 * Regras:
 *  - só mostra o que existe (SAF ou arquivo local); nada de pasta fictícia;
 *  - navegação com pilha de verdade (entrar, voltar, subir, histórico, endereço);
 *  - ao abrir um ZIP, lê a estrutura real com [ZipInspector] (prévia, não instala);
 *  - erros do sistema viram mensagem na tela, nunca crash.
 */
class FilesViewModel(app: Application) : AndroidViewModel(app) {

    private val fs = SafFileSystem(app)

    private val _state = MutableStateFlow(FilesState())
    val state: StateFlow<FilesState> = _state.asStateFlow()

    private val favorites = mutableListOf<Crumb>()
    private val history = mutableListOf<Crumb>()

    init {
        refreshSources()
    }

    // ── fontes ────────────────────────────────────────────────────────
    fun refreshSources() {
        _state.value = _state.value.copy(
            sources = fs.grantedTrees(),
            favorites = favorites.toList(),
        )
    }

    /** Registra uma árvore autorizada pelo usuário (resultado do seletor de pastas). */
    fun onTreePicked(uriString: String) {
        val uri = android.net.Uri.parse(uriString)
        fs.takePermission(uri)
        val name = fs.nameOf(uriString)
        refreshSources()
        open(Crumb(uriString, name))
    }

    // ── navegação ────────────────────────────────────────────────────
    fun open(root: Crumb) {
        load(root, crumbs = listOf(root))
    }

    fun openEntry(entry: BrowseEntry) {
        if (entry.isDirectory) {
            val crumbs = _state.value.crumbs + Crumb(entry.uri, entry.name)
            load(Crumb(entry.uri, entry.name), crumbs)
        } else {
            _state.value = _state.value.copy(info = entry)
        }
    }

    fun up() {
        val crumbs = _state.value.crumbs
        if (crumbs.size <= 1) return
        val target = crumbs.dropLast(1)
        load(target.last(), target)
    }

    fun goTo(index: Int) {
        val crumbs = _state.value.crumbs
        if (index !in crumbs.indices) return
        load(crumbs[index], crumbs.take(index + 1))
    }

    fun refresh() {
        val current = _state.value.crumbs.lastOrNull() ?: return
        load(current, _state.value.crumbs)
    }

    private fun load(dir: Crumb, crumbs: List<Crumb>) {
        _state.value = _state.value.copy(
            crumbs = crumbs,
            loading = true,
            error = null,
            notice = null,
            archive = null,
            info = null,
            query = "",
        )
        viewModelScope.launch {
            runCatching { fs.list(dir.uri) }
                .onSuccess { entries ->
                    if (entries.isNotEmpty()) {
                        history.removeAll { it.uri == dir.uri }
                        history.add(0, dir)
                        if (history.size > 20) history.removeAt(history.lastIndex)
                    }
                    _state.value = _state.value.copy(
                        entries = entries,
                        loading = false,
                        error = null,
                        history = history.toList(),
                        favorites = favorites.toList(),
                    )
                }
                .onFailure { e ->
                    _state.value = _state.value.copy(
                        entries = emptyList(),
                        loading = false,
                        error = describeError(e),
                    )
                }
        }
    }

    private fun describeError(e: Throwable): String = when {
        e is SecurityException -> "Sem permissão para esta pasta. Autorize o acesso pelo seletor de pastas."
        e is IllegalArgumentException -> e.message ?: "Pasta inválida"
        else -> "Falha ao listar: ${e.message ?: e::class.java.simpleName}"
    }

    // ── controles ────────────────────────────────────────────────────
    fun setSort(key: SortKey) {
        val s = _state.value
        _state.value = s.copy(
            sortKey = key,
            ascending = if (s.sortKey == key) !s.ascending else true,
        )
    }

    fun setQuery(query: String) {
        _state.value = _state.value.copy(query = query)
    }

    fun showInfo(entry: BrowseEntry?) {
        _state.value = _state.value.copy(info = entry)
    }

    /** Nome real do documento (o navegador não inventa rótulos). */
    fun nameOf(uri: String): String = fs.nameOf(uri)

    fun clearNotice() {
        _state.value = _state.value.copy(notice = null, error = null)
    }

    fun toggleFavorite() {
        val current = _state.value.crumbs.lastOrNull() ?: return
        if (favorites.any { it.uri == current.uri }) {
            favorites.removeAll { it.uri == current.uri }
            _state.value = _state.value.copy(favorites = favorites.toList(), notice = "Removido dos favoritos")
        } else {
            favorites.add(current)
            _state.value = _state.value.copy(favorites = favorites.toList(), notice = "Pasta adicionada aos favoritos")
        }
    }

    /**
     * Abre um ZIP como PRÉVIA: mostra a estrutura real lida pelo ZipInspector.
     * Não extrai e não instala nada aqui (isso é a Fase E, com confirmação).
     */
    fun previewArchive(entry: BrowseEntry) {
        _state.value = _state.value.copy(loading = true, error = null, notice = null)
        viewModelScope.launch {
            val local = fs.localCopyOf(entry.uri, entry.name)
            if (local == null) {
                _state.value = _state.value.copy(loading = false, error = "Não foi possível ler o arquivo ${entry.name}")
                return@launch
            }
            val report = withContext(Dispatchers.IO) { ZipInspector.inspect(local) }
            local.delete()
            _state.value = _state.value.copy(
                loading = false,
                archive = ArchivePreview(
                    name = entry.name,
                    entries = report.entries,
                    warnings = report.warnings,
                    isRepository = report.isRepository,
                    addonXmlPaths = report.addonXmlPaths,
                    rootPrefix = report.rootPrefix,
                ),
            )
        }
    }

    fun closeArchive() {
        _state.value = _state.value.copy(archive = null)
    }

}
