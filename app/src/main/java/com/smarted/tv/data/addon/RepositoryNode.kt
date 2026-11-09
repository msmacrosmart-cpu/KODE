package com.smarted.tv.data.addon

/**
 * Tipo de nó da árvore de um repositório (o que o nó É, não o que gostaríamos).
 */
enum class RepoNodeType {
    REPOSITORY,   // raiz do repositório
    CATEGORY,     // agrupamento por tipo de add-on
    ADDON,        // pacote instalável
    FOLDER,       // pasta interna do repositório
    FILE,         // arquivo dentro do repositório
    UNKNOWN,
}

/**
 * Caminho/endereço de onde o nó veio ([source] não é URL inventada: é a origem
 * real do dado — URL do repositório, ZIP local ou árvore SAF).
 */
data class RepoSource(val kind: SourceKind, val location: String) {
    enum class SourceKind { URL, ZIP, FOLDER, INSTALLED }
}

/**
 * Árvore dinâmica de repositório — nenhum nível é presumido pela estrutura.
 *
 * @param path caminho relativo dentro do repositório (ou URL do pacote)
 * @param children subnós, na ordem em que o repositório declara
 */
data class RepositoryNode(
    val id: String,
    val name: String,
    val type: RepoNodeType,
    val path: String = "",
    val parentId: String? = null,
    val children: List<RepositoryNode> = emptyList(),
    val metadata: Map<String, String> = emptyMap(),
    val capabilities: Set<Capability> = emptySet(),
    val source: RepoSource,
    val isDirectory: Boolean = false,
    val isPlayable: Boolean = false,
    val isInstallable: Boolean = false,
) {
    enum class Capability {
        BROWSE,       // dá para navegar
        INSPECT,      // dá para ler metadados
        INSTALL,      // dá para instalar (compatibilidade respeitada)
        UPDATE,       // há versão diferente instalada
        CONFIGURE,    // tem settings
        PLAY,         // produz reprodução
        LOCAL_FILE,   // o conteúdo está no aparelho
        REMOTE,       // o conteúdo está na rede
    }

    /** Versão do add-on, quando existir. */
    val version: String? get() = metadata["version"]

    /** Compatibilidade declarada (só para ADDON). */
    val compatibility: Compatibility? get() = metadata["compatibility"]?.let { raw ->
        runCatching { Compatibility.valueOf(raw) }.getOrNull()
    }

    fun childById(id: String): RepositoryNode? = children.firstOrNull { it.id == id }
}
