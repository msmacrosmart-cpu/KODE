package com.smarted.tv.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/**
 * Tokens do layout Smarted-TV.
 *
 * Referência de medidas: **1536 x 864** (horizontal, 16:9) — a mesma composição
 * do pacote `SmartedTV_Kotlin_Recriacao` (docs/referencia-nova-tela.png).
 */
object Smarted {
    const val RefW = 1536f
    const val RefH = 864f

    val Black = Color(0xFF050505)

    // ── Glass PRETO FOSCO PURO (matte): sem gradiente glossy ──
    val GlassTop = Color(0xFF121212)
    val GlassBottom = Color(0xFF0E0E0E)
    val GlassFlat = Color(0xFF101010)
    val Border = Color(0x1FFFFFFF)        // 12% — contorno discreto
    val BorderSelected = Color(0x66FFFFFF)

    val TextLight = Color(0xFFF2F2F2)
    val TextMuted = Color(0xFF8E8E93)

    // Conteúdo (área branca)
    val InkOnWhite = Color(0xFF0A0A0A)
    val InkMuted = Color(0xFF5A5A5A)
    val CardOnWhite = Color(0xFF161616)

    /**
     * Vidro fosco: preto fosco praticamente plano.
     * Sem brilho/gloss — a textura vem só da borda 1dp e da sombra.
     */
    fun glass() = Brush.verticalGradient(listOf(GlassFlat, Color(0xFF0B0B0B)))

    /** Superfície dos botões da sidebar (fosco, sem reflexo). */
    fun glassFrosted() = Brush.verticalGradient(listOf(Color(0xFF141414), Color(0xFF101010)))
}
