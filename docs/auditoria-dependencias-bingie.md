# Auditoria da skin Titan BINGIE MOD 2.2.3 (Omega) no SMARTED-TV

Base: `skin.titan.bingie.mod` 2.2.3, pasta `omega/` do repositório
`AchillesPunks/repository.titan.bingie.mod` (Kodi 21 / `xbmc.gui 5.17.0`).
Nada da skin foi reescrito: o APK leva a skin inteira (580 arquivos, 113 MB) e o
overlay substitui **3 arquivos** (`xml/Home.xml` — uma linha —,
`xml/script-skinshortcuts-includes.xml` — menu superior — e `resources/icon.png`).

## 1. Dependências declaradas no `addon.xml` da skin

| dependência | versão declarada | está no APK | situação |
|---|---|---|---|
| `xbmc.gui` | 5.17.0 | sim (Kodi 21.3) | ok |
| `script.bingie.helper` | 1.1.2 | sim | ok — precisa de `simplejson` (embarcado) |
| `script.skinshortcuts` | 2.1.0 | sim | ok — precisa de `unidecode` + `simpleeval` (embarcados) |
| `script.skin.helper.service` | 1.30.0 | sim | ok — precisa de `arrow` (embarcado) |
| `script.skin.helper.widgets` | 1.30.0 | sim | instalado, **não chamado pela Home** |
| `script.skin.helper.backgrounds` | 1.0.36 | sim | ok — precisa de `arrow` |
| `plugin.video.themoviedb.helper` | 5.4.16 | sim | instalado, **não chamado pela Home** |
| `resource.images.skinbackgrounds.titanium` | 1.0.0 | sim | ok |
| `resource.images.skinicons.wide` | 1.0.5 | sim | ok |
| `resource.images.backgroundoverlays.basic` | 1.0.0 | sim | ok |
| `plugin.video.youtube` | 7.0.2.2 | **não** | import removido: não existe no repo do autor; a skin carrega sem ele (só widgets de YouTube ficam vazios) |
| `plugin.program.autocompletion` | 2.1.2 | **não** | idem |
| `resource.images.studios.coloured` | 0.0.23 | **não** | idem (logos de estúdio) |

## 2. Erros reais que estavam no log e como foram tratados

| erro no `kodi.log` | causa | tratamento |
|---|---|---|
| `ModuleNotFoundError: unidecode` / `simpleeval` | `script.skinshortcuts` sem as libs | empacotadas como `script.module.*` |
| `ModuleNotFoundError: arrow` | `script.skin.helper.service` e `backgrounds` | empacotado (+ `dateutil`) |
| `ModuleNotFoundError: simplejson` | `script.bingie.helper` | empacotado |
| `ModuleNotFoundError: urllib3` | `requests` presente sem dependências | `requests` + `urllib3`, `idna`, `certifi`, `charset-normalizer` |
| `GetDirectory – Error getting plugin://script.skin.helper.widgets/...` | widgets do menu apontando para addon que precisa de biblioteca de vídeo | caminho trocado por rota do `plugin.video.smarted` |
| `Error loading Smart playlist special://skin/playlists/4kultrahdmovies.xsp` | playlist que a skin não entrega | caminho trocado por rota real |
| `Timers.xml` ausente (warning) | a skin não tem o arquivo | inofensivo, ignorado |

Varredura automática de imports (`tools/kodi/vendor-python-modules.py --check`)
roda no build e falha se algum import de terceiro não tiver módulo embarcado.

## 3. O que é chamado pela Home

Somente rotas do `plugin.video.smarted`, que abrem diretórios reais do
`plugin.video.BrazucaPlay.Matrix`:

```
route=recent-movies          -> Lançamentos (HERO, até 8 destaques)
route=recent-series          -> Séries com novidades
route=carrossel&alvo=<cat>   -> Filmes, Séries, Novelas, Animes, Doramas, Desenhos
route=favoritos-<cat>        -> Favoritos do addon por categoria
```

TV ao vivo: aba própria (`mode=21 #menu_canais`), sem carrossel de canais na Home,
sem misturar canal com filme/série.

## 4. O que ficou de fora (e por quê)

- **Wizard**: o repositório do autor não traz wizard; o payload do app
  (`service.smarted.bootstrap`) é quem prepara o perfil. Nenhuma chamada quebrada.
- **YouTube/autocompletion/studios.coloured**: não existem no repositório oficial
  do autor; removidos do `addon.xml` em vez de deixar a skin exigindo addon
  inexistente (era isso que impedia a instalação pelo repositório no aparelho).
- **Splash screen**: é do launcher do APK (dex), não da skin — trocar exigiria mexer
  no dex; a skin entra depois do splash.

## 5. Pendências conhecidas

- Logo/arte de marca dentro da Home (o Bingie desenha “BINGIE” em imagens próprias):
  só o ícone da skin foi trocado. Substituir as imagens de marca exige redesenho
  dos assets do Bingie — próximo passo de design.
- `Pillow` embarcado (20 MB) por causa do TMDb Helper; dá para cortar se as funções
  de imagem não forem usadas.
