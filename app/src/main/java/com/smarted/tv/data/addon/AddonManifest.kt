package com.smarted.tv.data.addon

/**
 * Modelo do `addon.xml` do Kodi (real, não inventado).
 * Campos opcionais refletem o que o arquivo realmente pode omitir.
 */
data class AddonManifest(
    val id: String,
    val name: String,
    val version: String,
    val providerName: String? = null,
    val description: String? = null,
    val summary: String? = null,
    val disclaimer: String? = null,
    val news: String? = null,
    val extensionPoint: String,          // ex.: xbmc.python.pluginsource, xbmc.python.script, xbmc.gui.skin
    val libraries: List<String> = emptyList(),   // ex.: resource.language.pt_br, script.module.requests
    val requiresKodi: String? = null,            // ex.: "19.0.0" (import version=)
    val entryPoint: String? = null,              // ex.: default.py, plugin.py
    val providedBy: String? = null,              // ex.: <provides>video</provides>
    val metadata: Map<String, String> = emptyMap(),
    val warnings: List<String> = emptyList(),
)

/** Categoria funcional derivada do `extension point` (não do nome do pacote). */
enum class AddonKind {
    VIDEO,        // xbmc.python.pluginsource provides=video, xbmc.addon.video
    AUDIO,        // provides=audio / music
    PROGRAM,      // xbmc.python.script / provides=executable
    SKIN,         // xbmc.gui.skin
    METADATA,     // xbmc.metadata.scraper.*
    SUBTITLE,     // xbmc.subtitle.module
    SERVICE,      // xbmc.service
    REPOSITORY,   // xbmc.addon.repository
    MODULE,       // xbmc.python.module / script.module.*
    MODULE_LIB,   // resource.* / script.module.* (dependências)
    UNKNOWN,
}

/**
 * Compatibilidade REAL com este app (Android/Compose, sem runtime XBMC).
 *
 * 1. COMPATIBLE             — recursos que o app sabe consumir (ex.: repositório, skin descritiva, metadados)
 * 2. COMPATIBLE_WITH_ADAPTATION — precisa de camada (ex.: plugin que só resolve URLs HTTP sem API do Kodi)
 * 3. PARTIAL                — só parte do conteúdo é utilizável
 * 4. NOT_COMPATIBLE         — depende de runtime/API exclusiva do Kodi
 */
enum class Compatibility {
    COMPATIBLE,
    COMPATIBLE_WITH_ADAPTATION,
    PARTIAL,
    NOT_COMPATIBLE,
}

data class CompatibilityReport(
    val level: Compatibility,
    val reasons: List<String>,
    val missing: List<String> = emptyList(),
)

/**
 * Avalia compatibilidade sem mentir: encontrar `addon.xml` não habilita execução.
 *
 * Base: add-ons Kodi são Python chamando a API `xbmc*`. Este app não embarca
 * interpretador Python nem ponte XBMC, portanto:
 *  - REPOSITORY: compatível (é só XML/estrutura de download).
 *  - SKIN: parcial (a skin é XML/PNG, mas o motor de skin do Kodi não existe aqui).
 *  - METADATA/SUBTITLE: parcial (parser teria de ser implementado).
 *  - VIDEO/AUDIO/PROGRAM com `xbmc.python.*`: NÃO compatível hoje
 *    (ver `docs/LIMITACOES.md`), a menos que o plugin só produza URLs diretas
 *    reconhecidas por um adaptador — logo, COMPATIBLE_WITH_ADAPTATION quando há
 *    `plugin://` mapeável.
 */
object CompatibilityEvaluator {

