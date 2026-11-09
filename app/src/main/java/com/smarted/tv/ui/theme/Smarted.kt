package com.smarted.tv.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/** Tokens do layout Smarted-TV. Referência de medidas: 1672 x 941. */
object Smarted {
    const val RefW = 1672f
    const val RefH = 941f

    val Black = Color(0xFF050505)
    val GlassTop = Color(0xFF202020)
    val GlassBottom = Color(0xFF0D0D0D)
    val Border = Color(0x33FFFFFF)
    val BorderSelected = Color(0x99FFFFFF)
    val TextLight = Color(0xFFF2F2F2)
    val InkOnWhite = Color(0xFF0A0A0A)
    val InkMuted = Color(0xFF5A5A5A)
    val CardOnWhite = Color(0xFF161616)

    fun glass() = Brush.verticalGradient(listOf(GlassTop, GlassBottom))
}
