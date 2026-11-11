# Configuração Release — skin.novatv

Arquivo único (a estrutura da Etapa 15 prevê `CONFIGURACAO_RELEASE/` como pasta; aqui é arquivo para não criar pasta vazia — o conteúdo é o mesmo).

## 1. Ambiente de build (medido)

| Ferramenta | Versão |
|---|---|
| SO | Linux x86_64 |
| Python | 3.11.2 (stdlib apenas para o build da skin) |
| Node | v22.22.3 (apenas para `node --check` do preview) |
| ZIP | `zipfile.ZIP_DEFLATED`, nível 9 |
| Kodi alvo | Omega 21.3 (`xbmc.gui 5.17.0`) |

## 2. Entrada e saída

- Entrada: `kodi/skin.novatv/` (138 arquivos, 1.235.406 B).
- Saída: `ENTREGA_FINAL/SKIN_KODI_OMEGA21.zip` (136 arquivos, 518.427 B, SHA-256 `ab294a22a623e3601c1aff5123c0ea1ca25111e181170dfde1130af136157deb`).
- Exclusões do ZIP: `README.md`, `docs/`, `__pycache__/`, `*.pyc`. Todo o resto é incluído com prefixo `skin.novatv/`.
- Script: `tools/kodi/build-skin-zip.py` (`--output`, `--check`).

## 3. Manifesto (`addon.xml`)

- `id="skin.novatv"`, `version="1.0.1"`, `name="Nova TV"`.
- `xbmc.gui 5.17.0`, resolução 1920×1080 16:9, `folder="xml"`, `debugging="false"`.
- Ícone `resources/icon.png`, fanart `resources/fanart.jpg`.
- Sem dependências obrigatórias de skin (a ponte Brazuca é dependência de conteúdo, não da skin em si).

## 4. Dependências de conteúdo (runtime, não build)

- `plugin.video.smarted` 0.2.0 (ponte, neste repositório).
- `plugin.video.BrazucaPlay.Matrix` 2.1.4 (provedor; instalado no perfil, não incluído no ZIP).
- Condicionais: PVR, serviço de clima, `script.globalsearch`, biblioteca do Kodi.

## 5. APK

Nenhum. Projeto é skin ZIP, não aplicativo Android (ver `RELATORIO_BUILD_RELEASE.md`). As ferramentas de reempacotamento de APK do Kodi em `tools/kodi/` não fazem parte deste build.

## 6. Comandos

```sh
python3 tools/kodi/build-skin-zip.py
python3 tools/kodi/build-skin-zip.py --check
python3 -m unittest discover -s tests
```
