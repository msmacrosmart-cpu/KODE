package com.smarted.tv.data.source

/**
 * Parser de listas e índices de mídia.
 *
 * Cada formato tem seu próprio parser — NADA é interpretado automaticamente como M3U.
 *   #EXTM3U + #EXT-X-STREAM-INF  -> master HLS (variantes, não canais)
 *   #EXTM3U                      -> lista M3U/M3U8 de itens
 *   [playlist]                   -> PLS
 *   <playlist><trackList> (XSPF) -> XSPF
 *   <asx>                        -> ASX
 *   <smil><body><seq>            -> WPL
 *   REM/TITLE/INDEX 01           -> CUE
 *   linha única com URL          -> STRM (Kodi)
 *
 * O parser é tolerante: linhas inválidas viram warning, nunca exceção.
 */
object PlaylistParser {

    private const val MAX_BYTES = 8 * 1024 * 1024   // 8 MB de lista é o limite

    fun parse(content: String, formatHint: PlaylistFormat? = null, baseUrl: String? = null): Playlist {
        val text = content.removePrefix("\uFEFF").trim()
        if (text.length > MAX_BYTES) {
            return Playlist(emptyList(), PlaylistFormat.UNKNOWN, warnings = listOf("Lista muito grande (> 8 MB)"))
        }
        if (text.isEmpty()) {
            return Playlist(emptyList(), formatHint ?: PlaylistFormat.UNKNOWN, warnings = listOf("Conteúdo vazio"))
        }

        val format = formatHint ?: detectFormat(text)
        return when (format) {
            PlaylistFormat.HLS -> parseHls(text)
            PlaylistFormat.M3U -> parseM3u(text)
            PlaylistFormat.PLS -> parsePls(text)
            PlaylistFormat.XSPF -> parseXspf(text)
            PlaylistFormat.ASX -> parseAsx(text)
            PlaylistFormat.WPL -> parseWpl(text)
            PlaylistFormat.CUE -> parseCue(text)
            PlaylistFormat.STRM -> parseStrm(text)
            else -> Playlist(
                emptyList(), PlaylistFormat.UNKNOWN,
                warnings = listOf("Formato de lista não reconhecido"),
            )
        }
    }

    /** Detecta o formato pelo conteúdo (não pela extensão). */
    fun detectFormat(text: String): PlaylistFormat {
        val t = text.trimStart()
        val lower = t.lowercase()
        return when {
            t.startsWith("#EXTM3U") && (lower.contains("#ext-x-stream-inf") || lower.contains("#ext-x-targetduration")) ->
                PlaylistFormat.HLS
            t.startsWith("#EXTM3U") -> PlaylistFormat.M3U
            t.startsWith("[playlist]", ignoreCase = true) -> PlaylistFormat.PLS
            lower.contains("<playlist") && lower.contains("xspf") -> PlaylistFormat.XSPF
            lower.startsWith("<?xml") && lower.contains("<asx") -> PlaylistFormat.ASX
            lower.contains("<smil") -> PlaylistFormat.WPL
            lower.contains("<mpd") -> PlaylistFormat.MPD
            Regex("(?im)^\\s*(REM|FILE|TRACK|INDEX)\\s").containsMatchIn(t) -> PlaylistFormat.CUE
            !t.contains('\n') && t.startsWith("http") -> PlaylistFormat.STRM
            else -> PlaylistFormat.UNKNOWN
        }
    }

