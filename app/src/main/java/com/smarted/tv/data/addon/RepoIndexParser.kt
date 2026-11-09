package com.smarted.tv.data.addon

import org.w3c.dom.Element
import javax.xml.parsers.DocumentBuilderFactory
import java.io.ByteArrayInputStream

/**
 * Parser de `addons.xml` — o catálogo de um repositório do Kodi.
 *
 * Estrutura real:
 * ```xml
 * <addons>
 *   <addon id="plugin.video.x" name="X" version="1.0.0" provider-name="...">
 *     <requires><import addon="xbmc.python" version="3.0.0"/></requires>
 *     <extension point="xbmc.python.pluginsource" library="default.py"><provides>video</provides></extension>
 *   </addon>
 *   ...
 * </addons>
 * ```
 *
 * Cada `<addon>` é lido pelo mesmo código do `addon.xml` ([AddonManifestParser.fromElement]),
 * então não existe um "formato de repositório" inventado: é o formato do Kodi.
 *
 * Tolerante e limitado: XML grande/inválido devolve erro, nunca exceção.
 */
object RepoIndexParser {

    data class Result(val manifests: List<AddonManifest>, val error: String? = null) {
        val isEmpty: Boolean get() = manifests.isEmpty()
    }

    /** addons.xml de repositórios reais raramente passa de 1 MB. */
    private const val MAX_BYTES = 8 * 1024 * 1024

    fun parse(xml: String): Result {
        if (xml.isBlank()) return Result(emptyList(), "addons.xml vazio")
        val bytes = xml.removePrefix("\uFEFF").toByteArray(Charsets.UTF_8)
        if (bytes.size > MAX_BYTES) return Result(emptyList(), "addons.xml grande demais (${bytes.size} bytes)")

        return try {
            val factory = DocumentBuilderFactory.newInstance().apply {
                isNamespaceAware = false
                isValidating = false
                isExpandEntityReferences = false
                runCatching { setFeature("http://apache.org/xml/features/disallow-doctype-decl", true) }
                runCatching { setFeature("http://xml.org/sax/features/external-general-entities", false) }
                runCatching { setFeature("http://xml.org/sax/features/external-parameter-entities", false) }
                runCatching { setFeature("http://javax.xml.XMLConstants/feature/secure-processing", true) }
            }
            val doc = factory.newDocumentBuilder().parse(ByteArrayInputStream(bytes))
            val root = doc.documentElement ?: return Result(emptyList(), "addons.xml sem elemento raiz")

            // Um addons.xml válido tem raiz <addons>; também aceitamos um único
            // <addon> (alguns repositórios publicam um arquivo por add-on).
            val addonElements: List<Element> = when (root.tagName.lowercase()) {
                "addons" -> {
                    val nodes = root.getElementsByTagName("addon")
                    (0 until nodes.length).mapNotNull { nodes.item(it) as? Element }
                }
                "addon" -> listOf(root)
                else -> return Result(emptyList(), "raiz <${root.tagName}> não é <addons>")
            }

            if (addonElements.isEmpty()) return Result(emptyList(), "addons.xml sem <addon>")

            val manifests = mutableListOf<AddonManifest>()
            val erros = mutableListOf<String>()
            addonElements.forEach { el ->
                val r = AddonManifestParser.fromElement(el)
                val m = r.manifest
                if (m != null) manifests += m else erros += (r.error ?: "add-on ilegível")
            }

            val error = when {
                manifests.isEmpty() -> "Nenhum add-on pôde ser lido: ${erros.take(3).joinToString("; ")}"
                erros.isNotEmpty() -> "${erros.size} entrada(s) ignorada(s): ${erros.take(3).joinToString("; ")}"
                else -> null
            }
            Result(manifests, error)
        } catch (e: Exception) {
            Result(emptyList(), "addons.xml inválido: ${e.message ?: e::class.java.simpleName}")
        }
    }
}
