# INTERACTION_MAP.md — Mapeamento de Interação do PREVIEW_KODI.html

> **Referência principal de layout e interação.**  
> **Imagens de referência** = referência visual.  
> **ZIP `backup_files/`** = referência de funcionalidades reais do Kodi.  
> **HTML original preservado intacto** em `ENTREGA_FINAL/PREVIEW_KODI.html`.

---

## 1. Visão Geral

O `PREVIEW_KODI.html` (221 linhas, 28.900 B) é um **protótipo interativo completo** com 44 telas, 245 botões, 128 cartões, 11 modais, e gerenciamento de foco D-pad. Ele define o **padrão de comportamento de UI** que a skin Kodi deve replicar.

### Princípio Fundamental
> Não copiar a aparência e descartar a lógica. **Preservar e adaptar** o máximo possível dos comportamentos existentes.

---

## 2. Sistema de Cores (Tokens de Design)

Extraído do CSS `:root`:

| Token | Valor | Uso | Equivalente Kodi |
|---|---|---|---|
| `--bg` | `#0d0d0d` | Fundo principal | `<color>` background |
| `--panel` | `#181818` | Painel, cartões base | Background de controles |
| `--panel2` | `#262626` | Painel secundário, switches | Background secundário |
| `--white` | `#f2f2f2` | Texto/destaque principal | `<font color="white">` |
| `--text` | `#d9d9d9` | Texto secundário | `<font color="grey">` |
| `--muted` | `#a6a6a6` | Texto menos importante | `<font color="darkgrey">` |
| `--line` | `rgba(255,255,255,.14)` | Bordas sutis | `<bordercolor>` |
| `--r` | `14px` | Bordas arredondadas | `<borderlength>` |

### Cores adicionais
- `#000` — fundo preto puro (header, footer, player)
- `#333` / `#3d3d3d` — cartões sem imagem (placeholder)
- `#2b2b2b` — fundo do hero
- `#1f1f1f` — variante de cartão

### Gradientes
- **Hero**: `linear-gradient(90deg,#000 8%,rgba(0,0,0,.55) 55%,rgba(0,0,0,.15))` + `linear-gradient(0deg,#000 5%,rgba(0,0,0,.25) 60%)` sobre `#2b2b2b`
- **Cartão**: `linear-gradient(0deg,rgba(0,0,0,.75),rgba(0,0,0,0) 55%)` sobre `#333`
- **Player**: `radial-gradient(circle at 50% 35%,#3a3a3a,#000 75%)`
- **Cartão wide**: `linear-gradient(0deg,rgba(0,0,0,.6),rgba(0,0,0,0) 60%)` sobre `#333`

---

## 3. Tipografia

| Elemento | Fonte | Tamanho |
|---|---|---|
| Corpo | `15px/1.45 "Liberation Sans",Arial,sans-serif` | base |
| Logo "NOVA TV" | `18px`, `700`, `letter-spacing:2px` | header |
| Meta / indicador | `13px` | header |
| H1 tela | `clamp(20px,3.2vw,44px)`, `1.1` line-height | tela |
| H1 hero | `clamp(26px,5vw,68px)` | hero |
| H2 seção | `clamp(15px,1.8vw,26px)` | tela |
| Sub | `0.92em` de base | texto secundário |
| Tag | `0.72em`, `letter-spacing:1px` | destaque |
| Botão nav | `13px` | navegação |

---

## 4. Componentes CSS e Mapeamento para Kodi

### 4.1 `.hero` → HeroBanner / Control Group

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `position:relative; min-height:52%` | Área de destaque | `<control group="hero">` com `position="end"` |
| Gradiente duplo + `#2b2b2b` | Fundo com sobreposição | `<image>` com `colordiff` ou `<subures>` |
| `padding:clamp(14px,3vw,44px)` | Espaçamento interno | `<padding>` nos controles |
| `display:flex; flex-direction:column; justify-content:flex-end` | Conteúdo alinhado à base | `<layout>` com `y=end` |
| `.tag` | rótulo (ex.: "LANÇAMENTO") | `<label>` com `<font>` pequeno |
| `<h1>` | título do conteúdo | `<label>` com `<font>` grande |
| `.sub` | meta (ano, gênero, duração) | `<label>` com `<font color="grey">` |
| `<p>` plot | sinopse | `<texture>` ou `<label>` com rolagem |
| `.ctl` (Assistir/Detalhes/+ Minha lista) | botões de ação | `<button>` com `OnClick` |

