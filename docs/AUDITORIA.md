# ETAPA 1 — AUDITORIA TÉCNICA (SmartED-TV)

Data: 2026-11-09 · Branch: `arena/9fe59e16-kode` · Commit auditado: `93b2979`

---

## 1. Arquitetura atual (o que existe de fato)

| Item | Estado real |
|---|---|
| Linguagem / UI | **Kotlin + Jetpack Compose** (Material3), 10 arquivos, **1.195 linhas** |
| Activity | 2: `MainActivity` (Compose) e `PlayerActivity` (Media3 ExoPlayer) |
| Layout | **100% Compose em código**. Não existe `res/layout/`, nem ConstraintLayout |
| Arquitetura | ViewModel único (`MainTvViewModel`) + `SmartedData` (StateFlow) → `SmartedApp` → Scaffold/Screens |
| Persistência | **Nenhuma** (sem Room, sem SQLite, sem DataStore, sem SharedPreferences) |
| Rede | OkHttp **declarado mas não usado**; nenhuma chamada HTTP no código |
| Player | Media3 1.4.1 + HLS. **Sem** `media3-exoplayer-dash`, **sem headers**, **sem escolha de MIME** |
| Imagens | Coil **declarado mas não usado** |
| Build | AGP 8.7.3 / Kotlin 2.1.0 / Gradle 8.10.2 / minSdk 21 / targetSdk 34 (CI em `.github/workflows/build.yml`) |

Dependências declaradas × realmente usadas: **OkHttp e Coil são dependências mortas**.

---

## 2. Compatibilidade com as Partes 1–3 enviadas

### Parte 1 — `AndroidManifest.xml` sugerido

| Item | Situação |
|---|---|
| `android:theme="@style/Theme.SmartedTV"` | ❌ **não existe**. O projeto tem `Theme.SmartEDTV` (arquivo `res/values/themes.xml`) |
| `android:label="Smarted-TV"` | ⚠️ o projeto usa `@string/app_name` = "SmartED-TV" |
| `android:screenOrientation="landscape"` | ⚠️ hoje é `sensorLandscape` + `requestedOrientation` na Activity (funciona nos dois) |
| **Dois `<intent-filter>`** (`LAUNCHER` separado de `LEANBACK_LAUNCHER`) | ❌ **vira dois ícones no launcher**. O correto é **um único filtro** com as duas categorias |
| `allowBackup="true"` | ⚠️ hoje é `false`; mudar reativa backup de dados |
| `uses-permission` (INTERNET/WAKE_LOCK) | ❌ **removidas** no texto sugerido — o app deixaria de ter rede |
| `android:name` da Application | ❌ removido (`SmartEDApp` deixaria de rodar) |

> Veredito: o manifest sugerido **não compila** (tema inexistente) e **quebra** rede/launcher. Mantive o manifest atual e só alinhei a orientação.

### Parte 2 — `MainActivity.kt` sugerido

| Item | Situação |
|---|---|
| `AppCompatActivity` | ❌ **AppCompat não está no projeto** (0 ocorrências em build.gradle) |
| `setContentView(R.layout.activity_main)` | ❌ **`res/layout/` não existe** — o app é Compose |
| `R.color.black` | ❌ **não existe** (as cores são `smarted_*`) |
| `window.decorView.systemUiVisibility` | ⚠️ API depreciada desde Android 11 |
| Efeito | **Crash imediato** (`ClassNotFoundException`/`Resources$NotFoundException`) |

> Veredito: aplicar a Parte 2 significa **abandonar o Compose** — reescrita total, proibida pelas regras. A Activity atual já faz orientação + imersão de forma correta.

### Parte 3 — `activity_main.xml` sugerido

Recursos **inexistentes** no projeto: `@style/SmartedMenuItem`, `@drawable/bg_content` — não compila.
Além disso:
- `androidx.constraintlayout` **não está** nas dependências;
- o layout traz `menuHome/menuChannels/menuMovies/menuSeries/menuBrowse/menuSettings` e um `FrameLayout` vazio: **não há conexão com nenhuma tela** (o próprio texto admite);
- **regressão funcional**: as 12 seções do Kodi e todas as telas atuais (Vídeos, Música, Programas, Rádio, Jogos, Imagens, Clima, Favoritos, Add-ons, Configurações com toggles reais) **desapareceriam**;
- os "ícones" são caracteres Unicode (`⌂ ▣ ▶ ▤ ⚙`), sem foco D-pad e sem estado;
- recriaria o menu conceitual de IPTV (TV ao vivo / Filmes / Séries / Navegador), contrariando a etapa anterior do usuário.

