# Mapa de referências visuais — 44 telas

Referência: https://grand-pothos-77ee72.netlify.app/ (galeria JS, 44 telas 16:9).
Método: leitura textual via `fetch_page` em 2026-11-11. O site é uma galeria JavaScript; a extração expôs nomes, grupos e o texto da tela 01, mas **não** expôs capturas, medidas em pixels ou CSS das demais telas. Este mapa registra o que foi efetivamente observado e marca o restante como inferência a partir de nomes/grupos — **não** como medição visual. Nenhuma captura de tela foi feita (sem automação de navegador nesta sessão).

## 1. Estrutura observada

- Cabeçalho: “Galeria de telas NovaTV — Selecione uma tela para visualizar o layout original em proporção 16:9.”
- Contador: “01 / 44”, título da tela, “Tela 01 • Layout original • 960 × 540”, “Use ← → para trocar de tela”.
- Rodapé: “← Anterior / Próxima →” + índice das 44 telas agrupado.
- Aviso do site: “esta página mostra os layouts HTML originais… Ela não é a skin XML executável do Kodi. Use-a para comparar… composição, cores, posições, cards e telas”.

## 2. As 44 telas (nomes e grupos observados)

| # | Nome | Grupo |
|---|---|---|
| 01 | Aurora | Início e entretenimento |
| 02 | Blade | Início e entretenimento |
| 03 | Top 10 | Início e entretenimento |
| 04 | Esportes | Início e entretenimento |
| 05 | Guia | Início e entretenimento |
| 06 | Canais | Início e entretenimento |
| 07 | Serie | Início e entretenimento |
| 08 | Player | Início e entretenimento |
| 09 | Aurora | Variações e configurações |
| 10 | Blade | Variações e configurações |
| 11 | Top 10 | Variações e configurações |
| 12 | Esportes | Variações e configurações |
| 13 | Guia | Variações e configurações |
| 14 | Canais | Variações e configurações |
| 15 | Serie | Variações e configurações |
| 16 | Player | Variações e configurações |
| 17 | Config | Mídia e navegação |
| 18 | Musica | Mídia e navegação |
| 19 | Tocando | Mídia e navegação |
| 20 | VideoMus | Mídia e navegação |
| 21 | Radio | Mídia e navegação |
| 22 | Jogos | Mídia e navegação |
| 23 | Complementos | Mídia e navegação |
| 24 | Imagens | Mídia e navegação |
| 25 | Videos | Mídia e navegação |
| 26 | Favoritos | Mídia e navegação |
| 27 | Clima | Mídia e navegação |
| 28 | Arquivos | Mídia e navegação |
| 29 | Energia | Sistema e gerenciamento |
| 30 | Busca | Sistema e gerenciamento |
| 31 | Gravacoes | Sistema e gerenciamento |
| 32 | Timers | Sistema e gerenciamento |
| 33 | Perfis | Sistema e gerenciamento |
| 34 | Contexto | Sistema e gerenciamento |
| 35 | AudioLeg | Sistema e gerenciamento |
| 36 | Sobre | Sistema e gerenciamento |
| 37 | Ajustes | Configurações avançadas |
| 38 | CPlayer | Configurações avançadas |
| 39 | CMidia | Configurações avançadas |
| 40 | CTV | Configurações avançadas |
| 41 | CServ | Configurações avançadas |
| 42 | CInt | Configurações avançadas |
| 43 | CSis | Configurações avançadas |
| 44 | CPerf | Configurações avançadas |

## 3. Tela 01 — Aurora (texto observado)

- Topo: “NOVA TV”, relógio “20:45”, menu “Início, Filmes, Séries, TV ao vivo, Esportes, Minha lista”.
- Hero: selo “LANÇAMENTO”, título “Noite Vermelha”, metadados “2026 · Thriller · 16 anos · 1h58”, sinopse “Uma investigadora aposentada volta ao caso que destruiu sua carreira quando novas pistas surgem.”, botões “Assistir, Trailer, + Minha lista”.
- Fileira “Lançamentos”: Noite Vermelha, Código Atlas, Rota 66, Maré Alta, Último Farol, Zona Cinza, Dias de Vidro.
- Padrão inferido para Blade/Top 10/Esportes: mesma moldura (topo + hero + fileiras), com variação de conteúdo/foco. **Não medido.**

## 4. Padrão visual predominante (da skin + tela 01)

- Monocromático estrito: preto, branco e cinzas. Paleta da skin (`colors/defaults.xml`): `bg #0d0d0d`, `panel #181818`, `panel2 #262626`, `white #f2f2f2`, `text #d9d9d9`, `muted #a6a6a6`, `accent #f2f2f2`, `ontext #0d0d0d`. Nenhuma cor de destaque.
- Tipografia: Liberation Sans (Regular/Bold), tamanhos 22–84 (`Font.xml`).
- Foco/seleção: fundo branco + texto preto + anel (`ring.png`) nos cards; underline branco no menu.
- Cards: pôster 2:3 (210×300) e paisagem 16:9 (360×205), scrim inferior, título, barra de progresso quando aplicável.
- Hero: fanart em tela cheia com scrim horizontal, selo, título grande, metadados, sinopse e botões.
- Espaçamentos base: margens 60 px, topo 28–30 px, fileiras com altura 340–400 px (ver `DESIGN_SYSTEM_ORIGINAL.md`).

## 5. Limitações (não inventadas)

- Sem capturas: proporções, espaçamentos exatos, ícones e estados de seleção das telas 02–44 **não** foram medidos. O preview (`PREVIEW_KODI.html`) reproduz a composição descrita (hero, fileiras, grades, listas, EPG, player, ajustes) de forma esquemática, não pixel a pixel.
- “Variações” (09–16) são tratadas como estados alternativos das mesmas 8 telas (foco, dados, diálogos), pois o site não expôs o que muda entre elas.
- Adaptação solicitada: **TV ao vivo em TV (06 Canais)**, **Filmes em Filmes (25)**, **Séries + Doramas + Animes + Desenhos + Novelas em Séries (07 Serie)**. O preview nomeia a tela 25 como “Filmes” (site: “Videos”) para refletir a rota `movies` da ponte.
