# SCREEN_MAP — mapa de telas da skin SMARTEDTV (Kodi 21 / Omega)

Complementa `XML_MAP.md` (que descreve arquivo por arquivo) e `INTERACTION_MAP.md`
(fluxos de navegação). Aqui cada **tela real do Kodi** é mapeada para o XML da
skin, com os controles que a compõem, a fonte de conteúdo e os estados previstos.

Atualizado na rodada 8 (v1.0.33): a Home passa a abrir o addon **Brazuca Play**
de verdade nas linhas e nos botões de categoria, e entram explicitamente as telas
**Ajustes** e **Energia**. Nenhuma tela anterior foi removida.

## 1. Telas

| # | Tela | Janela Kodi | Arquivo | Entrada | Fonte de conteúdo |
|---|------|-------------|---------|---------|-------------------|
| 1 | Home | `10000` | `xml/Home.xml` | boot / `ActivateWindow(Home)` / botão Home dos remotes | 3 linhas Brazuca Play + Favoritos + biblioteca |
| 2 | Ajustes (SMARTEDTV) | `10004` | `xml/Settings.xml` | botão **Ajustes** (9122) da barra superior | categorias nativas do Kodi |
| 3 | Categoria de Ajustes | `10004` (template) | `xml/SettingsCategory.xml` | seleção de uma categoria em Ajustes | settings do Kodi (sliders, spins, colorbutton…) |
| 4 | Navegação de vídeo | `10025` | `xml/MyVideoNav.xml` | qualquer rota do addon / Favoritos | `plugin://`, `favourites://`, `videodb://` |
| 5 | Favoritos | `10060` | `xml/MyFavourites.xml` | 9019 / 9124 → `ActivateWindow(10040)` e favoritos nativos | `favourites.xml` (Brazuka Play sincronizado) |
| 6 | Add-ons | `10040` | nativo | 9021 / 9124 | add-ons instalados |
| 7 | Menu de energia | `ShutdownMenu` | nativo (skin aplica tema) | botão **Energia** (9123) | ações de desligar/reiniciar/sair |
| 8 | Busca | `1107` | nativo + `Includes` | 9051 (Ajustes), lupa | teclado do Kodi |

## 2. Home (`xml/Home.xml`)

Ordem vertical (1080p, tudo responsivo por `%`/`right`/`bottom`):

| Faixa | y | Controles | Conteúdo |
|-------|---|-----------|----------|
| Barra superior | 20–80 | 9124 Add-ons, 9121 Busca (1107), 9122 **Ajustes** (`Settings`=10004), 9123 **Energia** (`ShutdownMenu`) | ícones 60×60, ancorados em `right` 376/276/176/76 |
| Hero | 150–476 | 9300 grouplist **Assistir**, 9301 Assistir, 9302 Trailer, 9303 Informações | poster/fanart + sinopse da linha 9200 |
| Linha 1 — TV ao vivo · Brazuca Play | 500 (lista 526) | `list` 9200 → `mode=21&url=#menu_canais` | canais PLUTO TV do addon |
| Linha 2 — Filmes · Brazuca Play | 686 (lista 712) | `list` 9201 → `mode=27&url=#filmes_menu` | busca, gêneros, lançamentos, A-Z, trilogia |
| Linha 3 — Séries · Brazuca Play | 872 (lista 898) | `list` 9202 → `mode=27&url=#series_menu` | busca de séries, todas as séries |
| Navegação por categorias | rodapé | `grouplist` 9000 → 9010–9022 | TV ao vivo, Filmes, Séries, Novelas, Animes, Doramas, Desenhos, Favoritos, Add-ons, **Brazuca Play**, YouTube |

Variantes de layout já existentes no arquivo (mantidas): 
- 9200/9201/9202 + 9300–9303 (layout principal, 3 linhas Brazuca);
- 9230/9240/9210/9220 + 9010/9061–9073, 9020/9091–9099, 9100/9101–9113 (layouts
  anteriores de 7 categorias + 4 linhas) — continuam no XML e continuam válidos;
- cada bloco tem `grouplist` de navegação próprio (9010, 9340, 9350, 9320, 9110).

**Estados previstos por linha**
- *carregando*: spinner do Kodi sobre a lista (o `content` é resolvido pelo addon);
- *vazio*: o addon devolve lista vazia → linha mostra "Nenhum item" (nunca texto fixo);
- *erro*: `RunPlugin` falhou → o item simplesmente não aparece (sem travar a Home).

## 3. Ajustes (`xml/Settings.xml` + `xml/SettingsCategory.xml`)

- `panel` 9000 = `File Manager` (atalho nativo), 9050 = **Voltar** (`Action(Back)`),
  9051 = **Buscar** (`ActivateWindow(1107)`);
- a lista de categorias é renderizada por `SettingsCategory.xml` (template do Kodi):
  `grouplist` 5 e 3, `button` 7/10, `radiobutton` 8/20, `spincontrolex` 9,
  `sliderex` 13, `colorbutton` 15, `image` 11 (ícone), `label` 2/14, `textbox` 6,
  `scrollbar` 60;
- **todo item tem ícone**: `media/icons/settings/*.png`, gerados por 
  `tools/kodi/make-settings-icons.py` (script Python puro, sem dependências);
- **nada cortado**: largura do painel reserva 72 px para ícone + 8 px de respiro,
  labels com `textwidth` limitado e `wrapmultiline` apenas onde o Kodi suporta;
- **desbloqueio discreto**: 5 aberturas consecutivas de Ajustes → 
  `Skin.SetBool(secret_unlocked)` (`Includes_SecretUnlock.xml`, `onload`).

## 4. Energia (`ShutdownMenu`)

Botão 9123 → `ActivateWindow(ShutdownMenu)` (nativo, mesmo comportamento do
Kodi 21: desligar, reiniciar, suspender, sair). Não há diálogo próprio, então
nada quebra se o sistema bloquear o desligamento.

## 5. Navegação de vídeo (`xml/MyVideoNav.xml`)

- `list` 50 (principal) e `list` 51 (variante), views 50/51/52;
- grouplist 9000 → 9010–9016 (Ajustes do Kodi, ordenar, ver, layout…);
- 9050 → 9051/9052/9053 (ações de contexto: reproduzir, informação, favorito);
- recebe **qualquer** rota do addon: categorias → pastas → subpastas → temporadas
  → episódios → player, além de busca e paginação (`mode` do addon);
- o botão **Voltar** do controle remoto funciona em toda a árvore porque cada
  nível é uma janela `10025` empilhada pelo Kodi (mecanismo nativo).

## 6. Favoritos / Add-ons

- `10060` lê `userdata/favourites.xml`, que o bootstrap mantém com 10 atalhos
  (7 do backup + TV ao vivo, Filmes, Séries);
- `10040` é o navegador nativo de add-ons; a partir dele o usuário chega ao
  Brazuca Play sem atalho nenhum na Home (garantia de "nada escondido").

## 7. Matriz de acessibilidade (controle remoto Android TV)

| Ação | Home | Ajustes | VideoNav |
|------|------|---------|----------|
| D-pad ↑↓←→ | entre barra, hero, linhas e navegação | lista de categorias ↔ painel | lista e barra de ações |
| OK | abre rota do addon | aplica o setting | abre pasta / reproduz |
| Back | retorna/Ajustes | volta ao grupo anterior | sobe um nível |
| Info | `Informações` (9303) | — | `Action(info)` |
| Home | nativo | nativo | nativo |