### 4.2 `.card` → ListItem / Thumb

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `aspect-ratio:2/3` | Cartão vertical | `<itemlayout>` com proporção 2:3 |
| `flex:0 0 clamp(110px,13vw,180px)` | Largura fixa | `<width>` no itemlayout |
| Gradiente + `#333` | Fundo com sobreposição | `<texture background>` |
| `border:2px solid transparent` | Borda invisível → branca no foco | `<border>` com `<focus>` |
| `.card:focus,.card:hover` → `border-color:var(--white)` | **Foco muda borda para branco** | `<focus bordercolor="white">` |
| `.n` (topo-esquerda) | número de ranking | `<label>` com `<font>` grande, `<position>` |
| `.bar` (inferior) | barra de progresso (continue watching) | `<progressbar>` |
| `data-go="detalhes"` | clique abre modal detalhes | `OnClick>ActivateWindow(10025, ...)` ou `<callback>` |
| `tabindex="0"` | focável | `<control>` com `tabindex` |

### 4.3 `.card.wide` → Wide Thumb (16:9)

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `aspect-ratio:16/9` | Cartão horizontal | `<itemlayout>` com proporção 16:9 |
| `flex-basis:clamp(180px,22vw,300px)` | Largura maior | `<width>` maior |

### 4.4 `.row` → Horizontal Scroll List

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `display:flex; gap:12px; overflow-x:auto` | Linha horizontal deslizante | `<list>` com `<scrolloffset>` e `<orientation>horizontal` |
| `padding:6px 4px 14px` | Espaçamento | `<padding>` |
| Cartões dentro | Cartões 2:3 ou 16:9 | `<itemlayout>` com orientação |

### 4.5 `.grid` → Grid View

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `grid-template-columns:repeat(auto-fill,minmax(clamp(110px,14vw,190px),1fr))` | Grade responsiva | `<view>` com `<grid>` ou `<list>` com `<layout>` |
| `gap:14px` | Espaçamento entre cartões | `<spacing>` |

### 4.6 `.split` → Split Layout (Menu + Conteúdo)

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `grid-template-columns:minmax(170px,22%) 1fr` | Coluna esquerda (menu) + direita (conteúdo) | `<layout>` com duas colunas |
| `gap:18px` | Espaçamento | `<padding>` |

### 4.7 `.menu` → Menu Lateral (Navigation)

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `display:flex; flex-direction:column; gap:8px` | Lista vertical de botões | `<control group="menu">` com `<orientation>vertical` |
| `.menu .btn` | botão de menu | `<button>` com `<label>` |
| `.menu .btn.on` → `background:var(--white);color:#0d0d0d` | **Item selecionado = fundo branco** | `<focus>` ou `<selected>` com `<texture>` branco |
| `data-nav` | navegação para tela | `OnClick>ActivateWindow(...)` |

### 4.8 `.list` → List View

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `.list .li` | item de lista | `<listitem>` |
| `display:flex; justify-content:space-between; gap:12px` | Espaçamento entre colunas | `<layout>` com `position` esquerda/direita |
| `border-bottom:1px solid var(--line)` | Separador sutil | `<border>` ou `<texture>` separadora |
| `.list .li:focus,.list .li:hover` → `background:var(--white);color:#0d0d0d` | **Foco = fundo branco** | `<focus>` com `<texture>` branco |
| `tabindex="0"` | focável | `<control>` com `tabindex` |

### 4.9 `.set` → Setting Item

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `display:flex; justify-content:space-between; align-items:center` | Linha de configuração | `<control>` com layout |
| `background:var(--panel2)` | Fundo | `<texture>` |
| `border-radius:var(--r)` | Borda arredondada | `<borderlength>` |
| `.set:focus,.set:hover` → `background:var(--white);color:#0d0d0d` | **Foco = fundo branco** | `<focus>` com `<texture>` branco |
| `data-tg` | toggle switch | `<toggle>` ou `<button>` com `OnClick` |
| `.sw` | switch visual | `<image>` com `<focus>` / `<selected>` |

### 4.10 `.sw` → Switch/Toggle

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `width:3em; height:1.5em; border-radius:99px` | Switch alinhado | `<image>` com `<width>`/`<height>` |
| `background:#555` (off) | Estado desligado | `<image>` default |
| `.sw.on` → `background:var(--white)` | **Estado ligado = branco** | `<selected>` com `<image>` branco |
| `.sw.on:after` → slider move | Movimento do slider | `<selected>` com `<texture>` diferente |
| `:focus .sw.on` → inverte | Foco inverte contraste | `<focus>` com `<selected>` |

### 4.11 `.player` → Video Player Overlay

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `background:radial-gradient(...)` | Fundo player | `<color>` ou `<texture>` |
| `display:flex; flex-direction:column; justify-content:flex-end` | Conteúdo na base | `<layout>` |
| `.bar` | barra de progresso | `<progressbar>` |
| `.ctl` | controles de reprodução | `<button>` com `OnClick>PlayerControl(...)` |
| `data-m="audio"` | menu de áudio | `OnClick>Dialog(Audio)` |
| `data-m="legenda"` | menu de legendas | `OnClick>Dialog(Subtitles)` |
| `data-m="info"` | informações do vídeo | `OnClick>Dialog(Info)` |
| `data-m="marcadores"` | marcadores | `OnClick>Dialog(Bookmarks)` |

