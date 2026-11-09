package com.smarted.tv.ui.screens

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.smarted.tv.data.source.ArchivePreview
import com.smarted.tv.data.source.BrowseEntry
import com.smarted.tv.data.source.FileBrowser
import com.smarted.tv.data.source.FileKind
import com.smarted.tv.data.source.FilesState
import com.smarted.tv.data.source.SortKey
import com.smarted.tv.ui.components.EmptyState
import com.smarted.tv.ui.components.FocusCard
import com.smarted.tv.ui.components.ScreenTitle
import com.smarted.tv.ui.theme.Smarted

/**
 * Navegador de arquivos REAL (Fase C).
 *
 * Tudo o que aparece vem de pastas autorizadas pelo usuário via SAF — nada de
 * "Armazenamento interno / Downloads" fixos. Sem fonte autorizada, a tela pede
 * a autorização em vez de inventar conteúdo.
 */
@Composable
fun ArquivosScreen(
    state: FilesState,
    onOpenSource: (String) -> Unit,
    onOpenEntry: (BrowseEntry) -> Unit,
    onUp: () -> Unit,
    onGoTo: (Int) -> Unit,
    onRefresh: () -> Unit,
    onSort: (SortKey) -> Unit,
    onQuery: (String) -> Unit,
    onToggleFavorite: () -> Unit,
    onTreePicked: (String) -> Unit,
    onPlay: (BrowseEntry) -> Unit,
    onCloseArchive: () -> Unit,
    onShowInfo: (BrowseEntry?) -> Unit,
    onDismissMessage: () -> Unit,
) {
    val pickFolder = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        if (uri != null) {
            onTreePicked(uri.toString())
        }
    }

    Column(Modifier.fillMaxSize()) {
        ScreenTitle("Arquivos")

        // ── barra de ferramentas ──
        FilesToolbar(
            state = state,
            onUp = onUp,
            onRefresh = onRefresh,
            onSort = onSort,
            onQuery = onQuery,
            onToggleFavorite = onToggleFavorite,
            onOpenFavorite = onOpenSource,
            onPickFolder = { pickFolder.launch(null) },
        )

        // ── caminho / navegação ──
        if (state.crumbs.isNotEmpty()) {
            Breadcrumbs(state, onGoTo)
            Spacer(Modifier.height(10.dp))
        }

        state.error?.let { MsgCard(it, isError = true, onDismiss = onDismissMessage) }
        state.notice?.let { MsgCard(it, isError = false, onDismiss = onDismissMessage) }

        when {
            state.loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Lendo pasta…", color = Smarted.InkMuted, fontSize = 16.sp)
            }

            state.crumbs.isEmpty() -> SourcesPanel(state, onOpenSource, onPickFolder = { pickFolder.launch(null) })

            else -> {
                val rows = FileBrowser.display(state)
                if (rows.isEmpty()) {
                    EmptyState(
                        message = if (state.query.isNotBlank()) "Nada encontrado para \"${state.query}\"" else "Pasta vazia",
                        hint = if (state.query.isNotBlank())
                            "A busca vale só para esta pasta. Limpe o campo para ver tudo."
                        else
                            "Esta pasta não tem arquivos nem subpastas. Use ⟲ para atualizar.",
                        icon = Icons.Rounded.FolderOpen,
                    )
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        contentPadding = PaddingValues(bottom = 24.dp),
                        modifier = Modifier.fillMaxSize(),
                    ) {
                        items(rows, key = { it.uri }) { entry ->
                            FileRow(
                                entry = entry,
                                onClick = {
                                    if (entry.isDirectory) onOpenEntry(entry)
                                    else if (entry.isArchive) onOpenEntry(entry)
                                    else if (entry.isPlayable) onPlay(entry)
                                    else onShowInfo(entry)
                                },
                                onPlay = { onPlay(entry) },
                                onInfo = { onShowInfo(entry) },
                            )
                        }
                    }
                    Text(
                        FileBrowser.summarize(rows),
                        color = Smarted.InkMuted,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
            }
        }
    }

    state.archive?.let { ArchiveDialog(it, onCloseArchive) }
    state.info?.let { InfoDialog(it, onDismiss = { onShowInfo(null) }) }
}

// ───────────────────────────── toolbar ─────────────────────────────

