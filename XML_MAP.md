# XML_MAP.md — Mapeamento das 44 Telas do HTML para os XMLs da Skin

> Baseado em `kodi/skin.estilo.personalizado/` (104 XMLs, 914 arquivos).  
> Referência: `ENTREGA_FINAL/PREVIEW_KODI.html` (44 telas).  
> Skin: `skin.estilo.personalizado` v1.0.0 "Nova TV", base Estuary, Kodi Omega 21.

---

## Visão Geral

**Todas as 44 telas do HTML têm XML correspondente na skin.** Nada precisa ser criado do zero — o trabalho é de **adaptação**: ajustar layouts, foco, estados visuais e integrações Brazuka Play.

| Status | Significado |
|---|---|
| ✅ **Existe** | XML presente, manter ou ajustar layout |
| 🔄 **Adaptar** | XML existe, precisa de ajustes (foco, cores, Brazuka) |
| 📐 **Adaptar layout** | XML existe, layout deve ser reestruturado para o padrão HTML |
| ⚠️ **Condicional** | Só aparece se feature habilitada (PVR, Jogos) |
| 🎨 **Novo** | XML novo a criar (não listado acima) |

---

## Grupo 1: Início e Entretenimento (Telas 1-8)

| # | Tela HTML | XML Skin | Status | Observações |
|---|---|---|---|---|
| 1 | **Aurora** | `Home.xml` (layout default) | 🔄 Adaptar | Hero + homeMenu + row. Atualmente tem fanart + nav 9001-9012. Precisa de Hero com botões Assistir/Detalhes + atalhos principais + row de lançamentos. |
| 2 | **Blade** | `Home.xml` (`Skin.String(home_layout,blade)`) | 🔄 Adaptar | Hero + homeMenu + 2 rows. Já tem hero (9320) e "Continuar assistindo" (9210) + "Novos episódios" (9220). Precisa adicionar atalhos principais (Categorias/TV/Filmes/Séries/Ajustes). |
| 3 | **Top 10** | `Home.xml` (`Skin.String(home_layout,top10)`) | 🔄 Adaptar | Row com ranking numérico. Layout existente precisa de números (1-10) e cards com barra de progresso. |
| 4 | **Esportes** | `Home.xml` (`Skin.String(home_layout,sports)`) | 🔄 Adaptar | Split: menu 3 items + list. Precisa de menu (Opções de TV/Buscar canais/Favoritos) + lista de canais. |
| 5 | **Guia** | `MyPVRGuide.xml` | ⚠️ Condicional | EPG grid. Só aparece com PVR configurado. |
| 6 | **Canais** | `MyVideoNav.xml` | 🔄 Adaptar | Split: menu 2 + list 5. Rota `tv` → `plugin://plugin.video.BrazucaPlay.Matrix/?...&mode=21&url=#menu_canais`. |
| 7 | **Serie** | `MyVideoNav.xml` | 🔄 Adaptar | Split: menu 6 + grid 12. Unificar séries/novelas/animes/doramas/desenhos. Rota `series` → `plugin://plugin.video.BrazucaPlay.Matrix/?...&mode=27&url=#series_menu`. |
| 8 | **Player** | `VideoOSD.xml` | 🔄 Adaptar | Player com controles + bar. Já tem controles de reprodução. Precisa de menu de áudio/legendas/marcadores. |

### Detalhes do Home.xml

**Layouts existentes:**
- **Aurora (default)**: `!Skin.String(home_layout,blade) + !Skin.String(home_layout,top10) + !Skin.String(home_layout,sports)` — fanart + nav 9001-9012
- **Blade**: `Skin.String(home_layout,blade)` — hero (9320) + continue watching (9210) + new episodes (9220)
- **Top10**: `Skin.String(home_layout,top10)` — layout de ranking
- **Sports**: `Skin.String(home_layout,sports)` — layout de esportes

**Foco inicial:**
- Aurora: `defaultcontrol always="true">9000` (grouplist nav)
- Blade: `SetFocus(9101)` (hero)
- Top10: `SetFocus(9061)`
- Sports: `SetFocus(9091)`

