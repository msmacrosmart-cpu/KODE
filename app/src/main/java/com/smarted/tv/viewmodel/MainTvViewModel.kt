package com.smarted.tv.viewmodel

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.viewModelScope
import com.smarted.tv.data.model.LiveChannel
import com.smarted.tv.data.model.Movie
import com.smarted.tv.data.model.Serie

class MainTvViewModel : ViewModel() {

    // Canais de TV
    private val _channels = MutableStateFlow<List<LiveChannel>>(emptyList())
    val channels: StateFlow<List<LiveChannel>> = _channels.stateIn(viewModelScope)

    // Filmes
    private val _movies = MutableStateFlow<List<Movie>>(emptyList())
    val movies: StateFlow<List<Movie>> = _movies.stateIn(viewModelScope)

    // Séries
    private val _series = MutableStateFlow<List<Serie>>(emptyList())
    val series: StateFlow<List<Serie>> = _series.stateIn(viewModelScope)

    // Índice selecionado no Navigation Rail
    private val _selectedIndex = MutableStateFlow(0)
    val selectedIndex: StateFlow<Int> = _selectedIndex.stateIn(viewModelScope)

    fun selectIndex(index: Int) {
        _selectedIndex.value = index
    }

    fun loadDemoData() {
        // Dados de demonstração (serão substituídos pela integração real com Xtream Codes / M3U)
        _channels.value = listOf(
            LiveChannel("ch1", 1, "Globo News", "https://via.placeholder.com/48x48?text=G", "https://example.com/stream1.m3u8", "Notícias"),
            LiveChannel("ch2", 2, "Record TV", "https://via.placeholder.com/48x48?text=R", "https://example.com/stream2.m3u8", "Entretenimento"),
            LiveChannel("ch3", 3, "SBT", "https://via.placeholder.com/48x48?text=S", "https://example.com/stream3.m3u8", "Variedades"),
            LiveChannel("ch4", 4, "Band", "https://via.placeholder.com/48x48?text=B", "https://example.com/stream4.m3u8", "Esportes"),
            LiveChannel("ch5", 5, "TV Cultura", "https://via.placeholder.com/48x48?text=C", "https://example.com/stream5.m3u8", "Cultura"),
        )

        _movies.value = listOf(
            Movie("m1", "O Poderoso Chefão", "https://via.placeholder.com/200x300?text=Godfather", description = "Drama criminal clássico", year = 1972, genre = "Drama", durationMin = 175),
            Movie("m2", "Interestelar", "https://via.placeholder.com/200x300?text=Interstellar", description = "Ficção científica espacial", year = 2014, genre = "Sci-Fi", durationMin = 169),
            Movie("m3", "Matrix", "https://via.placeholder.com/200x300?text=Matrix", description = "Realidade virtual e ação", year = 1999, genre = "Ação", durationMin = 136),
        )

        _series.value = listOf(
            Serie("s1", "Breaking Bad", "https://via.placeholder.com/200x300?text=BB", description = "Professor vira traficante", year = 2008, genre = "Drama", seasons = 5),
            Serie("s2", "Stranger Things", "https://via.placeholder.com/200x300?text=ST", description = "Mistérios em Hawkins", year = 2016, genre = "Sci-Fi", seasons = 4),
            Serie("s3", "The Mandalorian", "https://via.placeholder.com/200x300?text=Mando", description = "Star Wars universo", year = 2019, genre = "Ação", seasons = 3),
        )
    }
}
