# SmartED-TV - KODE

Aplicativo de IPTV para Android TV / TV Box com layout baseado no **MakroTV.XtreamYT** (sem YouTube) e menu de Configurações com todas as opções do **TV Eminem**.

## Layout Implementado (baseado no MakroTV.XtreamYT)

```
┌─────────────────────────────────────────────────────────┐
│ [Logo] SmartED-TV                          [Hamburguer] │  ← Header fixo
├──────────┬───────────────────────────────────────────────┤
│          │                                               │
│  [Ícone] │   Dashboard / Canais / Filmes / Séries        │
│  Início  │                                               │
│          │                                               │
│  [Ícone] │   Cards com ícones coloridos                  │
│  Canais  │   • Canais TV (Coral)                         │
│          │   • Filmes (Laranja)                          │
│  [Ícone] │   • Séries (Amarelo)                          │
│  Filmes  │                                               │
│          │                                               │
│  [Ícone] │   Configurações (menu TV Eminem):             │
│  Séries  │   • Conta e Perfil                            │
│          │   • Rede e Internet                           │
│  [Ícone] │   • Player de Vídeo                           │
│  Addons  │   • EPG e Programa                            │
│          │   • Parental Controls                         │
│  [Ícone] │   • Aparência e Tema                          │
│  Navegar │   • Idioma e Região                           │
│  Pastas  │   • Armazenamento                             │
│          │   • Sobre o Aplicativo                        │
│  [Ícone] │                                               │
│  Config  │                                               │
│  [Ícone] │                                               │
│  Sair    │                                               │
│          │                                               │
└──────────┴───────────────────────────────────────────────┘
```

### Principais características
- **Botão hambúrguer** ao lado do logo "SmartED-TV" (abre todas as opções estilo Kodi)
- **Sem YouTube** (removido conforme solicitado)
- **Navigation Rail lateral** com: Início, Canais, Filmes, Séries, Addons, Navegar Pastas, Configurações, Sair
- **Cards rápidos** no Dashboard com contadores
- **Configurações** com menu completo do TV Eminem (9 itens)
- Suporte Android TV / TV Box (leanback, D-pad, modo paisagem)
- Tema escuro com destaques coral/laranja/amarelo

## Estrutura do Projeto

```
KODE/
├── app/
│   ├── build.gradle.kts
│   ├── proguard-rules.pro
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/smarted/tv/
│       │   ├── SmartEDApp.kt
│       │   ├── MainActivity.kt
│       │   ├── ui/
│       │   │   ├── screens/
│       │   │   │   ├── AppScreen.kt        # Layout principal (Header + Rail + Conteúdo)
│       │   │   │   ├── DashboardScreen.kt
│       │   │   │   ├── LiveTvScreen.kt     # Canais (sem YouTube)
│       │   │   │   ├── VodScreen.kt        # Filmes
│       │   │   │   ├── SeriesScreen.kt     # Séries
│       │   │   │   ├── AddonsScreen.kt
│       │   │   │   ├── ToolsScreen.kt      # Navegar Pastas
│       │   │   │   ├── SettingsScreen.kt   # Configurações (menu TV Eminem)
│       │   │   │   └── ExitScreen.kt
│       │   │   ├── components/
│       │   │   │   ├── TvNavigationRail.kt # Menu lateral (8 itens, sem YouTube)
│       │   │   │   ├── SmartEDFocusable.kt
│       │   │   │   ├── GlassPanel.kt
│       │   │   │   └── ScreenHeader.kt
│       │   │   ├── player/                 # PlayerActivity (Media3 ExoPlayer)
│       │   │   └── theme/                  # Theme.kt, Color.kt
│       │   ├── viewmodel/
│       │   │   └── MainTvViewModel.kt
│       │   └── data/
│       │       └── model/Models.kt
│       └── res/
│           ├── values/ (strings, colors, themes)
│           ├── drawable/ (icones vetoriais)
│           ├── mipmap-anydpi-v26/ (icone adaptativo)
│           └── xml/network_security_config.xml
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── gradle/wrapper/
├── gradlew
├── tools/
│   ├── scripts/
│   │   ├── install-deps.sh    # Instala Java 17, apktool, apksigner, aapt
│   │   └── build-release.sh   # Gera APK assinado para release
│   └── apktool-src/           # Fonte do apktool (clonado)
└── reference/
    └── iptv-native/           # Projeto de referência IPTV-Native (clonado)
```

## Tecnologias
- Kotlin + Jetpack Compose
- Android Gradle Plugin 8.7.3, Kotlin 2.1.0
- Media3 ExoPlayer (vídeo)
- Coil (imagens), OkHttp (rede)

## Como Gerar o APK Release

```bash
# 1. Instale dependências (ambiente com internet completa)
chmod +x tools/scripts/install-deps.sh
sudo ./tools/scripts/install-deps.sh

# 2. Verifique as ferramentas
java -version
apktool --version
apksigner --version

# 3. Gere o APK release
chmod +x gradlew tools/scripts/build-release.sh
./tools/scripts/build-release.sh

# 4. APK assinado em:
app/build/outputs/apk/release/app-release.apk

# 5. Instale no dispositivo
adb install -r app/build/outputs/apk/release/app-release.apk
```

## ⚠️ Limitação deste sandbox

Este ambiente tem rede restrita (apenas github.com, api.github.com, codeload.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org). Não foi possível baixar:
- OpenJDK 17 (repos Debian bloqueados)
- apktool / apksigner / aapt (assets do GitHub bloqueados)
- O APK MakroTV.XtreamYT (release assets bloqueados)

Execute os scripts de build em um ambiente com internet completa para gerar o APK release.

## Referências
- Layout base: MakroTV.XtreamYT (https://github.com/smartmacro77-gif/apps/releases/tag/v1.0)
- Configurações: TV Eminem (menu completo de configurações)
- Arquitetura: IPTV-Native (https://github.com/msmacrosmart-cpu/IPTV-Native)