package com.smarted.tv.ui.screens

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
import com.smarted.tv.data.addon.AddonInstaller
import com.smarted.tv.data.addon.AddonKind
import com.smarted.tv.data.addon.Compatibility
import com.smarted.tv.data.addon.RepoNodeType
import com.smarted.tv.data.addon.RepositoryNode
import com.smarted.tv.data.addon.RepositoryStore
import com.smarted.tv.ui.components.EmptyState
import com.smarted.tv.ui.components.FocusCard
import com.smarted.tv.ui.components.ScreenTitle
import com.smarted.tv.ui.theme.Smarted
import com.smarted.tv.viewmodel.AddonsViewModel
import com.smarted.tv.viewmodel.RepositoriesViewModel

/**
 * Tela única de Add-ons (Fase E) com três abas reais:
 *  · Instalados — o que está no disco, com compatibilidade declarada;
 *  · Repositórios — fontes cadastradas (URL/ZIP/pasta) e catálogo navegável;
 *  · Instalar de ZIP — seleção de arquivo + confirmação antes de instalar.
 *
 * Nenhum add-on é listado sem existir; nenhum é marcado "funcionando" por ter addon.xml.
 */
@Composable
fun AddonsScreen(
    addonState: AddonsViewModel.State,
    repoState: RepositoriesViewModel.State,
    onInstallZip: (String, String) -> Unit,
    onConfirmInstall: (Boolean) -> Unit,
    onCancelPending: () -> Unit,
    onUninstall: (String) -> Unit,
    onSelectAddon: (AddonInstaller.Installed?) -> Unit,
    onSetCategory: (AddonKind?) -> Unit,
    onRefreshAddons: () -> Unit,
    onAddRepo: (String) -> Unit,
    onLoadRepo: (String) -> Unit,
    onOpenRepoNode: (RepositoryNode) -> Unit,
    onRepoUp: () -> Unit,
    onRepoNodeAt: (Int) -> Unit,
    onToggleRepo: (String, Boolean) -> Unit,
    onRemoveRepo: (String) -> Unit,
    onSelectRepoNode: (RepositoryNode?) -> Unit,
    onDismissMessage: () -> Unit,
    onOpenPlugin: (String) -> Unit,
) {
    var tab by remember { mutableStateOf(Tab.INSTALLED) }

    val pickZip = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val name = uri.lastPathSegment?.substringAfterLast('/') ?: "pacote.zip"
            onInstallZip(uri.toString(), name)
        }
    }

    Column(Modifier.fillMaxSize()) {
        ScreenTitle("Add-ons")

        TabRow(tab, repoState.repositories.size, addonState.installed.size) { tab = it }
        Spacer(Modifier.height(12.dp))

        addonState.error?.let { MessageCard(it, true, onDismissMessage) }
        addonState.notice?.let { MessageCard(it, false, onDismissMessage) }
        repoState.error?.let { MessageCard(it, true, onDismissMessage) }
        repoState.notice?.let { MessageCard(it, false, onDismissMessage) }

        when (tab) {
            Tab.INSTALLED -> InstalledTab(
                state = addonState,
                onUninstall = onUninstall,
                onSelect = onSelectAddon,
                onCategory = onSetCategory,
                onRefresh = onRefreshAddons,
                onBrowseZip = { pickZip.launch(arrayOf("application/zip", "application/octet-stream", "*/*")) },
            )

            Tab.REPOSITORIES -> RepositoriesTab(
                state = repoState,
                onAddRepo = onAddRepo,
                onLoadRepo = onLoadRepo,
                onOpenNode = onOpenRepoNode,
                onUp = onRepoUp,
                onNodeAt = onRepoNodeAt,
                onToggle = onToggleRepo,
                onRemove = onRemoveRepo,
                onSelectNode = onSelectRepoNode,
            )

            Tab.INSTALL_ZIP -> InstallZipTab(onBrowseZip = {
                pickZip.launch(arrayOf("application/zip", "application/octet-stream", "*/*"))
            })
        }
    }

    addonState.pending?.let { pending ->
        PendingDialog(pending, onConfirm = onConfirmInstall, onCancel = onCancelPending)
    }
    addonState.selected?.let { addon ->
        AddonDetailDialog(
            addon = addon,
            files = addonState.files,
            onClose = { onSelectAddon(null) },
            onUninstall = onUninstall,
            onOpen = { onOpenPlugin("plugin://${addon.id}/") },
        )
    }
}

