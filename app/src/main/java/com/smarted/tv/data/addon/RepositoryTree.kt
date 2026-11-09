package com.smarted.tv.data.addon

/**
 * Monta a árvore de um repositório a partir do catálogo real (`addons.xml`)
 * e da lista real de arquivos (quando o repositório veio de ZIP/pasta).
 *
 * Nada é presumido:
 *  - as categorias saem do tipo real de cada add-on ([CompatibilityEvaluator.kindOf]);
 *  - um add-on só entra como INSTALLABLE se o pacote existir de fato
 *    (`<id>/<id>-<versão>.zip` encontrado na lista de arquivos), senão continua
 *    visível mas sem a capacidade INSTALL — e o motivo fica registrado;
 *  - arquivos/pastas que não são add-on aparecem como FOLDER/FILE.
 */
object RepositoryTree {

    /** Categoria exibida (Kodi: "Add-ons de vídeo", "Programas", ...). */
    fun categoryLabel(kind: AddonKind): String = when (kind) {
        AddonKind.VIDEO -> "Add-ons de vídeo"
        AddonKind.AUDIO -> "Add-ons de música"
        AddonKind.PROGRAM -> "Programas"
        AddonKind.SKIN -> "Skins (aparência)"
        AddonKind.METADATA -> "Informações / metadados"
        AddonKind.SERVICE -> "Serviços"
        AddonKind.SUBTITLE -> "Legendas"
        AddonKind.REPOSITORY -> "Repositórios"
        AddonKind.MODULE -> "Módulos Python"
        AddonKind.MODULE_LIB -> "Bibliotecas / recursos"
        AddonKind.UNKNOWN -> "Não classificados"
    }

    /**
     * @param repoId id do repositório (id do add-on repository.* ou o nome do ZIP)
     * @param repoName nome exibido
     * @param manifests catálogo lido de addons.xml
     * @param filePaths caminhos reais dentro do repositório (ZIP/pasta); vazio para repositório por URL
     * @param source origem real
     */
    fun build(
        repoId: String,
        repoName: String,
        manifests: List<AddonManifest>,
        filePaths: List<String>,
        source: RepoSource,
    ): RepositoryNode {
        val fileSet = filePaths.map { it.replace('\\', '/') }
        val lowerFiles = fileSet.map { it.lowercase() }.toSet()

        // Categoriza respeitando o tipo real declarado por cada add-on.
        val byKind = manifests.groupBy { CompatibilityEvaluator.kindOf(it) }

        val categories = byKind.entries
            .sortedBy { it.key.ordinal }
            .map { (kind, list) ->
                val addons = list
                    .distinctBy { it.id }
                    .sortedBy { it.name.lowercase() }
                    .map { manifest -> addonNode(manifest, kind, fileSet, lowerFiles, source, repoId) }

                RepositoryNode(
                    id = "$repoId::cat::${kind.name}",
                    name = categoryLabel(kind),
                    type = RepoNodeType.CATEGORY,
                    path = kind.name,
                    parentId = repoId,
                    children = addons,
                    metadata = mapOf("count" to addons.size.toString()),
                    capabilities = setOf(RepositoryNode.Capability.BROWSE),
                    source = source,
                    isDirectory = true,
                )
            }

        // Qualquer arquivo que não pertença a um add-on conhecido continua visível.
        val knownPrefixes = manifests.map { it.id.lowercase() }
        val extras = fileSet
            .filter { path -> knownPrefixes.none { path.lowercase().startsWith("$it/") || path.lowercase() == it } }
            .filterNot { it.lowercase().endsWith("addons.xml") || it.lowercase().endsWith("addons.xml.md5") }
            .distinct()

        // Pastas-mãe reais dos arquivos extras (derivadas dos caminhos, não inventadas)
        val extraDirs = extras
            .flatMap { path ->
                val parts = path.split('/')
                (1 until parts.size).map { parts.take(it).joinToString("/") }
            }
            .distinct()

        val extraNodes = (extraDirs.map { RepositoryNode(
            id = "$repoId::extra::$it",
            name = it.substringAfterLast('/'),
            type = RepoNodeType.FOLDER,
            path = it,
            parentId = repoId,
            metadata = mapOf("motivo" to "Pasta do repositório fora do catálogo de add-ons"),
            capabilities = setOf(RepositoryNode.Capability.LOCAL_FILE),
            source = source,
            isDirectory = true,
        ) } + extras.take(MAX_EXTRA).map { path ->
            val isDir = extraDirs.contains(path)
            RepositoryNode(
                id = "$repoId::extra::$path",
                name = path.substringAfterLast('/'),
                type = if (isDir) RepoNodeType.FOLDER else RepoNodeType.FILE,
                path = path,
                parentId = repoId,
                metadata = mapOf("motivo" to "Arquivo do repositório fora do catálogo de add-ons"),
                capabilities = setOf(RepositoryNode.Capability.LOCAL_FILE),
                source = source,
                isDirectory = isDir,
            )
        }).sortedWith(compareByDescending<RepositoryNode> { it.isDirectory }.thenBy { it.path })

        return RepositoryNode(
            id = repoId,
            name = repoName,
            type = RepoNodeType.REPOSITORY,
            path = "",
            children = categories + extraNodes,
            metadata = mapOf(
                "addons" to manifests.size.toString(),
                "categorias" to categories.size.toString(),
                "arquivos" to filePaths.size.toString(),
            ),
            capabilities = setOf(RepositoryNode.Capability.BROWSE, RepositoryNode.Capability.INSPECT),
            source = source,
            isDirectory = true,
        )
    }