@Composable
private fun FilesToolbar(
    state: FilesState,
    onUp: () -> Unit,
    onRefresh: () -> Unit,
    onSort: (SortKey) -> Unit,
    onQuery: (String) -> Unit,
    onToggleFavorite: () -> Unit,
    onOpenFavorite: (String) -> Unit,
    onPickFolder: () -> Unit,
) {
    var searching by remember { mutableStateOf(false) }
    Row(
        Modifier.fillMaxWidth().padding(bottom = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ToolButton(Icons.Rounded.ArrowUpward, "Subir", enabled = state.canGoUp, onClick = onUp)
        ToolButton(Icons.Rounded.Refresh, "Atualizar", enabled = true, onClick = onRefresh)
        ToolButton(Icons.Rounded.Add, "Adicionar pasta", enabled = true, onClick = onPickFolder)

        // ordenação
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            SortKey.values().forEach { key ->
                val active = state.sortKey == key
                val arrow = if (active) (if (state.ascending) " ↑" else " ↓") else ""
                ToolChip("${key.label}$arrow", active) { onSort(key) }
            }
        }

        Spacer(Modifier.weight(1f))

        ToolButton(
            if (state.favorites.any { it.uri == state.crumbs.lastOrNull()?.uri }) Icons.Rounded.Star else Icons.Rounded.StarBorder,
            "Favoritar",
            enabled = state.crumbs.isNotEmpty(),
            onClick = onToggleFavorite,
        )
        if (searching) {
            SearchField(state.query, onQuery) { searching = false; onQuery("") }
        } else {
            ToolButton(Icons.Rounded.Search, "Buscar nesta pasta", enabled = true) { searching = true }
        }
    }

    if (state.favorites.isNotEmpty()) {
        Row(
            Modifier.fillMaxWidth().padding(bottom = 8.dp).horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Favoritos:", color = Smarted.InkMuted, fontSize = 13.sp)
            state.favorites.forEach { fav ->
                ToolChip(fav.name, false) { onOpenFavorite(fav.uri) }
            }
        }
    }
}

