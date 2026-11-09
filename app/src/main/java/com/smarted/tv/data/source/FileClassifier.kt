package com.smarted.tv.data.source

/**
 * Categoria funcional de um arquivo/fonte. Define o que o app PODE fazer com ele.
 * (não confundir com MIME: é a intenção de uso)
 */
enum class FileKind {
    VIDEO,          // vídeo progressivo → player
    AUDIO,          // áudio → player
    HLS,            // manifesto HLS (.m3u8) → player com MIME explícito
    DASH,           // manifesto DASH (.mpd) → player com MIME explícito
    SMOOTH,         // Smooth Streaming (.ism/.isml)
    SEGMENT,        // .ts/.m4s/.m4v fragmento de stream — NÃO é vídeo independente
    PLAYLIST,       // lista de mídia (m3u/pls/xspf/asx/wpl/cue/strm)
    ARCHIVE,        // zip/tar/gz → inspeção/extração
    ADDON_MANIFEST, // addon.xml / addon.py
    REPO_MANIFEST,  // addons.xml / addons.xml.md5 (raiz de repositório)
    CONFIG,         // xml/json/yaml de configuração (nunca reproduzir)
    SCRIPT,         // py/js — não executar
    DATABASE,       // db/sqlite
    IMAGE,          // ícones/artes
    SUBTITLE,       // srt/ass/vtt
    TEXT,
    UNKNOWN,
}

/** Ação recomendada para a categoria. */
enum class FileAction {
    PLAY,       // pode abrir no player
    BROWSE,     // abrir/entrar (pasta, arquivo, pacote)
    INSPECT,    // mostrar informações
    READ_ONLY,  // config/script/db: só ler metadados
    NONE,       // não tratar (ex.: segmento de stream)
}

/**
 * Resultado da classificação.
 *
 * @param mime         MIME inferido (extensão e/ou sniffing)
 * @param sniffed      true quando o tipo veio dos magic bytes (mais confiável)
 * @param confidence   0..1 — quão seguro é o resultado
 * @param reason       explicação curta (vai para o log/UI de diagnóstico)
 */
data class Classification(
    val kind: FileKind,
    val action: FileAction,
    val mime: String?,
    val sniffed: Boolean = false,
    val confidence: Float = 0.5f,
    val reason: String = "",
) {
    val isPlayable: Boolean get() = action == FileAction.PLAY
}

/**
 * Classificador centralizado. Única porta de entrada para decidir tipo/ação.
 *
 * Ordem de decisão:
 *  1. se veio conteúdo (cabeçalho) → magic bytes têm prioridade;
 *  2. senão, extensão;
 *  3. senão, heurística de URL;
 *  4. senão, UNKNOWN (nunca adivinhar "é m3u").
 */
object FileClassifier {

    /** Mínimo de bytes para sniffing confiável. */
    const val SNIFF_SIZE = 512

    fun classify(name: String?, head: ByteArray? = null): Classification {
        val source = name.orEmpty()
        val ext = MimeMap.extensionOf(source)

        // ── 1) Conteúdo tem prioridade ───────────────────────────────
        if (head != null && head.isNotEmpty()) {
            sniff(head)?.let { return it }
        }

        // ── 2) Extensão ──────────────────────────────────────────────
        extensionClass(ext)?.let { return it }

        // ── 3) URL de stream sem extensão ────────────────────────────
        if (MimeMap.looksLikeStreamUrl(source)) {
            return Classification(
                kind = FileKind.HLS, action = FileAction.PLAY, mime = null,
                sniffed = false, confidence = 0.4f,
                reason = "URL de streaming sem extensão — tratada como stream (HLS pode ser necessário)",
            )
        }

        return Classification(
            FileKind.UNKNOWN, FileAction.INSPECT, MimeMap.mimeOf(source),
            reason = "Extensão desconhecida ou ausente",
        )
    }

