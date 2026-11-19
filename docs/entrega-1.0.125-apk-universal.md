# SMARTEDTV 1.0.125 — um único APK universal

Rodada de finalização. **Nada da lógica de anúncios foi refeito, simplificado
ou reestruturado**: `e_tv()`, AdMob no celular, VAST pelo player na TV, regras
de frequência, VIP e ABIs 32/64 continuam como estavam aprovados. O que mudou
foi só a **entrega**: um arquivo em vez de dois.

## 1. Um APK só

| antes (1.0.122/1.0.123) | agora (1.0.125) |
| --- | --- |
| `SMARTEDTV-universal.apk` **e** `SMARTEDTV-tv.apk` | **só** `SMARTEDTV-universal.apk` |
| duas montagens no `build.sh` (`--variante mobile` e `--variante tv`) | **uma** montagem, sem `--variante` |
| duas pastas no Dropbox | uma: `SMARTEDTV UNIVERSAL` |

O APK vai **sem** `assets/smartedtv-variante.txt`, e isso é de propósito: o
marcador força a variante e faria a TV se comportar como celular (AdMob, que o
Google não suporta em Android TV). Sem marcador, quem decide é o aparelho, por
`variante.py` / `e_tv()` — exatamente o código aprovado.

O `build.sh` agora **falha de propósito** se o marcador aparecer no APK
assinado, para que um erro futuro não devolva AdMob à TV sem ninguém notar.

## 2. O que deixou de existir

- a segunda montagem e o `final_tv` no `build.sh`;
- a instalação do APK de TV no `install-smoke.sh`;
- `apk_tv` no workflow, o `SMARTEDTV-tv.apk` publicado nas releases e o
  sha256 "(TV)" nas notas — as notas falam de **um** arquivo;
- as pastas `SMARTEDTV-MOBILE` / `SMARTEDTV-ON` no código de atualização.

Antes de remover, conferi quem usava cada peça: `assets/smartedtv-variante.txt`
só era lido pelo `e_tv()` (que continua funcionando pelo aparelho) e o
`SMARTEDTV-tv.apk` só era consumido pelo passo de instalação do workflow.

## 3. Dois defeitos reais que a mudança expôs (e foram corrigidos)

Trocar duas entregas por uma quebrou premissas que estavam escondidas. Ambos
foram encontrados por teste, não por leitura:

1. **A TV recusava o APK da pasta.** `apk_serve_para_esta_versao()` recusava,
   na TV, qualquer APK *sem* marcador — era a regra de quando existia um APK só
   de celular sem marcador. Com o universo em um arquivo, isso impediria a TV de
   se atualizar pelo app. Agora "sem marcador" é o caso **normal**; só é recusado
   o que traz marcador (arquivo antigo de outra linha).
2. **A TV ficou sem reserva de download.** A reserva do GitHub estava sob
   `not eh_tv()`, porque a release publicava o APK de celular. Agora a release
   publica o universal, então a reserva vale nas duas variantes (o tamanho
   continua sendo conferido).

## 4. Fundo da tela de pastas (item 4)

**Não mexi.** A tela já estava com o cinza do tema, não com branco:

- `backgroundcolor` = `background` = `FF000000` (preto do tema);
- painel da lista `E6101010`, cartão normal `F2262626`, foco `FF3A3A3A`;
- não existe `B3FFFFFF` (o branco chapado que estourava);
- as duas skins (`skin.novatv` e `skin.estilo.personalizado`) são idênticas.

Os `TelaDePastasTest` cobrem exatamente essas propriedades e passam. Alterar
algo aqui só por mexer contrariaria o pedido de preservar a identidade visual.

## 5. Os três ciclos de teste

### Ciclo 1 — build e artefato (executado de verdade no CI)