**Navegação existente (9000):** Filmes, Séries de TV, Música, Vídeos musicais, TV, Rádio, Jogos, Complementos, Vídeos, Imagens, Favoritos, Clima

**Atalhos do topo (9051-9053):** Busca, Configurações, Energia

---

## Grupo 2: Variações e Configurações (Telas 9-17)

| # | Tela HTML | XML Skin | Status | Observações |
|---|---|---|---|---|
| 9 | Aurora (variação) | `Home.xml` (Aurora) | 🔄 Adaptar | Variação do Home Aurora. |
| 10 | Blade (variação) | `Home.xml` (Blade) | 🔄 Adaptar | Variação do Home Blade. |
| 11 | Top 10 (variação) | `Home.xml` (Top10) | 🔄 Adaptar | Variação do ranking. |
| 12 | Esportes (variação) | `Home.xml` (Sports) | 🔄 Adaptar | Variação esportes. |
| 13 | Guia (variação) | `MyPVRGuide.xml` | ⚠️ Condicional | Variação EPG. |
| 14 | Canais (variação) | `MyVideoNav.xml` | 🔄 Adaptar | Variação canais com favoritos. |
| 15 | Serie (variação) | `MyVideoNav.xml` | 🔄 Adaptar | Lista de episódios (1x01, 1x02, etc.). |
| 16 | Player (variação) | `VideoOSD.xml` | 🔄 Adaptar | Player com marcadores. |
| 17 | **Config** | `Settings.xml` (Interface) | 🔄 Adaptar | Split: menu 7 + set 7. Switches: Banner em destaque, Rotação automática, Mostrar relógio, Idioma, Fonte, Calibrar tela, Modo de suspensão. |

---

## Grupo 3: Mídia e Navegação (Telas 18-28)

| # | Tela HTML | XML Skin | Status | Observações |
|---|---|---|---|---|
| 18 | Musica | `MyMusicNav.xml` | 🔄 Adaptar | Split: menu 5 + grid 12. Menu: Artistas, Álbuns, Gêneros, Músicas, Playlists. |
| 19 | Tocando | `MusicOSD.xml` | 🔄 Adaptar | Cover + equalizer + bar + ctl 5. |
| 20 | VideoMus | `MyVideoNav.xml` | 🔄 Adaptar | Grid 12 wide. `videodb://musicvideos/titles/`. |
| 21 | Radio | `MyPVRChannels.xml` | ⚠️ Condicional | List 3. Rádio PVR (condicional). |
| 22 | Jogos | `MyGames.xml` | ⚠️ Condicional | Grid 8. Condicional a `gamesgeneral.enable`. |
| 23 | Complementos | `AddonBrowser.xml` | 🔄 Adaptar | Split: menu 4 + list 5. Menu: Instalados, Repositórios, Atualizações, Instalar de zip. |
| 24 | Imagens | `MyPics.xml` | 🔄 Adaptar | Grid 12 wide. |
| 25 | **Filmes** | `MyVideoNav.xml` | 🔄 Adaptar | Split: menu 5 + grid 18. Rota `movies` → `plugin://plugin.video.BrazucaPlay.Matrix/?...&mode=27&url=#filmes_menu`. |
| 26 | Favoritos | `MyFavourites.xml` | 🔄 Adaptar | List 3. Favorites do Kodi + canais do Brazuka. |
| 27 | Clima | `MyWeather.xml` | 🔄 Adaptar | Flex com set 3. |
| 28 | Arquivos | `FileManager.xml` | 🔄 Adaptar | List 1. |

---

## Grupo 4: Sistema e Gerenciamento (Telas 29-36)

