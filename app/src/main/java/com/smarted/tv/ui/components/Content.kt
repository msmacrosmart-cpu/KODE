package com.smarted.tv.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Inbox
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smarted.tv.ui.theme.Smarted

data class MediaItem(
    val id: String,
    val title: String,
    val subtitle: String = "",
    val imageUrl: String? = null,
    val isFolder: Boolean = false,
    /** URL de stream (usada ao abrir o player). */
    val url: String? = null,
)

@Composable
fun ScreenTitle(text: String) {
    Text(text, color = Smarted.InkOnWhite, fontWeight = FontWeight.Bold, fontSize = 28.sp,
        modifier = Modifier.padding(bottom = 16.dp))
}

/**
 * Estado vazio elegante: cartão de vidro claro com ícone, título e dica.
 * Nunca deixa a área branca "travada" sem feedback.
 */
@Composable
fun EmptyState(
    message: String,
    hint: String = "Use o painel de menu (☰) para navegar entre as seções do Kodi.",
    icon: ImageVector = Icons.Rounded.Inbox,
) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            Modifier
                .widthIn(max = 520.dp)
                .clip(RoundedCornerShape(24.dp))
                .background(Color(0xFFF4F4F4))
                .border(1.dp, Color(0x14000000), RoundedCornerShape(24.dp))
                .padding(horizontal = 36.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(
                Modifier.size(72.dp).clip(RoundedCornerShape(20.dp)).background(Smarted.CardOnWhite),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, null, tint = Color.White, modifier = Modifier.size(34.dp))
            }
            Spacer(Modifier.height(18.dp))
            Text(
                message,
                color = Smarted.InkOnWhite,
                fontWeight = FontWeight.Bold,
                fontSize = 20.sp,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                hint,
                color = Smarted.InkMuted,
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** Card grafite com foco de D-pad (borda preta grossa sobre o fundo branco). */
@Composable
fun FocusCard(
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    content: @Composable BoxScope.() -> Unit,
) {
    var f by remember { mutableStateOf(false) }
    val shape = RoundedCornerShape(20.dp)
    Box(
        modifier.clip(shape).background(Smarted.CardOnWhite)
            .border(if (f) 3.dp else 1.dp, if (f) Color.White else Smarted.Border, shape)
            .onFocusChanged { f = it.isFocused }
            .clickable(onClick = onClick),
        content = content
    )
}

@Composable
fun PosterGrid(
    items: List<MediaItem>,
    empty: String,
    onOpen: (MediaItem) -> Unit,
    emptyIcon: ImageVector = Icons.Rounded.Inbox,
) {
    if (items.isEmpty()) { EmptyState(empty, icon = emptyIcon); return }
    LazyVerticalGrid(
        columns = GridCells.Adaptive(170.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        items(items, key = { it.id }) { m ->
            FocusCard(Modifier.fillMaxWidth().aspectRatio(2f / 3f), { onOpen(m) }) {
                // TODO: carregar m.imageUrl (Coil) como fundo do card
                Column(Modifier.align(Alignment.BottomStart).padding(14.dp)) {
                    Text(m.title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                    if (m.subtitle.isNotEmpty())
                        Text(m.subtitle, color = Smarted.TextLight, fontSize = 13.sp, maxLines = 1)
                }
            }
        }
    }
}

@Composable
fun ListRows(
    items: List<MediaItem>, empty: String, icon: ImageVector? = null, onOpen: (MediaItem) -> Unit,
) {
    if (items.isEmpty()) { EmptyState(empty, icon = icon ?: Icons.Rounded.Inbox); return }
    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
        items(items, key = { it.id }) { m ->
            FocusCard(Modifier.fillMaxWidth().height(76.dp), { onOpen(m) }) {
                Row(Modifier.fillMaxSize().padding(horizontal = 22.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (icon != null) {
                        Icon(icon, null, tint = Color.White, modifier = Modifier.size(32.dp))
                        Spacer(Modifier.width(18.dp))
                    }
                    Column(Modifier.weight(1f)) {
                        Text(m.title, color = Color.White, fontWeight = FontWeight.Medium, fontSize = 18.sp,
                            maxLines = 1, overflow = TextOverflow.Ellipsis)
                        if (m.subtitle.isNotEmpty())
                            Text(m.subtitle, color = Smarted.TextLight, fontSize = 14.sp, maxLines = 1)
                    }
                }
            }
        }
    }
}
