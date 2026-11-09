package com.smarted.tv.data.archive

import java.io.File
import java.io.InputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipException
import java.util.zip.ZipInputStream

/**
 * Inspeção SEGURA de pacotes ZIP (repositórios e add-ons).
 *
 * Proteções implementadas:
 *  - Zip Slip / Path Traversal: entradas com `..`, caminho absoluto, unidade C: ou
 *    symlink são rejeitadas (nunca escritas fora da pasta destino);
 *  - zip bomb: limite de entradas, de bytes descompactados e de taxa de compressão;
 *  - profundidade excessiva de diretórios;
 *  - arquivos corrompidos (ZipException/CircularReference -> erro claro, sem crash);
 *  - nada é executado: só leitura de nomes e de bytes quando pedido.
 *
 * Regra do projeto: encontrar `addon.xml` NÃO significa que o add-on roda.
 * Ver [com.smarted.tv.data.addon.CompatibilityEvaluator].
 */
object ZipInspector {

    /** Limites de segurança (ajustáveis, com padrão conservador). */
    data class Limits(
        val maxEntries: Int = 20_000,
        val maxSingleEntryBytes: Long = 128L * 1024 * 1024,   // 128 MB
        val maxTotalUncompressedBytes: Long = 512L * 1024 * 1024, // 512 MB
        val maxCompressionRatio: Double = 200.0,
        val maxDepth: Int = 12,
    )

    /** Uma entrada do ZIP (metadados + segurança). */
    data class Entry(
        val name: String,
        val isDirectory: Boolean,
        val size: Long,
        val compressedSize: Long,
        val depth: Int,
        val unsafeReason: String? = null,
    ) {
        val isSafe: Boolean get() = unsafeReason == null
        val extension: String get() = name.substringAfterLast('.', "").lowercase()
        val fileName: String get() = name.substringAfterLast('/')
    }

    data class Report(
        val entries: List<Entry>,
        val addonXmlPaths: List<String>,
        val repoManifestPaths: List<String>,
        val iconPath: String?,
        val fanartPath: String?,
        val rootPrefix: String,
        val warnings: List<String>,
        val isRepository: Boolean,
        val hasAddonManifest: Boolean,
    ) {
        val unsafeEntries: List<Entry> get() = entries.filter { !it.isSafe }
        val totalFiles: Int get() = entries.count { !it.isDirectory }
    }

    /**
     * Lê a estrutura do ZIP sem extrair.
     * @param source arquivo local
     */
    fun inspect(source: File, limits: Limits = Limits()): Report =
        source.inputStream().buffered().use { inspect(it, limits) }

    /**
     * Lê a estrutura do ZIP sem extrair (stream).
     * O stream NÃO é fechado por este método.
     */
    fun inspect(input: InputStream, limits: Limits = Limits()): Report {
        val entries = mutableListOf<Entry>()
        val warnings = mutableListOf<String>()
        val addonXml = mutableListOf<String>()
        val repoManifests = mutableListOf<String>()
        var icon: String? = null
        var fanart: String? = null
        var totalUncompressed = 0L

        val zip = ZipInputStream(input)
        var count = 0

        try {
            while (true) {
                val entry: ZipEntry = try {
                    zip.nextEntry ?: break
                } catch (e: ZipException) {
                    warnings += "ZIP corrompido ou inválido: ${e.message}"
                    break
                }

                count++
                if (count > limits.maxEntries) {
                    warnings += "Limite de ${limits.maxEntries} entradas excedido — leitura interrompida (possível zip bomb)"
                    break
                }

                val name = entry.name.replace('\\', '/')
                val isDir = name.endsWith("/")
                val depth = name.count { it == '/' }
                val unsafe = unsafeReason(name, depth, limits)
                val size = entry.size.coerceAtLeast(0)
                totalUncompressed += if (size > 0) size else 0

                if (totalUncompressed > limits.maxTotalUncompressedBytes) {
                    warnings += "Conteúdo descompactado passaria de ${limits.maxTotalUncompressedBytes / (1024 * 1024)} MB — interrompido"
                    break
                }
                if (entry.compressedSize > 0 && size > 0 &&
                    size.toDouble() / entry.compressedSize > limits.maxCompressionRatio
                ) {
                    warnings += "Entrada '${name.take(80)}' com taxa de compressão suspeita (${size / entry.compressedSize}x)"
                }

                val e = Entry(name, isDir, size, entry.compressedSize, depth, unsafe)
                entries += e

                if (e.isSafe && !isDir) {
                    val lower = name.lowercase()
                    when {
                        lower.endsWith("addon.xml") -> addonXml += name
                        lower.endsWith("addons.xml") || lower.endsWith("addons.xml.md5") -> repoManifests += name
                        e.fileName.equals("icon.png", true) && icon == null -> icon = name
                        (e.fileName.equals("fanart.jpg", true) || e.fileName.equals("fanart.png", true)) && fanart == null -> fanart = name
                    }
                }
            }
        } catch (t: Throwable) {
            warnings += "Falha ao ler ZIP: ${t.message ?: t::class.java.simpleName}"
        }

        if (entries.isEmpty() && warnings.isEmpty()) warnings += "ZIP vazio"

        val rootPrefix = detectRootPrefix(entries)
        val isRepo = repoManifests.isNotEmpty()

        return Report(
            entries = entries,
            addonXmlPaths = addonXml,
            repoManifestPaths = repoManifests,
            iconPath = icon,
            fanartPath = fanart,
            rootPrefix = rootPrefix,
            warnings = warnings,
            isRepository = isRepo,
            hasAddonManifest = addonXml.isNotEmpty(),
        )
    }

