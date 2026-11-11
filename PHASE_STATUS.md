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

### Elementos adicionados em todas as 4 telas

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

### Backup
- `xml/Home.xml.bak` preservado para reversão

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
