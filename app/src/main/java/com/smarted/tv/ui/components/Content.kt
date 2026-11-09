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

@Composable
fun EmptyState(message: String) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(message, color = Smarted.InkMuted, fontSize = 18.sp)
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
fun PosterGrid(items: List<MediaItem>, empty: String, onOpen: (MediaItem) -> Unit) {
    if (items.isEmpty()) { EmptyState(empty); return }
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
    if (items.isEmpty()) { EmptyState(empty); return }
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
