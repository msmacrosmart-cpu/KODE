# PHASE_STATUS.md — Status do Projeto Brazuka Play Skin

> Referências: `INTERACTION_MAP.md`, `XML_MAP.md`, `PREVIEW_KODI.html`, `backup_files/`
> Branch: `arena/1a97faf9-kode`

---

## Phase 1: Auditoria (COMPLETADA)

### Documentos criados
- `INTERACTION_MAP.md` (704 linhas) — Mapeamento completo de interação HTML → Kodi
- `XML_MAP.md` (218 linhas) — Mapeamento das 44 telas do HTML para os XMLs da skin

### Descobertas
- O HTML é um protótipo interativo completo: 44 telas, 245 botões, 128 cartões, 11 modais
- Todos os componentes CSS mapeados para elementos Kodi
- Estados visuais (:focus, .on, .sw.on) identificados
- Navegação D-pad completa (←→↑↓, Enter, Esc)
- **Todas as 44 telas do HTML têm XML correspondente na skin** — trabalho de adaptação, não criação

---

## Phase 2: Visual/Estrutura (EM PROGRESSO)

### Telas do Home adaptadas

| Tela | Commit | Status | Alterações |
|---|---|---|---|
| **Aurora** | `f51e944` | ✅ Adaptada | Hero com botão "Detalhes" + atalhos principais (Categorias/TV ao vivo/Filmes/Séries/Ajustes) |
| **Blade** | `8937eea` | ✅ Adaptada | Hero com botões "Detalhes"/"+ Minha lista" + atalhos principais |
| **Top10** | `4f52102` | ✅ Adaptada | Hero com botões "Detalhes"/"+ Minha lista" + atalhos principais |
| **Sports** | `62ad9f2` | ✅ Adaptada | Hero com botões "Detalhes"/"+ Minha lista" + atalhos principais |

### Phase 5: YouTube/Programas/Música (CONCLUÍDA)

| XML | Commit | Status | Alterações |
|---|---|---|---|
| **MyMusicNav.xml** | `64c623c` | ✅ Adaptada | Menu lateral vertical pb_dark/pb_white, Busca/Ajustes/Sair |
| **MusicOSD.xml** | `64c623c` | ✅ Adaptada | Fundo pb_dark, cores pb_white |
| **MyPics.xml** | `18bf825` | ✅ Adaptada | Fundo pb_dark, header NOVA TV |
| **MyGames.xml** | `18bf825` | ✅ Adaptada | Fundo pb_dark, header NOVA TV |
| **MyPrograms.xml** | `18bf825` | ✅ Adaptada | Fundo pb_dark, header NOVA TV |
| **MyWeather.xml** | `18bf825` | ✅ Adaptada | Fundo pb_dark, header NOVA TV |

### Phase 3: Brazuka Play Integration (EM PROGRESSO)

**Ordem fixa do Home (Aurora) implementada** — commit `999ff98`:

| # | Seção | List ID | Conteúdo | Tipo Cartão |
|---|---|---|---|---|
| 1 | Continuar assistindo | 9200 | `special://skin/playlists/inprogress_movies.xsp` | Landscape 16:9 |
| 2 | Filmes — 10 mais recentes | 9201 | `videodb://recentlyaddedmovies/` (sortby=dateadded desc, limit=10) | Portrait 2:3 |
| 3 | Séries — 10 mais recentes | 9202 | `videodb://recentlyaddedepisodes/` (sortby=dateadded desc, limit=10) | Landscape 16:9 |
| 4 | Canais favoritos | 9203 | `favourites://` | Landscape 16:9 |
| 5 | Filmes — 10 mais votados | 9204 | `videodb://movies/titles/` (sortby=rating desc, limit=10) | Portrait 2:3 |
| 6 | Séries — 10 mais vistas | 9205 | `videodb://tvshows/titles/` (sortby=rating desc, limit=10) | Landscape 16:9 |

**Foco:** `onup=9200→9201→9202→9203→9204→9205`, `ondown=9400→9200` (atalhos → continue watching), `ondown=9205→9400` (última seção → atalhos)

### Phase 2: Visual/Estrutura (CONCLUÍDA)

