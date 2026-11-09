package com.smarted.tv.data.source

/**
 * Tabela central de tipos: extensão → MIME e "como isso deve ser tratado".
 *
 * Regra do projeto: NÃO decidir nada por extensão sozinha.
 * A extensão é só uma dica; o conteúdo (magic bytes) tem prioridade.
 * Ver [FileClassifier].
 */
object MimeMap {

    // ── Vídeo progressivo (player toca direto) ─────────────────────────
    private val video = mapOf(
        "mp4" to "video/mp4",
        "m4v" to "video/x-m4v",
        "mkv" to "video/x-matroska",
        "webm" to "video/webm",
        "avi" to "video/x-msvideo",
        "mov" to "video/quicktime",
        "wmv" to "video/x-ms-wmv",
        "flv" to "video/x-flv",
        "mpeg" to "video/mpeg",
        "mpg" to "video/mpeg",
        "m2v" to "video/mpeg2",
        "m2ts" to "video/mp2t",
        "mts" to "video/mp2t",
        "ts" to "video/mp2t",
        "vob" to "video/dvd",
        "3gp" to "video/3gpp",
        "ogv" to "video/ogg",
        "divx" to "video/divx",
    )

    // ── Áudio ──────────────────────────────────────────────────────────
    private val audio = mapOf(
        "mp3" to "audio/mpeg",
        "aac" to "audio/aac",
        "m4a" to "audio/mp4",
        "flac" to "audio/flac",
        "wav" to "audio/wav",
        "ogg" to "audio/ogg",
        "opus" to "audio/opus",
        "wma" to "audio/x-ms-wma",
        "ac3" to "audio/ac3",
        "eac3" to "audio/eac3",
        "dts" to "audio/vnd.dts",
        "ape" to "audio/x-ape",
        "alac" to "audio/alac",
    )

    // ── Manifestos de streaming (NÃO são listas de canais) ─────────────
    private val manifests = mapOf(
        "m3u8" to "application/vnd.apple.mpegurl",
        "mpd" to "application/dash+xml",
        "ism" to "application/vnd.ms-sstr+xml",
        "isml" to "application/vnd.ms-sstr+xml",
    )

    // ── Listas / índices de mídia ──────────────────────────────────────
    private val playlists = mapOf(
        "m3u" to "audio/x-mpegurl",
        "pls" to "audio/x-scpls",
        "xspf" to "application/xspf+xml",
        "asx" to "video/x-ms-asf",
        "wpl" to "application/vnd.ms-wpl",
        "cue" to "application/x-cue",
        "strm" to "application/x-kodi-strm",
    )

    // ── Pacotes e repositórios ─────────────────────────────────────────
    private val archives = mapOf(
        "zip" to "application/zip",
        "apk" to "application/vnd.android.package-archive",
        "tar" to "application/x-tar",
        "tgz" to "application/gzip",
        "gz" to "application/gzip",
        "7z" to "application/x-7z-compressed",
        "rar" to "application/vnd.rar",
    )

    // ── Metadados, scripts, dados, imagens ─────────────────────────────
    private val other = mapOf(
        "xml" to "application/xml",
        "nfo" to "text/xml",
        "json" to "application/json",
        "py" to "text/x-python",
        "js" to "application/javascript",
        "db" to "application/x-sqlite3",
        "sqlite" to "application/x-sqlite3",
        "srt" to "application/x-subrip",
        "ass" to "text/x-ssa",
        "vtt" to "text/vtt",
        "sub" to "text/plain",
        "jpg" to "image/jpeg",
        "jpeg" to "image/jpeg",
        "png" to "image/png",
        "webp" to "image/webp",
        "gif" to "image/gif",
        "txt" to "text/plain",
        "log" to "text/plain",
    )

    private val byExtension: Map<String, String> = video + audio + manifests + playlists + archives + other

    fun extensionOf(nameOrPath: String): String {
        val clean = nameOrPath.substringBefore('?').substringBefore('#')
        val name = clean.substringAfterLast('/')
        if (!name.contains('.')) return ""
        return name.substringAfterLast('.').lowercase()
    }

    fun mimeOf(nameOrPath: String, sniffed: String? = null): String? =
        sniffed ?: byExtension[extensionOf(nameOrPath)]

    fun isVideoExt(ext: String) = video.containsKey(ext)
    fun isAudioExt(ext: String) = audio.containsKey(ext)
    fun isManifestExt(ext: String) = manifests.containsKey(ext)
    fun isPlaylistExt(ext: String) = playlists.containsKey(ext)
    fun isArchiveExt(ext: String) = archives.containsKey(ext)

    /** URL sem extensão (comum em streams): ex. https://host:8080/live/123 */
    fun looksLikeStreamUrl(value: String): Boolean {
        val v = value.trim()
        if (!(v.startsWith("http://") || v.startsWith("https://") || v.startsWith("rtmp://") ||
                v.startsWith("rtsp://") || v.startsWith("udp://") || v.startsWith("rtp://"))
        ) return false
        return extensionOf(v).let { it.isEmpty() || it.length > 5 }
    }
}
