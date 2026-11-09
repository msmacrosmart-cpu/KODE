package com.smarted.tv.data.addon

import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import java.io.StringReader

/**
 * Parser de `addon.xml` (formato real do Kodi).
 *
 * Descoberta dinâmica, sem presumir estrutura fixa:
 *  - lê atributos de <addon>
 *  - varre TODOS os <extension point="..."> (um add-on pode ter vários)
 *  - coleta <import addon="..."/> (dependências/libraries)
 *  - coleta <provides>, <news>, <summary> e o texto multilíngue de <description lang="...">
 *  - exige/importa `version="..."` de `xbmc.addon` como versão mínima do Kodi
 *
 * Tolerante: XML malformado devolve null com mensagem, nunca exceção para o app.
 */
object AddonManifestParser {

    data class Result(val manifest: AddonManifest?, val error: String? = null)

    fun parse(xml: String): Result {
        if (xml.isBlank()) return Result(null, "addon.xml vazio")

        return try {
            val factory = XmlPullParserFactory.newInstance()
            factory.isNamespaceAware = false
            val parser = factory.newPullParser()
            parser.setInput(StringReader(xml.removePrefix("\uFEFF")))

            var id: String? = null
            var name: String? = null
            var version: String? = null
            var provider: String? = null
            var summary: String? = null
            var description: String? = null
            var disclaimer: String? = null
            var news: String? = null
            var extensionPoint: String? = null
            var provides: String? = null
            var entryPoint: String? = null
            var requiresKodi: String? = null
            val libraries = mutableListOf<String>()
            val warnings = mutableListOf<String>()
            val metadata = mutableMapOf<String, String>()

            var event = parser.eventType
            while (event != XmlPullParser.END_DOCUMENT) {
                if (event == XmlPullParser.START_TAG) {
                    when (parser.name) {
                        "addon" -> {
                            id = parser.getAttributeValue(null, "id")
                            name = parser.getAttributeValue(null, "name")
                            version = parser.getAttributeValue(null, "version")
                            provider = parser.getAttributeValue(null, "provider-name")
                        }
                        "extension" -> {
                            val point = parser.getAttributeValue(null, "point")
                            if (point != null) {
                                // guarda o primeiro ponto de extensão (o principal)
                                if (extensionPoint == null) extensionPoint = point
                                val providesAttr = parser.getAttributeValue(null, "provides")
                                if (providesAttr != null) provides = providesAttr
                                val libraryAttr = parser.getAttributeValue(null, "library")
                                if (libraryAttr != null) entryPoint = libraryAttr
                                metadata["extension.$point"] = providesAttr ?: ""
                            }
                        }
                        "import" -> {
                            val dep = parser.getAttributeValue(null, "addon")
                            val depVersion = parser.getAttributeValue(null, "version")
                            if (dep != null) {
                                if (dep == "xbmc.addon" || dep == "xbmc.python" || dep == "xbmc.gui") {
                                    if (dep == "xbmc.addon" && depVersion != null) requiresKodi = depVersion
                                    metadata["dep.$dep"] = depVersion ?: ""
                                } else {
                                    libraries += if (depVersion != null) "$dep>=$depVersion" else dep
                                }
                            }
                        }
                        "provides" -> provides = parser.nextTextSafe() ?: provides
                        "summary" -> summary = parser.nextTextSafe()
                        "description" -> {
                            val lang = parser.getAttributeValue(null, "lang")
                            val text = parser.nextTextSafe()
                            if (text != null && (lang == null || lang.startsWith("pt") || description == null)) {
                                if (lang == null || lang.startsWith("pt")) description = text
                            }
                        }
                        "disclaimer" -> disclaimer = parser.nextTextSafe()
                        "news" -> news = parser.nextTextSafe()
                    }
                }
                event = parser.next()
            }

            if (id.isNullOrBlank()) return Result(null, "<addon id=\"...\"> ausente")
            if (extensionPoint.isNullOrBlank()) {
                warnings += "Nenhum <extension point=...> encontrado"
            }

            val manifest = AddonManifest(
                id = id!!,
                name = name ?: id!!,
                version = version ?: "0",
                providerName = provider,
                description = description,
                summary = summary,
                disclaimer = disclaimer,
                news = news,
                extensionPoint = extensionPoint ?: "",
                libraries = libraries,
                requiresKodi = requiresKodi,
                entryPoint = entryPoint,
                providedBy = provides,
                metadata = metadata,
                warnings = warnings,
            )
            Result(manifest)
        } catch (e: Exception) {
            Result(null, "addon.xml inválido: ${e.message ?: e::class.java.simpleName}")
        }
    }

    /** Texto do próximo nó de texto, sem quebrar em CDATA/vazio. */
    private fun XmlPullParser.nextTextSafe(): String? {
        val sb = StringBuilder()
        var depth = 1
        while (depth > 0) {
            when (next()) {
                XmlPullParser.START_TAG -> depth++
                XmlPullParser.END_TAG -> depth--
                XmlPullParser.TEXT, XmlPullParser.CDSECT -> sb.append(text ?: "")
                XmlPullParser.END_DOCUMENT -> return sb.toString().trim().ifBlank { null }
            }
        }
        return sb.toString().trim().ifBlank { null }
    }
}
