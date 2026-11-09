package com.smarted.tv.ui.xmlengine

import android.util.Xml
import androidx.compose.ui.graphics.Color
import org.xmlpull.v1.XmlPullParser
import java.io.InputStream

/**
 * Lê o XML de layout (assets/layout (arquivos .xml)) e devolve um SmartLayout.
 * Parser tolerante: tags desconhecidas são ignoradas (não quebram o app).
 */
object LayoutParser {

    class LayoutException(message: String) : Exception(message)

    fun parse(input: InputStream): SmartLayout {
        val parser = Xml.newPullParser()
        parser.setFeature(XmlPullParser.FEATURE_PROCESS_NAMESPACES, false)
        parser.setInput(input, null)
        parser.nextTag()

        if (parser.name != "smarted") {
            throw LayoutException("O XML precisa começar com <smarted>. Encontrado: <${parser.name}>")
        }

        var theme = LayoutTheme()
        val screens = mutableListOf<ScreenLayout>()

        while (parser.next() != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType != XmlPullParser.START_TAG) continue
            when (parser.name) {
                "theme" -> theme = parseTheme(parser)
                "screen" -> screens += parseScreen(parser, theme)
            }
        }

        return SmartLayout(theme = theme, screen = screens.firstOrNull(), screens = screens)
    }

    // ── <theme bg="#0E0E10" accent="#EF5350" titleSize="30" .../> ──
    private fun parseTheme(parser: XmlPullParser): LayoutTheme {
        val a = parser.attributeMap()
        parser.skipToEndTag("theme")
        return LayoutTheme(
            background = colorOf(a["bg"]) ?: Color(0xFF0E0E10),
            surface = colorOf(a["surface"]) ?: Color(0xFF1A1A1D),
            accent = colorOf(a["accent"]) ?: Color(0xFFEF5350),
            accent2 = colorOf(a["accent2"]) ?: Color(0xFFFF8A00),
            textPrimary = colorOf(a["text"]) ?: Color(0xFFF2F2F2),
            textSecondary = colorOf(a["text2"]) ?: Color(0xFFA8A8AD),
            titleSizeSp = a["titleSize"]?.toFloatOrNull() ?: 30f,
            textSizeSp = a["textSize"]?.toFloatOrNull() ?: 15f,
            compact = a["compact"]?.toBoolean() ?: false,
        )
    }

    // ── <screen id="home" title="Início" subtitle="..."> ──
    private fun parseScreen(parser: XmlPullParser, theme: LayoutTheme): ScreenLayout {
        val a = parser.attributeMap()
        val id = a["id"] ?: throw LayoutException("<screen> sem atributo id")
        val title = a["title"] ?: ""
        val subtitle = a["subtitle"] ?: ""
        val showHeader = a["header"]?.toBoolean() ?: true
        val showSidebar = a["sidebar"]?.toBoolean() ?: true

        var sidebarItems = emptyList<NavNode>()
        var root: LayoutNode? = null

        val depth = parser.depth
        while (parser.next() != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType == XmlPullParser.END_TAG && parser.depth == depth) break
            if (parser.eventType != XmlPullParser.START_TAG) continue
            when (parser.name) {
                "sidebar" -> sidebarItems = parseSidebar(parser)
                else -> {
                    val node = parseNode(parser, depth + 1)
                    if (root == null) root = node
                    else root = root?.copy(children = (root?.children ?: emptyList()) + node)
                }
            }
        }

        return ScreenLayout(
            id = id,
            title = title,
            subtitle = subtitle,
            showHeader = showHeader,
            showSidebar = showSidebar,
            sidebarItems = sidebarItems,
            root = root,
        )
    }

    private fun parseSidebar(parser: XmlPullParser): List<NavNode> {
        val items = mutableListOf<NavNode>()
        var index = 0
        val depth = parser.depth
        while (parser.next() != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType == XmlPullParser.END_TAG && parser.depth == depth) break
            if (parser.eventType == XmlPullParser.START_TAG && parser.name == "item") {
                val a = parser.attributeMap()
                items += NavNode(
                    label = a["label"] ?: a["text"] ?: "Item",
                    action = a["action"] ?: "noop",
                    icon = a["icon"],
                    index = index++,
                )
                parser.skipToEndTag("item")
            }
        }
        return items
    }

    /** Converte uma tag qualquer em LayoutNode (recursivo). */
    private fun parseNode(parser: XmlPullParser, expectedDepth: Int): LayoutNode {
        val type = parser.name
        val props = parser.attributeMap()
        val children = mutableListOf<LayoutNode>()

        when (type) {
            // tags sem filhos / com texto simples
            "text", "image", "button", "spacer", "banner", "divider" -> {
                val inner = parser.readInnerText()
                parser.skipToEndTag(type)
                val text = props["text"] ?: inner
                return LayoutNode(type, if (!text.isNullOrBlank()) props + ("text" to text) else props)
            }
        }

        val depth = parser.depth
        while (parser.next() != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType == XmlPullParser.END_TAG && parser.depth == depth) break
            if (parser.eventType != XmlPullParser.START_TAG) continue
            children += parseNode(parser, depth + 1)
        }
        return LayoutNode(type, props, children)
    }

    // ── utilitários ──────────────────────────────────────────────
    /** Lê o texto entre <tag> e </tag> (se houver). */
    private fun XmlPullParser.readInnerText(): String? {
        val sb = StringBuilder()
        var event = next()
        while (event == XmlPullParser.TEXT || event == XmlPullParser.ENTITY_REF) {
            sb.append(text ?: "")
            event = next()
        }
        return sb.toString().trim().ifBlank { null }
    }

    private fun XmlPullParser.attributeMap(): Map<String, String> {
        val map = mutableMapOf<String, String>()
        for (i in 0 until attributeCount) {
            map[getAttributeName(i)] = getAttributeValue(i)
        }
        return map
    }

    private fun XmlPullParser.readText(): String? =
        if (next() == XmlPullParser.TEXT) text?.trim() else null

    /** Consome a tag atual até seu END_TAG, sem descer para os filhos. */
    private fun XmlPullParser.skipToEndTag(tag: String) {
        val startDepth = depth
        while (true) {
            val event = next()
            if (event == XmlPullParser.END_DOCUMENT) return
            if (event == XmlPullParser.END_TAG && depth == startDepth && name == tag) return
        }
    }

    fun colorOf(value: String?): Color? {
        if (value.isNullOrBlank()) return null
        val v = value.trim()
        if (v.startsWith("#")) {
            val hex = v.removePrefix("#")
            val argb = when (hex.length) {
                6 -> 0xFF000000L or hex.toLong(16)
                8 -> hex.toLong(16)
                3 -> {
                    val r = hex[0].toString().repeat(2)
                    val g = hex[1].toString().repeat(2)
                    val b = hex[2].toString().repeat(2)
                    0xFF000000L or ("$r$g$b".toLong(16))
                }
                else -> return null
            }
            return Color(argb)
        }
        return when (v.lowercase()) {
            "black" -> Color.Black
            "white" -> Color.White
            "red" -> Color.Red
            "transparent" -> Color.Transparent
            else -> null
        }
    }
}