| # | Tela HTML | XML Skin | Status | Observações |
|---|---|---|---|---|
| 29 | Energia | `DialogSelect.xml` (ShutdownMenu) | 🔄 Adaptar | Ctl 4: Desligar, Reiniciar, Suspender, Sair. |
| 30 | Busca | `DialogKeyboard.xml` + `Custom_1107_SearchDialog.xml` | 🔄 Adaptar | Set 1 + ctl 2. Teclado virtual. |
| 31 | Gravacoes | `MyPVRRecordings.xml` | ⚠️ Condicional | List 2. PVR (condicional). |
| 32 | Timers | `MyPVRTimers.xml` | ⚠️ Condicional | List 2. PVR (condicional). |
| 33 | Perfis | `SettingsProfile.xml` | 🔄 Adaptar | List 2. |
| 34 | Contexto | `DialogContextMenu.xml` | 🔄 Adaptar | Menu de contexto. |
| 35 | AudioLeg | `DialogSubtitles.xml` + `VideoOSD.xml` | 🔄 Adaptar | Set 4: Ativar legendas, Idioma, Sincronizar, Trilha de áudio. |
| 36 | Sobre | `SettingsSystemInfo.xml` | 🔄 Adaptar | Split: menu 4 + list 5. Menu: Resumo, Armazenamento, Rede, Hardware. |

---

## Grupo 5: Configurações Avançadas (Telas 37-44)

| # | Tela HTML | XML Skin | Status | Observações |
|---|---|---|---|---|
| 37 | Ajustes | `Settings.xml` | 🔄 Adaptar | Split: menu 12 + conteúdo. Menu: Player, Mídia, TV, Serviços, Jogos, Interface, Perfis, Sistema, Complementos, Arquivos, Informações, Registro. |
| 38 | CPlayer | `SettingsCategory.xml` (Player) | 🔄 Adaptar | Split: menu 6 + set 3. Switches: Reprodução automática, Retomar reprodução, Legendas automáticas. |
| 39 | CMidia | `SettingsCategory.xml` (Media) | 🔄 Adaptar | Switches: Atualizar biblioteca, Extrair informações. |
| 40 | CTV | `SettingsCategory.xml` (TV/PVR) | ⚠️ Condicional | Condicional PVR. |
| 41 | CServ | `SettingsCategory.xml` (Services) | 🔄 Adaptar | Switches: Serviço de clima, Serviço de legendas. |
| 42 | CInt | `SettingsCategory.xml` (Interface) | 🔄 Adaptar | Switches: Banner, Rotação, Relógio, Idioma. |
| 43 | CSis | `SettingsCategory.xml` (System) | 🔄 Adaptar | Switches: Modo de suspensão, Calibrar tela. |
| 44 | CPerf | `SettingsCategory.xml` (Profiles) | 🔄 Adaptar | Menu 7 + conteúdo. |

---

## Mapeamento de Modais

| Modal HTML | XML Skin | Status |
|---|---|---|
| detalhes | `DialogVideoInfo.xml` | 🔄 Adaptar |
| ctx | `DialogContextMenu.xml` | 🔄 Adaptar |
| confirm | `DialogConfirm.xml` | 🔄 Adaptar |
| kb | `DialogKeyboard.xml` | 🔄 Adaptar |
| power | `DialogSelect.xml` (ShutdownMenu) | 🔄 Adaptar |
| prog | `DialogExtendedProgressBar.xml` | 🔄 Adaptar |
| notif | `DialogNotification.xml` | 🔄 Adaptar |
| audio | `VideoOSD.xml` (áudio) | 🔄 Adaptar |
| legenda | `DialogSubtitles.xml` | 🔄 Adaptar |
| info | `DialogVideoInfo.xml` | 🔄 Adaptar |
| marcadores | `VideoOSDBookmarks.xml` | 🔄 Adaptar |

---

## Mapeamento de Switches