    /** Classificação por magic bytes (assinatura binária). */
    fun sniff(head: ByteArray): Classification? {
        fun starts(vararg bytes: Int, offset: Int = 0): Boolean {
            if (head.size < offset + bytes.size) return false
            return bytes.indices.all { (head[offset + it].toInt() and 0xFF) == bytes[it] }
        }
        fun ascii(s: String, offset: Int = 0): Boolean {
            if (head.size < offset + s.length) return false
            return s.indices.all { head[offset + it].toInt().toChar() == s[it] }
        }

        // ZIP (PK\x03\x04) — repositórios, add-ons, .kodi zips
        if (starts(0x50, 0x4B, 0x03, 0x04) || starts(0x50, 0x4B, 0x05, 0x06)) {
            return Classification(FileKind.ARCHIVE, FileAction.BROWSE, "application/zip", true, 1f, "magic: PK (ZIP)")
        }
        // GZIP
        if (starts(0x1F, 0x8B)) {
            return Classification(FileKind.ARCHIVE, FileAction.BROWSE, "application/gzip", true, 1f, "magic: 1F 8B (GZIP)")
        }
        // 7z
        if (starts(0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C)) {
            return Classification(FileKind.ARCHIVE, FileAction.BROWSE, "application/x-7z-compressed", true, 1f, "magic: 7z")
        }
        // RAR
        if (ascii("Rar!")) {
            return Classification(FileKind.ARCHIVE, FileAction.BROWSE, "application/vnd.rar", true, 1f, "magic: Rar!")
        }
        // SQLite
        if (ascii("SQLite format 3")) {
            return Classification(FileKind.DATABASE, FileAction.READ_ONLY, "application/x-sqlite3", true, 1f, "magic: SQLite")
        }
        // PNG / JPEG / WEBP / GIF
        if (starts(0x89, 0x50, 0x4E, 0x47)) {
            return Classification(FileKind.IMAGE, FileAction.INSPECT, "image/png", true, 1f, "magic: PNG")
        }
        if (starts(0xFF, 0xD8, 0xFF)) {
            return Classification(FileKind.IMAGE, FileAction.INSPECT, "image/jpeg", true, 1f, "magic: JPEG")
        }
        if (ascii("RIFF") && ascii("WEBP", 8)) {
            return Classification(FileKind.IMAGE, FileAction.INSPECT, "image/webp", true, 1f, "magic: WEBP")
        }
        if (ascii("GIF8")) {
            return Classification(FileKind.IMAGE, FileAction.INSPECT, "image/gif", true, 1f, "magic: GIF")
        }
        // MKV / WEBM (EBML)
        if (starts(0x1A, 0x45, 0xDF, 0xA3)) {
            return Classification(FileKind.VIDEO, FileAction.PLAY, "video/x-matroska", true, 0.95f, "magic: EBML (MKV/WebM)")
        }
        // FLV
        if (ascii("FLV")) {
            return Classification(FileKind.VIDEO, FileAction.PLAY, "video/x-flv", true, 1f, "magic: FLV")
        }
        // OGG (áudio ou vídeo)
        if (ascii("OggS")) {
            return Classification(FileKind.AUDIO, FileAction.PLAY, "audio/ogg", true, 0.9f, "magic: OggS")
        }
        // FLAC
        if (ascii("fLaC")) {
            return Classification(FileKind.AUDIO, FileAction.PLAY, "audio/flac", true, 1f, "magic: fLaC")
        }
        // ID3 (MP3 com tag)
        if (ascii("ID3")) {
            return Classification(FileKind.AUDIO, FileAction.PLAY, "audio/mpeg", true, 0.95f, "magic: ID3 (MP3)")
        }
        // MPEG-TS (188 bytes sync 0x47)
        if (head.size > 376 && (head[0].toInt() and 0xFF) == 0x47 && (head[188].toInt() and 0xFF) == 0x47) {
            return Classification(FileKind.SEGMENT, FileAction.PLAY, "video/mp2t", true, 0.9f,
                "magic: MPEG-TS (188 bytes) — pode ser segmento de stream")
        }
        // MP4 / fMP4 (ftyp) — inclusive segmentos .m4s
        if (ascii("ftyp", 4)) {
            val brand = String(head.copyOfRange(minOf(8, head.size), minOf(12, head.size)))
            val isSegment = brand.startsWith("msdh") || brand.startsWith("msix") || brand.startsWith("iso6")
            return Classification(
                if (isSegment) FileKind.SEGMENT else FileKind.VIDEO,
                if (isSegment) FileAction.INSPECT else FileAction.PLAY,
                "video/mp4", true, 0.95f,
                "magic: ISO-BMFF (ftyp=$brand)",
            )
        }
        // RIFF AVI
        if (ascii("RIFF") && ascii("AVI", 8)) {
            return Classification(FileKind.VIDEO, FileAction.PLAY, "video/x-msvideo", true, 1f, "magic: RIFF AVI")
        }
        // WAV
        if (ascii("RIFF") && ascii("WAVE", 8)) {
            return Classification(FileKind.AUDIO, FileAction.PLAY, "audio/wav", true, 1f, "magic: RIFF WAVE")
        }

        // ── Texto: manifestos e playlists (não confiar na extensão) ──
        val text = head.toString(Charsets.UTF_8).trimStart('\uFEFF', '\n', '\r', ' ')
        if (text.startsWith("#EXTM3U")) {
            // #EXT-X-STREAM-INF = HLS; sem isso, é lista M3U de canais
            return if (text.contains("#EXT-X-STREAM-INF") || text.contains("#EXT-X-TARGETDURATION")) {
                Classification(FileKind.HLS, FileAction.PLAY, "application/vnd.apple.mpegurl", true, 1f,
                    "conteúdo: #EXTM3U + #EXT-X-* (manifesto HLS)")
            } else {
                Classification(FileKind.PLAYLIST, FileAction.BROWSE, "audio/x-mpegurl", true, 1f,
                    "conteúdo: #EXTM3U (lista de canais/itens)")
            }
        }
        if (text.startsWith("<?xml") || text.startsWith("<")) {
            val lower = text.lowercase()
            return when {
                lower.contains("<mpd") ->
                    Classification(FileKind.DASH, FileAction.PLAY, "application/dash+xml", true, 1f, "conteúdo: <MPD> (DASH)")
                lower.contains("<smoothstreamingmedia") ->
                    Classification(FileKind.SMOOTH, FileAction.PLAY, "application/vnd.ms-sstr+xml", true, 1f, "conteúdo: SmoothStreamingMedia")
                lower.contains("<addons") || lower.contains("<addon ") ->
                    Classification(FileKind.REPO_MANIFEST, FileAction.BROWSE, "application/xml", true, 1f, "conteúdo: addons.xml")
                lower.contains("<playlist") && lower.contains("xspf") ->
                    Classification(FileKind.PLAYLIST, FileAction.BROWSE, "application/xspf+xml", true, 1f, "conteúdo: XSPF")
                lower.contains("<asx") ->
                    Classification(FileKind.PLAYLIST, FileAction.BROWSE, "video/x-ms-asf", true, 1f, "conteúdo: ASX")
                else ->
                    Classification(FileKind.CONFIG, FileAction.READ_ONLY, "application/xml", true, 0.8f, "conteúdo: XML genérico")
            }
        }
        if (text.startsWith("[playlist]")) {
            return Classification(FileKind.PLAYLIST, FileAction.BROWSE, "audio/x-scpls", true, 1f, "conteúdo: PLS")
        }
        return null
    }

