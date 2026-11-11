# Inventário de telas — Kodi Omega 21 (skin.novatv)

Classificação: **Nativa** (sempre disponível), **Condicional** (depende de recurso/configuração), **Add-on** (depende de complemento), **Pendente** (existe no Kodi mas exige conferência de IDs no Estuary instalado). Window IDs abaixo são os documentados no Kodi 21 / presentes na skin; não foram inventados — conferir em https://kodi.wiki/view/Window_IDs antes de publicar.

| Tela | Window ID | XML na skin | Classe | Observação |
|---|---|---|---|---|
| Início | 10000 | `Home.xml` | Nativa | Hero + menu + widgets |
| Vídeos / Filmes / Séries (navegação) | 25 | `MyVideoNav.xml` | Nativa | Views 50/51/52; conteúdo via biblioteca ou ponte |
| Detalhes filme/série | 2003 | `DialogVideoInfo.xml` | Nativa | Botões por ID nativo |
| Música | 502 | `MyMusicNav.xml` | Nativa | Genérica; exige biblioteca |
| Músicas (arquivos) | 10502 | `MyMusicSongs.xml` | Nativa | Genérica |
| Tocando agora | 2006 | `MusicVisualisation.xml` | Nativa | — |
| Música OSD | 2007 | `MusicOSD.xml` | Nativa | — |
| Arquivos (gerenciador) | 3 | `FileManager.xml` | Nativa | Botões por ID nativo |
| Seletor de arquivos | 10003 | `FileBrowser.xml` | Nativa | — |
| Player OSD | 2901 | `VideoOSD.xml` | Nativa | Controles verificados por teste |
| Tela cheia | 2005 | `VideoFullScreen.xml` | Nativa | — |
| Marcadores OSD | 2901 | `VideoOSDBookmarks.xml` | Nativa | IDs 2/3/4/11 |
| Áudio/Legendas/Ajustes OSD | 2901 | `DialogSettings.xml`, `VideoOSDSettings.xml` | Nativa | Modelo Kodi 21 (IDs 2–15, 28–30) |
| Ajustes (menu) | 5 | `Settings.xml` | Nativa | Rotas `ActivateWindow(*Settings)` |
| Ajustes (categoria) | 10 | `SettingsCategory.xml` | Nativa | Grouplists 3/5 |
| Ajustes da skin | 10 | `SkinSettings.xml` | Nativa | Hero/widgets |
| Informações do sistema | 10 | `SettingsSystemInfo.xml` | Nativa | Abas 94–100 |
| Complementos | 10040 | `AddonBrowser.xml` | Nativa | Genérica |
| Programas | 10001 | `MyPrograms.xml` | Nativa | Genérica |
| Imagens | 2 | `MyPics.xml` | Nativa | Genérica |
| Apresentação | 2008 | `SlideShow.xml` | Nativa | — |
| Clima | 2600 | `MyWeather.xml` | Add-on | Requer serviço de clima |
| Favoritos | 11111 | `DialogFavourites.xml` | Nativa | + widget de canais via Brazuca |
| Energia | 10111 | `ShutdownMenu.xml` | Nativa | — |
| Busca global | — | via `script.globalsearch` (botão 9010) | Add-on | Condicional ao complemento |
| Perfis | 123 | `Profiles.xml` | Nativa | — |
| Login / bloqueio | 10000/— | `LoginScreen.xml`, `LockSettings.xml` | Nativa | — |
| Calibração | 11 | `SettingsScreenCalibration.xml`, `ScreenCalibration.xml` | Nativa | — |
| Registro de eventos | 10100 | `EventLog.xml` | Nativa | Genérica |
| TV ao vivo (canais) | 10700 | `MyPVRChannels.xml` | Condicional | Requer PVR; no modo básico, TV vem da ponte Brazuca |
| Guia TV | 10701 | `MyPVRGuide.xml` | Condicional | Requer PVR |
| Gravações | 10702 | `MyPVRRecordings.xml` | Condicional | Requer PVR |
| Timers | 10703 | `MyPVRTimers.xml` | Condicional | Requer PVR |
| Busca PVR | 10704 | `MyPVRSearch.xml` | Condicional | Requer PVR |
| Rádio PVR | 10700 | `MyPVRChannels.xml` (rádio) | Condicional | Requer PVR |
| Jogos | 10820+ | `MyGames.xml`, `Game*.xml` (7) | Condicional | Requer `gamesgeneral.enable` |
| Diálogos: confirmação/seleção/teclado/contexto/progresso/notificação/volume | vários (10100+) | `Dialog*.xml` (30+) | Nativa | Maioria por ID nativo; teclado e seleção com testes de contrato |
| Diálogos PVR (guia, canais, timers, RDS) | 10700+ | `DialogPVR*.xml` (9) | Condicional | Requer PVR |
| Diálogos de ajustes (conteúdo, perfil, legendas, playlist) | 10100+ | `DialogContentSettings.xml`, `DialogProfileSettings.xml`, `DialogSubtitles.xml`, `SmartPlaylist*.xml` | Nativa | Modelo Kodi 21 |
| Ponte SMARTED-TV (TV/Filmes/Séries) | 25 (via `ActivateWindow(Videos, plugin://…)`) | `Home.xml` 9000 + `plugin.video.smarted` | Add-on | Rotas `root/tv/movies/series` → Brazuca 2.1.4 |

Notas:
- A existência de uma janela na skin não significa fidelidade visual a uma referência — ver `COMPARATIVO_TELAS.md`.
- Janelas genéricas (297 B) abrem e navegam, mas não têm layout específico de temporada/episódio, álbum ou artista. Criar layouts específicos sem referência visual seria invenção; ficam como pendência documentada.
- PVR, clima, jogos e busca global não são simulados: sem o recurso, as telas ficam vazias ou ocultas por condição (`Pvr.Has*`, `Library.HasContent`, `System.HasAddon`).
