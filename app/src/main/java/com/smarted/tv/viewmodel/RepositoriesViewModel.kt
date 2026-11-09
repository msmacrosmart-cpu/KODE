package com.smarted.tv.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smarted.tv.data.addon.RepoSource
import com.smarted.tv.data.addon.RepositoryClient
import com.smarted.tv.data.addon.RepositoryNode
import com.smarted.tv.data.addon.RepositoryStore
import com.smarted.tv.data.addon.RepositoryTree
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

/**
 * Gerenciador de repositórios (Fase D).
 *
 * Fluxo real:
 *  - adicionar por URL (addons.xml), por ZIP (catálogo dentro do pacote) ou por
 *    pasta autorizada;
 *  - carregar catálogo → montar árvore com categorias reais e compatibilidade;
 *  - habilitar/desabilitar, remover, recarregar e inspecionar cada add-on.
 *
 * Nenhum repositório é inventado: sem catálogo válido, mostramos o erro.
 */
class RepositoriesViewModel(app: Application) : AndroidViewModel(app) {

    private val client = RepositoryClient(app)
    private val store = RepositoryStore(app)

    data class State(
        val repositories: List<RepositoryStore.Entry> = emptyList(),
        val tree: RepositoryNode? = null,
        val openRepoId: String? = null,
        val nodePath: List<RepositoryNode> = emptyList(),
        val loading: Boolean = false,
        val error: String? = null,
        val notice: String? = null,
        val warnings: List<String> = emptyList(),
        val selected: RepositoryNode? = null,
    )

    private val _state = MutableStateFlow(State(repositories = store.all()))
    val state: StateFlow<State> = _state.asStateFlow()

    // ── cadastro ─────────────────────────────────────────────────────
    fun addByUrl(url: String, name: String? = null) {
        val trimmed = url.trim()
        if (trimmed.isEmpty()) {
            _state.value = _state.value.copy(error = "Informe a URL do addons.xml")
            return
        }
        val entry = RepositoryStore.Entry(
            id = "repo-url-" + trimmed.hashCode().toString(16),
            name = name?.takeIf { it.isNotBlank() } ?: trimmed.substringAfter("://").substringBefore('/'),
            kind = RepoSource.SourceKind.URL,
            location = trimmed,
            addedAt = System.currentTimeMillis(),
        )
        store.upsert(entry)
        _state.value = _state.value.copy(repositories = store.all(), error = null)
        load(entry)
    }

    fun addFromZip(file: File, displayName: String? = null) {
        val name = displayName ?: file.nameWithoutExtension
        val entry = RepositoryStore.Entry(
            id = "repo-zip-" + file.name.hashCode().toString(16),
            name = name,
            kind = RepoSource.SourceKind.ZIP,
            location = file.absolutePath,
            addedAt = System.currentTimeMillis(),
        )
        store.upsert(entry)
        _state.value = _state.value.copy(repositories = store.all(), error = null)
        load(entry)
    }

    fun remove(id: String) {
        store.remove(id)
        val remaining = store.all()
        _state.value = _state.value.copy(
            repositories = remaining,
            tree = if (_state.value.openRepoId == id) null else _state.value.tree,
            openRepoId = if (_state.value.openRepoId == id) null else _state.value.openRepoId,
            notice = "Repositório removido",
        )
    }

    fun setEnabled(id: String, enabled: Boolean) {
        store.setEnabled(id, enabled)
        _state.value = _state.value.copy(
            repositories = store.all(),
            notice = if (enabled) "Repositório habilitado" else "Repositório desabilitado",
        )
    }

    // ── leitura de catálogo ──────────────────────────────────────────
    fun load(entry: RepositoryStore.Entry) {
        if (!entry.enabled) {
            _state.value = _state.value.copy(error = "Repositório desabilitado — habilite para carregar")
            return
        }
        _state.value = _state.value.copy(loading = true, error = null, notice = null, warnings = emptyList(),
            selected = null)
        viewModelScope.launch {
            val loaded = when (entry.kind) {
                RepoSource.SourceKind.URL -> client.loadFromUrl(entry.location, entry.name)
                RepoSource.SourceKind.ZIP -> client.loadFromZip(File(entry.location), entry.name)
                RepoSource.SourceKind.FOLDER -> client.loadFromFolder({ null }, entry.name)
                RepoSource.SourceKind.INSTALLED -> client.loadFromFolder({ null }, entry.name)
            }
            if (!loaded.ok) {
                store.markLoaded(entry.id, 0, loaded.error)
                _state.value = _state.value.copy(
                    loading = false,
                    repositories = store.all(),
                    error = loaded.error ?: "Catálogo vazio",
                    warnings = loaded.warnings,
                )
                return@launch
            }
            val tree = RepositoryTree.build(
                repoId = entry.id,
                repoName = entry.name,
                manifests = loaded.manifests,
                filePaths = loaded.files,
                source = loaded.source,
            )
            store.markLoaded(entry.id, loaded.manifests.size)
            _state.value = _state.value.copy(
                loading = false,
                repositories = store.all(),
                tree = tree,
                openRepoId = entry.id,
                nodePath = listOf(tree),
                warnings = loaded.warnings,
                error = null,
                notice = "${loaded.manifests.size} add-ons no catálogo",
            )
        }
    }

    fun loadById(id: String) {
        store.find(id)?.let { load(it) }
    }

    // ── navegação na árvore ──────────────────────────────────────────
    fun openNode(node: RepositoryNode) {
        val tree = _state.value.tree ?: return
        val path = if (node.children.isNotEmpty()) RepositoryTree.pathTo(tree, node.id) else _state.value.nodePath
        if (node.children.isEmpty()) {
            _state.value = _state.value.copy(selected = node)
        } else {
            _state.value = _state.value.copy(nodePath = path.ifEmpty { listOf(node) }, selected = null)
        }
    }

    fun nodeAt(index: Int) {
        val path = _state.value.nodePath
        if (index in path.indices) {
            _state.value = _state.value.copy(nodePath = path.take(index + 1), selected = null)
        }
    }

    fun up() {
        val path = _state.value.nodePath
        if (path.size > 1) {
            _state.value = _state.value.copy(nodePath = path.dropLast(1), selected = null)
        } else {
            closeRepo()
        }
    }

    fun closeRepo() {
        _state.value = _state.value.copy(tree = null, openRepoId = null, nodePath = emptyList(), selected = null)
    }

    fun select(node: RepositoryNode?) {
        _state.value = _state.value.copy(selected = node)
    }

    fun clearMessage() {
        _state.value = _state.value.copy(error = null, notice = null)
    }
}
