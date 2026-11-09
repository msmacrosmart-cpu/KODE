package com.smarted.tv.data.archive

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Fixtures são gerados em tempo de teste (ZIP real criado no setUp).
 * Nenhum dado fictício é embarcado no app.
 */
class ZipInspectorTest {

    @get:Rule
    val tmp = TemporaryFolder()

    private fun zip(vararg entries: Pair<String, String>): File {
        val file = tmp.newFile("pacote-${System.nanoTime()}.zip")
        ZipOutputStream(file.outputStream()).use { out ->
            entries.forEach { (name, content) ->
                out.putNextEntry(ZipEntry(name))
                if (!name.endsWith("/")) out.write(content.toByteArray())
                out.closeEntry()
            }
        }
        return file
    }

    // ── Repositório Kodi ───────────────────────────────────────────────
    @Test
    fun `repositorio kodi e reconhecido por addons xml`() {
        val f = zip(
            "addons.xml" to "<?xml version=\"1.0\"?><addons><addon id=\"plugin.video.x\"/></addons>",
            "addons.xml.md5" to "abc123",
            "plugin.video.x/plugin.video.x-1.0.0.zip" to "PK",
        )
        val r = ZipInspector.inspect(f)
        assertTrue(r.isRepository)
        // `addons.xml` e o checksum `addons.xml.md5` são ambos parte do manifesto do repositório
        assertEquals(listOf("addons.xml", "addons.xml.md5"), r.repoManifestPaths)
        assertFalse(r.hasAddonManifest)
        assertEquals(3, r.totalFiles)
        assertTrue(r.warnings.isEmpty())
    }

    // ── Add-on avulso ─────────────────────────────────────────────────
    @Test
    fun `addon zip encontra addon xml icon e fanart na subpasta`() {
        val f = zip(
            "plugin.video.oneplay/addon.xml" to "<addon id=\"plugin.video.oneplay\"/>",
            "plugin.video.oneplay/icon.png" to "PNG",
            "plugin.video.oneplay/fanart.jpg" to "JPG",
            "plugin.video.oneplay/resources/lib/main.py" to "print(1)",
        )
        val r = ZipInspector.inspect(f)
        assertEquals(listOf("plugin.video.oneplay/addon.xml"), r.addonXmlPaths)
        assertEquals("plugin.video.oneplay/", r.rootPrefix)
        assertEquals("plugin.video.oneplay/icon.png", r.iconPath)
        assertEquals("plugin.video.oneplay/fanart.jpg", r.fanartPath)
        assertTrue(r.hasAddonManifest)
        assertFalse(r.isRepository)
    }

    // ── Segurança: Zip Slip ───────────────────────────────────────────
    @Test
    fun `zip slip e rejeitado e nao escapa do destino`() {
        val f = zip(
            "../../fora.txt" to "x",
            "/etc/passwd" to "x",
            "C:/windows/system32/x.dll" to "x",
            "ok/arquivo.txt" to "conteudo",
        )
        val r = ZipInspector.inspect(f)
        assertTrue(r.unsafeEntries.any { it.name == "../../fora.txt" })
        assertTrue(r.unsafeEntries.any { it.name == "/etc/passwd" })
        assertTrue(r.unsafeEntries.any { it.name.startsWith("C:") })

        val dest = tmp.newFolder("destino")
        val res = ZipInspector.extractSafely(f, dest)
        assertEquals(listOf("ok/arquivo.txt"), res.extracted)
        assertEquals(3, res.skipped.size)
        assertFalse(File(dest.parentFile, "fora.txt").exists())
        assertTrue(File(dest, "ok/arquivo.txt").exists())
    }

    // ── Zip bomb / limites ────────────────────────────────────────────
    @Test
    fun `zip bomb e interrompido pelo limite de entradas`() {
        val file = tmp.newFile("bomb.zip")
        ZipOutputStream(file.outputStream()).use { out ->
            repeat(30) { i ->
                out.putNextEntry(ZipEntry("f$i.txt"))
                out.write(ByteArray(8 * 1024)) // mesmo comprimindo, gera entradas
                out.closeEntry()
            }
        }
        val r = ZipInspector.inspect(file, ZipInspector.Limits(maxEntries = 10))
        assertTrue(r.entries.size <= 10)
        assertTrue(r.warnings.any { it.contains("Limite") })
    }

    @Test
    fun `profundidade excessiva e sinalizada`() {
        val deep = (1..20).joinToString("/") { "n$it" } + "/f.txt"
        val r = ZipInspector.inspect(zip(deep to "x"))
        assertTrue(r.unsafeEntries.isNotEmpty())
    }

    // ── Leitura e extração ────────────────────────────────────────────
    @Test
    fun `readEntry devolve conteudo real e bloqueia caminho inseguro`() {
        val f = zip("addon.xml" to "<addon id=\"x\"/>", "../evil.txt" to "x")
        assertEquals("<addon id=\"x\"/>", ZipInspector.readEntry(f, "addon.xml")?.toString(Charsets.UTF_8))
        assertNull(ZipInspector.readEntry(f, "../evil.txt"))
        assertNull(ZipInspector.readEntry(f, "inexistente.xml"))
    }

    @Test
    fun `zip corrompido devolve warning em vez de excecao`() {
        val f = tmp.newFile("ruim.zip")
        f.writeBytes(byteArrayOf(0x50, 0x4B, 0x03, 0x04, 0x00, 0x01, 0x02))
        val r = ZipInspector.inspect(f)
        assertNotNull(r)
        assertTrue(r.warnings.isNotEmpty())
    }

    @Test
    fun `extract preserva a estrutura original`() {
        val f = zip(
            "plugin.video.x/addon.xml" to "<addon/>",
            "plugin.video.x/resources/settings.xml" to "<settings/>",
            "plugin.video.x/resources/language/pt_br/strings.po" to "msgctxt \"#0\"",
        )
        val dest = tmp.newFolder("extraido")
        val res = ZipInspector.extractSafely(f, dest)
        assertEquals(3, res.extracted.size)
        assertTrue(File(dest, "plugin.video.x/addon.xml").exists())
        assertTrue(File(dest, "plugin.video.x/resources/language/pt_br/strings.po").exists())
    }
}
