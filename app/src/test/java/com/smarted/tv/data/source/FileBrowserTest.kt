package com.smarted.tv.data.source

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Regras do navegador de arquivos (Fase C), sem Android:
 * ordenação, busca, breadcrumb, tamanhos, datas e decisão de ação.
 */
class FileBrowserTest {

    private fun dir(name: String, modified: Long = 0) =
        BrowseEntry("content://tree/$name", name, isDirectory = true, lastModified = modified)

    private fun file(name: String, size: Long = 0, modified: Long = 0) =
        BrowseEntry(
            uri = "content://tree/$name",
            name = name,
            isDirectory = false,
            size = size,
            lastModified = modified,
            kind = FileClassifier.classify(name).kind,
            action = FileClassifier.classify(name).action,
        )

    private val amostra = listOf(
        file("b.mkv", 3_000),
        dir("Zeta"),
        file("a.MP4", 1_000),
        dir("alfa"),
        file("c.srt", 10),
    )

    @Test
    fun `pastas vem antes e nome nao diferencia maiusculas`() {
        val out = FileBrowser.sort(amostra)
        assertEquals(listOf("alfa", "Zeta", "a.MP4", "b.mkv", "c.srt"), out.map { it.name })
    }

    @Test
    fun `ordenar por tamanho respeita ordem pedida e mantem pastas na frente`() {
        val desc = FileBrowser.sort(amostra, SortKey.SIZE, ascending = false)
        // tamanho decrescente: b.mkv (3000) > a.MP4 (1000) > c.srt (10); pastas na frente
        assertEquals(listOf("alfa", "Zeta", "b.mkv", "a.MP4", "c.srt"), desc.map { it.name })
    }

    @Test
    fun `ordenar por data usa metadados reais`() {
        val entradas = listOf(
            file("antigo.txt", modified = 1_000),
            file("novo.txt", modified = 9_000),
        )
        assertEquals(listOf("antigo.txt", "novo.txt"), FileBrowser.sort(entradas, SortKey.DATE).map { it.name })
        assertEquals(listOf("novo.txt", "antigo.txt"),
            FileBrowser.sort(entradas, SortKey.DATE, ascending = false).map { it.name })
    }

    @Test
    fun `busca ignora acentos e maiusculas e nunca sai da pasta`() {
        val entradas = listOf(file("São_Paulo.jpg"), file("rio.png"), dir("Sao_Conteudo"))
        assertEquals(listOf("São_Paulo.jpg", "Sao_Conteudo"),
            FileBrowser.filter(entradas, "sao").map { it.name })
        assertTrue(FileBrowser.filter(entradas, "xyz").isEmpty())
    }

    @Test
    fun `display aplica busca e ordenacao juntas`() {
        val state = FilesState(
            crumbs = listOf(Crumb("content://tree", "tree")),
            entries = amostra,
            query = "c.",
            sortKey = SortKey.NAME,
        )
        assertEquals(listOf("c.srt"), FileBrowser.display(state).map { it.name })
    }

    @Test
    fun `breadcrumb e resumo do diretorio sao exatos`() {
        val crumbs = listOf(Crumb("u0", "Armazenamento"), Crumb("u1", "Filmes"), Crumb("u2", "2024"))
        assertEquals("Armazenamento  ›  Filmes  ›  2024", FileBrowser.breadcrumbText(crumbs))
        assertEquals("2 pastas · 3 arquivos", FileBrowser.summarize(amostra))
        assertEquals("Vazio", FileBrowser.summarize(emptyList()))
        assertEquals("1 pasta", FileBrowser.summarize(listOf(dir("x"))))
    }

    @Test
    fun `tamanho e data desconhecidos aparecem como travessao`() {
        assertEquals("—", FileBrowser.describeSize(0))
        assertEquals("512 B", FileBrowser.describeSize(512))
        assertEquals("1.0 KB", FileBrowser.describeSize(1024))
        assertEquals("2.5 MB", FileBrowser.describeSize(2_621_440))
        assertEquals("—", FileBrowser.describeDate(0))
        assertTrue(FileBrowser.describeDate(1_700_000_000_000).matches(Regex("\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}")))
    }

    @Test
    fun `mime do sistema complementa a classificacao sem sobrepor o conteudo`() {
        // extensão .bin é desconhecida; o MIME do sistema diz que é vídeo
        val porMime = FileBrowser.classify("arquivo.bin", "video/x-matroska")
        assertEquals(FileKind.VIDEO, porMime.kind)
        assertEquals(FileAction.PLAY, porMime.action)

        // extensão conhecida vence o MIME genérico
        val porExt = FileBrowser.classify("filme.mkv", "application/octet-stream")
        assertEquals(FileKind.VIDEO, porExt.kind)
        assertTrue(porExt.reason.isNotEmpty())
    }

    @Test
    fun `zip e pasta de arquivos sao navegaveis mas ts nao e video independente`() {
        val zip = FileBrowser.classify("repo.zip", "application/zip")
        assertEquals(FileKind.ARCHIVE, zip.kind)
        assertEquals(FileAction.BROWSE, zip.action)

        // .ts pode ser vídeo MPEG-TS independente ou segmento; o classificador
        // marca como SEGMENT (fragmento) com ação de reprodução — não é "lista".
        val ts = FileBrowser.classify("seg-001.ts", "video/mp2t")
        assertEquals(FileKind.SEGMENT, ts.kind)
        assertFalse(ts.action == FileAction.BROWSE)
    }

    @Test
    fun `estado sem fonte nao finge ter conteudo`() {
        val vazio = FilesState()
        assertFalse(vazio.hasSource)
        assertFalse(vazio.canGoUp)
        assertTrue(vazio.entries.isEmpty())
        val fundo = FilesState(crumbs = listOf(Crumb("u", "Raiz")))
        assertTrue(fundo.hasSource)
        assertFalse(fundo.canGoUp)
    }

    @Test
    fun `uri insegura e rejeitada e http nao e arquivo`() {
        assertFalse(SafFileSystem.isSafeDocumentUri("content://x/../etc"))
        assertFalse(SafFileSystem.isSafeDocumentUri("https://exemplo.com/a.m3u8"))
        assertTrue(SafFileSystem.isSafeDocumentUri("content://com.android.externalstorage.documents/tree/primary%3AFilmes"))
    }
}
