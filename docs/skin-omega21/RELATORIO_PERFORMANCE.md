# Relatório de performance

Data: 2026-11-11. Medições estáticas locais (sem Kodi/dispositivo). Nenhuma otimização visual foi aplicada nesta etapa — a skin já é leve e a auditoria não encontrou desperdício relevante.

## 1. Medições reais

| Recurso | Medida |
|---|---|
| Skin descomprimida | 1.235.406 B (138 arquivos) |
| ZIP de entrega | 518.427 B (136 arquivos, `ZIP_DEFLATED` nível 9) |
| `xml/` | 322.531 B (93 arquivos; maior `Home.xml` 53.342 B) |
| `media/` | 34.649 B (33 PNGs; 21 placeholders de 899 B) |
| `fonts/` | 825.388 B (2 TTFs Liberation Sans) |
| `resources/` | 40.829 B (`fanart.jpg` 37.017 B + `icon.png` 3.248 B) |
| `colors/` + `language/` | 377 B + 5.081 B |
| Ponte SMARTED-TV | 7 módulos Python, 32.640 B no total (`default.py` 10.643 B, `search.py` 9.052 B) |
| Preview HTML | 28.900 B (arquivo único, sem imagens/fontes externas) |

## 2. Análise

- **Imagens**: nenhum PNG excessivo. Os `Default*.png` de 899 B são placeholders mínimos (carregamento barato). `fanart.jpg` (37 KB) e `icon.png` (3 KB) estão em tamanho normal. Nenhuma textura duplicada relevante; `white.png` (79 B) é reutilizada como base de cores via `colordiffuse` — padrão eficiente.
- **Fontes**: 2 arquivos (Regular/Bold) cobrem os 8 estilos (`Font.xml`). Não há fontes por idioma nem pesos extras.
- **XML**: 93 arquivos, maioria pequena. `Home.xml` (53 KB) concentra hero/menu/widgets — esperado. Includes reutilizáveis (`Views`, `Header`, `Bg`) evitam duplicação nas janelas genéricas (297 B cada).
- **Animações**: fade 200/150 ms, scroll 200–500 ms, autoscroll do hero 7 s (condicional a `hero_autoscroll`). Nenhum efeito pesado.
- **Ponte**: widgets com cache diário (`daily_cache.py`) e coalescência de requisições simultâneas; busca limitada a 24 MB por fonte; sem polling agressivo. Falhas de fonte não bloqueiam a Home (log + diretório vazio).
- **ZIP**: 518 KB é tamanho normal para skin com 2 fontes. Não houve redução artificial de qualidade.

## 3. Otimizações aplicadas

Nenhuma nesta etapa. Motivo: sem gargalo medido e sem dispositivo para testar, qualquer corte (imagens, fontes, animações) seria especulativo e poderia prejudicar fidelidade/legibilidade — contra a regra do projeto.

## 4. Pendências (exigem dispositivo)

- Tempo de inicialização, abertura de telas, uso de CPU/memória e fluidez de rolagem em TV Box/TV Stick.
- Carregamento de fanarts remotas do Brazuca (rede + cache do Kodi).
- Teste com biblioteca grande (milhares de itens) e PVR ativo.

## 5. Recomendações

- Manter `hide_hero`/`hide_widgets` disponíveis para dispositivos fracos (já existem em `settings.xml`).
- Se o hero pesar em hardware limitado, desativar `hero_autoscroll` (padrão ligado) — sem alterar XML.
- Não adicionar texturas grandes nem fontes extras sem medir o impacto no ZIP e na memória.
