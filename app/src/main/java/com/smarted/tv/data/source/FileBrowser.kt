package com.smarted.tv.data.source

import com.smarted.tv.data.archive.ZipInspector
import java.text.Normalizer
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Ordenação do navegador (Kodi: nome, tipo, data, tamanho). */
enum class SortKey(val label: String) {
    NAME("Nome"),
    TYPE("Tipo"),
    DATE("Data"),
    SIZE("Tamanho"),
}

/**
 * Uma entrada REAL de diretório (arquivo ou pasta).
 * [uri] é a URI do SAF (`content://...`), nunca um caminho inventado.
 */
data class BrowseEntry(
    val uri: String,
    val name: String,
    val isDirectory: Boolean,
    val size: Long = 0L,
    val lastModified: Long = 0L,
    val mime: String? = null,
    val kind: FileKind = FileKind.UNKNOWN,
    val action: FileAction = FileAction.INSPECT,
    val reason: String = "",
) {
    /** Extensão em minúsculas ("" quando não houver). */
    val extension: String get() = name.substringAfterLast('.', "").lowercase(Locale.ROOT)

    val isPlayable: Boolean get() = !isDirectory && action == FileAction.PLAY
    val isArchive: Boolean get() = !isDirectory && kind == FileKind.ARCHIVE
}

/** Um nível do caminho (breadcrumb). */
data class Crumb(val uri: String, val name: String)

/**
 * Estado do navegador. `entries` é sempre o que o sistema de arquivos devolveu:
 * nenhuma pasta é criada ou simulada pelo app.
 */
data class FilesState(
    val crumbs: List<Crumb> = emptyList(),
    val entries: List<BrowseEntry> = emptyList(),
    val sortKey: SortKey = SortKey.NAME,
    val ascending: Boolean = true,
    val query: String = "",
    val loading: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
    val sources: List<Crumb> = emptyList(),
    val favorites: List<Crumb> = emptyList(),
    val history: List<Crumb> = emptyList(),
    val archive: ArchivePreview? = null,
    val info: BrowseEntry? = null,
) {
    val canGoUp: Boolean get() = crumbs.size > 1
    val hasSource: Boolean get() = crumbs.isNotEmpty()
}

/** Prévia real de um ZIP aberto no navegador (não é instalação). */
data class ArchivePreview(
    val name: String,
    val entries: List<ZipInspector.Entry>,
    val warnings: List<String>,
    val isRepository: Boolean,
    val addonXmlPaths: List<String>,
    val rootPrefix: String,
) {
    val totalFiles: Int get() = entries.count { !it.isDirectory }
    val unsafe: Int get() = entries.count { !it.isSafe }
}

/**
 * Regras puras do navegador (testáveis sem Android):
 * ordenar, filtrar, breadcrumbs, tamanhos e datas legíveis.
 *
 * Pastas sempre vêm antes na ordenação — comportamento de gerenciador de arquivos.
 */
object FileBrowser {

    fun sort(
        entries: List<BrowseEntry>,
        key: SortKey = SortKey.NAME,
        ascending: Boolean = true,
    ): List<BrowseEntry> {
        val cmp = when (key) {
            SortKey.NAME -> compareBy<BrowseEntry> { it.name.lowercase(Locale.ROOT) }
            SortKey.TYPE -> compareBy<BrowseEntry> { if (it.isDirectory) "" else it.extension }
                .thenBy { it.name.lowercase(Locale.ROOT) }
            SortKey.DATE -> compareBy<BrowseEntry> { it.lastModified }.thenBy { it.name.lowercase(Locale.ROOT) }
            SortKey.SIZE -> compareBy<BrowseEntry> { if (it.isDirectory) -1L else it.size }
                .thenBy { it.name.lowercase(Locale.ROOT) }
        }
        // Pastas sempre primeiro; a direção (crescente/decrescente) vale para os
        // dois grupos. Ordenar cada grupo e depois concatenar evita que o
        // `reversed()` da lista inteira misture pastas e arquivos.
        fun ordered(group: List<BrowseEntry>): List<BrowseEntry> {
            val sorted = group.sortedWith(cmp)
            return if (ascending) sorted else sorted.reversed()
        }
        return ordered(entries.filter { it.isDirectory }) + ordered(entries.filterNot { it.isDirectory })
    }

