# APK único (monólito): Kodi + AdMob no mesmo pacote

Decisão: **fim do app auxiliar**. Um só APK, pacote `smartedtv.full`, com o
player compilado do código-fonte, os anúncios dentro do app e o conteúdo da
linha clássica. Instalou um arquivo, acabou.

## Como o build funciona

```
xbmc/xbmc @ 21.3-Omega
        │
        ├─ integrate-monolith.py       (smartedtv/tools)
        │     1. version.txt: APP_PACKAGE smartedtv.full   (APP_NAME segue "Kodi" → libkodi.so e .kodi intactos)
        │     2. Gradle: versionCode 2103050 / versionName 1.0.64
        │                + implementation play-services-ads:23.2.0
        │     3. Manifesto: permissão AD_ID, meta-data APPLICATION_ID,
        │                AppOpenActivity + PreRollActivity (sensorLandscape, exported)
        │     4. Java: SmartAds / AdTela / AppOpenActivity / PreRollActivity
        │                copiados para tools/android/packaging/xbmc/src/
        │                E listados no cmake/scripts/android/Install.cmake
        │                (sem essa lista o Java não entra no APK)
        │     5. Conteúdo: skin.novatv (+ skin.smartedtv.classic), plugin.video.smarted,
        │                service.smarted.bootstrap, resource.uisounds.silencio
        │                → addons/ + installdata/common/addons.txt + system/addon-manifest.xml
        │     6. settings.xml: skin padrão = skin.novatv
        │     7. smart_ads.py: classes internas (smartedtv.full.*) e plano B desligado
        │
        ├─ tools/depends → cmakebuildsys → make -j2 → make apk
        │
        └─ conferência bloqueante (aapt2 + dex + assets) → release
```

Workflow: `.github/workflows/build-monolith.yml` (tag `v1.0.64-unificado`,
arquivo `SMARTEDTV-1.0.64-unificado-arm64-v8a.apk`).

## Por que o `APP_NAME` não muda

O Kodi deriva `libkodi.so`, `assets/addons/kodi.binary.*`, o perfil `.kodi` e as
variáveis `KODI_*` do `APP_NAME`. Trocar para SMARTEDTV renomearia tudo isso e
quebraria o carregamento da biblioteca nativa e os dados do usuário. O que muda
é só o **applicationId** (identidade do app no Android) e os textos de exibição.

## A ponte dos anúncios, agora interna

Antes (dois apps): `StartAndroidActivity(smartedtv.full, ação, …, org.smartedtv.ads.PreRollActivity)`.

Agora (um app): o mesmo builtin, apontando para dentro:

```
StartAndroidActivity(smartedtv.full,smartedtv.ads.PREROLL,,,,,,,smartedtv.full.PreRollActivity)
StartAndroidActivity(smartedtv.full,smartedtv.ads.APPOPEN,,,,,,,smartedtv.full.AppOpenActivity)
```

- o plano B (data URI no launcher) fica **desligado**: o launcher do pacote é o
  próprio Kodi, abriria a interface de novo;
- o vídeo continua carregando atrás do anúncio, porque é o mesmo processo;
- desinstalar o app de anúncios não quebra mais nada — ele não existe.

## Modo de teste do AdMob

Ligado por padrão (`SmartAds.teste = true`), usando os blocos de teste do Google.
Para produção: `smartedtv/tools/ads-java/SmartAds.java.in` → `teste = false`
(e recompilar). Em tempo de execução, o próprio `StartAndroidActivity` pode
mandar `smartedtv://ads?teste=0`.

## O que a conferência do CI exige antes de publicar

| Checagem | Onde |
| --- | --- |
| `package: name='smartedtv.full'` | aapt2 badging |
| versionName 1.0.64 / versionCode 2103050 | aapt2 badging |
| `.AppOpenActivity`, `.PreRollActivity` | aapt2 xmltree |
| APPLICATION_ID + permissão `AD_ID` | aapt2 xmltree |
| `sensorLandscape` nas telas de anúncio | aapt2 xmltree |
| blocos do AdMob + classes + SDK + tag `SmartAds` | dex |
| `assets/addons/skin.novatv`, `plugin.video.smarted`, bootstrap, uisounds | ZIP |
| ponte apontando para dentro e sem plano B | smart_ads.py embarcado |

Se qualquer uma falhar, o APK não é publicado.

## Riscos e o que observar

1. **Tempo**: build completo ~1h30 num runner (dependências + Kodi + Gradle).
2. **Disco**: a receita já limpa o runner porque o build passa de 14 GB.
3. **Primeira instalação**: outro applicationId, então não atualiza por cima do
   `org.xbmc.kodi` antigo — são apps diferentes, podem conviver.
