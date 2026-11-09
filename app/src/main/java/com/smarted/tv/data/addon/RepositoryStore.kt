package com.smarted.tv.data.addon

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Repositórios cadastrados pelo usuário (persistência real, sobrevive a reinício).
 *
 * Guarda apenas o necessário para reabrir a fonte: id, nome, tipo e local.
 * O catálogo e a compatibilidade são lidos novamente da fonte — nunca cacheados
 * como se fossem verdade permanente.
 */
class RepositoryStore(context: Context) {

    private val prefs = context.getSharedPreferences("smarted_repos", Context.MODE_PRIVATE)

    /** Repositório cadastrado. */
    data class Entry(
        val id: String,
        val name: String,
        val kind: RepoSource.SourceKind,
        val location: String,
        val enabled: Boolean = true,
        val addedAt: Long = 0L,
        val lastLoadedAt: Long = 0L,
        val addonCount: Int = 0,
        val lastError: String? = null,
    )

    fun all(): List<Entry> {
        val raw = prefs.getString(KEY, null) ?: return emptyList()
        return runCatching {
            val arr = JSONArray(raw)
            (0 until arr.length()).map { i -> fromJson(arr.getJSONObject(i)) }
        }.getOrDefault(emptyList())
    }

    fun find(id: String): Entry? = all().firstOrNull { it.id == id }

    fun upsert(entry: Entry) {
        val list = all().toMutableList()
        val index = list.indexOfFirst { it.id == entry.id }
        if (index >= 0) list[index] = entry else list.add(entry)
        save(list)
    }

    /** Atualiza estado após uma leitura (sucesso ou erro). */
    fun markLoaded(id: String, count: Int, error: String? = null) {
        val current = find(id) ?: return
        upsert(current.copy(addonCount = count, lastLoadedAt = System.currentTimeMillis(), lastError = error))
    }

    fun setEnabled(id: String, enabled: Boolean) {
        val current = find(id) ?: return
        upsert(current.copy(enabled = enabled))
    }

    fun remove(id: String) {
        save(all().filterNot { it.id == id })
    }

    private fun save(list: List<Entry>) {
        val arr = JSONArray()
        list.forEach { arr.put(toJson(it)) }
        prefs.edit().putString(KEY, arr.toString()).apply()
    }

    private fun toJson(e: Entry): JSONObject = JSONObject().apply {
        put("id", e.id)
        put("name", e.name)
        put("kind", e.kind.name)
        put("location", e.location)
        put("enabled", e.enabled)
        put("addedAt", e.addedAt)
        put("lastLoadedAt", e.lastLoadedAt)
        put("addonCount", e.addonCount)
        e.lastError?.let { put("lastError", it) }
    }

    private fun fromJson(o: JSONObject): Entry = Entry(
        id = o.getString("id"),
        name = o.optString("name", o.getString("id")),
        kind = runCatching { RepoSource.SourceKind.valueOf(o.optString("kind", "URL")) }
            .getOrDefault(RepoSource.SourceKind.URL),
        location = o.optString("location", ""),
        enabled = o.optBoolean("enabled", true),
        addedAt = o.optLong("addedAt", 0),
        lastLoadedAt = o.optLong("lastLoadedAt", 0),
        addonCount = o.optInt("addonCount", 0),
        lastError = o.optString("lastError").takeIf { it.isNotBlank() },
    )

    private companion object {
        const val KEY = "repositories"
    }
}