enum class Tab(val label: String) { INSTALLED("Instalados"), REPOSITORIES("Repositórios"), INSTALL_ZIP("Instalar de ZIP") }

@Composable
private fun TabRow(selected: Tab, repos: Int, installed: Int, onSelect: (Tab) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Tab.entries.forEach { t ->
            val active = t == selected
            val count = when (t) {
                Tab.INSTALLED -> installed
                Tab.REPOSITORIES -> repos
                Tab.INSTALL_ZIP -> null
            }
            val shape = RoundedCornerShape(14.dp)
            Box(
                Modifier.clip(shape)
                    .background(if (active) Smarted.CardOnWhite else Color(0xFFEDEDED))
                    .border(1.dp, if (active) Color.Transparent else Color(0x14000000), shape)
                    .clickable { onSelect(t) }
                    .padding(horizontal = 18.dp, vertical = 11.dp),
            ) {
                Text(
                    if (count != null) "${t.label} · $count" else t.label,
                    color = if (active) Color.White else Smarted.InkOnWhite,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Normal,
                    fontSize = 14.sp,
                )
            }
        }
    }
}

// ───────────────────────── instalados ─────────────────────────

@Composable
private fun InstalledTab(
    state: AddonsViewModel.State,
    onUninstall: (String) -> Unit,
    onSelect: (AddonInstaller.Installed?) -> Unit,
    onCategory: (AddonKind?) -> Unit,
    onRefresh: () -> Unit,
    onBrowseZip: () -> Unit,
) {
    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(bottom = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SmallChip("Todos (${state.installed.size})", state.categoryFilter == null) { onCategory(null) }
            state.installed.map { it.kind }.distinct().sortedBy { it.ordinal }.forEach { kind ->
                SmallChip(kindLabel(kind), state.categoryFilter == kind) { onCategory(kind) }
            }
            Spacer(Modifier.weight(1f))
            SmallAction(Icons.Rounded.Refresh, "Atualizar", onRefresh)
            SmallAction(Icons.Rounded.Add, "Instalar ZIP", onBrowseZip)
        }

        if (state.installed.isEmpty()) {
            EmptyState(
                message = "Nenhum add-on instalado",
                hint = "Use \"Instalar de ZIP\" para escolher um pacote .zip do aparelho. " +
                    "Add-ons do Kodi em Python precisam de adaptação para rodar aqui — " +
                    "o app mostra isso antes de instalar.",
                icon = Icons.Rounded.Extension,
            )
            return
        }

        Text(
            "${state.installed.size} instalados · ${state.runnable} executáveis ou adaptáveis",
            color = Smarted.InkMuted, fontSize = 13.sp, modifier = Modifier.padding(bottom = 8.dp),
        )

        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(state.filtered, key = { it.id }) { addon ->
                FocusCard(Modifier.fillMaxWidth().height(84.dp), { onSelect(addon) }) {
                    Row(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(kindIcon(addon.kind), null, tint = Color.White, modifier = Modifier.size(28.dp))
                        Spacer(Modifier.width(16.dp))
                        Column(Modifier.weight(1f)) {
                            Text("${addon.name}  ${addon.version}", color = Color.White,
                                fontWeight = FontWeight.Medium, fontSize = 16.sp,
                                maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text("${kindLabel(addon.kind)} · ${compatLabel(addon.compatibility)}",
                                color = Smarted.TextLight, fontSize = 12.sp, maxLines = 1)
                        }
                        CompatBadge(addon.compatibility)
                    }
                }
            }
        }
    }
}

// ───────────────────────── repositórios ─────────────────────────

