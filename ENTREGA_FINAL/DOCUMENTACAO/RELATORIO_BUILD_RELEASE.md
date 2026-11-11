# Relatório de build Release

Data: 2026-11-11.

## 1. Arquitetura do projeto

O projeto **não** é um aplicativo Android compilável. É uma **skin Kodi em ZIP** (`kodi/skin.novatv`) + **ponte de conteúdo** (`kodi/addons/plugin.video.smarted`) que encaminha para o Brazuca Play 2.1.4. O repositório também contém ferramentas de **reempacotamento do APK do Kodi** (`tools/kodi/build-smarted-test.sh`, etc.), que preservam o motor Kodi e não compilam o Kodi do código-fonte — fora do escopo desta entrega de skin.

**Consequência (Etapa 13): não existe `APK_RELEASE.apk` próprio a gerar.** Nenhum APK foi criado, modificado ou simulado nesta etapa. Gerar um APK artificial ou modificar o Kodi original para “simular” a skin violaria a regra do projeto.

## 2. Build da skin (executado)

- Ferramenta: `tools/kodi/build-skin-zip.py` (Python 3.11.2, stdlib `zipfile`).
- Entrada: `kodi/skin.novatv/` (138 arquivos). Saída: `ENTREGA_FINAL/SKIN_KODI_OMEGA21.zip`.
- Estrutura: pasta única `skin.novatv/` no topo do ZIP, com `skin.novatv/addon.xml` (exigência do Kodi). Excluídos do ZIP: `README.md` e `docs/` (desenvolvimento), `__pycache__`/`*.pyc`.
- Resultado: **136 arquivos, 518.427 bytes, SHA-256 `ab294a22a623e3601c1aff5123c0ea1ca25111e181170dfde1130af136157deb`**. Validação `--check`: estrutura + todos os XML válidos.
- Comparação: ZIP anterior no Dropbox tinha 512.732 B (mesma skin, empacotamento ad-hoc). Diferença explicada por conteúdo/exclusões e nível de compressão; ambas contêm a mesma skin (XML inalterado).

## 3. Configuração Release

- `xbmc.gui 5.17.0`, 1920×1080, `debugging="false"`, `effectslowdown 1.0` (`addon.xml`).
- Sem R8/ProGuard/Shrink Resources (não se aplicam a skin XML).
- Sem assinatura (ZIP de skin não é assinado; instalação via Complementos > Instalar de zip).
- Ver `CONFIGURACAO_RELEASE.md` para versões e comandos.

## 4. Problemas e testes

- Problemas: nenhum erro de build. Limitação: sem Kodi real, a instalação não foi testada (ver `RELATORIO_VALIDACAO_VISUAL.md`).
- Testes: 53 testes unitários OK (6 ignorados por Java/Pillow) + `--check` do ZIP.
- Tamanho do APK: **N/A** (sem aplicativo). Tamanho original/final do APK não se aplica.

## 5. Como repetir o build

```sh
python3 tools/kodi/build-skin-zip.py
python3 tools/kodi/build-skin-zip.py --check
# Instalar no Kodi 21: Complementos > Instalar de arquivo zip > SKIN_KODI_OMEGA21.zip
# Depois: Interface > Skin > Nova TV. Instalar também a ponte + Brazuca 2.1.4 para TV/Filmes/Séries.
```

## 6. Entrega

`ENTREGA_FINAL/` contém `SKIN_KODI_OMEGA21.zip`, `PREVIEW_KODI.html` e `DOCUMENTACAO/` (cópias dos 10 arquivos desta pasta). `APK_RELEASE.apk` **não** está presente por não haver aplicativo Android real. `RECURSOS_PREVIEW/` foi omitido porque o preview é arquivo único autocontido (sem CSS/JS/imagens externas) — criar pasta vazia violaria a regra de não preencher estrutura.

## 6. APK release 1.0.23 (executado em 2026-11-11)

Pedido posterior do cliente: gerar o APK final release mantendo o tamanho do APK anterior. Executado sobre a base publicada `v1.0.22-smarted-arm64-redownload` (`SMARTED-TV-v1.0.22-arm64.apk`, 238.196.801 B), sem recompilar o Kodi.

- Base obtida por `.github/private-apk-chunks.json` (29 blocos Git LFS-free versionados) e conferida byte a byte: SHA-256 `8b58ee878aa0356a268bfa19bb891b079233370c9fd367d54a9a425bcd6d9b2e`.
- `tools/kodi/build-release-apk.py`: versão `1.0.22 (2103008)` → `1.0.23 (2103009)`; skin (138 arquivos) e ponte (15 arquivos) substituídas pelas versões do repositório; entradas em `assets/system/addon-manifest.xml` garantidas; assinaturas antigas removidas. Demais 6.963 entradas preservadas (libs nativas, `classes.dex`, perfil/backup).
- `tools/kodi/align-apk.py` + `apksigner` (v1+v2+v3) com `smarted-tv-test.jks`, alias `smarted-tv-test`.
- Validação executada (log do run 42936327651, todas as etapas verdes): assinatura `Verifies` nos 3 esquemas; certificado SHA-256 `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`; identidade `org.xbmc.kodi` / `SMARTED-TV` / `1.0.23` (2103009); 46 bibliotecas + `classes.dex` idênticos à base; skin e ponte idênticas ao repositório.
- Resultado: **238.196.800 bytes** (192 B menor que a 1.0.22 — mesma ordem de tamanho), SHA-256 `2d8c085ec6555c2724d4024a0cba6efc97f73b6e9acf09a96300787bb4ae3ce1` (digest confirmado na API do release).
- Release: `v1.0.23-smarted-arm64`, asset `SMARTED-TV-v1.0.23-arm64.apk`, publicado (não draft).
- Link de download: `https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.23-smarted-arm64/SMARTED-TV-v1.0.23-arm64.apk` (repositório privado: exige sessão GitHub autorizada; sem autenticação retorna 404).
- Segurança: o link público temporário da keystore usado pelo runner foi revogado após o build.

**Limitação registrada:** não houve instalação nem execução em dispositivo/emulador nesta etapa; a validação acima é estática (assinatura, identidade, integridade de motor e conteúdo). A aprovação visual/funcional depende da instalação pelo cliente.
