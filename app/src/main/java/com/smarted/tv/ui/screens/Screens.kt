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

/**
 * Configurações no padrão Kodi (sem IPTV/Xtream):
 * Interface · Player · Mídia · Sistema · Redes
 */
data class SettingsInfo(
    val skin: String = "Smarted-TV",
    val language: String = "Português (Brasil)",
    val region: String = "Brasil",
    val player: String = "ExoPlayer (Media3)",
    val hardwareAccel: Boolean = true,
    val audioOutput: String = "Auto (HDMI)",
    val subtitles: String = "Português",
    val mediaSources: Int = 2,
    val libraryUpdate: String = "Nunca",
    val cacheSize: String = "Normal",
    val storage: String = "Interno",
    val networkStatus: String = "Conectado",
    val hostname: String = "smarted-tv",
    val internetAccess: Boolean = true,
    val version: String = "1.0.5",
)

/**
 * Configurações no padrão Kodi:
 *  Perfil e conta · Aparência · Player · EPG/Programação · Parental ·
 *  Idioma e região · Armazenamento · Rede · Sobre
 */
@Composable
fun ConfiguracoesScreen(
    info: SettingsInfo,
    onAction: (String) -> Unit = {},
) = Column(Modifier.fillMaxSize()) {
    ScreenTitle("Configurações")
    val rows = listOf(
        // Interface
        MediaItem("interface", "Interface", "${info.skin} • ${info.language}"),
        MediaItem("skin", "Aparência (skin)", info.skin),
        MediaItem("language", "Idioma e região", "${info.language} • ${info.region}"),
        // Player
        MediaItem("player", "Player de vídeo", info.player),
        MediaItem("accel", "Aceleração de hardware", if (info.hardwareAccel) "Ativada" else "Desativada"),
        MediaItem("audio", "Saída de áudio", info.audioOutput),
        MediaItem("subtitles", "Legendas", info.subtitles),
        // Mídia
        MediaItem("mediasources", "Fontes de mídia", "${info.mediaSources} fontes configuradas"),
        MediaItem("library", "Atualizar biblioteca", info.libraryUpdate),
        MediaItem("cache", "Cache de vídeo", info.cacheSize),
        // Sistema
        MediaItem("storage", "Armazenamento", info.storage),
        MediaItem("about", "Sobre o SmartED-TV", "Versão ${info.version}"),
        // Redes
        MediaItem("network", "Rede e internet", info.networkStatus),
        MediaItem("hostname", "Nome do dispositivo", info.hostname),
        MediaItem("internet", "Acesso à internet", if (info.internetAccess) "Permitido" else "Bloqueado"),
    )
    ListRows(rows, "", Icons.Rounded.Settings) { m -> onAction("config:" + m.id) }
}

// ───────────────────────── Telas Kodi (mídia / add-ons) ─────────────────────────

/** Grade de itens (filmes, séries, programas, imagens...). */
@Composable
fun PosterScreen(
    title: String,
    items: List<MediaItem>,
    empty: String,
    onOpen: (MediaItem) -> Unit,
    emptyIcon: ImageVector = Icons.Rounded.Movie,
) = Column(Modifier.fillMaxSize()) {
    ScreenTitle(title)
    PosterGrid(items, empty, onOpen, emptyIcon)
}

/** Lista de itens (canais, rádio, add-ons, arquivos, favoritos...). */
@Composable
fun ListScreen(
    title: String,
    items: List<MediaItem>,
    empty: String,
    icon: ImageVector,
    onOpen: (MediaItem) -> Unit,
) = Column(Modifier.fillMaxSize()) {
    ScreenTitle(title)
    ListRows(items, empty, icon, onOpen)
}

/** Clima — cartão simples (sem API externa por enquanto). */
@Composable
fun ClimaScreen(city: String = "—", temp: String = "—", desc: String = "Clima não configurado") =
    Column(Modifier.fillMaxSize()) {
        ScreenTitle("Clima")
        FocusCard(Modifier.fillMaxWidth().height(180.dp), {}) {
            Row(Modifier.fillMaxSize().padding(28.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.WbSunny, null, tint = Color.White, modifier = Modifier.size(64.dp))
                Spacer(Modifier.width(24.dp))
                Column {
                    Text(city, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 30.sp)
                    Text(temp, color = Color.White, fontSize = 40.sp, fontWeight = FontWeight.Bold)
                    Text(desc, color = Smarted.TextLight, fontSize = 16.sp)
                }
            }
        }
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
