# Design System Original — Nova TV (Kodi Omega 21)

Fonte: `kodi/skin.novatv/colors/defaults.xml`, `xml/Font.xml`, `xml/Includes.xml`, `xml/Home.xml`, `xml/VideoOSD.xml`, `media/`. Identidade monocromática estrita; nenhuma cor vibrante ou gradiente colorido.

## 1. Paleta

| Token | Valor | Uso |
|---|---|---|
| `bg` | `ff0d0d0d` (#0d0d0d) | Fundo principal |
| `panel` | `ff181818` (#181818) | Painéis, diálogos |
| `panel2` | `ff262626` (#262626) | Botões sem foco, listas de ajustes |
| `white` | `fff2f2f2` (#f2f2f2) | Títulos, foco, selos |
| `text` | `ffd9d9d9` (#d9d9d9) | Texto principal |
| `muted` | `ffa6a6a6` (#a6a6a6) | Metadados, secundário |
| `accent` | `fff2f2f2` (igual a `white`) | Foco (fundo branco) |
| `ontext` | `ff0d0d0d` (igual a `bg`) | Texto sobre foco |
| `dim` | `b3000000` (preto 70%) | Véu de diálogos |

Alfas utilitários: `20ffffff` (linhas), `28ffffff` (fanart), `30ffffff`/`50ffffff`/`80ffffff` (scrollbar/progresso), `b3ffffff` (arte sem foco), `f2141414` (painel lateral).

## 2. Tipografia (Liberation Sans, SIL OFL)

| Nome | Arquivo | Tamanho | Uso |
|---|---|---|---|
| `font_tiny` | Regular | 22 | Selos, rótulos pequenos |
| `font_small` | Regular | 26 | Metadados, títulos de card |
| `font_main` | Regular | 28 | Corpo, botões |
| `font_main_bold` | Bold | 28 | Títulos de fileira |
| `font_large` | Regular | 36 | Títulos de seção |
| `font_large_bold` | Bold | 36 | Títulos de diálogo |
| `font_title` | Bold | 54 | Cabeçalhos de janela |
| `font_hero` | Bold | 84 | Título do hero |

## 3. Espaçamentos e molduras

- Base 1920×1080 (Kodi escala para outras resoluções; não há media queries na skin XML).
- Margens laterais: 60 px. Topo: 28–30 px (menu), 30 px (cabeçalho).
- Hero: 1920×780, conteúdo a partir de x=60, selo 200×34, título y=236, metadados y=350, sinopse y=400 (900×120), botões y≈540.
- Menu 9000: 1205×76 em (175,28); itens 190×76; foco com underline 120×4.
- Fileiras: altura 340 (lista) dentro de grupo 400; cards pôster 230×320 (arte 210×300), paisagem 380×250 (arte 360×205).
- Listas (Views 50): linha 76 px, largura 1760; painéis 51/52: 1760×830 a partir de y=170.
- Diálogos: painel 1500×700 em (210,190); botões 230×64; bordas `rounded.png` com `border="16"`.
- Foco: `texturefocus` branco + `focusedcolor ontext`; cards com anel `ring.png` (-5,-5, +10).

## 4. Componentes

- **Cabeçalho** (`Header`): título da janela + pasta atual + relógio à direita.
- **Hero** (9100): fanart + `scrim_h.png`, selo, título, metadados, sinopse, botões Assistir/Trailer/Detalhes.
- **Menu** (9000): horizontal, texto centralizado; foco = bold branco + underline.
- **Fileiras de widgets** (9200–9280): label + lista horizontal; arte via `ItemArt`/`ItemLand`; progresso `ListItem.PercentPlayed`.
- **Listas/Painéis** (50/51/52): linha, grade de pôsteres, grade paisagem; scrollbar 60 (8 px).
- **ViewOptions** (9000/9001): painel lateral 520 px + botões Visualização/Ordenar por/Ordem/Filtrar.
- **Player OSD** (`VideoOSD`): seek 87, controles 600–611, áudio 710, legendas 70046, vídeo 711, marcadores 70044, processo 712.
- **Ajustes** (`SettingsCategory`/`DialogSettings`): grouplists 3/5, controles 7/8/9/10/13/15, OK/Cancelar/Padrão 28/29/30.
- **Diálogos**: confirmação, seleção, teclado (IDs 100–172 + 300–312), contexto, progresso, notificação, volume, busca.
- **Estados**: sem foco = `panel2` + `text`; com foco = `accent` (branco) + `ontext` (preto). Transições: fade 200 ms (abrir) / 150 ms (fechar), scroll 200–500 ms.

## 5. Preview HTML

`ENTREGA_FINAL/PREVIEW_KODI.html` usa os mesmos tokens (CSS vars `--bg`, `--panel`, `--panel2`, `--white`, `--text`, `--muted`), mesma fonte do sistema, raio 14 px, foco branco/preto e palco 16:9 escalável. É esquemático (dados ilustrativos), sem dependências externas e sem cores fora da paleta — verificado por script (nenhuma URL externa, hex apenas em cinzas).
