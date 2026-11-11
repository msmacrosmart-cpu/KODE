# Comparativo — 44 referências × skin atual

Critério: **IDÊNTICA** (fiel), **COMPATÍVEL** (estrutura correta, pequenas diferenças), **PARCIAL** (alguns elementos corretos, diferenças relevantes), **DIFERENTE** (layout incompatível), **AUSENTE** (não implementada), **NÃO APLICÁVEL** (sem correspondência técnica). Como não houve captura das referências (ver `MAPA_REFERENCIAS_VISUAIS.md`), a classificação é por **presença funcional + estrutura XML**, não por pixel. Nenhuma tela é classificada como IDÊNTICA sem comparação visual efetiva.

| # | Tela | Situação | Diferenças | Ação | Prioridade |
|---|---|---|---|---|---|
| 01 | Aurora | PARCIAL | Hero/menu/fileiras existem (9100/9000/9200), mas dados vêm do Brazuca (não dos títulos da referência) e Top 10/Esportes não são widgets reais | Preservar; preview reproduz composição | Alta |
| 02 | Blade | PARCIAL | Variação da Home; skin tem um único Home (hero + widgets) | Preservar; preview mostra variação de foco/dados | Média |
| 03 | Top 10 | AUSENTE | Sem ranking real (sem métrica confiável); não fabricado | Documentar; preview esquemático | Média |
| 04 | Esportes | PARCIAL | Sem tela própria; acesso via TV Brazuca (opções da fonte) | Preservar rota; preview mostra opções reais | Média |
| 05 | Guia | PARCIAL | `MyPVRGuide.xml` existe, mas exige PVR; sem PVR fica vazio | Preservar; não simular | Média |
| 06 | Canais | COMPATÍVEL | TV ao vivo via ponte (`route=tv` → `#menu_canais` + busca Brazuca/Pluto) | Preservar; preview = TV ao vivo | Alta |
| 07 | Serie | COMPATÍVEL | Hub `route=series` (Buscar + 5 categorias) existe; episódios via Brazuca | Preservar; preview = Séries + 5 subcategorias | Alta |
| 08 | Player | COMPATÍVEL | `VideoOSD.xml` completo (seek, controles, áudio/legendas/marcadores) | Preservar; validar em Kodi real | Alta |
| 09–16 | Variações (Aurora→Player) | PARCIAL | Mesmas janelas das telas 01–08 com estados diferentes; skin não tem “variação” separada | Preview mostra variações; skin preservada | Baixa |
| 17 | Config | COMPATÍVEL | `Settings.xml` + `SettingsCategory.xml` (Player/Mídia/TV/Serviços/Interface/Sistema/Skin) | Preservar | Média |
| 18 | Musica | PARCIAL | `MyMusicNav.xml` genérica (Views); sem layout de artista/álbum | Documentar pendência; não inventar layout | Média |
| 19 | Tocando | COMPATÍVEL | `MusicVisualisation.xml` + `MusicOSD.xml` | Preservar | Baixa |
| 20 | VideoMus | PARCIAL | Widget 9270 + `MyVideoNav` (videodb musicvideos); sem tela própria | Preservar | Baixa |
| 21 | Radio | NÃO APLICÁVEL* | `MyPVRChannels.xml` (rádio) exige PVR; sem PVR não há conteúdo | Documentar; não simular | Baixa |
| 22 | Jogos | NÃO APLICÁVEL* | `MyGames.xml` + 7 `Game*.xml` exigem suporte a jogos | Documentar; não simular | Baixa |
| 23 | Complementos | PARCIAL | `AddonBrowser.xml` genérica (Views) | Preservar | Baixa |
| 24 | Imagens | PARCIAL | `MyPics.xml` genérica | Preservar | Baixa |
| 25 | Videos → Filmes | COMPATÍVEL | `route=movies` (Buscar/Lançamentos/Gêneros/A–Z + menu original) via `MyVideoNav` | Preservar; preview nomeia “Filmes” | Alta |
| 26 | Favoritos | PARCIAL | `DialogFavourites.xml` + widget 9230 (canais favoritos via Brazuca) | Preservar | Baixa |
| 27 | Clima | PARCIAL | `MyWeather.xml` existe; exige serviço de clima | Preservar | Baixa |
| 28 | Arquivos | COMPATÍVEL | `FileManager.xml` + `FileBrowser.xml` (botões por ID nativo) | Preservar | Baixa |
| 29 | Energia | COMPATÍVEL | `ShutdownMenu.xml` | Preservar | Baixa |
| 30 | Busca | PARCIAL | Busca de canais/séries na ponte + `script.globalsearch` (condicional); sem busca global própria | Preservar | Média |
| 31 | Gravacoes | NÃO APLICÁVEL* | `MyPVRRecordings.xml` exige PVR | Documentar | Baixa |
| 32 | Timers | NÃO APLICÁVEL* | `MyPVRTimers.xml` exige PVR | Documentar | Baixa |
| 33 | Perfis | COMPATÍVEL | `Profiles.xml` | Preservar | Baixa |
| 34 | Contexto | COMPATÍVEL | `DialogContextMenu.xml` (ID nativo) | Preservar | Baixa |
| 35 | AudioLeg | COMPATÍVEL | `DialogSettings.xml` (modelo Kodi 21) | Preservar; conferir IDs no Estuary | Média |
| 36 | Sobre | COMPATÍVEL | `SettingsSystemInfo.xml` (abas 94–100) | Preservar | Baixa |
| 37 | Ajustes | COMPATÍVEL | `Settings.xml` (12 rotas) | Preservar | Média |
| 38 | CPlayer | COMPATÍVEL | `SettingsCategory.xml` (Player) | Preservar | Baixa |
| 39 | CMidia | COMPATÍVEL | `SettingsCategory.xml` (Mídia) | Preservar | Baixa |
| 40 | CTV | NÃO APLICÁVEL* | `SettingsCategory.xml` (TV/PVR) exige PVR; oculto no modo básico | Documentar | Baixa |
| 41 | CServ | COMPATÍVEL | `SettingsCategory.xml` (Serviços) | Preservar | Baixa |
| 42 | CInt | COMPATÍVEL | `SettingsCategory.xml` (Interface) + `SkinSettings.xml` | Preservar | Baixa |
| 43 | CSis | COMPATÍVEL | `SettingsCategory.xml` (Sistema) | Preservar | Baixa |
| 44 | CPerf | COMPATÍVEL | `Profiles.xml` / `SettingsProfile.xml` | Preservar | Baixa |

\* NÃO APLICÁVEL aqui significa “sem recurso no ambiente” (PVR/jogos), não “tela inexistente no Kodi”. A janela existe na skin; o conteúdo depende do recurso.

Adaptação TV/Filmes/Séries (solicitada): **TV ao vivo → 06 Canais** (`route=tv`), **Filmes → 25 Filmes** (`route=movies`), **Séries/Doramas/Animes/Desenhos/Novelas → 07 Serie** (`route=series`). Todas COMPATÍVEIS e preservadas; o preview as mostra como telas principais.
