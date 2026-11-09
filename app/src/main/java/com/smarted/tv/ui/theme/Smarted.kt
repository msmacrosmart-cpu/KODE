package com.smarted.tv.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/** Tokens do layout Smarted-TV. Referência de medidas: 1672 x 941 (horizontal). */
object Smarted {
    const val RefW = 1672f
    const val RefH = 941f

    val Black = Color(0xFF050505)

    // ── Glass PRETO FOSCO (sem brilho): vidro escuro + leve textura ──
    val GlassTop = Color(0xFF171717)      // antes 0xFF202020 (acinzentado/brilhante)
    val GlassBottom = Color(0xFF0A0A0A)
    val GlassFlat = Color(0xFF101010)     // fosco puro (base dos botões)
    val Border = Color(0x2BFFFFFF)        // 17%
    val BorderSelected = Color(0x8AFFFFFF)

    val TextLight = Color(0xFFF2F2F2)
    val TextMuted = Color(0xFF8E8E93)

    // Conteúdo (área branca)
    val InkOnWhite = Color(0xFF0A0A0A)
    val InkMuted = Color(0xFF5A5A5A)
    val CardOnWhite = Color(0xFF161616)

    /** Vidro fosco: gradiente quase imperceptível (não "molha" a tela). */
    fun glass() = Brush.verticalGradient(listOf(Color(0xFF141414), Color(0xFF0B0B0B)))

    /** Vidro fosco com borda interna suave — usado nos botões da sidebar. */
    fun glassFrosted() = Brush.verticalGradient(
        listOf(Color(0xFF1B1B1B), Color(0xFF0E0E0E), Color(0xFF090909))
    )
}
