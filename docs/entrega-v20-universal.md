# SMARTEDTV 1.0.90 (v20) — um único APK universal

Resposta ao pedido: **sim, é possível um único APK com assinatura v1 + v2 + v3
e as duas arquiteturas**. Esta é a v20.

## APK

https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.90-universal-v20/SMARTEDTV-atual-v20-universal.apk

- Tamanho: **285.488.378 bytes**
- SHA-256: `3fbc702f4ed329b0b67666049902855b241e99672d3df42e18fcec69c150149f`
- Pacote: `smartedtv.full`
- Versão: **1.0.90 / versionCode 2103076**
- minSdk 21 · targetSdk 34
- ABIs: **arm64-v8a + armeabi-v7a** no mesmo arquivo
- Assinatura: **v1 = true, v2 = true, v3 = true**, certificado
  `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`
- `debuggable=false`, `testOnly` ausente

Release: https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.90-universal-v20

## Build

- Workflow rápido original: `build-v17-responsivo.yml` (não recompila o Kodi).
- Execução: **44204393094**, concluída com sucesso.
- Passos: testes, auditorias 720p/1080p/4K, boot simulado, versão, alinhamento,
  `apksigner` conferindo v1/v2/v3 e as duas ABIs, release.
- Commit que gerou o APK: `77ee8c0`.

## Instalação

Não houve teste em aparelho físico neste ambiente. A tentativa de emulador
ARM64 no GitHub Actions não concluiu o boot (runner sem aceleração ARM), então
não há resultado de instalação a declarar. A validação do arquivo é a do CI:
ZIP íntegro, `zipalign` OK, assinatura v1/v2/v3 e ambas as ABIs.

Se este APK — que é o mesmo formato v1/v2/v3 das versões anteriores — ainda for
recusado, a causa não é mais assinatura/ABI/identidade. Nesse caso o código do
`adb install -r` é o único dado que fecha o diagnóstico (`INSTALL_FAILED_*`).
