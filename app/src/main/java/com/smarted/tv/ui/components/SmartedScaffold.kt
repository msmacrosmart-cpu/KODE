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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smarted.tv.ui.theme.Smarted
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class SidebarItem(val label: String, val icon: ImageVector)
data class KodiOption(val label: String, val icon: ImageVector, val action: String)

val sidebarItems = listOf(
    SidebarItem("Canais", Icons.Rounded.LiveTv),
    SidebarItem("Filmes", Icons.Rounded.Movie),
    SidebarItem("Séries", Icons.Rounded.LocalMovies),
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
 * Casca do layout Smarted-TV — composição do pacote `SmartedTV_Kotlin_Recriacao`
 * (docs/referencia-nova-tela.png).
 *
 * Estrutura da referência (1536 x 864):
 *  - fundo grafite/preto com brilho diagonal e um painel inclinado;
 *  - cápsula da marca (esquerda) e cápsula de relógio/data em português;
 *  - trilho único de navegação com os 4 botões (Canais, Filmes, Séries, Navegar);
 *  - área branca com curva grande no canto superior esquerdo + extensão inferior
 *    que contorna o trilho, exatamente como na imagem.
 *
 * O conteúdo das telas é desenhado dentro da área branca, respeitando as margens
 * da curva — sem cobrir o trilho nem a faixa de respiro.
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
        modifier
            .fillMaxSize()
            .background(Smarted.Black)
            .onPreviewKeyEvent {
                if (it.key == Key.Menu && it.type == KeyEventType.KeyUp) {
                    drawerOpen = !drawerOpen
                    true
                } else false
            }
    ) {
        val d = LocalDensity.current
        // Escala da referência 1536 x 864, proporcional nos dois eixos.
        val sx = constraints.maxWidth / Smarted.RefW
        val sy = constraints.maxHeight / Smarted.RefH
        fun px(v: Float) = with(d) { (v * sx).toDp() }
        fun py(v: Float) = with(d) { (v * sy).toDp() }
        fun fs(v: Float) = with(d) { (v * sx).toSp() }

        // ── Fundo: gradiente diagonal + painel grafite inclinado ──
        Box(Modifier.fillMaxSize().drawBehind {
            drawRect(
                Brush.linearGradient(
                    colorStops = arrayOf(
                        0f to Smarted.BackdropStart,
                        0.38f to Smarted.BackdropMid,
                        1f to Smarted.BackdropEnd,
                    ),
                    start = Offset(0f, 0f),
                    end = Offset(size.width, size.height),
                )
            )
            // painel inclinado (o "brilho" diagonal da referência)
            val panel = Path().apply {
                moveTo(size.width * 0.36f, 0f)
                lineTo(size.width * 0.55f, 0f)
                lineTo(size.width * 0.44f, size.height * 0.34f)
                lineTo(size.width * 0.30f, size.height * 0.34f)
                close()
            }
            drawPath(panel, Color(0x16000000))
            // área branca com as duas curvas da referência
            drawPath(whitePath(size.width, size.height), Color(0xFFFEFEFE))
        })

        // ── Cápsula da marca ──
        Capsule(Modifier.offset(px(221f), py(12f)).size(px(287f), py(76f))) {
            Text(
                "Smarted-TV",
                color = Color(0xFFF7F7F7),
                fontWeight = FontWeight.Bold,
                fontSize = fs(37f),
                maxLines = 1,
            )
        }

        // ── Cápsula de relógio e data (pt-BR, atualizados) ──
        Capsule(Modifier.offset(px(890f), py(12f)).size(px(535f), py(76f))) {
            val now by produceState(Date()) {
                while (true) {
                    value = Date()
                    delay(15_000)
                }
            }
            val locale = Locale("pt", "BR")
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    SimpleDateFormat("HH:mm", locale).format(now),
                    color = Color.White, fontWeight = FontWeight.Bold, fontSize = fs(38f), maxLines = 1,
                )
                Spacer(Modifier.width(px(23f)))
                Box(Modifier.width(1.dp).height(py(38f)).background(Color(0xFF777777)))
                Spacer(Modifier.width(px(23f)))
                Text(
                    SimpleDateFormat("EEEE, d 'de' MMMM", locale).format(now)
                        .replaceFirstChar { if (it.isLowerCase()) it.titlecase(locale) else it.toString() },
                    color = Color(0xFFF0F0F0), fontSize = fs(22f), fontWeight = FontWeight.Medium,
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
        }

        // ── Trilho único de navegação ──
        val railShape = RoundedCornerShape(px(48f))
        Box(
            Modifier.offset(px(23f), py(52f))
                .size(px(167f), py(648f))
                .clip(railShape)
                .background(
                    Brush.verticalGradient(
                        listOf(Smarted.RailTop, Smarted.RailMid, Smarted.RailBottom)
                    )
                )
                .border(1.dp, Smarted.RailBorder, railShape)
        )
        Column(
            modifier = Modifier.offset(px(37f), py(87f)).width(px(122f)),
            verticalArrangement = Arrangement.spacedBy(py(22f)),
        ) {
            sidebarItems.forEachIndexed { index, item ->
                NavigationTile(
                    item = item,
                    selected = selected == index,
                    onClick = { onSelect(index) },
                    modifier = Modifier.size(px(122f), py(132f)),
                    iconSize = fs(43f),
                    labelSize = fs(23f),
                )
            }
        }

        // ── Hambúrguer: abre o painel Kodi (tecla MENU também) ──
        Box(
            Modifier.offset(px(1129f), py(96f)).size(px(40f), py(40f)).clip(CircleShape)
                .background(Color(0x33000000)).border(1.dp, Color(0x33FFFFFF), CircleShape)
                .focusable().clickable { drawerOpen = true },
            contentAlignment = Alignment.Center,
        ) { Icon(Icons.Rounded.Menu, "Menu", tint = Smarted.InkOnWhite, modifier = Modifier.fillMaxSize(0.55f)) }

        // ── Conteúdo das telas (área branca, respeitando a curva) ──
        Box(
            Modifier.offset(px(190f), py(107f))
                .size(px(Smarted.RefW - 190f - 23f), py(Smarted.RefH - 107f - 23f))
                .padding(start = px(44f), top = px(56f), end = px(40f), bottom = px(44f)),
            content = content,
        )

        // ── Painel Kodi ──
        if (drawerOpen) {
            Box(Modifier.fillMaxSize().background(Color(0x99000000)).clickable { drawerOpen = false })
            val ps = RoundedCornerShape(px(40f))
            Column(
                Modifier.offset(px(23f), py(52f)).width(px(440f)).height(px(760f)).clip(ps)
                    .background(Smarted.glassFrosted())
                    .border(1.dp, Smarted.Border, ps).padding(px(18f)),
                verticalArrangement = Arrangement.spacedBy(py(9f)),
            ) {
                Row(
                    Modifier.fillMaxWidth().height(py(52f)).padding(horizontal = px(10f)),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Menu", color = Color.White, fontWeight = FontWeight.Bold, fontSize = fs(24f))
                    Spacer(Modifier.width(px(12f)))
                    Text("Kodi", color = Smarted.TextMuted, fontSize = fs(17f))
                }
                kodiOptions.forEach { opt ->
                    var f by remember { mutableStateOf(false) }
                    val s = RoundedCornerShape(px(26f))
                    Row(
                        Modifier.fillMaxWidth().height(py(54f)).clip(s).background(Smarted.glass())
                            .border(if (f) 2.dp else 1.dp, if (f) Color.White else Smarted.Border, s)
                            .onFocusChanged { f = it.isFocused }
                            .clickable { drawerOpen = false; onKodiOption(opt.action) }
                            .padding(horizontal = px(26f)),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(opt.icon, null, tint = Color.White, modifier = Modifier.size(py(24f)))
                        Spacer(Modifier.width(px(16f)))
                        Text(opt.label, color = Smarted.TextLight, fontWeight = FontWeight.Medium, fontSize = fs(19f))
                    }
                }
            }
        }
    }
}

