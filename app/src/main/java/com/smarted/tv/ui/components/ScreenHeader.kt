package com.smarted.tv.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.smarted.tv.ui.theme.SmartEDColors

@Composable
fun ScreenHeader(title: String, subtitle: String) {
    Column {
        Text(
            text = title,
            color = SmartEDColors.TextPrimary,
            fontSize = 34.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
        )
        Text(
            text = subtitle,
            color = SmartEDColors.TextSecondary,
            fontSize = 14.sp,
        )
    }
}
