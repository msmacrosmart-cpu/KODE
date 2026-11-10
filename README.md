# KODE — teste com Kodi 21.3 e Estuary em preto e branco

Esta base **reempacota um Kodi já compilado**. Não é uma compilação do código-fonte do Kodi, nem o antigo aplicativo Compose. A navegação, os add-ons e o motor são os do pacote recebido; foram alterados apenas a paleta padrão da Estuary e os dois fundos fornecidos com essa skin. Fanart, capas, outras skins, temas escolhidos pelo usuário e texturas podem continuar coloridos.

## Inspeção

O ZIP recebido pelo Dropbox contém 5.567 entradas; inclui `AndroidManifest.xml` binário, `classes.dex`, `resources.arsc`, os assets e `lib/armeabi-v7a/libkodi.so`. O conteúdo passou no teste de integridade ZIP e seu hash Dropbox corresponde ao informado pelo serviço. O SHA-256 é `01eeb9a9b2efc9f0de322fc4a7f128ba1bbe17021596128fa7622b65cfe2fbbc`. **Este hash difere do SHA-256 `96223d8da43c76ad7d4e04b32ead84d88bf4147e90d5c4b4fbb7f82c36efc053` publicado na release GitHub**, apesar de terem mesmo nome e tamanho. Portanto este build utiliza especificamente o arquivo do Dropbox, não um arquivo verificado como idêntico ao da release.

O pacote declara `org.xbmc.kodi`, versão 21.3, Android mínimo 21 e destino 34; inclui apenas bibliotecas nativas **armeabi-v7a (32 bits ARM)**. Não funcionará em dispositivos sem suporte a essa ABI. A Estuary usa a estrutura oficial de `assets/addons/skin.estuary/`; seu `Home.xml` é idêntico ao do tag oficial `21.3-Omega` inspecionado.

## Gerar APK de teste

Em Linux x86_64 com Python 3, pip, Node/npm e acesso a PyPI e npm:

```sh
./tools/kodi/setup.sh
# Somente se for uma nova instalação de teste, sem chave anterior:
./tools/kodi/init-test-key.sh
./tools/kodi/build-test.sh /caminho/Kodi.for.Android.21.3.zip
```

O arquivo de entrada não é incluído no repositório; use a cópia recebida pelo Dropbox. O reempacotador exige o SHA-256 dessa cópia. As ferramentas e a chave de teste ficam em `~/.cache/kode-build` (ou em `$KODE_BUILD_HOME`); o resultado fica em `artifacts/kodi-estuary-pb-teste.apk`. A instalação usa JDK 17 do pacote `jdk4py`, Pillow e o `apksigner.jar` do pacote npm `@postar/apktool-node`. Não há SDK Android ou compilação Gradle envolvidos neste processo.

O build verifica a assinatura v1/v2/v3. O APK mantém o nome de pacote original do Kodi, mas tem uma **chave de teste diferente**: não é atualização do Kodi instalado e pode exigir desinstalá-lo, o que pode apagar seus dados. Faça backup antes de qualquer desinstalação. A chave de teste não é apropriada para distribuição ou produção. Guarde uma cópia segura dessa chave fora do repositório; o cache deste ambiente é temporário. Se ela for perdida, o build para em vez de gerar outra chave silenciosamente, porque um APK com chave diferente não atualiza a instalação anterior. `init-test-key.sh` cria uma chave apenas para uma instalação independente e não sobrescreve uma chave existente.

## Limitações e licenças

A assinatura e o conteúdo foram verificados estaticamente; **o APK ainda não foi instalado nem testado em dispositivo ou emulador**. As funções reais e o comportamento da skin ainda precisam ser validados no aparelho. O APK é baseado em binários de terceiros, não no fonte reconstruído, e o código-fonte correspondente exato ao ZIP do Dropbox não foi verificado. Antes de redistribuir, verifique a proveniência, as licenças dos componentes e as obrigações de fornecimento do fonte. O Kodi oficial está em https://github.com/xbmc/xbmc (tag `21.3-Omega`). A licença da Estuary acompanha a alteração em `kodi/skin/LICENSE.txt`; os avisos originais também permanecem no APK.

## Versões e releases

As próximas mudanças devem ter um release de teste identificado e acompanhado de link. O rótulo do release não altera automaticamente o `versionCode` ou o `versionName` no AndroidManifest compilado: este APK ainda declara Kodi 21.3 (`versionCode` 2103000). Atualizações sobre uma instalação existente exigem o mesmo nome de pacote e a mesma chave; o versionamento Android crescente e a assinatura durável ainda precisam ser implementados antes de prometer atualizações de produção.
