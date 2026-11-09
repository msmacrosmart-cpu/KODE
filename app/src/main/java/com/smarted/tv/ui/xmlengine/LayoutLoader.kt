package com.smarted.tv.ui.xmlengine

import android.content.Context
import java.io.File

/**
 * Carrega o layout de 3 lugares, nesta ordem:
 *  1. arquivo externo (editável no aparelho): getExternalFilesDir("layout")/home.xml
 *  2. assets/layout/<arquivo>
 *  3. fallback embutido (nunca deixa o app sem layout -> nunca tela preta)
 */
object LayoutLoader {

    private const val ASSET_DIR = "layout"

    data class Result(
        val layout: SmartLayout,
        val source: String,
        val error: String? = null,
    )

    fun load(context: Context, file: String = "home.xml"): Result {
        // 1) arquivo externo (permite trocar layout sem recompilar)
        val external = File(context.getExternalFilesDir(null), "$ASSET_DIR/$file")
        if (external.exists()) {
            runCatching {
                external.inputStream().use { return Result(LayoutParser.parse(it), "arquivo: ${external.path}") }
            }.onFailure { e ->
                return Result(builtin(), "embutido", "Erro no XML externo (${external.path}): ${e.message}")
            }
        }

        // 2) assets
        runCatching {
            context.assets.open("$ASSET_DIR/$file").use {
                return Result(LayoutParser.parse(it), "assets/$ASSET_DIR/$file")
            }
        }.onFailure { e ->
            return Result(builtin(), "embutido", "Não achei assets/$ASSET_DIR/$file (${e.message})")
        }

        return Result(builtin(), "embutido")
    }

    /** Layout mínimo embutido no código — rede de segurança. */
    fun builtin(): SmartLayout {
        val theme = LayoutTheme()
        val items = listOf(
            NavNode("Início", "screen:home", "home", 0),
            NavNode("Canais", "screen:canais", "live_tv", 1),
            NavNode("Filmes", "screen:filmes", "movie", 2),
            NavNode("Séries", "screen:series", "tv", 3),
            NavNode("Config", "screen:configuracoes", "settings", 4),
            NavNode("Sair", "exit", "logout", 5),
        )
        val screen = ScreenLayout(
            id = "home",
            title = "SmartED-TV",
            subtitle = "Layout embutido (assets ausente)",
            sidebarItems = items,
            root = LayoutNode(
                type = "column",
                props = mapOf("padding" to "24"),
                children = listOf(
                    LayoutNode("text", mapOf("text" to "Bem-vindo ao SmartED-TV", "size" to "30")),
                    LayoutNode(
                        "row",
                        mapOf("gap" to "16", "padding" to "16"),
                        listOf(
                            LayoutNode("card", mapOf("title" to "Canais", "action" to "screen:canais", "icon" to "live_tv")),
                            LayoutNode("card", mapOf("title" to "Filmes", "action" to "screen:filmes", "icon" to "movie")),
                            LayoutNode("card", mapOf("title" to "Séries", "action" to "screen:series", "icon" to "tv")),
                        ),
                    ),
                ),
            ),
        )
        return SmartLayout(theme = theme, screen = screen, screens = listOf(screen))
    }
}
