# SMARTEDTV 1.0.122 — duas versões: celular e TV

Entrega feita sobre a estrutura atual do projeto (sem reconstruir, sem trocar
versão-base do Kodi, arquitetura ou pipeline). Os dois APKs saíram do **mesmo
workflow rápido** que publicava a versão única, rodada 44461237415 (commit
`6f90684`).

## 1. Os dois arquivos

| | **CELULAR** | **TV** |
|---|---|---|
| Arquivo | `SMARTEDTV-universal.apk` | `SMARTEDTV-tv.apk` |
| SHA-256 | `3c0ec83b8df3580940e4edda6d0321be86e80aa9c32918bd108de9a7442c9879` | `c6e9a14599d48b3a29b3533b32aaedd1c49723176788b6e3930f42dddb929906` |
| Tamanho | 287299688 bytes | 287299688 bytes |
| Pacote Android | `smartedtv.full` (preservado) | `smartedtv.full` |
| Marcador interno | `mobile` | `tv` |
| Pasta Dropbox | `SMARTEDTV-MOBILE/SMARTEDTV.apk` | `SMARTEDTV-ON/SMARTEDTV.apk` |
| Versão / código | 1.0.122 / 2103108 | 1.0.122 / 2103108 |
| Anúncios | AdMob (intocado) | sem AdMob; ver item 5 |

Release: `v1.0.122-universal` — https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.122-universal

**Sobre o pacote:** mantive `smartedtv.full` nos dois arquivos, como pedido
(preservar o identificador do MOBILE). O que identifica a versão é o marcador
`assets/smartedtv-variante.txt` gravado pelo build, lido por `variante.py`.
Consequência prática, e ela precisa ser dita: **os dois não ficam instalados ao
mesmo tempo no mesmo aparelho** — são o mesmo app, um substitui o outro. Mudar
o pacote da TV para `smartedtv.tv` exigiria editar `classes.dex` (as activities
`PreRollActivity`/`Splash` e o `libkodi.so` carregam o nome do pacote), o que só
é possível com build completo do app Android — fora do que foi permitido nesta
rodada. Se quiser as duas instalações simultâneas, é um build de código-fonte,
não um ajuste de empacotamento.

Mesmo certificado de teste dos dois: `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a` (v1/v2/v3),
minSdk 21, target 34, arm64-v8a + armeabi-v7a.

## 2. O que mudou no código

- **`variante.py` (novo)** — única fonte da decisão `mobile`/`tv`: lê o marcador
  do APK, depois `System.Platform.Android.TV`, nome do aparelho e altura de tela;
  em dúvida, **mobile** (a versão aprovada). Nada de `if tv` espalhado.
- **`vip.py`** — pasta do Dropbox por versão, `pacote_do_apk()` e
  `apk_serve_para_esta_versao()` (a TV recusa APK da outra versão, inclusive
  APK antigo sem marcador). O MOBILE mantém exatamente os links que já
  funcionavam.
- **`script.smartedtv.welcome/default.py`** — botões Dropbox e Baixar/Atualizar
  seguem a mesma pasta; se a pasta da TV ainda não existe, o app avisa o que
  falta em vez de baixar o APK da outra versão.
- **`smart_ads.py`** — o celular continua igual; a TV não abre mais a activity
  do AdMob (era o que pausava o vídeo e voltava sem nada no projetor) e registra
  no log o que falta. A regra de frequência continua sendo só de `ads_regra`.
- **`Home.xml` (as duas skins)** — D-pad: `9098`/`9099` voltaram a ser irmãos do
  `9097` no `grouplist 9020` (o commit `52021d7` os tinha deixado *dentro* do
  botão Energia, sem nenhuma saída de foco); os `SetFocus` de `onload` só rodam
  no layout que existe; `9220`/`9230`/`9240` não descem mais para si mesmos.
  Layout e identidade intactos (`git diff` da Home contra `884ccb7` = vazio, à
  exceção das saídas de foco acima).
- **`Startup.xml` (Splash)** — a marca da abertura agora é a **logo do app**
  (antes era o texto "SMARTEDTV"); aplicado também no injetor que grava o
  `Startup.xml` dentro do APK. A logo da Home não foi tocada.
- **`service.py`** — "Conteudo incompleto: veja userdata/smarted-bootstrap.log"
  e o aviso de atalhos saíram da interface e ficaram no log interno. Falha
  crítica de perfil continua visível (o `AlertDialog` do `ProfileBootstrap`).