4. **Conteúdo**: o catálogo é literalmente o mesmo addon da linha clássica
   (`plugin.video.smarted`), com a skin e o `service.smarted.bootstrap` que já
   rodam hoje. Se algo do catálogo depender do perfil antigo (`.kodi`), a
   primeira abertura recria — vale testar a Home e as categorias na TV.

## Armadilha das dependências (custou dois runs)

O `tools/depends` **não** instala em `--prefix/lib`. O `configure.ac` faz
`deps_dir="$use_host-$use_ndk_api-$build_type"`, então as bibliotecas ficam em:

```
$RUNNER_TEMP/xbmc-depends/aarch64-linux-android-21-release/{lib,include,share}
```

Checar `$RUNNER_TEMP/xbmc-depends/lib` faz o build morrer depois de ~75 min de
dependências já compiladas. A conferência atual procura `xbmc-depends/*-android-*`
e não bloqueia (quem decide é a compilação do Kodi).

## Estado do build (13/11/2026)

O que já está provado, com os runs reais:

| Run | Até onde chegou |
| --- | --- |
| 43619130136 | integração do monólito **OK**, dependências compiladas, morreu na conferência do prefixo |
| 43627396317 | idem (prefixo ainda errado) |
| 43635491717 | **nem começou**: bloqueio de faturamento do GitHub Actions |

Duas vezes a etapa `6. Código-fonte + INTEGRAÇÃO DO MONÓLITO` passou no fonte
real do Kodi 21.3-Omega — ou seja, o patch (`applicationId`, versão, gradle,
manifesto, Java, Install.cmake, addons, skin padrão, ponte) está correto.

### O bloqueio atual não é código

```
The job was not started because recent account payments have failed
or your spending limit needs to be increased.
Please check the 'Billing & plans' section in your settings
```

Relatório da conta: <https://github.com/settings/billing> → *Spending limits* e
forma de pagamento. Enquanto isso não for resolvido, **nenhum** workflow roda
nesse repositório privado (nem os pequenos).

Custo por tentativa: ~110 min de runner (≈75 min de dependências + ≈35 min de
Kodi/Gradle). Com o cache funcionando, as próximas caem para ~40 min.

### Checklist para quando o billing voltar

1. `git push` em `arena/7dedf371-kode` (mexer em `.github/workflows/build-monolith.yml`
   ou em `smartedtv/`) — o build dispara sozinho.
2. Acompanhar até o passo `10. Conferir o monolito`; ele é bloqueante.
3. Se falhar, os logs úteis caem no próprio repositório:
   `docs/build-log-deps.txt` (fotografia das dependências) e
   `docs/build-log-falha.txt` (fim dos logs de dependências/Kodi).
4. Sucesso = release `v1.0.64-unificado` com
   `SMARTEDTV-1.0.64-unificado-arm64-v8a.apk` + `.sha256`.

## Identidade visual (1.0.65)

Artes do usuário aplicadas em 13/11, via `smartedtv/assets/brand/`:

| Arquivo | Origem | Uso |
| --- | --- | --- |
| `splash.png` (1280x720) | arte widescreen enviada | splash do Android e da GUI, preenchendo 1920x1080 sem barras |
| `logo-oficial.jpg` (2000x2000) | arte quadrada enviada | banner Android TV 320x180 e ícones internos do Kodi |
| `mark.png` (1720x1720) | recorte central da arte quadrada | launcher (36…192 px), `vendor_icon`, `vendor_logo` |

`make-brand-assets.py` passou a aceitar a arte widescreen: `cover()` preenche o
quadro 16:9 (corta as sobras) em vez de emoldurar a arte quadrada. Sem
`splash.png`, ele volta ao comportamento antigo — nada quebra.

## Verificação do APK (depois de dois runs perdidos)

A conferência agora é um script: `smartedtv/tools/verify-monolito-apk.py`.

* roda **todas** as checagens e imprime um relatório (OK / FALHA / aviso);
* só o fim decide o código de saída — um erro não esconde os outros;
* julga o que é obrigatório (pacote, versão, activities, APPLICATION_ID, AD_ID,
  addons, splash, libkodi.so, classes do AdMob no dex) e o que é aviso;
* grava `docs/verificacao-apk.txt` no próprio repositório.

O `APPLICATION_ID` do AdMob **não** existe no dex: ele é uma meta-data do
manifesto. Exigi-lo no dex derrubou os runs 43637389678 e 43638117645 com o APK
já pronto — o tipo de erro que o relatório completo teria mostrado na hora.

