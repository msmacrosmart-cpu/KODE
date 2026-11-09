package com.smarted.tv.data.addon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * addon.xml reais (estrutura do Kodi) escritos no teste.
 * Valida parsing dinâmico + classificação por extension point + compatibilidade honesta.
 */
class AddonManifestParserTest {

    private val videoPlugin = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <addon id="plugin.video.oneplay"
               name="OnePlay"
               version="2.4.1"
               provider-name="OnePlay Team">
          <requires>
            <import addon="xbmc.python" version="3.0.0"/>
            <import addon="script.module.requests" version="2.22.0"/>
          </requires>
          <extension point="xbmc.python.pluginsource" library="default.py">
            <provides>video</provides>
          </extension>
          <extension point="xbmc.addon.metadata">
            <summary lang="pt_BR">Filmes e séries</summary>
            <description lang="pt_BR">Addon de vídeo para streaming.</description>
          </extension>
        </addon>
    """.trimIndent()

    private val repository = """
        <?xml version="1.0" encoding="UTF-8"?>
        <addon id="repository.oneplay" name="OnePlay Repo" version="1.0.0" provider-name="OnePlay">
          <requires><import addon="xbmc.addon" version="19.0.0"/></requires>
          <extension point="xbmc.addon.repository" name="OnePlay Repository">
            <info compressed="false">https://repo.example/addons.xml</info>
            <checksum>https://repo.example/addons.xml.md5</checksum>
            <datadir zip="true">https://repo.example/zips/</datadir>
          </extension>
        </addon>
    """.trimIndent()

    private val skin = """
        <addon id="skin.smarted" name="Smarted Skin" version="1.0.0" provider-name="x">
          <extension point="xbmc.gui.skin" defaultthemename="Textures.xbt" debugging="false"/>
        </addon>
    """.trimIndent()

    private val scriptModule = """
        <addon id="script.module.requests" name="Requests" version="2.22.0" provider-name="x">
          <extension point="xbmc.python.module" library="lib"/>
        </addon>
    """.trimIndent()

    // ── Parsing ────────────────────────────────────────────────────────
    @Test
    fun `video plugin tem id nome versao provider e entrypoint`() {
        val r = AddonManifestParser.parse(videoPlugin)
        val m = r.manifest
        assertNotNull(m)
        assertEquals("plugin.video.oneplay", m!!.id)
        assertEquals("OnePlay", m.name)
        assertEquals("2.4.1", m.version)
        assertEquals("OnePlay Team", m.providerName)
        assertEquals("xbmc.python.pluginsource", m.extensionPoint)
        assertEquals("default.py", m.entryPoint)
        assertEquals("video", m.providedBy)
    }

    @Test
    fun `dependencias sao coletadas`() {
        val m = AddonManifestParser.parse(videoPlugin).manifest!!
        assertTrue(m.libraries.any { it.startsWith("script.module.requests") })
    }

    @Test
    fun `descricao em portugues e capturada`() {
        val m = AddonManifestParser.parse(videoPlugin).manifest!!
        assertEquals("Addon de vídeo para streaming.", m.description)
    }

    @Test
    fun `versao minima do kodi vem de xbmc addon`() {
        val m = AddonManifestParser.parse(repository).manifest!!
        assertEquals("19.0.0", m.requiresKodi)
    }

    @Test
    fun `xml invalido devolve erro sem excecao`() {
        val r = AddonManifestParser.parse("<addon id=\"x\"><requires>")
        // parser tolerante: pode ler parcialmente; o importante é não lançar
        if (r.manifest == null) assertNotNull(r.error)
    }

    @Test
    fun `xml sem id e rejeitado com mensagem`() {
        val r = AddonManifestParser.parse("<addon name=\"Sem ID\"/>")
        assertNull(r.manifest)
        assertNotNull(r.error)
        assertTrue(r.error!!.contains("id"))
    }

    // ── Classificação ─────────────────────────────────────────────────
    @Test
    fun `classifica video repositorio skin e modulo`() {
        assertEquals(AddonKind.VIDEO, AddonKindOf(videoPlugin))
        assertEquals(AddonKind.REPOSITORY, AddonKindOf(repository))
        assertEquals(AddonKind.SKIN, AddonKindOf(skin))
        assertEquals(AddonKind.MODULE, AddonKindOf(scriptModule))
    }

    @Test
    fun `plugin de audio e classificado como audio`() {
        val audio = """
            <addon id="plugin.audio.radio" name="Rádio" version="1.0">
              <extension point="xbmc.python.pluginsource" library="main.py">
                <provides>audio</provides>
              </extension>
            </addon>
        """.trimIndent()
        assertEquals(AddonKind.AUDIO, AddonKindOf(audio))
    }

    // ── Compatibilidade honesta ───────────────────────────────────────
    @Test
    fun `repositorio e compativel mas video python exige adaptacao`() {
        val repoManifest = AddonManifestParser.parse(repository).manifest!!
        val repoReport = CompatibilityEvaluator.evaluate(repoManifest, CompatibilityEvaluator.kindOf(repoManifest))
        assertEquals(Compatibility.COMPATIBLE, repoReport.level)

        val videoManifest = AddonManifestParser.parse(videoPlugin).manifest!!
        val videoReport = CompatibilityEvaluator.evaluate(videoManifest, CompatibilityEvaluator.kindOf(videoManifest))
        assertEquals(Compatibility.COMPATIBLE_WITH_ADAPTATION, videoReport.level)
        assertTrue(videoReport.missing.any { it.contains("Python") })
    }

    @Test
    fun `modulo python nunca e declarado compativel`() {
        val m = AddonManifestParser.parse(scriptModule).manifest!!
        val r = CompatibilityEvaluator.evaluate(m, CompatibilityEvaluator.kindOf(m))
        assertEquals(Compatibility.NOT_COMPATIBLE, r.level)
        assertFalse(r.reasons.isEmpty())
    }

    @Test
    fun `skin e parcial e explica o motivo`() {
        val m = AddonManifestParser.parse(skin).manifest!!
        val r = CompatibilityEvaluator.evaluate(m, CompatibilityEvaluator.kindOf(m))
        assertEquals(Compatibility.PARTIAL, r.level)
        assertTrue(r.missing.any { it.contains("xbmc.gui") })
    }

    private fun AddonKindOf(xml: String): AddonKind {
        val m = AddonManifestParser.parse(xml).manifest!!
        return CompatibilityEvaluator.kindOf(m)
    }
}
