package com.smarted.tv.ui.components

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.key.*
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smarted.tv.ui.theme.Smarted
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.*

data class SidebarItem(val label: String, val icon: ImageVector)
data class KodiOption(val label: String, val icon: ImageVector, val action: String)

val sidebarItems = listOf(
    SidebarItem("Canais", Icons.Rounded.LiveTv),
    SidebarItem("Filmes", Icons.Rounded.Movie),
    SidebarItem("Séries", Icons.Rounded.Theaters),
    SidebarItem("Navegar", Icons.Rounded.ShowChart),
)

/**
 * Todas as opções do menu estilo Kodi (home do Kodi).
 * Ordem equivalente à tela inicial do Kodi: Vídeos, Música, Programas, Rádio,
 * Jogos, Imagens, Clima, Favoritos + Add-ons, Arquivos, Configurações, Sair.
 */
val kodiOptions = listOf(
    KodiOption("Vídeos", Icons.Rounded.Movie, "screen:videos"),
    KodiOption("Música", Icons.Rounded.LibraryMusic, "screen:musica"),
    KodiOption("Programas", Icons.Rounded.Apps, "screen:programas"),
    KodiOption("Rádio", Icons.Rounded.Radio, "screen:radio"),
    KodiOption("Jogos", Icons.Rounded.SportsEsports, "screen:jogos"),
    KodiOption("Imagens", Icons.Rounded.Image, "screen:imagens"),
    KodiOption("Clima", Icons.Rounded.WbSunny, "screen:clima"),
    KodiOption("Favoritos", Icons.Rounded.Star, "screen:favoritos"),
    KodiOption("Add-ons", Icons.Rounded.Extension, "screen:addons"),
    KodiOption("Arquivos", Icons.Rounded.Folder, "screen:arquivos"),
    KodiOption("Configurações", Icons.Rounded.Settings, "screen:configuracoes"),
    KodiOption("Sair", Icons.Rounded.PowerSettingsNew, "exit"),
)

/**
 * Casca do layout Smarted-TV: cabeçalho, menu lateral, área branca com curvas
 * e painel Kodi (hambúrguer / tecla MENU). Tudo escalado sobre a referência 1672x941.
 */
@Composable
fun SmartedScaffold(
    selected: Int?,
    onSelect: (Int) -> Unit,
    onKodiOption: (String) -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    var drawerOpen by remember { mutableStateOf(false) }
    BackHandler(enabled = drawerOpen) { drawerOpen = false }

    BoxWithConstraints(
        modifier.fillMaxSize().background(Smarted.Black).onPreviewKeyEvent {
            if (it.key == Key.Menu && it.type == KeyEventType.KeyUp) { drawerOpen = !drawerOpen; true } else false
        }
    ) {
        val d = LocalDensity.current
        // Layout HORIZONTAL (paisagem) desenhado na referência 1672 x 941.
        // sx mantém proporções no eixo horizontal; sy acompanha a altura do aparelho.
        val sx = constraints.maxWidth / Smarted.RefW
        val sy = constraints.maxHeight / Smarted.RefH
        fun px(v: Float) = with(d) { (v * sx).toDp() }
        fun py(v: Float) = with(d) { (v * sy).toDp() }
        fun fs(v: Float) = with(d) { (v * sx).toSp() }

        // Fundo + área branca com as curvas da referência
        Box(Modifier.fillMaxSize().drawBehind {
            drawRect(
                Brush.linearGradient(
                    listOf(Color(0xFF2A2A2A), Smarted.Black, Smarted.Black),
                    start = Offset(0f, 0f), end = Offset(size.width * 0.45f, size.height * 0.25f)
                )
            )
            drawPath(whitePath(size.width, size.height), Color.White)
        })

        // Cabeçalho
        Capsule(Modifier.offset(px(242f), py(14f)).size(px(310f), py(80f))) {
            Text("Smarted-TV", color = Color.White, fontWeight = FontWeight.Bold, fontSize = fs(40f), maxLines = 1)
        }
        Capsule(Modifier.offset(px(970f), py(14f)).size(px(578f), py(80f))) {
            val now by produceState(Date()) { while (true) { value = Date(); delay(1000) } }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    SimpleDateFormat("HH:mm", Locale.getDefault()).format(now),
                    color = Color.White, fontWeight = FontWeight.Bold, fontSize = fs(42f), maxLines = 1
                )
                Spacer(Modifier.width(px(24f)))
                Box(Modifier.width(1.dp).height(py(36f)).background(Smarted.Border))
                Spacer(Modifier.width(px(24f)))
                Text(
                    SimpleDateFormat("EEEE, d 'de' MMMM", Locale("pt", "BR")).format(now)
                        .replaceFirstChar { it.uppercase() },
                    color = Smarted.TextLight, fontSize = fs(25f), maxLines = 1
                )
            }
        }

        // Menu lateral (peça única + 4 botões)
        val menuShape = RoundedCornerShape(px(56f))
        Box(
            Modifier.offset(px(24f), py(56f)).size(px(186f), py(716f)).clip(menuShape)
                .background(Smarted.glassFrosted())
                .border(1.dp, Smarted.Border, menuShape)
        )
        val tops = listOf(82f, 254f, 412f, 570f)
        val heights = listOf(150f, 146f, 146f, 146f)
        sidebarItems.forEachIndexed { i, item ->
            MenuButton(
                item, i == selected, { onSelect(i) },
                Modifier.offset(px(40f), py(tops[i])).size(px(140f), py(heights[i]))
            )
        }

        // Hambúrguer: no espaço preto acima do menu lateral
        Box(
            Modifier.offset(px(94f), py(7f)).size(px(44f), py(44f)).clip(CircleShape)
                .background(Smarted.glass()).border(1.dp, Smarted.Border, CircleShape)
                .focusable().clickable { drawerOpen = true },
            contentAlignment = Alignment.Center
        ) { Icon(Icons.Rounded.Menu, "Menu", tint = Color.White, modifier = Modifier.fillMaxSize(0.6f)) }

        // Conteúdo das telas (dentro da área branca)
        Box(
            Modifier.offset(px(318f), py(174f)).size(px(Smarted.RefW - 318f - 40f), py(Smarted.RefH - 174f - 30f)),
            content = content
        )

        // Painel Kodi
        if (drawerOpen) {
            Box(Modifier.fillMaxSize().background(Color(0x99000000)).clickable { drawerOpen = false })
            val ps = RoundedCornerShape(px(40f))
            Column(
                Modifier.offset(px(24f), py(56f)).width(px(440f)).height(px(830f)).clip(ps)
                    .background(Smarted.glassFrosted())
                    .border(1.dp, Smarted.Border, ps).padding(px(18f)),
                verticalArrangement = Arrangement.spacedBy(py(10f))
            ) {
                Row(
                    Modifier.fillMaxWidth().height(py(56f)).padding(horizontal = px(10f)),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Menu", color = Color.White, fontWeight = FontWeight.Bold, fontSize = fs(26f))
                    Spacer(Modifier.width(px(12f)))
                    Text("Kodi", color = Smarted.TextMuted, fontSize = fs(18f))
                }
                kodiOptions.forEach { opt ->
                    var f by remember { mutableStateOf(false) }
                    val s = RoundedCornerShape(px(28f))
                    Row(
                        Modifier.fillMaxWidth().height(py(62f)).clip(s).background(Smarted.glass())
                            .border(if (f) 2.dp else 1.dp, if (f) Color.White else Smarted.Border, s)
                            .onFocusChanged { f = it.isFocused }
                            .clickable { drawerOpen = false; onKodiOption(opt.action) }
                            .padding(horizontal = px(28f)),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(opt.icon, null, tint = Color.White, modifier = Modifier.size(py(28f)))
                        Spacer(Modifier.width(px(18f)))
                        Text(opt.label, color = Smarted.TextLight, fontWeight = FontWeight.Medium, fontSize = fs(21f))
                    }
                }
            }
        }
    }
}

