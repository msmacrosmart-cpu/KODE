package com.smarted.tv.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LiveTv
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Puzzle
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Tv
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.smarted.tv.ui.theme.SmartEDColors

/**
 * Menu lateral de navegação (estilo Kodi "navegar").
 * Itens: Início, Canais, Filmes, Séries, Addons, Navegar Pastas, Configurações, Sair.
 * YouTube foi removido conforme solicitado.
 */
@Composable
fun TvNavigationRail(
    selectedIndex: Int,
    onItemClick: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val items = listOf(
        NavItem(0, "Início", Icons.Default.Home),
        NavItem(1, "Canais", Icons.Default.LiveTv),
        NavItem(2, "Filmes", Icons.Default.Movie),
        NavItem(3, "Séries", Icons.Default.Tv),
        NavItem(4, "Addons", Icons.Default.Puzzle),
        NavItem(5, "Pastas", Icons.Default.Folder),
        NavItem(6, "Config", Icons.Default.Settings),
        NavItem(7, "Sair", Icons.Default.Logout),
    )

    Column(
        modifier = modifier
            .width(84.dp)
            .background(SmartEDColors.Surface)
            .padding(top = 16.dp, bottom = 16.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        items.forEach { item ->
            val selected = selectedIndex == item.index
            val scale by animateFloatAsState(
                targetValue = if (selected) 1.10f else 1f,
                animationSpec = tween(150),
                label = "railItemScale",
            )

            Box(
                modifier = Modifier
                    .graphicsLayer {
                        scaleX = scale
                        scaleY = scale
                    }
                    .clip(RoundedCornerShape(18.dp))
                    .background(
                        if (selected) SmartEDColors.Coral.copy(alpha = 0.25f)
                        else Color(0x14FFFFFF)
                    )
                    .border(
                        width = if (selected) 2.dp else 1.dp,
                        color = if (selected) SmartEDColors.Coral else Color(0x1AFFFFFF),
                        shape = RoundedCornerShape(18.dp),
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
                        contentDescription = item.label,
                        tint = if (selected) SmartEDColors.TextPrimary else SmartEDColors.TextSecondary,
                        modifier = Modifier.size(24.dp),
                    )
                    Text(
                        text = item.label,
                        style = MaterialTheme.typography.labelSmall,
                        color = if (selected) SmartEDColors.TextPrimary else SmartEDColors.TextSecondary,
                        modifier = Modifier.padding(top = 4.dp),
                        maxLines = 1,
                    )
                }
            }
        }
    }
}

private data class NavItem(
    val index: Int,
    val label: String,
    val icon: ImageVector,
)
