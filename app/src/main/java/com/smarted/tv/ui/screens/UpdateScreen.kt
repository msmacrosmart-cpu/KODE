package com.smarted.tv.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smarted.tv.ui.components.FocusCard
import com.smarted.tv.ui.components.ScreenTitle
import com.smarted.tv.ui.theme.Smarted
import com.smarted.tv.viewmodel.UpdateViewModel

/**
 * Atualizações do app — instala **por cima** da versão atual.
 *
 * O que a tela mostra é o estado real:
 *  - versão instalada (lida do package manager);
 *  - o que o manifesto publicado diz (versão, `versionCode`, SHA-256);
 *  - progresso do download e resultado da verificação de integridade;
 *  - aviso quando o Android exige liberar "instalar apps desconhecidos".
 */
@Composable
fun UpdateScreen(
    state: UpdateViewModel.State,
    onCheck: () -> Unit,
    onDownload: () -> Unit,
    onOpenPermission: () -> Unit,
    onDismiss: () -> Unit,
) {
    Column(Modifier.fillMaxSize()) {
        ScreenTitle("Atualizações")

        Card {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.SystemUpdate, null, tint = Color.White, modifier = Modifier.size(26.dp))
                Spacer(Modifier.width(14.dp))
                Column {
                    Text(
                        "Versão instalada: ${state.currentVersion.ifBlank { "—" }} (build ${state.currentVersionCode})",
                        color = Color.White, fontWeight = FontWeight.Medium, fontSize = 15.sp,
                    )
                    Text(
                        "A atualização é instalada por cima — não é preciso desinstalar.",
                        color = Smarted.TextLight, fontSize = 12.sp,
                    )
                }
            }
        }

        Spacer(Modifier.height(10.dp))

        val update = state.available
        if (update != null) {
            Card {
                Column {
                    Text("Nova versão ${update.version}", color = Color.White,
                        fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Spacer(Modifier.height(4.dp))
                    Text("build ${update.versionCode} · ${update.apkName}", color = Smarted.TextLight, fontSize = 12.sp)
                    Text("SHA-256: ${update.sha256.take(24)}…", color = Smarted.TextMuted, fontSize = 11.sp)
                    Spacer(Modifier.height(10.dp))
                    if (state.downloading) {
                        Text("Baixando… ${state.progress}%", color = Color.White, fontSize = 13.sp)
                        Spacer(Modifier.height(6.dp))
                        Box(
                            Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp))
                                .background(Color(0xFF2A2A2A))
                        ) {
                            Box(
                                Modifier.fillMaxWidth(state.progress / 100f).height(8.dp)
                                    .clip(RoundedCornerShape(4.dp)).background(Color.White)
                            )
                        }
                    } else {
                        Action(Icons.Rounded.Download, "Baixar e atualizar", onDownload)
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
        }

        if (!state.canInstall) {
            Card {
                Column {
                    Text("O Android pede uma autorização", color = Color.White,
                        fontWeight = FontWeight.Medium, fontSize = 14.sp)
                    Text(
                        "Permita instalar apps desta fonte para o SmartED-TV. Sem isso o instalador não abre.",
                        color = Smarted.TextLight, fontSize = 12.sp,
                    )
                    Spacer(Modifier.height(8.dp))
                    Action(Icons.Rounded.Settings, "Abrir permissão", onOpenPermission)
                }
            }
            Spacer(Modifier.height(10.dp))
        }

        state.message?.let { Msg(it, false, onDismiss); Spacer(Modifier.height(8.dp)) }
        state.error?.let { Msg(it, true, onDismiss); Spacer(Modifier.height(8.dp)) }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Action(Icons.Rounded.Refresh, if (state.checking) "Consultando…" else "Procurar atualização", onCheck)
        }

        Spacer(Modifier.height(14.dp))
        Text(
            "Fonte: manifest update.json da última release. O arquivo é conferido por SHA-256 antes de abrir o instalador.",
            color = Smarted.InkMuted, fontSize = 11.sp,
        )
    }
}

@Composable
private fun Card(content: @Composable () -> Unit) {
    Box(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp))
            .background(Color(0xFF161616)).padding(18.dp)
    ) { content() }
}

@Composable
private fun Action(icon: ImageVector, label: String, onClick: () -> Unit) {
    Row(
        Modifier.clip(RoundedCornerShape(13.dp)).background(Color(0xFF2A2A2A))
            .border(1.dp, Color(0x1FFFFFFF), RoundedCornerShape(13.dp))
            .clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, label, tint = Color.White, modifier = Modifier.size(18.dp))
        Spacer(Modifier.width(7.dp))
        Text(label, color = Color.White, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun Msg(text: String, isError: Boolean, onDismiss: () -> Unit) {
    val bg = if (isError) Color(0xFFFDECEA) else Color(0xFFEFF7EE)
    val fg = if (isError) Color(0xFF7A2018) else Color(0xFF1F5F2A)
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(13.dp)).background(bg)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text, color = fg, fontSize = 12.sp, modifier = Modifier.weight(1f))
        Icon(Icons.Rounded.Close, "Fechar", tint = fg,
            modifier = Modifier.size(16.dp).clickable(onClick = onDismiss))
    }
}