private fun whitePath(w: Float, h: Float): Path {
    val sx = w / Smarted.RefW
    val sy = h / Smarted.RefH
    // Mais espaço entre o menu lateral e a área branca (respiro).
    val left = 286f * sx; val top = 148f * sy
    val r1x = 66f * sx; val r1y = 66f * sy
    val menuBottom = 786f * sy
    val lowLeft = 74f * sx
    val r2x = 78f * sx; val r2y = 78f * sy
    return Path().apply {
        moveTo(left + r1x, top)
        lineTo(w, top); lineTo(w, h); lineTo(lowLeft, h)
        lineTo(lowLeft, menuBottom + r2y)
        quadraticBezierTo(lowLeft, menuBottom, lowLeft + r2x, menuBottom)
        lineTo(left - 40f * sx, menuBottom)
        quadraticBezierTo(left, menuBottom, left, menuBottom - 40f * sy)
        lineTo(left, top + r1y)
        quadraticBezierTo(left, top, left + r1x, top)
        close()
    }
}

@Composable
private fun Capsule(modifier: Modifier, content: @Composable () -> Unit) {
    val shape = RoundedCornerShape(50)
    Box(
        modifier.clip(shape)
            .background(Smarted.glassFrosted())
            .border(1.dp, Smarted.Border, shape),
        contentAlignment = Alignment.Center
    ) { content() }
}

@Composable
private fun MenuButton(item: SidebarItem, selected: Boolean, onClick: () -> Unit, modifier: Modifier) {
    val shape = RoundedCornerShape(34.dp)
    var focused by remember { mutableStateOf(false) }
    val borderColor = when {
        focused -> Color.White
        selected -> Smarted.BorderSelected
        else -> Smarted.Border
    }
    Column(
        modifier.clip(shape)
            // glass preto FOSCO: base opaca + brilho no topo bem discreto
            .background(Smarted.glassFrosted())
            .border(if (focused) 2.dp else 1.dp, borderColor, shape)
            .onFocusChanged { focused = it.isFocused }
            .clickable(onClick = onClick),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(item.icon, null, tint = Color.White, modifier = Modifier.fillMaxWidth(0.46f).aspectRatio(1f))
        Spacer(Modifier.height(8.dp))
        Text(item.label, color = Smarted.TextLight, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, maxLines = 1)
    }
}
