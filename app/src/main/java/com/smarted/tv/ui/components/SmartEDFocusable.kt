package com.smarted.tv.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.smarted.tv.ui.theme.SmartEDColors

/**
 * Superfície focável para D-pad + toque (Android TV / TV Box).
 * Foco = borda com gradiente + glow + leve zoom. OK/Enter disparam onClick.
 */
@Composable
fun SmartEDFocusable(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    shape: RoundedCornerShape = RoundedCornerShape(16.dp),
    selected: Boolean = false,
    focusScale: Float = 1.03f,
    idleColor: Color = Color(0x14FFFFFF),
    onFocused: () -> Unit = {},
    content: @Composable BoxScope.(focused: Boolean) -> Unit,
) {
    var focused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(targetValue = if (focused) focusScale else 1f, animationSpec = tween(150), label = "focusScale")

    val border: Brush = when {
        focused -> SmartEDColors.Sunset
        selected -> SolidColor(SmartEDColors.Coral.copy(alpha = 0.7f))
        else -> SolidColor(Color(0x1AFFFFFF))
    }
    val background = when {
        focused -> Color(0x33FFFFFF)
        selected -> Color(0x1FFFFFFF)
        else -> idleColor
    }

    Box(
        modifier = modifier
            .onFocusChanged {
                focused = it.isFocused
                if (it.isFocused) onFocused()
            }
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .shadow(
                elevation = if (focused) 14.dp else 0.dp,
                shape = shape,
                clip = false,
                ambientColor = SmartEDColors.Orange,
                spotColor = SmartEDColors.Pink,
            )
            .clip(shape)
            .background(background)
            .border(width = if (focused) 2.dp else 1.dp, brush = border, shape = shape)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onClick,
            ),
    ) {
        content(focused)
    }
}
