# Ambiente de compilação SMARTEDTV

Este documento responde às perguntas 1.1 a 1.6 da entrega: ferramentas, versões,
dependências, configurações, comando de build e onde o APK sai.

## 1. Resumo

O SMARTEDTV é o **Kodi 21.3-Omega compilado do código-fonte** para Android
arm64-v8a, com a identidade visual da marca aplicada no código (nome do app,
textos de interface, splash, ícones, banner) e **sem** add-ons de conteúdo, sem
skin Nova TV e sem perfil pré-configurado.

O ambiente está versionado em `smartedtv/tools/` e é reproduzível com dois
comandos: `setup-build-env.sh` (uma vez) e `build-apk.sh` (a cada build).

```
smartedtv/
├── assets/brand/            artes oficiais da marca (vindas do Dropbox)
├── out/                     artefatos gerados de identidade (splash, ícones, banner)
├── tools/
│   ├── setup-build-env.sh   instala/valida SDK, NDK, JDK
│   ├── make-brand-assets.py gera os recursos visuais a partir das artes oficiais
│   ├── patch-source.py      aplica a marca no código do Kodi
│   ├── build-apk.sh         compila, empacota, assina e verifica
│   ├── verify-apk.py        26 verificações estáticas no APK final
│   └── smoke-emulador.sh    instala e abre no emulador, coletando evidências
├── build/                   (gerado) fonte patchado, dependências, APK
└── DOCUMENTACAO/            esta documentação
```

## 2. Ferramentas instaladas e versões

As versões **não foram escolhidas por preferência**: são exatamente as que a
`docs/README.Android.md` do Kodi 21.3-Omega pede e as que o build de referência
deste projeto usou com sucesso (run `42775900278`, 1h05m, concluído).

| Ferramenta | Versão | Por que esta versão |
|---|---|---|
| Ubuntu | 22.04 | Runner do build de referência |
| JDK | 17 (Temurin) | AGP 8.1.1 exige 17; o build de referência usou 17 |
| Android SDK platform | `android-34` | `compileSdk`/`targetSdk` do Kodi 21.3 |
| Android build-tools | `33.0.1` | Versão indicada no README.Android |
| Android NDK | `21.4.7075529` | NDK 26+ removeu o toolchain que o Kodi 21.3 usa — **não atualizar** |
| Gradle | 8.3 (wrapper do próprio Kodi) | `gradle-wrapper.properties` do upstream |
| Android Gradle Plugin | 8.1.1 | `tools/android/packaging/build.gradle` do upstream |
| CMake | 3.22+ (Ubuntu 22.04) | mínimo 3.12; o do sistema funciona |
| GCC/G++ | do Ubuntu 22.04 | compila as dependências nativas do host |
| Python | 3.11 | scripts de automação e dependências do Kodi |
| commandlinetools | 11076708 | sdkmanager estável |

Tudo isso é instalado por `smartedtv/tools/setup-build-env.sh`, que ao final
escreve `smartedtv/build/env-report.txt` com as versões efetivamente instaladas.

## 3. Dependências

### 3.1 Dependências de sistema (host)

Autoconf, automake, bison, build-essential, curl, flex, gawk, git, gperf,
lib32stdc++6, lib32z1, lib32z1-dev, libcurl4-openssl-dev, unzip, zip, zlib1g-dev,
libtool, pkg-config, cmake.

### 3.2 Dependências compiladas (`tools/depends`)

O Kodi não usa as bibliotecas do sistema no Android: ele compila ~40 dependências
cruzadas (ffmpeg, curl, openssl/gnutls, libass, freetype, harfbuzz, fribidi,
libdvd*, libbluray, sqlite, taglib, tinyxml, expat, rapidjson, flatbuffers, fmt,
spdlog, pcre, libiconv, gettext, python3.11, cryptodome, pillow, etc.) em
`smartedtv/build/xbmc-depends` para `aarch64-linux-android`.

Esse passo é o mais demorado (~40 min) e é **cacheável**: rodando com
`SKIP_DEPENDS=1` a recompilação usa as dependências já compiladas e leva minutos.

### 3.3 Add-ons embarcados

Só os add-ons nativos do Kodi 21.3 (`assets/addons/`), incluindo `skin.estuary`,
`repository.xbmc.org` (para o usuário instalar o que quiser depois) e os
`kodi.binary.*`. Nenhum add-on de conteúdo, nenhuma skin adicional.

`resource.language.pt_br` é incluído a partir do repositório oficial
`xbmc/repo-resources` (branch `omega`), porque o Kodi só embarca `en_gb` por
padrão e o público deste projeto é brasileiro.

