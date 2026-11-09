package com.smarted.tv.data.source

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.InputStream

/**
 * Ponte entre o SAF (Storage Access Framework) e o navegador.
 *
 * Tudo que aparece na tela vem do sistema de arquivos real:
 *  - pastas autorizadas pelo usuário via `ACTION_OPEN_DOCUMENT_TREE`
 *    (permissão persistida — sobrevive a reinícios);
 *  - árvore do documento escolhido com `ACTION_OPEN_DOCUMENT`.
 *
 * Nada é sintetizado. Sem permissão persistida, o provedor de armazenamento
 * nega a listagem (SecurityException) e o app mostra isso ao usuário em vez de
 * inventar pastas.
 *
 * Tipos de URI aceitos:
 *  - `content://` (SAF)  → DocumentFile
 *  - `file://` / caminho → File
 *  - `http(s)://`        → NÃO é arquivo; quem trata é o player/plugin.
 */
class SafFileSystem(private val context: Context) {

    private val resolver get() = context.contentResolver

    /** Pastas realmente autorizadas (persistidas pelo sistema). */
    fun grantedTrees(): List<Crumb> =
        resolver.persistedUriPermissions
            .filter { it.isReadPermission }
            .mapNotNull { perm ->
                val uri = perm.uri.toString()
                Crumb(uri, treeDisplayName(uri))
            }
            .distinctBy { it.uri }

    private fun treeDisplayName(uriString: String): String {
        val docId = runCatching {
            DocumentsContract.getTreeDocumentId(Uri.parse(uriString))
        }.getOrNull() ?: return context.getString(android.R.string.untitled)
        val volume = docId.substringBefore(':', docId)
        val path = docId.substringAfter(':', "")
        if (path.isBlank()) return "Armazenamento $volume"
        return path.substringAfterLast('/')
    }

    /** Persiste a permissão da árvore escolhida pelo usuário. */
    fun takePermission(treeUri: Uri): Boolean = runCatching {
        resolver.takePersistableUriPermission(treeUri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
        true
    }.getOrDefault(false)

    fun releasePermission(treeUri: Uri) {
        runCatching {
            resolver.releasePersistableUriPermission(treeUri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }

    /**
     * Lista as entradas de uma pasta. Devolve a lista REAL, já classificada.
     * @throws SecurityException quando a URI não está autorizada
     */
    suspend fun list(uri: String, limits: Int = MAX_ENTRIES): List<BrowseEntry> = withContext(Dispatchers.IO) {
        val doc = documentOf(uri) ?: throw IllegalArgumentException("Pasta inacessível: $uri")
        if (!doc.isDirectory) throw IllegalArgumentException("Não é uma pasta: ${doc.name ?: uri}")
        if (!doc.canRead()) throw SecurityException("Sem permissão de leitura em ${doc.name ?: uri}")

        doc.listFiles()
            .take(limits)
            .map { child ->
                val name = child.name ?: "(sem nome)"
                val isDir = child.isDirectory
                val classification = FileBrowser.classify(name, child.type)
                BrowseEntry(
                    uri = child.uri.toString(),
                    name = name,
                    isDirectory = isDir,
                    size = if (isDir) 0L else child.length(),
                    lastModified = child.lastModified(),
                    mime = child.type,
                    kind = if (isDir) FileKind.UNKNOWN else classification.kind,
                    action = if (isDir) FileAction.BROWSE else classification.action,
                    reason = if (isDir) "pasta" else classification.reason,
                )
            }
            .let { FileBrowser.sort(it) }
    }

    /** Lê os primeiros bytes reais para confirmação por assinatura. */
    suspend fun head(uri: String, size: Int = FileClassifier.SNIFF_SIZE): ByteArray? = withContext(Dispatchers.IO) {
        runCatching {
            openStream(uri)?.use { input ->
                val buffer = ByteArray(size)
                val read = input.read(buffer)
                if (read <= 0) null else buffer.copyOf(read)
            }
        }.getOrNull()
    }

    /** Abre um stream de leitura para qualquer URI suportada. */
    fun openStream(uri: String): InputStream? = runCatching {
        when {
            uri.startsWith("content://") -> resolver.openInputStream(Uri.parse(uri))
            uri.startsWith("file://") -> Uri.parse(uri).path?.let { File(it).inputStream() }
            uri.startsWith("/") -> File(uri).inputStream()
            else -> null // http(s) não é arquivo: o player resolve
        }
    }.getOrNull()

    /** Copia para um arquivo temporário (ZIP precisa de acesso aleatório). */
    suspend fun localCopyOf(uri: String, name: String): File? = withContext(Dispatchers.IO) {
        runCatching {
            val input = openStream(uri) ?: return@runCatching null
            val ext = name.substringAfterLast('.', "bin").take(8)
            val out = File.createTempFile("smarted-", ".$ext", context.cacheDir)
            input.use { i -> out.outputStream().use { o -> i.copyTo(o) } }
            out
        }.getOrNull()
    }

    /** Metadados do sistema (tamanho, data, tipo) — sem inventar. */
    fun documentOf(uri: String): DocumentFile? = runCatching {
        when {
            uri.startsWith("content://") -> {
                val parsed = Uri.parse(uri)
                if (DocumentsContract.isTreeUri(parsed)) {
                    DocumentFile.fromTreeUri(context, parsed)
                        ?: DocumentFile.fromSingleUri(context, parsed)
                } else {
                    // documento filho de árvore → singleUri resolve para o DocumentFile
                    DocumentFile.fromSingleUri(context, parsed)
                        ?: DocumentFile.fromTreeUri(context, parsed)
                }
            }
            uri.startsWith("file://") -> Uri.parse(uri).path?.let { DocumentFile.fromFile(File(it)) }
            uri.startsWith("/") -> DocumentFile.fromFile(File(uri))
            else -> null
        }
    }.getOrNull()

    /** Nome legível do documento (usado no breadcrumb). */
    fun nameOf(uri: String): String =
        documentOf(uri)?.name?.takeIf { it.isNotBlank() }
            ?: Uri.decode(uri.substringAfterLast('/')).ifBlank { uri }

    companion object {
        /** Limite de itens por pasta (proteção de memória em pastas gigantes). */
        const val MAX_ENTRIES = 5_000

        fun isSafeDocumentUri(uri: String): Boolean {
            if (!uri.startsWith("content://") && !uri.startsWith("file://") && !uri.startsWith("/")) return false
            val lower = uri.lowercase()
            return !lower.contains("../") && !lower.contains("%2e%2e")
        }
    }
}