> Veredito: adotar a Parte 3 = substituir a UI inteira por uma tela **estática e vazia**, sem as funções exigidas nas Etapas 3–9. **Não adotada** (mantive identidade visual + navegação, como pede "PRESERVE a interface atual").

---

## 3. O erro `"Nenhum arquivo .m3u/.m3u8 encontrado na pasta."`

**Essa mensagem não existe neste repositório.** Busca completa (código, XML, strings, assets): 0 ocorrências.

Ocorrências de "m3u" no projeto: 5, todas em `MainTvViewModel.loadDemoData()` como **URLs de demonstração** (`test-streams.mux.dev`). Não há leitura de pasta, nem filtro de extensão.

**Conclusão técnica:** a mensagem vem de **outro binário** — muito provavelmente um dos APKs `SmartED-TV-3.0.0.xxx` do histórico do aparelho (MediaFire). Diagnóstico do fluxo alegado:

> "o sistema trata qualquer repositório como pasta de listas M3U" — **não é o caso aqui**, porque **não existe** descoberta de arquivos, importação de repositório, leitura de ZIP, parsing de playlist nem `addon.xml`. Não há o que corrigir: **precisa ser construído**.

### O que realmente falta (100% ausente)

| Componente | Estado |
|---|---|
| Leitura de ZIP (`ZipFile`/`ZipInputStream`) | ❌ inexistente |
| Importação/gerenciamento de repositórios | ❌ inexistente |
| Parsing de `addon.xml` | ❌ inexistente |
| Parser de M3U/M3U8/PLS/XSPF/ASX/WPL/CUE/STRM | ❌ inexistente |
| Classificação de arquivos (extensão/MIME/conteúdo) | ❌ inexistente |
| Navegador de diretórios (SAF/`DocumentFile`) | ❌ inexistente — a tela "Arquivos" mostra **2 pastas hardcoded** ("Armazenamento interno", "Downloads") |
| `plugin://` / adaptadores de plugin | ❌ inexistente |
| Banco de dados / persistência | ❌ inexistente |
| Reprodução com MIME/headers/DASH | ❌ parcial: só `MediaItem.fromUri()` + HLS |

---

## 4. Causas prováveis do que o usuário está vendo

1. **APK antigo**: instalou `SmartED-TV-1.0.6` sobre um app que já tinha outra assinatura, ou abriu um APK 3.0.0 anterior → mensagens que não existem neste código.
2. **`this.assets` vazio**: não há `assets/` no APK (o motor de layout XML foi removido na integração do pacote de design). Nenhum recurso embarcado → qualquer leitura de "layout em assets" falha silenciosamente.
3. **Dados de demonstração**: Canais/Filmes/Séries vêm de `loadDemoData()` com streams públicos do Mux. Não é fonte real, e o usuário classificou como "demo".
4. **Sem descoberta de conteúdo**: telas de Música/Rádio/Jogos/etc. são listas vazias por construção (não há repositório).

---

## 5. Componentes a criar/alterar (plano mínimo, sem reescrita)

**Novos pacotes** (Camada de dados pura Kotlin, testável com JUnit na JVM, sem Android):

```
data/source/        FileClassifier (ext+MIME+magic bytes) · PlaylistParser (m3u/m3u8/pls/xspf/asx/wpl/cue) · MimeMap
data/repository/    RepositoryNode (id,name,type,path,parentId,children,metadata,capabilities,source,
                                    isDirectory,isPlayable,isInstallable) · RepositoryScanner · ZipInspector
data/addon/         AddonManifestParser (addon.xml) · AddonCatalog (video/program/music/skin/metadata/service/
                    subtitle/repository/module) · CompatibilityEvaluator (4 níveis)
data/plugin/        PluginRouter (plugin://id?action=...) · PluginAdapter (interface) · UnsupportedAdapter
data/local/         LocalFileBrowser (DocumentFile/SAF) · StorageAccess
platform/           RepoStore (persistência: repositórios, add-ons instalados, fontes)
```