@Composable
private fun SearchField(query: String, onQuery: (String) -> Unit, onClose: () -> Unit) {
    Row(
        Modifier
            .width(320.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(Color(0xFFF0F0F0))
            .border(1.dp, Color(0x1A000000), RoundedCornerShape(14.dp))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Rounded.Search, null, tint = Smarted.InkMuted, modifier = Modifier.size(18.dp))
        Spacer(Modifier.width(8.dp))
        Box(Modifier.weight(1f)) {
            if (query.isEmpty()) Text("Buscar nesta pasta", color = Smarted.InkMuted, fontSize = 14.sp)
            BasicTextField(
                value = query,
                onValueChange = onQuery,
                textStyle = TextStyle(color = Smarted.InkOnWhite, fontSize = 14.sp),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        Icon(
            Icons.Rounded.Close, "Fechar busca",
            tint = Smarted.InkMuted,
            modifier = Modifier.size(18.dp).clip(RoundedCornerShape(9.dp)).clickableNoRipple(onClose),
        )
    }
}

private fun Modifier.clickableNoRipple(onClick: () -> Unit): Modifier =
    this.clickable(onClick = onClick)

@Composable
private fun ToolButton(icon: ImageVector, label: String, enabled: Boolean, onClick: () -> Unit) {
    val shape = RoundedCornerShape(14.dp)
    Box(
        Modifier
            .clip(shape)
            .background(if (enabled) Color(0xFFEDEDED) else Color(0xFFF5F5F5))
            .border(1.dp, Color(0x14000000), shape)
            .then(if (enabled) Modifier.clickableNoRipple(onClick) else Modifier)
            .padding(horizontal = 12.dp, vertical = 10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, label, tint = if (enabled) Smarted.InkOnWhite else Smarted.InkMuted, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(6.dp))
            Text(label, color = if (enabled) Smarted.InkOnWhite else Smarted.InkMuted, fontSize = 13.sp)
        }
    }
}

@Composable
private fun ToolChip(label: String, active: Boolean, onClick: () -> Unit) {
    val shape = RoundedCornerShape(12.dp)
    Box(
        Modifier
            .clip(shape)
            .background(if (active) Smarted.CardOnWhite else Color(0xFFEDEDED))
            .border(1.dp, if (active) Color.Transparent else Color(0x14000000), shape)
            .clickableNoRipple(onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(label, color = if (active) Color.White else Smarted.InkOnWhite, fontSize = 13.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Normal)
    }
}

// ───────────────────────────── caminho ─────────────────────────────

@Composable
private fun Breadcrumbs(state: FilesState, onGoTo: (Int) -> Unit) {
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        state.crumbs.forEachIndexed { index, crumb ->
            if (index > 0) Text("  ›  ", color = Smarted.InkMuted, fontSize = 14.sp)
            val isLast = index == state.crumbs.lastIndex
            Text(
                crumb.name,
                color = if (isLast) Smarted.InkOnWhite else Smarted.InkMuted,
                fontWeight = if (isLast) FontWeight.Bold else FontWeight.Normal,
                fontSize = 14.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .then(if (isLast) Modifier else Modifier.clickableNoRipple { onGoTo(index) })
                    .padding(horizontal = 6.dp, vertical = 4.dp),
            )
        }
    }
}

// ───────────────────────────── fontes ─────────────────────────────

@Composable
private fun SourcesPanel(state: FilesState, onOpenSource: (String) -> Unit, onPickFolder: () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        if (state.sources.isEmpty()) {
            EmptyState(
                message = "Nenhuma pasta autorizada",
                hint = "Toque em \"Adicionar pasta\" para escolher um local do aparelho. " +
                    "O Android só permite listar pastas que você autorizar.",
                icon = Icons.Rounded.FolderOff,
            )
        } else {
            Text("Fontes autorizadas", color = Smarted.InkMuted, fontSize = 13.sp,
                modifier = Modifier.padding(bottom = 8.dp))
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(state.sources, key = { it.uri }) { src ->
                    FocusCard(Modifier.fillMaxWidth().height(72.dp), { onOpenSource(src.uri) }) {
                        Row(Modifier.fillMaxSize().padding(horizontal = 22.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Rounded.SdStorage, null, tint = Color.White, modifier = Modifier.size(28.dp))
                            Spacer(Modifier.width(16.dp))
                            Text(src.name, color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.Medium)
                        }
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            ToolButton(Icons.Rounded.Add, "Adicionar outra pasta", enabled = true, onClick = onPickFolder)
        }
    }
}

// ───────────────────────────── linha ─────────────────────────────

@Composable
private fun FileRow(
    entry: BrowseEntry,
    onClick: () -> Unit,
    onPlay: () -> Unit,
    onInfo: () -> Unit,
) {
    FocusCard(Modifier.fillMaxWidth().height(70.dp), onClick) {
        Row(Modifier.fillMaxSize().padding(horizontal = 18.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(iconOf(entry), null, tint = Color.White, modifier = Modifier.size(26.dp))
            Spacer(Modifier.width(16.dp))
            Column(Modifier.weight(1f)) {
                Text(entry.name, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Medium,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(subtitleOf(entry), color = Smarted.TextLight, fontSize = 12.sp, maxLines = 1)
            }
            if (entry.isPlayable) {
                Icon(
                    Icons.Rounded.PlayArrow, "Reproduzir", tint = Color.White,
                    modifier = Modifier.size(26.dp).clickableNoRipple(onPlay),
                )
                Spacer(Modifier.width(12.dp))
            }
            Icon(
                Icons.Rounded.Info, "Informações", tint = Smarted.TextLight,
                modifier = Modifier.size(20.dp).clickableNoRipple(onInfo),
            )
        }
    }
}

private fun subtitleOf(entry: BrowseEntry): String {
    if (entry.isDirectory) return "Pasta"
    val parts = mutableListOf<String>()
    val type = when (entry.kind) {
        FileKind.VIDEO -> "Vídeo"
        FileKind.AUDIO -> "Áudio"
        FileKind.HLS -> "HLS (lista .m3u8)"
        FileKind.DASH -> "DASH (.mpd)"
        FileKind.SMOOTH -> "Smooth Streaming"
        FileKind.SEGMENT -> "Segmento de stream (não é vídeo)"
        FileKind.PLAYLIST -> "Lista de reprodução"
        FileKind.ARCHIVE -> "Pacote (ZIP)"
        FileKind.ADDON_MANIFEST -> "addon.xml"
        FileKind.REPO_MANIFEST -> "Manifesto de repositório"
        FileKind.CONFIG -> "Configuração"
        FileKind.SCRIPT -> "Script (não executável)"
        FileKind.DATABASE -> "Banco de dados"
        FileKind.IMAGE -> "Imagem"
        FileKind.SUBTITLE -> "Legenda"
        FileKind.TEXT -> "Texto"
        FileKind.UNKNOWN -> "Tipo não identificado"
    }
    parts += type
    if (entry.size > 0) parts += FileBrowser.describeSize(entry.size)
    if (entry.lastModified > 0) parts += FileBrowser.describeDate(entry.lastModified)
    return parts.joinToString(" · ")
}

private fun iconOf(entry: BrowseEntry): ImageVector = when {
    entry.isDirectory -> Icons.Rounded.Folder
    else -> when (entry.kind) {
        FileKind.VIDEO -> Icons.Rounded.Movie
        FileKind.AUDIO -> Icons.Rounded.Audiotrack
        FileKind.HLS, FileKind.DASH, FileKind.SMOOTH -> Icons.Rounded.LiveTv
        FileKind.SEGMENT -> Icons.Rounded.Link
        FileKind.PLAYLIST -> Icons.Rounded.QueueMusic
        FileKind.ARCHIVE -> Icons.Rounded.FolderZip
        FileKind.ADDON_MANIFEST, FileKind.REPO_MANIFEST -> Icons.Rounded.Extension
        FileKind.CONFIG, FileKind.TEXT -> Icons.Rounded.Description
        FileKind.SCRIPT -> Icons.Rounded.Code
        FileKind.DATABASE -> Icons.Rounded.Storage
        FileKind.IMAGE -> Icons.Rounded.Image
        FileKind.SUBTITLE -> Icons.Rounded.Subtitles
        FileKind.UNKNOWN -> Icons.Rounded.InsertDriveFile
    }
}

// ───────────────────────────── mensagens ─────────────────────────────

@Composable
private fun MsgCard(text: String, isError: Boolean, onDismiss: () -> Unit) {
    val bg = if (isError) Color(0xFFFDECEA) else Color(0xFFEFF7EE)
    val fg = if (isError) Color(0xFF7A2018) else Color(0xFF1F5F2A)
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp)
            .clip(RoundedCornerShape(14.dp)).background(bg).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text, color = fg, fontSize = 13.sp, modifier = Modifier.weight(1f))
        Icon(Icons.Rounded.Close, "Fechar", tint = fg,
            modifier = Modifier.size(18.dp).clickableNoRipple(onDismiss))
    }
}

// ───────────────────────────── diálogos ─────────────────────────────

@Composable
private fun ArchiveDialog(preview: ArchivePreview, onClose: () -> Unit) {
    Dialog(onDismissRequest = onClose) {
        Column(
            Modifier.width(720.dp).heightIn(max = 560.dp)
                .clip(RoundedCornerShape(22.dp)).background(Color.White).padding(24.dp),
        ) {
            Text(preview.name, color = Smarted.InkOnWhite, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Spacer(Modifier.height(6.dp))
            Text(
                "${preview.totalFiles} arquivos · " +
                    if (preview.isRepository) "manifesto de repositório encontrado" else "sem manifesto de repositório",
                color = Smarted.InkMuted, fontSize = 13.sp,
            )
            if (preview.addonXmlPaths.isNotEmpty()) {
                Text("addon.xml: ${preview.addonXmlPaths.joinToString(", ")}", color = Smarted.InkMuted, fontSize = 12.sp)
            }
            if (preview.unsafe > 0) {
                Spacer(Modifier.height(6.dp))
                Text("${preview.unsafe} entrada(s) insegura(s) detectada(s) — não serão extraídas.",
                    color = Color(0xFF7A2018), fontSize = 12.sp)
            }
            preview.warnings.forEach {
                Text("⚠ $it", color = Color(0xFF7A2018), fontSize = 12.sp)
            }
            Spacer(Modifier.height(12.dp))
            LazyColumn(Modifier.weight(1f)) {
                items(preview.entries) { e ->
                    Text(
                        (if (e.isDirectory) "▸ " else "  ") + e.name,
                        color = if (e.isSafe) Smarted.InkOnWhite else Color(0xFF7A2018),
                        fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(vertical = 2.dp),
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                ToolChip("Fechar", true, onClose)
            }
        }
    }
}

@Composable
private fun InfoDialog(entry: BrowseEntry, onDismiss: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            Modifier.width(520.dp).clip(RoundedCornerShape(22.dp)).background(Color.White).padding(24.dp),
        ) {
            Text(entry.name, color = Smarted.InkOnWhite, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Spacer(Modifier.height(10.dp))
            InfoLine("Tipo", subtitleOf(entry))
            InfoLine("MIME", entry.mime ?: "—")
            InfoLine("Tamanho", if (entry.isDirectory) "—" else FileBrowser.describeSize(entry.size))
            InfoLine("Modificado", FileBrowser.describeDate(entry.lastModified))
            InfoLine("Ação", when (entry.action) {
                com.smarted.tv.data.source.FileAction.PLAY -> "Reproduzir no player"
                com.smarted.tv.data.source.FileAction.BROWSE -> "Abrir/inspecionar"
                com.smarted.tv.data.source.FileAction.INSPECT -> "Ver informações"
                com.smarted.tv.data.source.FileAction.READ_ONLY -> "Só leitura (não executa)"
                com.smarted.tv.data.source.FileAction.NONE -> "Não tratado"
            })
            InfoLine("Local", entry.uri)
            if (entry.reason.isNotBlank()) InfoLine("Motivo", entry.reason)
            Spacer(Modifier.height(14.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                ToolChip("Fechar", true, onDismiss)
            }
        }
    }
}

@Composable
private fun InfoLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Text("$label: ", color = Smarted.InkMuted, fontSize = 13.sp, modifier = Modifier.width(104.dp))
        Text(value, color = Smarted.InkOnWhite, fontSize = 13.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
    }
}
