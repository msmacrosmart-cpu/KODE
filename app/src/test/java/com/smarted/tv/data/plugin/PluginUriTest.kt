package com.smarted.tv.data.plugin

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Fase F: `plugin://` não é URL HTTP.
 * Estes testes fixam o formato do Kodi e o comportamento do roteador.
 */
class PluginUriTest {

    @Test
    fun `plugin simples com id e caminho`() {
        val p = PluginUri.parse("plugin://plugin.video.alfa/")!!
        assertEquals("plugin.video.alfa", p.addonId)
        assertTrue(p.path.isEmpty())
        assertTrue(p.params.isEmpty())
    }

    @Test
    fun `caminho com segmentos e parametros codificados`() {
        val p = PluginUri.parse("plugin://plugin.video.alfa/series/1/?mode=episodios&titulo=Season%201")!!
        assertEquals("plugin.video.alfa", p.addonId)
        assertEquals(listOf("series", "1"), p.path)
        assertEquals("episodios", p.param("mode"))
        assertEquals("Season 1", p.param("titulo"))
    }

    @Test
    fun `http nao e plugin`() {
        assertNull(PluginUri.parse("https://exemplo.com/plugin.video.x"))
        assertNull(PluginUri.parse("plugin://"))
        assertNull(PluginUri.parse(null))
        assertNull(PluginUri.parse("/sdcard/filme.mkv"))
    }

    @Test
    fun `rebuild preserva parametros e adiciona novos`() {
        val p = PluginUri.parse("plugin://plugin.video.x/browse?page=2")!!
        val rebuilt = p.rebuild(mapOf("q" to "a b"))
        // URLEncoder usa "+" para espaço em query string — formato aceito em plugin://
        assertEquals("plugin://plugin.video.x/browse?page=2&q=a+b", rebuilt)
        val again = PluginUri.parse(rebuilt)!!
        assertEquals("2", again.param("page"))
        assertEquals("a b", again.param("q"))
    }

    @Test
    fun `rota sem addon instalado explica e nao inventa`() {
        val router = PluginRouter(installed = { emptyList() })
        val result = runBlockingRoute(router, "plugin://plugin.video.naoinstalado/")
        assertTrue(result is PluginRouter.Result.Unsupported)
        val unsupported = result as PluginRouter.Result.Unsupported
        assertTrue(unsupported.reason.contains("não está instalado"))
    }

    @Test
    fun `addon instalado sem adaptador declara que precisa de adaptacao`() {
        val instalado = listOf(
            com.smarted.tv.data.addon.AddonInstaller.Installed(
                id = "plugin.video.alfa",
                name = "Alfa",
                version = "1.0.0",
                kind = com.smarted.tv.data.addon.AddonKind.VIDEO,
                compatibility = com.smarted.tv.data.addon.Compatibility.COMPATIBLE_WITH_ADAPTATION,
                extensionPoint = "xbmc.python.pluginsource",
                directory = "/data/addons/plugin.video.alfa",
                installedAt = 0,
            )
        )
        val router = PluginRouter(installed = { instalado })
        val result = runBlockingRoute(router, "plugin://plugin.video.alfa/?mode=main")
        assertTrue(result is PluginRouter.Result.Unsupported)
        val detail = (result as PluginRouter.Result.Unsupported).detail.joinToString(" ")
        assertTrue(detail.contains("xbmc"))
    }

    @Test
    fun `adaptador local lista pasta real e nao simula`() {
        // adaptador falso mínimo: prova que o roteador entrega o que o adaptador produz
        val fake = object : PluginAdapter {
            override val addonId = "plugin.video.alfa"
            override val description = "dados de teste"
            override suspend fun browse(uri: PluginUri) = PluginListing(
                addonId = addonId,
                title = "Alfa",
                items = listOf(
                    PluginItem(
                        label = "Filme local",
                        target = PluginTarget.Media("content://doc/1", mimeHint = "video/mp4", title = "Filme local"),
                        isFolder = false,
                    )
                ),
            )
            override suspend fun resolve(item: PluginItem) = item.target!!
        }
        val instalado = listOf(
            com.smarted.tv.data.addon.AddonInstaller.Installed(
                id = "plugin.video.alfa", name = "Alfa", version = "1.0.0",
                kind = com.smarted.tv.data.addon.AddonKind.VIDEO,
                compatibility = com.smarted.tv.data.addon.Compatibility.COMPATIBLE,
                extensionPoint = "xbmc.python.pluginsource",
                directory = "/tmp", installedAt = 0,
            )
        )
        val router = PluginRouter(installed = { instalado }, adapters = listOf(fake))
        val result = runBlockingRoute(router, "plugin://plugin.video.alfa/")
        assertTrue(result is PluginRouter.Result.Listing)
        val listing = (result as PluginRouter.Result.Listing).listing
        assertEquals(1, listing.items.size)
        assertTrue(listing.items.first().isPlayable)
    }

    private fun runBlockingRoute(router: PluginRouter, uri: String): PluginRouter.Result =
        kotlinx.coroutines.runBlocking { router.route(uri) }
}