O APK de cada build sobe como artifact (`apk-unificado-<versão>`), e o workflow
`check-apk.yml` roda a mesma verificação contra esse artifact em ~1 min, sem
recompilar: dá para ajustar a checagem sem esperar 2 h.

## Resultado (13/11/2026)

Build **verde**: run `43643564098` (Kodi 21.3-Omega compilado do fonte, ~1h45).

Release: <https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.65-unificado>

* `SMARTEDTV-1.0.65-unificado-arm64-v8a.apk` — 89.380.197 bytes
* `SMARTEDTV-1.0.65-unificado-arm64-v8a.apk.sha256`

Verificação automática (`docs/verificacao-apk.txt`): **0 falhas e 0 avisos**.

| Item | Estado |
| --- | --- |
| `package: name='smartedtv.full'` | OK |
| versionName 1.0.65 / versionCode 2103051 | OK |
| `.AppOpenActivity` / `.PreRollActivity` no manifesto | OK |
| `APPLICATION_ID` do AdMob + permissão `AD_ID` | OK |
| telas de anúncio em `sensorLandscape` (=6) | OK |
| skin.novatv + 60 addons embarcados | OK |
| splash novo (GUI e Android) + 52 PNG em `res/` | OK |
| `lib/arm64-v8a/libkodi.so` | OK |
| blocos do AdMob, activities e SDK no dex | OK |
| ponte apontando para dentro, sem plano B | OK |

O APK também fica guardado como artifact (`apk-unificado-1.0.65`), então
`check-apk.yml` reconfere tudo em ~1 min sem recompilar.

## 1.0.66 — base estável restaurada + splash branco

### O que estava faltando (bug do catálogo)

A 1.0.65 abria com **perfil limpo**. Na linha clássica o APK levava dentro de si
um perfil já customizado — e é lá que morava o `plugin.video.BrazucaPlay.Matrix`,
para onde `plugin.video.smarted` delega as categorias (Doramas, Animes,
Novelas, Desenhos). Sem o Brazuca instalado, sobram só os atalhos que o próprio
plugin monta: as categorias "somem".

Agora o APK carrega `assets/smarted/profile/**` + `profile-manifest.txt` da
**1.0.63 clássica** (release `v1.0.63-classica`), injetado no build.

### Como a base entra e é aplicada

```
1b. baixa SMARTED-TV-v1.0.63-arm64.apk        (manifesto conferido: 1447de81…)
9.  make apk -> inject-base-estavel.py        (assets/smarted/** entra; assinatura antiga sai)
    zipalign -p 4 -> apksigner sign           (realinha e assina com o keystore do projeto)
app: Splash.startXBMC() -> SeedBase.pronto()
    copia assets/smarted/profile/** para <files>/.kodi com hash+tamanho conferidos,
    ajusta lookandfeel.skin para skin.novatv e publica por rename atômico
```

`SeedBase` é o equivalente interno do launcher dex da linha clássica:
**só age quando não existe `.kodi`** (perfil de quem já usa nunca é tocado),
valida o SHA-256 fixo do manifesto antes de copiar, grava num diretório de
preparo e só então faz o rename. Qualquer falha = perfil antigo preservado e o
Kodi abre normal (o app nunca fica travado).

### Splash (item 3 do pedido)

`res/layout/activity_splash.xml` reescrito:

| antes | agora |
| --- | --- |
| barra azul (`@drawable/progresscolor`, gradiente `#0E5A91`) | `@drawable/progresswhite` — branco puro sobre trilho `#33FFFFFF`, 3dp, cantos 2dp |
| `TextView` branco com "Starting SMARTEDTV...", "Clearing cache..." | `visibility="gone"`, o Kodi continua escrevendo nele sem aparecer |
| arte com `scaleType=centerCrop` (cortava as bordas) | `centerInside` + fundo preto: logo widescreen inteira e centralizada |

As 5 chamadas `mProgress.setVisibility(View.INVISIBLE)` do `Splash.java` foram
removidas: a barra não desaparece mais no meio do carregamento.

A verificação bloqueante passou a exigir: manifesto do perfil com o hash
esperado, presença do Brazuca no perfil, `drawable/progresswhite` nos recursos,
`assents`/texto escondido no layout e a classe `SeedBase` no dex.

## Resultado 1.0.66

Release: <https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.66-unificado>

