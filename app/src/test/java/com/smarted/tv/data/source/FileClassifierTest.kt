package com.smarted.tv.data.source

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Testes do classificador central.
 * Rodam na JVM (sem Android): `./gradlew test`.
 */
class FileClassifierTest {

    private fun head(s: String) = s.toByteArray(Charsets.UTF_8)
    private fun bytes(vararg v: Int) = v.map { it.toByte() }.toByteArray()

    // ── Extensão ───────────────────────────────────────────────────────
    @Test
    fun `m3u8 e reconhecido como HLS e nao como lista de canais`() {
        val c = FileClassifier.classify("https://host/live/master.m3u8")
        assertEquals(FileKind.HLS, c.kind)
        assertEquals(FileAction.PLAY, c.action)
        assertEquals("application/vnd.apple.mpegurl", c.mime)
    }

    @Test
    fun `mpd e DASH`() {
        val c = FileClassifier.classify("video.mpd")
        assertEquals(FileKind.DASH, c.kind)
        assertEquals("application/dash+xml", c.mime)
    }

    @Test
    fun `m3u simples e lista navegavel`() {
        val c = FileClassifier.classify("lista.m3u")
        assertEquals(FileKind.PLAYLIST, c.kind)
        assertEquals(FileAction.BROWSE, c.action)
    }

    @Test
    fun `m4s nunca e video independente`() {
        val c = FileClassifier.classify("seg-001.m4s")
        assertEquals(FileKind.SEGMENT, c.kind)
        assertEquals(FileAction.NONE, c.action)
    }

    @Test
    fun `zip e pacote`() {
        assertEquals(FileKind.ARCHIVE, FileClassifier.classify("addon.zip").kind)
    }

    @Test
    fun `py nao pode ser executado`() {
        val c = FileClassifier.classify("default.py")
        assertEquals(FileKind.SCRIPT, c.kind)
        assertEquals(FileAction.READ_ONLY, c.action)
    }

    @Test
    fun `json nao e playlist`() {
        val c = FileClassifier.classify("info.json")
        assertEquals(FileKind.CONFIG, c.kind)
        assertFalse(c.isPlayable)
    }

    @Test
    fun `video e audio sao reproduziveis`() {
        assertTrue(FileClassifier.classify("filme.mkv").isPlayable)
        assertTrue(FileClassifier.classify("musica.flac").isPlayable)
    }

    // ── Magic bytes (conteúdo vence a extensão) ─────────────────────────
    @Test
    fun `zip renomeado para m3u e detectado pelo conteudo`() {
        val zipHead = bytes(0x50, 0x4B, 0x03, 0x04, 0x14, 0x00)
        val c = FileClassifier.classify("disfarcado.m3u", zipHead)
        assertEquals(FileKind.ARCHIVE, c.kind)
        assertTrue(c.sniffed)
    }

    @Test
    fun `texto com EXTM3U e HLS mesmo sem extensao`() {
        val hls = head("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000\n720p/index.m3u8\n")
        val c = FileClassifier.classify("sem-extensao", hls)
        assertEquals(FileKind.HLS, c.kind)
        assertTrue(c.sniffed)
    }

    @Test
    fun `texto com EXTM3U sem EXT-X e lista de canais`() {
        val m3u = head("#EXTM3U\n#EXTINF:-1,Globo\nhttp://host/globo.m3u8\n")
        val c = FileClassifier.classify("canais.txt", m3u)
        assertEquals(FileKind.PLAYLIST, c.kind)
    }

    @Test
    fun `addons xml e manifesto de repositorio`() {
        val xml = head("<?xml version=\"1.0\"?><addons><addon id=\"plugin.video.x\"/></addons>")
        val c = FileClassifier.classify("addons.xml", xml)
        assertEquals(FileKind.REPO_MANIFEST, c.kind)
    }

    @Test
    fun `mpd pelo conteudo`() {
        val mpd = head("<?xml version=\"1.0\"?><MPD xmlns=\"urn:mpeg:dash:schema:mpd:2011\"></MPD>")
        assertEquals(FileKind.DASH, FileClassifier.classify("manifest", mpd).kind)
    }

    @Test
    fun `mp4 ftyp e video e fmp4 e segmento`() {
        val video = ByteArray(12).also { "....ftypisom".toByteArray().copyInto(it) }
        assertEquals(FileKind.VIDEO, FileClassifier.classify("a.mp4", video).kind)

        val seg = ByteArray(12).also { "....ftypmsdh".toByteArray().copyInto(it) }
        assertEquals(FileKind.SEGMENT, FileClassifier.classify("a.m4s", seg).kind)
    }

    @Test
    fun `mpegts e reconhecido pelo sync 188`() {
        val ts = ByteArray(400)
        ts[0] = 0x47
        ts[188] = 0x47
        val c = FileClassifier.classify("stream.bin", ts)
        assertEquals(FileKind.SEGMENT, c.kind)   // segmento: não tratar como vídeo isolado
        assertTrue(c.reason.contains("MPEG-TS"))
    }

    @Test
    fun `desconhecido nao vira m3u`() {
        val c = FileClassifier.classify("arquivo.xyz")
        assertEquals(FileKind.UNKNOWN, c.kind)
        assertEquals(FileAction.INSPECT, c.action)
    }

    @Test
    fun `url de stream sem extensao e reconhecida`() {
        assertTrue(MimeMap.looksLikeStreamUrl("http://host:8080/live/user/pass/123"))
        assertFalse(MimeMap.looksLikeStreamUrl("filme.mkv"))
    }
}