| Tela | Commit | Status |
|---|---|---|
| **Aurora** | `f51e944` + `999ff98` + `e611b52` | ✅ Adaptada + Ordem fixa + Hero Brazuka Play |
| **Blade** | `8937eea` | ✅ Adaptada |
| **Top10** | `4f52102` | ✅ Adaptada |
| **Sports** | `62ad9f2` | ✅ Adaptada |
| **MyVideoNav** | `bd3f374` | ✅ Adaptada |
| **VideoOSD** | `90271a0` | ✅ Adaptada |
| **MyFavourites** | `dee5403` | ✅ Adaptada |
| **Settings.xml** | `174b5f7` | ✅ Adaptada | Tema pb_dark/pb_white, botão Busca, 9 categorias |
| **SettingsCategory.xml** | `174b5f7` | ✅ Adaptada | Tema pb_dark/pb_white, descrições pb_white |

**MyFavourites.xml — Menu lateral (grouplist 9000, vertical):**
1. **TV ao vivo** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais")`
2. **Filmes** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu")`
3. **Séries** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23series_menu")`
4. **Novelas** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=25&url=%23novelas_menu")`
5. **Animes** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=22&url=%23animes_menu")`
6. **Doramas** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=31&url=%23doramas_menu")`
7. **Desenhos** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=28&url=%23desenhos_menu")`
8. **Favoritos Kodi** → `ActivateWindow(Favourites)`

**MyFavourites.xml — Painel de conteúdo (à direita):**
- List 50 (lista vertical com thumbnail 180x90 + título + sinopse)
- Foco: `onright=50` no menu, `onup/ondown/onleft=9000` na lista
- Busca/Ajustes/Sair na barra inferior

**MyVideoNav.xml — Menu lateral (grouplist 9000, vertical):**
1. **TV ao vivo** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais")`
2. **Filmes** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu")`
3. **Séries** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23series_menu")`
4. **Novelas** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=25&url=%23novelas_menu")`
5. **Animes** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=22&url=%23animes_menu")`
6. **Doramas** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=31&url=%23doramas_menu")`
7. **Desenhos** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=28&url=%23desenhos_menu")`

**MyVideoNav.xml — Painel de conteúdo (à direita):**
- List 50 (lista vertical com thumbnail 180x90 + título + sinopse)
- List 51 (lista vertical com poster 1000x350 + sinopse lateral)
- Foco: `onright=50` no menu, `onup/ondown/onleft=9000` na lista
- Busca/Ajustes/Sair na barra inferior

**VideoOSD.xml — Opções do app durante a reprodução:**
- Controles de reprodução (grupo 201): Previous, Rewind, Play/Pause, Stop, Forward, Next, Record
- Opções do app (grupo 202): Home, Channels, Guide, Playlist, Info, **Áudio (NEW)**, Bookmarks, Teletext, Subtitles, Stereoscopic, Settings
- Barra de progresso (grupo 6000): seek + timeshift
- Foco: `defaultcontrol=602` (Play/Pause), navegação ←→ entre grupos, ↑↓ entre botões

**VIDEOOSD_MAP.md** documenta o mapeamento completo de todas as opções do VideoOSD.

### Elementos adicionados em todas as 4 telas do Home

**Hero:**
- Botão "Detalhes" (`Action(Info)`) — substitui "Trailer" ou "Informações"
- Botão "+ Minha lista" (`Action(AddToPlaylist)`) — substitui "Informações" ou "Gravações"

**Atalhos principais (grouplist horizontal):**
1. **Categorias** → `ActivateWindow(Videos,root,return)`
2. **TV ao vivo** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais")`
3. **Filmes** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu")`
4. **Séries** → `ActivateWindow(10025, "plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23series_menu")`
5. **Ajustes** → `ActivateWindow(Settings)`

### Foco
- Aurora: `ondown=9300` (hero) → `ondown=9400` (atalhos) → `ondown=9200` (lançamentos)
- Blade: `onup=9320` (hero) → `onup=9410` (atalhos) → `onup=9210` (continue watching)
- Top10: `onup=9340` (hero) → `onup=9420` (atalhos) → `onup=9230` (top 10)
- Sports: `onup=9350` (hero) → `onup=9430` (atalhos) → `onup=9240` (canais)
- MyVideoNav: `onright=50` (menu → conteúdo), `onup/ondown/onleft=9000` (conteúdo → menu)

### Backup
- `xml/Home.xml.bak` preservado para reversão
- `xml/MyVideoNav.xml.bak` preservado para reversão

---

## Próximos Passos

### Phase 2 (continuação)
1. **MyVideoNav.xml** — Adaptar para Brazuka Play:
   - Menu lateral com categorias (TV ao vivo, Filmes, Séries, Novalas, Animes, Doramas, Desenhos)
   - Grade/lista de conteúdo
   - Foco no menu ao abrir
   - Rotas Brazuka Play mapeadas

