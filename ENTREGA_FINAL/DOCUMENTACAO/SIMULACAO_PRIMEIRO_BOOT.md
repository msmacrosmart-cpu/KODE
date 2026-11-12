# Simulação de primeiro boot — validação da Home (SMARTEDTV)

Executado por `tools/kodi/simulate-first-boot.py`. Cada passagem monta o perfil semeado do APK base, roda o bootstrap real (repair, favoritos, performance, skin/nós), instala a skin do repositório como add-on de sistema e executa **o add-on real** para cada nó da Home.

## Resultado por passagem

| Passagem | Checks | Falhas | Resultado |
|---|---|---|---|
| 1 | 26 | 0 | OK |
| 2 | 22 | 0 | OK |
| 3 | 22 | 0 | OK |

## Rotas executadas (última passagem)

| Nó | Item da skin | Rota | Itens | Amostra |
|---|---|---|---|---|
| 9200 | 9200 | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais&nam` | 1 | PLUTO TV |
| 9201 | 9201 | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu&nam` | 5 | ● PESQUISE POR FILMES, CATEGORIA: GÊNEROS, CATEGORIA: LANÇAMENTOS |
| 9202 | 9202 | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23series_menu&nam` | 2 | ●● PESQUISAR SÉRIES, ●● TODAS SÉRIES |
| btn-9010 | TV ao vivo | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais&nam` | 0 | mesma rota de outro botão |
| btn-9011 | Filmes | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu&nam` | 0 | mesma rota de outro botão |
| btn-9012 | Séries | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23series_menu&nam` | 0 | mesma rota de outro botão |
| btn-9022 | Brazuca Play | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=0&name=Brazuca%20Play&ico` | 10 | ● FAVORITOS, ● TV AO VIVO, ● FILMES |

## Checks por passagem

### Passagem 1
- [OK] bootstrap sem exceção — None
- [OK] ponto de partida: skin.estuary (semeada pelo APK) — guisettings inicial sem skin.estuary
- [OK] reparo do Brazuca Play ok — ['plugin.video.BrazucaPlay.Matrix', 'script.module.certifi', 'script.module.chardet', 'script.module.idna', 'script.module.kodi-six', 'script.module.requests', 'script.module.simplejson', 'script.module.six', 'script.module.urllib3']
- [OK] 100% dos atalhos gravados — total=10
- [OK] skin SMARTEDTV ativa — {"skin": "skin.novatv", "changed": true, "installed": true}
- [OK] skin aplicada de fato — installed=True changed=True
- [OK] nós da Home ligados às rotas — []
- [OK] guisettings aponta para skin.novatv
- [OK] favourites.xml com 10 atalhos — total=10
- [OK] atalho TV ao vivo aponta para mode=21
- [OK] atalho Filmes aponta para mode=27
- [OK] atalho Séries aponta para mode=27
- [OK] Home.xml da skin encontrado
- [OK] Home tem os 4 botões da barra + nós — botões=['9010', '9011', '9012', '9013', '9014', '9015', '9016', '9018', '9022', '9061', '9062', '9063', '9064', '9065', '9066', '9067', '9069', '9091', '9092', '9093', '9094', '9099', '9101', '9102', '9103', '9104', '9105', '9106', '9107', '9109']
- [OK] Home tem as 3 linhas de conteúdo — linhas=['9200', '9201', '9202']
- [OK] linha 9200 usa a rota #menu_canais — plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=#menu_canais&name=TV ao vivo&iconima
- [OK] linha 9201 usa a rota #filmes_menu — plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=#filmes_menu&name=Filmes&iconimage=D
- [OK] linha 9202 usa a rota #series_menu — plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=#series_menu&name=Séries&iconimage=D
- [OK] 9200 (9200) devolve itens do addon — itens=1 erro=None
- [OK] 9201 (9201) devolve itens do addon — itens=5 erro=None
- [OK] 9202 (9202) devolve itens do addon — itens=2 erro=None
- [OK] btn-9013 (Novelas) devolve itens do addon — itens=2 erro=None
- [OK] btn-9014 (Animes) devolve itens do addon — itens=2 erro=None
- [OK] btn-9015 (Doramas) devolve itens do addon — itens=2 erro=None
- [OK] btn-9016 (Desenhos) devolve itens do addon — itens=2 erro=None
- [OK] btn-9022 (Brazuca Play) devolve itens do addon — itens=10 erro=None

### Passagem 2
- [OK] bootstrap sem exceção — None
- [OK] ponto de partida: skin.estuary (semeada pelo APK) — guisettings inicial sem skin.estuary
- [OK] reparo do Brazuca Play ok — ['plugin.video.BrazucaPlay.Matrix', 'script.module.certifi', 'script.module.chardet', 'script.module.idna', 'script.module.kodi-six', 'script.module.requests', 'script.module.simplejson', 'script.module.six', 'script.module.urllib3']
- [OK] 100% dos atalhos gravados — total=10
- [OK] skin SMARTEDTV ativa — {"skin": "skin.novatv", "changed": true, "installed": true}
- [OK] skin aplicada de fato — installed=True changed=True
- [OK] nós da Home ligados às rotas — []
- [OK] guisettings aponta para skin.novatv
- [OK] favourites.xml com 10 atalhos — total=10
- [OK] atalho TV ao vivo aponta para mode=21
- [OK] atalho Filmes aponta para mode=27
- [OK] atalho Séries aponta para mode=27
- [OK] Home.xml da skin encontrado
- [OK] Home tem os 4 botões da barra + nós — botões=['9010', '9011', '9012', '9013', '9014', '9015', '9016', '9018', '9022', '9061', '9062', '9063', '9064', '9065', '9066', '9067', '9069', '9091', '9092', '9093', '9094', '9099', '9101', '9102', '9103', '9104', '9105', '9106', '9107', '9109']
- [OK] Home tem as 3 linhas de conteúdo — linhas=['9200', '9201', '9202']
- [OK] linha 9200 usa a rota #menu_canais — plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=#menu_canais&name=TV ao vivo&iconima
- [OK] linha 9201 usa a rota #filmes_menu — plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=#filmes_menu&name=Filmes&iconimage=D
- [OK] linha 9202 usa a rota #series_menu — plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=#series_menu&name=Séries&iconimage=D
- [OK] 9200 (9200) devolve itens do addon — itens=1 erro=None
- [OK] 9201 (9201) devolve itens do addon — itens=5 erro=None
- [OK] 9202 (9202) devolve itens do addon — itens=2 erro=None
- [OK] btn-9022 (Brazuca Play) devolve itens do addon — itens=10 erro=None

### Passagem 3
- [OK] bootstrap sem exceção — None
- [OK] ponto de partida: skin.estuary (semeada pelo APK) — guisettings inicial sem skin.estuary
- [OK] reparo do Brazuca Play ok — ['plugin.video.BrazucaPlay.Matrix', 'script.module.certifi', 'script.module.chardet', 'script.module.idna', 'script.module.kodi-six', 'script.module.requests', 'script.module.simplejson', 'script.module.six', 'script.module.urllib3']
- [OK] 100% dos atalhos gravados — total=10
- [OK] skin SMARTEDTV ativa — {"skin": "skin.novatv", "changed": true, "installed": true}
- [OK] skin aplicada de fato — installed=True changed=True
- [OK] nós da Home ligados às rotas — []
- [OK] guisettings aponta para skin.novatv
- [OK] favourites.xml com 10 atalhos — total=10
- [OK] atalho TV ao vivo aponta para mode=21
- [OK] atalho Filmes aponta para mode=27
- [OK] atalho Séries aponta para mode=27
- [OK] Home.xml da skin encontrado
- [OK] Home tem os 4 botões da barra + nós — botões=['9010', '9011', '9012', '9013', '9014', '9015', '9016', '9018', '9022', '9061', '9062', '9063', '9064', '9065', '9066', '9067', '9069', '9091', '9092', '9093', '9094', '9099', '9101', '9102', '9103', '9104', '9105', '9106', '9107', '9109']
- [OK] Home tem as 3 linhas de conteúdo — linhas=['9200', '9201', '9202']
- [OK] linha 9200 usa a rota #menu_canais — plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=#menu_canais&name=TV ao vivo&iconima
- [OK] linha 9201 usa a rota #filmes_menu — plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=#filmes_menu&name=Filmes&iconimage=D
- [OK] linha 9202 usa a rota #series_menu — plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=#series_menu&name=Séries&iconimage=D
- [OK] 9200 (9200) devolve itens do addon — itens=1 erro=None
- [OK] 9201 (9201) devolve itens do addon — itens=5 erro=None
- [OK] 9202 (9202) devolve itens do addon — itens=2 erro=None
- [OK] btn-9022 (Brazuca Play) devolve itens do addon — itens=10 erro=None

## Limite do ambiente

Este sandbox não tem KVM, `adb`, `emulator`, `java` nem acesso ao repositório do SDK Android (`dl.google.com`), então um AVD real não pode ser iniciado aqui. A simulação acima usa o **perfil semeado real**, a **skin real do repositório** e o **add-on real instalado no perfil**, com os mesmos parâmetros que a skin passa ao Kodi — é o mais próximo de um emulador que o ambiente permite.
