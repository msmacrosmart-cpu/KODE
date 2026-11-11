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
