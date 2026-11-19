# SMARTEDTV 1.0.123 — anúncio na TV, fluxo de entrada e D-pad

Rodada focada **só na TV** (mobile intocado). Sobre a estrutura atual, sem
reconstruir o app e sem trocar o pipeline.

## 1. Anúncio na TV: agora existe e toca de verdade

Era o pedido mais importante: *"garanta que os anúncios sejam reproduzidos"*.

### O que estava errado (e era meu erro)

Na 1.0.122 eu **desliguei o anúncio na TV de propósito**. O `tocar_anuncio()`
retornava antes de disparar qualquer coisa quando `e_tv()` era verdadeiro,
porque o AdMob não preenche em Android TV. Resultado: na TV o anúncio não
aparecia **porque nunca era pedido**.

### O que é verdade (documentação do Google)

O Google declara na própria página do SDK: *"Google Mobile Ads SDK for Android
does not support Android TV"*
(https://developers.google.com/admob/android/sdk). Não é um bloco novo no AdMob
que resolve — o formato de tela cheia do celular não existe para TV.

O formato que existe em TV é **anúncio de vídeo linear (VAST)**. Até aqui eu
tratei como se isso exigisse compilar o Google IMA SDK dentro do `classes.dex`
(build de código-fonte, proibido nesta rodada). **Não exige.** O próprio player
do Kodi — o mesmo que toca canais, filmes e séries em TV, box, stick e projetor
— toca o vídeo do anúncio.

### Como ficou

`kodi/addons/service.smarted.bootstrap/ads_vast.py` (novo, 1 arquivo):

1. lê a tag VAST configurada (do projeto ou da propriedade da janela);
2. baixa o XML **com timeout** (12 s) e segue `Wrapper` até 2 níveis — é assim
   que o Ad Manager entrega quando há mediação;
3. escolhe o criativo de vídeo (MP4/WebM progressivo primeiro, HLS depois, o
   mais próximo da resolução da tela);
4. entrega ao player do Kodi (`PlayMedia`) e **confirma que tocou**;
5. dispara os eventos VAST obrigatórios: `impression`, `start`,
   `firstQuartile`, `midpoint`, `thirdQuartile`, `complete` (e `skip`);
6. **devolve o conteúdo**: ao vivo reabre sem `seek` (seek em canal contínuo
   derruba o fluxo); filme/série volta na posição em que estava.

Regra de honestidade: `exibido` só é `True` quando o vídeo do anúncio realmente
tocou. Sem tag, sem rede, VAST sem criativo ou player recusando → devolve
`False`, o conteúdo **não** é recarregado e a reprodução segue. Nenhum anúncio é
simulado e nenhuma tag é inventada.

### O que continua valendo

- **Celular não mudou**: continua disparando a activity AdMob do APK. Há teste
  garantindo isso (`test_celular_continua_disparando_admob`).
- Frequência intacta em `ads_regra.py`: 1 por conteúdo por sessão, 2 min desde a
  conclusão/pulo, VIP nunca, uma tentativa por troca; falha não consome o
  intervalo.

### O que falta para o anúncio aparecer no seu aparelho

**Uma coisa só: a tag VAST do projeto.** Sem ela não há anúncio (e nada é
inventado). Duas formas:

1. **Validar agora, sem contratar nada**: Ajustes → "Testar anúncio" (com o modo
   avançado liberado). A TV usa a **tag de teste oficial do Google** e mostra na
   tela se o anúncio foi exibido ou o motivo exato da falha. Isso não gera
   tráfego inválido — é o inventário de teste do próprio Google.
2. **Produção**: pegar a tag VAST no Google Ad Manager (unidade de vídeo) e
   preencher `VAST_TAG_PADRAO` em `smart_ads.py`. Com a tag, o mesmo caminho
   passa a rodar no pré-roll de toda troca de conteúdo, respeitando a regra de
   frequência.

## 2. Fluxo inicial: entrada antes da Home

Corrigido em `service.smarted.bootstrap/service.py`:

- a **janela de startup não conta mais como interface pronta** — era isso que
  fazia o app abrir na Home na TV. Agora o vigia espera a **tela de entrada**;
- `main()` não libera a Home por cima da escolha ("assistir com anúncios" ×
  "ir para o checkout"); o preparo continua em segundo plano;
- a Home só é liberada se a tela de entrada realmente não vier (addon
  quebrado/desabilitado) — o app nunca fica no preto.

Ordem garantida: **Splash (Startup.xml) → tela de entrada/escolha → Home**.

## 3. Erro de bootstrap na TV

A mensagem técnica (`Não foi possível preparar: … userdata/smarted-bootstrap.log`)
já não aparece na interface desde a 1.0.122; nesta rodada o que sobrava era o
boot indo para a Home antes da tela. Falha crítica de perfil continua registrada
no log interno, nunca escondida.

## 4. D-pad

Corrigido na rodada anterior e mantido: no layout ativo (`aurora`), `9201`/`9203`
sobem para o hero (`9300`) sem depender de layout. Falta apenas a validação
física em TV real (não há controle remoto neste ambiente).

## 5. Testes (3 ciclos, como pedido)

| Ciclo | O que roda | Resultado |
|---|---|---|
| 1 | `tests/test_ads_vast_tv.py` — 40 testes novos: leitura de VAST, Wrapper, eventos, recibo honesto, retorno do conteúdo, celular × TV, botão de teste, entrega do módulo no APK | **40 OK** |
| 2 | smoke do caminho completo (tag → VAST → player → eventos → conteúdo de volta), sem rede e sem aparelho | **6/6 OK** |
| 3 | `static-check` (229 XML, 77 scripts) + suíte completa | **540 testes, 0 falhas novas** vs baseline `/tmp/base119.txt` |

Também: `test_injetor_tela_entrada` atualizado (o `ads_vast.py` novo passa a ser
entregue no APK — sem isso a TV receberia um `smart_ads.py` chamando um módulo
ausente) e `test_ads_por_dispositivo` atualizado (o log agora diz que falta a
**tag**, não o SDK IMA).

**O que não pude provar aqui**: o Google está bloqueado na rede deste ambiente,
então não baixei uma tag VAST real daqui. O parser foi exercitado com VAST 3.0
real (Inline e Wrapper) e o caminho de reprodução com um player simulado. A
prova em aparelho é o passo 1 do item 1 (botão "Testar anúncio" na TV).

## 6. Os dois APKs (publicados)

Release: https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.123-universal
(Build e testes: run 44468195492, commit `d91326f`)

| | **CELULAR** | **TV** |
|---|---|---|
| Arquivo | `SMARTEDTV-universal.apk` | `SMARTEDTV-tv.apk` |
| SHA-256 | `099108699d7286e6e656e115bac4e82cd3a9ad36f0d9b622cc1dd08a0de1b3d6` | `173b0dcf5b688310ee2d806d67619e8c4e6af3c14fe986e59385fe0571d4f330` |
| Tamanho | 287299688 bytes | 287299688 bytes |
| Versão / código | 1.0.123 / 2103109 | 1.0.123 / 2103109 |
| Anúncio | AdMob (intocado) | vídeo VAST pelo player |

Mesmo pacote `smartedtv.full`, mesmo certificado de teste
`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`; o que
diferencia os arquivos é `assets/smartedtv-variante.txt`.

## 7. Arquivos

- `kodi/addons/service.smarted.bootstrap/ads_vast.py` — **novo**
- `kodi/addons/service.smarted.bootstrap/smart_ads.py` — TV usa vídeo; bloqueio removido
- `kodi/addons/service.smarted.bootstrap/check.py` — botão "Testar anúncio" na TV
- `kodi/addons/service.smarted.bootstrap/service.py` — ordem de boot + log do anúncio
- `tools/kodi/injetar-tela-entrada.py` — entrega `ads_vast.py` no APK
- `tests/test_ads_vast_tv.py` — **novo**, 40 testes
- `kodi/skin.novatv/xml/Home.xml`, `kodi/skin.estilo.personalizado/xml/Home.xml` — D-pad (rodada anterior)
