package com.smarted.tv.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/** Paleta de cores do SmartED-TV (fundo escuro + destaques vermelho/laranja/amarelo). */
object SmartEDColors {
    val Background = Color(0xFF0E0E10)
    val Surface = Color(0xFF1A1A1D)
    val SurfaceHigh = Color(0xFF232327)
    val GlassTop = Color(0x26FFFFFF)
    val GlassBottom = Color(0x0AFFFFFF)
    val Coral = Color(0xFFEF5350)
    val Pink = Color(0xFFFF3D5A)
    val Orange = Color(0xFFFF8A00)
    val Yellow = Color(0xFFFFD23F)
    val TextPrimary = Color(0xFFF2F2F2)
    val TextSecondary = Color(0xFFA8A8AD)
    val Success = Color(0xFF4CAF50)
    val Danger = Color(0xFFFF5252)

    val Sunset: Brush get() = Brush.linearGradient(listOf(Pink, Orange, Yellow))

    /** Cores de destaque usadas nos cards (ciclo por índice). */
    val Accents: List<Color> = listOf(Coral, Orange, Yellow, Success)
}