    private const val MAX_EXTRA = 200

    private fun addonNode(
        manifest: AddonManifest,
        kind: AddonKind,
        filePaths: List<String>,
        lowerFiles: Set<String>,
        source: RepoSource,
        repoId: String,
    ): RepositoryNode {
        val report = CompatibilityEvaluator.evaluate(manifest, kind)

        // Pacote real: <id>/<id>-<versão>.zip (convenção do Kodi) ou qualquer
        // zip dentro da pasta do add-on.
        val version = manifest.version
        val candidates = listOf(
            "${manifest.id}/${manifest.id}-$version.zip",
            "${manifest.id}-$version.zip",
        ).map { it.lowercase() }
        val pacoteReal = candidates.firstOrNull { lowerFiles.contains(it) }
            ?: filePaths.firstOrNull {
                val low = it.lowercase()
                low.startsWith("${manifest.id.lowercase()}/") && low.endsWith(".zip")
            }

        val capabilities = mutableSetOf(RepositoryNode.Capability.INSPECT, RepositoryNode.Capability.BROWSE)
        if (pacoteReal != null) capabilities += RepositoryNode.Capability.INSTALL
        if (report.level == Compatibility.PARTIAL || report.level == Compatibility.COMPATIBLE_WITH_ADAPTATION) {
            capabilities += RepositoryNode.Capability.CONFIGURE
        }
        if (kind == AddonKind.VIDEO || kind == AddonKind.AUDIO) capabilities += RepositoryNode.Capability.PLAY
        capabilities += if (source.kind == RepoSource.SourceKind.URL) {
            RepositoryNode.Capability.REMOTE
        } else {
            RepositoryNode.Capability.LOCAL_FILE
        }

        val meta = mutableMapOf(
            "id" to manifest.id,
            "version" to manifest.version,
            "kind" to kind.name,
            "compatibility" to report.level.name,
            "compatibilityReasons" to report.reasons.joinToString(" | "),
            "missing" to report.missing.joinToString(" | "),
            "extensionPoint" to manifest.extensionPoint,
            "libraries" to manifest.libraries.joinToString(", "),
        )
        manifest.providerName?.let { meta["provider"] = it }
        manifest.description?.let { meta["description"] = it }
        manifest.summary?.let { meta["summary"] = it }
        manifest.requiresKodi?.let { meta["requiresKodi"] = it }
        manifest.entryPoint?.let { meta["entryPoint"] = it }
        if (pacoteReal != null) meta["package"] = pacoteReal else {
            meta["installBlocked"] = if (source.kind == RepoSource.SourceKind.URL) {
                "Pacote remoto: precisa baixar ${manifest.id}/${manifest.id}-$version.zip"
            } else {
                "Pacote ${manifest.id}-$version.zip não encontrado no repositório"
            }
        }

        return RepositoryNode(
            id = "$repoId::addon::${manifest.id}",
            name = manifest.name,
            type = RepoNodeType.ADDON,
            path = pacoteReal ?: manifest.id,
            parentId = "$repoId::cat::${kind.name}",
            metadata = meta,
            capabilities = capabilities,
            source = source,
            isInstallable = pacoteReal != null,
            isPlayable = kind == AddonKind.VIDEO || kind == AddonKind.AUDIO,
        )
    }

    /** Busca recursiva por id (usada ao abrir um nó específico). */
    fun find(root: RepositoryNode, id: String): RepositoryNode? {
        if (root.id == id) return root
        root.children.forEach { child ->
            find(child, id)?.let { return it }
        }
        return null
    }

    /** Caminho da raiz até o nó (para breadcrumb). */
    fun pathTo(root: RepositoryNode, id: String): List<RepositoryNode> {
        if (root.id == id) return listOf(root)
        root.children.forEach { child ->
            val sub = pathTo(child, id)
            if (sub.isNotEmpty()) return listOf(root) + sub
        }
        return emptyList()
    }
}
