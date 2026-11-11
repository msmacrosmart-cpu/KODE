# Relatório de validação visual e funcional

Data: 2026-11-11. Ambiente: Linux x86_64, Python 3.11.2, Node v22.22.3. **Sem Kodi real** — nada abaixo substitui teste em Kodi 21.

## 1. Testes executados (resultados reais)

- `python3 -m unittest discover -s tests` → **53 testes, OK (6 ignorados por falta de Java/Pillow)**. Inclui:
  - `test_skin_audit`: includes resolvidos, texturas estáticas presentes, sem IDs duplicados por arquivo, ações do hero (2 onclick) e controles do OSD/marcadores.
  - `test_original_home_design`: hashes dos layouts dos cards 9200–9230 (design original preservado).
  - `test_novatv_integration`: XML parse (≥94 arquivos), controles de ajustes Kodi 21, teclado, seleção, rotas restritas/desbloqueio, Startup, Settings, paleta, rotas Brazuca, staging de backup/ponte.
  - `test_brazuka_*`, `test_channel_*`, `test_widget_cache`: catálogo, busca, favoritos, cache — sem dados fabricados.
- Auditoria manual por script: 93 XMLs parseados, 6 includes definidos, 0 texturas ausentes, pt_BR/en_GB com 42 strings cada.
- Preview: 44 telas confirmadas por contagem, JS válido (`node --check`), HTML parse OK, 0 URLs externas, hex apenas em cinzas (`#000,#0d0d0d,#181818,#1f1f1f,#262626,#2b2b2b,#333,#3a3a3a,#3d3d3d,#555,#a6a6a6,#d9d9d9,#f2f2f2,#fff`), TV/Filmes/Séries + 5 subcategorias presentes.
- ZIP: `tools/kodi/build-skin-zip.py --check` → estrutura `skin.novatv/addon.xml` no topo + todos os XML válidos. 136 arquivos, 518.427 B.

## 2. O que foi verificado visualmente

- Preview aberto por leitura de código + validação de estrutura (não por captura de tela). Navegação por teclado, hash, modais e responsividade (grid fluida, palco 16:9, overflow) foram revisados no código; o arquivo é autocontido e funciona offline.
- Paleta do preview confere com `colors/defaults.xml`; foco branco/preto confere com `Home.xml`/`Includes.xml`.

## 3. O que NÃO foi verificado (limitações explícitas)

- Renderização 1080p no Kodi, navegação por controle remoto, reprodução de streams, PVR, clima, jogos e busca global.
- Fidelidade pixel a pixel às 44 referências (sem capturas do site; ver `MAPA_REFERENCIAS_VISUAIS.md`).
- Desempenho em TV Box/TV Stick (sem dispositivo).
- Instalação do ZIP no Kodi (sem ambiente Kodi).

## 4. Segunda auditoria (comparativo atualizado)

- Nenhuma tela aplicável foi reclassificada para melhor sem evidência nova. Classificações em `COMPARATIVO_TELAS.md` permanecem por presença funcional + estrutura.
- Critério de aprovação **não** atingido para “fidelidade visual comprovada”: pendente de capturas e Kodi real (Ciclo 3 do `PLANO_DE_IMPLEMENTACAO.md`). O que se aprova nesta etapa é integridade estrutural, contratos de teste e preview navegável.

## 5. Como repetir

```sh
python3 -m unittest discover -s tests
python3 tools/kodi/build-skin-zip.py
python3 tools/kodi/build-skin-zip.py --check
# Abrir ENTREGA_FINAL/PREVIEW_KODI.html no navegador (duplo clique ou servidor local).
```
