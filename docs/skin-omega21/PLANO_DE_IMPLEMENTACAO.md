# Plano de implementação

Regra: preservar o que funciona; corrigir só o necessário; não reescrever a skin. Nenhuma tela IDÊNTICA/COMPATÍVEL será reescrita. Nenhuma funcionalidade será removida sem justificativa.

## Ciclo 1 — feito (agente anterior, arquivos no Dropbox)

- Auditoria estática da skin (XML, includes, texturas, IDs, paleta).
- Preview HTML de 11 telas + 6 diálogos (responsivo, teclado, tela cheia, só cinzas).
- Relatórios `AUDITORIA_PROJETO.md`, `COBERTURA_TELAS_KODI.md`, `CHANGELOG.md`.
- ZIP `SKIN_KODI_OMEGA21.zip` (512.732 B) empacotando a skin existente, sem alterar XML.
- Decisão: responsividade no Kodi via escalonamento 1920×1080 + scrollbar/grouplist; no HTML via grid fluida.

## Ciclo 2 — feito nesta entrega (2026-11-11)

1. **Preview de 44 telas** (`ENTREGA_FINAL/PREVIEW_KODI.html`, 28.900 B, arquivo único, sem dependências externas): 44 telas numeradas como no site, navegação por ← →/↑ ↓/Enter/Esc, hash, tela cheia, modais (Detalhes, Contexto, Confirmação, Teclado, Progresso, Notificação, Áudio, Legendas, Info, Marcadores, Energia). TV/Filmes/Séries como telas principais (06/25/07) com as rotas reais da ponte. Paleta e foco idênticos ao Design System; verificado por script (sem URLs externas, hex só em cinzas, JS válido).
2. **Documentação completa** (esta pasta, 10 arquivos): análise, mapa, design system, inventário, comparativo, plano, validação, performance, build e configuração.
3. **Build reproduzível do ZIP** (`tools/kodi/build-skin-zip.py`): estrutura `skin.novatv/` no topo, exclusão de `README.md`/`docs/`, validação de estrutura + XML. Saída: `ENTREGA_FINAL/SKIN_KODI_OMEGA21.zip` (136 arquivos, 518.427 B, SHA-256 `ab294a22…157deb`).
4. **Validação estática completa**: 53 testes (`python3 -m unittest discover -s tests`) + checagens de preview/ZIP (ver `RELATORIO_VALIDACAO_VISUAL.md`).
5. **Skin XML inalterada**: nenhum arquivo em `kodi/skin.novatv/xml/` foi modificado. Motivo: auditoria não encontrou erro estrutural; botões sem `<onclick>` são tratados pelo Kodi por ID; layouts dos cards são travados por hash. Alterações arriscadas (ex.: visibilidade `IsEmpty` dos widgets) ficam como pendência documentada, exigindo Kodi real.

## Ciclo 3 — pendente (exige Kodi Omega 21 real)

- Instalar `SKIN_KODI_OMEGA21.zip` + ponte + Brazuca 2.1.4 em Kodi 21.3 (Android/PC), conferir `kodi.log`, navegar por controle remoto/teclado/mouse/toque.
- Conferir IDs das janelas `sync` (`JANELAS.md`) no Estuary instalado; corrigir divergências.
- Comparar visualmente cada tela com as referências (capturas 16:9) e atualizar `COMPARATIVO_TELAS.md`.
- Avaliar visibilidade `!Container(id).IsEmpty` nos grupos de widgets (9200–9280) para ocultar fileiras vazias sem flicker.
- Avaliar layouts específicos de temporada/episódio, álbum e artista somente se houver referência visual.
- Medir tempos de abertura e uso de memória em TV Box/TV Stick de baixo desempenho.

## O que não será feito

- Não reescrever a skin inteira; não trocar layouts COMPATÍVEIS por “aproximados”.
- Não fabricar Top 10, eventos de Esportes, PVR, clima ou catálogo: sem fonte real, a tela fica vazia/oculta por condição.
- Não gerar APK: o projeto é skin ZIP + ponte, não aplicativo Android (ver `RELATORIO_BUILD_RELEASE.md`).
- Não alterar o site de referência.