@Composable
private fun RepositoriesTab(
    state: RepositoriesViewModel.State,
    onAddRepo: (String) -> Unit,
    onLoadRepo: (String) -> Unit,
    onOpenNode: (RepositoryNode) -> Unit,
    onUp: () -> Unit,
    onNodeAt: (Int) -> Unit,
    onToggle: (String, Boolean) -> Unit,
    onRemove: (String) -> Unit,
    onSelectNode: (RepositoryNode?) -> Unit,
) {
    var url by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize()) {
        // adicionar por URL
        Row(
            Modifier.fillMaxWidth().padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.weight(1f).height(46.dp).clip(RoundedCornerShape(14.dp))
                    .background(Color(0xFFF0F0F0)).border(1.dp, Color(0x14000000), RoundedCornerShape(14.dp))
                    .padding(horizontal = 14.dp),
                contentAlignment = Alignment.CenterStart,
            ) {
                if (url.isEmpty()) {
                    Text("https://…/addons.xml", color = Smarted.InkMuted, fontSize = 14.sp)
                }
                BasicTextField(
                    value = url, onValueChange = { url = it }, singleLine = true,
                    textStyle = TextStyle(color = Smarted.InkOnWhite, fontSize = 14.sp),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            SmallAction(Icons.Rounded.Add, "Adicionar", { if (url.isNotBlank()) { onAddRepo(url); url = "" } })
        }

        if (state.tree != null) {
            RepoTreeView(state, onOpenNode, onUp, onNodeAt, onSelectNode)
            return
        }

        if (state.repositories.isEmpty()) {
            EmptyState(
                message = "Nenhum repositório cadastrado",
                hint = "Cole a URL do addons.xml de um repositório do Kodi, ou importe o ZIP do repositório " +
                    "pela aba Arquivos.",
                icon = Icons.Rounded.Storage,
            )
            return
        }

        Text("Repositórios cadastrados", color = Smarted.InkMuted, fontSize = 13.sp,
            modifier = Modifier.padding(bottom = 8.dp))
        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(state.repositories, key = { it.id }) { repo ->
                RepoRow(repo, onLoad = { onLoadRepo(repo.id) }, onToggle = { onToggle(repo.id, !repo.enabled) },
                    onRemove = { onRemove(repo.id) })
            }
        }
    }
}

@Composable
private fun RepoRow(
    repo: RepositoryStore.Entry,
    onLoad: () -> Unit,
    onToggle: () -> Unit,
    onRemove: () -> Unit,
) {
    FocusCard(Modifier.fillMaxWidth().height(88.dp), onLoad) {
        Row(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.Storage, null, tint = Color.White, modifier = Modifier.size(26.dp))
            Spacer(Modifier.width(16.dp))
            Column(Modifier.weight(1f)) {
                Text(repo.name, color = Color.White, fontWeight = FontWeight.Medium, fontSize = 16.sp,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    listOfNotNull(
                        when (repo.kind) {
                            com.smarted.tv.data.addon.RepoSource.SourceKind.URL -> "URL"
                            com.smarted.tv.data.addon.RepoSource.SourceKind.ZIP -> "ZIP"
                            com.smarted.tv.data.addon.RepoSource.SourceKind.FOLDER -> "Pasta"
                            com.smarted.tv.data.addon.RepoSource.SourceKind.INSTALLED -> "Interno"
                        },
                        if (repo.addonCount > 0) "${repo.addonCount} add-ons" else null,
                        if (!repo.enabled) "desabilitado" else null,
                        repo.lastError,
                    ).joinToString(" · "),
                    color = if (repo.lastError != null) Color(0xFFFFB4A9) else Smarted.TextLight,
                    fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
            Icon(if (repo.enabled) Icons.Rounded.ToggleOn else Icons.Rounded.ToggleOff, "Habilitar",
                tint = Color.White, modifier = Modifier.size(30.dp).clickable(onClick = onToggle))
            Spacer(Modifier.width(12.dp))
            Icon(Icons.Rounded.Delete, "Remover", tint = Color.White,
                modifier = Modifier.size(22.dp).clickable(onClick = onRemove))
        }
    }
}

@Composable
private fun RepoTreeView(
    state: RepositoriesViewModel.State,
    onOpenNode: (RepositoryNode) -> Unit,
    onUp: () -> Unit,
    onNodeAt: (Int) -> Unit,
    onSelectNode: (RepositoryNode?) -> Unit,
) {
    val current = state.nodePath.lastOrNull() ?: state.tree ?: return
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            SmallAction(Icons.Rounded.ArrowUpward, "Subir", onUp)
            Spacer(Modifier.width(10.dp))
            Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()), verticalAlignment = Alignment.CenterVertically) {
                state.nodePath.forEachIndexed { index, node ->
                    if (index > 0) Text("  ›  ", color = Smarted.InkMuted, fontSize = 13.sp)
                    Text(
                        node.name,
                        color = if (index == state.nodePath.lastIndex) Smarted.InkOnWhite else Smarted.InkMuted,
                        fontWeight = if (index == state.nodePath.lastIndex) FontWeight.Bold else FontWeight.Normal,
                        fontSize = 13.sp,
                        modifier = Modifier.clickable { onNodeAt(index) }.padding(4.dp),
                    )
                }
            }
        }

        state.warnings.forEach { MessageCard("⚠ $it", false) {} }

        val children = current.children
        if (children.isEmpty()) {
            EmptyState("Nada nesta categoria", "O catálogo do repositório não declara itens aqui.",
                icon = Icons.Rounded.Inbox)
            return
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(children, key = { it.id }) { node ->
                FocusCard(Modifier.fillMaxWidth().height(78.dp), {
                    if (node.children.isNotEmpty()) onOpenNode(node) else onSelectNode(node)
                }) {
                    Row(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(nodeIcon(node), null, tint = Color.White, modifier = Modifier.size(24.dp))
                        Spacer(Modifier.width(14.dp))
                        Column(Modifier.weight(1f)) {
                            Text(
                                node.name + (node.version?.let { "  $it" } ?: ""),
                                color = Color.White, fontWeight = FontWeight.Medium, fontSize = 15.sp,
                                maxLines = 1, overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                nodeSubtitle(node),
                                color = if (node.capabilities.contains(RepositoryNode.Capability.INSTALL))
                                    Smarted.TextLight else Color(0xFFFFC9A3),
                                fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                            )
                        }
                        node.compatibility?.let { CompatBadge(it) }
                    }
                }
            }
        }
    }
}

