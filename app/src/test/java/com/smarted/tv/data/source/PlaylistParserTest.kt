package com.smarted.tv.data.source

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Testes dos parsers de lista — cada formato tem seu próprio caminho.
 * Rodam na JVM: `./gradlew test`.
 */
class PlaylistParserTest {

    // ── M3U (lista de itens) ───────────────────────────────────────────
    private val m3u = """
        #EXTM3U
        #EXTINF:-1 tvg-id="globo" tvg-logo="http://logo/globo.png" group-title="Filmes",O Poderoso Chefão
        http://host/filmes/chefao.mkv
        #EXTINF:-1 group-title="Notícias",Globo News
        http://host/live/globo.m3u8
    """.trimIndent()

    @Test
    fun `m3u extrai itens com grupo logo e id`() {
        val p = PlaylistParser.parse(m3u, PlaylistFormat.M3U)
        assertEquals(PlaylistFormat.M3U, p.format)
        assertEquals(2, p.entries.size)

        val filme = p.entries[0]
        assertEquals("O Poderoso Chefão", filme.title)
        assertEquals("Filmes", filme.group)
        assertEquals("http://logo/globo.png", filme.logoUrl)
        assertEquals("globo", filme.tvgId)
        assertEquals(PlaylistEntryType.VOD, filme.type)

        val canal = p.entries[1]
        assertEquals(PlaylistEntryType.LIVE, canal.type)
    }

    @Test
    fun `m3u ignora linhas que nao sao url e nao lanca excecao`() {
        val p = PlaylistParser.parse(
            "#EXTM3U\n#EXTINF:-1,Teste\nnao-e-url\nhttp://ok/stream.ts\n",
            PlaylistFormat.M3U,
        )
        assertEquals(1, p.entries.size)
        assertTrue(p.warnings.any { it.contains("não é URL") })
    }

    @Test
    fun `m3u vazia gera warning`() {
        val p = PlaylistParser.parse("#EXTM3U\n", PlaylistFormat.M3U)
        assertTrue(p.entries.isEmpty())
        assertTrue(p.warnings.isNotEmpty())
    }

    // ── HLS (manifesto, não lista de canais) ──────────────────────────
    private val master = """
        #EXTM3U
        #EXT-X-VERSION:6
        #EXT-X-STREAM-INF:BANDWIDTH=5200000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
        1080p/index.m3u8
        #EXT-X-STREAM-INF:BANDWIDTH=1800000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
        720p/index.m3u8
    """.trimIndent()

    @Test
    fun `hls master extrai variantes com resolucao e bitrate`() {
        val p = PlaylistParser.parse(master, PlaylistFormat.HLS)
        assertTrue(p.isMasterManifest)
        assertEquals(2, p.variants.size)
        assertEquals(1920, p.variants[0].width)
        assertEquals(1080, p.variants[0].height)
        assertEquals(5200000L, p.variants[0].bandwidthBps)
        assertEquals("1080p/index.m3u8", p.variants[0].uri)
        assertEquals(2, p.entries.size)
    }

    @Test
    fun `hls media manifesto nao vira canais`() {
        val media = """
            #EXTM3U
            #EXT-X-TARGETDURATION:6
            #EXT-X-MAP:URI="init.mp4"
            #EXTINF:6.0,
            seg1.m4s
            #EXTINF:6.0,
            seg2.m4s
        """.trimIndent()
        val p = PlaylistParser.parse(media, PlaylistFormat.HLS)
        assertFalse(p.isMasterManifest)
        assertTrue(p.entries.isEmpty()) // segmentos não são itens navegáveis
    }

    @Test
    fun `hls criptografado avisa sobre DRM`() {
        val enc = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"key.bin\"\n#EXTINF:6,\nseg.ts\n"
        val p = PlaylistParser.parse(enc, PlaylistFormat.HLS)
        assertTrue(p.warnings.any { it.contains("criptografado") })
    }

    // ── PLS ────────────────────────────────────────────────────────────
    @Test
    fun `pls extrai FileN e TitleN`() {
        val pls = "[playlist]\nFile1=http://a/1.mp3\nTitle1=Primeira\nFile2=http://a/2.mp3\nTitle2=Segunda\nNumberOfEntries=2\n"
        val p = PlaylistParser.parse(pls, PlaylistFormat.PLS)
        assertEquals(2, p.entries.size)
        assertEquals("Primeira", p.entries[0].title)
        assertEquals("http://a/2.mp3", p.entries[1].url)
    }

