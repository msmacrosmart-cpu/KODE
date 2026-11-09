package com.smarted.tv.ui.xmlengine

import androidx.compose.ui.graphics.Color

/**
 * Modelo do layout em XML (formato SmartED, inspirado no "skin" do Kodi).
 *
 * O app lê o arquivo de `app/src/main/assets/layout/*.xml` em tempo de execução.
 * Trocar o XML = trocar o layout, sem recompilar o Kotlin.
 *
 * Equivalências com o Kodi:
 *   Kodi <window>            -> <screen>
 *   Kodi <control type=list> -> <sidebar>/<list>/<grid>
 *   Kodi <include>/<defaults>-> <theme>
 *   Kodi <onclick>Activate   -> action="screen:canais"
 */
data class SmartLayout(
    val theme: LayoutTheme = LayoutTheme(),
    val screen: ScreenLayout? = null,
    val screens: List<ScreenLayout> = emptyList(),
) {
    fun screen(key: String): ScreenLayout? = screens.firstOrNull { it.id == key } ?: screen
}

data class LayoutTheme(
    val background: Color = Color(0xFF0E0E10),
    val surface: Color = Color(0xFF1A1A1D),
    val accent: Color = Color(0xFFEF5350),
    val accent2: Color = Color(0xFFFF8A00),
    val textPrimary: Color = Color(0xFFF2F2F2),
    val textSecondary: Color = Color(0xFFA8A8AD),
    val titleSizeSp: Float = 30f,
    val textSizeSp: Float = 15f,
    val compact: Boolean = false,
)

data class ScreenLayout(
    val id: String,
    val title: String = "",
    val subtitle: String = "",
    val showHeader: Boolean = true,
    val showSidebar: Boolean = true,
    val sidebarItems: List<NavNode> = emptyList(),
    val root: LayoutNode? = null,
)

/** Nó genérico de layout. Cada tag do XML vira um LayoutNode com props. */
data class LayoutNode(
    val type: String,
    val props: Map<String, String> = emptyMap(),
    val children: List<LayoutNode> = emptyList(),
) {
    fun prop(name: String, default: String? = null): String? = props[name] ?: default
    fun propInt(name: String, default: Int = 0): Int = props[name]?.toIntOrNull() ?: default
    fun propFloat(name: String, default: Float = 0f): Float = props[name]?.toFloatOrNull() ?: default
    fun propBool(name: String, default: Boolean = false): Boolean =
        when (props[name]?.lowercase()) {
            "true", "1", "yes", "sim" -> true
            "false", "0", "no", "nao", "não" -> false
            else -> default
        }

    fun child(type: String): LayoutNode? = children.firstOrNull { it.type == type }
    fun childrenOf(type: String): List<LayoutNode> = children.filter { it.type == type }
}

/** Item de menu / ação (equivalente aos <item> do menu do Kodi). */
data class NavNode(
    val label: String,
    val action: String,
    val icon: String? = null,
    val index: Int = -1,
)
