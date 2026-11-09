package com.smarted.tv.integration

import com.smarted.tv.data.addon.AddonKind
import com.smarted.tv.data.addon.AddonManifestParser
import com.smarted.tv.data.addon.Compatibility
import com.smarted.tv.data.addon.CompatibilityEvaluator
import com.smarted.tv.data.addon.RepoIndexParser
import com.smarted.tv.data.addon.RepoSource
import com.smarted.tv.data.addon.RepositoryNode
import com.smarted.tv.data.addon.RepositoryTree
import com.smarted.tv.data.archive.ZipInspector
import com.smarted.tv.data.plugin.PluginRouter
import com.smarted.tv.data.plugin.PluginUri
import com.smarted.tv.data.source.FileBrowser
import com.smarted.tv.data.source.FileClassifier
import com.smarted.tv.data.source.FileKind
import com.smarted.tv.data.source.PlaylistFormat
import com.smarted.tv.data.source.PlaylistParser
import com.smarted.tv.data.source.SortKey
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Fase G — teste de integração ponta a ponta, sem Android e sem rede.
 *
 * Percorre o caminho real que o app usa:
 *   ZIP de repositório → ZipInspector → addons.xml → catálogo →
 *   árvore com categorias → add-on instalável → URI plugin:// →
 *   roteador sem adaptador (declara o limite real).
 *
 * E, paralelamente, um fluxo de mídia:
 *   arquivo descoberto → classificação → playlist/HLS lida → item reproduzível.
 */
class EndToEndFlowTest {

