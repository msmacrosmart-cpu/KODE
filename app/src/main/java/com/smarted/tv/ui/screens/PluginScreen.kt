package com.smarted.tv.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smarted.tv.data.plugin.PluginItem
import com.smarted.tv.data.plugin.PluginTarget
import com.smarted.tv.ui.components.EmptyState
import com.smarted.tv.ui.components.FocusCard
import com.smarted.tv.ui.components.ScreenTitle
import com.smarted.tv.ui.theme.Smarted
import com.smarted.tv.viewmodel.PluginViewModel

/**
 * Navegação virtual `plugin://` (Fase F).
 *
 * Mostra apenas o que o adaptador real produziu. Sem adaptador ou sem add-on
 * instalado, aparece o motivo técnico — jamais uma lista de exemplo.
 */
@Composable
fun PluginScreen(
    state: PluginViewModel.State,
    onBack: () -> Unit,
    onActivate: (PluginItem) -> Unit,
    onClose: () -> Unit,
) {
    Column(Modifier.fillMaxSize()) {
        ScreenTitle(state.title.ifBlank { "Plugin" })

        Row(Modifier.fillMaxWidth().padding(bottom = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Row(
                Modifier.clip(RoundedCornerShape(13.dp)).background(Color(0xFFEDEDED))
                    .border(1.dp, Color(0x14000000), RoundedCornerShape(13.dp))
                    .clickable(onClick = onBack).padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(if (state.canGoBack) Icons.Rounded.ArrowBack else Icons.Rounded.Close, "Voltar",
                    tint = Smarted.InkOnWhite, modifier = Modifier.size(17.dp))
                Spacer(Modifier.width(6.dp))
                Text(if (state.canGoBack) "Voltar" else "Sair do plugin", color = Smarted.InkOnWhite, fontSize = 13.sp)
            }
            Spacer(Modifier.width(12.dp))
            Text(state.uri.orEmpty(), color = Smarted.InkMuted, fontSize = 12.sp,
                maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
            if (!state.canGoBack && state.uri != null) {
                Text("Fechar", color = Smarted.InkMuted, fontSize = 12.sp,
                    modifier = Modifier.clickable(onClick = onClose).padding(8.dp))
            }
        }

        state.error?.let { motivo ->
            Column(
                Modifier.fillMaxWidth().padding(bottom = 10.dp).clip(RoundedCornerShape(14.dp))
                    .background(Color(0xFFFDECEA)).padding(16.dp),
            ) {
                Text(motivo, color = Color(0xFF7A2018), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                state.details.forEach {
                    Text("• $it", color = Color(0xFF7A2018), fontSize = 12.sp,
                        modifier = Modifier.padding(top = 3.dp))
                }
            }
        }

        state.warnings.forEach {
            Text("⚠ $it", color = Color(0xFF7A5A18), fontSize = 12.sp, modifier = Modifier.padding(vertical = 2.dp))
        }

        when {
            state.loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Consultando o add-on…", color = Smarted.InkMuted, fontSize = 15.sp)
            }

            !state.hasContent && state.error != null -> EmptyState(
                message = "Sem listagem para este add-on",
                hint = "Isso é um limite real: add-ons em Python dependem da API xbmc*, que este app " +
                    "não executa. Nenhum conteúdo é inventado.",
                icon = Icons.Rounded.ExtensionOff,
            )

            !state.hasContent -> EmptyState(
                message = "Nada para mostrar",
                hint = "O adaptador respondeu, mas não há itens nesta pasta do add-on.",
                icon = Icons.Rounded.Inbox,
            )

            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(state.items) { item -> PluginRow(item) { onActivate(item) } }
            }
        }
    }
}

@Composable
private fun PluginRow(item: PluginItem, onClick: () -> Unit) {
    FocusCard(Modifier.fillMaxWidth().height(76.dp), onClick) {
        Row(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                when {
                    item.isFolder -> Icons.Rounded.Folder
                    item.target is PluginTarget.Media -> Icons.Rounded.PlayArrow
                    else -> Icons.Rounded.Info
                },
                null, tint = Color.White, modifier = Modifier.size(24.dp),
            )
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(item.label, color = Color.White, fontWeight = FontWeight.Medium, fontSize = 16.sp,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
                val sub = item.label2 ?: when (val t = item.target) {
                    is PluginTarget.Media -> t.uri.substringBefore('?')
                    is PluginTarget.Unsupported -> t.reason
                    is PluginTarget.Virtual -> t.uri.pathText
                    null -> "sem destino"
                }
                Text(sub, color = Smarted.TextLight, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            if (item.target is PluginTarget.Unsupported) {
                Text("não toca", color = Color(0xFFFFC9A3), fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