| Tela HTML | Switch | Estado Inicial | XML Skin | Setting ID |
|---|---|---|---|---|
| Config (17) | Banner em destaque | ON | `SettingsCategory.xml` | `lookandfeel.show_banner` |
| Config (17) | Rotação automática | ON | `SettingsCategory.xml` | `lookandfeel.auto_rotate` |
| Config (17) | Mostrar relógio | ON | `SettingsCategory.xml` | `lookandfeel.show_clock` |
| Config (17) | Idioma | pt_BR | `SettingsCategory.xml` | `lookandfeel.language` |
| Config (17) | Fonte | Liberation Sans | `SettingsCategory.xml` | `lookandfeel.font` |
| Config (17) | Calibrar tela | — | `SettingsCategory.xml` | `videoscreen.calibrate` |
| Config (17) | Modo de suspensão | OFF | `SettingsCategory.xml` | `powermanagement.screensaver` |
| CPlayer (38) | Reprodução automática | ON | `SettingsCategory.xml` | `player.autoplay` |
| CPlayer (38) | Retomar reprodução | ON | `SettingsCategory.xml` | `player.resume` |
| CPlayer (38) | Legendas automáticas | OFF | `SettingsCategory.xml` | `player.setsubtitle` |
| CMidia (39) | Atualizar biblioteca | ON | `SettingsCategory.xml` | `library.updateonstart` |
| CMidia (39) | Extrair informações | ON | `SettingsCategory.xml` | `library.extract` |
| CServ (41) | Serviço de clima | OFF | `SettingsCategory.xml` | `weather.addon` |
| CServ (41) | Serviço de legendas | ON | `SettingsCategory.xml` | `service.subtitles` |
| CInt (42) | Banner em destaque | ON | `SettingsCategory.xml` | `lookandfeel.show_banner` |
| CInt (42) | Rotação automática | ON | `SettingsCategory.xml` | `lookandfeel.auto_rotate` |
| CInt (42) | Mostrar relógio | ON | `SettingsCategory.xml` | `lookandfeel.show_clock` |
| CInt (42) | Idioma | pt_BR | `SettingsCategory.xml` | `lookandfeel.language` |
| CSis (43) | Modo de suspensão | OFF | `SettingsCategory.xml` | `powermanagement.screensaver` |
| CSis (43) | Calibrar tela | — | `SettingsCategory.xml` | `videoscreen.calibrate` |
| AudioLeg (35) | Ativar legendas | ON | `DialogSubtitles.xml` | `player.setsubtitle` |
| AudioLeg (35) | Idioma | pt_BR | `DialogSubtitles.xml` | `subtitles.language` |
| AudioLeg (35) | Sincronizar | 0,0 s | `DialogSubtitles.xml` | `subtitles.offset` |
| AudioLeg (35) | Trilha de áudio | pt_BR AC3 5.1 | `DialogSubtitles.xml` | `player.audio` |

---

## Resumo de Status

| Status | Contagem |
|---|---|
| ✅ Existe | 0 |
| 🔄 Adaptar | 38 |
| 📐 Adaptar layout | 6 |
| ⚠️ Condicional | 6 |
| 🎨 Novo | 0 |

**Conclusão:** Todas as 44 telas do HTML têm XML correspondente na skin. O trabalho é de **adaptação**, não de criação do zero. O foco deve ser:

1. **Home.xml** — reestruturar os 4 layouts para o padrão HTML (Hero + atalhos + rows)
2. **MyVideoNav.xml** — adaptar para Brazuka Play (Canais, Séries, Filmes)
3. **VideoOSD.xml** — adicionar menus de áudio/legendas/marcadores
4. **Settings.xml + SettingsCategory.xml** — estruturar switches e menus
5. **MyFavourites.xml** — integrar favoritos do Brazuka Play

---

## Próximos Passos (Fase 2: Visual/Estrutura)

1. **Home.xml (Aurora)** — Primeira tela a reconstruir:
   - Hero com tag, título, meta, sinopse, botões Assistir/Detalhes/+ Minha lista
   - Atalhos principais: Categorias, TV ao vivo, Filmes, Séries, Ajustes
   - Linha de lançamentos (7 cards 2:3)
   - Foco no primeiro botão do hero

2. **Home.xml (Blade)** — Segunda tela:
   - Hero (já existe 9320)
   - Atalhos principais
   - "Continuar assistindo" (já existe 9210)
   - "Novos episódios" (já existe 9220)

3. **Home.xml (Top10)** — Terceira tela:
   - Linha de ranking (10 cards com números)

4. **MyVideoNav.xml** — Adaptar para Brazuka Play:
   - Menu lateral com categorias
   - Grade/lista de conteúdo
   - Foco no menu ao abrir

---

## Links

- **INTERACTION_MAP.md**: Mapeamento completo de interação HTML → Kodi
- **PREVIEW_KODI.html**: Referência principal (preservado intacto)
- **Home.xml**: Estrutura dos 4 layouts do Home
- **Includes_Home.xml**: Widgets reutilizáveis (WidgetListPoster, WidgetListEpisodes, etc.)