| Item | Valor |
| --- | --- |
| APK | `SMARTEDTV-1.0.66-unificado-arm64-v8a.apk` |
| tamanho | 248.023.338 bytes (236,5 MB — 85 MB do Kodi + ~160 MB da base estável) |
| sha256 | `d97f97d2c978c2d11219c09f720b1956e7e23c2e901c803904c5f9b5ac413318` |
| adicionais | `.sha256` ao lado |

Conferência automática sobre o próprio APK publicado: **0 falhas, 0 avisos** —
pacote/versão, activities e APPLICATION_ID do AdMob, permissão AD_ID, skin +
60 addons, splash, `libkodi.so`, classes do AdMob no dex, ponte interna,
perfil semeado (2731 arquivos, manifesto `1447de81…`, Brazuca presente) e
barra branca com o texto escondido.

### Notas de processo (para não repetir)

* O GitHub Actions roda `run:` com `bash -e`: um passo que chama um script que
  retorna != 0 morre **antes** de gravar o relatório. Os passos de conferência
  usam `set +e` em volta do Python e só decidem o resultado no fim.
* `aapt2` imprime `visibility` pela enum do aapt (`visible=0, invisible=1,
  gone=2`) — não pelos valores do `View` (`GONE=8`).
* A release do 1.0.66 foi publicada pelo `check-apk.yml` a partir do artifact
  do build, porque o build morreu no passo de conferência por causa desses dois
  detalhes — o APK em si já estava correto e assinado. O fluxo normal
  (`build-monolith.yml` → passo 12) volta a publicar sozinho agora que a
  conferência está certa.

## 1.0.67 — skin e catálogo vindos do APK estável

### O que o diff provou (`docs/diff-estavel.txt`)

Comparação entre `v1.0.63-classica` (7774 entradas) e o APK unificado (7162):

| pasta | estável | unificado | leitura |
|---|---|---|---|
| `assets/addons/skin.novatv/` | **934** | 222 | faltavam 712 arquivos, quase todos `media/*.png` |
| `assets/addons/plugin.video.smarted/` | 16 | 16 | 7 arquivos com conteúdo **diferente** |
| `assets/addons/service.smarted.bootstrap/` | 11 | 11 | só `smart_ads.py` diferente (nosso, por causa do AdMob) |

O perfil não era o problema: sem as imagens da skin e com o catálogo trocado,
a Home abria com as abas/categorias vazias — exatamente o que aparecia na tela.
Os backups internos (`BACKUP+SMARTED.zip`, `SaveData.zip`) também não têm
skin/menus, então não havia de onde recuperar isso do perfil.

### Correção

`inject-base-estavel.py` agora tem a lista `SUBSTITUIR`:

```python
SUBSTITUIR = ("assets/addons/skin.novatv/",
              "assets/addons/plugin.video.smarted/")
```

Ao injetar o perfil da base, as entradas dessas duas pastas são **descartadas
do nosso APK e substituídas, byte a byte, pelas do APK estável** — 712 imagens
da skin + o `plugin.video.smarted` original. O resto do APK continua sendo o
nosso, em especial `service.smarted.bootstrap/smart_ads.py` (ponte do AdMob,
ids `ca-app-pub-2066014755407744/…`), que é justamente o único arquivo que
difere no bootstrap.

### Conferência nova (verificador)

* `skin.novatv` com **≥ 800 arquivos** e **≥ 600 imagens em `media/`**;
* `media/DefaultAddon.png` presente (imagem-sentinela);
* `plugin.video.smarted` com **≥ 16 arquivos** e `catalogue.py` presente.

Se qualquer uma falhar, o APK não é publicado.

### Resultado 1.0.67

