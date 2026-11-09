# SmartED-TV — Fases B a G (paridade funcional com o Kodi)

Relatório de execução das etapas 2 a 11 do pedido
**"SISTEMA COMPLETO DE NAVEGAÇÃO, REPOSITÓRIOS E ADD-ONS COM PARIDADE FUNCIONAL AO KODI"**.
Complementa `docs/AUDITORIA.md` (etapa 1) e `docs/LIMITACOES.md` (o que ainda não roda).

> Regra seguida em todo o trabalho: **nenhum dado fictício**. Sem `addons.xml` válido não há
> repositório; sem `addon.xml` não há add-on; sem adaptador registrado não há listagem de `plugin://`.
> Quando algo não é possível, a tela mostra o motivo técnico.

---

## O que foi entregue, por etapa

| Etapa | Pedido | Entregue | Onde (arquivo) |
|---|---|---|---|
| 1 | Diagnóstico antes do código | `docs/AUDITORIA.md`: 10 arquivos / 1.195 linhas originais, sem ZIP/SAF/plugin/repo | `docs/AUDITORIA.md` |
| 2 | Identificar arquivos por extensão + conteúdo + MIME + contexto | Classificador central com 17 categorias, 5 ações, magic bytes, MIME por sistema e heurística de URL | `data/source/MimeMap.kt`, `FileClassifier.kt` |
| 2 | Cada formato de playlist com seu parser | M3U/M3U8, HLS master (variantes), HLS mídia, MPD, PLS, XSPF, ASX, WPL, CUE, STRM | `data/source/PlaylistParser.kt` |
| 3 | Navegador de arquivos real | Entrar/subir/breadcrumb clicável/histórico/favoritos/ordenação (nome, tipo, data, tamanho)/busca na pasta/atualizar/info/diagnóstico de erro | `data/source/FileBrowser.kt`, `SafFileSystem.kt`, `viewmodel/FilesViewModel.kt`, `ui/screens/FilesScreen.kt` |
| 4 | Gerenciador de repositórios | Adicionar por URL, importar ZIP, catálogo `addons.xml`, árvore `RepositoryNode`, habilitar/remover, recarregar, erros reais | `data/addon/{RepoIndexParser,RepositoryClient,RepositoryTree,RepositoryStore}.kt` |
| 5 | Todos os tipos de add-on + compatibilidade em 4 níveis | 11 tipos (`VIDEO`…`MODULE_LIB`), avaliação honesta com razões e dependências ausentes | `data/addon/AddonManifest.kt` |
| 6 | ZIP: inspeção, extração segura, instalação, registro | Zip Slip/traversal/absoluto/unidade/NUL/profundidade, limites de entrada/bytes/compressão, extração confinada, registro de instalados | `data/archive/ZipInspector.kt`, `data/addon/AddonInstaller.kt` |
| 7 | UI estilo Kodi + `plugin://` virtual | Abas Instalados/Repositórios/Instalar de ZIP, categorias reais, selo de compatibilidade, detalhe com arquivos instalados; roteador `plugin://` com contrato de adaptador | `ui/screens/{AddonsScreen,PluginScreen}.kt`, `data/plugin/*` |
| 8 | Reprodução real | HLS, DASH, progressive, áudio, local (`content://`), URL direta, cabeçalhos HTTP, MIME explícito, mensagens de DRM/codec/protocolo | `ui/player/{MediaSource,PlayerActivity}.kt` |
| 9 | Telas e D-pad | Telas existentes preservadas; novos fluxos em Compose com foco de D-pad (`FocusCard`), estados de vazio/carregando/erro | `ui/screens/*` |
| 10 | Testes reais | 92 testes JVM (classificador, parsers, ZIP, addon.xml, árvore, plugin, player, integração ponta a ponta) | `app/src/test/java/...` |
| 11 | Conclusão só com evidência | CI verde, APK 1.0.7 assinado, limitações declaradas | `docs/LIMITACOES.md` |

---

## Decisões técnicas que mudaram o app

1. **Nada de pastas fixas.** As duas pastas de exemplo ("Armazenamento interno", "Downloads") foram
   removidas do `MainTvViewModel`. A tela Arquivos lista apenas árvores autorizadas pelo usuário
   via SAF (`ACTION_OPEN_DOCUMENT_TREE`), com permissão persistida.
2. **Duas etapas na instalação.** O ZIP é primeiro **inspecionado** (manifesto, dependências,
   compatibilidade) e só depois, com confirmação, extraído. Pacote não compatível só instala como
   arquivo, com aviso explícito.
3. **`addon.xml` deixa de ser sinônimo de "funciona".** `CompatibilityEvaluator` devolve
   `COMPATIBLE` / `COMPATIBLE_WITH_ADAPTATION` / `PARTIAL` / `NOT_COMPATIBLE` e a UI mostra o selo +
   o que falta (ex.: "Runtime Python 3 + ponte xbmcplugin/xbmcgui/xbmcaddon").
4. **`plugin://` tem adaptador, não simulação.** `PluginRouter` exige add-on instalado **e** um
   `PluginAdapter` registrado. O adaptador incluído (`LocalFolderPluginAdapter`) lista o conteúdo
   real de uma pasta autorizada — o único caso em que este app consegue produzir itens verificáveis.
5. **Player com `MediaSource` explícito.** Antes era `MediaItem.fromUri` (sem DASH, sem headers, sem
   MIME para URL sem extensão). Agora `MediaSourceSpec` decide HLS/DASH/progressive e aplica
   `DefaultHttpDataSource` com os cabeçalhos que a fonte exigir.

## Dois bugs reais encontrados pelo teste de integração

| Bug | Impacto | Correção |
|---|---|---|
| Vídeo binário contendo `<` era classificado como XML (arquivo `.mkv` virava `CONFIG`) | arquivo não abria no player | `FileClassifier` só trata como XML quando há tag fechada nos primeiros 200 bytes |
| Master HLS devolvia variantes relativas (`720p/index.m3u8`) sem resolver | variante nunca tocava | `PlaylistParser.parseHls(text, baseUrl)` resolve com `java.net.URI#resolve`, preservando a query string |

## Evidência de teste

- **92 testes JVM**, executados em `gradle test` no CI a cada push.
- Suites: `FileClassifierTest` (18), `PlaylistParserTest` (14), `FileBrowserTest` (11),
  `ZipInspectorTest` (8), `AddonManifestParserTest` (11), `RepositoryTreeTest` (9),
  `AddonPackageRulesTest` (4), `PluginUriTest` (7), `MediaSourceSpecTest` (7),
  `EndToEndFlowTest` (3).
- O teste de integração percorre: ZIP de repositório → `ZipInspector` → `addons.xml` → árvore com
  categorias → pacote interno é add-on válido → `plugin://` sem adaptador devolve limite real.
- Artefatos do CI: `SmartED-TV-apk` (~88,8 MB) e `test-reports` (~68 KB).

## Onde ainda há limite (e por quê)

Ver `docs/LIMITACOES.md`. Resumo: não há runtime Python/xbmc*; por isso add-ons Python aparecem
como **requer adaptação** e o `plugin://` deles não é navegável. RAR/7z não são lidos. DRM não é
tratado nem contornado. DNS/proxy/credenciais de fontes externas são responsabilidade do usuário.