    /** Busca dentro da pasta atual, sem diferenciar maiúsculas/acentos. */
    fun filter(entries: List<BrowseEntry>, query: String): List<BrowseEntry> {
        val q = query.trim()
        if (q.isEmpty()) return entries
        val needle = fold(q)
        return entries.filter { fold(it.name).contains(needle) }
    }

    /** Lista final exibida: filtra e depois ordena. */
    fun display(state: FilesState): List<BrowseEntry> =
        sort(filter(state.entries, state.query), state.sortKey, state.ascending)

    /** Caminho legível: `Armazenamento › Filmes › 2024`. */
    fun breadcrumbText(crumbs: List<Crumb>, separator: String = "  ›  "): String =
        crumbs.joinToString(separator) { it.name }

    /** Resumo honesto do que está na pasta. */
    fun summarize(entries: List<BrowseEntry>): String {
        val folders = entries.count { it.isDirectory }
        val files = entries.count { !it.isDirectory }
        val parts = mutableListOf<String>()
        if (folders > 0) parts += if (folders == 1) "1 pasta" else "$folders pastas"
        if (files > 0) parts += if (files == 1) "1 arquivo" else "$files arquivos"
        return if (parts.isEmpty()) "Vazio" else parts.joinToString(" · ")
    }

    /** Tamanho legível (nunca inventa: 0 B é 0 B). */
    fun describeSize(bytes: Long): String {
        if (bytes <= 0L) return "—"
        val units = listOf("B", "KB", "MB", "GB", "TB")
        var value = bytes.toDouble()
        var unit = 0
        while (value >= 1024.0 && unit < units.lastIndex) {
            value /= 1024.0
            unit++
        }
        return if (unit == 0) "${bytes} ${units[unit]}"
        else String.format(Locale.US, "%.1f %s", value, units[unit])
    }

    /** Data legível; 0 (desconhecida) mostra "—". */
    fun describeDate(millis: Long): String {
        if (millis <= 0L) return "—"
        return SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("pt", "BR")).format(Date(millis))
    }

    /** Classifica uma entrada a partir do nome + MIME informado pelo sistema. */
    fun classify(name: String, mime: String?, head: ByteArray? = null): Classification {
        val byContent = FileClassifier.classify(name, head)
        if (byContent.kind != FileKind.UNKNOWN) return byContent
        val fromMime = mime?.let { kindOfMime(it) } ?: return byContent
        return byContent.copy(
            kind = fromMime,
            action = actionOf(fromMime),
            mime = mime,
            confidence = 0.6f,
            reason = "tipo informado pelo sistema: $mime",
        )
    }

    private fun kindOfMime(mime: String): FileKind? {
        val m = mime.lowercase(Locale.ROOT)
        return when {
            m == "application/vnd.apple.mpegurl" || m == "application/x-mpegurl" -> FileKind.HLS
            m == "application/dash+xml" -> FileKind.DASH
            m == "application/zip" || m == "application/x-zip-compressed" -> FileKind.ARCHIVE
            m == "application/vnd.android.package-archive" -> FileKind.ARCHIVE
            m.startsWith("video/") -> FileKind.VIDEO
            m.startsWith("audio/") -> FileKind.AUDIO
            m.startsWith("image/") -> FileKind.IMAGE
            m.startsWith("text/") -> FileKind.TEXT
            m == "application/xml" || m == "text/xml" -> FileKind.CONFIG
            m == "application/json" -> FileKind.CONFIG
            else -> null
        }
    }

    private fun actionOf(kind: FileKind): FileAction = when (kind) {
        FileKind.VIDEO, FileKind.AUDIO, FileKind.HLS, FileKind.DASH -> FileAction.PLAY
        FileKind.ARCHIVE, FileKind.PLAYLIST -> FileAction.BROWSE
        FileKind.UNKNOWN -> FileAction.INSPECT
        else -> FileAction.INSPECT
    }

    /** Remove acentos e caixa para busca tolerante. */
    private fun fold(text: String): String =
        Normalizer.normalize(text, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
}
