package com.smarted.tv.data.addon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Fase E: o que decide se um pacote pode ser instalado.
 *
 * A parte de registro (SharedPreferences) precisa de Android; aqui testamos a
 * regra que evita instalar lixo: id válido, manifesto presente, dependências
 * declaradas e compatibilidade real.
 */
class AddonPackageRulesTest {

    private val installerRules = AddonInstallerRules

    private fun zipWith(addonXml: String): File {
        val file = Files.createTempFile("addon-teste-", ".zip").toFile()
        ZipOutputStream(file.outputStream()).use { out ->
            out.putNextEntry(ZipEntry("plugin.video.teste/addon.xml"))
            out.write(addonXml.toByteArray())
            out.closeEntry()
            out.putNextEntry(ZipEntry("plugin.video.teste/default.py"))
            out.write("print('nada é executado pelo app')".toByteArray())
            out.closeEntry()
        }
        return file
    }

    private val manifestoVideo = """
        <addon id="plugin.video.teste" name="Teste" version="1.0.0" provider-name="Teste">
          <requires>
            <import addon="xbmc.python" version="3.0.0"/>
            <import addon="script.module.requests" version="2.22.0"/>
          </requires>
          <extension point="xbmc.python.pluginsource" library="default.py">
            <provides>video</provides>
          </extension>
        </addon>
    """.trimIndent()

    @Test
    fun `id de addon segue o padrao do kodi`() {
        assertTrue(installerRules.isValidId("plugin.video.alfa"))
        assertTrue(installerRules.isValidId("repository.x"))
        assertTrue(installerRules.isValidId("script.module.requests"))
        assertFalse(installerRules.isValidId("../etc/passwd"))
        assertFalse(installerRules.isValidId(""))
        assertFalse(installerRules.isValidId("com barra"))
        assertFalse(installerRules.isValidId(".oculto"))
    }

    @Test
    fun `zip sem addon xml nao e addon`() {
        val semManifesto = Files.createTempFile("vazio-", ".zip").toFile()
        ZipOutputStream(semManifesto.outputStream()).use { out ->
            out.putNextEntry(ZipEntry("leiame.txt"))
            out.write("sem addon aqui".toByteArray())
            out.closeEntry()
        }
        val report = com.smarted.tv.data.archive.ZipInspector.inspect(semManifesto)
        assertFalse(report.hasAddonManifest)
        assertTrue(report.addonXmlPaths.isEmpty())
    }

    @Test
    fun `manifesto do zip e lido como video python com dependencias`() {
        val zip = zipWith(manifestoVideo)
        val report = com.smarted.tv.data.archive.ZipInspector.inspect(zip)
        assertEquals(listOf("plugin.video.teste/addon.xml"), report.addonXmlPaths)

        val xml = com.smarted.tv.data.archive.ZipInspector.readEntry(zip, "plugin.video.teste/addon.xml")!!
        val manifest = AddonManifestParser.parse(xml.toString(Charsets.UTF_8)).manifest!!
        assertEquals("plugin.video.teste", manifest.id)
        assertEquals(AddonKind.VIDEO, CompatibilityEvaluator.kindOf(manifest))

        val compat = CompatibilityEvaluator.evaluate(manifest, AddonKind.VIDEO)
        assertEquals(Compatibility.COMPATIBLE_WITH_ADAPTATION, compat.level)
        assertTrue(compat.missing.any { it.contains("Python") })

        // dependência real declarada (não inventada)
        assertTrue(manifest.libraries.contains("script.module.requests>=2.22.0"))
        zip.delete()
    }

    @Test
    fun `repositorio e compativel mas modulo nao`() {
        val repo = AddonManifestParser.parse(
            """<addon id="repository.t" name="T" version="1.0">
                 <extension point="xbmc.addon.repository"/>
               </addon>"""
        ).manifest!!
        assertEquals(Compatibility.COMPATIBLE,
            CompatibilityEvaluator.evaluate(repo, CompatibilityEvaluator.kindOf(repo)).level)

        val modulo = AddonManifestParser.parse(
            """<addon id="script.module.x" name="X" version="1.0">
                 <extension point="xbmc.python.module" library="lib"/>
               </addon>"""
        ).manifest!!
        assertEquals(Compatibility.NOT_COMPATIBLE,
            CompatibilityEvaluator.evaluate(modulo, CompatibilityEvaluator.kindOf(modulo)).level)
    }
}
