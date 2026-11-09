package com.smarted.tv.data.plugin.adapters

import android.content.Context
import com.smarted.tv.data.plugin.PluginAdapter
import com.smarted.tv.data.plugin.PluginItem
import com.smarted.tv.data.plugin.PluginListing
import com.smarted.tv.data.plugin.PluginTarget
import com.smarted.tv.data.plugin.PluginUri
import com.smarted.tv.data.source.FileAction
import com.smarted.tv.data.source.FileBrowser
import com.smarted.tv.data.source.SafFileSystem

/**
 * Adaptador REAL para add-ons do tipo pasta local.
 *
 * Serve a um caso concreto e verificável: um add-on cuja URI aponta para uma
 * pasta do aparelho (autorizada via SAF ou caminho de arquivo). A listagem é
 * 100% o conteúdo real da pasta, classificada pelo [FileClassifier];
 * a reprodução usa a própria URI do arquivo, com MIME explícito.
 *
 * URI suportada:
 * ```
 * plugin://<id>/browse?folder=<uri content:// ou caminho>
 * ```
 *
 * Se a URI não trouxer pasta, devolve erro — não inventa conteúdo.
 */
class LocalFolderPluginAdapter(
    private val context: Context,
    override val addonId: String,
) : PluginAdapter {

    override val description: String =
        "Lista o conteúdo real de uma pasta autorizada (SAF). Sem pasta declarada, não há listagem."

    private val fs = SafFileSystem(context)

    override suspend fun browse(uri: PluginUri): PluginListing {
        val folder = uri.params["folder"]
            ?: uri.params["path"]?.takeIf { it.startsWith("content://") || it.startsWith("/") || it.startsWith("file://") }
            ?: return PluginListing(
                addonId = addonId,
                title = addonId,
                error = "URIs deste adaptador precisam de ?folder=<pasta do aparelho>",
            )

        if (!SafFileSystem.isSafeDocumentUri(folder)) {
            return PluginListing(addonId = addonId, title = addonId, error = "Caminho recusado: $folder")
        }

        val entries = runCatching { fs.list(folder) }
            .getOrElse { e ->
                return PluginListing(
                    addonId = addonId,
                    title = folder,
                    error = "Não foi possível listar a pasta: ${e.message ?: e::class.java.simpleName}",
                )
            }

        val items = entries.map { entry ->
            val classification = FileBrowser.classify(entry.name, entry.mime)
            PluginItem(
                label = entry.name,
                label2 = if (entry.isDirectory) "pasta" else FileBrowser.describeSize(entry.size),
                target = if (entry.isDirectory) {
                    PluginTarget.Virtual(
                        PluginUri(
                            addonId = addonId,
                            path = listOf("browse"),
                            params = mapOf("folder" to entry.uri),
                            raw = "plugin://$addonId/browse?folder=${entry.uri}",
                        )
                    )
                } else if (classification.action == FileAction.PLAY) {
                    PluginTarget.Media(
                        uri = entry.uri,
                        mimeHint = classification.mime,
                        title = entry.name,
                    )
                } else {
                    PluginTarget.Unsupported("Tipo ${classification.kind} não é reproduzível", entry.uri)
                },
                isFolder = entry.isDirectory,
                params = mapOf("addonId" to addonId),
                metadata = mapOf("kind" to classification.kind.name, "mime" to (classification.mime ?: "")),
            )
        }.sortedWith(compareByDescending<PluginItem> { it.isFolder }.thenBy { it.label.lowercase() })

        return PluginListing(
            addonId = addonId,
            title = fs.nameOf(folder),
            items = items,
            warnings = if (items.isEmpty()) listOf("A pasta está vazia") else emptyList(),
        )
    }

    override suspend fun resolve(item: PluginItem): PluginTarget =
        item.target ?: PluginTarget.Unsupported("Item sem destino declarado")

    /** Só atende ids que o app registrou explicitamente. */
    override fun supports(addonId: String): Boolean = this.addonId.equals(addonId, ignoreCase = true)
}
