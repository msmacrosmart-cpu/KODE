package com.smarted.tv.data.addon

import android.content.Context
import com.smarted.tv.data.archive.ZipInspector
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Instalação real de add-ons a partir de um ZIP local.
 *
 * Passos (todos verificáveis, nenhum "simulado"):
 *  1. [ZipInspector.inspect] — recusa pacote corrompido ou com entradas inseguras;
 *  2. localiza `addon.xml` de verdade e lê o manifesto;
 *  3. confere dependências declaradas contra o que já está instalado
 *     (avisa o que falta; nunca executa nada);
 *  4. extrai com [ZipInspector.extractSafely] para `files/addons/<id>/`;
 *  5. registra na lista de instalados (persistida) com versão e compatibilidade.
 *
 * Não executa scripts Python do add-on. A reprodução de conteúdo de um add-on
 * só acontece quando um adaptador [com.smarted.tv.data.plugin] souber montar a
 * listagem — caso contrário a UI mostra "requer adaptação".
 */
/**
 * Regras puras do instalador (testáveis sem Android).
 * O id do add-on vira nome de pasta em `files/addons/`, por isso é validado.
 */
object AddonInstallerRules {
    fun isValidId(id: String): Boolean =
        id.length in 1..128 && Regex("^[a-zA-Z0-9][a-zA-Z0-9._-]*$").matches(id) && !id.contains("..")
}

class AddonInstaller(private val context: Context) {

    private val root: File get() = File(context.filesDir, "addons")
    private val prefs = context.getSharedPreferences("smarted_addons", Context.MODE_PRIVATE)

    /** Add-on instalado no aparelho. */
    data class Installed(
        val id: String,
        val name: String,
        val version: String,
        val kind: AddonKind,
        val compatibility: Compatibility,
        val extensionPoint: String,
        val directory: String,
        val installedAt: Long,
        val dependencies: List<String> = emptyList(),
        val missingDependencies: List<String> = emptyList(),
        val sourcePackage: String = "",
    )

    data class Result(
        val installed: Installed? = null,
        val error: String? = null,
        val warnings: List<String> = emptyList(),
        val needsConfirmation: Boolean = false,
    )

    // ── registro ─────────────────────────────────────────────────────
    fun installed(): List<Installed> {
        val raw = prefs.getString(KEY, null) ?: return emptyList()
        return runCatching {
            val arr = JSONArray(raw)
            (0 until arr.length()).map { fromJson(arr.getJSONObject(it)) }
        }.getOrDefault(emptyList()).sortedBy { it.name.lowercase() }
    }

    fun find(id: String): Installed? = installed().firstOrNull { it.id == id }

    /** ID de add-on válido (o mesmo padrão do Kodi: pontos e minúsculas). */
    fun isValidId(id: String): Boolean = AddonInstallerRules.isValidId(id)

    /**
     * Inspeciona o ZIP antes de instalar (etapa de confirmação na UI).
     * Devolve o manifesto encontrado, sem extrair nada.
     */
    suspend fun inspectPackage(zipFile: File): Result = withContext(Dispatchers.IO) {
        val report = ZipInspector.inspect(zipFile)
        if (report.unsafeEntries.isNotEmpty()) {
            return@withContext Result(
                error = "Pacote recusado: ${report.unsafeEntries.size} entrada(s) insegura(s) " +
                    "(${report.unsafeEntries.first().name} — ${report.unsafeEntries.first().unsafeReason})",
            )
        }
        if (report.warnings.isNotEmpty()) {
            return@withContext Result(error = "Pacote inválido: ${report.warnings.first()}")
        }
        val addonXml = report.addonXmlPaths.firstOrNull()
            ?: return@withContext Result(error = "ZIP não contém addon.xml — não é um add-on do Kodi")
        val bytes = ZipInspector.readEntry(zipFile, addonXml, maxBytes = 2L * 1024 * 1024)
            ?: return@withContext Result(error = "Falha ao ler $addonXml")
        val parsed = AddonManifestParser.parse(bytes.toString(Charsets.UTF_8))
        val manifest = parsed.manifest ?: return@withContext Result(error = parsed.error ?: "addon.xml inválido")
        if (!isValidId(manifest.id)) return@withContext Result(error = "id inválido no addon.xml: ${manifest.id}")

        val kind = CompatibilityEvaluator.kindOf(manifest)
        val compatibility = CompatibilityEvaluator.evaluate(manifest, kind)
        val missing = manifest.libraries.filter { dep ->
            val depId = dep.substringBefore(">=")
            installed().none { it.id == depId }
        }
        val already = find(manifest.id)
        val warnings = mutableListOf<String>()
        if (missing.isNotEmpty()) warnings += "Dependências ausentes: ${missing.joinToString(", ")}"
        if (compatibility.level == Compatibility.NOT_COMPATIBLE) {
            warnings += "Compatibilidade: não compatível — ${compatibility.missing.joinToString(", ")}"
        }
        if (already != null && already.version != manifest.version) {
            warnings += "Já instalado na versão ${already.version} — esta é ${manifest.version}"
        }

        Result(
            installed = Installed(
                id = manifest.id,
                name = manifest.name,
                version = manifest.version,
                kind = kind,
                compatibility = compatibility.level,
                extensionPoint = manifest.extensionPoint,
                directory = File(root, manifest.id).absolutePath,
                installedAt = System.currentTimeMillis(),
                dependencies = manifest.libraries,
                missingDependencies = missing,
                sourcePackage = zipFile.name,
            ),
            warnings = warnings,
            needsConfirmation = true,
        )
    }

