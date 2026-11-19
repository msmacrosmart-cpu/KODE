# SMARTEDTV 1.0.129 — addons, D-pad da Home e anúncio na TV

Rodada de diagnóstico. Nada de tentativa: cada item abaixo tem **a causa
localizada** (log do projetor ou histórico Git), **o que foi mudado** e **a
prova**. O que não pôde ser provado está dito como não provado.

APK: `SMARTEDTV-universal.apk` • SHA-256
`c98154666ef5d26807b95bcc186c7152b3e97ffe9887dde860dbd3a01afc8118` •
287312095 bytes • 1.0.129 / código 2103115.

---

## Resultado por problema

| Problema | Causa identificada | Correção aplicada | Teste realizado | Resultado |
| --- | --- | --- | --- | --- |
| Navegação D-pad (subir para o hero/topo) | `d91326f` trocou as fileiras 9201/9203 por três `<onup>` **sem condição** (9300, 9201, 9203). O Kodi usa a primeira sem condição; quando o hero está oculto, o salto não acontece e o foco fica preso. Antes (873542f/21a89e2) a subida era uma ação por layout | Fileiras sobem para o hero (uma ação); hero sobe para a **barra superior** em qualquer layout; a barra de categorias (9000) desce para o hero nos dois layouts e passa a existir também na blade | `tests/test_navegacao_aurora.py` (9) + `test_home_navegacao` + `check-foco-skin` | **Corrigido na lógica e provado por teste**. Não testado com controle físico |
| Addons / bootstrap | `ads_regra.py`, `ads_vast.py`, `repair.py`, `favourites.py` e `skin_setup.py` **não estavam** na lista de módulos do injetor do pipeline. O `import ads_regra` no topo do `smart_ads.py` derrubava o `service.py` inteiro (log: `FileNotFoundError`) | Os 6 módulos entram no APK; teste compara a pasta com a lista; o build passa a **reprovar** APK incompleto e o emulador confere o APK **instalado** | `test_addon_completo_no_apk` (8), `test_conferir_modulos_apk` (4), CI: "todos os modulos do addon estao no APK instalado" | **Corrigido e provado no APK instalado no AVD**. Boot do serviço com addon real (sem erro de import) não testado em hardware |
| Anúncios na TV | A tag do "Testar anúncio" era `external/vmap/single_ad_samples`: devolve **VMAP**, e o leitor só entendia **VAST** (`<Ad><InLine>`). O caminho terminava em `vast-sem-criativo` e nenhum anúncio tocava | Tag de teste passa a ser a de anúncio único (VAST) do mesmo inventário oficial; o leitor agora segue **VMAP** (AdBreak → AdTagURI) como já seguia Wrapper | `test_ads_vmap_tv` (6) + prova do caminho completo com VMAP real (recibo com criativo 720p e player chamado) | **Causa corrigida; reprodução em TV real NÃO validada** (sem aparelho e sem rede para o DoubleClick neste ambiente) |
| Funcionamento MOBILE | — | Nada do AdMob, da activity de abertura, da detecção `e_tv()` nem do VIP foi alterado | AVD API 30: instalação limpa (armeabi-v7a), atualização por cima (arm64-v8a), LAUNCHER e LEANBACK_LAUNCHER, 3 reaberturas com imagem | **Sem regressão no que foi testado** (582 testes; 0 regressões vs. base) |

---

## 1. Addons e bootstrap — o erro que aparecia no projetor

### O que o log diz (kodi.log, 19/11 11:41:23)

```
error: EXCEPTION Thrown (PythonToCppException)
Error Type: <class 'FileNotFoundError'>
Error Contents: ... service.smarted.bootstrap/ads_regra.py
  File ".../smart_ads.py", line 66, in <module>  import ads_regra
  File ".../service.py", line 21, in <module>    import smart_ads
```

### A causa

