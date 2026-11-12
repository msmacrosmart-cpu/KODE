# VIDEOOSD_MAP.md — Mapeamento das Opções do VideoOSD

> Baseado em `kodi/skin.estilo.personalizado/xml/VideoOSD.xml`
> Referência: `ENTREGA_FINAL/PREVIEW_KODI.html` (tela Player, 8)
> Commit: `90271a0`

---

## Visão Geral

O VideoOSD.xml agora contém **todas as opções do app** acessíveis durante a reprodução. Cada opção está mapeada para o comportamento equivalente no HTML de referência.

---

## Grupo 201 (Esquerda) — Controles de Reprodução

| ID | Botão | HTML Equivalente | Comportamento | Mapeamento HTML |
|---|---|---|---|---|
| 600 | Previous | Anterior | `PlayerControl(Previous)` | "Anterior" |
| 601 | Rewind | Voltar 10s | `PlayerControl(Rewind)` | "Voltar 10s" |
| 602 | Play/Pause | Pausar | `PlayerControl(Play)` | "Pausar" |
| 603 | Stop | — | `PlayerControl(Stop)` | — |
| 606 | Forward | Avançar 30s | `PlayerControl(Forward)` | "Avançar 30s" |
| 607 | Next | Próximo | `PlayerControl(Next)` | "Próximo" |
| 608 | Record | — | `PVR.ToggleRecordPlayingChannel` | — (condicional PVR) |

---

## Grupo 202 (Direita) — Opções do App

| ID | Botão | HTML Equivalente | Comportamento | Mapeamento HTML |
|---|---|---|---|---|
| 804 | Home | — | `PlayerControl(ShowVideoMenu)` | — |
| 70040 | Channels | — | `ActivateWindow(PVROSDChannels)` | — (condicional PVR) |
| 70041 | Guide | — | `ActivateWindow(pvrchannelguide)` | — (condicional PVR) |
| 70042 | Playlist | — | `ActivateWindow(videoplaylist)` | — |
| 70043 | Info | Info | `Info` | "Info" |
| **70049** | **Áudio** | **Áudio** | `ActivateWindow(osdaudiosettings)` | "Áudio" |
| 70044 | Bookmarks | Marcadores | `ActivateWindow(videobookmarks)` | "Marcadores" |
| 70045 | Teletext | — | `ActivateWindow(Teletext)` | — (condicional) |
| 70046 | Subtitles | Legendas | `ActivateWindow(osdsubtitlesettings)` | "Legendas" |
| 70047 | Stereoscopic | — | `ActivateWindow(1101)` | — (condicional) |
| 70048 | Settings | — | `ActivateWindow(1101)` | — |

---

## Grupo 6000 — Barra de Progresso

| ID | Elemento | Comportamento |
|---|---|---|
| 87 | Botão de busca (invisível) | `StepBack`/`StepForward` |
| Slider | Barra de progresso | `seek` |
| Slider | Barra de progresso (foco) | `seek` |
| Slider | Barra timeshift (LiveTV) | `pvr.seek` |
| Slider | Barra timeshift (foco) | `pvr.seek` |

---

## Mapeamento Completo HTML → VideoOSD

| HTML (tela Player) | VideoOSD | Status |
|---|---|---|
| Anterior | 600 (Previous) | ✅ |
| Voltar 10s | 601 (Rewind) | ✅ |
| Pausar | 602 (Play/Pause) | ✅ |
| Avançar 30s | 606 (Forward) | ✅ |
| Próximo | 607 (Next) | ✅ |
| Áudio | 70049 (Áudio) | ✅ NEW |
| Legendas | 70046 (Subtitles) | ✅ |
| Info | 70043 (Info) | ✅ |
| Marcadores | 70044 (Bookmarks) | ✅ |
| Barra de progresso | Slider 6000 | ✅ |
| Marcador no tempo | 87 (StepBack/Forward) | ✅ |

---

## Brazuka Play no VideoOSD

Durante a reprodução de conteúdo do Brazuka Play, as seguintes opções estão disponíveis:

| Conteúdo | Opções Disponíveis |
|---|---|
| **TV ao vivo** | Canais (70040), Guia (70041), Record (608), Timeshift (Slider) |
| **Filmes** | Info (70043), Áudio (70049), Legendas (70046), Marcadores (70044) |
| **Séries** | Info (70043), Áudio (70049), Legendas (70046), Marcadores (70044) |
| **Novelas** | Info (70043), Áudio (70049), Legendas (70046), Marcadores (70044) |
| **Animes** | Info (70043), Áudio (70049), Legendas (70046), Marcadores (70044) |
| **Doramas** | Info (70043), Áudio (70049), Legendas (70046), Marcadores (70044) |
| **Desenhos** | Info (70043), Áudio (70049), Legendas (70046), Marcadores (70044) |

---

## Ícones Utilizados

| Ícone | Status |
|---|---|
| `osd/fullscreen/buttons/settings.png` | ✅ Existe (usado para Áudio) |
| `osd/fullscreen/buttons/information.png` | ✅ Existe |
| `osd/fullscreen/buttons/bookmarks.png` | ✅ Existe |
| `osd/fullscreen/buttons/settings-subtitle.png` | ✅ Existe |
| `osd/fullscreen/buttons/channels.png` | ✅ Existe |
| `osd/fullscreen/buttons/guide.png` | ✅ Existe |
| `osd/fullscreen/buttons/home.png` | ✅ Existe |
| `osd/fullscreen/buttons/playlist.png` | ✅ Existe |
| `osd/fullscreen/buttons/teletext.png` | ✅ Existe |
| `osd/fullscreen/buttons/stereoscopic.png` | ✅ Existe |
| `osd/fullscreen/buttons/record.png` | ✅ Existe |
| `osd/fullscreen/buttons/previous.png` | ✅ Existe |
| `osd/fullscreen/buttons/rewind.png` | ✅ Existe |
| `osd/fullscreen/buttons/forward.png` | ✅ Existe |
| `osd/fullscreen/buttons/next.png` | ✅ Existe |
| `osd/fullscreen/buttons/stop.png` | ✅ Existe |
| `osd/fullscreen/buttons/button-fo.png` | ✅ Existe |

---

## Foco

| Controle | Foco Inicial | Comportamento |
|---|---|---|
| 602 (Play/Pause) | `defaultcontrol always="true"` | Foco no play/pause ao abrir |
| 6000 (Barra) | `onup=200`/`ondown=200` | Foco na barra de progresso |
| 201 (Controles esquerda) | `onleft=70048` | Foco no botão de settings |
| 202 (Opções direita) | `onright=600` | Foco no botão de previous |

---

## Regras Preservadas

- ✅ Nunca remover addons funcionais
- ✅ Nunca substituir Brazuka Play
- ✅ Nunca duplicar integrações
- ✅ Nunca inventar conteúdo/stats
- ✅ Todas as opções do app acessíveis durante a reprodução
- ✅ Foco sempre definido
- ✅ Navegação D-pad completa (←→ entre grupos, ↑↓ entre botões)
- ✅ Estados visuais obrigatórios (ícone de foco)