Run [44541124229](https://github.com/msmacrosmart-cpu/KODE/actions/runs/44541124229)
(1.0.124) e [44543668744](https://github.com/msmacrosmart-cpu/KODE/actions/runs/44543668744)
(1.0.125), ambos **success** em todos os passos:

- APK universal gerado: `build/universal/SMARTEDTV-universal.apk`, 287299613 bytes;
- **um** arquivo: `ls` da pasta de build depois do `rm -f .../SMARTEDTV-tv.apk`;
- ABIs 32/64 no mesmo arquivo, laudo: "identidade, SDK 21, ABIs 32/64,
  assinatura v1/v2/v3 e certificado";
- `smartedtv.full`, versionCode 2103110/2103111, versionName 1.0.124/1.0.125;
- sem marcador de variante (trava do `build.sh` passou);
- emulador API 30: instalação limpa (`armeabi-v7a`) e atualização por cima da
  v22 sem desinstalar (`arm64-v8a`), abertura por `LAUNCHER` e por
  `LEANBACK_LAUNCHER`;
- `.github/workflows`: falha do Ciclo 1 (teste da pasta antiga) reproduzida
  localmente, corrigida e revalidada.

### Ciclo 2 — comportamento por aparelho

Automatizado, **não** em aparelho físico:

| cenário | resultado |
| --- | --- |
| celular → dispara a Activity AdMob do APK | passa |
| TV → **não** dispara AdMob | passa |
| TV → pede anúncio de vídeo (VAST) e não AdMob | passa |
| TV sem tag → não pede nada e não quebra | passa |
| VAST: impressão e quartis na ordem, wrapper, timeout, criativo inválido | passa |
| anúncio que não inicia não vira impressão; player recusando não conta como exibido | passa |
| ao vivo reabre sem seek; filme retoma na posição | passa |
| VIP sem anúncio em qualquer perfil | passa |
| navegação por controle (keymap/voltar), boot entrada→Home | passa |
| detecção: `Android.TV`, marca do aparelho, tela HD, dúvida → celular | passa |

Total: 170 testes (1 skip pré-existente), mais `static-check` (229 XML, 77
scripts).

### Ciclo 3 — repetição e integridade da publicação

- suíte e testes de anúncio repetidos depois de cada correção: sem regressão
  nova (nenhum `FAIL`/`ERROR` que exista no meu estado e não exista na base);
- a trava de `versionCode` **recusou** republicar 1.0.124 (run 44542530123,
  falha esperada e desejada) — por isso a versão final é 1.0.125;
- `v1.0.124-universal`, que era um passo intermediário, foi apagada (release e
  tag);
- assistentes `SMARTEDTV-tv.apk` removidos de `v1.0.123-universal` e
  `v1.0.122-universal`: nenhuma release oferece dois APKs;
- conferência do arquivo publicado: SHA-256
  `b3ce351449e6e8e5f351dc19d546447c34130df72c16b36b4ea86b5891568b94` e
  287299613 bytes, idênticos ao log do build do mesmo run.

**Não foi testado, por falta de aparelho físico** (nem CI substitui isso):
anúncio tocando numa TV real, controle remoto de uma TV real, e a instalação
por cima numa TV real. A prova no aparelho continua sendo
**Ajustes → Testar anúncio**.

## 6. Release final

`v1.0.125-universal` (**Latest**), com **exatamente um** arquivo:
`SMARTEDTV-universal.apk`. Título e notas falam de um único APK.

## 7. Dropbox: pendência externa, e o motivo

A pasta **`SMARTEDTV UNIVERSAL`** foi criada e está pública
(`/scl/fo/0f1ux2r4p8mooqyeswy0y/…`), e o app procura `SMARTEDTV.apk` nela. Ela
está **vazia**: o `SMARTEDTV.apk` ainda não foi enviado, porque

- o sandbox não alcança `api.dropboxapi.com` (só GitHub/npm/PyPI), e o conector
  do Dropbox recusa arquivo acima de 100 MB — o APK tem 274 MB.

Caminhos para fechar: baixar de `releases/latest/download/SMARTEDTV-universal.apk`
e subir pela interface do Dropbox com o nome `SMARTEDTV.apk`, **ou** liberar
rede/SDK do Dropbox no ambiente para eu publicar pelo `upload_session`.

Enquanto a pasta estiver vazia, a atualização **não fica sem saída**: o
`resolver_apk_publicado()` cai para a release do GitHub, que hoje tem o universal.

## 8. Achado durante a conferência (sem mudança de comportamento)

O link fixo `DROPBOX_URL` (`/scl/fi/adn9elzkj...`) hoje entrega
**`SMARTEDTV-2atual.apk`** (a v22, 242 MB), não o `SMARTEDTV.apk` — o `/scl/fi/`
resolve pelo **ID do arquivo**, não pelo nome. O app recusa esse arquivo pela
conferência de nome e segue para a pasta/release, então ninguém instala a versão
errada; o comentário no código passou a registrar o fato.