### 4.12 `.epg` → EPG Grid (Guia de TV)

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `grid-template-columns:140px repeat(4,1fr)` | Coluna de canal + 4 horários | `<layout>` com `<grid>` |
| `.h` (header) | cabeçalho | `<label>` com `<font color="white">` |
| `.n` (now) | programa atual | `<label>` com `<font>` e `<texture>` destacado |
| `background:var(--panel)` | fundo da grade | `<texture>` |

### 4.13 `.kb` → Virtual Keyboard

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `grid-template-columns:repeat(10,1fr)` | 10 colunas | `<layout>` com `<grid>` |
| `.btn` | tecla | `<button>` com `<label>` |

### 4.14 `.dlg` → Dialog Modal

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `background:var(--panel)` | fundo | `<texture>` |
| `border-radius:var(--r)` | borda arredondada | `<borderlength>` |
| `width:min(860px,100%)` | largura máxima | `<width>` |
| `max-height:90vh; overflow:auto` | rolagem interna | `<scroll>` |

### 4.15 `.stage` / `.scr` → Screen Container

| Propriedade CSS | Valor | Mapeamento Kodi |
|---|---|---|
| `aspect-ratio:16/9` | proporção fixa | `<resolution>1920x1080` |
| `.scr` | tela individual | `<window>` ou `<layout>` |
| `.scr.on` → `display:block` | tela ativa | `<window id="...">` |

---

## 5. Estados de Interação

### 5.1 Estados Visuais Confirmados

| Estado | Acionamento | Efeito Visual | Mapeamento Kodi |
|---|---|---|---|
| **Foco (`:focus`)** | Tab / D-pad | Borda branca (`card`) / Fundo branco (`btn`, `set`, `li`) | `<focus>` |
| **Selecionado (`.on`)** | Clique / Enter | Fundo branco + texto escuro | `<selected>` ou `<focus>` |
| **Hover (`:hover`)** | Mouse | Igual a foco | N/A (D-pad usa foco) |
| **Off (`.sw` default)** | Padrão | `background:#555` | `<image>` default |
| **On (`.sw.on`)** | Toggle | `background:var(--white)` + slider move | `<selected>` com `<image>` |
| **Foco + On (`.set:focus .sw.on`)** | Foco no switch ligado | Inverte contraste | `<focus><selected>` combinado |

### 5.2 Estados de Tela

| Estado | Descrição | Mapeamento Kodi |
|---|---|---|
| Tela ativa (`.scr.on`) | `display:block` | `<window id>` ativo |
| Tela inativa (`.scr`) | `display:none` | `<window id>` inativo |
| Modal aberto (`#mask.on`) | máscara visível + diálogo | `<dialog>` com `<onload>` |
| Modal fechado (`#mask`) | oculto | `<dialog>` sem `<onload>` |

---

## 6. Mapeamento de Navegação

### 6.1 Navegação entre Telas (44 telas)

**Mecanismo**: Função `show(i)` — alterna `.on` entre `.scr`, atualiza botões de nave, Índice, meta, `location.hash`, move foco.

**Gatilhos**:
- `data-i` (botões de nave `#nav` e índice `#idx`) → `show(+dataset.i)`
- `ArrowRight` / `ArrowLeft` → `show(cur+1)` / `show(cur-1)` (cíclico)
- `#prev` / `#next` → `show(cur-1)` / `show(cur+1)`

**Mapeamento para Kodi**:
- `data-i` → `OnClick>ActivateWindow(<window_id>)`
- `ArrowRight/Left` → `<onleft>` / `<onright>` no controle de navegação
- `#prev/#next` → `<onup>` / `<ondown>` ou botões de navegação

### 6.2 Navegação por Menu (`data-nav`)

**Mecanismo**: Clique em `.menu .btn[data-nav]` → busca tela correspondente via `map` e chama `show()`.

**Mapeamento de menus**:

| Menu | Tela alvo | Window Kodi |
|---|---|---|
| TV ao vivo | 5 (Canais) | `ActivateWindow(10025, plugin://...BrazucaPlay...#menu_canais)` |
| Filmes | 24 (Filmes) | `ActivateWindow(10025, plugin://...BrazucaPlay...#filmes_menu)` |
| Séries | 6 (Serie) | `ActivateWindow(10025, plugin://...BrazucaPlay...#series_menu)` |
| Novalas | 6 (Serie) | `ActivateWindow(10025, plugin://...BrazucaPlay...#novelas_menu)` |
| Animes | 6 (Serie) | `ActivateWindow(10025, plugin://...BrazucaPlay...#animes_menu)` |
| Doramas | 6 (Serie) | `ActivateWindow(10025, plugin://...BrazucaPlay...#doramas_menu)` |
| Desenhos | 6 (Serie) | `ActivateWindow(10025, plugin://...BrazucaPlay...#desenhos_menu)` |
| Player | 37 (CPlayer) | `ActivateWindow(10001)` |
| Mídia | 38 (CMidia) | `ActivateWindow(10004)` |
| TV | 39 (CTV) | `ActivateWindow(10007)` |
| Serviços | 40 (CServ) | `ActivateWindow(10008)` |
| Interface | 41 (CInt) | `ActivateWindow(10003)` |
| Sistema | 42 (CSis) | `ActivateWindow(10002)` |
| Skin | 16 (Config) | `ActivateWindow(10003)` |
| Perfis | 43 (CPerf) | `ActivateWindow(10006)` |

### 6.3 Navegação por Atalhos (`data-go`)

**Mecanismo**: Clique em `.card[data-go]` ou `.btn[data-go]` → busca tela alvo ou abre modal.

| `data-go` | Alvo | Mapeamento Kodi |
|---|---|---|
| `detalhes` | modal "detalhes" | `OnClick>ActivateWindow(10025, ...)` ou diálogo de informações |
| `player` | tela 7 (Player) | `OnClick>PlayerControl(Play)` ou `ActivateWindow(10001)` |
| `canais` | tela 5 (Canais) | `ActivateWindow(10025, plugin://...BrazucaPlay...#menu_canais)` |
| `filmes` | tela 24 (Filmes) | `ActivateWindow(10025, plugin://...BrazucaPlay...#filmes_menu)` |
| `serie` | tela 6 (Serie) | `ActivateWindow(10025, plugin://...BrazucaPlay...#series_menu)` |
| `config` | tela 16 (Config) | `ActivateWindow(10003)` |

### 6.4 Navegação por Tela (Home Menu)

**Tela Aurora** tem `homeMenu(0)` com botões:
- "Categorias" → `data-go="canais"`
- "TV ao vivo" → `data-go="canais"`
- "Filmes" → `data-go="filmes"`
- "Séries" → `data-go="serie"`
- "Ajustes" → `data-go="config"`

**Mapeamento para Kodi Home**: Estes são os **atalhos principais da tela inicial** — devem ser os primeiros items focáveis após o Hero.

---

## 7. Mapeamento de Foco (D-pad)

### 7.1 Comportamento de Foco

**Mecanismo**: 
- `show(i)` — após trocar de tela, busca `#s{i} [tabindex],#s{i} button` e chama `.focus()`
- `ArrowDown/ArrowUp` — dentro da tela/modal, percorre `[tabindex="0"],button` sequencialmente
- `Enter` — aciona o elemento focado (`document.activeElement.click()`)

**Mapeamento para Kodi**:

| Comportamento HTML | Equivalente Kodi |
|---|---|
| `.focus()` após trocar de tela | `<onload>` com `<control>` de foco |
| `ArrowDown` → próximo elemento focável | `<ondown>` / `<onup>` no controle |
| `Enter` → aciona elemento focado | `<onclick>` no controle |
| `scrollIntoView` (rolagem automática) | `<scrolloffset>` / `<autoscroll>` |

### 7.2 Sequência de Foco por Tela

| Tela | Primeiro elemento focável | Comportamento |
|---|---|---|
| Aurora | Botão hero "Assistir" | Foco no hero |
| Canais | Menu "Opções de TV" | Foco no menu |
| Serie | Menu "Séries" | Foco no menu |
| Player | Botão "Pausar" | Foco no player |
| Config | Menu "Interface" | Foco no menu |

### 7.3 Foco em Cartões

**Cartões** têm `tabindex="0"` → são focáveis individualmente.
- `Enter` no cartão → abre modal "detalhes"
- Foco → borda branca (`border-color:var(--white)`)

**Mapeamento Kodi**: `<listitem>` com `<control>` focável + `<onclick>`.

---

## 8. Mapeamento de Modais

### 8.1 Modais Implementados

