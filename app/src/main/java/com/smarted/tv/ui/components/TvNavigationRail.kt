package com.smarted.tv.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smarted.tv.ui.theme.SmartEDColors

/**
 * Menu lateral de navegação (estilo Kodi "navegar").
 * Itens: Início, Canais, Filmes, Séries, Addons, Ferramentas, Configurações, Sair.
 * YouTube foi removido conforme solicitado.
 */
@Composable
fun TvNavigationRail(
    selectedIndex: Int,
    onItemClick: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val items = listOf(
        NavItem(0, "Início", androidx.compose.material3.Icons.Default.Home),
        NavItem(1, "Canais", androidx.compose.material3.Icons.Default.LiveTv),
        NavItem(2, "Filmes", androidx.compose.material3.Icons.Default.Movie),
        NavItem(3, "Séries", androidx.compose.material3.Icons.Default.TV),
        NavItem(4, "Addons", androidx.compose.material3.Icons.Default.Puzzle),
        NavItem(5, "Navegar Pastas", androidx.compose.material3.Icons.Default.Folder),
        NavItem(6, "Configurações", androidx.compose.material3.Icons.Default.Settings),
        NavItem(7, "Sair", androidx.compose.material3.Icons.Default.Logout),
    )

    Column(
        modifier = modifier
            .width(80.dp)
            .background(SmartEDColors.Surface)
            .padding(top = 24.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        items.forEach { item ->
            val selected = selectedIndex == item.index
            val scale by animateFloatAsState(if (selected) 1.10f else 1f, tween(150))

            Box(
                modifier = Modifier
                    .graphicsLayer { scaleX = scale; scaleY = scale }
                    .clip(RoundedCornerShape(18.dp))
                    .background(
                        if (selected) SmartEDColors.Coral.copy(alpha = 0.25f)
                        else Color(0x14FFFFFF)
                    )
                    .border(
                        if (selected) 2.dp else 1.dp,
                        if (selected) SmartEDColors.Coral
                        else Color(0x1AFFFFFF),
                        RoundedCornerShape(18.dp),
                    )
                    .shadow(
                        elevation = if (selected) 10.dp else 0.dp,
                        shape = RoundedCornerShape(18.dp),
                        clip = false,
                        ambientColor = SmartEDColors.Orange,
                        spotColor = SmartEDColors.Pink,
                    )
                    .size(60.dp)
                    .clickable { onItemClick(item.index) },
            ) {
                Column(
                    modifier = Modifier.fillMaxSize().padding(4.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(
                        imageVector = item.icon,
                        contentDescription = null,
                        tint = if (selected) SmartEDColors.TextPrimary
                        else SmartEDColors.TextSecondary,
                        modifier = Modifier.size(26.dp),
                    )
                    Text(
                        text = item.label,
                        style = androidx.compose.material3.MaterialTheme.typography.labelSmall,
                        color = if (selected) SmartEDColors.TextPrimary
                        else SmartEDColors.TextSecondary,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
            }
        }
    }
}

private data class NavItem(
    val index: Int,
    val label: String,
    val icon: ImageVector
)
