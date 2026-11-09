package com.smarted.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
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
                SafeScreen {
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
}

/**
 * Se qualquer tela lançar exceção, mostra uma mensagem legível em vez de tela preta.
 * (antes: exception em composable = janela preta e app "travado")
 */
@Composable
private fun SafeScreen(content: @Composable () -> Unit) {
    Box(modifier = Modifier.fillMaxSize().background(Color(0xFF0E0E10))) {
        try {
            content()
        } catch (t: Throwable) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(
                    text = "SmartED-TV\n\nErro ao montar a tela:\n${t.message ?: t::class.java.simpleName}\n\nPressione VOLTAR e abra novamente.",
                    color = Color(0xFFF2F2F2),
                )
            }
        }
    }
}
