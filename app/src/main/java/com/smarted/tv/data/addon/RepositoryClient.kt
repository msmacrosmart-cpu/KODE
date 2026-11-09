package com.smarted.tv.data.addon

import android.content.Context
import com.smarted.tv.data.archive.ZipInspector
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Leitura de repositórios do Kodi, das três origens reais:
 *
 *  1. **URL** — o add-on `repository.*` declara `<info>` com a URL do
 *     `addons.xml`; baixamos esse XML e montamos a árvore. Só HTTP/HTTPS,
 *     com limite de tamanho e tempo; o checksum `addons.xml.md5` é opcional.
 *  2. **ZIP** — lido com [ZipInspector] (proteções de zip slip/bomb); o
 *     `addons.xml` é extraído da própria estrutura.
 *  3. **Pasta autorizada (SAF)** — lê `addons.xml` do diretório escolhido.
 *
 * Nunca inventa catálogo: se o XML não existir/for inválido, devolve erro claro.
 * Nenhum byte baixado é executado.
 */
class RepositoryClient(private val context: Context) {

    data class Loaded(
        val id: String,
        val name: String,
        val manifests: List<AddonManifest>,
        val files: List<String>,
        val source: RepoSource,
        val warnings: List<String> = emptyList(),
        val error: String? = null,
    ) {
        val ok: Boolean get() = error == null && manifests.isNotEmpty()
    }

    // ── 1) Repositório por URL ────────────────────────────────────────
    /**
     * @param indexUrl URL do `addons.xml` (vem do `<info>` do add-on de repositório)
     */
    suspend fun loadFromUrl(indexUrl: String, name: String? = null): Loaded = withContext(Dispatchers.IO) {
        val source = RepoSource(RepoSource.SourceKind.URL, indexUrl)
        val id = "repo-url-" + indexUrl.hashCode().toString(16)
        if (!isHttpUrl(indexUrl)) {
            return@withContext Loaded(id, name ?: indexUrl, emptyList(), emptyList(), source,
                error = "Endereço inválido: use http(s)://…/addons.xml")
        }
        val body = fetchText(indexUrl)
            ?: return@withContext Loaded(id, name ?: indexUrl, emptyList(), emptyList(), source,
                error = "Não foi possível baixar $indexUrl")

        val parsed = RepoIndexParser.parse(body)
        val warnings = mutableListOf<String>()
        parsed.error?.let { warnings += it }

        // Checksum opcional: se o repositório publica addons.xml.md5, verificamos.
        val md5Url = indexUrl.substringBeforeLast('/') + "/addons.xml.md5"
        val remoteMd5 = fetchText(md5Url)?.trim()?.substringBefore(' ')?.lowercase()
        if (remoteMd5 != null && remoteMd5.matches(Regex("[0-9a-f]{32}"))) {
            val local = md5(body)
            if (local != remoteMd5) warnings += "Checksum md5 do addons.xml não confere (local $local, remoto $remoteMd5)"
        }

        // Caminhos de pacote reais: o repositório declara <datadir zip="true">,
        // mas o padrão do Kodi é <id>/<id>-<versão>.zip. Marcamos como caminhos
        // REMOTOS (não como arquivos existentes).
        val files = parsed.manifests.map { "${it.id}/${it.id}-${it.version}.zip" }

        Loaded(id, name ?: hostOf(indexUrl), parsed.manifests, files, source, warnings)
    }

    // ── 2) Repositório em ZIP local ───────────────────────────────────
    suspend fun loadFromZip(zipFile: File, displayName: String? = null): Loaded = withContext(Dispatchers.IO) {
        val source = RepoSource(RepoSource.SourceKind.ZIP, zipFile.absolutePath)
        val name = displayName ?: zipFile.nameWithoutExtension
        val id = "repo-zip-" + zipFile.name.hashCode().toString(16)
        val report = ZipInspector.inspect(zipFile)
        val warnings = report.warnings.toMutableList()

        val index = report.repoManifestPaths.firstOrNull { it.lowercase().endsWith("addons.xml") }
        if (index == null) {
            return@withContext Loaded(id, name, emptyList(), report.entries.map { it.name }, source,
                warnings = warnings,
                error = if (report.addonXmlPaths.isNotEmpty()) {
                    "Este ZIP contém add-on (${report.addonXmlPaths.first()}) e não um catálogo de repositório"
                } else {
                    "ZIP sem addons.xml — não é um repositório do Kodi"
                })
        }
        val xml = ZipInspector.readEntry(zipFile, index, maxBytes = 8L * 1024 * 1024)
            ?: return@withContext Loaded(id, name, emptyList(), report.entries.map { it.name }, source,
                warnings = warnings, error = "Falha ao ler $index dentro do ZIP")

        val parsed = RepoIndexParser.parse(xml.toString(Charsets.UTF_8))
        parsed.error?.let { warnings += it }
        Loaded(id, name, parsed.manifests, report.entries.map { it.name }, source, warnings)
    }

    // ── 3) Repositório por pasta autorizada ──────────────────────────
    suspend fun loadFromFolder(readAddonsXml: () -> String?, displayName: String): Loaded =
        withContext(Dispatchers.IO) {
            val source = RepoSource(RepoSource.SourceKind.FOLDER, displayName)
            val id = "repo-dir-" + displayName.hashCode().toString(16)
            val xml = readAddonsXml()
                ?: return@withContext Loaded(id, displayName, emptyList(), emptyList(), source,
                    error = "addons.xml não encontrado na pasta")
            val parsed = RepoIndexParser.parse(xml)
            val warnings = mutableListOf<String>().also { list -> parsed.error?.let { list += it } }
            Loaded(id, displayName, parsed.manifests, emptyList(), source, warnings)
        }

    // ── HTTP mínimo ──────────────────────────────────────────────────
    private fun fetchText(url: String): String? = runCatching {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 10_000
            readTimeout = 20_000
            instanceFollowRedirects = true
            setRequestProperty("User-Agent", "SmartED-TV (Kodi repo reader)")
            setRequestProperty("Accept", "application/xml,text/xml,*/*")
        }
        try {
            if (conn.responseCode !in 200..299) return@runCatching null
            val bytes = conn.inputStream.use { input ->
                val out = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(32 * 1024)
                var total = 0
                while (true) {
                    val read = input.read(buffer)
                    if (read <= 0) break
                    total += read
                    if (total > MAX_INDEX_BYTES) return@runCatching null
                    out.write(buffer, 0, read)
                }
                out.toByteArray()
            }
            bytes.toString(Charsets.UTF_8)
        } finally {
            conn.disconnect()
        }
    }.getOrNull()

    private fun md5(text: String): String =
        java.security.MessageDigest.getInstance("MD5")
            .digest(text.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

    private fun isHttpUrl(url: String): Boolean {
        val low = url.lowercase()
        return (low.startsWith("http://") || low.startsWith("https://")) && low.contains("/")
    }

    private fun hostOf(url: String): String = runCatching { URL(url).host }.getOrDefault(url)

    companion object {
        /** addons.xml de repositórios grandes (ex.: Kodi oficial) fica abaixo disso. */
        const val MAX_INDEX_BYTES = 8 * 1024 * 1024
    }
}
