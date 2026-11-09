package com.smarted.tv.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.unit.dp
import com.smarted.tv.ui.theme.SmartEDColors

@Composable
fun GlassPanel(
    modifier: Modifier = Modifier,
    shape: RoundedCornerShape = RoundedCornerShape(24.dp),
    content: @Composable BoxScope.() -> Unit,
) {
    Box(
        modifier
            .clip(shape)
            .background(SmartEDColors.Surface.copy(alpha = 0.72f))
            .background(Brush.verticalGradient(listOf(SmartEDColors.GlassTop, SmartEDColors.GlassBottom)))
            .border(
                1.dp,
                Brush.verticalGradient(listOf(Color(0x66FFFFFF), Color(0x1AFFFFFF))),
                shape,
            ),
        content = content,
    )
}
