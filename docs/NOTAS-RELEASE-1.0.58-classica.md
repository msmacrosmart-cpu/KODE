SMARTED-TV 1.0.58 (ARM64, Kodi 21) — LINHA CLASSICA (sem Bingie), a mesma da 1.0.47.

Base: APK 1.0.47 publicado em v1.0.47-classica (SHA-256 70f5429f…e338a3),
reempacotado sem recompilar o Kodi. Motor (libkodi.so), dex, perfil semeado,
plugin.video.smarted e bootstrap seguem byte a byte como estavam.

CORRECAO 1 — PAINEL BRANCO NA LISTAGEM DE PASTAS
- A view de lista (MyVideoNav, lista 50) desenhava o fundo de cada linha com a
  textura pb_rounded.png — cinza-clara (244,244,244) — tingida de BRANCO:
  B3FFFFFF na linha normal e FFFFFFFF na linha focada. Resultado: a lista de
  pastas/conteudos virava um bloco claro no meio da interface escura.
- Agora: linha normal #CC121212 (cinza-escuro translucido) e linha focada
  #FF1E1E1E (cinza-escuro solido). Nenhuma textura foi alterada.

CORRECAO 2 — FILEIRAS DA HOME SOBREPOSTAS
- O layout aurora (o padrao) tinha tres fileiras em posicoes erradas:
  "Lancamentos" (lista 9201) em y=800 com 120 px de altura, "Filmes" (lista 9202)
  em y=700 com 200 px — as duas se sobrepunham — e "Series" (lista 9203) em
  y=1180, ou seja, fora da tela de 1080p.
- Agora sao exatamente duas, com respiro:
    Lancamentos / Filmes  -> rotulo em y=540, fileira em y=570 (194 px)
    Series                -> rotulo em y=792, fileira em y=822 (194 px)
    28 px livres entre o fim da fileira de cima (764) e o rotulo de baixo (792)
- A fileira "Filmes" duplicada (9202) foi removida; a de cima continua
  alimentando o HERO (titulo, sinopse e fanart leem Container(9201)) e usa o
  mesmo layout de capa 16:9 da fileira de baixo.
- Foco: cima -> baixo e baixo -> cima ligados direto entre 9201 e 9203.

SKIN
- skin.novatv (a skin padrao do aparelho) agora 1.0.18 — o numero novo faz o
  Kodi descartar a skin compilada em cache da versao anterior.
- Uma unica copia da skin no APK (nao ha duplicata skin.smartedtv.classic nesta
  linha), por isso o arquivo continua na faixa dos ~240 MB.

ASSINATURA E ATUALIZACAO
- Mesma chave smarted-tv-test (SHA-256 855de171…): instala por cima da 1.0.47 e
  da 1.0.56/1.0.57, nao instala por cima do Kodi oficial.
- versionName 1.0.58 / versionCode 2103044 (maior que 2103033 da 1.0.47, entao
  atualiza sem desinstalar e sem perder o perfil).
