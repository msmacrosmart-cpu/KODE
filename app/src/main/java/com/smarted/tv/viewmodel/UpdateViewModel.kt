package com.smarted.tv.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smarted.tv.data.update.UpdateChecker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Estado da atualização do app (Configurações › Atualizações).
 *
 * Só reporta o que o manifesto publicado diz e o que o aparelho responde —
 * nunca "atualizado" sem ter consultado.
 */
class UpdateViewModel(app: Application) : AndroidViewModel(app) {

    private val checker = UpdateChecker(app)

    data class State(
        val currentVersion: String = "",
        val currentVersionCode: Int = 0,
        val installedCert: String? = null,
        val available: UpdateChecker.Manifest? = null,
        val checking: Boolean = false,
        val downloading: Boolean = false,
        val progress: Int = 0,
        val message: String? = null,
        val error: String? = null,
        val canInstall: Boolean = true,
        val downloadedApk: String? = null,
    )

    private val _state = MutableStateFlow(
        State(
            currentVersion = checker.currentVersionName(),
            currentVersionCode = checker.currentVersionCode(),
            installedCert = checker.installedCertSha256(),
            canInstall = checker.canInstallPackages(),
        )
    )
    val state: StateFlow<State> = _state.asStateFlow()

    fun check() {
        if (_state.value.checking) return
        _state.value = _state.value.copy(checking = true, error = null, message = null)
        viewModelScope.launch {
            when (val result = checker.check()) {
                is UpdateChecker.Check.Available -> _state.value = _state.value.copy(
                    checking = false,
                    available = result.manifest,
                    message = "Nova versão disponível: ${result.manifest.version} " +
                        "(instalada: ${_state.value.currentVersion})",
                )
                is UpdateChecker.Check.UpToDate -> _state.value = _state.value.copy(
                    checking = false,
                    available = null,
                    message = "Você já está na versão mais recente (${result.version}).",
                )
                is UpdateChecker.Check.Failed -> _state.value = _state.value.copy(
                    checking = false,
                    error = result.reason,
                )
            }
        }
    }

    fun downloadAndInstall() {
        val manifest = _state.value.available ?: return
        if (_state.value.downloading) return

        if (!checker.canInstallPackages()) {
            _state.value = _state.value.copy(
                canInstall = false,
                error = "Permita \"Instalar apps desconhecidos\" para o SmartED-TV e tente de novo.",
            )
            checker.requestInstallPermission()
            return
        }

        _state.value = _state.value.copy(downloading = true, progress = 0, error = null, message = null)
        viewModelScope.launch {
            val result = checker.download(manifest) { p ->
                _state.value = _state.value.copy(progress = p)
            }
            val file = result.file
            if (file == null) {
                _state.value = _state.value.copy(
                    downloading = false,
                    error = result.error ?: "Falha ao baixar o APK",
                )
                return@launch
            }
            _state.value = _state.value.copy(
                downloading = false,
                progress = 100,
                downloadedApk = file.absolutePath,
                message = "APK baixado e verificado (SHA-256). Confirmando no instalador…",
            )
            val opened = checker.install(file)
            if (opened.isFailure) {
                _state.value = _state.value.copy(
                    error = "Não foi possível abrir o instalador: " +
                        (opened.exceptionOrNull()?.message ?: "erro desconhecido"),
                )
            }
        }
    }

    fun openInstallPermission() = checker.requestInstallPermission()

    fun refreshLocal() {
        _state.value = _state.value.copy(
            currentVersion = checker.currentVersionName(),
            currentVersionCode = checker.currentVersionCode(),
            canInstall = checker.canInstallPackages(),
        )
    }

    fun clearMessage() {
        _state.value = _state.value.copy(message = null, error = null)
    }
}
