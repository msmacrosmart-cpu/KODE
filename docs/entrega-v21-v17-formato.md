# SMARTEDTV 1.0.91 (v21) — mesmo formato da v17 que instalou

A v17 (`1.0.87 / 2103073`, APK universal, v1+v2+v3) instalou. A v21 usa
**exatamente o mesmo pipeline de release da v17** (commit `070cc08`), sobre o
mesmo APK base v16, sem recompilar o Kodi, e traz todas as edições posteriores.

## APK

https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.91-instalacao-v21/SMARTEDTV-atual-v21-instalacao-universal.apk

- Tamanho: **285.488.379 bytes**
- SHA-256: `b55d54ccff19acffcdab4bd20f90291b442acd2a3bc485dfc9fbcdabf2f67854`
- Pacote: `smartedtv.full`
- Versão: **1.0.91 / versionCode 2103077**
- ABIs: `arm64-v8a` + `armeabi-v7a` no mesmo APK
- Assinatura: v1 + v2 + v3, certificado
  `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`
- minSdk 21, targetSdk 34, `debuggable=false`, sem `testOnly`

Release: https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.91-instalacao-v21

## Comparação com a v17 que instalou

| Item | v17 (instalou) | v21 |
|---|---|---|
| Pipeline | `070cc08` | mesmo arquivo, só versão/tag |
| Base | APK universal v16 | APK universal v16 |
| ABI | arm64 + armv7 | arm64 + armv7 |
| Assinatura | v1+v2+v3 | v1+v2+v3 |
| Certificado | `855de171...` | `855de171...` |
| Tamanho | 285.488.387 B | 285.488.379 B |
| Versão | 1.0.87 / 2103073 | 1.0.91 / 2103077 |

A diferença de 8 bytes é conteúdo de addon/skin; não há mudança de pacote,
assinatura, ABI ou formato de APK.

## Build

- Workflow: `build-v17-responsivo.yml` (pipeline rápido, sem compilar Kodi).
- Execução: **44206293586**, sucesso.
- Commit do APK: `5566449`.
- Passos: testes, auditoria responsiva, boot simulado, versão, alinhamento,
  assinatura com a chave, imagens e release.

## Instalação

Não houve teste em aparelho físico nesta rodada. O que está verificado no CI:
ZIP íntegro, `zipalign`, assinatura v1+v2+v3, as duas ABIs, manifesto
1.0.91/2103077 e boot simulado. A v17 equivalente instalou no aparelho do
relato; a v21 preserva esse mesmo formato.

Se o Downloader falhar antes de abrir o instalador, teste o mesmo link em um
navegador (Chrome) ou baixe no PC e transfira. Se o instalador abrir e recusar,
o código `adb install -r` é o dado que fecha a causa.
