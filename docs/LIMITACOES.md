# Limitações declaradas — SmartED-TV 1.0.7

O compromisso do projeto é **não simular**. Tudo abaixo é um limite real e aparece na interface
com a explicação correspondente, em vez de um conteúdo de exemplo.

## 1. Add-ons Python do Kodi (`xbmc.python.*`)

O Kodi executa add-ons Python dentro de um runtime próprio e injeta a API `xbmc`, `xbmcgui`,
`xbmcplugin`, `xbmcaddon`. Este app **não** embarca interpretador Python nem essa ponte.

- `plugin.video.*` / `plugin.audio.*` / `script.*` → **requer adaptação** (`COMPATIBLE_WITH_ADAPTATION`).
- `xbmc.python.module`, `xbmc.service`, `resource.*` → **não compatível** (`NOT_COMPATIBLE`);
  ainda podem ser instalados como arquivo, sem execução.
- `xbmc.addon.repository` → **compatível** (é só XML + download de pacotes).
- `xbmc.gui.skin`, scrapers, legendas → **parcial** (a estrutura é declarativa, o motor não existe).

Consequência prática: abrir `plugin://<addon-python>/...` mostra o motivo, nunca uma lista inventada.
O único adaptador funcional hoje é o de **pasta local** (`LocalFolderPluginAdapter`).

## 2. Formatos de arquivo

- **RAR** e **7z** não são lidos (RAR é patenteado; 7z exigiria Commons Compress + XZ).
- **ISO/Blu-ray**, DVD e pastas `VIDEO_TS` não são montados.
- Playlists `.strm` são lidas, mas não resolvem caminhos internos da biblioteca do Kodi.
- `.nfo` e `.db` do Kodi são lidos como textos/arquivos; o esquema da biblioteca do Kodi não é importado.

## 3. Reprodução

- **Codecs** dependem do aparelho: AVI/DivX/Xvid, HEVC em TV Box antiga, VC-1 e AC-3/E-AC3 podem
  não tocar. O player mostra "o aparelho não suporta o codec deste arquivo".
- **DRM** (Widevine/PlayReady com licença externa) não é reproduzido nem contornado. A tela diz isso.
- **Smooth Streaming** (`.ism/Manifest`) é reconhecido e classificado, mas o Media3 não traz `SmoothStreamingMediaSource`;
  o arquivo é tratado como manifesto progressivo e pode falhar — mensagem clara ao usuário.
- **RTMP/RTSP** são aceitos como protocolo, mas sem módulo de extensão do Media3 a reprodução
  depende do aparelho; quando falha, o erro é exibido.
- Sem suporte a legendas embutidas (apenas faixas externas informadas pela fonte).

## 4. Rede e credenciais

- Cabeçalhos HTTP (`Referer`, `User-Agent`, `Authorization`) e cookies são repassados ao player, e
  **nunca** gravados em log. O app não armazena login de fontes externas.
- Redirecionamentos entre protocolos são permitidos (`http` ↔ `https`), sem reescrever a URL
  (a query string original é sempre preservada).

## 5. Armazenamento

- Listagem limitada a 5.000 itens por pasta (proteção de memória).
- Só pastas **autorizadas pelo usuário** (SAF) são visíveis: o Android 11+ não permite listar
  armazenamento arbitrário sem `MANAGE_EXTERNAL_STORAGE` (que este app não pede).
- Instalação em `files/addons/<id>/` do armazenamento privado do app; nada é instalado em `/system`
  nem executado.

## 6. O que permanece funcionando como antes

- Canais, Filmes, Séries, Música, Rádio, Jogos, Imagens, Clima, Favoritos, Configurações, Sair
  (12 opções do menu Kodi), layout matte-glass, orientação horizontal travada, assinatura v1+v2+v3
  e releases com APK universal + por ABI.
