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
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LiveTv
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Tv
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smarted.tv.data.model.LiveChannel
import com.smarted.tv.ui.components.SmartEDFocusable
import com.smarted.tv.ui.components.TvNavigationRail
import com.smarted.tv.ui.player.PlayerActivity
import com.smarted.tv.ui.theme.SmartEDColors
import com.smarted.tv.ui.xmlengine.LayoutLoader
import com.smarted.tv.ui.xmlengine.SmartLayoutScreen
import com.smarted.tv.viewmodel.MainTvViewModel

/**
 * Tela principal.
 *
 * Layout: vem de assets/layout/home.xml (motor XML). Se o XML falhar,
 * cai automaticamente para as telas nativas (fallback) — nunca fica preta.
 */
@Composable
fun AppScreen(vm: MainTvViewModel) {
    val context = LocalContext.current
    val state by vm.uiState.collectAsState()

    // Carrega o layout uma vez por Activity (não a cada recomposição)
    val loaded = remember { LayoutLoader.load(context, "home.xml") }
    val layout = loaded.layout

    val useXmlLayout = loaded.error == null || layout.screens.isNotEmpty()

    if (useXmlLayout && layout.screens.isNotEmpty()) {
        SmartLayoutScreen(
            layout = layout,
            screenKey = state.currentScreenKey,
            onNavigate = { action ->
                when {
                    action.startsWith("screen:") -> vm.setScreen(action.removePrefix("screen:"))
                    action.startsWith("play:") -> {
                        val url = action.removePrefix("play:")
                        context.startActivity(PlayerActivity.intent(context, url, "SmartED-TV"))
                    }
                    action == "exit" -> vm.setScreen("sair")
                    else -> Unit
                }
            },
        )
        if (state.currentScreenKey == "sair") {
            ExitOverlay()
        }
    } else {
        NativeFallbackScreen(vm = vm, layoutError = loaded.error, layoutSource = loaded.source)
    }
}

@Composable
private fun ExitOverlay() {
    Box(
        modifier = Modifier.fillMaxSize().background(Color(0xE6000000)),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "Sair do SmartED-TV?",
                color = SmartEDColors.TextPrimary,
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                text = "Pressione VOLTAR no controle para fechar.",
                color = SmartEDColors.TextSecondary,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  FALLBACK NATIVO — usado só se o XML não existir/estiver inválido
// ═══════════════════════════════════════════════════════════════════════

@Composable
private fun NativeFallbackScreen(
    vm: MainTvViewModel,
    layoutError: String? = null,
    layoutSource: String = "embutido",
) {
    val context = LocalContext.current
    val selectedIndex by vm.selectedIndex.collectAsState()
    val channels by vm.channels.collectAsState()
    val movies by vm.movies.collectAsState()
    val series by vm.series.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(SmartEDColors.Background)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
                .background(SmartEDColors.Surface)
                .padding(start = 20.dp, end = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Default.Tv, contentDescription = null, tint = SmartEDColors.Coral, modifier = Modifier.size(28.dp))
            Text(
                text = "SmartED-TV",
                color = SmartEDColors.TextPrimary,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(start = 10.dp),
            )
            Spacer(Modifier.weight(1f))
            IconButton(onClick = { vm.selectIndex(6) }) {
                Icon(Icons.Default.Menu, contentDescription = "Menu", tint = SmartEDColors.TextPrimary)
            }
        }

        Row(modifier = Modifier.weight(1f).fillMaxSize()) {
            TvNavigationRail(
                selectedIndex = selectedIndex,
                onItemClick = { vm.selectIndex(it) },
                modifier = Modifier.fillMaxHeight(),
            )
            Box(Modifier.weight(1f).fillMaxHeight().padding(24.dp)) {
                when (selectedIndex) {
                    1 -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(channels, key = { it.id }) { ch ->
                            ListRow(ch.number.toString() + " • " + ch.name, ch.category) {
                                ch.streamUrl?.let { url ->
                                    context.startActivity(PlayerActivity.intent(context, url, ch.name))
                                }
                            }
                        }
                    }
                    2 -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(movies, key = { it.id }) { m ->
                            ListRow(m.title, "${m.year} • ${m.genre}") { }
                        }
                    }
                    3 -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(series, key = { it.id }) { s ->
                            ListRow(s.title, "${s.year} • ${s.seasons} temporadas") { }
                        }
                    }
                    else -> Column {
                        Text("Bem-vindo ao SmartED-TV", color = SmartEDColors.TextPrimary, style = MaterialTheme.typography.headlineMedium)
                        Text(
                            "Layout em XML indisponível (${layoutSource}) — usando tela nativa de segurança.",
                            color = SmartEDColors.TextSecondary,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        if (layoutError != null) {
                            Text(
                                "Detalhe: $layoutError",
                                color = SmartEDColors.TextSecondary,
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ListRow(title: String, subtitle: String, onClick: () -> Unit) {
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
            Icon(Icons.Default.LiveTv, contentDescription = null, tint = SmartEDColors.Coral, modifier = Modifier.size(22.dp))
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(title, color = SmartEDColors.TextPrimary, style = MaterialTheme.typography.titleMedium, maxLines = 1)
                Text(subtitle, color = SmartEDColors.TextSecondary, style = MaterialTheme.typography.bodySmall, maxLines = 1)
            }
            Icon(Icons.Default.PlayArrow, contentDescription = null, tint = SmartEDColors.Coral, modifier = Modifier.size(20.dp))
        }
    }
}

@Suppress("unused")
@Composable
private fun InfoLine(text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(Icons.Default.Info, contentDescription = null, tint = SmartEDColors.TextSecondary, modifier = Modifier.size(16.dp))
        Text(text = text, color = SmartEDColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
    }
}

@Suppress("unused")
private fun unusedChannel(ch: LiveChannel) = ch.name