| Modal | Conteúdo | Gatilho | Mapeamento Kodi |
|---|---|---|---|
| `detalhes` | Título, sinopse, nota, diretor, botão "Reproduzir" | Cartão `data-go="detalhes"` | `Dialog(VideoInfo)` ou `ActivateWindow(10025, ...)` |
| `ctx` | Reproduzir, Marcar assistido, Adicionar favoritos, Informações | `data-m="ctx"` | `<onclick>ContextMenu` ou `Dialog(ContextMenu)` |
| `confirm` | "Remover item?" + Sim/Não | — | `<dialog>` com confirmação |
| `kb` | Teclado virtual | `data-m="kb"` | `<onclick>Keyboard` ou `<dialog>` teclado |
| `power` | Desligar/Reiniciar/Suspender/Sair | `data-m="power"` | `<onclick>SystemPower` / `Quit` |
| `prog` | Barra de progresso "Atualizando" | `data-m="prog"` | `<onclick>UpdateLibrary` |
| `notif` | Notificação informativa | — | `<notification>` |
| `audio` | Seleção de áudio (Português AC3, Inglês AAC) | `data-m="audio"` | `<onclick>Dialog(Audio)` |
| `legenda` | Legendas: ativar, idioma, sincronização | `data-m="legenda"` | `<onclick>Dialog(Subtitles)` |
| `info` | Codec, resolução, áudio | `data-m="info"` | `<onclick>Dialog(VideoInfo)` |
| `marcadores` | Lista de marcadores + adicionar | `data-m="marcadores"` | `<onclick>Dialog(Bookmarks)` |

### 8.2 Comportamento dos Modais

- `modal(k)` — insere HTML no `#dlg`, adiciona `.on` no `#mask`, foca primeiro `.on` ou `button`
- `close()` — remove `.on` do `#mask`, chama `show(cur)`
- `#mask` click outside → `close()`
- `Escape` → `close()`

**Mapeamento para Kodi**:
- `modal(k)` → `<onload>` do diálogo
- `close()` → `<onclose>` do diálogo
- Clique fora → não aplicável (Kodi usa `<onclose>`)
- `Escape` → `<onclose>`

---

## 9. Mapeamento das 44 Telas

### Grupo 1: Início e Entretenimento (1-8)

| # | Tela | Componentes | Conteúdo | Mapeamento Kodi |
|---|---|---|---|---|
| 1 | **Aurora** | hero + homeMenu + row (7 cards) | Home com hero + lançamentos | `Home.xml` layout Aurora |
| 2 | **Blade** | hero + homeMenu + 2 rows (8+6 wide) | Home com hero + filmes/séries recentes | `Home.xml` layout Blade |
| 3 | **Top 10** | row (10 cards com números) | Ranking por popularidade | `View_500_Wall` ou `Home.xml` layout Top10 |
| 4 | **Esportes** | split (menu 3 items + list 3) | Navegação TV Brazuca | `VideoNav.xml` ou `MyPVR*.xml` |
| 5 | **Guia** | epg grid | Programação PVR (condicional) | `MyPVRGuide.xml` |
| 6 | **Canais** | split (menu 2 + list 5) | TV ao vivo (rota `tv`) | `VideoNav.xml` com `plugin://...#menu_canais` |
| 7 | **Serie** | split (menu 6 + grid 12) | Séries/Novelas/Animes/Doramas/Desenhos | `VideoNav.xml` com `plugin://...#series_menu` |
| 8 | **Player** | player + bar + ctl 8 | Reprodução com controles | `VideoOSD.xml` |

### Grupo 2: Variações e Configurações (9-16)

| # | Tela | Componentes | Mapeamento Kodi |
|---|---|---|---|
| 9 | Aurora (variação) | hero + homeMenu + row 7 | Variação do Home Aurora |
| 10 | Blade (variação) | hero + homeMenu + 2 rows | Variação do Home Blade |
| 11 | Top 10 (variação) | row 10 | Variação do ranking |
| 12 | Esportes (variação) | split (menu + list 2) | Variação esportes |
| 13 | Guia (variação) | epg grid | Variação guia |
| 14 | Canais (variação) | list 3 | Variação canais |
| 15 | Serie (variação) | list 6 (episódios) | Detalhes de série |
| 16 | Player (variação) | player + ctl 5 | Player com marcadores |
| 17 | **Config** | split (menu 7 + set 7) | Configurações de interface | `Settings.xml` Interface |

### Grupo 3: Mídia e Navegação (18-28)

| # | Tela | Componentes | Mapeamento Kodi |
|---|---|---|---|
| 18 | Musica | split (menu 5 + grid 12) + player | `MusicNav.xml` / `MusicOSD.xml` |
| 19 | Tocando | flex (cover + eq + bar + ctl 5) | `MusicOSD.xml` Now Playing |
| 20 | VideoMus | grid 12 wide | `VideoNav.xml` music videos |
| 21 | Radio | list 3 (condicional PVR) | `MyPVRRadio.xml` ou vazio |
| 22 | Jogos | grid 8 (condicional) | `GamesNav.xml` ou vazio |
| 23 | Complementos | split (menu 4 + list 5) | `AddonBrowser.xml` |
| 24 | Imagens | grid 12 wide | `PicturesNav.xml` |
| 25 | **Filmes** | split (menu 5 + grid 18) | `VideoNav.xml` com `plugin://...#filmes_menu` |
| 26 | Favoritos | list 3 | `MyFavourites.xml` |
| 27 | Clima | flex (set 3) | `Weather.xml` |
| 28 | Arquivos | list 1 | `FileManager.xml` |

