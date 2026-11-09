package com.smarted.tv.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.LiveTv
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.NavigateNext
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Tv
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smarted.tv.data.model.LiveChannel
import com.smarted.tv.ui.components.SmartEDFocusable
import com.smarted.tv.ui.components.TvNavigationRail
import com.smarted.tv.ui.player.PlayerActivity
import com.smarted.tv.ui.theme.SmartEDColors
import com.smarted.tv.ui.theme.SmartEDTheme
import com.smarted.tv.viewmodel.MainTvViewModel

@Composable
fun AppScreen(vm: MainTvViewModel = MainTvViewModel()) {
    val context = LocalContext.current
    val selectedIndex by vm.selectedIndex.collectAsState()

    SmartEDTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = SmartEDColors.Background) {
            Column(modifier = Modifier.fillMaxSize()) {
                // ── Header fixo com logo + botão hambúrguer ──
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(64.dp)
                        .background(SmartEDColors.Surface)
                        .padding(start = 20.dp, end = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Default.Tv,
                        contentDescription = "Logo SmartED-TV",
                        tint = SmartEDColors.Coral,
                        modifier = Modifier.size(30.dp),
                    )
                    Text(
                        text = "SmartED-TV",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = SmartEDColors.TextPrimary,
                        modifier = Modifier.padding(start = 10.dp),
                    )

                    Spacer(Modifier.weight(1f))

                    // Botão hambúrguer - abre todas as opções (estilo Kodi)
                    IconButton(onClick = { vm.selectIndex(6) }) {
                        Icon(
                            imageVector = Icons.Default.Menu,
                            contentDescription = "Menu de opções",
                            tint = SmartEDColors.TextPrimary,
                        )
                    }
                }

                // ── Corpo: Navigation Rail + Conteúdo ──
                Row(modifier = Modifier.weight(1f).fillMaxSize()) {
                    TvNavigationRail(
                        selectedIndex = selectedIndex,
                        onItemClick = { index -> vm.selectIndex(index) },
                        modifier = Modifier.fillMaxHeight(),
                    )

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .padding(horizontal = 28.dp, vertical = 20.dp),
                    ) {
                        when (selectedIndex) {
                            0 -> DashboardScreen(
                                onOpenChannels = { vm.selectIndex(1) },
                                onOpenMovies = { vm.selectIndex(2) },
                                onOpenSeries = { vm.selectIndex(3) },
                            )
                            1 -> LiveTvScreen(
                                vm = vm,
                                onPlay = { channel ->
                                    channel.streamUrl?.let { url ->
                                        context.startActivity(
                                            PlayerActivity.intent(context, url, channel.name)
                                        )
                                    }
                                },
                            )
                            2 -> VodScreen(vm)
                            3 -> SeriesScreen(vm)
                            4 -> AddonsScreen()
                            5 -> ToolsScreen()
                            6 -> SettingsScreen(vm)
                            else -> ExitScreen()
                        }
                    }
                }
            }
        }
    }
}

// ───────────────────────────── Dashboard ─────────────────────────────

@Composable
private fun DashboardScreen(
    onOpenChannels: () -> Unit,
    onOpenMovies: () -> Unit,
    onOpenSeries: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            text = "Bem-vindo ao SmartED-TV",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = SmartEDColors.TextPrimary,
        )
        Text(
            text = "Seu centro de entretenimento IPTV",
            style = MaterialTheme.typography.bodyMedium,
            color = SmartEDColors.TextSecondary,
            modifier = Modifier.padding(top = 4.dp, bottom = 28.dp),
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            QuickCard(
                title = "Canais TV",
                subtitle = "Ao vivo",
                icon = Icons.Default.LiveTv,
                color = SmartEDColors.Coral,
                onClick = onOpenChannels,
                modifier = Modifier.weight(1f),
            )
            QuickCard(
                title = "Filmes",
                subtitle = "VOD",
                icon = Icons.Default.Movie,
                color = SmartEDColors.Orange,
                onClick = onOpenMovies,
                modifier = Modifier.weight(1f),
            )
            QuickCard(
                title = "Séries",
                subtitle = "Temporadas",
                icon = Icons.Default.Tv,
                color = SmartEDColors.Yellow,
                onClick = onOpenSeries,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun QuickCard(
    title: String,
    subtitle: String,
    icon: ImageVector,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    SmartEDFocusable(
        onClick = onClick,
        modifier = modifier.height(140.dp),
        shape = RoundedCornerShape(20.dp),
        idleColor = color.copy(alpha = 0.15f),
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(34.dp))
            Spacer(Modifier.height(10.dp))
            Text(title, style = MaterialTheme.typography.titleMedium, color = SmartEDColors.TextPrimary)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = SmartEDColors.TextSecondary)
        }
    }
}

// ───────────────────────────── Canais ─────────────────────────────

@Composable
private fun LiveTvScreen(vm: MainTvViewModel, onPlay: (LiveChannel) -> Unit) {
    val channels by vm.channels.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Canais TV", "${channels.size} canais disponíveis")
        if (channels.isEmpty()) {
            EmptyState("Nenhum canal disponível")
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(channels, key = { it.id }) { channel ->
                    ListRow(
                        icon = Icons.Default.LiveTv,
                        color = SmartEDColors.Coral,
                        title = "${channel.number} • ${channel.name}",
                        subtitle = channel.category,
                        trailing = { Icon(Icons.Default.PlayArrow, contentDescription = "Assistir", tint = SmartEDColors.Coral) },
                        onClick = { onPlay(channel) },
                    )
                }
            }
        }
    }
}