    private fun repoZip(): File {
        val addonsXml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <addons>
              <addon id="plugin.video.alfa" name="Alfa" version="1.0.0" provider-name="Equipe">
                <requires><import addon="xbmc.python" version="3.0.0"/></requires>
                <extension point="xbmc.python.pluginsource" library="default.py">
                  <provides>video</provides>
                </extension>
              </addon>
              <addon id="repository.alfa" name="Repo Alfa" version="1.0.0">
                <extension point="xbmc.addon.repository"/>
              </addon>
            </addons>
        """.trimIndent()

        val addonZip = """
            <addon id="plugin.video.alfa" name="Alfa" version="1.0.0" provider-name="Equipe">
              <requires><import addon="xbmc.python" version="3.0.0"/></requires>
              <extension point="xbmc.python.pluginsource" library="default.py">
                <provides>video</provides>
              </extension>
            </addon>
        """.trimIndent()

        val file = Files.createTempFile("repo-integracao-", ".zip").toFile()
        ZipOutputStream(file.outputStream()).use { out ->
            out.putNextEntry(ZipEntry("addons.xml")); out.write(addonsXml.toByteArray()); out.closeEntry()
            out.putNextEntry(ZipEntry("addons.xml.md5")); out.write("d41d8cd98f00b204e9800998ecf8427e".toByteArray()); out.closeEntry()

            // pacote interno real (ZIP dentro do ZIP), como nos repositórios do Kodi
            val interno = java.io.ByteArrayOutputStream()
            ZipOutputStream(interno).use { z ->
                z.putNextEntry(ZipEntry("plugin.video.alfa/addon.xml")); z.write(addonZip.toByteArray()); z.closeEntry()
                z.putNextEntry(ZipEntry("plugin.video.alfa/default.py")); z.write("# nada é executado".toByteArray()); z.closeEntry()
            }
            out.putNextEntry(ZipEntry("plugin.video.alfa/plugin.video.alfa-1.0.0.zip"))
            out.write(interno.toByteArray())
            out.closeEntry()
        }
        return file
    }

    @Test
    fun `fluxo completo de repositorio ate plugin e limite honesto`() {
        val zip = repoZip()

        // 1) inspeção segura
        val report = ZipInspector.inspect(zip)
        assertTrue(report.isRepository)
        assertTrue(report.warnings.isEmpty())
        assertEquals(0, report.unsafeEntries.size)

        // 2) catálogo real
        val xml = ZipInspector.readEntry(zip, "addons.xml")!!.toString(Charsets.UTF_8)
        val catalog = RepoIndexParser.parse(xml)
        assertEquals(2, catalog.manifests.size)

        // 3) árvore com capacidades reais (o pacote existe dentro do ZIP)
        val tree = RepositoryTree.build(
            repoId = "repo-integra",
            repoName = "Repo Integração",
            manifests = catalog.manifests,
            filePaths = report.entries.map { it.name },
            source = RepoSource(RepoSource.SourceKind.ZIP, zip.absolutePath),
        )
        val alfa = RepositoryTree.find(tree, "repo-integra::addon::plugin.video.alfa")!!
        assertTrue(alfa.isInstallable)
        assertTrue(alfa.capabilities.contains(RepositoryNode.Capability.INSTALL))
        assertEquals(Compatibility.COMPATIBLE_WITH_ADAPTATION, alfa.compatibility)

        val repoAddon = RepositoryTree.find(tree, "repo-integra::addon::repository.alfa")!!
        assertEquals(Compatibility.COMPATIBLE, repoAddon.compatibility)

        // 4) pacote interno é um add-on válido por si só
        val interno = ZipInspector.readEntry(zip, "plugin.video.alfa/plugin.video.alfa-1.0.0.zip")!!
        val internoFile = Files.createTempFile("interno-", ".zip").toFile()
        internoFile.writeBytes(interno)
        val internoReport = ZipInspector.inspect(internoFile)
        assertEquals(listOf("plugin.video.alfa/addon.xml"), internoReport.addonXmlPaths)
        val manif = AddonManifestParser.parse(
            ZipInspector.readEntry(internoFile, "plugin.video.alfa/addon.xml")!!.toString(Charsets.UTF_8)
        ).manifest!!
        assertEquals(AddonKind.VIDEO, CompatibilityEvaluator.kindOf(manif))

        // 5) plugin:// daquele add-on: sem adaptador → limite declarado
        val uri = PluginUri.parse("plugin://plugin.video.alfa/?mode=main")!!
        assertEquals("plugin.video.alfa", uri.addonId)
        val router = PluginRouter(installed = { emptyList() })
        val routed = kotlinx.coroutines.runBlocking { router.route(uri.raw) }
        assertTrue(routed is PluginRouter.Result.Unsupported)
        assertTrue((routed as PluginRouter.Result.Unsupported).reason.contains("não está instalado"))

        internoFile.delete()
        zip.delete()
    }

    @Test
    fun `fluxo de midia playlist hls e arquivo local`() {
        // arquivo .m3u8 detectado pelo conteúdo, não pela extensão
        val master = """
            #EXTM3U
            #EXT-X-STREAM-INF:BANDWIDTH=2400000,RESOLUTION=1280x720
            720p/index.m3u8
            #EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
            360p/index.m3u8
        """.trimIndent()
        val classified = FileBrowser.classify("sem-extensao", "application/vnd.apple.mpegurl", master.toByteArray())
        assertEquals(FileKind.HLS, classified.kind)

        val playlist = PlaylistParser.parse(master, PlaylistFormat.HLS)
        assertEquals(PlaylistFormat.HLS, playlist.format)
        assertTrue(playlist.isMasterManifest)
        assertEquals(2, playlist.variants.size)
        assertTrue(playlist.entries.all { it.url.startsWith("http") })

        // lista de canais comum continua sendo lista navegável
        val lista = FileBrowser.classify("canais.m3u", null, "#EXTM3U\n#EXTINF:-1,Canal\nhttp://a/b\n".toByteArray())
        assertEquals(FileKind.PLAYLIST, lista.kind)

        // segmento não é vídeo independente
        val segmento = FileClassifier.classify("init.m4s")
        assertEquals(FileKind.SEGMENT, segmento.kind)
    }

    @Test
    fun `navegador mantem ordem e busca mesmo com muitos itens`() {
        val pasta = (1..200).map { i ->
            com.smarted.tv.data.source.BrowseEntry(
                uri = "content://doc/$i",
                name = "arquivo-%03d.%s".format(i, if (i % 3 == 0) "mkv" else "srt"),
                isDirectory = false,
                size = i.toLong() * 100,
                kind = if (i % 3 == 0) FileKind.VIDEO else FileKind.SUBTITLE,
            )
        } + com.smarted.tv.data.source.BrowseEntry("content://doc/d", "Filmes", isDirectory = true)

        val state = com.smarted.tv.data.source.FilesState(
            crumbs = listOf(com.smarted.tv.data.source.Crumb("content://doc", "doc")),
            entries = pasta,
            sortKey = SortKey.SIZE,
            ascending = false,
        )
        val ordenado = FileBrowser.display(state)
        assertEquals("Filmes", ordenado.first().name)
        assertEquals("arquivo-200.srt", ordenado[1].name)

        val filtrado = FileBrowser.display(state.copy(query = "arquivo-05"))
        assertEquals(10, filtrado.size) // 050..059
        assertNotNull(filtrado.first())
        assertFalse(filtrado.any { it.isDirectory })
    }
}
