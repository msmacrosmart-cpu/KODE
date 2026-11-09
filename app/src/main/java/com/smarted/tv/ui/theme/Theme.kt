package com.smarted.tv.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import com.smarted.tv.ui.theme.SmartEDColors

@Composable
fun SmartEDTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) {
        darkColorScheme(
            primary = SmartEDColors.Coral,
            background = SmartEDColors.Background,
            surface = SmartEDColors.Surface,
            onPrimary = Color.White,
            onBackground = SmartEDColors.TextPrimary,
            onSurface = SmartEDColors.TextPrimary,
        )
    } else {
        darkColorScheme(
            primary = SmartEDColors.Coral,
            background = SmartEDColors.Background,
            surface = SmartEDColors.Surface,
            onPrimary = Color.White,
            onBackground = SmartEDColors.TextPrimary,
            onSurface = SmartEDColors.TextPrimary,
        )
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography(),
        content = content
    )
}
