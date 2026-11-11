# Navegação do Brazuca Play — comprovação da árvore original (v1.0.32)

Fonte de verdade: o próprio add-on instalado no perfil
(`addons/plugin.video.BrazucaPlay.Matrix/default.py`, v2.1.4). Nada foi
reimplementado na skin: cada atalho abre `ActivateWindow(10025, plugin://…)`,
ou seja, o Kodi executa o diretório do add-on e o D-pad/OK/Back, os menus
contextuais, a paginação, a busca e a ordenação continuam sendo os nativos.

## Entradas da skin (Home)

| Item | Ação | Nível que abre |
|---|---|---|
| **Brazuca Play** (nav, id 9022) | `plugin://plugin.video.BrazucaPlay.Matrix/?mode=0` | menu raiz completo do add-on |
| **TV ao vivo** (nav, 9010) | `mode=15&url=canais` | favoritos de canais (sincronizados) |
| **Filmes** (nav, 9011) | `mode=15&url=filmes` | favoritos de filmes |
| **Séries** (nav, 9012) | `mode=15&url=series` | favoritos de séries |
| **Novelas / Animes / Doramas / Desenhos** (9013–9016) | `mode=25/22/31/28` + `#…_menu` | pastas originais do add-on |
| **Add-ons** (topo, 9124) | `ActivateWindow(10040)` | navegador de add-ons (rota nativa) |
| **Favoritos** (nav, 9019) | `ActivateWindow(10060)` | favoritos do Kodi (10 atalhos do add-on) |

As três linhas da Home (9200/9201/9202) listam os mesmos favoritos do add-on em
formato de cartaz (leitura de `addon_data/plugin.video.BrazucaPlay.Matrix/favorites.dat`,
rota `favoritos-<categoria>` do `plugin.video.smarted`).

## Árvore executada de verdade (harness offline, perfil `/tmp/prof2`)

Comando: `python3 tests/kodi_plugin_stubs/run_plugin.py …` / dump com stub de
`xbmcgui`, exatamente os parâmetros que a skin passa.

```
mode=0                                   → 10 itens (menu raiz do add-on)
├── FAVORITOS                mode=15 (url vazia)     → pastas por categoria
├── TV AO VIVO               mode=21 #menu_canais
│   └── PLUTO TV             mode=21 #pluto_menu
│       └── 14 CATEGORIAS    mode=21 #plutotv_4 … #plutotv_15
├── FILMES                   mode=27 #filmes_menu
│   ├── PESQUISE POR FILMES  mode=20 #pesquisar_filmes      (busca nativa)
│   ├── CATEGORIA: GÊNEROS   mode=27 #filmes_por_generos_menu
│   │   └── AÇÃO … TERROR    mode=27 #movies_pages=…&nome.xml#1  (paginação)
│   ├── CATEGORIA: LANÇAMENTOS     mode=27
│   ├── CATEGORIA: ORDEM ALFABÉTICA mode=27 #movies_pages=…
│   └── CATEGORIA: TRILOGIA        mode=3  #trilogias_list
├── SÉRIES                   mode=27 #series_menu
│   ├── PESQUISAR SÉRIES     mode=20 #pesquisar_series
│   └── TODAS SÉRIES         mode=27
├── DESENHOS                 mode=28 #desenhos_menu
├── DORAMAS                  mode=31 #doramas_menu
├── ANIMES                   mode=22 #animes_menu
├── NOVELAS                  mode=25 #novelas_menu
├── CONFIGURAÇÕES            mode=4  (sem pasta)
└── VERIFICAR UPDATES        mode=4  #update
```

Níveis 2 e 3 conferidos nesta execução: `#pluto_menu` devolveu as 14 categorias
reais (Estilo de vida, Filmes, Infantil, Investigação, Música, Notícias,
Novelas, Reality, Retrô, South Park, Séries, TV Brasileira, …) e
`#filmes_por_generos_menu` devolveu os gêneros com paginação
(`#movies_pages=…`). As listas de canais/filmes em si dependem da rede do
aparelho — sem rede o add-on mostra a notificação dele, como sempre fez.

## Comparação com a instalação de referência

O `favourites.xml` semeado no perfil (que veio do aparelho em uso) aponta para
exatamente as mesmas rotas usadas agora:

```
mode=21 url=#menu_canais      (TV AO VIVO)
mode=27 url=#filmes_menu      (FILMES)
mode=27 url=#series_menu      (SÉRIES)
mode=28 url=#desenhos_menu    (DESENHOS)
mode=31 url=#doramas_menu     (DORAMAS)
mode=22 url=#animes_menu      (ANIMES)
mode=25 url=#novelas_menu     (NOVELAS)
```

Nenhuma rota foi inventada e nenhuma foi removida: a skin só escolhe qual
diretório abrir. O que a v1.0.32 acrescentou foi o atalho **Brazuca Play**
(menu raiz) para deixar claro que a árvore inteira continua a um clique, além
da troca dos três botões da Home para os **favoritos sincronizados**.

## Testes automatizados que travam isso

`tests/test_skin_phone_layout.py::NavegacaoCompletaTest`

* `test_botao_abre_o_menu_raiz_do_addon`
* `test_todo_atalho_executa_o_addon_e_nao_uma_lista_da_skin`
* `test_atalhos_de_favoritos_abrem_a_janela_do_addon`
* `test_addons_continuam_alcancaveis_pela_barra_superior`
* `test_skin_nao_embute_catalogo`

`tests/test_bridge_favorites.py` cobre a leitura de `favorites.dat` (URLs
nativas, playable × pasta, arquivo nunca escrito).