O `ads_regra.py` **existia** no repositório, mas não estava na lista `MODULOS`
de `tools/kodi/atualizar-apk-v17.py` — o injetor que o pipeline atual usa. O
`import` está no **topo** do `smart_ads.py`, então não havia onde tratar: o
`service.py` inteiro abortava antes de fazer qualquer coisa.

Isso explica as duas coisas que você relatou (notificação de erro e addons
"não carregando"): **nenhum** trabalho do serviço rodava — reparo, favoritos,
skin, menu, anúncio.

A lista ainda omitia `ads_vast.py` (que era injetado por outro script,
`injetar-tela-entrada.py`, que o pipeline atual não chama) e `repair.py`,
`favourites.py`, `skin_setup.py` (importados no topo do `service.py`). Eram
cinco defeitos com a mesma causa, e o primeiro mascarava os outros.

### Prova de que antes funcionava

No `kodi.old.log` (19/11 00:00), o serviço rodava:

```
[service.smarted.bootstrap] RESULTADO: ok (restaurados=0, faltando=0)
[service.smarted.bootstrap] silencio: navegacao sem sons
[service.smarted.bootstrap] favoritos: 10 atalhos já presentes
```

No `kodi.log` atual (11:41), **nenhuma** dessas linhas aparece. A regressão é
entre os dois, e a diferença é a lista de módulos do injetor.

### O que foi feito

- os seis módulos entram em `MODULOS`;
- `tests/test_addon_completo_no_apk.py` compara a **pasta** com a lista: um
  módulo novo que esqueça de entrar no APK falha aqui, não no aparelho;
- `tools/kodi/conferir-modulos-no-apk.py`: o CI **reprova** o APK incompleto
  (testado: reprova sem `ads_regra.py`, aprova o completo);
- o smoke do emulador agora extrai o addon do APK **já instalado** e confere
  módulo por módulo, além de reprovar o boot se o logcat mostrar
  `ModuleNotFoundError` do addon.

### Prova no APK publicado (run 44553462190)

```
notice: todos os modulos do addon estao no APK instalado
notice: v22 instalada e atualizada com adb install -r; versionCode=2103115; ABI: arm64-v8a
notice: reabertura 1/2/3: app vivo e com imagem na tela
```

### Ainda não provado

O boot completo do serviço **numa TV real** (você precisa ver o `kodi.log` do
aparelho depois de instalar esta versão). O que está provado: os arquivos estão
dentro do APK instalado e o boot no AVD não gerou erro de import.

---

## 2. Navegação da Home (Aurora)

### A causa (histórico Git)

| commit | o que fez |
| --- | --- |
| `873542f` | estado que funcionava: `9201` → `9300` (hero) e `9000`; `9203` → `9300` + `9201` |
| `21a89e2` / `92681ce` | caminho hero → barra superior comprovado no emulador |
| **`d91326f`** | trocou por **três `<onup>` sem condição** em `9201` e `9203` (9300, 9201, 9203) — a regressão |

No Kodi 21, `CGUIControl::OnUp` consulta `CGUIAction::GetNavigation`, que
devolve a **primeira** ação cuja condição passa, e ignora as demais. Com três
ações incondicionais, só a primeira vale — e quando o hero está oculto
(`pb_hide_hero`) o salto para `9300` não acontece: o foco fica preso na
fileira. Era exatamente o "desço, mas não volto".

### O que foi feito (sem tocar em layout, cards ou dimensões)

| de | para | antes | agora |
| --- | --- | --- | --- |
| fileira `9201` (Lançamentos) | hero | 3 `<onup>` (9300/9201/9203) | `9300` |
| fileira `9203` (Séries) | hero | 3 `<onup>` (9300/9201/9203) | `9300` |
| hero `9300` | barra superior | `9000` só no Aurora / `9121` só na blade | **`9121` nos dois** |
| categorias `9000` | hero | só `9300`, e **não existia na blade** | `9320` (blade) + `9300` (Aurora); visível nos dois |

