package com.smarted.tv.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smarted.tv.data.addon.AddonInstaller
import com.smarted.tv.data.addon.AddonKind
import com.smarted.tv.data.addon.Compatibility
import com.smarted.tv.data.addon.RepositoryStore
import com.smarted.tv.data.addon.RepositoryTree
import com.smarted.tv.data.source.SafFileSystem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

/**
 * Estado das telas de Repositórios e Add-ons (Fases D/E).
 *
 * - Repositórios: cadastro por URL/ZIP/pasta, carregar catálogo, navegar na
 *   árvore real (categorias → add-ons), habilitar/remover.
 * - Add-ons: instalar de ZIP (com confirmação quando não compatível), listar
 *   instalados com compatibilidade real, desinstalar, explorar arquivos.
 */
class AddonsViewModel(app: Application) : AndroidViewModel(app) {

    private val repos = RepositoriesViewModel(app)
    private val installer = AddonInstaller(app)
    private val store = RepositoryStore(app)
    private val fs = SafFileSystem(app)

    val repoState: StateFlow<RepositoriesViewModel.State> = repos.state

    data class State(
        val installed: List<AddonInstaller.Installed> = emptyList(),
        val pending: AddonInstaller.Result? = null,
        val selected: AddonInstaller.Installed? = null,
        val files: List<String> = emptyList(),
        val loading: Boolean = false,
        val error: String? = null,
        val notice: String? = null,
        val categoryFilter: AddonKind? = null,
    ) {
        val filtered: List<AddonInstaller.Installed>
            get() = categoryFilter?.let { k -> installed.filter { it.kind == k } } ?: installed

        /** Só o que pode rodar de fato (compatível ou com adaptação). */
        val runnable: Int
            get() = installed.count {
                it.compatibility == Compatibility.COMPATIBLE ||
                    it.compatibility == Compatibility.COMPATIBLE_WITH_ADAPTATION
            }
    }

    private val _state = MutableStateFlow(State(installed = installer.installed()))
    val state: StateFlow<State> = _state.asStateFlow()

    // ── repositórios (delegação) ────────────────────────────────────
    fun addRepoByUrl(url: String) = repos.addByUrl(url)
    fun loadRepo(id: String) = repos.loadById(id)
    fun openRepoNode(node: com.smarted.tv.data.addon.RepositoryNode) = repos.openNode(node)
    fun repoUp() = repos.up()
    fun repoNodeAt(index: Int) = repos.nodeAt(index)
    fun closeRepo() = repos.closeRepo()
    fun selectRepoNode(node: com.smarted.tv.data.addon.RepositoryNode?) = repos.select(node)
    fun toggleRepo(id: String, enabled: Boolean) = repos.setEnabled(id, enabled)
    fun removeRepo(id: String) = repos.remove(id)
    fun clearRepoMessage() = repos.clearMessage()

    /** Importa um repositório a partir de um ZIP escolhido no SAF. */
    fun addRepoFromZip(uri: String, name: String) {
        viewModelScope.launch {
            val local = fs.localCopyOf(uri, name) ?: run {
                _state.value = _state.value.copy(error = "Não foi possível ler $name")
                return@launch
            }
            repos.addFromZip(local, name.substringBeforeLast('.'))
            local.delete()
        }
    }

    /** Instala um add-on a partir de um ZIP escolhido no SAF (2 etapas). */
    fun inspectAddonZip(uri: String, name: String) {
        _state.value = _state.value.copy(loading = true, error = null, notice = null)
        viewModelScope.launch {
            val local = fs.localCopyOf(uri, name)
            if (local == null) {
                _state.value = _state.value.copy(loading = false, error = "Não foi possível ler $name")
                return@launch
            }
            val result = installer.inspectPackage(local)
            pendingFile = if (result.installed != null) local else null
            if (pendingFile == null) local.delete()
            _state.value = _state.value.copy(loading = false, pending = result, error = result.error)
        }
    }

    /** ZIP inspecionado, aguardando confirmação (cópia temporária real). */
    private var pendingFile: File? = null

    /** Confirma a instalação do pacote inspecionado. */
    fun confirmInstall(allowIncompatible: Boolean = false) {
        val pkg = _state.value.pending ?: return
        val file = pendingFile?.takeIf { it.exists() }
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            val result = if (file != null) {
                installer.install(file, allowIncompatible).also { pendingFile?.delete(); pendingFile = null }
            } else {
                AddonInstaller.Result(error = "O arquivo temporário do pacote expirou. Selecione o ZIP novamente.")
            }
            _state.value = _state.value.copy(
                loading = false,
                installed = installer.installed(),
                pending = if (result.error == null) null else result,
                error = result.error,
                notice = result.installed?.let { "Instalado: ${it.name} ${it.version}" },
            )
        }
    }

    fun cancelPending() {
        pendingFile?.delete()
        pendingFile = null
        _state.value = _state.value.copy(pending = null, error = null)
    }

    fun uninstall(id: String) {
        installer.uninstall(id)
        _state.value = _state.value.copy(
            installed = installer.installed(),
            selected = null,
            files = emptyList(),
            notice = "Add-on removido",
        )
    }

    fun select(addon: AddonInstaller.Installed?) {
        _state.value = _state.value.copy(
            selected = addon,
            files = addon?.let { installer.filesOf(it.id).map { f -> f.absolutePath } } ?: emptyList(),
        )
    }

    fun setCategory(kind: AddonKind?) {
        _state.value = _state.value.copy(categoryFilter = kind)
    }

    fun refresh() {
        _state.value = _state.value.copy(installed = installer.installed())
    }

    fun clearMessage() {
        _state.value = _state.value.copy(error = null, notice = null)
    }

    /** Categorias realmente presentes nos add-ons instalados. */
    fun categories(): List<Pair<AddonKind, String>> =
        _state.value.installed.map { it.kind }.distinct()
            .sortedBy { it.ordinal }
            .map { it to RepositoryTree.categoryLabel(it) }
}
