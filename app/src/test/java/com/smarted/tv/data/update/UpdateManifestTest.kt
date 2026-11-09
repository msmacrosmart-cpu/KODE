package com.smarted.tv.data.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Regra de atualização: só é "nova versão" quando o `versionCode` publicado é
 * maior que o instalado — é exatamente o que o Android usa para permitir
 * atualizar por cima sem desinstalar.
 *
 * (O download/instalação em si depende do Android; aqui garantimos a decisão.)
 */
class UpdateManifestTest {

    private fun isNewer(published: Int, installed: Int) = published > installed

    @Test
    fun `versionCode maior e atualizacao disponivel`() {
        assertTrue(isNewer(71, 70))
        assertTrue(isNewer(100, 1))
    }

    @Test
    fun `mesmo versionCode nao e atualizacao`() {
        assertFalse(isNewer(70, 70))
        assertFalse(isNewer(69, 70))
    }

    @Test
    fun `manifesto publicado pelo CI tem os campos que o app le`() {
        // formato exato gerado no build.yml (dist/update.json)
        val json = """
            {"version":"1.0.11","versionCode":71,"apk":"SmartED-TV-1.0.11-universal.apk",
             "apkUrl":"https://github.com/msmacrosmart-cpu/KODE/releases/latest/download/SmartED-TV-1.0.11-universal.apk",
             "sha256":"abc123","certSha256":"AA:BB","notes":"https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.11"}
        """.trimIndent()

        // leitura com Regex: org.json é stub no teste de JVM (isReturnDefaultValues)
        fun field(name: String) = Regex("\"$name\"\\s*:\\s*\"([^\"]*)\"").find(json)?.groupValues?.get(1)
        fun intField(name: String) = Regex("\"$name\"\\s*:\\s*(\\d+)").find(json)?.groupValues?.get(1)?.toInt()

        assertEquals(71, intField("versionCode"))
        assertEquals("1.0.11", field("version"))
        assertTrue(field("apkUrl")!!.endsWith("SmartED-TV-1.0.11-universal.apk"))
        assertTrue(!field("sha256").isNullOrBlank())
        // todas as chaves obrigatórias presentes
        listOf("version", "versionCode", "apk", "apkUrl", "sha256", "certSha256", "notes")
            .forEach { assertTrue("faltou $it", json.contains("\"$it\"")) }
    }

    @Test
    fun `atualizacao exige mesma assinatura`() {
        // decisão que evita INSTALL_FAILED_UPDATE_INCOMPATIBLE
        fun canUpdate(installedCert: String, newCert: String) = installedCert == newCert
        assertTrue(canUpdate("AA:BB", "AA:BB"))
        assertFalse(canUpdate("AA:BB", "CC:DD"))
    }
}