    fun evaluate(manifest: AddonManifest, kind: AddonKind): CompatibilityReport {
        val reasons = mutableListOf<String>()
        val missing = mutableListOf<String>()

        return when (kind) {
            AddonKind.REPOSITORY -> {
                reasons += "Repositório do Kodi é apenas XML/estrutura de download — o app consegue ler e baixar pacotes."
                CompatibilityReport(Compatibility.COMPATIBLE, reasons)
            }

            AddonKind.SKIN -> {
                reasons += "Skin do Kodi é declarativa (XML + imagens), mas o motor de skin (xbmc.gui) não existe neste app."
                missing += "Interpretador de skin (xbmc.gui)"
                CompatibilityReport(Compatibility.PARTIAL, reasons, missing)
            }

            AddonKind.METADATA, AddonKind.SUBTITLE -> {
                reasons += "O add-on é um módulo de scraping/legendas acionado pela API do Kodi."
                missing += "Ponte de chamada (xbmc.python) e contrato de scraper"
                CompatibilityReport(Compatibility.PARTIAL, reasons, missing)
            }

            AddonKind.MODULE, AddonKind.MODULE_LIB -> {
                reasons += "Módulo/dependência Python: pode ser lido e instalado como arquivo."
                missing += "Runtime Python + API xbmc*"
                CompatibilityReport(Compatibility.NOT_COMPATIBLE, reasons, missing)
            }

            AddonKind.VIDEO, AddonKind.AUDIO, AddonKind.PROGRAM -> {
                val isPython = manifest.extensionPoint.startsWith("xbmc.python")
                if (isPython) {
                    reasons += "Add-on Python (${manifest.extensionPoint}): a navegação é gerada em tempo de execução pela API xbmc*."
                    missing += "Runtime Python 3 + ponte xbmcplugin/xbmcgui/xbmcaddon"
                    // Se só resolve URLs diretas e não usa API de GUI, um adaptador pode cobrir.
                    CompatibilityReport(Compatibility.COMPATIBLE_WITH_ADAPTATION, reasons, missing)
                } else {
                    reasons += "Tipo ${manifest.extensionPoint} pode ser descrito por metadados."
                    CompletableOrPartial(reasons, missing)
                }
            }

            AddonKind.SERVICE -> {
                reasons += "Serviço do Kodi roda em segundo plano via API xbmc*."
                missing += "Runtime Python + ciclo de vida de serviço do Kodi"
                CompatibilityReport(Compatibility.NOT_COMPATIBLE, reasons, missing)
            }

            AddonKind.UNKNOWN -> {
                reasons += "Ponto de extensão não reconhecido: ${manifest.extensionPoint}"
                missing += "Especificação do tipo de add-on"
                CompatibilityReport(Compatibility.NOT_COMPATIBLE, reasons, missing)
            }
        }
    }

    private fun CompletableOrPartial(reasons: List<String>, missing: List<String>): CompatibilityReport {
        missing += "Contrato específico do ponto de extensão"
        return CompatibilityReport(Compatibility.PARTIAL, reasons, missing)
    }

    /** Deriva a categoria a partir do extension point / provides (dados reais). */
    fun kindOf(manifest: AddonManifest): AddonKind {
        val ep = manifest.extensionPoint.lowercase()
        val provides = manifest.providedBy?.lowercase().orEmpty()
        val id = manifest.id.lowercase()

        return when {
            ep.contains("repository") || id.startsWith("repository.") -> AddonKind.REPOSITORY
            ep.contains("gui.skin") -> AddonKind.SKIN
            ep.contains("metadata.scraper") -> AddonKind.METADATA
            ep.contains("subtitle") -> AddonKind.SUBTITLE
            ep.contains("service") -> AddonKind.SERVICE
            ep.contains("pluginsource") && provides.contains("video") -> AddonKind.VIDEO
            ep.contains("pluginsource") && (provides.contains("audio") || provides.contains("music")) -> AddonKind.AUDIO
            ep.contains("pluginsource") && provides.contains("executable") -> AddonKind.PROGRAM
            ep.contains("pluginsource") -> AddonKind.VIDEO
            ep.contains("script") && id.startsWith("script.module") -> AddonKind.MODULE
            ep.contains("script") -> AddonKind.PROGRAM
            ep.contains("python.module") -> AddonKind.MODULE
            id.startsWith("resource.") || id.startsWith("script.module.") -> AddonKind.MODULE_LIB
            else -> AddonKind.UNKNOWN
        }
    }
}