    // ── XSPF ───────────────────────────────────────────────────────────
    @Test
    fun `xspf extrai location e title`() {
        val xspf = """
            <?xml version="1.0" encoding="UTF-8"?>
            <playlist xmlns="http://xspf.org/ns/0/" version="1">
              <trackList>
                <track><title>Faixa A</title><location>http://a/a.mp3</location></track>
                <track><title>Faixa B</title><location>http://a/b.mp3</location></track>
              </trackList>
            </playlist>
        """.trimIndent()
        val p = PlaylistParser.parse(xspf, PlaylistFormat.XSPF)
        assertEquals(2, p.entries.size)
        assertEquals("Faixa A", p.entries[0].title)
    }

    // ── ASX ────────────────────────────────────────────────────────────
    @Test
    fun `asx extrai ref href`() {
        val asx = "<asx version=\"3.0\"><entry><title>Rádio X</title><ref href=\"http://r/x.asx\"/></entry></asx>"
        val p = PlaylistParser.parse(asx, PlaylistFormat.ASX)
        assertEquals(1, p.entries.size)
        assertEquals("Rádio X", p.entries[0].title)
    }

    // ── WPL ────────────────────────────────────────────────────────────
    @Test
    fun `wpl extrai media src`() {
        val wpl = "<smil><body><seq><media src=\"C:\\musica\\a.mp3\"/></seq></body></smil>"
        val p = PlaylistParser.parse(wpl, PlaylistFormat.WPL)
        assertEquals(1, p.entries.size)
        assertTrue(p.entries[0].url.endsWith("a.mp3"))
    }

    // ── CUE ────────────────────────────────────────────────────────────
    @Test
    fun `cue extrai faixas com artista`() {
        val cue = """
            PERFORMER "Artista"
            TITLE "Álbum"
            FILE "album.flac" WAVE
              TRACK 01 AUDIO
                TITLE "Primeira"
                INDEX 01 00:00:00
              TRACK 02 AUDIO
                TITLE "Segunda"
                INDEX 01 03:20:00
        """.trimIndent()
        val p = PlaylistParser.parse(cue, PlaylistFormat.CUE)
        assertEquals(2, p.entries.size)
        assertEquals("Artista - Primeira", p.entries[0].title)
        assertEquals("album.flac", p.entries[0].url)
    }

    // ── STRM ───────────────────────────────────────────────────────────
    @Test
    fun `strm usa a primeira url do arquivo`() {
        val p = PlaylistParser.parse("http://host/live/stream.m3u8\n", PlaylistFormat.STRM)
        assertEquals(1, p.entries.size)
        assertEquals("http://host/live/stream.m3u8", p.entries[0].url)
    }

    // ── Detecção de formato pelo conteúdo ──────────────────────────────
    @Test
    fun `detecta formato pelo conteudo e nao pela extensao`() {
        assertEquals(PlaylistFormat.HLS, PlaylistParser.detectFormat(master))
        assertEquals(PlaylistFormat.M3U, PlaylistParser.detectFormat(m3u))
        assertEquals(PlaylistFormat.PLS, PlaylistParser.detectFormat("[playlist]\nFile1=http://a\n"))
        assertEquals(PlaylistFormat.XSPF, PlaylistParser.detectFormat("<playlist xmlns=\"http://xspf.org/ns/0/\">"))
        assertEquals(PlaylistFormat.CUE, PlaylistParser.detectFormat("FILE \"a.flac\" WAVE\nTRACK 01 AUDIO\n"))
        assertEquals(PlaylistFormat.STRM, PlaylistParser.detectFormat("http://host/x"))
    }

    @Test
    fun `formato desconhecido devolve warning e nao explode`() {
        val p = PlaylistParser.parse("conteúdo qualquer\nsem formato")
        assertEquals(PlaylistFormat.UNKNOWN, p.format)
        assertTrue(p.entries.isEmpty())
        assertNotNull(p.warnings.firstOrNull())
    }
}