Resultado do grafo (as duas skins ficam idênticas):

```
search/ajustes/energia (9121-9123) -> 9000 (categorias)
9000 -> 9300 (hero)  [e 9320 na blade]
9300 -> 9201, 9203, 9000, 9121
9201 -> 9300    9203 -> 9300
```

Ou seja: **última fileira → hero → barra superior**, e a descida de volta pelo
mesmo caminho. Nada de `<onup>` apontando para si mesmo.

### Testes

- `tests/test_navegacao_aurora.py` (novo, 9 testes): cada direção tem **uma**
  ação incondicional; as fileiras sobem para controle existente no Aurora; o
  hero chega na barra; as categorias existem e descem nos dois layouts; a
  hierarquia completa (último item → topo) existe.
- `tests/test_home_navegacao.py`: o teste que exigia `9203 → 9201` foi
  corrigido (era a intenção errada que veio da regressão).
- `tests/test_foco_dpad_aparelho.py`: passa.

### Não testado

Controle remoto físico. A prova aqui é o grafo de foco e o parser real do Kodi
(`GetActions`/`GetNavigation`), não dedo no D-pad.

---

## 3. Anúncios na TV — por que nunca apareceu

Respondendo à sua lista, uma por uma:

| # | etapa | resultado |
| --- | --- | --- |
| 1 | o anúncio está sendo solicitado? | **Não estava.** Sem tag configurada o app não pede (de propósito). Com o modo de teste, pedia — e vinha o problema da etapa 4 |
| 2 | a URL/tag está correta? | **Não.** A tag de teste era `…/vmap/single_ad_samples` (corpus **VMAP**) |
| 3 | existe resposta do servidor? | Sim (quando há rede), mas no formato VMAP |
| 4 | o VAST recebido é válido? | **Não era VAST.** VMAP não tem `<Ad><InLine>`; o leitor descartava |
| 5 | recursos carregados? | Nunca chegou aqui: não havia criativo escolhido |
| 6 | o player inicia? | Nunca chegou aqui |
| 7 | eventos? | Implementados (`impression`, quartis, `complete`, `skip`) — só disparam se tocar |
| 8 | incompatibilidade com Android TV? | Nenhuma no caminho: é o player do Kodi (`PlayMedia`), que existe em TV |
| 9 | bloqueio por config/dependência? | **Sim**: `ads_vast.py` nunca entrou no APK (item 1) e a tag pedia VMAP |

### O que foi feito

1. a **tag de teste** passa a ser a de anúncio único (`external/single_ad_samples`),
   do mesmo inventário oficial de teste do Google — sem inventar ID nem tag;
2. o leitor agora **segue VMAP**: pega o primeiro `<AdBreak>` → `<AdTagURI>` e
   continua como já fazia com `Wrapper`. Isso conserta também uma tag VMAP do
   dono do app (entrega padrão do Ad Manager), que antes era jogada fora;
3. `ads_vast.py` entra no APK (item 1) — antes dele nem existia no aparelho.

### Prova (executada aqui, com VMAP no formato oficial do IAB)

```
1. tag pedida        : https://ads.exemplo.com/vmap
2. VMAP lido         : <vmap:VMAP><vmap:AdBreak><vmap:AdTagURI>
3. AdTagURI seguido  : https://ads.exemplo.com/vast/preroll
4. criativo escolhido: https://ads.exemplo.com/720.mp4   (720p, mais próximo da tela)
5. player chamado    : True
6. recibo            : exibido=False / motivo=nao-iniciou
```

O passo 6 é **honesto e proposital**: no teste o player é falso e nunca toca.
O recibo só vira `exibido=True` quando o vídeo do anúncio realmente toca — é a
regra que você pediu (não declarar anúncio exibido sem reprodução). Antes desta
correção, com a mesma tag, o recibo era `vast-sem-criativo` e o player nem era
chamado.

### O que NÃO está provado, e por quê

