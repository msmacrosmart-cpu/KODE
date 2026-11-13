SMARTEDTV 1.0.56 (ARM64, Kodi 21.3-Omega) — white-label SMARTEDTV com VOD/IPTV já na Home.

IDENTIDADE
- Nome exibido no Android trocado para SMARTEDTV no string pool do resources.arsc
  (tool: tools/kodi/patch-resources-label.py). Só o texto muda: o pacote continua
  org.xbmc.kodi, e libkodi.so, classes.dex e o motor seguem byte a byte.
- Textos, títulos de diálogo, notificações e nomes de addon do projeto agora dizem
  SMARTEDTV em todo lugar (antes alternavam com "SMARTED-TV").

SKIN
- Skin padrão: Bingie Mod 2.2.3 (mod oficial do Bingie, inalterado na estrutura),
  agora em preto/branco/cinza (recolor-skin.py --skin bingie).
- Menu superior e barra lateral nativos da skin (skinshortcuts-mainmenu) mapeados
  para as rotas reais do addon de vídeo.
- skin.smartedtv.classic continua embarcada como alternativa em Ajustes > Aparência.

VIKINGS REPO
- repository addon baixado no build (tools/kodi/fetch-vikings-repo.py), injetado em
  assets/addons/ e registrado no addon-manifest.xml: o Kodi instala e ativa o
  repositório no primeiro boot, sem ação do usuário.
- O endereço divulgado (vkodi.net) está fora do ar desde dez/2025; o build usa o
  repositório oficial do time Vikings no GitHub (vikingsbuild/vikings.repo →
  vkkodi.repo 3.00, que aponta para a árvore "matrix", Kodi 19+).
- O zip do repositório vai também no payload do service.smarted.bootstrap, então o
  registro é refeito sem rede se o perfil perder o addon.
- Se plugin.video.BrazucaPlay.Matrix faltar, o bootstrap roda UpdateAddonRepos() +
  InstallAddon(plugin.video.BrazucaPlay.Matrix).

ADD-ON DE VÍDEO
- plugin.video.BrazucaPlay.Matrix 2.1.4 (zip publicado pelo próprio Vikings Repo)
  embarcado no payload do bootstrap: o reparo instala esse pacote quando o perfil
  semeado não trouxe o addon.
- Dependências verificadas no APK final: requests, urllib3, idna, certifi, chardet,
  six, kodi-six, simplejson e o cloudrequest embutido.

TELAS E WIDGETS
- TV ao vivo: mode=21 url=#todoscanais (lista de canais).
- Filmes, Séries, Novelas, Animes, Doramas e Desenhos: mode=1 com a base do próprio
  addon em base16(base64), igual ao addDir() — sem menu intermediário.
- Home: HERO + carrosséis dessas mesmas listas + linha de favoritos por categoria.
- script.skin.helper.widgets, themoviedb.helper e playlists inexistentes não são
  mais chamados (eram a origem do "GetDirectory – Error" no log).

LOG
- donate_consider do Brazuca silenciado; nav-check grava PASS/FALHA por botão em
  userdata/addon_data/service.smarted.bootstrap/smarted-nav-check.log.
- bootstrap grava também userdata/smarted-bootstrap.log com o resultado do reparo e
  a linha "vikings: repos=... plugin=... falhas=...".

ASSINATURA E ATUALIZAÇÃO
- Mesma chave smarted-tv-test (SHA-256 855de171...): atualiza por cima da 1.0.55,
  não atualiza o Kodi oficial. versionCode 2103042.
