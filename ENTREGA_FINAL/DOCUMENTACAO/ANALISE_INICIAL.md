# Análise inicial — skin.novatv (Kodi Omega 21)

Data: 2026-11-11. Fonte: repositório `kodi/skin.novatv` (branch `arena/7024aff2-kode`).
Nenhuma alteração de skin foi feita nesta etapa; apenas leitura e medição.

## 1. Identificação

| Item | Valor |
|---|---|
| Nome | Nova TV (`skin.novatv`) |
| Versão | 1.0.1 (`addon.xml`) |
| Compatibilidade declarada | Kodi Omega 21, `xbmc.gui 5.17.0`, 1920×1080 16:9 |
| Idiomas | `pt_BR`, `en_GB` (42 strings cada, paridade verificada) |
| Licença | GPL-2.0-or-later |
| Ponte de conteúdo | `plugin.video.smarted` 0.2.0 (depende de `plugin.video.BrazucaPlay.Matrix` 2.1.4) |

## 2. Estrutura (138 arquivos, 1.235.406 bytes)

- `addon.xml` — manifesto da skin.
- `xml/` — 93 arquivos XML (91 janelas + `Includes.xml` + `Font.xml`).
- `colors/defaults.xml` — paleta monocromática (9 cores).
- `fonts/` — `Regular.ttf` (410.820 B) + `Bold.ttf` (414.568 B), Liberation Sans (SIL OFL).
- `media/` — 33 PNGs (34.649 B no total). Maioria são placeholders de 899 B (`Default*.png`, `default.png`); utilitários: `white.png`, `rounded.png`, `ring.png`, `scrim_h/v.png`, `nib.png`, `arrow_l/r.png`, `radio_on/off.png`, `circle.png`, `smarted-logo.png` (13.344 B).
- `resources/` — `icon.png` (3.248 B), `fanart.jpg` (37.017 B), `settings.xml` (hero/widgets).
- `language/` — `strings.po` pt_BR + en_GB.
- `hero_details.py` — script de detalhes do hero (lê `Container(9100)`).
- `docs/JANELAS.md` + `README.md` — documentação interna (excluídos do ZIP de entrega).

Maiores arquivos: `Home.xml` (53.342 B), `DialogKeyboard.xml` (33.250 B), `VideoOSD.xml` (15.270 B), `Includes.xml` (10.832 B). O restante das janelas tem 297–8.079 B.

## 3. Janelas e includes

- Includes definidos em `Includes.xml`: `Anim`, `Bg`, `Fanart`, `Header`, `Views` (listas 50/51/52 + scrollbar 60), `ViewOptions` (botões 2/3/4/19) e variáveis `ItemArt`/`ItemLand`. Todas as referências `<include>` resolvem; nenhuma textura estática referenciada está ausente em `media/` (verificado por script).
- `Home.xml` (1.399 linhas): hero 9100 (`recent-movies`), menu 9000, botões 9010/9011/9012, widgets 9200–9280 em grouplist 9500. Layouts dos cards 9200–9230 travados por hash em `tests/test_original_home_design.py` — não alterar sem atualizar o teste.
- Janelas completas (layout próprio): `Home`, `VideoOSD`, `VideoOSDBookmarks`, `DialogKeyboard`, `DialogSelect`, `DialogSettings`/`DialogAddonSettings`, `Settings`, `SettingsCategory`, `DialogVideoInfo`, `DialogAddonInfo`, `DialogMusicInfo`, `MyWeather`, `FileManager`, `FileBrowser`, `ShutdownMenu`, `MyPVRGuide`, `SettingsSystemInfo`, `SkinSettings`, etc.
- Janelas funcionais genéricas (297 B, só `Bg`/`Fanart`/`Header`/`Views`/`ViewOptions`): `MyVideoNav`, `MyMusicNav`, `MyMusicSongs`, `MyPics`, `MyPrograms`, `AddonBrowser`, `MyGames`, `MyPVRChannels/Recordings/Timers/Search`, playlists, `EventLog`. Elas abrem e exibem lista/grade/miniatura via `Views`; não são quebradas, mas não têm layout específico (série/temporada, álbum, artista).
- Janelas de ajustes (5.721–8.079 B) compartilham o modelo de controles Kodi 21 (IDs 2,3,5,6,7,8,9,10,11,12,13,14,15 + 28/29/30 nos diálogos), verificado por `test_settings_controls_match_kodi_21`. Botões sem `<onclick>` nesses diálogos (OK/Cancelar/Padrão, Sim/Não, teclas) são tratados pelo código nativo do Kodi por ID — não é defeito.

