package com.smarted.tv.ui.player

import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.exoplayer.dash.DashMediaSource
import androidx.media3.exoplayer.hls.HlsMediaSource
import androidx.media3.exoplayer.source.MediaSource
import androidx.media3.exoplayer.source.ProgressiveMediaSource

/**
 * Descrição de uma mídia a reproduzir — o que o app REALMENTE sabe sobre ela.
 *
 * @param uri endereço completo (URL com query string preservada, `content://`,
 *            `file://` ou caminho). Nunca truncado.
 * @param mimeHint MIME explícito quando conhecido (HLS/DASH/reprodução local).
 * @param headers cabeçalhos HTTP exigidos pela fonte (Referer, User-Agent, auth).
 *                Nunca são gravados em log.
 * @param subtitles URLs/paths de legendas informadas pela fonte.
 */
data class MediaSourceSpec(
    val uri: String,
    val mimeHint: String? = null,
    val headers: Map<String, String> = emptyMap(),
    val title: String = "",
    val isLive: Boolean = false,
    val subtitles: List<String> = emptyList(),
) {
    /** Protocolo real, inferido da URI (nunca adivinhado do título). */
    val scheme: String get() = Uri.parse(uri).scheme.orEmpty().lowercase()

    val isLocal: Boolean
        get() = scheme == "content" || scheme == "file" || uri.startsWith("/")

    /** Só é tocável o que tem protocolo conhecido. */
    val isSupported: Boolean
        get() = isLocal || scheme == "http" || scheme == "https" || scheme == "rtsp" || scheme == "rtmp"

    /** Tipo efetivo: MIME explícito ou inferido pela extensão do caminho. */
    fun effectiveMime(): String? = mimeHint ?: mimeFromPath(uri)

    companion object {
        /**
         * MIME pela extensão do CAMINHO (ignora query/fragmento).
         * Retorna null quando não sabe — o player então decide sozinho.
         */
        fun mimeFromPath(uri: String): String? {
            val path = uri.substringBefore('?').substringBefore('#').lowercase()
            return when {
                path.endsWith(".m3u8") -> MimeTypes.APPLICATION_M3U8
                path.endsWith(".mpd") -> MimeTypes.APPLICATION_MPD
                path.endsWith(".ism") || path.endsWith(".isml") -> MimeTypes.APPLICATION_SS
                path.endsWith(".mp4") || path.endsWith(".m4v") -> MimeTypes.VIDEO_MP4
                path.endsWith(".webm") -> MimeTypes.VIDEO_WEBM
                path.endsWith(".mkv") -> "video/x-matroska"
                path.endsWith(".ts") -> MimeTypes.VIDEO_MP2T
                path.endsWith(".flac") -> "audio/flac"
                path.endsWith(".mp3") -> MimeTypes.AUDIO_MPEG
                path.endsWith(".m4a") || path.endsWith(".aac") -> MimeTypes.AUDIO_AAC
                path.endsWith(".ogg") || path.endsWith(".opus") -> MimeTypes.AUDIO_OGG
                path.endsWith(".wav") -> "audio/wav"
                else -> null
            }
        }

        /**
         * Monta o [MediaSource] certo para o tipo. Isto é o que permite tocar
         * DASH e HLS sem extensão, além de mídia local do SAF, com cabeçalhos.
         */
        fun buildSource(context: android.content.Context, spec: MediaSourceSpec): MediaSource {
            val httpFactory: DataSource.Factory =
                if (spec.headers.isEmpty()) {
                    DefaultDataSource.Factory(context)
                } else {
                    val http = DefaultHttpDataSource.Factory()
                        .setUserAgent(spec.headers["User-Agent"] ?: DEFAULT_UA)
                        .setDefaultRequestProperties(spec.headers)
                        .setAllowCrossProtocolRedirects(true)
                    DefaultDataSource.Factory(context, http)
                }

            val mime = spec.effectiveMime()
            val item = MediaItem.Builder()
                .setUri(spec.uri)
                .apply { mime?.let { setMimeType(it) } }
                .build()

            return when (mime) {
                MimeTypes.APPLICATION_M3U8 -> HlsMediaSource.Factory(httpFactory).createMediaSource(item)
                MimeTypes.APPLICATION_MPD -> DashMediaSource.Factory(httpFactory).createMediaSource(item)
                MimeTypes.APPLICATION_SS -> ProgressiveMediaSource.Factory(httpFactory).createMediaSource(item)
                else -> ProgressiveMediaSource.Factory(httpFactory).createMediaSource(item)
            }
        }

        const val DEFAULT_UA = "SmartED-TV/1.0 (Android; ExoPlayer)"
    }
}