2. **VideoOSD.xml** — Adicionar menus:
   - Áudio (DialogAudio)
   - Legendas (DialogSubtitles)
   - Marcadores (VideoOSDBookmarks)
   - Informações (DialogVideoInfo)

3. **MyFavourites.xml** — Integrar favoritos do Brazuka Play

### Phase 3: Brazuka Play Integration
4. **Home order fixo** — Implementar a ordem especificada:
   1. Continue assistindo
   2. Filmes — 10 mais recentes
   3. Séries — 10 mais recentes
   4. Canais favoritos
   5. Filmes — 10 mais vistos/votados
   6. Séries — 10 mais vistas/votadas

5. **Hero fed by real content** — Conectar hero ao conteúdo real do Brazuka Play

---

## Regras Preservadas

- ✅ Nunca remover addons funcionais
- ✅ Nunca substituir Brazuka Play
- ✅ Nunca duplicar integrações
- ✅ Nunca inventar conteúdo/stats
- ✅ Nunca mostrar opções não configuradas
- ✅ Nunca mostrar TV PVR se não habilitado
- ✅ Nunca alterar origem de conteúdo sem necessidade
- ✅ Nunca quebrar compatibilidade Kodi
- ✅ Foco sempre definido ao abrir tela
- ✅ Estados visuais obrigatórios (foco muda cor/borda)
- ✅ Navegação D-pad completa
- ✅ Mudanças incrementais e reversíveis
- ✅ Backup de arquivos antes de modificar

---

## Commits

| Commit | Descrição |
|---|---|
| `d1672aa` | Add INTERACTION_MAP.md |
| `753b8b7` | Add XML_MAP.md |
| `f51e944` | Adaptar tela Aurora |
| `8937eea` | Adaptar tela Blade |
| `4f52102` | Adaptar tela Top10 |
| `62ad9f2` | Adaptar tela Sports |

---

## v1.0.27 — Brazuca Play no primeiro boot + Ajustes/Energia (2026-11-11)

### Diagnóstico
- O perfil semeado (`assets/smarted/profile/`) já contém o plugin e as dependências,
  mas o Kodi só monta o banco de addons depois do primeiro boot. Sem o addon
  registrado/habilitado e sem os dados de addon, a janela do Brazuca Play abria
  vazia e o Kodi avisava que o addon não pôde ser carregado.
- O próprio plugin baixa `cloudrequest` da internet na primeira execução; se esse
  download falha, o menu não monta (o código do plugin mostra "Erro ao importar plugin!").

### Correções
| Item | Onde | O que faz |
|---|---|---|
| `service.smarted.bootstrap` | `kodi/addons/service.smarted.bootstrap/` | Serviço de startup que verifica o `plugin.video.BrazucaPlay.Matrix` e a cadeia de dependências obrigatórias, reinstala a partir de `addons/packages/*.zip` quando falta/está corrompido, cria `userdata/addon_data/...`, habilita os addons via JSON-RPC e descompacta o `cloudrequest` embutido |
| Payload `cloudrequest-py3.zip` | `.../payload/` | Pacote oficial do repositório do Brazuca (v1.0.0 de requests_toolbelt), agora entregue pronto — o plugin não depende de rede no primeiro boot |
| Relatório | `userdata/smarted-bootstrap.log` | Registro do que foi verificado/restaurado, para diagnóstico |
| Ajustes/Energia na Home | `xml/Home.xml` | Barra fixa (Busca, Ajustes, Energia) em todos os layouts; "Energia" abre o menu de energia do Kodi |
| Ciclo de Ajustes | `xml/Settings.xml` | `<onload>` incrementa `secret_settings_cycle` (o controle anterior era invisível e nunca disparava o unlock) |
| Ícones de Ajustes | `media/icons/settings/` | Novos ícones (Aparência, Energia, Diagnóstico) + itens "Diagnóstico Brazuca Play" e "Energia" na tela de Ajustes |

### Testes
- `tests/test_smarted_bootstrap.py` — reparo, dependências, path traversal, payload, build.
- `tests/test_brazucaplay_runtime.py` — roda o `default.py` real do plugin fora do Kodi
  (`SMARTED_PROFILE=<perfil>`) e exige o menu principal completo sem exceção.
- `tools/kodi/verify-boot-integrity.py` — perfil byte-idêntico ao manifesto do dex.