private fun nodeIcon(node: RepositoryNode): ImageVector = when (node.type) {
    RepoNodeType.REPOSITORY -> Icons.Rounded.Storage
    RepoNodeType.CATEGORY -> Icons.Rounded.Category
    RepoNodeType.FOLDER -> Icons.Rounded.Folder
    RepoNodeType.FILE -> Icons.Rounded.Description
    RepoNodeType.ADDON -> Icons.Rounded.Extension
    RepoNodeType.UNKNOWN -> Icons.Rounded.HelpOutline
}

private fun nodeSubtitle(node: RepositoryNode): String = when (node.type) {
    RepoNodeType.CATEGORY -> "${node.children.size} add-ons"
    RepoNodeType.REPOSITORY -> "${node.metadata["addons"] ?: "?"} add-ons · ${node.metadata["categorias"]} categorias"
    RepoNodeType.ADDON -> listOfNotNull(
        kindLabelFromMetadata(node.metadata["kind"]),
        node.compatibility?.let { compatLabel(it) },
        if (node.isInstallable) "pacote disponível" else "sem pacote",
    ).joinToString(" · ")
    else -> node.path
}

private fun kindLabelFromMetadata(raw: String?): String? =
    raw?.let { runCatching { AddonKind.valueOf(it) }.getOrNull() }?.let { kindLabel(it) }

// ───────────────────────── instalar de ZIP ─────────────────────────

@Composable
private fun InstallZipTab(onBrowseZip: () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        EmptyState(
            message = "Instalar um add-on a partir de ZIP",
            hint = "O app lê addon.xml, confere dependências e compatibilidade antes de extrair. " +
                "Nada é executado sem a sua confirmação.",
            icon = Icons.Rounded.FolderZip,
        )
        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
            SmallAction(Icons.Rounded.UploadFile, "Escolher arquivo .zip", onBrowseZip)
        }
    }
}

// ───────────────────────── diálogos ─────────────────────────

