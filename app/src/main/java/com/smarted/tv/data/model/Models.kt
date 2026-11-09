package com.smarted.tv.data.model

/** Canal de TV ao vivo */
data class LiveChannel(
    val id: String,
    val number: Int,
    val name: String,
    val logoUrl: String? = null,
    val streamUrl: String? = null,
    val category: String = "Geral",
    val isLive: Boolean = true,
)

/** Filme (VOD) */
data class Movie(
    val id: String,
    val title: String,
    val posterUrl: String? = null,
    val backdropUrl: String? = null,
    val description: String = "",
    val year: Int = 0,
    val genre: String = "",
    val durationMin: Int = 0,
    val streamUrl: String? = null,
)

/** Série */
data class Serie(
    val id: String,
    val title: String,
    val posterUrl: String? = null,
    val backdropUrl: String? = null,
    val description: String = "",
    val year: Int = 0,
    val genre: String = "",
    val seasons: Int = 0,
    val streamUrl: String? = null,
)

/** Item genérico para grid de cards (usado nas telas de navegação) */
data class BrowseItem(
    val id: String,
    val title: String,
    val subtitle: String = "",
    val imageUrl: String? = null,
    val type: ItemType = ItemType.Movie,
)

enum class ItemType {
    Channel, Movie, Serie, Addon, Setting
}