**A reprodução do anúncio numa TV real não foi verificada.** Duas limitações
reais deste ambiente:

- não há TV/box/stick físico nem aqui, nem no CI (o AVD é celular);
- este ambiente **não alcança** `pubads.g.doubleclick.net` (a rede só libera
  GitHub/npm/PyPI), então não posso confirmar a resposta do servidor de anúncios
  do Google daqui.

O que dá para afirmar: os três defeitos que impediam o anúncio de tocar
(arquivo ausente no APK, tag pedindo VMAP, VMAP não lido) estão corrigidos e
cobertos por teste. A validação final é no aparelho: **Ajustes → Testar
anúncio**, e me manda o `kodi.log` com as linhas `[SmartAds]` — elas dizem
exatamente em que etapa parou, se parar.

Sobre IMA SDK: **não foi integrado**. Ele exigiria compilar o SDK Java dentro do
`classes.dex` — o que este repositório não faz (só reempacota um APK base, sem
fonte Java), e a integração certa depende do player nativo, não do player do
Kodi. O caminho VAST-por-player continua sendo o tecnicamente compatível aqui;
o diagnóstico acima mostra que o problema era de formato de tag e de arquivo
faltando, não de falta de SDK.

---

## 4. Mobile — sem regressão

- nada do AdMob, `AppOpenActivity`/`PreRollActivity`, `e_tv()` ou VIP foi
  alterado;
- AVD API 30 (mesmo build): instalação limpa em `armeabi-v7a`, atualização por
  cima da v22 em `arm64-v8a`, abertura por `LAUNCHER` e `LEANBACK_LAUNCHER`, três
  reaberturas com imagem (sem tela preta);
- 582 testes: **0 regressões** vs. a base desta rodada. As 24 falhas que
  restam são **pré-existentes** (testes antigos de layout/teclado que descrevem
  uma skin anterior) e nenhuma toca em addon, navegação, anúncio ou update.

---

## 5. Release e Dropbox

- `v1.0.129-universal` (**Latest**) com **exatamente um** arquivo:
  `SMARTEDTV-universal.apk` (287312095 bytes, SHA-256 acima, igual ao log do
  mesmo build);
- releases intermediárias desta rodada (1.0.126/127/128) apagadas — não fica
  versão de teste no ar;
- nenhuma release tem dois APKs (1.0.122/123/125 também estão com um só);
- Dropbox: a pasta **`SMARTEDTV UNIVERSAL`** existe e está pública
  (`/scl/fo/0f1ux2r4p8mooqyeswy0y/AFHlvKmq-qedIwSWQLDoUGY?rlkey=q92lngn8lu7gqojbcref69ikb`),
  e o app procura `SMARTEDTV.apk` nela. **Continua vazia**: o conector recusa
  arquivo acima de 100 MB e o sandbox não alcança a API do Dropbox (274 MB).
  Enquanto estiver vazia, a atualização cai para a release do GitHub, que tem o
  universal.

---

## 6. O que ficou pendente (e por quê)

| pendência | motivo | como fechar |
| --- | --- | --- |
| Anúncio tocando em TV real | sem aparelho e sem rede para o DoubleClick aqui | instalar 1.0.129, Ajustes → Testar anúncio, enviar `kodi.log` |
| D-pad com controle físico | sem aparelho | testar subir das fileiras até a barra superior |
| Boot do serviço numa TV real | sem aparelho | conferir no log: `RESULTADO: ok`, `favoritos: … atalhos` (linhas que voltaram a existir) |
| `SMARTEDTV.apk` no Dropbox | limite de 100 MB do conector; sandbox sem rede para o Dropbox | baixar da release e subir com esse nome, ou liberar a rede/API do Dropbox no ambiente |
| 24 testes antigos falhando | pré-existentes, descrevem uma skin anterior (layout/teclado) | fora do escopo desta rodada; não escondem nada dos itens acima |
