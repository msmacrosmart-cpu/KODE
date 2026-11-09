package com.smarted.tv.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.smarted.tv.ui.components.TvNavigationRail
import com.smarted.tv.ui.theme.SmartEDColors
import com.smarted.tv.ui.theme.SmartEDTheme
import com.smarted.tv.viewmodel.MainTvViewModel

@Composable
fun AppScreen(vm: MainTvViewModel = viewModel { MainTvViewModel() }) {
    var railSelectedIndex by remember { mutableIntStateOf(0) }
    val selectedIndex by vm.selectedIndex.collectAsState()

    if (selectedIndex != railSelectedIndex) {
        railSelectedIndex = selectedIndex
    }

    SmartEDTheme {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = SmartEDColors.Background
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                // ── Header fixo com logo + botão hambúrguer ──
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(64.dp)
                        .padding(start = 20.dp, end = 20.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    // Logo SmartED-TV ao lado do botão hambúrguer
                    Icon(
                        imageVector = androidx.compose.material3.Icons.Default.Television,
                        contentDescription = "Logo SmartED-TV",
                        tint = SmartEDColors.Coral,
                        modifier = Modifier.size(34.dp),
                    )
                    Text(
                        text = "SmartED-TV",
                        style = MaterialTheme.typography.titleLarge,
                        color = SmartEDColors.TextPrimary,
                        modifier = Modifier.padding(start = 10.dp),
                    )

                    Spacer(Modifier.weight(1f))

                    // Botão hambúrguer - abre todas as opções (estilo Kodi)
                    IconButton(onClick = { }) {
                        Icon(
                            imageVector = androidx.compose.material3.Icons.Default.Menu,
                            contentDescription = "Menu de opções",
                            tint = SmartEDColors.TextPrimary,
                        )
                    }
                }

                // ── Corpo: Navigation Rail + Conteúdo ──
                Row(
                    modifier = Modifier.weight(1f).fillMaxSize()
                ) {
                    // Menu lateral (estilo Kodi "navegar")
                    TvNavigationRail(
                        selectedIndex = railSelectedIndex,
                        onItemClick = { index ->
                            railSelectedIndex = index
                            vm.selectIndex(index)
                        },
                        modifier = Modifier.fillMaxHeight(),
                    )

                    // Área de conteúdo principal
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxSize()
                            .padding(start = 24.dp, top = 24.dp, end = 24.dp, bottom = 24.dp),
                    ) {
                        when (railSelectedIndex) {
                            0 -> DashboardScreen(vm)
                            1 -> LiveTvScreen(vm)      // Canais (sem YouTube)
                            2 -> VodScreen(vm)          // Filmes
                            3 -> SeriesScreen(vm)       // Séries
                            4 -> AddonsScreen()         // Addons
                            5 -> ToolsScreen()          // Ferramentas / Navegar pastas
                            6 -> SettingsScreen(vm)     // Configurações (menu TV Eminem)
                            7 -> ExitScreen()           // Sair
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DashboardScreen(vm: MainTvViewModel) {
    val channels by vm.channels.collectAsState()
    val movies by vm.movies.collectAsState()
    val series by vm.series.collectAsState()

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Bem-vindo ao SmartED-TV",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 8.dp),
        )
        Text(
            text = "Seu centro de entretenimento IPTV",
            style = MaterialTheme.typography.bodyMedium,
            color = SmartEDColors.TextSecondary,
            modifier = Modifier.padding(bottom = 32.dp),
        )

        // Cards rápidos
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(16.dp),
        ) {
            QuickCard(
                title = "Canais TV",
                subtitle = "${channels.size} canais ao vivo",
                icon = androidx.compose.material3.Icons.Default.LiveTv,
                color = SmartEDColors.Coral,
            )
            QuickCard(
                title = "Filmes",
                subtitle = "${movies.size} títulos",
                icon = androidx.compose.material3.Icons.Default.Movie,
                color = SmartEDColors.Orange,
            )
            QuickCard(
                title = "Séries",
                subtitle = "${series.size} séries",
                icon = androidx.compose.material3.Icons.Default.TV,
                color = SmartEDColors.Yellow,
            )
        }
    }
}

@Composable
private fun QuickCard(
    title: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: androidx.compose.ui.graphics.Color,
) {
    Box(
        modifier = Modifier
            .weight(1f)
            .height(120.dp)
            .clip(androidx.compose.foundation.shape.RoundedCornerShape(20.dp))
            .background(color.copy(alpha = 0.15f))
            .border(1.dp, color.copy(alpha = 0.4f), androidx.compose.foundation.shape.RoundedCornerShape(20.dp)),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(32.dp),
            )
            Spacer(modifier = androidx.compose.foundation.layout.Spacer(Modifier.height(8.dp)))
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = SmartEDColors.TextPrimary,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = SmartEDColors.TextSecondary,
            )
        }
    }
}

@Composable
private fun LiveTvScreen(vm: MainTvViewModel) {
    val channels by vm.channels.collectAsState()
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Canais TV",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        if (channels.isEmpty()) {
            Text(text = "Nenhum canal disponível", color = SmartEDColors.TextSecondary)
        } else {
            androidx.compose.foundation.lazy.LazyColumn(
                modifier = Modifier.fillMaxWidth(),
            ) {
                items(channels, key = { it.id }) { ch ->
                    ChannelCard(channel = ch)
                }
            }
        }
    }
}

