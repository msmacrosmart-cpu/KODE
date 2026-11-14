SMARTEDTV 1.0.57 (ARM64, Kodi 21.3-Omega) — correções visuais: painéis escuros e Home com duas fileiras sem sobreposição.

CORREÇÃO 1 — PAINEL BRANCO NAS LISTAS (agora cinza-escuro)
- Causa: a Bingie pinta os painéis com Skin.String(...) usado direto em
  colordiffuse. O valor de fábrica de HomeWidgetsBorderColor é a palavra "None",
  que não é um ARGB válido — o Kodi não consegue converter e cai no branco.
  Toda lista que abre com a "view Bingie" ativa (listagem de pastas do addon,
  diálogos de pasta/arquivo, seleção de add-on) herdava esse branco.
- Correção: o overlay da Home fixa, no boot, os painéis em cinza-escuro
  translúcido #CC121212 (GeneralPanelsColor, ViewDetailsPanelColor,
  HomeWidgetsBorderColor, SideBladePanelColor) e zera os painéis que a skin
  deixa como "None" (HeaderPanelColor e FooterPanelColor viram 00FFFFFF, ou
  seja, sem barra pintada — e nunca branco). Só reescreve quando o valor está
  diferente, para não escrever em disco a cada carga da Home.
- Nenhuma textura foi alterada: arquivos .png da skin seguem intactos.

CORREÇÃO 2 — FILEIRAS DUPLICADAS NA HOME (agora 2 fileiras, com respiro)
- Causa: cada botão do menu gerava dois widgets (lista do Brazuca + rota de
  favoritos). A Home empilha os widgets do botão focado num grouplist com
  <itemgap>2</itemgap>: as duas fileiras ficavam coladas e a de baixo era
  cortada pelo rodapé — o efeito visual de "lançamentos duplicados/sobrepostos".
- Correção:
  * um widget por categoria (Filmes, Séries, Doramas, Novelas, Animes,
    Desenhos) — sem fileira repetida;
  * botão Home com exatamente duas fileiras: Lançamentos/Filmes em cima e
    Séries embaixo;
  * <itemgap> do grouplist de widgets: 2 → 36 px de respiro vertical
    (overlay xml/IncludesHomeBingie.xml);
  * estilo de widget fixado em landscape (212 px por fileira), o único em que
    duas fileiras cabem inteiras na área de carrosséis em 1080p
    (2 × 212 + 36 = 460 px).
- Os botões continuam abrindo a listagem final do Brazuca Play (mode=1), sem
  menu intermediário e sem chamar addons/playlists ausentes.

RESTANTE IGUAL À 1.0.55/1.0.56
- White-label SMARTEDTV (rótulo do app no resources.arsc, textos e diálogos).
- Bingie Mod 2.2.3 como skin padrão (preto/branco/cinza) + skin clássica
  embarcada como alternativa.
- Vikings Repo (vkkodi.repo 3.00) registrado no build e no payload do
  bootstrap; plugin.video.BrazucaPlay.Matrix 2.1.4 embarcado.
- TV ao vivo em mode=21 (lista de canais); demais categorias em mode=1.

ASSINATURA E ATUALIZAÇÃO
- Mesma chave smarted-tv-test (SHA-256 855de171...): atualiza por cima da
  1.0.56, não atualiza o Kodi oficial. versionCode 2103043.
