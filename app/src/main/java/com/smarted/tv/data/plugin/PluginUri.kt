package com.smarted.tv.data.plugin

import java.net.URLDecoder
import java.net.URLEncoder

/**
 * `plugin://` NÃO é uma URL HTTP.
 *
 * Formato real do Kodi:
 * ```
 * plugin://plugin.video.exemplo/acao/sub/1/?mode=lista&id=42&titulo=Filme%20X
 *  └── addon id ──┘└─ caminho ─┘ └──── parâmetros ────┘
 * ```
 *
 * - `/<segmentos>`        → caminho virtual dentro do add-on
 * - `?a=1&b=2`           → parâmetros (decodificados, ordem preservada)
 *
 * Nada aqui faz resposta de rede: é só o endereço virtual. Quem resolve é um
 * [PluginAdapter].
 */
data class PluginUri(
    val addonId: String,
    val path: List<String>,
    val params: Map<String, String>,
    val raw: String,
) {
    /** Caminho textual (`acao/sub/1`). */
    val pathText: String get() = path.joinToString("/")

    /** Parâmetro com fallback. */
    fun param(key: String): String? = params[key]

    /** Reconstitui a URI (usado ao passar adiante para o mesmo add-on). */
    fun rebuild(extra: Map<String, String> = emptyMap()): String {
        val query = (params + extra).entries.joinToString("&") { (k, v) ->
            "$k=${URLEncoder.encode(v, "UTF-8")}"
        }
        val base = "plugin://$addonId/" + path.joinToString("/") { URLEncoder.encode(it, "UTF-8") }
        return if (query.isEmpty()) base else "$base?$query"
    }

    companion object {
        private val SCHEME = "plugin://"

        /** @return null quando não é `plugin://` (nunca "adivinha" plugin) */
        fun parse(uri: String?): PluginUri? {
            if (uri == null) return null
            val trimmed = uri.trim()
            if (!trimmed.startsWith(SCHEME, ignoreCase = true)) return null
            val afterScheme = trimmed.substring(SCHEME.length)
            if (afterScheme.isBlank()) return null

            val beforeQuery = afterScheme.substringBefore('?')
            val query = afterScheme.substringAfter('?', "")

            val addonId = beforeQuery.substringBefore('/').trim()
            if (addonId.isBlank()) return null

            val pathPart = beforeQuery.substringAfter('/', "")
                .trim('/')
                .takeIf { it.isNotEmpty() }
                ?.split('/')
                ?.map { decode(it) }
                ?.filter { it.isNotEmpty() }
                ?: emptyList()

            // O plugin pode receber `params`/`path` já codificados pelo Kodi.
            val params = mutableMapOf<String, String>()
            if (query.isNotEmpty()) {
                query.split('&').forEach { pair ->
                    if (pair.isBlank()) return@forEach
                    val key = decode(pair.substringBefore('='))
                    val value = decode(pair.substringAfter('=', ""))
                    if (key.isNotBlank()) params[key] = value
                }
            }

            return PluginUri(addonId = addonId, path = pathPart, params = params, raw = trimmed)
        }

        /** Extrai `plugin://...` de uma URI que veio com query codificada. */
        fun decodeIfEncoded(uri: String): String {
            val decoded = decode(uri)
            return if (decoded.startsWith(SCHEME, true)) decoded else uri
        }

        private fun decode(value: String): String =
            runCatching { URLDecoder.decode(value, "UTF-8") }.getOrDefault(value)
    }
}
