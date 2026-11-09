package com.smarted.tv.ui.xmlengine

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Extension
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LiveTv
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Tv
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smarted.tv.ui.components.SmartEDFocusable
import com.smarted.tv.ui.xmlengine.LayoutParser.colorOf

/**
 * Renderiza o SmartLayout (vindo do XML) em Compose.
 * Suporta: column, row, grid, list, sidebar, card, text, image, button, spacer, divider, banner.
 * Navegação por D-pad (foco) e toque.
 */
@Composable
fun SmartLayoutScreen(
    layout: SmartLayout,
    screenKey: String,
    onNavigate: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val theme = layout.theme
    val screen = layout.screen(screenKey) ?: layout.screen ?: LayoutLoader.builtin().screen!!

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(theme.background),
    ) {
        if (screen.showHeader) {
            Header(screen = screen, theme = theme, onNavigate = onNavigate)
        }

        Row(modifier = Modifier.weight(1f).fillMaxWidth()) {
            if (screen.showSidebar && screen.sidebarItems.isNotEmpty()) {
                Sidebar(
                    items = screen.sidebarItems,
                    activeAction = "screen:$screenKey",
                    theme = theme,
                    onNavigate = onNavigate,
                )
            }

            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .padding(horizontal = 24.dp, vertical = 16.dp),
            ) {
                screen.root?.let { root ->
                    RenderNode(root, theme, onNavigate)
                }
            }
        }
    }
}