### Grupo 4: Sistema e Gerenciamento (29-36)

| # | Tela | Componentes | Mapeamento Kodi |
|---|---|---|---|
| 29 | Energia | ctl (power 4) | `Power.xml` |
| 30 | Busca | set 1 + ctl 2 | `Search.xml` / `Keyboard.xml` |
| 31 | Gravacoes | list 2 (condicional PVR) | `MyPVRRecordings.xml` |
| 32 | Timers | list 2 (condicional PVR) | `MyPVRTimers.xml` |
| 33 | Perfis | list 2 | `Profiles.xml` |
| 34 | Contexto | ctl 1 | Menu de contexto Kodi |
| 35 | AudioLeg | set 4 | `DialogAudio.xml` / `DialogSubtitles.xml` |
| 36 | Sobre | split (menu 4 + list 5) | `SystemInfo.xml` |

### Grupo 5: Configurações Avançadas (37-44)

| # | Tela | Componentes | Mapeamento Kodi |
|---|---|---|---|
| 37 | Ajustes | split (menu 12 + conteúdo) | `Settings.xml` raiz |
| 38 | CPlayer | split (menu 6 + set 3) | `Settings.xml` Player |
| 39 | CMidia | split (menu 6 + set 2) | `Settings.xml` Media |
| 40 | CTV | split (menu 6 + conteúdo) | `Settings.xml` TV/PVR |
| 41 | CServ | split (menu 6 + set 2) | `Settings.xml` Services |
| 42 | CInt | split (menu 6 + set 4) | `Settings.xml` Interface |
| 43 | CSis | split (menu 6 + set 2) | `Settings.xml` System |
| 44 | CPerf | split (menu 7 + conteúdo) | `Settings.xml` Profiles |

---

## 10. Mapeamento de Switches (Configurações)

### Switches no HTML

| Tela | Switch | Estado Inicial | Mapeamento Kodi |
|---|---|---|---|
| Config (17) | Banner em destaque | ON (1) | `<setting type="boolean">` |
| Config (17) | Rotação automática do banner | ON (1) | `<setting type="boolean">` |
| Config (17) | Mostrar relógio | ON (1) | `<setting type="boolean">` |
| Config (17) | Idioma | — (valor "Português (Brasil)") | `<setting type="string">` |
| Config (17) | Fonte | — ("Liberation Sans") | `<setting type="string">` |
| Config (17) | Calibrar tela | — (valor "›") | `<setting type="action">` |
| Config (17) | Modo de suspensão | OFF (0) | `<setting type="boolean">` |
| CPlayer (38) | Reprodução automática | ON (1) | `<setting type="boolean">` |
| CPlayer (38) | Retomar reprodução | ON (1) | `<setting type="boolean">` |
| CPlayer (38) | Legendas automáticas | OFF (0) | `<setting type="boolean">` |
| CMidia (39) | Atualizar biblioteca ao iniciar | ON (1) | `<setting type="boolean">` |
| CMidia (39) | Extrair informações | ON (1) | `<setting type="boolean">` |
| CServ (41) | Serviço de clima | OFF (0) | `<setting type="boolean">` |
| CServ (41) | Serviço de legendas | ON (1) | `<setting type="boolean">` |
| CInt (42) | Banner em destaque | ON (1) | `<setting type="boolean">` |
| CInt (42) | Rotação automática | ON (1) | `<setting type="boolean">` |
| CInt (42) | Mostrar relógio | ON (1) | `<setting type="boolean">` |
| CInt (42) | Idioma | — ("Português (Brasil)") | `<setting type="string">` |
| CSis (43) | Modo de suspensão | OFF (0) | `<setting type="boolean">` |
| CSis (43) | Calibrar tela | — ("›") | `<setting type="action">` |
| AudioLeg (35) | Ativar legendas | ON (1) | `<setting type="boolean">` |
| AudioLeg (35) | Idioma das legendas | — ("Português") | `<setting type="string">` |
| AudioLeg (35) | Sincronizar legendas | — ("0,0 s") | `<setting type="string">` |
| AudioLeg (35) | Trilha de áudio | — ("Português · AC3 5.1") | `<setting type="string">` |

---

## 11. Comportamentos Específicos

### 11.1 Hero — Conteúdo em Destaque

**HTML**: Hero com tag, título, meta, sinopse, botões "Assistir", "Detalhes", "+ Minha lista".