@Composable
private fun PendingDialog(
    pending: AddonInstaller.Result,
    onConfirm: (Boolean) -> Unit,
    onCancel: () -> Unit,
) {
    val addon = pending.installed
    Dialog(onDismissRequest = onCancel) {
        Column(
            Modifier.width(600.dp).clip(RoundedCornerShape(22.dp)).background(Color.White).padding(26.dp),
        ) {
            Text(addon?.name ?: "Pacote recusado", color = Smarted.InkOnWhite,
                fontWeight = FontWeight.Bold, fontSize = 19.sp)
            Spacer(Modifier.height(10.dp))
            addon?.let { a ->
                InfoRow("ID", a.id)
                InfoRow("Versão", a.version)
                InfoRow("Tipo", kindLabel(a.kind))
                InfoRow("Ponto de extensão", a.extensionPoint.ifBlank { "—" })
                InfoRow("Compatibilidade", compatLabel(a.compatibility))
                if (a.dependencies.isNotEmpty()) InfoRow("Dependências", a.dependencies.joinToString(", "))
                if (a.missingDependencies.isNotEmpty())
                    InfoRow("Ausentes", a.missingDependencies.joinToString(", "))
            }
            pending.error?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, color = Color(0xFF7A2018), fontSize = 13.sp)
            }
            pending.warnings.forEach {
                Text("⚠ $it", color = Color(0xFF7A5A18), fontSize = 12.sp)
            }
            Spacer(Modifier.height(16.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Spacer(Modifier.weight(1f))
                SmallAction(Icons.Rounded.Close, "Cancelar", onCancel)
                if (addon != null) {
                    val incompatible = addon.compatibility == Compatibility.NOT_COMPATIBLE
                    SmallAction(
                        if (incompatible) Icons.Rounded.Warning else Icons.Rounded.Download,
                        if (incompatible) "Instalar só como arquivo" else "Instalar",
                        { onConfirm(incompatible) },
                    )
                }
            }
        }
    }
}