/**
 * Área branca da referência: retângulo com canto superior esquerdo arredondado
 * (58/1536 e 757/864) e, abaixo do trilho, a extensão que desce até o rodapé com
 * canto de 62 — exatamente a silhueta da imagem.
 */
private fun whitePath(w: Float, h: Float): Path {
    val sx = w / Smarted.RefW
    val sy = h / Smarted.RefH
    fun x(v: Float) = v * sx
    fun y(v: Float) = v * sy

    val mainLeft = x(190f)
    val mainTop = y(107f)
    val mainRadius = x(58f)

    val lowLeft = x(57f)
    val railBottom = y(704f)       // fim do trilho (52 + 648 + respiro)
    val lowRadius = x(62f)

    return Path().apply {
        moveTo(w, h)
        lineTo(lowLeft, h)
        lineTo(lowLeft, railBottom + lowRadius)
        quadraticBezierTo(lowLeft, railBottom, lowLeft + lowRadius, railBottom)
        // degrau até a base da área principal
        lineTo(mainLeft - x(10f), railBottom)
        quadraticBezierTo(mainLeft, railBottom, mainLeft, railBottom - y(10f))
        lineTo(mainLeft, mainTop + mainRadius)
        quadraticBezierTo(mainLeft, mainTop, mainLeft + mainRadius, mainTop)
        lineTo(w, mainTop)
        lineTo(w, h)
        close()
    }
}

@Composable
private fun Capsule(modifier: Modifier, content: @Composable () -> Unit) {
    val shape = RoundedCornerShape(50)
    Box(
        modifier.clip(shape)
            .background(Brush.verticalGradient(listOf(Smarted.CapsuleTop, Smarted.CapsuleBottom)))
            .border(1.5.dp, Smarted.CapsuleBorder, shape),
        contentAlignment = Alignment.Center,
    ) { content() }
}

/** Raio dos botões da barra esquerda — 0 = quadrado perfeito. */
private val SQUARE_CORNER = 0.dp

@Composable
private fun NavigationTile(
    item: SidebarItem,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier,
    iconSize: TextUnit,
    labelSize: TextUnit,
) {
    var focused by remember { mutableStateOf(false) }
    // Botões da esquerda: quadrados (cantos vivos), conforme pedido.
    val shape = RoundedCornerShape(SQUARE_CORNER)
    val fill = if (selected) {
        Brush.verticalGradient(listOf(Smarted.TileTopSelected, Smarted.TileBottomSelected))
    } else {
        Brush.verticalGradient(listOf(Smarted.TileTop, Smarted.TileBottom))
    }
    Column(
        modifier
            .clip(shape)
            .background(fill)
            .border(if (focused) 2.dp else 1.5.dp, if (focused) Color.White else Smarted.TileBorder, shape)
            .onFocusChanged { focused = it.isFocused }
            .clickable(onClick = onClick),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(item.icon, null, tint = Color.White, modifier = Modifier.size(iconSize.value.dp))
        Spacer(Modifier.height(9.dp))
        Text(
            item.label,
            color = Color.White,
            fontSize = labelSize,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            maxLines = 1,
        )
    }
}