    // ─────────────────────────── M3U / M3U8 ────────────────────────────
    private fun parseM3u(text: String): Playlist {
        val entries = mutableListOf<PlaylistEntry>()
        val warnings = mutableListOf<String>()
        var pending: MutableMap<String, String> = mutableMapOf()
        var pendingName: String? = null
        var pendingGroup: String? = null
        var pendingLogo: String? = null
        var pendingTvg: String? = null
        var pendingDuration: Long? = null

        text.lineSequence().forEachIndexed { index, raw ->
            val line = raw.trim()
            if (line.isEmpty()) return@forEachIndexed

            when {
                line.startsWith("#EXTINF:") -> {
                    val attrs = parseAttributes(line)
                    pending = attrs.toMutableMap()
                    pendingGroup = attrs["group-title"]
                    pendingLogo = attrs["tvg-logo"]
                    pendingTvg = attrs["tvg-id"]
                    pendingDuration = line.substringAfter("#EXTINF:", "")
                        .substringBefore(',').trim().toDoubleOrNull()?.toLong()
                    pendingName = line.substringAfter(',', "").trim().ifBlank { null }
                }
                line.startsWith("#") -> {
                    // #EXTGRP:group, #EXTVLCOPT, #PLAYLIST etc. — não são itens
                    if (line.startsWith("#EXTGRP:")) pendingGroup = line.removePrefix("#EXTGRP:").trim()
                }
                else -> {
                    if (!line.contains("://") && !line.startsWith("/")) {
                        warnings += "Linha ${index + 1} ignorada (não é URL): ${line.take(60)}"
                        return@forEachIndexed
                    }
                    entries += PlaylistEntry(
                        title = pendingName ?: line.substringAfterLast('/').ifBlank { "Item ${entries.size + 1}" },
                        url = line,
                        type = inferType(pendingGroup, pendingDuration),
                        group = pendingGroup,
                        logoUrl = pendingLogo,
                        tvgId = pendingTvg,
                        durationSec = pendingDuration,
                        attributes = pending,
                    )
                    pending = mutableMapOf()
                    pendingName = null; pendingGroup = null; pendingLogo = null; pendingTvg = null; pendingDuration = null
                }
            }
        }
        if (entries.isEmpty()) warnings += "Nenhum item válido na lista M3U"
        return Playlist(entries, PlaylistFormat.M3U, warnings = warnings)
    }

    /** Master HLS: variantes + metadados de segmento. Não é lista de canais. */
    private fun parseHls(text: String): Playlist {
        val variants = mutableListOf<StreamVariant>()
        val warnings = mutableListOf<String>()
        var pendingAttrs: Map<String, String> = emptyMap()
        var initSegment: String? = null
        var targetDuration: Int? = null
        var mediaSequence: Long? = null
        var encryption: String? = null
        var isMedia = false

        text.lineSequence().forEach { raw ->
            val line = raw.trim()
            when {
                line.startsWith("#EXT-X-STREAM-INF:") -> {
                    pendingAttrs = parseAttributes(line)
                }
                line.startsWith("#EXT-X-TARGETDURATION:") -> {
                    targetDuration = line.substringAfter(':').trim().toIntOrNull()
                    isMedia = true
                }
                line.startsWith("#EXT-X-MEDIA-SEQUENCE:") -> {
                    mediaSequence = line.substringAfter(':').trim().toLongOrNull()
                }
                line.startsWith("#EXT-X-MAP:") -> {
                    initSegment = parseAttributes(line)["uri"]
                }
                line.startsWith("#EXT-X-KEY:") -> {
                    encryption = parseAttributes(line)["method"]
                    if (encryption != null && encryption != "NONE") {
                        warnings += "Conteúdo HLS criptografado (METHOD=$encryption) — pode exigir chave/DRM"
                    }
                }
                line.startsWith("#EXTINF:") -> isMedia = true
                line.startsWith("#") || line.isEmpty() -> Unit
                else -> {
                    if (pendingAttrs.isNotEmpty()) {
                        variants += StreamVariant(
                            uri = line,
                            bandwidthBps = pendingAttrs["bandwidth"]?.toLongOrNull(),
                            width = pendingAttrs["resolution"]?.substringBefore('x')?.toIntOrNull(),
                            height = pendingAttrs["resolution"]?.substringAfter('x')?.toIntOrNull(),
                            codecs = pendingAttrs["codecs"],
                            audioGroup = pendingAttrs["audio"],
                        )
                        pendingAttrs = emptyMap()
                    } else if (isMedia) {
                        // Segmento de mídia: não é item navegável
                    }
                }
            }
        }

        val entries = variants.map {
            PlaylistEntry(
                title = buildString {
                    append(it.height?.let { h -> "${h}p" } ?: "variante")
                    it.bandwidthBps?.let { b -> append(" • ${b / 1000} kbps") }
                },
                url = resolve(it.uri),
                type = PlaylistEntryType.LIVE,
                attributes = mapOfNotNull(
                    "bandwidth" to it.bandwidthBps?.toString(),
                    "resolution" to (it.width?.let { w -> "${w}x${it.height}" }),
                    "codecs" to it.codecs,
                ),
            )
        }

        return Playlist(
            entries = entries,
            format = PlaylistFormat.HLS,
            isMasterManifest = variants.isNotEmpty() && !isMedia,
            variants = variants,
            warnings = warnings.also {
                if (variants.isEmpty() && isMedia) it += "Manifesto de mídia HLS (segmentos) — reproduzir a URL original, não os segmentos"
            },
        )
    }