@Composable
private fun AddonDetailDialog(
    addon: AddonInstaller.Installed,
    files: List<String>,
    onClose: () -> Unit,
    onUninstall: (String) -> Unit,
    onOpen: () -> Unit,
) {
    Dialog(onDismissRequest = onClose) {
        Column(
            Modifier.width(680.dp).heightIn(max = 600.dp)
                .clip(RoundedCornerShape(22.dp)).background(Color.White).padding(26.dp),
        ) {
            Text("${addon.name}  ${addon.version}", color = Smarted.InkOnWhite,
                fontWeight = FontWeight.Bold, fontSize = 19.sp)
            Spacer(Modifier.height(10.dp))
            InfoRow("ID", addon.id)
            InfoRow("Tipo", kindLabel(addon.kind))
            InfoRow("Compatibilidade", compatLabel(addon.compatibility))
            InfoRow("Extensão", addon.extensionPoint.ifBlank { "—" })
            InfoRow("Pasta", addon.directory)
            if (addon.missingDependencies.isNotEmpty())
                InfoRow("Dependências ausentes", addon.missingDependencies.joinToString(", "))
            Spacer(Modifier.height(10.dp))
            Text("Arquivos instalados (${files.size})", color = Smarted.InkMuted, fontSize = 12.sp)
            LazyColumn(Modifier.weight(1f)) {
                items(files) { f ->
                    Text(f.substringAfter(addon.directory).trimStart('/'), color = Smarted.InkOnWhite,
                        fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(vertical = 1.dp))
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SmallAction(Icons.Rounded.Delete, "Desinstalar", { onUninstall(addon.id) })
                if (addon.compatibility == Compatibility.COMPATIBLE ||
                    addon.compatibility == Compatibility.COMPATIBLE_WITH_ADAPTATION
                ) {
                    SmallAction(Icons.Rounded.PlayArrow, "Abrir add-on", onOpen)
                }
                Spacer(Modifier.weight(1f))
                SmallAction(Icons.Rounded.Close, "Fechar", onClose)
            }
        }
    }
}

// ───────────────────────── componentes pequenos ─────────────────────────

@Composable
private fun CompatBadge(level: Compatibility) {
    val (bg, fg, text) = when (level) {
        Compatibility.COMPATIBLE -> Triple(Color(0xFF2E7D32), Color.White, "executável")
        Compatibility.COMPATIBLE_WITH_ADAPTATION -> Triple(Color(0xFFF9A825), Color.Black, "requer adaptação")
        Compatibility.PARTIAL -> Triple(Color(0xFF6D4C41), Color.White, "parcial")
        Compatibility.NOT_COMPATIBLE -> Triple(Color(0xFFB3261E), Color.White, "não compatível")
    }
    Box(Modifier.clip(RoundedCornerShape(10.dp)).background(bg).padding(horizontal = 10.dp, vertical = 5.dp)) {
        Text(text, color = fg, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun SmallChip(label: String, active: Boolean, onClick: () -> Unit) {
    val shape = RoundedCornerShape(12.dp)
    Box(
        Modifier.clip(shape).background(if (active) Smarted.CardOnWhite else Color(0xFFEDEDED))
            .border(1.dp, if (active) Color.Transparent else Color(0x14000000), shape)
            .clickable(onClick = onClick).padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(label, color = if (active) Color.White else Smarted.InkOnWhite, fontSize = 12.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Normal)
    }
}

@Composable
private fun SmallAction(icon: ImageVector, label: String, onClick: () -> Unit) {
    val shape = RoundedCornerShape(13.dp)
    Row(
        Modifier.clip(shape).background(Color(0xFFEDEDED)).border(1.dp, Color(0x14000000), shape)
            .clickable(onClick = onClick).padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, label, tint = Smarted.InkOnWhite, modifier = Modifier.size(17.dp))
        Spacer(Modifier.width(6.dp))
        Text(label, color = Smarted.InkOnWhite, fontSize = 13.sp)
    }
}

@Composable
private fun MessageCard(text: String, isError: Boolean, onDismiss: () -> Unit) {
    val bg = if (isError) Color(0xFFFDECEA) else Color(0xFFEFF7EE)
    val fg = if (isError) Color(0xFF7A2018) else Color(0xFF1F5F2A)
    Row(
        Modifier.fillMaxWidth().padding(vertical = 5.dp).clip(RoundedCornerShape(13.dp))
            .background(bg).padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text, color = fg, fontSize = 12.sp, modifier = Modifier.weight(1f))
        Icon(Icons.Rounded.Close, "Fechar", tint = fg,
            modifier = Modifier.size(16.dp).clickable(onClick = onDismiss))
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text("$label:", color = Smarted.InkMuted, fontSize = 12.sp, modifier = Modifier.width(140.dp))
        Text(value, color = Smarted.InkOnWhite, fontSize = 12.sp, maxLines = 4, overflow = TextOverflow.Ellipsis)
    }
}

private fun kindLabel(kind: AddonKind): String = when (kind) {
    AddonKind.VIDEO -> "Vídeo"
    AddonKind.AUDIO -> "Música"
    AddonKind.PROGRAM -> "Programa"
    AddonKind.SKIN -> "Skin"
    AddonKind.METADATA -> "Metadados"
    AddonKind.SERVICE -> "Serviço"
    AddonKind.SUBTITLE -> "Legendas"
    AddonKind.REPOSITORY -> "Repositório"
    AddonKind.MODULE -> "Módulo Python"
    AddonKind.MODULE_LIB -> "Biblioteca"
    AddonKind.UNKNOWN -> "Desconhecido"
}

private fun kindIcon(kind: AddonKind): ImageVector = when (kind) {
    AddonKind.VIDEO -> Icons.Rounded.Movie
    AddonKind.AUDIO -> Icons.Rounded.LibraryMusic
    AddonKind.PROGRAM -> Icons.Rounded.Apps
    AddonKind.SKIN -> Icons.Rounded.Palette
    AddonKind.METADATA -> Icons.Rounded.Info
    AddonKind.SERVICE -> Icons.Rounded.SettingsSuggest
    AddonKind.SUBTITLE -> Icons.Rounded.Subtitles
    AddonKind.REPOSITORY -> Icons.Rounded.Storage
    AddonKind.MODULE, AddonKind.MODULE_LIB -> Icons.Rounded.Code
    AddonKind.UNKNOWN -> Icons.Rounded.HelpOutline
}

private fun compatLabel(level: Compatibility): String = when (level) {
    Compatibility.COMPATIBLE -> "compatível"
    Compatibility.COMPATIBLE_WITH_ADAPTATION -> "requer adaptação (Python/xbmc*)"
    Compatibility.PARTIAL -> "parcial"
    Compatibility.NOT_COMPATIBLE -> "não compatível"
}