// ───────────────────────────── Filmes / Séries ─────────────────────────────

@Composable
private fun VodScreen(vm: MainTvViewModel) {
    val movies by vm.movies.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Filmes", "${movies.size} títulos no catálogo")
        if (movies.isEmpty()) {
            EmptyState("Nenhum filme disponível")
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(movies, key = { it.id }) { movie ->
                    ListRow(
                        icon = Icons.Default.Movie,
                        color = SmartEDColors.Orange,
                        title = movie.title,
                        subtitle = "${movie.year} • ${movie.genre} • ${movie.durationMin} min",
                        onClick = { },
                    )
                }
            }
        }
    }
}

@Composable
private fun SeriesScreen(vm: MainTvViewModel) {
    val series by vm.series.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Séries", "${series.size} séries no catálogo")
        if (series.isEmpty()) {
            EmptyState("Nenhuma série disponível")
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(series, key = { it.id }) { serie ->
                    ListRow(
                        icon = Icons.Default.Tv,
                        color = SmartEDColors.Yellow,
                        title = serie.title,
                        subtitle = "${serie.year} • ${serie.seasons} temporadas",
                        onClick = { },
                    )
                }
            }
        }
    }
}

// ───────────────────────────── Addons / Pastas ─────────────────────────────

@Composable
private fun AddonsScreen() {
    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Addons", "Extensões instaladas")
        EmptyState("Gerencie seus addons aqui")
    }
}

@Composable
private fun ToolsScreen() {
    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Navegar / Ferramentas", "Navegador de pastas e ferramentas do sistema")
        ListRow(
            icon = Icons.Default.Folder,
            color = SmartEDColors.Success,
            title = "Armazenamento interno",
            subtitle = "Navegar por arquivos locais",
            onClick = { },
        )
    }
}

// ───────────────────────────── Configurações ─────────────────────────────

@Composable
private fun SettingsScreen(vm: MainTvViewModel) {
    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Configurações", "Menu completo (TV Eminem)")

        LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            item { SettingsItem("Conta e Perfil", Icons.Default.Person) }
            item { SettingsItem("Rede e Internet", Icons.Default.Wifi) }
            item { SettingsItem("Player de Vídeo", Icons.Default.Videocam) }
            item { SettingsItem("EPG e Programa", Icons.Default.Schedule) }
            item { SettingsItem("Parental Controls", Icons.Default.ChildCare) }
            item { SettingsItem("Aparência e Tema", Icons.Default.Palette) }
            item { SettingsItem("Idioma e Região", Icons.Default.Language) }
            item { SettingsItem("Armazenamento", Icons.Default.Storage) }
            item { SettingsItem("Sobre o Aplicativo", Icons.Default.Info) }
            item { SettingsItem("Sair do aplicativo", Icons.Default.NavigateNext) { vm.selectIndex(7) } }
        }
    }
}

@Composable
private fun SettingsItem(title: String, icon: ImageVector, onClick: () -> Unit = {}) {
    ListRow(
        icon = icon,
        color = SmartEDColors.Coral,
        title = title,
        subtitle = "",
        trailing = {
            Icon(
                imageVector = Icons.Default.NavigateNext,
                contentDescription = null,
                tint = SmartEDColors.TextSecondary,
            )
        },
        onClick = onClick,
    )
}

// ───────────────────────────── Sair ─────────────────────────────

@Composable
private fun ExitScreen() {
    Column(modifier = Modifier.fillMaxSize()) {
        ScreenTitle("Sair", "Deseja encerrar o aplicativo?")
        Text(
            text = "Pressione VOLTAR para sair.",
            color = SmartEDColors.TextSecondary,
        )
    }
}

// ───────────────────────────── Componentes base ─────────────────────────────

@Composable
private fun ScreenTitle(title: String, subtitle: String) {
    Column(modifier = Modifier.padding(bottom = 20.dp)) {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = SmartEDColors.TextPrimary,
        )
        Text(text = subtitle, style = MaterialTheme.typography.bodySmall, color = SmartEDColors.TextSecondary)
    }
}

@Composable
private fun EmptyState(message: String) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(text = message, color = SmartEDColors.TextSecondary)
    }
}

@Composable
private fun ListRow(
    icon: ImageVector,
    color: Color,
    title: String,
    subtitle: String,
    trailing: (@Composable () -> Unit)? = null,
    onClick: () -> Unit,
) {
    SmartEDFocusable(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().height(72.dp),
        shape = RoundedCornerShape(14.dp),
        focusScale = 1.01f,
        idleColor = SmartEDColors.Surface,
    ) {
        Row(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(color.copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(22.dp))
            }
            Spacer(Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    color = SmartEDColors.TextPrimary,
                    maxLines = 1,
                )
                if (subtitle.isNotEmpty()) {
                    Text(
                        text = subtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = SmartEDColors.TextSecondary,
                        maxLines = 1,
                    )
                }
            }
            trailing?.invoke()
        }
    }
}