- **Build** — `build.sh` monta os dois APKs com a mesma receita; o único
  parâmetro novo é `--variante` no `atualizar-apk-v17.py`.

## 3. Testes (2 ciclos)

Ciclo 1 (v1.0.121, run 44459376769) e ciclo 2 (v1.0.122, run 44461237415),
os dois com o pipeline inteiro verde: `static-check` (229 XML, 76 scripts),
regressões de tela/controle/overlays, assinatura v1/v2/v3, auditoria do APK e
emulador API 30 (atualização por cima da v22 sem desinstalar, instalação limpa,
LAUNCHER e LEANBACK_LAUNCHER, três reaberturas).

Suíte local: **23 falhas, todas antigas** (baseline de `/tmp/base119.txt`),
nenhuma nova. 12 testes novos em `tests/test_variante_mobile_tv.py`.
`check-foco-skin.py`: nenhum "SEM SAIDA" nas duas skins.

Onde não houve teste real, digo com clareza:

- **Não testei em projetor/TV física.** O emulador é API 30 com tradução ARM;
  não há saída de vídeo nem controle remoto real nele.
- **Anúncio na TV não foi exibido em aparelho nenhum** — não existe inventário
  possível hoje (ver item 5). O que testei é que a versão TV não pede AdMob,
  não bloqueia a reprodução e não simula sucesso.

## 4. D-pad: o que foi corrigido

A causa do "D-pad não anda" não era falta de `onup/ondown`: o commit `52021d7`
deixou três botões **aninhados dentro de outro botão**. Corrigido com validação
estrutural do pai (`9097`, `9098` e `9099` agora são filhos do `grouplist
9020`). Também: `SetFocus` de `onload` apontando para controles de layouts que
não aparecem (voltava o foco para o nada) e fileiras que desciam para si mesmas.

## 5. Anúncio na TV: o que falta, sem rodeio

O Google **não suporta o AdMob (Google Mobile Ads) em Android TV** — não é
questão de criar outro bloco: o formato de tela cheia que o app usa não existe
para TV, e é por isso que no projetor a tela abria e voltava vazia.

O formato suportado em TV é **vídeo linear (VAST/VMAP) via Google IMA SDK**,
que precisa estar **compilado dentro do app Android**, com o vídeo passando pelo
player do app — não pelo player do Kodi. Hoje o APK traz o `classes.dex` do
Kodi pronto (`docs/diag-ads-java.txt`: só `com.google.android.gms.ads.*`, nenhuma
referência a IMA) e o pipeline rápido preserva esse dex por definição.

**Falta, para a TV ter anúncio:**

1. compilar o app Android do zero com `androidx.media3:media3-exoplayer-ima`
   (ou `interactivemedia`) — é build de código-fonte, não empacotamento;
2. uma conta/ad manager com o inventário de vídeo e a **tag VAST** (o campo
   `VAST_TAG_PADRAO` em `smart_ads.py` já existe e está vazio de propósito);
3. decidir o player: com o Kodi como está, o anúncio de vídeo não tem onde ser
   renderizado no meio do stream.

Até lá a versão TV **não pede anúncio** e a reprodução nunca é bloqueada; a
regra de frequência (1 por conteúdo por sessão, 2 min do fim do anúncio, VIP
nunca, uma tentativa por troca) permanece intacta em `ads_regra.py` para quando
o vídeo existir.

## 6. Configuração externa pendente

- **Pasta `SMARTEDTV-ON` no Dropbox**: precisa existir e ter um link de pasta
  (`/scl/fo/...` com `rlkey`). O nome já está no código (`vip.DROPBOX_PASTA_TV`,
  hoje vazio) — **não inventei link nem token**. Enquanto estiver vazio, a TV
  mostra "Atualização não configurada" e não baixa nada.
- **Confirmar que a pasta histórica é a `SMARTEDTV-MOBILE`**: o link atual
  (`/scl/fo/5w6yfp0tvee0xro2wh0m3/...`) continua sendo o do celular; se a pasta
  publicada tiver outro nome, é só ajustar `PASTA_NOME_MOBILE` (o link é o
  contrato, o nome é rótulo).
- **`SMARTEDTV.apk` nas duas pastas** (nome fixo já usado pelo app).

## 7. O que não mudou (conferido)

Home (layout, logo, identidade), reprodução de canais/filmes/séries, addons,
VIP, Lovable, checkout Cakto, compartilhamento, QR Codes, navegação, assinatura,
Kodi 21.3 base, ABIs e o pipeline de build.
