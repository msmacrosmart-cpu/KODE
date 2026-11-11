# COMPONENT_MAP — componentes reutilizáveis da skin SMARTEDTV

Descreve os blocos de XML que se repetem (e que **não** devem ser alterados sem
atualizar este mapa). Atualizado na rodada 8 (v1.0.33) com os componentes novos
**linha Brazuca Play**, **botão de categoria** e **ícone de Ajustes**; nenhum
componente validado antes foi modificado.

## 1. Includes globais (`xml/Includes.xml`)

Componentes nomeados, incluídos por `TopBar`, `BottomBar` e pelas telas:

| Include | Onde é usado | Papel |
|---|---|---|
| `CommonScrollbars` | todas as listas | scrollbars verticais/horizontais |
| `HiddenObject` | Home, VideoNav | foco inicial invisível |
| `RatingCircle` / `UserRatingContent` | VideoNav, info | notas |
| `InfoList` / `LeftAlignedInfo` | VideoNav | painel de informação da lista |
| `DefaultSimpleListLayout` | VideoNav | layout de lista simples |
| `InfoFlag` / `MediaFlag(s)` | VideoNav, Home | selos de qualidade/idioma |
| `TopBar` / `TopBarLabels` / `BreadcrumbsLabel` | todas as telas | barra superior + caminho |
| `BottomBar` / `BottomBarTwoListInfo` | diálogos e listas | barra inferior |
| `FullScreenDimensions` | todas as telas | 1920×1080 de referência + `%` |
| `FocusableProgressBar` | player e Ajustes | barra focável |
| `ContentPanel` | Ajustes e listas | painel de conteúdo |
| `WeatherIconHome` / `WeatherIconMyWeather` | Home, Tempo | clima |
| `AddonLauncherPanel` / `FileManagerPanel` | Add-ons, gerenciador | painéis nativos |
| `DialogBackgroundCommons` | diálogos | fundo padrão |

## 2. Barra superior da Home

`xml/Home.xml`, quatro `button` 60×60 ancorados em `right`:

| id | direita | Ícone | Ação |
|---|---|---|---|
| 9124 | 376 | `DefaultAddonProgram.png` | `ActivateWindow(10040)` — Add-ons |
| 9121 | 276 | lupa | `ActivateWindow(1107)` — Busca |
| 9122 | 176 | engrenagem | `ActivateWindow(Settings)` — **Ajustes** (10004) |
| 9123 | 76 | power | `ActivateWindow(ShutdownMenu)` — **Energia** |

Contrato: os ids 9121–9124 são estáveis; testes e o mapa de telas dependem deles.

## 3. Hero (destaque)

`grouplist` **9300** (1000×56) + botões **9301 Assistir**, **9302 Trailer**,
**9303 Informações**; faixa 150–476. Fontes: `$INFO[ListItem.*]` do item
focado na linha 9200 (nunca texto fixo). Alvo:
- 9301 → `PlayMedia($INFO[Container(9200).ListItem.FileNameAndPath])`
- 9302 → `PlayMedia($INFO[Container(9200).ListItem.Trailer])`
- 9303 → `SetFocus(9200)`

## 4. Linha de conteúdo (card) — componente novo/atualizado

Cada linha é um `list` horizontal com `itemlayout`/`focusedlayout` **210×150**:

```
image  210×150  $VAR[ItemArt]           (pôster/fanart do addon)
image  210×50   pb_scrim_v.png          (preto degradê, y=100)
label  194×38   $INFO[ListItem.Label]   (font10, y=106, sem scroll)
focused: mesmo layout com colordiffuse branco (destaque)
```