    /** Classificação por extensão (usada para conteúdo ausente ou não reconhecido). */
    fun extensionClass(ext: String): Classification? = when {
        ext.isEmpty() -> null

        ext == "m3u8" -> Classification(FileKind.HLS, FileAction.PLAY, MimeMap.mimeOf("x.m3u8"), confidence = 0.8f,
            reason = "extensão .m3u8 (HLS) — confirmar com o conteúdo quando possível")
        ext == "mpd" -> Classification(FileKind.DASH, FileAction.PLAY, MimeMap.mimeOf("x.mpd"), confidence = 0.9f, reason = "extensão .mpd (DASH)")
        ext == "ism" || ext == "isml" -> Classification(FileKind.SMOOTH, FileAction.PLAY, MimeMap.mimeOf("x.ism"), confidence = 0.9f, reason = "extensão Smooth Streaming")

        // segmentos: .ts pode ser vídeo independente OU segmento; .m4s sempre segmento
        ext == "m4s" -> Classification(FileKind.SEGMENT, FileAction.NONE, "video/iso.segment", confidence = 0.9f,
            reason = ".m4s é segmento fragmentado — não tratar como vídeo isolado")
        ext == "ts" -> Classification(FileKind.SEGMENT, FileAction.PLAY, "video/mp2t", confidence = 0.5f,
            reason = ".ts: pode ser segmento de stream; tentar sniffing antes de reproduzir")

        ext == "m3u" || ext == "pls" || ext == "xspf" || ext == "asx" || ext == "wpl" || ext == "cue" || ext == "strm" ->
            Classification(FileKind.PLAYLIST, FileAction.BROWSE, MimeMap.mimeOf("x.$ext"), confidence = 0.85f, reason = "lista de mídia (.$ext)")

        ext == "zip" || ext == "tar" || ext == "gz" || ext == "tgz" || ext == "7z" || ext == "rar" || ext == "apk" ->
            Classification(FileKind.ARCHIVE, FileAction.BROWSE, MimeMap.mimeOf("x.$ext"), confidence = 0.9f, reason = "pacote (.$ext)")

        ext == "py" || ext == "js" -> Classification(FileKind.SCRIPT, FileAction.READ_ONLY, MimeMap.mimeOf("x.$ext"), confidence = 0.95f,
            reason = "script — NÃO executar")
        ext == "db" || ext == "sqlite" -> Classification(FileKind.DATABASE, FileAction.READ_ONLY, "application/x-sqlite3", confidence = 0.9f, reason = "banco de dados")
        ext == "nfo" -> Classification(FileKind.CONFIG, FileAction.READ_ONLY, "text/xml", confidence = 0.7f, reason = "metadados NFO")
        ext == "xml" -> Classification(FileKind.CONFIG, FileAction.READ_ONLY, "application/xml", confidence = 0.5f,
            reason = "XML — conteúdo decide se é addon/repo/config")
        ext == "json" -> Classification(FileKind.CONFIG, FileAction.READ_ONLY, "application/json", confidence = 0.7f, reason = "JSON (não é playlist)")
        ext == "srt" || ext == "ass" || ext == "vtt" || ext == "sub" ->
            Classification(FileKind.SUBTITLE, FileAction.READ_ONLY, MimeMap.mimeOf("x.$ext"), confidence = 0.9f, reason = "legenda")

        MimeMap.isVideoExt(ext) -> Classification(FileKind.VIDEO, FileAction.PLAY, MimeMap.mimeOf("x.$ext"), confidence = 0.85f, reason = "vídeo (.$ext)")
        MimeMap.isAudioExt(ext) -> Classification(FileKind.AUDIO, FileAction.PLAY, MimeMap.mimeOf("x.$ext"), confidence = 0.85f, reason = "áudio (.$ext)")

        ext == "jpg" || ext == "jpeg" || ext == "png" || ext == "webp" || ext == "gif" ->
            Classification(FileKind.IMAGE, FileAction.INSPECT, MimeMap.mimeOf("x.$ext"), confidence = 0.9f, reason = "imagem")
        ext == "txt" || ext == "log" || ext == "md" ->
            Classification(FileKind.TEXT, FileAction.INSPECT, "text/plain", confidence = 0.8f, reason = "texto")

        else -> null
    }
}