**Mapeamento Kodi**:
- Tag → `<label>` com `<font>` pequeno, `<textcolor>` branco
- Título → `<label>` com `<font>` grande
- Meta → `<label>` com `<font color="grey">`
- Sinopse → `<label>` com rolagem ou `<texture>`
- Botões → `<button>` com `<onclick>`

**Comportamento**: Foco no primeiro botão ("Assistir") ao abrir a tela.

### 11.2 Cartões — Conteúdo Focável

**HTML**: Cartão com imagem (gradiente), título, opcional número/ranking, opcional barra de progresso.

**Mapeamento Kodi**:
- Imagem → `<thumb>` ou `<texture>`
- Título → `<label>`
- Número → `<label>` com `<font>` grande, `<position>top-left`
- Barra → `<progressbar>`
- Foco → `<bordercolor>white</bordercolor>` + `<borderlength>`

**Comportamento**:
- `Enter` → abre modal "detalhes"
- Foco → borda branca
- Cartão wide (16:9) → para séries/filmes em destaque

### 11.3 Menu Lateral — Navegação

**HTML**: Botões verticais, item selecionado com fundo branco.

**Mapeamento Kodi**:
- `<control group="menu">` com `<orientation>vertical`
- Item selecionado → `<selected>` com `<texture>` branco + `<textcolor>black</textcolor>`
- Foco → `<focus>` com `<texture>` branco

**Comportamento**:
- `↑↓` move entre itens do menu
- `Enter` navega para a tela correspondente
- Foco sempre no menu quando a tela é aberta

### 11.4 Switch — Configuração

**HTML**: Switch com slider, estado ON = fundo branco.

**Mapeamento Kodi**:
- `<control>` com `<texture>` default (off) e `<focus>`/`<selected>` (on)
- `<onclick>` alterna o valor

**Comportamento**:
- `Enter` alterna ON/OFF
- Visual: fundo `#555` (off) → `var(--white)` (on)
- Foco no switch inverte contraste

### 11.5 Modal — Diálogo

**HTML**: Máscara sobre a tela, diálogo centralizado com conteúdo.

**Mapeamento Kodi**:
- `<dialog>` com `<onload>` e `<onclose>`
- Foco no primeiro botão
- `Esc` fecha

**Comportamento**:
- Foco sempre no primeiro botão do modal
- `↑↓` move entre botões
- `Enter` aciona
- `Esc` fecha

### 11.6 EPG — Guia de TV

**HTML**: Grade com canal + 4 horários, programa atual destacado.

**Mapeamento Kodi**:
- `<layout>` com `<grid>`
- Cabeçalho → `<label>` com `<font color="white">`
- Programa atual → `<label>` com `<texture>` destacado

**Comportamento**:
- `←→` move entre canais
- `↑↓` move entre horários
- `Enter` seleciona programa

### 11.7 Player — Reprodução

**HTML**: Fundo radial, controles inferiores (Anterior, Voltar 10s, Pausar, Avançar 30s, Próximo, Áudio, Legendas, Info).

**Mapeamento Kodi**:
- `<player>` com `<control>` de reprodução
- Barra → `<progressbar>`
- Controles → `<button>` com `<onclick>PlayerControl(...)`

**Comportamento**:
- Foco no botão "Pausar"
- `←→` busca no tempo
- `Enter` pausa/reproduz
- `Esc` sai do player

### 11.8 Busca — Teclado Virtual

**HTML**: Campo de texto + teclado 10 colunas.

**Mapeamento Kodi**:
- `<dialog>` com `<keyboard>`
- Teclas → `<button>` com `<onclick>Keyboard(...)`

**Comportamento**:
- `←→↑↓` move entre teclas
- `Enter` insere caractere
- `Esc` cancela

---

## 12. Mapeamento de Eventos (HTML → Kodi)

| Evento HTML | Comportamento | Equivalente Kodi |
|---|---|---|
| `click [data-i]` | `show(+dataset.i)` | `OnClick>ActivateWindow(<id>)` |
| `click [data-go]` | `show(target)` ou `modal('detalhes')` | `OnClick>ActivateWindow(...)` ou `Dialog(VideoInfo)` |
| `click [data-m]` | `modal(dataset.m)` | `OnClick>Dialog(<tipo>)` |
| `click [data-x]` | `close()` | `OnClick>Close` / `<onclose>` |
| `click [data-tg]` | alterna `.sw.on` | `OnClick>ToggleSetting` |
| `click [data-nav]` | `show(map[nav])` | `OnClick>ActivateWindow(...)` |
| `click #mask` (fora) | `close()` | `<onclose>` (fora) |
| `click #prev` | `show(cur-1)` | `OnClick>ActivateWindow(<prev>)` |
| `click #next` | `show(cur+1)` | `OnClick>ActivateWindow(<next>)` |
| `keydown ArrowRight` | `show(cur+1)` | `<onright>ActivateWindow(<next>)` |
| `keydown ArrowLeft` | `show(cur-1)` | `<onleft>ActivateWindow(<prev>)` |
| `keydown ArrowDown` | foco próximo elemento | `<ondown>` (foco próximo) |
| `keydown ArrowUp` | foco anterior elemento | `<onup>` (foco anterior) |
| `keydown Enter` | aciona elemento focado | `<onclick>` no controle |
| `keydown Escape` | fecha modal / volta tela 1 | `<onclose>` / `<onleft>` |

