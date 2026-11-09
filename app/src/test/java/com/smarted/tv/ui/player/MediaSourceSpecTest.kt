package com.smarted.tv.ui.player

import androidx.media3.common.MimeTypes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Fase F — o que o player precisa saber para tocar cada tipo de mídia.
 * Não testa a renderização (exige aparelho): testa a decisão de tipo/URL.
 */
class MediaSourceSpecTest {

    @Test
    fun `hls e dash sao reconhecidos pela extensao`() {
        assertEquals(MimeTypes.APPLICATION_M3U8, MediaSourceSpec.mimeFromPath("http://a/b/live.m3u8"))
        assertEquals(MimeTypes.APPLICATION_MPD, MediaSourceSpec.mimeFromPath("http://a/b/manifest.mpd"))
        assertEquals(MimeTypes.APPLICATION_SS,
            MediaSourceSpec.mimeFromPath("http://a/b/manifest.ism/Manifest"))
    }

    @Test
    fun `parametros da url nao interferem no tipo`() {
        assertEquals(MimeTypes.APPLICATION_M3U8,
            MediaSourceSpec.mimeFromPath("https://cdn/x/index.m3u8?token=abc&exp=123"))
        assertEquals(MimeTypes.APPLICATION_MPD,
            MediaSourceSpec.mimeFromPath("https://cdn/x/manifest.mpd?auth=zzz#t=10"))
    }

    @Test
    fun `tipo desconhecido nao e chutado`() {
        assertNull(MediaSourceSpec.mimeFromPath("https://cdn/live/sem-extensao"))
        assertNull(MediaSourceSpec.mimeFromPath("content://doc/42"))
    }

    @Test
    fun `mime explicito tem prioridade sobre a extensao`() {
        val spec = MediaSourceSpec(uri = "https://cdn/sem-extensao", mimeHint = MimeTypes.APPLICATION_M3U8)
        assertEquals(MimeTypes.APPLICATION_M3U8, spec.effectiveMime())
    }

    @Test
    fun `protocolos suportados e nao suportados`() {
        assertTrue(MediaSourceSpec("https://a/b.m3u8").isSupported)
        assertTrue(MediaSourceSpec("http://a/b.mp4").isSupported)
        assertTrue(MediaSourceSpec("content://com.android.externalstorage.documents/x").isSupported)
        assertTrue(MediaSourceSpec("file:///sdcard/filme.mkv").isSupported)
        assertTrue(MediaSourceSpec("/sdcard/filme.mkv").isSupported)
        assertFalse(MediaSourceSpec("plugin://plugin.video.x/1").isSupported)
        assertFalse(MediaSourceSpec("magnet:?xt=urn:btih:abc").isSupported)
    }

    @Test
    fun `local e remoto sao distinguidos`() {
        assertTrue(MediaSourceSpec("content://doc/1").isLocal)
        assertTrue(MediaSourceSpec("file:///a/b.mp4").isLocal)
        assertFalse(MediaSourceSpec("https://a/b.mp4").isLocal)
    }

    @Test
    fun `headers e legenda seguem junto com a midia`() {
        val spec = MediaSourceSpec(
            uri = "https://cdn/live.m3u8?token=segredo",
            mimeHint = MimeTypes.APPLICATION_M3U8,
            headers = mapOf("Referer" to "https://site/", "User-Agent" to "UA"),
            subtitles = listOf("https://cdn/legenda.vtt"),
            isLive = true,
        )
        assertEquals(2, spec.headers.size)
        assertEquals("https://site/", spec.headers["Referer"])
        assertTrue(spec.isLive)
        assertEquals(listOf("https://cdn/legenda.vtt"), spec.subtitles)
        // a URL inteira é preservada (query string não é descartada)
        assertEquals("https://cdn/live.m3u8?token=segredo", spec.uri)
    }
}