## 4. Configurações aplicadas

### 4.1 Configuração de compilação

```
./configure \
  --with-tarballs=<build>/tarballs \
  --host=aarch64-linux-android \
  --with-sdk-path=<sdk> \
  --with-ndk-path=<sdk>/ndk/21.4.7075529 \
  --prefix=<build>/xbmc-depends
```

Depois: `make -C tools/depends/target/cmakebuildsys BUILD_DIR=<build>/kodi-build`
e `make -C <build>/kodi-build -j<N>` e `make -C <build>/kodi-build apk`.

### 4.2 Identidade (o que `patch-source.py` altera)

Ver a tabela completa no cabeçalho de `smartedtv/tools/patch-source.py`. Em
resumo: nome do app Android, textos de splash/permissões/log, strings de produto,
nome padrão do dispositivo, descrição da skin Estuary e todos os recursos de
imagem (splash, launcher, banner, `vendor_logo`, `vendor_icon`, `icon*`).

### 4.3 Assinatura

O build assina com a **chave de teste do projeto**
`dropbox/smarted-tv-test.jks` (alias `smarted-tv-test`, senha `android`, ambos já
versionados no repositório como nas builds anteriores). É a mesma chave usada
desde a versão 1.0.15 da linha de teste, o que mantém a possibilidade de
atualizar instalações de teste existentes — desde que o `versionCode` seja maior
(este build usa **2104000**, contra 2103001/2103002 das versões 1.0.15/1.0.16).

> ⚠️ **Não é chave de produção.** A chave oficial do Kodi (certificado
> `f517b44b…`) não está disponível neste repositório. Sem ela, **não é possível**
> atualizar uma instalação do Kodi oficial ou de qualquer build assinado com a
> chave oficial — o Android recusa a atualização por divergência de assinatura.
> Nesse caso é necessário desinstalar (perdendo os dados) ou usar outro
> Application ID. Ver `RELATORIO-INTEGRIDADE.md` §Atualização.

## 5. Comando de compilação

```bash
# uma vez, no host de build (Ubuntu 22.04+)
./smartedtv/tools/setup-build-env.sh

# a cada build
./smartedtv/tools/build-apk.sh
```

Para recompilar rápido depois da primeira vez:

```bash
SKIP_DEPENDS=1 ./smartedtv/tools/build-apk.sh
```

Na CI o mesmo pipeline roda em `.github/workflows/smartedtv-build-source.yml`
(ubuntu-22.04, JDK 17, SDK/NDK fixos, ~65 min).

## 6. Onde o APK é gerado

| Arquivo | Caminho |
|---|---|
| APK final | `smartedtv/build/out/SMARTEDTV-21.4-arm64-v8a.apk` |
| Hash | `smartedtv/build/out/SMARTEDTV-21.4-arm64-v8a.apk.sha256` |
| Relatório do build | `smartedtv/build/out/build-report.txt` |
| Relatório do ambiente | `smartedtv/build/env-report.txt` |
| Log completo | `smartedtv/build/build.log` |

Na CI os mesmos arquivos ficam no artefato `smartedtv-apk-arm64`.

## 7. Limitações encontradas neste ambiente

| Limitação | Impacto | Solução |
|---|---|---|
| O sandbox de desenvolvimento não tem acesso a `dl.google.com`, `mirrors.kodi.tv` nem ao mirror do Gradle | SDK, NDK e dependências nativas **não puderam ser baixados aqui**; só a lógica dos scripts pôde ser validada localmente | compilação executada na CI do GitHub (ubuntu-22.04), que tem acesso; o mesmo comando roda em qualquer Ubuntu 22.04 |
| Sem aparelho Android físico nem KVM no sandbox | instalação/execução só é possível no emulador da CI | workflow `smartedtv-emulator-test.yml` (API 30, x86_64) instala, abre e coleta evidências |
| Sem a chave de produção do Kodi | não é possível atualizar uma instalação oficial existente | mantido `org.xbmc.kodi` + documentado; ver §Atualização |

## 8. Como reproduzir do zero, sem este repositório

1. Instalar Ubuntu 22.04 com as dependências de §3.1.
2. `git clone --branch 21.3-Omega https://github.com/xbmc/xbmc`
3. `python3 smartedtv/tools/patch-source.py <kodi>` (aplica a marca)
4. Seguir §4.1 para compilar.
5. Assinar com sua chave mantendo `org.xbmc.kodi`.

O passo 3 é o único específico deste projeto; todo o resto é o procedimento
oficial do Kodi para Android.
