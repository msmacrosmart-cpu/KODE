# SMARTEDTV 1.0.57 (arm64-v8a)

Correções visuais pedidas: painéis escuros e Home com duas fileiras sem sobreposição.

## 1. Painel branco eliminado

- A Bingie pinta os painéis com `Skin.String(...)` direto em `colordiffuse`. O
  valor de fábrica de `HomeWidgetsBorderColor` é a palavra `None`, que não é um
  ARGB válido — o Kodi não converte e cai no **branco**. Todas as listas que
  abrem com a "view Bingie" ativa (listagem de pastas do addon, diálogos de
  pasta/arquivo) herdavam esse branco.
- O overlay da Home agora fixa no boot: `GeneralPanelsColor`,
  `ViewDetailsPanelColor`, `HomeWidgetsBorderColor` e `SideBladePanelColor` em
  **#CC121212** (cinza-escuro translúcido); `HeaderPanelColor` e
  `FooterPanelColor`, que a skin deixa como `None`, viram `00FFFFFF`
  (transparente, nunca branco).
- Nenhuma textura `.png` foi alterada.

## 2. Home com duas fileiras e respiro

- Antes: cada botão tinha dois widgets (lista do Brazuca + rota de favoritos);
  a Home empilhava as duas fileiras com `<itemgap>2</itemgap>`, cortando a de
  baixo — o efeito de "lançamentos duplicados/sobrepostos".
- Agora: **um widget por categoria**; o botão **Home** tem exatamente duas
  fileiras (Lançamentos/Filmes em cima, Séries embaixo); `<itemgap>` 2 → **36 px**
  (`xml/IncludesHomeBingie.xml`); estilo `landscape` (212 px por fileira), o único
  em que 2 × 212 + 36 = 460 px cabem inteiros na área de carrosséis em 1080p.

## Build

`python3 tools/kodi/bingie-overlay.py <skin-bingie> kodi/skin.smartedtv.bingie`
regenera os três arquivos do overlay; `tools/kodi/static-check.py` valida o XML.
Release publicada pelo workflow `build-release-apk.yml` com
`--to-version 1.0.57 --to-code 2103043`.
