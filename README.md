# SMARTEDTV para Android

**[Baixar o APK universal](https://github.com/msmacrosmart-cpu/KODE/releases/latest/download/SMARTEDTV-universal.apk)** · [Releases](https://github.com/msmacrosmart-cpu/KODE/releases)

Um único arquivo para **ARM de 32 e 64 bits**, a partir do **Android 5.0** (API 21). O pacote da linha atual é `smartedtv.full`, com launchers para celular e TV. Para compilar por commit, verificar a assinatura e diagnosticar recusas de instalação, veja o **[guia da release universal](docs/release-universal.md)**.

---

## Histórico — APK de teste 1.0.15 baseado em Kodi 21.3

As informações abaixo referem-se **apenas à antiga linha arm64 `org.xbmc.kodi`**, não ao download universal acima.

Este projeto **reempacota binários do Kodi**, não compila o sistema Kodi do código-fonte. Ele preserva o motor, Java/Dex e os add-ons do APK de entrada. A versão de teste atual altera o nome exibido no Android, ícones do launcher, banner da TV, imagens de inicialização e marca principal da interface; define a paleta padrão da Estuary em tons de cinza. Imagens de add-ons, fanart, capas, outras skins e referências internas ao Kodi podem permanecer inalteradas.

## Compatibilidade e limitações

- A versão `1.0.15` contém apenas **arm64-v8a**, Android 5 (API 21) ou posterior. Existem aparelhos ARM 32 bits, Intel e 64 bits incompatíveis; este APK não é universal.
- A assinatura foi verificada e o APK foi alinhado; classes.dex e todas as 46 bibliotecas nativas foram comparadas byte a byte com a entrada. **Não foi instalado nem testado em aparelho ou emulador.** Isso não prova que todas as funções funcionem.
- O nome de pacote permanece `org.xbmc.kodi`, porque o motor compilado e os componentes podem depender dele. Não pode coexistir com o Kodi oficial; uma instalação com outra assinatura pode causar conflito. Faça backup antes de qualquer desinstalação.
- Usa uma chave **de teste**, diferente tanto da oficial quanto da versão de teste anterior. Este APK não pode atualizar instalações com outras assinaturas. Não use essa chave para produção. Para atualizações futuras desta linha de teste, preserve a chave com segurança; não crie outra silenciosamente.
- O código-fonte e as licenças do Kodi devem ser avaliados antes de redistribuir. O código oficial está em https://github.com/xbmc/xbmc/tree/21.3-Omega; a licença da Estuary está em `kodi/skin/LICENSE.txt`, e os avisos originais permanecem no APK. O código-fonte correspondente exato do primeiro ZIP de 32 bits não foi verificado.

## Ambiente de reempacotamento

Em Linux x86_64 com Python 3, pip, npm, DejaVu Sans e acesso a PyPI e npm:

```sh
./tools/kodi/setup.sh
# Coloque a chave de teste já existente em ~/.cache/kode-build/smarted-tv-test.jks.
./tools/kodi/build-smarted-test.sh /caminho/kodi-21.3-Omega-arm64-v8a.apk
```

A entrada utilizada foi o APK arm64 21.3 recebido pelo Dropbox, SHA-256 `34e7526705a038fa12f70161d0c1cc38f10deb0fee305b46fbd46ff015d05b44`, com assinatura verificada e certificado correspondente ao APK Kodi inspecionado. A saída fica em `artifacts/SMARTED-TV-v1.0.15-arm64-teste.apk`. O script valida a origem, decodifica recursos com Apktool, aplica a marca, alinha os arquivos armazenados, assina, verifica assinatura e compara o código e assets. A chave tem senha de teste e não deve ser usada em produção. As ferramentas ficam no cache; o APK original e a chave não são incluídos no Git.

O instalador usa JDK 17 do pacote `jdk4py`, Pillow, `pyaxmlparser`, Apktool e apksigner do pacote npm `@postar/apktool-node`. Não é um ambiente de compilação completo do Kodi com Android SDK/NDK e Gradle.

## Versionamento

Esta versão altera o `versionName` para `1.0.15` e o `versionCode` para `2103001`; para atualizações posteriores é necessário incrementar o código e preservar o pacote e a assinatura. O conteúdo nativo continua sendo Kodi 21.3. As versões anteriores usavam outro certificado; não são atualizáveis diretamente para esta versão.
