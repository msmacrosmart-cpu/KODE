package com.smarted.tv.data.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.Locale

/**
 * Atualização do app **por cima da versão instalada** (sem desinstalar).
 *
 * Dois fatos do Android governam isto:
 *  1. o APK novo precisa ter assinatura igual à instalada — por isso o CI assina
 *     sempre com a mesma chave (`tools/keystore` ou secret);
 *  2. `versionCode` maior → o instalador aceita atualizar em vez de recusar.
 *
 * Fluxo: lê o manifesto publicado na última release (`update.json`), compara
 * `versionCode`, baixa o APK universal, confere o **SHA-256** do arquivo e abre o
 * instalador do sistema via FileProvider (o usuário confirma; o app não instala
 * nada silenciosamente).
 */
class UpdateChecker(private val context: Context) {

    /** Manifesto publicado em cada release pelo CI. */
    data class Manifest(
        val version: String,
        val versionCode: Int,
        val apkName: String,
        val apkUrl: String,
        val sha256: String,
        val certSha256: String,
        val notesUrl: String,
    )

    sealed class Check {
        data class Available(val manifest: Manifest, val currentVersionCode: Int) : Check()
        data class UpToDate(val version: String) : Check()
        data class Failed(val reason: String) : Check()
    }

    data class Download(
        val file: File? = null,
        val error: String? = null,
        val progress: Int = 0,
        val sha256Ok: Boolean = false,
    )

    companion object {
        /** Endereço estável: a release mais recente sempre tem o mesmo nome. */
        const val UPDATE_URL =
            "https://github.com/msmacrosmart-cpu/KODE/releases/latest/download/update.json"

        const val APK_FALLBACK_VERSION_URL =
            "https://github.com/msmacrosmart-cpu/KODE/releases/latest/download/"

        private const val MAX_JSON = 64 * 1024
        private const val MAX_APK = 120L * 1024 * 1024
    }

    /** Versão instalada agora (nunca um número fixo no código). */
    fun currentVersionCode(): Int = runCatching {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode.toInt()
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(context.packageName, 0).versionCode
        }
    }.getOrDefault(0)

    fun currentVersionName(): String = runCatching {
        context.packageManager.getPackageInfo(context.packageName, 0).versionName.orEmpty()
    }.getOrDefault("")

    /** SHA-256 do certificado que assinou o app instalado. */
    fun installedCertSha256(): String? = runCatching {
        val info = context.packageManager.getPackageInfo(
            context.packageName,
            android.content.pm.PackageManager.GET_SIGNING_CERTIFICATES,
        )
        val signer = info.signingInfo?.apkContentsSigners?.firstOrNull() ?: return@runCatching null
        MessageDigest.getInstance("SHA-256").digest(signer.toByteArray())
            .joinToString(":") { "%02X".format(it) }
    }.getOrNull()

    /** Consulta o manifesto publicado. Nunca lança: devolve [Check.Failed]. */
    suspend fun check(): Check = withContext(Dispatchers.IO) {
        val body = fetchText(UPDATE_URL)
            ?: return@withContext Check.Failed(
                "Não foi possível ler o manifesto de atualização.\n" +
                    "Verifique a conexão ou se há uma release publicada."
            )
        val manifest = parse(body)
            ?: return@withContext Check.Failed("Manifesto de atualização inválido (JSON inesperado).")

        val current = currentVersionCode()
        if (manifest.versionCode > current) Check.Available(manifest, current)
        else Check.UpToDate(currentVersionName().ifBlank { manifest.version })
    }

    /** Baixa o APK do manifesto e valida o SHA-256 publicado. */
    suspend fun download(manifest: Manifest, onProgress: (Int) -> Unit = {}): Download =
        withContext(Dispatchers.IO) {
            val target = File(context.cacheDir, "update-${manifest.version}.apk")
            if (target.exists()) target.delete()

            val conn = runCatching { (URL(manifest.apkUrl).openConnection() as HttpURLConnection) }.getOrNull()
                ?: return@withContext Download(error = "Endereço do APK inválido")
            try {
                conn.connectTimeout = 15_000
                conn.readTimeout = 30_000
                conn.instanceFollowRedirects = true
                conn.setRequestProperty("Accept", "application/vnd.android.package-archive")
                if (conn.responseCode !in 200..299) {
                    return@withContext Download(error = "Download falhou (HTTP ${conn.responseCode})")
                }
                val total = conn.contentLengthLong.takeIf { it > 0 }
                var written = 0L
                conn.inputStream.use { input ->
                    target.outputStream().use { out ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            val read = input.read(buffer)
                            if (read <= 0) break
                            written += read
                            if (written > MAX_APK) {
                                target.delete()
                                return@withContext Download(error = "APK maior que o limite de segurança")
                            }
                            out.write(buffer, 0, read)
                            if (total != null) onProgress(((written * 100) / total).toInt().coerceIn(0, 100))
                        }
                    }
                }
            } catch (e: Exception) {
                target.delete()
                return@withContext Download(error = "Falha no download: ${e.message ?: e::class.java.simpleName}")
            } finally {
                conn.disconnect()
            }

            if (manifest.sha256.isNotBlank()) {
                val actual = sha256(target)
                if (!actual.equals(manifest.sha256, ignoreCase = true)) {
                    target.delete()
                    return@withContext Download(
                        error = "Arquivo corrompido: SHA-256 não confere.\n" +
                            "esperado ${manifest.sha256.take(16)}…\nobtido ${actual.take(16)}…"
                    )
                }
            }
            Download(file = target, progress = 100, sha256Ok = true)
        }

    /**
     * Abre o instalador do sistema com o APK baixado.
     * O Android mostra "Atualizar" quando a assinatura é a mesma e o versionCode é maior.
     */
    fun install(apk: File): Result<Unit> = runCatching {
        val uri: Uri = FileProvider.getUriForFile(context, "${context.packageName}.updates", apk)
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    /** Pode instalar pacotes? (Android 8+ exige permissão por app.) */
    fun canInstallPackages(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.O || context.packageManager.canRequestPackageInstalls()

    /** Intent para o usuário liberar "instalar apps desconhecidos" deste app. */
    fun requestInstallPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        runCatching {
            context.startActivity(
                Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
                    .setData(Uri.parse("package:${context.packageName}"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }
    }

    private fun parse(body: String): Manifest? = runCatching {
        val json = JSONObject(body)
        val url = json.optString("apkUrl").ifBlank {
            APK_FALLBACK_VERSION_URL + json.optString("apk")
        }
        Manifest(
            version = json.optString("version").ifBlank { "?" },
            versionCode = json.optInt("versionCode", 0),
            apkName = json.optString("apk"),
            apkUrl = url,
            sha256 = json.optString("sha256").lowercase(Locale.ROOT),
            certSha256 = json.optString("certSha256"),
            notesUrl = json.optString("notes"),
        ).takeIf { it.versionCode > 0 && it.apkUrl.startsWith("http") }
    }.getOrNull()

    private fun fetchText(url: String): String? = runCatching {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 10_000
            readTimeout = 15_000
            instanceFollowRedirects = true
            setRequestProperty("User-Agent", "SmartED-TV updater")
        }
        try {
            if (conn.responseCode !in 200..299) return@runCatching null
            val bytes = conn.inputStream.use { it.readNBytes(MAX_JSON) }
            bytes.toString(Charsets.UTF_8)
        } finally {
            conn.disconnect()
        }
    }.getOrNull()

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
