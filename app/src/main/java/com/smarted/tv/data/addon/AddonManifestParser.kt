package com.smarted.tv.data.addon

import org.w3c.dom.Element
import org.w3c.dom.Node
import javax.xml.parsers.DocumentBuilderFactory
import java.io.ByteArrayInputStream

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
 * Implementado com DOM (JAXP) porque é estável tanto no Android quanto nos
 * testes de JVM — diferente de XmlPullParser, cuja fábrica é um stub no unit test.
 * Entidades externas/DTD são desligadas (XXE) e o tamanho é limitado.
 *
 * Tolerante: XML malformado devolve null com mensagem, nunca exceção para o app.
 */
object AddonManifestParser {

    data class Result(val manifest: AddonManifest?, val error: String? = null)

    /** addon.xml é XML de metadados; acima disso é abuso/corrupção. */
    private const val MAX_BYTES = 2 * 1024 * 1024

    fun parse(xml: String): Result {
        if (xml.isBlank()) return Result(null, "addon.xml vazio")
        val bytes = xml.removePrefix("\uFEFF").toByteArray(Charsets.UTF_8)
        if (bytes.size > MAX_BYTES) return Result(null, "addon.xml grande demais (${bytes.size} bytes)")

        return try {
            val factory = DocumentBuilderFactory.newInstance().apply {
                isNamespaceAware = false
                isValidating = false
                isExpandEntityReferences = false
                // XXE / expansão de entidades
                runCatching { setFeature("http://apache.org/xml/features/disallow-doctype-decl", true) }
                runCatching { setFeature("http://xml.org/sax/features/external-general-entities", false) }
                runCatching { setFeature("http://xml.org/sax/features/external-parameter-entities", false) }
                runCatching { setFeature("http://javax.xml.XMLConstants/feature/secure-processing", true) }
                // Strings literais: XMLConstants do Android não expõe ACCESS_EXTERNAL_*
                runCatching { setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "") }
                runCatching { setAttribute("http://javax.xml.XMLConstants/property/accessExternalSchema", "") }
            }
            val doc = factory.newDocumentBuilder()
                .parse(ByteArrayInputStream(bytes))
            val root = doc.documentElement ?: return Result(null, "addon.xml sem elemento raiz")
            return fromElement(root)
        } catch (e: Exception) {
            Result(null, "addon.xml inválido: ${e.message ?: e::class.java.simpleName}")
        }
    }

    /**
     * Lê um elemento `<addon>` já parseado (usado também por `addons.xml`,
     * que contém vários `<addon>`).
     */
    internal fun fromElement(root: Element): Result {
        return try {
            if (root.tagName.lowercase() != "addon") {
                return Result(null, "raiz <${root.tagName}> não é <addon>")
            }

            val id = root.getAttribute("id").takeIf { it.isNotBlank() }
                ?: return Result(null, "<addon id=\"...\"> ausente")
            val name = root.getAttribute("name").takeIf { it.isNotBlank() }
            val version = root.getAttribute("version").takeIf { it.isNotBlank() }
            val provider = root.getAttribute("provider-name").takeIf { it.isNotBlank() }

            val libraries = mutableListOf<String>()
            val warnings = mutableListOf<String>()
            val metadata = mutableMapOf<String, String>()
            var requiresKodi: String? = null
            var extensionPoint: String? = null
            var provides: String? = null
            var entryPoint: String? = null

            // <requires><import .../></requires>
            for (imp in root.descendants("import")) {
                val dep = imp.getAttribute("addon").takeIf { it.isNotBlank() } ?: continue
                val depVersion = imp.getAttribute("version").takeIf { it.isNotBlank() }
                if (dep == "xbmc.addon" || dep == "xbmc.python" || dep == "xbmc.gui") {
                    if (dep == "xbmc.addon" && depVersion != null) requiresKodi = depVersion
                    metadata["dep.$dep"] = depVersion ?: ""
                } else {
                    libraries += if (depVersion != null) "$dep>=$depVersion" else dep
                }
            }

            // Todos os <extension point="...">
            val extensions = root.children("extension")
            for (ext in extensions) {
                val point = ext.getAttribute("point").takeIf { it.isNotBlank() } ?: continue
                metadata["extension.$point"] = ext.getAttribute("provides")
                if (extensionPoint == null) extensionPoint = point
                val providesAttr = ext.getAttribute("provides").takeIf { it.isNotBlank() }
                if (providesAttr != null && provides == null) provides = providesAttr
                val libraryAttr = ext.getAttribute("library").takeIf { it.isNotBlank() }
                if (libraryAttr != null && entryPoint == null) entryPoint = libraryAttr
                // <provides>video</provides> dentro da extensão de plugin
                val providesTag = ext.children("provides").firstOrNull()?.textContent?.trim()
                if (!providesTag.isNullOrBlank() && provides == null) provides = providesTag
            }
            if (extensionPoint == null) warnings += "Nenhum <extension point=...> encontrado"

            val description = localizedText(root, "description")
            val summary = localizedText(root, "summary")
            val disclaimer = localizedText(root, "disclaimer")
            val news = localizedText(root, "news")

            val manifest = AddonManifest(
                id = id,
                name = name ?: id,
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

    /**
     * Texto de `addon.example`/`<description>`, preferindo pt/pt_BR e caindo
     * para o primeiro disponível. Nunca inventa conteúdo.
     */
    private fun localizedText(root: Element, tag: String): String? {
        val all = root.descendants(tag).mapNotNull { el ->
            val text = el.textContent?.trim()?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
            (el.getAttribute("lang").takeIf { it.isNotBlank() } ?: "") to text
        }
        if (all.isEmpty()) return null
        return all.firstOrNull { it.first.startsWith("pt", ignoreCase = true) }?.second
            ?: all.first().second
    }

    private fun Element.descendants(tag: String): List<Element> {
        val out = mutableListOf<Element>()
        val nodes = getElementsByTagName(tag)
        for (i in 0 until nodes.length) (nodes.item(i) as? Element)?.let { out += it }
        return out
    }

    private fun Element.children(tag: String): List<Element> {
        val out = mutableListOf<Element>()
        var n: Node? = firstChild
        while (n != null) {
            if (n is Element && n.tagName.equals(tag, ignoreCase = true)) out += n
            n = n.nextSibling
        }
        return out
    }
}
