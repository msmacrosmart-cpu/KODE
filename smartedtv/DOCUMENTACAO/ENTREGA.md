# Entrega

Índice do que está sendo entregue, mapeado 1:1 nos itens A–D do pedido.

## A. APK SMARTEDTV

| Item | Onde |
|---|---|
| APK compilado (arm64-v8a) | `smartedtv/build/out/SMARTEDTV-21.4-arm64-v8a.apk` |
| SHA-256 | `smartedtv/build/out/SMARTEDTV-21.4-arm64-v8a.apk.sha256` |
| Artefato da CI | `smartedtv-apk-arm64` no run listado em `RESULTADO-BUILD.md` |
| Verificação automática | `smartedtv/tools/verify-apk.py` (26 checagens) |

Características verificadas no APK:

- Kodi 21.3-Omega compilado do código-fonte (`libkodi.so` real, arm64-v8a).
- Nome exibido **SMARTEDTV** no launcher/Android TV.
- Splash **SMARTEDTV** (nativa do Android e da GUI).
- Ícones, banner e marca da Home com o selo oficial.
- `applicationId` **org.xbmc.kodi** preservado.
- **Sem** Brazuka Play, **sem** add-ons de conteúdo, **sem** skin Nova TV/Titan.
- **Sem** perfil pré-configurado; playlists/fontes são configuradas pelo usuário.

## B. Projeto de build

```
smartedtv/
├── assets/brand/logo-oficial.jpg      arte oficial da marca (1600×1600)
├── assets/brand/mark.png              selo recortado da arte oficial
├── out/media/*                        recursos de identidade (gerados, versionados)
├── out/android-packaging-media/*      ícones de launcher e banner
├── tools/setup-build-env.sh           prepara JDK/SDK/NDK (versões do Kodi 21.3)
├── tools/make-brand-assets.py         gera os recursos a partir da arte oficial
├── tools/patch-source.py              aplica a marca no código do Kodi (idempotente)
├── tools/build-apk.sh                 compila + empacota + assina + verifica
├── tools/verify-apk.py                verificação estática do APK
├── tools/smoke-emulador.sh            instala e abre no emulador, coletando provas
└── build/                             (gerado) — não versionado
```

Workflows:

- `.github/workflows/smartedtv-build-source.yml` — build real do código-fonte.
- `.github/workflows/smartedtv-emulator-test.yml` — instalação + execução.

## C. Documentação

| Arquivo | Conteúdo |
|---|---|
| `DOCUMENTACAO/AMBIENTE.md` | como o ambiente foi preparado; ferramentas, versões, dependências, configurações, comando de build, local do APK, limitações do sandbox |
| `DOCUMENTACAO/INSPECAO-DROPBOX.md` | inventário do Dropbox; comparação das versões; qual base foi escolhida e por quê; quais arquivos serviram de referência; o que foi ignorado |
| `DOCUMENTACAO/ALTERACOES.md` | lista completa e arquivo-por-arquivo das alterações de identidade |
| `DOCUMENTACAO/TESTES.md` | todos os testes executados, com resultado e o que não foi executado |
| `DOCUMENTACAO/RESULTADO-BUILD.md` | resultado do build real (run, duração, SHA-256, saída do verificador, saída do emulador) |
| `DOCUMENTACAO/RELATORIO-INTEGRIDADE.md` | preservado × removido × personalizado; limitações; situação de instalação e atualização |
| `README.md` (desta pasta) | visão geral e comandos rápidos |

## D. Relatório de integridade

`DOCUMENTACAO/RELATORIO-INTEGRIDADE.md`, com as seções:

1. Base utilizada.
2. O que foi preservado do Kodi original.
3. O que foi removido / não incluído.
4. O que foi personalizado.
5. Por que `APP_NAME` não foi renomeado (decisão técnica).
6. Instalação e atualização — o que é verdade.
7. Limitações encontradas.
8. Identificações residuais de "Kodi" (honestidade técnica).
9. Situação final.

## Resumo em uma frase

O APK é o **Kodi 21.3 real, compilado do código-fonte**, com a marca SMARTEDTV
aplicada nos textos e imagens de identificação, mantendo `org.xbmc.kodi`,
`libkodi.so`, o perfil `.kodi` e a compatibilidade de add-ons — e **sem** o
conteúdo de terceiros que existia antes.
