# SMARTED-TV 1.0.48 — skin Bingie (renomeada SMARTEDTV)

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.48-smarted-arm64/SMARTED-TV-v1.0.48-arm64.apk
**Tamanho:** 368.745.340 bytes · **versionName:** 1.0.48 · **versionCode:** 2103034 · pacote `org.xbmc.kodi` (ARM64)
**Build:** GitHub Actions run `43175381989` — todos os passos verdes, assinado com a mesma chave da linha 1.0.15+.

## O que mudou

- É **atualização da linha principal** (mesmo APK, mesma assinatura, mesma instalação por cima da 1.0.47). Não é app paralelo.
- A skin **BINGIE MOD 2.2.3** (mod Titan Bingie do AchillesPunks, feita para Kodi 21 / Omega) vai **embutida no APK** e **já é a skin padrão**, com o nome **SMARTEDTV** (`skin.novatv`).
- Todas as dependências dela vão dentro do APK: `script.bingie.helper`, `script.skinshortcuts`, `script.skin.helper.service`, `script.skin.helper.widgets`, `script.skin.helper.backgrounds`, `plugin.video.themoviedb.helper`, `script.module.*` e `resource.images.*`. **Nada precisa ser baixado no aparelho** — era aí que a instalação pelo repositório travava.
- A skin antiga continua instalada como **SMARTEDTV Classica**: Ajustes > Aparência > Skin > *SMARTEDTV Classica* volta para a interface da 1.0.47 na hora.
- Motor de carregamento (pontes, plugin `plugin.video.smarted` 0.3.3), categorias, filtros e ajustes: **iguais aos da 1.0.47**.

## Instalação

1. Baixe o APK no link acima (368 MB — o download demora).
2. Instale por cima da versão atual (mesma chave, atualiza sem desinstalar).
3. Abra: o app entra direto na skin SMARTEDTV (Bingie).

## A skin é funcional hoje?

Sim, estruturalmente: a 2.2.3 é a build atual do mod para Kodi Omega (o Kodi do app é 21.x, `xbmc.gui 5.17.0`, exatamente o que o `addon.xml` dela exige) e todas as dependências obrigatórias estão embarcadas. O repositório do autor continua ativo (últimos commits em dez/2025), mas:

- três dependências **opcionais** que ele lista não existem no repositório dele — `plugin.video.youtube`, `plugin.program.autocompletion` e `resource.images.studios.coloured`. Foram liberadas do `addon.xml`; sem elas a skin carrega normalmente, só widgets/logos que dependem delas ficam vazios;
- a skin é "crua": a Home do Bingie é montada por widgets e atalhos, então no primeiro boot ela pode aparecer com pouca coisa até você apontar os widgets (TMDb Helper) ou criar os menus. Isso é comportamento da skin, não defeito do APK;
- se ela travar ou ficar estranha no aparelho, troque para *SMARTEDTV Classica* em Ajustes > Aparência > Skin (ou reinstale a 1.0.47).

## Se quiser a skin sem embutir (manual, no Kodi)

O que provavelmente falhou antes: o zip do repositório do autor tem ~100 MB e a skin depende de addons que não estão lá; se um deles faltar, o Kodi recusa a instalação. Instalando manualmente, instale nesta ordem: os `script.module.*` e `resource.images.*`, depois `script.skinshortcuts`, `script.skin.helper.*`, `script.bingie.helper`, `plugin.video.themoviedb.helper` e por último `skin.titan.bingie.mod`. No APK esse problema não existe.