## 4. Ponte SMARTED-TV (TV / Filmes / Séries)

`kodi/addons/plugin.video.smarted/` (22 arquivos, 7 módulos Python):

- `routes.py` — rotas reais do Brazuca 2.1.4, sem dados embutidos:
  - `root` → TV ao vivo, Filmes, Séries, Doramas, Animes, Novelas, Desenhos.
  - `tv` → Opções de TV (`#menu_canais`, modo 21) + Buscar canais.
  - `series` → Buscar em todas as categorias + Séries, Novelas, Animes, Doramas, Desenhos.
  - `movies` → visão geral do menu de filmes (Buscar, Lançamentos, Gêneros, A–Z + menu original).
- `default.py` — diretórios `recent-movies`, `recent-series`, `channel-favorites`, `search-series`, `search-channels`, `movies`.
- `catalogue.py`, `search.py`, `channel_search.py`, `favorites.py`, `daily_cache.py` — leitura de diretórios reais, busca nas 5 fontes públicas, cache diário de widgets. Nenhum catálogo ou stream é fabricado.

Menu da Home (`Home.xml` 9000, modo básico): **Categorias** (`route=root`), **TV ao vivo** (`route=tv`), **Filmes** (`route=movies`), **Séries** (`route=series`), **Ajustes**. Itens completos (biblioteca, PVR, música, jogos, complementos, imagens, favoritos, clima, arquivos, programas) aparecem com `SmartedFullMode` (desbloqueio por 8 toques no logo + navegação em Ajustes). Widgets: 9200 lançamentos, 9210 séries recentes, 9220 em andamento, 9230 canais favoritos, 9240 gravações, 9250 rádio, 9260 álbuns, 9270 vídeos musicais, 9280 favoritos — cada grupo com visibilidade própria (`HasAddon`, `Library.HasContent`, `Pvr.Has*`).

## 5. Dependências e riscos

- Obrigatórias para o modo básico: `plugin.video.BrazucaPlay.Matrix` 2.1.4 + `plugin.video.smarted`. Sem elas, os 4 primeiros itens do menu ficam ocultos e os widgets de conteúdo somem (comportamento intencional).
- Condicionais: PVR (guia, canais, rádio, gravações, timers), biblioteca (filmes/séries/música), serviço de clima, `script.globalsearch`, suporte a jogos.
- Riscos conhecidos: IDs de controle das janelas `sync` em `JANELAS.md` devem ser conferidos no Estuary do Kodi 21 instalado; janelas genéricas não têm layout específico de série/álbum/artista; widgets vazios (fonte indisponível) mostram título + área em branco (visibilidade por `IsEmpty` é melhoria futura, exige validação em Kodi real).
- **Não testado em Kodi real** nesta etapa (sem ambiente Kodi). Testes executados são estáticos (ver `RELATORIO_VALIDACAO_VISUAL.md`).

## 6. Arquivos do Dropbox

Raiz do Dropbox (imagem de 2026-11-10 21:34): `SKIN_KODI_OMEGA21.zip` (512.732 B), `PREVIEW_KODI.html` (15.695 B, 11 telas), `COBERTURA_TELAS_KODI.md`, `AUDITORIA_PROJETO.md`, `CHANGELOG.md`. Pasta `SKIN ATUALIZACAO` vazia. Esta entrega substitui o preview de 11 telas por um preview de 44 telas e consolida a documentação no repositório (ver `PLANO_DE_IMPLEMENTACAO.md`).
