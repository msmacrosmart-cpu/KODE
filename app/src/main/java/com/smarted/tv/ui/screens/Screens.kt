package com.smarted.tv.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.smarted.tv.ui.components.*
import com.smarted.tv.ui.theme.Smarted

@Composable
fun CanaisScreen(channels: List<MediaItem>, onOpen: (MediaItem) -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Canais")
    ListRows(channels, "Nenhum canal carregado", Icons.Rounded.LiveTv, onOpen)
}

@Composable
fun FilmesScreen(movies: List<MediaItem>, onOpen: (MediaItem) -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Filmes")
    PosterGrid(movies, "Nenhum filme carregado", onOpen)
}

@Composable
fun SeriesScreen(series: List<MediaItem>, onOpen: (MediaItem) -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Séries")
    PosterGrid(series, "Nenhuma série carregada", onOpen)
}

private data class Tile(val label: String, val icon: ImageVector, val action: String)

@Composable
fun NavegarScreen(onAction: (String) -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Navegar")
    val tiles = listOf(
        Tile("Addons", Icons.Rounded.Extension, "screen:addons"),
        Tile("Arquivos", Icons.Rounded.Folder, "screen:arquivos"),
        Tile("Configurações", Icons.Rounded.Settings, "screen:configuracoes"),
    )
    LazyVerticalGrid(
        columns = GridCells.Adaptive(220.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        modifier = Modifier.fillMaxSize(),
    ) {
        gridItems(tiles, key = { it.label }) { t ->
            FocusCard(Modifier.fillMaxWidth().height(150.dp), { onAction(t.action) }) {
                Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(t.icon, null, tint = Color.White, modifier = Modifier.size(48.dp))
                    Spacer(Modifier.height(10.dp))
                    Text(t.label, color = Smarted.TextLight, fontWeight = FontWeight.Medium, fontSize = 18.sp)
                }
            }
        }
    }
}

@Composable
fun AddonsScreen(addons: List<MediaItem>, onOpen: (MediaItem) -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Addons")
    ListRows(addons, "Nenhum addon instalado", Icons.Rounded.Extension, onOpen)
}

@Composable
fun ArquivosScreen(files: List<MediaItem>, onOpen: (MediaItem) -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Arquivos")
    ListRows(files, "Nenhuma pasta ou arquivo", Icons.Rounded.Folder, onOpen)
}

data class SettingsInfo(
    val account: String = "—",
    val server: String = "—",
    val expiration: String = "—",
    val epgStatus: String = "—",
)

@Composable
fun ConfiguracoesScreen(info: SettingsInfo, onUpdateEpg: () -> Unit) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Configurações")
    val rows = listOf(
        MediaItem("account", "Conta", info.account),
        MediaItem("server", "Servidor", info.server),
        MediaItem("exp", "Expiração", info.expiration),
        MediaItem("epg", "Atualizar EPG", info.epgStatus),
    )
    ListRows(rows, "", Icons.Rounded.Settings) { if (it.id == "epg") onUpdateEpg() }
}

@Composable
fun SairDialog(onConfirm: () -> Unit, onDismiss: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        FocusCard(Modifier.width(420.dp), {}) {
            Column(Modifier.padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("Sair do aplicativo?", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 22.sp)
                Spacer(Modifier.height(24.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    FocusCard(Modifier.weight(1f).height(64.dp), onDismiss) {
                        Text("Cancelar", color = Color.White, fontSize = 18.sp, modifier = Modifier.align(Alignment.Center))
                    }
                    FocusCard(Modifier.weight(1f).height(64.dp), onConfirm) {
                        Text("Sair", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp,
                            modifier = Modifier.align(Alignment.Center))
                    }
                }
            }
        }
    }
}
