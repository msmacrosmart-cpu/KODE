package com.smarted.tv.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import com.smarted.tv.data.model.LiveChannel
import com.smarted.tv.data.model.Movie
import com.smarted.tv.data.model.Serie

/**
 * Estado único da aplicação.
 *
 * IMPORTANTE: este ViewModel precisa ser obtido com `viewModel()` na Activity
 * (ver MainActivity). Se for instanciado direto no composable (`MainTvViewModel()`)
 * ele é recriado a cada recomposição, o estado é descartado e o app fica em tela preta.
 */
class MainTvViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(SmartEdUiState())
    val uiState: StateFlow<SmartEdUiState> = _uiState.asStateFlow()

    // Compatibilidade com as telas atuais
    val channels: StateFlow<List<LiveChannel>> get() = _channels
    val movies: StateFlow<List<Movie>> get() = _movies
    val series: StateFlow<List<Serie>> get() = _series
    val selectedIndex: StateFlow<Int> get() = _selectedIndex

    private val _channels = MutableStateFlow<List<LiveChannel>>(emptyList())
    private val _movies = MutableStateFlow<List<Movie>>(emptyList())
    private val _series = MutableStateFlow<List<Serie>>(emptyList())
    private val _selectedIndex = MutableStateFlow(0)

    init {
        loadDemoData()
    }

    fun selectIndex(index: Int) {
        _selectedIndex.value = index
        _uiState.value = _uiState.value.copy(currentScreen = index)
    }

    fun setScreen(key: String) {
        _uiState.value = _uiState.value.copy(currentScreenKey = key)
    }

    fun setError(message: String?) {
        _uiState.value = _uiState.value.copy(errorMessage = message)
    }

    fun setLayoutSource(source: String) {
        _uiState.value = _uiState.value.copy(layoutSource = source)
    }

    fun loadDemoData() {
        viewModelScope.launch {
            runCatching {
                // Catálogo de demonstração (substituído pela integração Xtream/M3U)
                _channels.value = listOf(
                    LiveChannel("ch1", 1, "Globo News", null, "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", "Notícias"),
                    LiveChannel("ch2", 2, "Record TV", null, "https://test-streams.mux.dev/pts_shift/master.m3u8", "Entretenimento"),
                    LiveChannel("ch3", 3, "SBT", null, "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", "Variedades"),
                    LiveChannel("ch4", 4, "Band", null, "https://test-streams.mux.dev/pts_shift/master.m3u8", "Esportes"),
                    LiveChannel("ch5", 5, "TV Cultura", null, "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", "Cultura"),
                )
                _movies.value = listOf(
                    Movie("m1", "O Poderoso Chefão", description = "Drama criminal clássico", year = 1972, genre = "Drama", durationMin = 175),
                    Movie("m2", "Interestelar", description = "Ficção científica espacial", year = 2014, genre = "Sci-Fi", durationMin = 169),
                    Movie("m3", "Matrix", description = "Realidade virtual e ação", year = 1999, genre = "Ação", durationMin = 136),
                )
                _series.value = listOf(
                    Serie("s1", "Breaking Bad", description = "Professor vira traficante", year = 2008, genre = "Drama", seasons = 5),
                    Serie("s2", "Stranger Things", description = "Mistérios em Hawkins", year = 2016, genre = "Sci-Fi", seasons = 4),
                    Serie("s3", "The Mandalorian", description = "Star Wars universo", year = 2019, genre = "Ação", seasons = 3),
                )
            }.onFailure { e ->
                setError("Falha ao carregar catálogo: ${e.message}")
            }
        }
    }
}

/** Estado da UI (um único objeto — evita recomposições com estado divergente). */
data class SmartEdUiState(
    val currentScreen: Int = 0,
    val currentScreenKey: String = "home",
    val errorMessage: String? = null,
    val layoutSource: String = "assets",
)
