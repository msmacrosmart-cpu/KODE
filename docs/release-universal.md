# Build rápido — SMARTEDTV para Android

Esta é a linha **`smartedtv.full`** com a tela de entrada, o perfil e o motor Kodi da v22, não a linha histórica `org.xbmc.kodi`. Um commit de versão gera **um único** `SMARTEDTV-universal.apk`. Nada de APKs por arquitetura, XAPK, ZIP de partes ou instalador extra. O hash do download fica na descrição da release.

## Compatibilidade

- Android **5.0 (API 21)** ou posterior; target 34. No mesmo APK: `armeabi-v7a` (ARM 32) e `arm64-v8a` (ARM 64). O Android escolhe a biblioteca; um chip 64 com sistema 32 pode usar ARMv7.
- Celular: `MAIN/LAUNCHER`. Android TV, box, projetor e Fire TV com Android compatível: `MAIN/LEANBACK_LAUNCHER`, banner, layout de TV e navegação por controle. Nem toque, nem Leanback, nem hardware de TV são obrigatórios para instalar.
- “Universal” é **ARM**, não Android-x86/Intel. TV ou projetor precisa executar Android (não basta ter HDMI). Fire OS 7/8 baseados em Android atendem ao piso de API; Fire OS 5/6, Vega OS e sistemas como Tizen/webOS não atendem. Não há garantia de reprodução para todo codec ou firmware.

## Como publicar

1. No branch de release, altere `VERSION_NAME` e `VERSION_CODE` em `kodi/addons/service.smarted.bootstrap/smarted_release.py` junto com os overlays que pretende distribuir. Preserve as atribuições `NOME=valor`: esse descritor também é lido pelo shell. Use código **maior** que o já publicado. A v22 reutilizava `2103073`; a v21 já usava `2103077`.
2. Faça commit e push **no mesmo branch**. O workflow `smartedtv-universal.yml` usa um runner Ubuntu, JDK e Android SDK Build Tools 35.0.0; não recompila NDK, Gradle ou o Kodi. Não altere os workflows que geravam APKs por ABI.
3. `prepare.sh` busca o asset **fixo** da v22 e confere SHA-256 e certificado antes de usá-lo. O JKS legado é conferido pelo `content_hash` do backup no Dropbox (não se cria link público). `build.sh` aplica os overlays do checkout, ajusta o manifesto, alinha com `zipalign` e assina com `apksigner`. Nunca gera uma chave substituta.
4. O build verifica a assinatura v1/v2/v3, o certificado, o ZIP, o manifesto, os cabeçalhos ELF e a igualdade das libs/Dex com a base. Roda o boot simulado e, no AVD descartável API 30 com tradução ARM, instala a v22 e executa `adb install -r` da versão nova. Testa também instalação limpa e abre os componentes resolvidos para os dois launchers. Um erro impede a publicação. Não confundir tradução ARM e verificação estática de API 21 com testes físicos em cada aparelho.
5. A tag imutável `v<VERSION_NAME>-universal` aponta para o commit do build. O asset tem nome estável: `https://github.com/msmacrosmart-cpu/KODE/releases/latest/download/SMARTEDTV-universal.apk`. Para reproduzir uma entrega específica, prefira o link com a tag. Tempo em fila, rede e boot do AVD variam; dez minutos não são SLA.

**Reprodução local (Linux):** JDK 17+, Python 3.10+, `gh`, Android SDK com cmdline-tools, `ANDROID_HOME` definido e acesso ao GitHub Releases. Execute `smartedtv/release/prepare.sh` e `smartedtv/release/build.sh`. A saída é `build/universal/SMARTEDTV-universal.apk` (ignorada no Git). O smoke de instalação é **só para AVD descartável**, não para o celular do usuário.

**Assinatura:** este canal mantém o certificado SHA-256 `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a` para atualizar instalações compatíveis. A chave **de teste** e sua configuração **já estavam no repositório público**; não a trate como credencial privada de produção. Uma migração de produção requer chave protegida e plano de atualização, não uma troca silenciosa de certificado.

## Se um aparelho recusar

Mantenha o Play Protect ligado. Use o APK da release, confira o SHA-256, o espaço livre e, se fizer sideload, a permissão de instalação para o navegador/gerenciador escolhido. **Não desinstale nem apague dados como primeiro passo.** Com depuração USB autorizada, estes comandos dão um diagnóstico sem apagar o perfil:

```sh
adb shell getprop ro.build.version.sdk
adb shell getprop ro.product.cpu.abilist
adb install -r SMARTEDTV-universal.apk
```

`INSTALL_FAILED_NO_MATCHING_ABIS` aponta para a CPU/SO; `OLDER_SDK` para a API; `VERSION_DOWNGRADE` para um código anterior; `UPDATE_INCOMPATIBLE` pode indicar outra assinatura para `smartedtv.full` (inclusive em outro perfil). O código exato vale mais que a mensagem genérica “app não instalado”.
