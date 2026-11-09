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
import com.smarted.tv.ui.ClimateInfo
import com.smarted.tv.ui.SmartedData
import com.smarted.tv.ui.components.MediaItem
import com.smarted.tv.ui.screens.SettingsInfo

/**
 * Estado da aplicação. Deve ser obtido via `by viewModels()` na Activity
 * (nunca instanciado dentro do composable — era a causa da tela preta).
 */
class MainTvViewModel : ViewModel() {

    private val _channels = MutableStateFlow<List<LiveChannel>>(emptyList())
    val channels: StateFlow<List<LiveChannel>> = _channels.asStateFlow()

    private val _movies = MutableStateFlow<List<Movie>>(emptyList())
    val movies: StateFlow<List<Movie>> = _movies.asStateFlow()

    private val _series = MutableStateFlow<List<Serie>>(emptyList())
    val series: StateFlow<List<Serie>> = _series.asStateFlow()

    private val _settings = MutableStateFlow(SettingsInfo())
    val settings: StateFlow<SettingsInfo> = _settings.asStateFlow()

    private val _videos = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _music = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _programs = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _radio = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _games = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _images = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _addons = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _files = MutableStateFlow<List<MediaItem>>(emptyList())
    private val _favorites = MutableStateFlow<List<MediaItem>>(emptyList())

    /** Dados já no formato do layout (observável — a tela atualiza sozinha). */
    private val _data = MutableStateFlow(SmartedData())
    val data: StateFlow<SmartedData> = _data.asStateFlow()

    init {
        loadDemoData()
    }

    /** Converte os modelos do app para os modelos do layout (MediaItem). */
    private fun publish() {
        _data.value = smartedData()
    }

    fun smartedData(): SmartedData = SmartedData(
        channels = _channels.value.map {
            MediaItem(
                id = it.id,
                title = "${it.number} • ${it.name}",
                subtitle = it.category,
                imageUrl = it.logoUrl,
                url = it.streamUrl,
            )
        },
        movies = _movies.value.map {
            MediaItem(
                id = it.id,
                title = it.title,
                subtitle = listOfNotNull(it.year.takeIf { y -> y > 0 }?.toString(), it.genre)
                    .filter { p -> p.isNotBlank() }.joinToString(" • "),
                imageUrl = it.posterUrl,
                url = it.streamUrl,
            )
        },
        series = _series.value.map {
            MediaItem(
                id = it.id,
                title = it.title,
                subtitle = listOfNotNull(it.year.takeIf { y -> y > 0 }?.toString(), "${it.seasons} temp.")
                    .joinToString(" • "),
                imageUrl = it.posterUrl,
                url = it.streamUrl,
            )
        },
        videos = _videos.value,
        music = _music.value,
        programs = _programs.value,
        radio = _radio.value,
        games = _games.value,
        images = _images.value,
        addons = _addons.value,
        files = _files.value,
        favorites = _favorites.value,
        settings = _settings.value,
        climate = ClimateInfo(),
    )

    /** Clique em um item de Configurações. */
    fun onSettingAction(key: String) {
        _settings.value = when (key) {
            "config:epg" -> _settings.value.copy(epgStatus = "Sincronizando…")
            else -> _settings.value
        }
        publish()
    }

    fun updateEpg() {
        viewModelScope.launch {
            _settings.value = _settings.value.copy(epgStatus = "Atualizando…")
            publish()
            // TODO: integrar download real do EPG (XMLTV)
            _settings.value = _settings.value.copy(epgStatus = "EPG atualizado agora")
            publish()
        }
    }

    fun loadDemoData() {
        viewModelScope.launch {
            runCatching {
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
                _files.value = listOf(
                    MediaItem("f1", "Armazenamento interno", "Pastas e arquivos locais", isFolder = true),
                    MediaItem("f2", "Downloads", "Arquivos baixados", isFolder = true),
                )
                _addons.value = emptyList()
                _programs.value = emptyList()
                _music.value = emptyList()
                _radio.value = emptyList()
                _games.value = emptyList()
                _images.value = emptyList()
                _videos.value = emptyList()
                _favorites.value = emptyList()

                _settings.value = SettingsInfo(
                    account = "Demonstração",
                    server = "—",
                    expiration = "—",
                    epgStatus = "Não sincronizado",
                    version = "1.0.4",
                    skin = "Smarted-TV",
                )
            }
        }
    }
}
