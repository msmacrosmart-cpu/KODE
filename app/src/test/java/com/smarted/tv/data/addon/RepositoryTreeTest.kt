package com.smarted.tv.data.addon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Fase D: catálogo de repositório (addons.xml), árvore dinâmica e
 * capacidades reais (instalável só quando o pacote existe).
 */
class RepositoryTreeTest {

    private val addonsXml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <addons>
          <addon id="plugin.video.alfa" name="Alfa" version="1.2.0" provider-name="Equipe Alfa">
            <requires>
              <import addon="xbmc.python" version="3.0.0"/>
              <import addon="script.module.requests" version="2.22.0"/>
            </requires>
            <extension point="xbmc.python.pluginsource" library="default.py">
              <provides>video</provides>
            </extension>
          </addon>
          <addon id="plugin.audio.radio" name="Rádio Beta" version="0.9.1" provider-name="Beta">
            <extension point="xbmc.python.pluginsource" library="addon.py">
              <provides>audio</provides>
            </extension>
          </addon>
          <addon id="repository.alfa" name="Alfa Repo" version="1.0.0" provider-name="Alfa">
            <requires><import addon="xbmc.addon" version="19.0.0"/></requires>
            <extension point="xbmc.addon.repository" name="Alfa">
              <info compressed="false">https://repo.alfa/addons.xml</info>
              <datadir zip="true">https://repo.alfa/zips/</datadir>
            </extension>
          </addon>
        </addons>
    """.trimIndent()

    // ── catálogo ─────────────────────────────────────────────────────
    @Test
    fun `addons xml lista todos os addons`() {
        val r = RepoIndexParser.parse(addonsXml)
        assertEquals(3, r.manifests.size)
        assertNull(r.error)
        assertEquals(listOf("plugin.video.alfa", "plugin.audio.radio", "repository.alfa"),
            r.manifests.map { it.id })
    }

    @Test
    fun `addons xml invalido explica o motivo`() {
        val r = RepoIndexParser.parse("<addons><addon id='x'>")
        assertTrue(r.manifests.isEmpty())
        assertNotNull(r.error)
    }

    @Test
    fun `raiz errada e rejeitada`() {
        val r = RepoIndexParser.parse("<playlist><item/></playlist>")
        assertTrue(r.manifests.isEmpty())
        assertTrue(r.error!!.contains("addons"))
    }

    // ── árvore ───────────────────────────────────────────────────────
    private fun tree(files: List<String>): RepositoryNode {
        val manifests = RepoIndexParser.parse(addonsXml).manifests
        return RepositoryTree.build(
            repoId = "repo-teste",
            repoName = "Repo de teste",
            manifests = manifests,
            filePaths = files,
            source = RepoSource(RepoSource.SourceKind.ZIP, "/tmp/repo.zip"),
        )
    }

    @Test
    fun `categorias saem do tipo real do addon`() {
        val root = tree(emptyList())
        val nomes = root.children.map { it.name }
        assertTrue(nomes.contains("Add-ons de vídeo"))
        assertTrue(nomes.contains("Add-ons de música"))
        assertTrue(nomes.contains("Repositórios"))
        assertEquals("3", root.metadata["addons"])
    }

    @Test
    fun `addon sem pacote no zip nao e instalavel e explica`() {
        val root = tree(listOf("addons.xml", "addons.xml.md5"))
        val alfa = RepositoryTree.find(root, "repo-teste::addon::plugin.video.alfa")!!
        assertFalse(alfa.isInstallable)
        assertFalse(alfa.capabilities.contains(RepositoryNode.Capability.INSTALL))
        assertTrue(alfa.metadata["installBlocked"]!!.contains("não encontrado"))

        // compatibilidade honesta: plugin python de vídeo = adaptação
        assertEquals(Compatibility.COMPATIBLE_WITH_ADAPTATION, alfa.compatibility)
    }

    @Test
    fun `addon com pacote presente e instalavel`() {
        val root = tree(
            listOf(
                "addons.xml",
                "plugin.video.alfa/plugin.video.alfa-1.2.0.zip",
                "plugin.audio.radio/plugin.audio.radio-0.9.1.zip",
            )
        )
        val alfa = RepositoryTree.find(root, "repo-teste::addon::plugin.video.alfa")!!
        assertTrue(alfa.isInstallable)
        assertTrue(alfa.capabilities.contains(RepositoryNode.Capability.INSTALL))
        assertEquals("plugin.video.alfa/plugin.video.alfa-1.2.0.zip", alfa.path)
        assertEquals("1.2.0", alfa.version)
    }

    @Test
    fun `arquivos fora do catalogo continuam visiveis`() {
        val root = tree(listOf("addons.xml", "addons.xml.md5", "docs/leia-me.txt", "tools/util.py"))
        val extras = root.children.filter { it.type != RepoNodeType.CATEGORY }
        assertTrue(extras.any { it.path == "docs/leia-me.txt" })
        assertTrue(extras.any { it.path == "docs" })
        // o manifesto do repositório não deve aparecer como conteúdo
        assertFalse(extras.any { it.path.endsWith("addons.xml") })
    }

    @Test
    fun `caminho da raiz ate o addon e encontrado`() {
        val root = tree(emptyList())
        val alfaId = "repo-teste::addon::plugin.video.alfa"
        val caminho = RepositoryTree.pathTo(root, alfaId)
        assertEquals(3, caminho.size)
        assertEquals(root.id, caminho.first().id)
        assertEquals(alfaId, caminho.last().id)
        assertNotNull(RepositoryTree.find(root, alfaId))
        assertNull(RepositoryTree.find(root, "nao-existe"))
    }

    @Test
    fun `repositorio remoto nao engana sobre pacote local`() {
        val manifests = RepoIndexParser.parse(addonsXml).manifests
        val root = RepositoryTree.build(
            repoId = "repo-url",
            repoName = "Repo remoto",
            manifests = manifests,
            filePaths = manifests.map { "${it.id}/${it.id}-${it.version}.zip" },
            source = RepoSource(RepoSource.SourceKind.URL, "https://repo.alfa/addons.xml"),
        )
        val alfa = RepositoryTree.find(root, "repo-url::addon::plugin.video.alfa")!!
        // o caminho remoto existe, então a capacidade INSTALL aparece...
        assertTrue(alfa.capabilities.contains(RepositoryNode.Capability.REMOTE))
        // ...mas o nó nunca é marcado como arquivo local
        assertFalse(alfa.capabilities.contains(RepositoryNode.Capability.LOCAL_FILE))
    }
}
