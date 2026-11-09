package com.smarted.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.smarted.tv.ui.screens.AppScreen
import com.smarted.tv.ui.theme.SmartEDTheme
import com.smarted.tv.viewmodel.MainTvViewModel

class MainActivity : ComponentActivity() {

    // ViewModel único da Activity: sobrevive à recomposição/rotação.
    private val vm: MainTvViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            // Garante tela escura (nunca preta) + proteção contra crash de tela
            SmartEDTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    AppScreen(vm = vm)
                }
            }
        }
    }
}
