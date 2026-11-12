# SMARTED-TV 1.0.51 — Home só VOD do Brazuca + build rápido

**APK direto:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.51-smarted-arm64/SMARTED-TV-v1.0.51-arm64.apk

**Tamanho:** 375.954.146 bytes · **versionName** 1.0.51 · **versionCode** 2103037 · `org.xbmc.kodi` ARM64
**Build:** run `43182263510` — 12 passos verdes; **passo 3 = Teste estatico rapido (0,2 s)**.

## 1. Teste estático no lugar do emulador

`tools/kodi/static-check.py` (novo, roda como **passo 3** do workflow, antes de baixar/apagar qualquer coisa):

- valida **todo XML** de `kodi/` e `tools/` com `xml.etree.ElementTree`;
- compila **todo `.py`** com `py_compile`;
- imprime `Teste estatico: 211 XML validos, 47 scripts compilados em 0.1 s`;
- erro sai como `::error::` no check-run (sem precisar abrir log).

O pipeline de release não usa emulador/KVM — é `ubuntu-22.04` + Python. Os workflows de emulador
que existiam (`test-*-emulator.yml`) continuam só como diagnóstico manual, fora do release.

> Na primeira execução ele já pegou um bug real: a troca de widgets tinha gerado XML inválido.

## 2. Home só com VOD do Brazuca Play

Barra superior (9 itens, sem Add-ons):

| aba | ação nativa | carrossel/HERO |
|---|---|---|
| Filmes | `mode=27&url=#filmes_menu` | `route=recent-movies` (Lançamentos) + `route=carrossel&alvo=filmes` |
| Séries | `mode=27&url=#series_menu` | `route=carrossel&alvo=series` + `route=recent-series` |
| Novelas | `mode=25&url=#novelas_menu` | `route=carrossel&alvo=novelas` |
| Animes | `mode=22&url=#animes_menu` | `route=carrossel&alvo=animes` |
| Doramas | `mode=31&url=#doramas_menu` | `route=carrossel&alvo=doramas` |
| Desenhos | `mode=28&url=#desenhos_menu` | `route=carrossel&alvo=desenhos` |
| Busca / Ajustes / Sair | `1109` / `Settings` / `ShutdownMenu` | — |

**TV ao vivo saiu** da barra e de todos os widgets (zero `menu_canais`, zero canais na Home).

As rotas `route=carrossel&alvo=…` são do `plugin.video.smarted`: elas descem a árvore do
Brazuca até o nível que **reproduz** (filme/canal) ou entrega capa de série, com fallback para
os favoritos da categoria — a linha nunca fica vazia nem mostra pasta de menu.

## 3. Erros de log: widgets legados neutralizados

O overlay agora troca, em **todo** o menu (não só na barra), os caminhos que o Kodi acusava:

```
plugin://script.skin.helper.widgets/?action=…   -> plugin://plugin.video.smarted/?route=carrossel&alvo=…
plugin://plugin.video.themoviedb.helper…        -> idem
special://skin/playlists/4kultrahdmovies.xsp    -> idem (arquivo não existe na skin)
```

Resultado no APK de 1.0.51: **0** chamadas a esses três caminhos (eram 60+ ocorrências).
Os addons legados continuam instalados (a skin usa as janelas de ficha deles), mas não são
mais chamados pela Home — é isso que zerava o `GetDirectory – Error` no log.

## 4. Polimento

- Som: `resource.uisounds.silencio` como padrão (nenhum clique na navegação).
- Menu: só texto — `<icon></icon>` em todas as entradas, nenhuma moldura.
- Barra: sem Add-ons; Busca/Ajustes/Sair fixos à direita.
- Rolagem: menu estático (sem `skinshortcuts buildxml` a cada Home), então a Home não
  reconstrói nada ao rolar; listas com `scrolltime` herdado do Bingie.
- Bootstrap 1.0.6: marcador `menu-smarted-v2` força **um** `ReloadSkin()` na atualização.

## 5. Addons: o que já vai embutido

`plugin.video.BrazucaPlay.Matrix` (payload do perfil), `plugin.video.smarted` 0.3.3,
`service.smarted.bootstrap` 1.0.6, `resource.uisounds.silencio`, skin Bingie 2.2.3 como
`skin.novatv` (= SMARTEDTV), `skin.smartedtv.classic` (volta pela Ajustes > Aparência > Skin)
e os módulos: arrow, dateutil, unidecode, simpleeval, requests+urllib3/idna/certifi/charset-normalizer,
beautifulsoup4+soupsieve, musicbrainzngs, simplejson, Pillow.

## 6. Se ainda aparecer erro

Me mande o `kodi.log`. Os candidatos que sobraram são só os do **próprio addon Brazuca**
(`GetDirectory` quando o servidor dele cai) — nada da skin.