---

## 13. Mapeamento de Foco por Controle

### 13.1 Hierarquia de Foco

```
1. Tela ativa (.scr.on)
   ├─ Primeiro elemento focável (focus automático)
   │  ├─ Hero: botão "Assistir"
   │  ├─ Menu: primeiro item
   │  ├─ Cartão: primeiro cartão
   │  └─ Switch: primeiro switch
   └─ Navegação ↑↓ entre elementos
2. Modal aberto (#mask.on)
   ├─ Primeiro botão .on
   └─ Navegação ↑↓ entre botões
```

### 13.2 Rolagem Automática

**HTML**: `scrollIntoView({inline:'center',block:'nearest'})` — garante visibilidade do elemento focado.

**Kodi**: `<scrolloffset>` e `<autoscroll>` no controle de lista.

---

## 14. Prioridades de Implementação (Reconstrução)

### Fase 1 (Imediata) — Telas do Home
1. **Aurora (tela 1)** — Hero + homeMenu + row de lançamentos
2. **Blade (tela 2)** — Hero + homeMenu + 2 rows (filmes/séries recentes)
3. **Top 10 (tela 3)** — row de ranking

### Fase 2 — Telas de Conteúdo
4. **Canais (tela 6)** — TV ao vivo com menu + lista
5. **Serie (tela 7)** — Séries com menu + grade
6. **Filmes (tela 24)** — Filmes com menu + grade
7. **Player (tela 8)** — Controles de reprodução

### Fase 3 — Telas de Configuração
8. **Config (tela 17)** — Configurações de interface
9. **Ajustes (tela 37)** — Raiz de configurações
10. **Switches (11.4)** — Toggles de configuração

### Fase 4 — Telas de Sistema
11. **Modais** — Detalhes, contexto, áudio, legendas, marcadores
12. **EPG (tela 5)** — Guia de TV (condicional PVR)
13. **Busca (tela 30)** — Teclado virtual

### Fase 5 — Telas Restantes
14. **Musica/Tocando** — Player de música
15. **Complementos** — Gerenciamento de addons
16. **Perfis/Sobre** — Sistema e perfis
17. **Arquivos/Energia/Clima** — Telas utilitárias

---

## 15. Regras de Preservação

1. **Nunca descartar lógica interativa** — cada `data-*` tem um comportamento mapeado.
2. **Foco sempre definido** — nenhuma tela deve abrir sem foco explícito.
3. **Estados visuais obrigatórios** — foco deve mudar cor/borda.
4. **Navegação D-pad completa** — ←→ entre telas, ↑↓ entre elementos, Enter acionar, Esc fechar.
5. **Modais com fechamento** — sempre `Esc` ou clique em fechar.
6. **Switches alternáveis** — sempre `Enter` paratoggle.
7. **Cartões clicáveis** — sempre `Enter` abre detalhes.
8. **Menus com indicador** — item selecionado sempre visível.

---

## 16. Links de Referência

- **HTML original**: `ENTREGA_FINAL/PREVIEW_KODI.html` (preservado intacto)
- **Base skin**: `kodi/skin.estilo.personalizado/` (914 files, 106 XMLs)
- **Backup real**: `backup_files/files/.kodi/` (38 addons)
- **Brazuka Play**: `plugin.video.BrazucaPlay.Matrix` v2.1.4
- **Favoritos**: `backup_files/files/.kodi/userdata/favourites.xml` (7 entradas)
- **Imagens de referência**: `/tmp/arena-coding-uploads/` (5 imagens)

---

## 17. Documento de Referência — Estado 2026-11-11

- HTML: 44 telas, 245 botões, 128 cartões, 11 modais, 24 switches
- CSS: 8 tokens de cor, 4 gradientes, tipografia Liberation Sans
- JS: 3 funções (`show`, `modal`, `close`), 3 eventos (`click`, `keydown`)
- Navegação: 44 telas cíclicas, 15 mapeamentos `data-nav`, 6 mapeamentos `data-go`
- Foco: automático ao abrir tela, sequencial com ↑↓, Enter aciona, Esc fecha
- Estados visuais: `:focus` (borda/fundo branco), `.on` (selecionado), `.sw.on` (switch ligado)