    /** Instala de fato (após confirmação do usuário). */
    suspend fun install(zipFile: File, allowIncompatible: Boolean = false): Result = withContext(Dispatchers.IO) {
        val pre = inspectPackage(zipFile)
        val candidate = pre.installed ?: return@withContext Result(error = pre.error ?: "Pacote inválido")
        if (candidate.compatibility == Compatibility.NOT_COMPATIBLE && !allowIncompatible) {
            return@withContext Result(
                error = "Add-on não compatível (${candidate.kind}). Pode ser instalado apenas como arquivo, " +
                    "sem execução — confirme para continuar.",
                installed = candidate,
                needsConfirmation = true,
            )
        }

        val target = File(root, candidate.id)
        if (target.exists()) {
            val backup = File(root, "${candidate.id}.old")
            backup.deleteRecursively()
            if (!target.renameTo(backup)) target.deleteRecursively()
        }
        val extraction = ZipInspector.extractSafely(zipFile, target)
        if (extraction.extracted.isEmpty()) {
            return@withContext Result(error = "Nada foi extraído: ${extraction.skipped.firstOrNull() ?: "pacote vazio"}")
        }
        // Se o ZIP tinha uma pasta raiz única (plugin.video.x/...), promovemos o conteúdo.
        promoteSingleRoot(target, candidate.id)

        val registro = candidate.copy(
            directory = target.absolutePath,
            installedAt = System.currentTimeMillis(),
            sourcePackage = zipFile.name,
        )
        save(listOf(registro) + installed().filterNot { it.id == registro.id })
        Result(installed = registro, warnings = pre.warnings + extraction.skipped)
    }

    fun uninstall(id: String): Boolean {
        val ok = File(root, id).deleteRecursively()
        save(installed().filterNot { it.id == id })
        return ok
    }

    /** Conteúdo instalado (arquivos reais no disco) para a tela de detalhes. */
    fun filesOf(id: String): List<File> {
        val dir = File(root, id)
        if (!dir.exists()) return emptyList()
        return dir.walkTopDown().filter { it.isFile }.take(500).toList()
    }

    private fun promoteSingleRoot(target: File, id: String) {
        val children = target.listFiles() ?: return
        if (children.size != 1) return
        val only = children.first()
        if (!only.isDirectory || only.name != id) return
        only.listFiles()?.forEach { file ->
            val dest = File(target, file.name)
            if (dest.exists()) dest.deleteRecursively()
            file.renameTo(dest)
        }
        only.delete()
    }

    private fun save(list: List<Installed>) {
        val arr = JSONArray()
        list.forEach { arr.put(toJson(it)) }
        prefs.edit().putString(KEY, arr.toString()).apply()
    }

    private fun toJson(i: Installed): JSONObject = JSONObject().apply {
        put("id", i.id)
        put("name", i.name)
        put("version", i.version)
        put("kind", i.kind.name)
        put("compatibility", i.compatibility.name)
        put("extensionPoint", i.extensionPoint)
        put("directory", i.directory)
        put("installedAt", i.installedAt)
        put("sourcePackage", i.sourcePackage)
        put("dependencies", JSONArray(i.dependencies))
        put("missingDependencies", JSONArray(i.missingDependencies))
    }

    private fun fromJson(o: JSONObject): Installed = Installed(
        id = o.getString("id"),
        name = o.optString("name", o.getString("id")),
        version = o.optString("version", "0"),
        kind = runCatching { AddonKind.valueOf(o.optString("kind", "UNKNOWN")) }.getOrDefault(AddonKind.UNKNOWN),
        compatibility = runCatching { Compatibility.valueOf(o.optString("compatibility", "PARTIAL")) }
            .getOrDefault(Compatibility.PARTIAL),
        extensionPoint = o.optString("extensionPoint", ""),
        directory = o.optString("directory", ""),
        installedAt = o.optLong("installedAt", 0),
        sourcePackage = o.optString("sourcePackage", ""),
        dependencies = o.optJSONArray("dependencies").toStringList(),
        missingDependencies = o.optJSONArray("missingDependencies").toStringList(),
    )

    private fun JSONArray?.toStringList(): List<String> {
        if (this == null) return emptyList()
        return (0 until length()).mapNotNull { optString(it).takeIf { s -> s.isNotBlank() } }
    }

    private companion object {
        const val KEY = "installed"
    }
}
