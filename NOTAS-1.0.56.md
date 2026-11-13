# SMARTEDTV 1.0.56 — Vikings Repo no build, marca SMARTEDTV no Android e VOD na Home

**APK direto:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.56-smarted-arm64/SMARTEDTV-v1.0.56-arm64.apk

- **Tamanho:** 377 281 837 bytes · **SHA-256:** `01a3d826206b6903a66abf4995eb2915cc9842b37f4c22fb194901fd757d6867`
- **versionName** 1.0.56 · **versionCode** 2103042 · pacote `org.xbmc.kodi` · **arm64-v8a**
- **Run do build:** `43446656673` — 13/13 passos verdes, sem reexecução
- **Assinatura:** `smarted-tv-test` (certificado SHA-256 `855de171…951a`), conferida no run
  antes de publicar; atualiza por cima da 1.0.55, não atualiza o Kodi oficial

## 1. Marca SMARTEDTV no rótulo do Android (novo)

O rótulo que o Android mostra não está no `AndroidManifest.xml`: é uma string do
*string pool* global de `resources.arsc`. Trocar o texto muda o tamanho do
arquivo inteiro (os deslocamentos são relativos), então o build **remonta o
pool**:

`tools/kodi/patch-resources-label.py`
- decodifica todas as strings (UTF-8 ou UTF-16, os dois formatos do AAPT2);
- troca `SMARTED-TV` por `SMARTEDTV` preservando ordem, flags e estilos;
- atualiza o tamanho do chunk do pool e do cabeçalho da tabela;
- confere o resultado com o próprio leitor antes de devolver;
- **aborta o build** se o pool não estiver no formato esperado (nunca publica
  tabela de recursos inconsistente).

No APK final o passo 10 lê o arquivo com `pyaxmlparser` e exige
`get_app_name() == 'SMARTEDTV'`. Passou.

Todo o resto da marca também foi unificado: nomes de add-on, títulos de diálogo,
notificações e prefixos de log do projeto dizem SMARTEDTV (antes alternavam com
`SMARTED-TV`). O **pacote** continua `org.xbmc.kodi` de propósito — o motor
compilado e o dex do launcher dependem dele — e `libkodi.so`/`classes.dex` são
comparados byte a byte com a base em todo build.

## 2. Vikings Repo registrado nativamente (novo)

O endereço divulgado (`https://vkodi.net/repo`) **está fora do ar**: sonda
executada na CI (`probe-vikings.yml`, resultado em `.github/vikings-probe.txt`)
recebeu timeout em todas as URLs, e há relatos de usuários desde dez/2025.

O build usa o **repositório oficial do time Vikings no GitHub**:
`vikingsbuild/vikings.repo` → add-on de repositório **`vkkodi.repo` 3.00**, que
aponta para a árvore `matrix` (Kodi ≥ 18.9.1) — a mesma que publica
`plugin.video.BrazucaPlay.Matrix` 2.1.4.

`tools/kodi/fetch-vikings-repo.py`:
- baixa o zip e valida (um `addon.xml` na raiz, `id` igual ao da pasta,
  `extension point="xbmc.addon.repository"` presente);
- extrai para a pasta de add-ons extras do build;
- guarda o zip em `_payload/` para o bootstrap;
- baixa também o zip do add-on de vídeo publicado pelo repositório.

O build injeta a pasta em `assets/addons/vkkodi.repo/` e registra
`<addon optional="true">vkkodi.repo</addon>` em `assets/system/addon-manifest.xml`
— ou seja, o Kodi instala e ativa o repositório no primeiro boot, sem toque do
usuário. Os dois zips (repositório e add-on de vídeo) vão no
`service.smarted.bootstrap/payload/`:
- `repository.py` refaz o registro **sem rede** se o perfil perder o add-on e,
  se `plugin.video.BrazucaPlay.Matrix` faltar, roda `UpdateAddonRepos()` +
  `InstallAddon(plugin.video.BrazucaPlay.Matrix)`;
- `repair.py` copia `plugin.video.BrazucaPlay.Matrix-2.1.4.zip` para
  `addons/packages/` e o reparo do perfil instala a partir dele.

No log do primeiro boot aparece uma linha só:

```
vikings: repos=vkkodi.repo plugin=ok falhas=nenhuma
```

## 3. Skin, menu e widgets

- Skin padrão: **Bingie Mod 2.2.3**, agora também **preto/branco/cinza**
  (`recolor-skin.py --skin bingie` aplicado no run, antes de injetar).
- Menu superior/lateral = `skinshortcuts-mainmenu` da própria skin, com os oito
  botões (Home, TV, Filmes, Séries, Doramas, Novelas, Animes, Desenhos) e
  Busca/Ajustes/Sair.
- Destinos: TV = `mode=21&url=#todoscanais`; Filmes/Séries/Novelas/Animes/
  Doramas/Desenhos = `mode=1` com a base do add-on em `base16(base64)` — o mesmo
  caminho do `addDir()`, sem menu intermediário e sem tela preta.
- Home: HERO + carrosséis dessas listas + linha de favoritos por categoria.
- `script.skin.helper.widgets`, `themoviedb.helper` e playlists inexistentes não
  são mais chamados (eram a origem do `GetDirectory – Error`).

## 4. Verificações que o build faz no APK final

Motor e dex byte a byte · assinatura e certificado esperados · rótulo SMARTEDTV ·
versionCode 2103042 · skin padrão completa (Bingie + `Home.xml` +
`script-skinshortcuts-includes.xml` idênticos ao repositório) · ordem exata dos
oito rótulos · ausência dos menus intermediários (`#filmes_menu`, `#menu_canais`
etc.) · `vkkodi.repo` no manifesto com `xbmc.addon.repository` · zips no payload
do bootstrap · `plugin.video.BrazucaPlay.Matrix` presente · módulos Python
(`arrow`, `unidecode`, `simplejson`, `requests`, `simpleeval`, `dateutil`) ·
integridade do perfil semeado (`profile-manifest.txt` e linha da skin).

Testes unitários: **252** (inclui os 18 novos do Vikings Repo e 7 do
`resources.arsc`); teste estático: 211 XML válidos, 55 scripts compilados.

## 5. O que só o aparelho pode confirmar

O clique real em cada botão e a contagem de itens por categoria. O primeiro boot
grava `userdata/addon_data/service.smarted.bootstrap/smarted-nav-check.log` com
`PASS <aba> N itens` / `FALHA <aba>: motivo`, e `userdata/smarted-bootstrap.log`
com o resultado do reparo e a linha `vikings:`.
