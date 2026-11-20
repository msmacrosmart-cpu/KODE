# Erros de addons na abertura: causa raiz provada e o que foi testado

APK de referência: **1.0.147** (`v1.0.147-universal`).
Ambiente de teste: emulador de projetor Android TV (leanback, `ro.build.characteristics=tv`),
API 30, x86_64 com tradução ARM — o mesmo job `Diagnostico no emulador de projetor`.

## O que aparece hoje no laudo do projetor

```
addons no perfil: 27
addons com erro: 0
falhas de Home/skin: 0
erros do servico do app: 5
  ! ModuleNotFoundError: No module named 'youtube_plugin.kodion.items.base_item'
  ! ModuleNotFoundError: No module named 'youtube_plugin.kodion.exceptions'
  ! OpenWizard: [First Run] Skipping Save Data Settings
  ! service.xbmc.versioncheck: Command '('uname','-rs')' died with SIGSEGV
```

E, no mesmo boot, a limpeza do app:

```
[service.smarted.bootstrap] perfil limpo (rodada 1): 11 retirado(s), 1 sem codigo, restantes=nenhum
[service.smarted.bootstrap] limpeza de terceiros: 11 addon(s) do perfil antigo
    (One.repo, plugin.audio.mp3streams, plugin.program.openwizard, plugin.video.youtube,
     repository.elementumorg, repository.redwizard, repository.resolveurl,
     repository.streamxtv.matrix, service.subtitles.legendei, ...)
```

## Causa raiz (ordem dos eventos, medida no log)

1. O perfil que o APK instala no primeiro arranque traz os addons de terceiros
   (`plugin.video.youtube`, `plugin.program.openwizard`, `plugin.audio.mp3streams`,
   `service.subtitles.legendei` e cinco repositórios) — herança da base do Brazuca Play.
2. O Kodi inicia os addons de **serviço** de tudo que está instalado durante
   `CServiceManager::InitStageTwo`, **antes** de qualquer Python do app rodar
   (23:56:54 o OpenWizard/YouTube, 23:57:05 a limpeza do app).
3. Quando a limpeza do `service.py` roda, o erro já foi mostrado na tela. Por isso
   a limpeza funcionando (11 → 0 restantes) **não** elimina o aviso do primeiro boot.

Conclusão: a correção tem de ser no **perfil embarcado** (tirar os addons de
terceiros do APK), não no aparelho.

## O que foi tentado para corrigir de verdade (e por que parou)

| Tentativa | Resultado medido |
|---|---|
| Limpar os addons no aparelho (`service.py`, 1.0.139/1.0.140) | remove os 11, `restantes=nenhum`, mas o erro do boot já ocorreu antes |
| Limpeza repetida em rodadas + vigia contínuo (1.0.147) | mantém o perfil limpo depois; não evita o primeiro boot |
| Tirar os addons do perfil embarcado + reescrever `profile-manifest.txt` e o pin no `classes4.dex` (1.0.142–1.0.146) | **app não abre**: `NoClassDefFoundError: Failed resolution of: Lsmartedtv/full/XBMCJsonRPC` / `Caused by: ClassNotFoundException: smartedtv.full.XBMCJsonRPC` |
| Recompilar o `classes3.dex` (bootstrap) com o pin novo | o pin real vive no `classes4.dex` (compartilhado com o código do app); mexer nele invalida o arquivo no ART |

Experimento controlado (3 variantes no emulador de projetor, mesmo APK base):

```
A = perfil limpo + pin trocado no dex  -> MORRE (NoClassDefFoundError XBMCJsonRPC)
D = perfil limpo + dex intacto         -> vivo, Home carrega
C = tudo intacto                       -> vivo
```

Ou seja: o dex que contém o pin não pode ser editado byte a byte; e o perfil não
pode ser alterado sem atualizar o pin conferido pelo `ProfileDirectorySeed`.

## Caminho técnico que falta (para a próxima rodada)

O pin do perfil está em `classes4.dex` junto de código do app (`smartedtv.full.*`).
O caminho correto é **remover a conferência de pin por pin fixo** do lado Java:
`ProfileDirectorySeed.install(...)` receber o pin de um arquivo de recurso
(`assets/smarted/profile-pin.txt`) em vez de uma constante do dex. Assim o perfil
pode mudar sem tocar em dex nenhum. Isso exige recompilar o dex do app
(`classes4.dex`) fora do injetor — o mesmo processo que gerou a base v22.

Enquanto isso não é feito, a 1.0.147 é a entrega **boa**: Home com dados
(`falhas de Home/skin: 0`), addons sem erro de instalação (`addons com erro: 0`),
perfil limpo depois do primeiro boot, e os avisos remanescentes são de addons de
terceiros herdados do perfil de fábrica.