    // ──────────────────────────────── PLS ──────────────────────────────
    private fun parsePls(text: String): Playlist {
        val files = sortedMapOf<Int, String>()
        val titles = mutableMapOf<Int, String>()
        text.lineSequence().forEach { raw ->
            val line = raw.trim()
            val eq = line.indexOf('=')
            if (eq <= 0) return@forEach
            val key = line.substring(0, eq).trim().lowercase()
            val value = line.substring(eq + 1).trim()
            when {
                key.startsWith("file") -> key.removePrefix("file").toIntOrNull()?.let { files[it] = value }
                key.startsWith("title") -> key.removePrefix("title").toIntOrNull()?.let { titles[it] = value }
            }
        }
        val entries = files.map { (idx, url) ->
            PlaylistEntry(titles[idx] ?: "Item $idx", url, PlaylistEntryType.UNKNOWN)
        }
        return Playlist(entries, PlaylistFormat.PLS,
            warnings = if (entries.isEmpty()) listOf("Nenhum item em FileN=") else emptyList())
    }

    // ─────────────────────────────── XSPF ──────────────────────────────
    private fun parseXspf(text: String): Playlist {
        val trackRegex = Regex("<track>(.*?)</track>", RegexOption.DOT_MATCHES_ALL)
        val entries = trackRegex.findAll(text).mapNotNull { m ->
            val block = m.groupValues[1]
            val loc = Regex("<location>(.*?)</location>", RegexOption.DOT_MATCHES_ALL)
                .find(block)?.groupValues?.get(1)?.trim() ?: return@mapNotNull null
            val title = Regex("<title>(.*?)</title>", RegexOption.DOT_MATCHES_ALL)
                .find(block)?.groupValues?.get(1)?.trim()
            PlaylistEntry(title ?: loc.substringAfterLast('/'), loc, PlaylistEntryType.UNKNOWN)
        }.toList()
        return Playlist(entries, PlaylistFormat.XSPF,
            warnings = if (entries.isEmpty()) listOf("Nenhum <track> com <location> no XSPF") else emptyList())
    }

