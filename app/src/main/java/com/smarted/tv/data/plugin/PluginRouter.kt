package com.smarted.tv.data.plugin

import com.smarted.tv.data.addon.AddonInstaller
import com.smarted.tv.data.addon.Compatibility

/**
 * Roteador de `plugin://`.
 *
 * Fluxo real (sem simulação):
 *  1. parseia a URI ([PluginUri]);
 *  2. confirma que o add-on está **instalado**;
 *  3. procura um [PluginAdapter] registrado para aquele id;
 *  4. se não houver, devolve [Result.Unsupported] com motivo honesto
 *     ("requer adaptação: runtime Python + API xbmc*") — nunca uma listagem falsa.
 *
 * O roteador é o único lugar que decide para onde um `plugin://` vai.
 */
class PluginRouter(
    private val installed: () -> List<AddonInstaller.Installed>,
    adapters: List<PluginAdapter> = emptyList(),
) {
    private val adapters = adapters.toList()
    private val extraAdapters = mutableListOf<PluginAdapter>()

    sealed class Result {
        data class Listing(val listing: PluginListing) : Result()
        data class Media(val media: PluginTarget.Media) : Result()
        data class Unsupported(val reason: String, val detail: List<String> = emptyList()) : Result()
        data class Invalid(val raw: String) : Result()
    }

    /** Registra um adaptador em tempo de execução (ex.: novas integrações). */
    fun register(adapter: PluginAdapter) {
        extraAdapters += adapter
    }

    fun adapterFor(addonId: String): PluginAdapter? =
        (extraAdapters + adapters).firstOrNull { it.supports(addonId) }

    /** Navega: devolve listagem, mídia direta ou motivo de indisponibilidade. */
    suspend fun route(rawUri: String): Result {
        val uri = PluginUri.parse(rawUri) ?: return Result.Invalid(rawUri)

        val addon = installed().firstOrNull { it.id == uri.addonId }
            ?: return Result.Unsupported(
                reason = "Add-on ${uri.addonId} não está instalado",
                detail = listOf("Instale o pacote do add-on em Add-ons › Instalar de ZIP antes de abrir um plugin://"),
            )

        val adapter = adapterFor(uri.addonId)
        if (adapter == null) {
            return Result.Unsupported(
                reason = "Add-on ${addon.name} requer adaptação",
                detail = buildList {
                    add("Ponto de extensão: ${addon.extensionPoint.ifBlank { "—" }}")
                    if (addon.compatibility == Compatibility.COMPATIBLE_WITH_ADAPTATION) {
                        add("Este add-on é Python e depende da API xbmc* (xbmcplugin/xbmcgui).")
                        add("Sem um adaptador registrado no app, a navegação não pode ser montada.")
                    } else {
                        add("Compatibilidade declarada: ${addon.compatibility.name}")
                    }
                    addon.missingDependencies.takeIf { it.isNotEmpty() }?.let {
                        add("Dependências ausentes: ${it.joinToString(", ")}")
                    }
                },
            )
        }

        val listing = adapter.browse(uri)
        if (listing.error != null) {
            return Result.Unsupported(
                reason = "Falha ao ler ${uri.addonId}",
                detail = listOf(listing.error) + listing.warnings,
            )
        }
        return Result.Listing(listing)
    }

    /** Resolve um item até uma mídia tocável. */
    suspend fun resolve(item: PluginItem): PluginTarget {
        item.target?.let { return it }
        val adapter = adapterFor(item.params["addonId"].orEmpty()) ?: return PluginTarget.Unsupported(
            "Item sem destino e sem adaptador para resolver"
        )
        return adapter.resolve(item)
    }
}