@Composable
private fun Header(screen: ScreenLayout, theme: LayoutTheme, onNavigate: (String) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(64.dp)
            .background(theme.surface)
            .padding(horizontal = 20.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Default.Tv, contentDescription = null, tint = theme.accent, modifier = Modifier.size(28.dp))
        Spacer(Modifier.width(10.dp))
        Column {
            Text(
                text = screen.title.ifBlank { "SmartED-TV" },
                color = theme.textPrimary,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
            )
            if (screen.subtitle.isNotBlank()) {
                Text(text = screen.subtitle, color = theme.textSecondary, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun Sidebar(
    items: List<NavNode>,
    activeAction: String,
    theme: LayoutTheme,
    onNavigate: (String) -> Unit,
) {
    Column(
        modifier = Modifier
            .width(88.dp)
            .fillMaxHeight()
            .background(theme.surface)
            .padding(vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        items.forEach { item ->
            val selected = item.action == activeAction
            SmartEDFocusable(
                onClick = { onNavigate(item.action) },
                modifier = Modifier.size(64.dp),
                shape = RoundedCornerShape(16.dp),
                selected = selected,
                idleColor = if (selected) theme.accent.copy(alpha = 0.22f) else Color(0x14FFFFFF),
            ) {
                Column(
                    modifier = Modifier.fillMaxSize(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(
                        imageVector = iconFor(item.icon, item.action),
                        contentDescription = item.label,
                        tint = if (selected) theme.textPrimary else theme.textSecondary,
                        modifier = Modifier.size(24.dp),
                    )
                    Text(
                        text = item.label,
                        color = if (selected) theme.textPrimary else theme.textSecondary,
                        fontSize = 10.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
fun RenderNode(node: LayoutNode, theme: LayoutTheme, onNavigate: (String) -> Unit) {
    val padding = node.propInt("padding", 0).dp
    val gap = node.propInt("gap", 8).dp

    when (node.type) {
        "column" -> Column(
            modifier = Modifier.fillMaxSize().padding(padding),
            verticalArrangement = Arrangement.spacedBy(gap),
        ) { node.children.forEach { RenderNode(it, theme, onNavigate) } }

        "row" -> Row(
            modifier = Modifier.fillMaxWidth().padding(padding),
            horizontalArrangement = Arrangement.spacedBy(gap),
        ) { node.children.forEach { RenderNode(it, theme, onNavigate) } }

        "grid" -> {
            val cols = node.propInt("columns", 3)
            val items = node.children
            LazyVerticalGrid(
                columns = GridCells.Fixed(cols),
                horizontalArrangement = Arrangement.spacedBy(gap),
                verticalArrangement = Arrangement.spacedBy(gap),
                modifier = Modifier.fillMaxSize(),
            ) { items(items, key = { it.props.hashCode() + it.type }) { RenderNode(it, theme, onNavigate) } }
        }

        "list" -> LazyColumn(
            verticalArrangement = Arrangement.spacedBy(gap),
            modifier = Modifier.fillMaxSize(),
        ) { items(node.children) { RenderNode(it, theme, onNavigate) } }

        "rowscroll" -> LazyRow(
            horizontalArrangement = Arrangement.spacedBy(gap),
            modifier = Modifier.fillMaxWidth(),
        ) { items(node.children) { RenderNode(it, theme, onNavigate) } }

        "text" -> Text(
            text = node.prop("text", "") ?: "",
            color = colorOf(node.prop("color")) ?: theme.textPrimary,
            fontSize = node.propFloat("size", theme.textSizeSp).sp,
            fontWeight = if (node.propBool("bold")) FontWeight.Bold else FontWeight.Normal,
            modifier = Modifier.padding(padding),
        )

        "button", "card" -> {
            val action = node.prop("action")
            SmartEDFocusable(
                onClick = { action?.let(onNavigate) },
                modifier = Modifier
                    .then(if (node.propBool("fullWidth")) Modifier.fillMaxWidth() else Modifier)
                    .height(node.propInt("height", 96).dp),
                shape = RoundedCornerShape(16.dp),
                idleColor = colorOf(node.prop("bg")) ?: theme.surface,
            ) {
                Row(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    node.prop("icon")?.let {
                        Icon(
                            imageVector = iconFor(it, action),
                            contentDescription = null,
                            tint = colorOf(node.prop("color")) ?: theme.accent,
                            modifier = Modifier.size(28.dp),
                        )
                        Spacer(Modifier.width(12.dp))
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = node.prop("title", node.prop("text", "") ?: "") ?: "",
                            color = theme.textPrimary,
                            fontSize = theme.textSizeSp.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        node.prop("subtitle")?.let {
                            Text(text = it, color = theme.textSecondary, fontSize = (theme.textSizeSp - 2f).sp, maxLines = 1)
                        }
                    }
                    if (action != null) {
                        Icon(Icons.Default.PlayArrow, contentDescription = null, tint = theme.accent, modifier = Modifier.size(20.dp))
                    }
                }
            }
        }

        "spacer" -> Spacer(Modifier.height(node.propInt("height", 16).dp))

        "divider" -> Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(theme.textSecondary.copy(alpha = 0.25f)),
        )

        "image" -> {
            val size = node.propInt("size", 64).dp
            val src = node.prop("src")
            val bitmap = if (src != null) rememberAssetBitmap(src) else null
            Box(
                modifier = Modifier
                    .size(size)
                    .border(1.dp, theme.accent.copy(alpha = 0.4f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                if (bitmap != null) {
                    Image(
                        bitmap = bitmap,
                        contentDescription = node.prop("alt"),
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize(),
                    )
                } else {
                    Icon(iconFor(node.prop("icon"), null), contentDescription = null, tint = theme.accent)
                }
            }
        }

        "banner" -> Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(node.propInt("height", 140).dp)
                .background(theme.accent.copy(alpha = 0.15f), RoundedCornerShape(20.dp))
                .padding(20.dp),
            contentAlignment = Alignment.CenterStart,
        ) {
            Column {
                Text(
                    text = node.prop("title", "") ?: "",
                    color = theme.textPrimary,
                    fontSize = (theme.titleSizeSp - 4f).sp,
                    fontWeight = FontWeight.Bold,
                )
                node.prop("subtitle")?.let {
                    Text(text = it, color = theme.textSecondary, fontSize = theme.textSizeSp.sp)
                }
            }
        }

        else -> {
            // tag desconhecida: tenta renderizar filhos (não quebra)
            Column(verticalArrangement = Arrangement.spacedBy(gap)) {
                node.children.forEach { RenderNode(it, theme, onNavigate) }
            }
        }
    }
}

/** Ícones por nome (equivalente às texturas da skin do Kodi). */
fun iconFor(name: String?, action: String?): ImageVector = when (name?.lowercase()) {
    "home", "inicio", "início" -> Icons.Default.Home
    "live_tv", "canais", "tv_live" -> Icons.Default.LiveTv
    "movie", "filmes" -> Icons.Default.Movie
    "tv", "series", "séries" -> Icons.Default.Tv
    "folder", "pastas" -> Icons.Default.Folder
    "settings", "config" -> Icons.Default.Settings
    "logout", "sair" -> Icons.Default.Logout
    "addon", "addons", "extension" -> Icons.Default.Extension
    "info" -> Icons.Default.Info
    else -> when {
        action?.contains("canais") == true -> Icons.Default.LiveTv
        action?.contains("filmes") == true -> Icons.Default.Movie
        action?.contains("series") == true -> Icons.Default.Tv
        action?.contains("config") == true -> Icons.Default.Settings
        action?.contains("exit") == true -> Icons.Default.Logout
        else -> Icons.Default.Home
    }
}

/** Carrega imagem de assets/layout/images/<src> (equivalente às texturas da skin do Kodi). */
@Composable
private fun rememberAssetBitmap(src: String): androidx.compose.ui.graphics.ImageBitmap? {
    val context = LocalContext.current
    return remember(src) {
        runCatching {
            context.assets.open("layout/images/$src").use { BitmapFactory.decodeStream(it)?.asImageBitmap() }
        }.getOrNull()
    }
}
