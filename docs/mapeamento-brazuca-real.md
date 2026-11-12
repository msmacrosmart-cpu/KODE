# Mapeamento real do Brazuca Play (2.1.4) → botões da SMARTED

Fonte analisada: código do próprio addon, publicado em
`skyrisk/brazucaplay` → `addons/repo/Plugins/plugin.video.BrazucaPlay.Matrix/plugin.video.BrazucaPlay.Matrix-2.1.4.zip`.
O `default.py` vem ofuscado em duas camadas (`exec(zlib(base64(...)))`); foi decodificado
localmente (sem executar) e o despachante `mode=...` foi lido linha a linha.

## O que estava errado antes

| Botão | Ação antiga | O que o addon fazia |
|-------|-------------|---------------------|
| Filmes | `mode=27&url=#filmes_menu` | abria o **menu de listas** (PESQUISAR / GÊNEROS / LANÇAMENTOS / ORDEM ALFABÉTICA / TRILOGIA) |
| Séries | `mode=27&url=#series_menu` | abria o menu (PESQUISAR SÉRIES / TODAS SÉRIES) |
| Doramas | `mode=31&url=#doramas_menu` | modo 31 é o **resolver** de séries/doramas, não listagem |
| Novelas | `mode=25&url=#novelas_menu` | abria o menu (PESQUISAR / TODAS NOVELAS) |
| Animes | `mode=22&url=#animes_menu` | abria o menu (PESQUISAR / TODOS ANIMES) |
| Desenhos | `mode=28&url=#desenhos_menu` | abria o menu (PESQUISAR / TODOS DESENHOS) |
| TV | `mode=21&url=#menu_canais` | `ch_layout=false` (padrão) → **menu de categorias** de canais |

Ou seja: os botões abriam exatamente a "tela intermediária para escolher listas" que o
usuário rejeitou. Além disso `mode=1` do addon exige a URL codificada em
`base16(base64(url))` — qualquer caminho escrito "à mão" nesse modo falha e o Kodi
mostra a janela genérica de arquivos.

## Destinos finais usados agora (2026-11)

| Botão | Chamada ao plugin | Entrega |
|-------|-------------------|---------|
| TV | `?mode=21&url=#todoscanais` | lista de canais (branch `elif '#todoscanais' in url`, linha 6809) |
| Filmes | `?mode=1&url=base16b64(…/5b87797329c7b46422565ffbaab3be7e/raw/lancamentos.xml)` | lista de filmes lançamentos (5,7 MB no gist) |
| Séries | `?mode=1&url=base16b64(…/16070347f20c87c72540f9f805b57a66/raw/SeriesBase)` | séries (9,1 MB) |
| Doramas | `?mode=1&…/DoramasBase` | doramas (3,5 MB) |
| Novelas | `?mode=1&…/07f1f4cd1b203cbf2efec959c4e8645a/raw/novelas.xml` | novelas (774 KB) |
| Animes | `?mode=1&…/AnimesBase` | animes (3,2 MB) |
| Desenhos | `?mode=1&…/DesenhosBase` | desenhos (1,2 MB) |

Cada uma dessas fontes existe e está publicada (conferido pela API do GitHub: arquivos
`lancamentos.xml`, `SeriesBase`, `DoramasBase`, `AnimesBase`, `DesenhosBase`,
`novelas.xml`, `channels.xml`).

A codificação é a mesma do `addDir()` do addon:

```python
url = quote_plus(base64.b16encode(base64.b64encode(url.encode())).decode())
```

E o despachante faz o caminho inverso (`base64.b64decode(base64.b16decode(url))`), por
isso só funciona com base16 em maiúsculas.

## Widgets da Home

Os widgets apontam para **as mesmas listas finais** do addon (nada de `route=carrossel`
genérico), com a linha de Favoritos por categoria vinda de `plugin.video.smarted`.
TV ao vivo continua fora dos carrosséis.

## Avisos silenciados (não críticos)

`donate_consider()` do Brazuca abre um diálogo de doação sempre que a setting está
vazia/vencida — por cima da Home e no meio do carregamento dos widgets. O bootstrap grava
`donate_consider = 991231` (nada além disso é tocado no addon). Reprodução, navegação e
favoritos do Brazuca seguem intactos.

`parental_password()` só cria `pass.txt` com `0000`; não abre diálogo.
`InstallPlugin()` instala `inputstream.adaptive/ffmpegdirect` se faltarem — não mostra
mensagem ao usuário.

## Como validar no aparelho

Primeiro boot da 1.0.55 grava:

```
userdata/addon_data/service.smarted.bootstrap/smarted-nav-check.log
```

com uma linha por destino (`PASS Filmes 348 itens` / `FALHA Filmes: <motivo>`), usando
`Files.GetDirectory` na mesma URL do clique. Também aparece no `kodi.log` como
`nav-check: ...`.