| Linha | id | y (lista) | `content` |
|---|---|---|---|
| TV ao vivo · Brazuca Play | 9200 | 526 | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais` |
| Filmes · Brazuca Play | 9201 | 712 | `…?mode=27&url=%23filmes_menu` |
| Séries · Brazuca Play | 9202 | 898 | `…?mode=27&url=%23series_menu` |

Todos os itens vêm do addon: **zero** `ListItem` fictício, **zero** texto de
demo. Navegação: `onup` 9000, `ondown` da última linha → 9000.

## 5. Navegação por categorias (grouplist 9000)

`grouplist` de 56 px no rodapé com `button` filhos. Categorias e destinos:

| id | Rótulo | Destino |
|---|---|---|
| 9010 | TV ao vivo | `mode=21&url=%23menu_canais` |
| 9011 | Filmes | `mode=27&url=%23filmes_menu` |
| 9012 | Séries | `mode=27&url=%23series_menu` |
| 9013 | Novelas | `mode=25` |
| 9014 | Animes | `mode=22` |
| 9015 | Doramas | `mode=31` |
| 9016 | Desenhos | `mode=28` |
| 9017 | Busca | `mode=20` |
| 9019 | Favoritos | `ActivateWindow(10060)` |
| 9021 | Add-ons | `ActivateWindow(10040)` |
| 9022 | Brazuca Play | `mode=0` (raiz real do addon) |
| 9018 | YouTube | plugin YouTube (se instalado) |

## 6. Template de Ajustes (`xml/SettingsCategory.xml`)

Template nativo do Kodi reutilizado pela skin; ids fixos do Kodi:

| id | tipo | Uso |
|---|---|---|
| 5 / 3 | grouplist | coluna de categorias / de itens |
| 7 / 10 | button | ações (inclusive "Voltar") |
| 8 / 20 | radiobutton | opções exclusivas |
| 9 | spincontrolex | listas de valores |
| 13 | sliderex | volumes/velocidades |
| 15 | colorbutton | cores de tema |
| 11 | image | **ícone do item** (`media/icons/settings/`) |
| 2 / 14 | label | títulos e valores |
| 6 | textbox | descrição longa |
| 60 | scrollbar | rolagem |

Regra visual: ícone 48×48 à esquerda, texto a partir de 72 px, nunca cortado
(`textwidth` + margem). Ícones: 26 PNGs em `media/icons/settings/`, gerados por
`tools/kodi/make-settings-icons.py`; prévia em `tools/kodi/preview-settings-grid.py`.

## 7. Desbloqueio discreto (`xml/Includes_SecretUnlock.xml`)

`onload` da janela 10004 incrementa um contador em `Skin.String`; no 5º acesso
seguido grava `Skin.SetBool(secret_unlocked)` (persistido em `guisettings.xml`,
sobrevive a reinício). Nenhum texto, som ou animação é exibido.

## 8. Navegação de vídeo (`xml/MyVideoNav.xml`)

- `list` **50** (principal) e **51** (variante), views 50/51/52;
- `grouplist` 9000 + botões 9010–9016 (ordenar/ver/ajustes);
- `grouplist` 9050 + botões 9051–9053 (ações de contexto);
- recebe qualquer `plugin://` do addon e mantém Back nativo (pilha de janelas).

## 9. Contratos que não podem quebrar

1. ids 9121–9124, 9000, 9010–9022, 9200–9202, 9300–9303 são referenciados por
   testes (`tests/test_skin_phone_layout.py`, `tests/test_advanced_unlock.py`) e
   pelo simulador (`tools/kodi/simulate-first-boot.py`);
2. `<content>` das linhas sempre aponta para `plugin://plugin.video.BrazucaPlay.Matrix/`;
3. Ajustes sempre com ícone em cada item (validado por
   `tools/kodi/preview-settings-grid.py`, que falha se faltar PNG);
4. nenhum layout alternativo (blade/top10/sports) é removido ao mexer no layout
   principal: as variantes continuam no `Home.xml` e são escolhidas por
   `Skin.String(home_layout,…)`.

## 10. Carrossel de conteúdo (v1.0.34)

Componente que alimenta as linhas da Home com mídia de verdade:

| Peça | Arquivo | Papel |
|---|---|---|
| `carousel(rpc, alvo)` | `kodi/addons/plugin.video.smarted/catalogue.py` | escolhe a raiz do addon e percorre até a mídia |
| `walk(rpc, root, depth, prefer)` | idem | desce uma pasta por nível; para quando há mídia |
| rota `carrossel` | `default.py` | serve a lista com cache diário e fallback de favoritos |
| `_widget_cached` | `default.py` + `daily_cache.py` | cache `carrossel-<alvo>` no perfil |
| linha 9206 | `xml/Home.xml` | favoritos nativos (`favourites://`) |

Contratos: 168×120 por cartaz; `<content target="videos">`; `IsPlayable=true`
quando o item é mídia; `onup/ondown` encadeando 9206 → 9200 → 9201 → 9202 → 9000.
