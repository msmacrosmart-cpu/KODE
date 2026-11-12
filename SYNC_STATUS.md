# SYNC_STATUS.md — Sincronização das Abas Principais

> Data: 2026-11-11
> Comando: "veja se a sincronização das abas TV, Filmes, Series, Musica e YouTube está com conteudos. Se tiver, pode liberar elas sem o unlock secret."

---

## Estado das Abas

| Aba | Conteúdo | Addon | Status | Liberado sem unlock? |
|---|---|---|---|---|
| **TV ao vivo** | Canais Brazuca Play (live TV) | `plugin.video.BrazucaPlay.Matrix` mode=21 `#menu_canais` | ✅ Sincronizado | ✅ SIM |
| **Filmes** | Filmes Brazuca Play (recently added) | `plugin.video.BrazucaPlay.Matrix` mode=27 `#filmes_menu` | ✅ Sincronizado | ✅ SIM |
| **Séries** | Séries Brazuca Play | `plugin.video.BrazucaPlay.Matrix` mode=27 `#series_menu` | ✅ Sincronizado | ✅ SIM |
| **Música** | Música + MP3 Streams | Kodi Music + `plugin.audio.mp3streams` | ✅ Sincronizado | ✅ SIM |
| **YouTube** | Busca YouTube | `plugin.video.youtube` mode=search | ✅ Sincronizado | ✅ SIM |

---

## Detalhes por Layout

### Aurora (grupo 9000)
| ID | Aba | Comando |
|---|---|---|
| 9010 | TV ao vivo | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais)` |
| 9011 | Filmes | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu)` |
| 9012 | Séries | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23series_menu)` |
| 9013 | Novelas | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=25&url=%23novelas_menu)` |
| 9014 | Animes | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=22&url=%23animes_menu)` |
| 9015 | Doramas | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=31&url=%23doramas_menu)` |
| 9016 | Desenhos | `ActivateWindow(10025, plugin://plugin.video.BrazucaPlay.Matrix/?mode=28&url=%23desenhos_menu)` |
| 9017 | Música | `ActivateWindow(Music,root,return)` |
| 9018 | YouTube | `ActivateWindow(10025, plugin://plugin.video.youtube/?mode=search)` |

### Blade (grupo 9100)
| ID | Aba | Comando |
|---|---|---|
| 9101 | TV ao vivo | BrazucaPlay mode=21 |
| 9102 | Filmes | BrazucaPlay mode=27 `#filmes_menu` |
| 9103 | Séries | BrazucaPlay mode=27 `#series_menu` |
| 9104 | Novelas | BrazucaPlay mode=25 |
| 9105 | Animes | BrazucaPlay mode=22 |
| 9106 | Doramas | BrazucaPlay mode=31 |
| 9107 | Desenhos | BrazucaPlay mode=28 |
| 9108 | Música | `ActivateWindow(Music,root,return)` |
| 9109 | YouTube | `ActivateWindow(10025, plugin://plugin.video.youtube/?mode=search)` |
| 9110 | Busca | `ActivateWindow(1107)` |
| 9111 | Ajustes | `ActivateWindow(Settings)` |
| 9112 | Sair | `ActivateWindow(Home)` |

### Top10 (grupo 9010)
| ID | Aba | Comando |
|---|---|---|
| 9061 | TV ao vivo | BrazucaPlay mode=21 |
| 9062 | Filmes | BrazucaPlay mode=27 `#filmes_menu` |
| 9063 | Séries | BrazucaPlay mode=27 `#series_menu` |
| 9064 | Novelas | BrazucaPlay mode=25 |
| 9065 | Animes | BrazucaPlay mode=22 |
| 9066 | Doramas | BrazucaPlay mode=31 |
| 9067 | Desenhos | BrazucaPlay mode=28 |
| 9068 | Música | `ActivateWindow(Music,root,return)` |
| 9069 | YouTube | `ActivateWindow(10025, plugin://plugin.video.youtube/?mode=search)` |
| 9070 | Busca | `ActivateWindow(1107)` |
| 9071 | Ajustes | `ActivateWindow(Settings)` |
| 9072 | Sair | `ActivateWindow(Home)` |

### Sports (grupo 9020)
| ID | Aba | Comando |
|---|---|---|
| 9091 | TV ao vivo | BrazucaPlay mode=21 |
| 9092 | Filmes | BrazucaPlay mode=27 |
| 9093 | Séries | BrazucaPlay mode=27 |
| 9094 | Desenhos | BrazucaPlay mode=28 |
| 9095 | Busca | `ActivateWindow(1107)` |
| 9096 | Ajustes | `ActivateWindow(Settings)` |
| 9097 | Sair | `ActivateWindow(Home)` |
| 9098 | Música | `ActivateWindow(Music,root,return)` |
| 9099 | YouTube | `ActivateWindow(10025, plugin://plugin.video.youtube/?mode=search)` |

---

## Música — Integração com plugin.audio.mp3streams

O addon `plugin.audio.mp3streams` já vem no app (backup `backup_files/files/.kodi/addons/plugin.audio.mp3streams/`).

No `MyMusicNav.xml`, foi adicionado:
- Botão "MP3 Streams" (id 9053) → `ActivateWindow(10025, plugin://plugin.audio.mp3streams/)`
- Botão "Atualizar biblioteca" (id 619) → `UpdateLibrary(music)`
- Botão "Lista de reprodução" (id 612) → `ActivateWindow(musicplaylist)`

---

## Decisão do Usuário

> "veja se a sincronização das abas TV, Filmes, Series, Musica e YouTube está com conteudos. Se tiver, pode liberar elas sem o unlock secret."

**Todas as 5 abas principais já estão sincronizadas com conteúdo real.**

**Liberadas sem unlock secret.** O unlock secret (8 cliques no logo + 2 ciclos Settings) continua disponível para configurações avançadas, mas não é necessário para acessar as abas principais.

---

## Regras Preservadas

- ✅ Todas as 5 abas usam addons existentes (BrazucaPlay, MP3 Streams, YouTube)
- ✅ Sem conteúdo inventado
- ✅ Sem addons novos criados
- ✅ Sem duplicação de integrações
- ✅ Foco D-pad funciona em todos os layouts
- ✅ Navegação ←→ entre atalhos, ↑↓ entre seções do Hero