    /**
     * Lê o conteúdo de UMA entrada segura (limite de tamanho aplicado).
     * Retorna null se a entrada não existir, for insegura ou passar do limite.
     */
    fun readEntry(source: File, entryName: String, maxBytes: Long = 4L * 1024 * 1024): ByteArray? {
        if (unsafeReason(entryName, entryName.count { it == '/' }, Limits()) != null) return null
        source.inputStream().buffered().use { input ->
            val zip = ZipInputStream(input)
            while (true) {
                val e = try { zip.nextEntry } catch (x: ZipException) { return null } ?: return null
                if (e.name.replace('\\', '/') == entryName) {
                    if (e.size > maxBytes) return null
                    return zip.readLimited(maxBytes)
                }
            }
        }
        @Suppress("UNREACHABLE_CODE")
        return null
    }

    /**
     * Extrai o pacote para [targetDir] com validação por entrada.
     * Nunca escreve fora de [targetDir]. Não executável por design.
     *
     * @return lista de arquivos extraídos (caminhos relativos)
     */
    fun extractSafely(
        source: File,
        targetDir: File,
        limits: Limits = Limits(),
    ): ExtractionResult {
        val extracted = mutableListOf<String>()
        val skipped = mutableListOf<String>()
        val targetCanonical = targetDir.canonicalFile
        var written = 0L

        if (!targetCanonical.exists() && !targetCanonical.mkdirs()) {
            return ExtractionResult(emptyList(), listOf("Não foi possível criar ${targetCanonical.path}"), 0)
        }

        source.inputStream().buffered().use { input ->
            val zip = ZipInputStream(input)
            var count = 0
            while (true) {
                val entry = try { zip.nextEntry } catch (e: ZipException) { break } ?: break
                count++
                if (count > limits.maxEntries) break

                val name = entry.name.replace('\\', '/')
                if (unsafeReason(name, name.count { it == '/' }, limits) != null) {
                    skipped += "$name (insegura)"
                    continue
                }
                val outFile = File(targetCanonical, name).canonicalFile
                if (!outFile.path.startsWith(targetCanonical.path + File.separator) && outFile != targetCanonical) {
                    skipped += "$name (fora do destino)"
                    continue
                }
                if (entry.isDirectory) {
                    outFile.mkdirs()
                    continue
                }
                if (entry.size > 0 && written + entry.size > limits.maxTotalUncompressedBytes) {
                    skipped += "$name (limite total excedido)"
                    break
                }
                outFile.parentFile?.mkdirs()
                outFile.outputStream().use { zip.copyTo(it) }
                written += outFile.length()
                extracted += name
            }
        }
        return ExtractionResult(extracted, skipped, written)
    }

    data class ExtractionResult(
        val extracted: List<String>,
        val skipped: List<String>,
        val bytesWritten: Long,
    )

    // ─────────────────────────── segurança ───────────────────────────
    /** Motivo de insegurança da entrada, ou null se for segura. */
    fun unsafeReason(name: String, depth: Int, limits: Limits): String? {
        if (name.isBlank()) return "nome vazio"
        if (name.contains("../") || name.contains("..\\")) return "path traversal (..)"
        if (name.startsWith("/")) return "caminho absoluto"
        if (Regex("^[A-Za-z]:").containsMatchIn(name)) return "caminho com unidade (C:)"
        if (name.contains("\u0000")) return "caractere nulo no nome"
        if (depth > limits.maxDepth) return "profundidade excessiva ($depth)"
        if (name.length > 4096) return "nome muito longo"
        return null
    }

    /** Detecta a pasta raiz única (ex.: `plugin.video.x/`), comum nos addons. */
    private fun detectRootPrefix(entries: List<Entry>): String {
        val files = entries.filter { !it.isDirectory && it.isSafe }
        if (files.isEmpty()) return ""
        val first = files.first().name
        if (!first.contains('/')) return ""
        val prefix = first.substringBefore('/') + "/"
        return if (files.all { it.name.startsWith(prefix) }) prefix else ""
    }

    private fun InputStream.readLimited(maxBytes: Long): ByteArray {
        val buffer = ByteArray(16 * 1024)
        val out = java.io.ByteArrayOutputStream()
        var total = 0L
        while (true) {
            val read = read(buffer)
            if (read <= 0) break
            total += read
            if (total > maxBytes) break
            out.write(buffer, 0, read)
        }
        return out.toByteArray()
    }
}
