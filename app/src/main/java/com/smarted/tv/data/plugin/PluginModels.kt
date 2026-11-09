package com.smarted.tv.data.plugin

/**
 * Item de uma listagem de plugin — o que a UI pode mostrar e o que pode fazer.
 *
 * Estes objetos são produzidos por um [PluginAdapter] a partir de dados REAIS
 * (caminhos locais, URLs declaradas pelo add-on). Nada é preenchido por padrão:
 * um item sem [target] não é reproduzível e a UI deve dizer isso.
 */
data class PluginItem(
    val label: String,
    val label2: String? = null,
    val iconUrl: String? = null,
    val thumbUrl: String? = null,
    val fanartUrl: String? = null,
    val target: PluginTarget?,
    val isFolder: Boolean = false,
    val params: Map<String, String> = emptyMap(),
    val metadata: Map<String, String> = emptyMap(),
) {
    val isPlayable: Boolean get() = !isFolder && target is PluginTarget.Media
}

/** Para onde o item leva quando o usuário confirma. */
sealed class PluginTarget {
    /** Nova navegação dentro do mesmo add-on (`plugin://...`). */
    data class Virtual(val uri: PluginUri) : PluginTarget()

    /** Mídia reproduzível: URL HTTP(S), arquivo local ou URI do SAF. */
    data class Media(
        val uri: String,
        val mimeHint: String? = null,
        val headers: Map<String, String> = emptyMap(),
        val isLive: Boolean = false,
        val title: String = "",
        val subtitles: List<String> = emptyList(),
    ) : PluginTarget() {
        val isLocal: Boolean
            get() = uri.startsWith("content://") || uri.startsWith("file://") || uri.startsWith("/")
    }

    /** O adaptador não sabe resolver: mostrar o motivo, nunca simular. */
    data class Unsupported(val reason: String, val rawTarget: String? = null) : PluginTarget()
}

/** Resultado de uma tentativa de adaptação. */
data class PluginListing(
    val addonId: String,
    val title: String,
    val items: List<PluginItem> = emptyList(),
    val warnings: List<String> = emptyList(),
    val error: String? = null,
) {
    val isEmpty: Boolean get() = items.isEmpty()
}

/**
 * Contrato de adaptação de um add-on do Kodi.
 *
 * Implementações reais vivem em `data/plugin/adapters` e trabalham com dados
 * verificáveis (arquivos locais, catálogos declarados, listas geradas por
 * fontes abertas). Um add-on Python genérico NÃO tem adaptador: nesse caso a
 * UI declara "requer adaptação" — jamais inventa uma listagem.
 */
interface PluginAdapter {
    /** id do add-on que este adaptador atende (`plugin.video.*`, etc). */
    val addonId: String

    /** Uma linha explicando de onde vêm os dados. */
    val description: String

    /** Lista o conteúdo de uma URI do add-on. */
    suspend fun browse(uri: PluginUri): PluginListing

    /** Resolve o alvo de um item (quando pode ser reproduzido). */
    suspend fun resolve(item: PluginItem): PluginTarget

    /** O adaptador consegue atender este add-on? */
    fun supports(addonId: String): Boolean = this.addonId.equals(addonId, ignoreCase = true)
}