@Composable
private fun ChannelCard(channel: com.smarted.tv.data.model.LiveChannel) {
    androidx.compose.material3.Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
            .width(500.dp),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(64.dp).clip(androidx.compose.foundation.shape.RoundedCornerShape(10.dp)).background(androidx.compose.ui.graphics.Color(0x22FFFFFF)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = androidx.compose.material3.Icons.Default.LiveTv,
                    contentDescription = null,
                    tint = SmartEDColors.Coral,
                    modifier = Modifier.size(32.dp),
                )
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column(Modifier.weight(1f), verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "${channel.number} - ${channel.name}",
                    style = MaterialTheme.typography.titleLarge,
                    color = SmartEDColors.TextPrimary,
                )
                Text(
                    text = channel.category,
                    style = MaterialTheme.typography.bodyMedium,
                    color = SmartEDColors.TextSecondary,
                )
            }
        }
    }
}

@Composable
private fun VodScreen(vm: MainTvViewModel) {
    val movies by vm.movies.collectAsState()
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Filmes",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        if (movies.isEmpty()) {
            Text(text = "Nenhum filme disponível", color = SmartEDColors.TextSecondary)
        } else {
            androidx.compose.foundation.lazy.LazyColumn(
                modifier = Modifier.fillMaxWidth(),
            ) {
                items(movies, key = { it.id }) { m ->
                    MediaCard(
                        title = m.title,
                        subtitle = "${m.year} • ${m.genre} • ${m.durationMin} min",
                        icon = androidx.compose.material3.Icons.Default.Movie,
                        color = SmartEDColors.Orange,
                    )
                }
            }
        }
    }
}

@Composable
private fun SeriesScreen(vm: MainTvViewModel) {
    val series by vm.series.collectAsState()
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Séries",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        if (series.isEmpty()) {
            Text(text = "Nenhuma série disponível", color = SmartEDColors.TextSecondary)
        } else {
            androidx.compose.foundation.lazy.LazyColumn(
                modifier = Modifier.fillMaxWidth(),
            ) {
                items(series, key = { it.id }) { s ->
                    MediaCard(
                        title = s.title,
                        subtitle = "${s.year} • ${s.seasons} temporadas",
                        icon = androidx.compose.material3.Icons.Default.TV,
                        color = SmartEDColors.Yellow,
                    )
                }
            }
        }
    }
}

@Composable
private fun MediaCard(
    title: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: androidx.compose.ui.graphics.Color,
) {
    androidx.compose.material3.Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
            .width(500.dp),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(64.dp).clip(androidx.compose.foundation.shape.RoundedCornerShape(10.dp)).background(color.copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = color,
                    modifier = Modifier.size(32.dp),
                )
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column(Modifier.weight(1f), verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(4.dp)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge,
                    color = SmartEDColors.TextPrimary,
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = SmartEDColors.TextSecondary,
                )
            }
        }
    }
}

@Composable
private fun AddonsScreen() {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Addons",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        Text(text = "Gerencie seus addons aqui", color = SmartEDColors.TextSecondary)
    }
}

@Composable
private fun ToolsScreen() {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Navegar / Ferramentas",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        Text(text = "Navegador de pastas e ferramentas do sistema", color = SmartEDColors.TextSecondary)
    }
}

@Composable
private fun SettingsScreen(vm: MainTvViewModel) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Configurações",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        // Menu de configurações do TV Eminem
        SettingsItem("Conta e Perfil", androidx.compose.material3.Icons.Default.Person) { }
        SettingsItem("Rede e Internet", androidx.compose.material3.Icons.Default.Wifi) { }
        SettingsItem("Player de Vídeo", androidx.compose.material3.Icons.Default.Videocam) { }
        SettingsItem("EPG e Programa", androidx.compose.material3.Icons.Default.Schedule) { }
        SettingsItem("Parental Controls", androidx.compose.material3.Icons.Default.ChildFriendly) { }
        SettingsItem("Aparência e Tema", androidx.compose.material3.Icons.Default.Palette) { }
        SettingsItem("Idioma e Região", androidx.compose.material3.Icons.Default.Language) { }
        SettingsItem("Armazenamento", androidx.compose.material3.Icons.Default.Storage) { }
        SettingsItem("Sobre o Aplicativo", androidx.compose.material3.Icons.Default.Info) { }
    }
}

@Composable
private fun SettingsItem(title: String, icon: androidx.compose.ui.graphics.vector.ImageVector, onClick: () -> Unit) {
    androidx.compose.material3.Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .width(500.dp),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = SmartEDColors.Coral,
                modifier = Modifier.size(28.dp),
            )
            Spacer(modifier = Modifier.width(16.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = SmartEDColors.TextPrimary,
                modifier = Modifier.weight(1f),
            )
            Icon(
                imageVector = androidx.compose.material3.Icons.Default.NavigateNext,
                contentDescription = null,
                tint = SmartEDColors.TextSecondary,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun ExitScreen() {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "Sair",
            style = MaterialTheme.typography.headlineLarge,
            color = SmartEDColors.TextPrimary,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        Text(text = "Deseja encerrar o aplicativo?", color = SmartEDColors.TextSecondary)
    }
}
