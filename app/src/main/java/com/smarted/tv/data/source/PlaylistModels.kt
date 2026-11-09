package com.smarted.tv.data.source

/** Tipo de uma entrada de playlist. */
enum class PlaylistEntryType { LIVE, VOD, SERIES, AUDIO, UNKNOWN }

/**
 * Item extraído de uma lista/índice de mídia.
 * Campos opcionais refletem o que cada formato realmente fornece.
 */
data class PlaylistEntry(
    val title: String,
    val url: String,
    val type: PlaylistEntryType = PlaylistEntryType.UNKNOWN,
    val group: String? = null,
    val logoUrl: String? = null,
    val tvgId: String? = null,
    val durationSec: Long? = null,
    val attributes: Map<String, String> = emptyMap(),
)

/** Resultado do parsing de uma lista. */
data class Playlist(
    val entries: List<PlaylistEntry>,
    val format: PlaylistFormat,
    val isMasterManifest: Boolean = false,
    val variants: List<StreamVariant> = emptyList(),
    val warnings: List<String> = emptyList(),
)

enum class PlaylistFormat { M3U, HLS, MPD, PLS, XSPF, ASX, WPL, CUE, STRM, UNKNOWN }

/** Variante de um master HLS/DASH (resolução, bitrate, codecs). */
data class StreamVariant(
    val uri: String,
    val bandwidthBps: Long? = null,
    val width: Int? = null,
    val height: Int? = null,
    val codecs: String? = null,
    val audioGroup: String? = null,
)

/** Alterações de segmento HLS (#EXT-X-MAP, #EXT-X-KEY) — necessárias para reproduzir. */
data class HlsSegmentInfo(
    val mediaSequence: Long? = null,
    val targetDuration: Int? = null,
    val initSegmentUri: String? = null,
    val encryptionMethod: String? = null,
)