Release: <https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.67-unificado> — run [43661280978](https://github.com/msmacrosmart-cpu/KODE/actions/runs/43661280978), build verde do início ao fim (o `build-monolith.yml` publicou sozinho).

| item | valor |
|---|---|
| APK | `SMARTEDTV-1.0.67-unificado-arm64-v8a.apk` |
| tamanho | 249.678.389 bytes (238,1 MB) |
| pacote / versão | `smartedtv.full` / 1.0.67 (2103053) |
| skin.novatv | **934 arquivos**, **712 imagens** em `media/` |
| plugin.video.smarted | 16 arquivos (mesmos da 1.0.63) |
| conferência | **0 falhas, 0 avisos** |

O build anterior (1.0.66, run 43659376318) falhou no passo 9 com uma
**colisão falsa**: as 222 entradas de `skin.novatv` do APK novo entravam no
conjunto `existentes` do injetor, e a checagem "não duplicar" abortava a
injeção. A checagem agora usa só as entradas realmente escritas, e um teste
ponta a ponta (`InjecaoDaBaseTest`) monta dois APKs de mentira e prova que
skin/plugin vêm da base enquanto `smart_ads.py` continua o nosso (AdMob).

Também: o passo 9 grava `smartedtv/log-passo9.txt` e o passo 11 publica esse
log no branch quando falha (antes o log do erro se perdia) e faz
`git pull --rebase` antes do push, para não perder o relatório quando o branch
andou durante o build.

## 1.0.68 — base do Dropbox + seed que não desiste

### A base é a do usuário

O build passou a baixar o APK de referência do dono do app
(`https://www.dropbox.com/scl/fi/p5blo0t1rw86bwhcmkkns/SMARTEDTV.apk…`) e a usá-lo
como base, em vez de uma cópia nossa publicada em release. Inspeção
(`docs/base-dropbox.txt`): 242.222.254 bytes, `org.xbmc.kodi` 1.0.63 (2103049),
7774 arquivos, `skin.novatv` com **934** arquivos e **712** imagens,
`plugin.video.smarted` 0.3.3, perfil com 2735 arquivos (340 só em `userdata`,
incluindo `Addons33.db`, `Textures13.db`, `ViewModes6.db` e os `addon_data` do
Brazuca/YouTube). É o mesmo conteúdo que já entrávamos, agora com a fonte certa.

### Por que a estrutura não aparecia (causa real)

O seeder original do APK foi descompilado (`docs/bootstrap-referencia.txt`,
`org.smartedtv.bootstrap.*`) e comparado com o nosso:

| regra do original | nosso 1.0.66 |
|---|---|
| `ProfileDirectorySeed.install(profile, manifest, dataHome, filesDir, "1447de81…")` | igual |
| confere `profile-manifest.txt` por SHA-256 | igual |
| copia conferindo arquivo a arquivo, staging + rename | igual |
| `setDefaultSkin`: troca `skin.estuary` por `skin.novatv` | igual |
| **se `.kodi` existe, devolve `false` e nunca semeia** | igual |

O problema é a última linha combinada com o histórico do app: a 1.0.65 abriu o
Kodi com perfil vazio, o Kodi **criou** `Android/data/smartedtv.full/files/.kodi`
e, a partir daí, toda abertura caía em "já existe perfil, não mexer". O perfil
ficava Estuary puro — sem skin, sem menus, sem Brazuca. Nunca mais semeava.

### Correção (sem inventar estrutura)

* `perfilSmarted(.kodi)` = tem `addons/plugin.video.BrazucaPlay.Matrix/addon.xml`
  **e** `userdata/guisettings.xml`. Só um perfil assim é preservado.
* `.kodi` que não é da base (Kodi recém-instalado ou build antigo do app) é
  **renomeado** para `.kodi.antigo-<timestamp>` e a base entra no lugar. Nada é
  apagado.
* `jaTentei()` evita laço de splash se a cópia falhar duas vezes.
* `home()` passa a respeitar `xbmc.data`, como o launcher original.
* Tudo é registrado em `Android/data/smartedtv.full/files/smarted-seed.log`
  (`perfil da base ja presente`, `instalando a base…`, `instalado: N arquivos`,
  `falhou: …`) — é o arquivo que fecha qualquer dúvida em campo.

### Resultado 1.0.68

Release: <https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.68-unificado> — run
[43699254709](https://github.com/msmacrosmart-cpu/KODE/actions/runs/43699254709), build verde
(nenhum passo pulado por falha; o passo 1b baixou a base do Dropbox).

| item | valor |
|---|---|
| APK | `SMARTEDTV-1.0.68-unificado-arm64-v8a.apk` |
| tamanho | 249.682.485 bytes (238,1 MB) |
| pacote / versão | `smartedtv.full` / 1.0.68 (2103054) |
| base usada | APK do Dropbox (242.222.254 bytes, `org.xbmc.kodi` 1.0.63) |
| manifesto do perfil | `1447de81…` (igual ao da base → mesmo perfil) |
| skin.novatv | 934 arquivos, 712 imagens |
| conferência | **0 falhas, 0 avisos** |

Na primeira abertura desta versão o app guarda o `.kodi` vazio que sobrou das
tentativas anteriores como `Android/data/smartedtv.full/files/.kodi.antigo-<data>`
e instala a base. A cópia tem ~240 MB: a tela fica na splash com a barra branca
até terminar (1 a 3 minutos). O que aconteceu fica em
`Android/data/smartedtv.full/files/smarted-seed.log`.