    // ─────────────────────────────── ASX ───────────────────────────────
    private fun parseAsx(text: String): Playlist {
        val refRegex = Regex("<ref\\s+href=\"([^\"]+)\"\\s*/?>", RegexOption.IGNORE_CASE)
        val entryRegex = Regex("<entry>(.*?)</entry>", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE))
        val entries = mutableListOf<PlaylistEntry>()
        entryRegex.findAll(text).forEach { m ->
            val block = m.groupValues[1]
            val href = refRegex.find(block)?.groupValues?.get(1) ?: return@forEach
            val title = Regex("<title>(.*?)</title>", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE))
                .find(block)?.groupValues?.get(1)?.trim()
            entries += PlaylistEntry(title ?: href.substringAfterLast('/'), href, PlaylistEntryType.UNKNOWN)
        }
        if (entries.isEmpty()) {
            refRegex.findAll(text).forEach { m ->
                val href = m.groupValues[1]
                entries += PlaylistEntry(href.substringAfterLast('/'), href, PlaylistEntryType.UNKNOWN)
            }
        }
        return Playlist(entries, PlaylistFormat.ASX,
            warnings = if (entries.isEmpty()) listOf("Nenhum <ref href> no ASX") else emptyList())
    }

    // ─────────────────────────────── WPL ───────────────────────────────
    private fun parseWpl(text: String): Playlist {
        val mediaRegex = Regex("<media\\s+src=\"([^\"]+)\"", RegexOption.IGNORE_CASE)
        val entries = mediaRegex.findAll(text).map { m ->
            val url = m.groupValues[1]
            PlaylistEntry(url.substringAfterLast('/'), url, PlaylistEntryType.AUDIO)
        }.toList()
        return Playlist(entries, PlaylistFormat.WPL,
            warnings = if (entries.isEmpty()) listOf("Nenhum <media src> no WPL") else emptyList())
    }

    // ─────────────────────────────── CUE ───────────────────────────────
    private fun parseCue(text: String): Playlist {
        val entries = mutableListOf<PlaylistEntry>()
        var currentTitle: String? = null
        var currentPerformer: String? = null
        var currentFile: String? = null
        var currentAlbum: String? = null
        var albumPerformer: String? = null   // PERFORMER global (antes do 1o TRACK)

        text.lineSequence().forEach { raw ->
            val line = raw.trim()
            when {
                line.startsWith("FILE ", ignoreCase = true) -> {
                    currentFile = line.removePrefix("FILE").trim()
                        .substringBefore(" WAVE").substringBefore(" MP3").trim().trim('"')
                }
                line.startsWith("TRACK ", ignoreCase = true) -> {
                    currentTitle = null; currentPerformer = null
                }
                line.startsWith("TITLE ", ignoreCase = true) -> {
                    val v = line.substringAfter("TITLE").trim().trim('"')
                    if (currentFile != null && currentTitle == null) currentTitle = v else currentAlbum = v
                }
                line.startsWith("PERFORMER ", ignoreCase = true) -> {
                    val value = line.substringAfter("PERFORMER").trim().trim('"')
                    if (currentFile == null && currentTitle == null) {
                        albumPerformer = value      // global: vale para todas as faixas
                    } else {
                        currentPerformer = value
                    }
                }
                line.startsWith("INDEX ", ignoreCase = true) -> {
                    val file = currentFile
                    if (file != null) {
                        entries += PlaylistEntry(
                            title = listOfNotNull(currentPerformer ?: albumPerformer, currentTitle)
                                .joinToString(" - ")
                                .ifBlank { file.substringAfterLast('/') },
                            url = file,
                            type = PlaylistEntryType.AUDIO,
                            group = currentAlbum,
                            attributes = mapOfNotNull("index" to line.substringAfter("INDEX").trim()),
                        )
                    }
                    currentTitle = null
                }
            }
        }
        return Playlist(entries, PlaylistFormat.CUE,
            warnings = if (entries.isEmpty()) listOf("Nenhuma faixa INDEX/FILE no CUE") else emptyList())
    }

    // ─────────────────────────────── STRM ──────────────────────────────
    /** .strm do Kodi: arquivo com uma URL dentro (um item só). */
    private fun parseStrm(text: String): Playlist {
        val url = text.lineSequence().map { it.trim() }.firstOrNull { it.isNotEmpty() && !it.startsWith("#") }
        return if (url == null) {
            Playlist(emptyList(), PlaylistFormat.STRM, warnings = listOf("STRM sem URL"))
        } else {
            Playlist(
                listOf(PlaylistEntry(url.substringAfterLast('/').ifBlank { "Stream" }, url, PlaylistEntryType.UNKNOWN)),
                PlaylistFormat.STRM,
            )
        }
    }

    // ───────────────────────────── utilitários ─────────────────────────
    /** KEY="VALUE" KEY2=VALUE2 → map */
    internal fun parseAttributes(line: String): Map<String, String> {
        val map = mutableMapOf<String, String>()
        Regex("([A-Za-z0-9_-]+)\\s*=\\s*(?:\"([^\"]*)\"|'([^']*)'|([^\\s,]+))").findAll(line).forEach { m ->
            val key = m.groupValues[1].lowercase()
            val value = m.groupValues.drop(2).firstOrNull { it.isNotEmpty() } ?: ""
            map[key] = value
        }
        return map
    }

    private fun inferType(group: String?, duration: Long?): PlaylistEntryType {
        val g = group?.lowercase().orEmpty()
        return when {
            g.contains("filme") || g.contains("movie") || g.contains("vod") -> PlaylistEntryType.VOD
            g.contains("serie") || g.contains("série") || g.contains("series") -> PlaylistEntryType.SERIES
            g.contains("radio") || g.contains("rádio") -> PlaylistEntryType.AUDIO
            duration != null && duration > 0 -> PlaylistEntryType.VOD
            else -> PlaylistEntryType.LIVE
        }
    }

    private fun resolve(uri: String): String = uri

    private fun mapOfNotNull(vararg pairs: Pair<String, String?>): Map<String, String> =
        pairs.mapNotNull { (k, v) -> v?.let { k to it } }.toMap()
}