**Alterações cirúrgicas em arquivos existentes**

| Arquivo | Mudança |
|---|---|
| `PlayerActivity.kt` | `DefaultMediaSourceFactory` + MIME explícito (HLS/DASH/SS), `DefaultHttpDataSource.Factory` com headers, `media3-exoplayer-dash` |
| `build.gradle.kts` | `+media3-exoplayer-dash`, `+documentfile`, `+junit` (test) |
| `MainTvViewModel.kt` | `loadDemoData()` **vira opcional/desligado por padrão**; dados passam a vir de repositórios + SAF |
| `SmartedApp.kt` | rotas novas `screen:repositorios` e navegação do plugin/arquivo |
| `Screens.kt` | telas de Repositórios, detecção de arquivos, info de add-on (ícones reais via Coil) |
| `AndroidManifest.xml` | **manter** o atual (rede + app name + single intent-filter com LAUNCHER+LEANBACK) |

**Não será feito**: trocar Compose por XML/ConstraintLayout, remover AppCompat inexistente, duplicar ícones no launcher.

---

## 6. Limitações estruturais que precisam ser ditas antes

1. **Add-ons Python do Kodi não executam** em Android sem runtime. Implementável: navegação e parsing; **não implementável** sem custo alto: executar `default.py`/Kodi API. Classificação será honesta: `COMPATIBLE` / `COMPATIBLE_WITH_ADAPTATION` / `PARTIAL` / `NOT_COMPATIBLE`.
2. **`plugin://` sem add-on executável não retorna itens**. O router resolve o caminho, mas se o add-on é Python dependente de `xbmc*`, retorna lista vazia + motivo explícito (sem simular resultados).
3. **DRM / codecs proprietários** (Widevine L1, AC-3/DTS em alguns aparelhos): serão sinalizados, não contornados.
4. **`.7z`/`.rar`**: exigem biblioteca extra (Apache Commons Compress só tem 7z; RAR é patenteado) — ficam como "não suportado" declarado.
5. **Testes reais** (Etapa 10): o sandbox **não tem JDK/Android SDK nem acesso a repositórios externos**. Testes de unidade JVM rodarão no CI (GitHub Actions); testes instrumentados exigem aparelho.

---

## 7. Proposta de execução incremental

| Fase | Entrega | Validável |
|---|---|---|
| **A** | `FileClassifier` + `MimeMap` + `PlaylistParser` (m3u/m3u8/pls/xspf/asx/wpl/cue/strm) + testes JVM | `./gradlew test` (CI) |
| **B** | `ZipInspector` (Zip Slip, path traversal, limites) + `AddonManifestParser` + `AddonCatalog` + `CompatibilityEvaluator` + testes | CI |
| **C** | `LocalFileBrowser` (SAF real, breadcrumbs, ordenação, busca) + tela Arquivos | APK |
| **D** | `RepoStore` + importar repositório (ZIP/URL) + `RepositoryScanner` + `RepositoryNode` + tela Repositórios | APK |
| **E** | Tela Add-ons por categoria com ícones reais + info + compatibilidade | APK |
| **F** | `PluginRouter` + adaptadores + player com MIME/headers/DASH | APK |
| **G** | Testes de integração (fixtures ZIP sintéticos gerados nos testes, sem dados fictícios no app) + release | CI + APK |

**Nenhum dado fictício no app**: as listas passam a vir de SAF/repositórios; o demo atual será removido do caminho padrão.

---

## 8. Decisão necessária do usuário

1. Confirma que **não adoto as Partes 1–3** (manifest/AppCompat/XML) e sigo com Compose, mantendo o visual? *(recomendado)*
2. O APK que mostra `"Nenhum arquivo .m3u/.m3u8"` é o **1.0.6** ou um **3.0.0.xxx** antigo? Preciso saber qual binário é a base.
3. Posso iniciar na **Fase A** agora (parsers + testes no CI), avançando fase por fase com evidência de build?
