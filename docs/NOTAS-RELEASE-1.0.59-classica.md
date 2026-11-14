# SMARTED-TV 1.0.59 (linha clássica) — player abrindo na hora

Base: **1.0.58 clássica** (sha256 `ece4fb03cde87beb7fb351c3683c1cb5f834eb6270783daf97429eaca7cee6cf`).
Nada do Kodi foi recompilado: o APK foi reempacotado e o único add-on trocado foi o
**service.smarted.bootstrap** (1.0.8 → 1.0.9). Skin continua 1.0.18 (sem mudança visual).

## Onde estavam os 10–20 segundos

O tempo não era do decoder, era de espera. Três coisas seguravam o primeiro frame:

1. **`advancedsettings.xml` antigo**: `buffermode 4` + `memorysize 256 MB` + `readfactor 10`.
   O modo 4 guarda cache de *tudo* e o player não libera o vídeo antes de encher o buffer
   configurado — com 256 MB, isso é espera garantida em qualquer internet.
2. **Troca de modo de vídeo** (`adjustrefreshrate` ligado): cada abertura pisca a tela e
   custa 1–3 s antes do primeiro frame.
3. **Trabalho nosso no caminho do clique**: o `nav-check` (varredura de todas as pastas da
   barra por `Files.GetDirectory`, JSON-RPC) rodava **na linha do boot, antes** de o
   desempenho ser aplicado, e o loop de 1800 s reabria os nós da Home no meio do uso.

## O que mudou nesta versão

| Item | Antes | Agora |
|---|---|---|
| `filecache.buffermode` | 4 (tudo) | **1** (stream da internet) |
| `filecache.memorysize` | 256 MB | **50 MB** (`<memorysize>52428800</memorysize>`) |
| `filecache.readfactor` | 10x | **20x** (`<readfactor>20.0</readfactor>`) |
| `chunksize` | padrão | **512 KB** |
| `videoplayer.adjustrefreshrate` | ligado | **0 — desligado** |
| MediaCodec / Surface | — | ligados |
| `curlclienttimeout` / `curllowspeedtime` | padrão | **15 s / 20 s** |
| `apply_performance()` no boot | depois do nav-check | **antes de tudo** |
| `nav-check` | síncrono no boot | **20 s depois, em segundo plano, e nunca com vídeo tocando** |

O buffer de 50 MB é de propósito: enche em poucos segundos numa conexão de 30–100 Mbps e
já libera o player. Continua sendo cache (nada de vídeo travando por rede instável), só que
curto — e o `readfactor` 20x faz o Kodi ler 20x o bitrate para reabastecer.

Detalhe de coerência: a lista de valores aceitos pelo Kodi em *Configurações → Vídeo → Cache*
é fechada (16, 20, 24, 32, 48, 64…), então o ajuste via JSON-RPC usa **48 MB** (o valor cheio
mais próximo de 50) e o `advancedsettings.xml` manda **50 MB em bytes**. Quem vale no boot é
o `advancedsettings.xml`.

## Sobre "player nativo direto, sem diálogo de fonte"

Quando o link é direto, o Kodi Omega já toca no player nativo sem diálogo — não existe
diálogo de escolha de fonte no caminho. O que existia era **espera**: buffer grande, troca de
modo de vídeo e concorrência com a nossa varredura de pastas. Isso foi resolvido acima.
O `resolve` do link em si é do **Brazuca Play** (add-on de terceiro, embutido no APK) — não é
código deste projeto e não foi alterado; por isso a versão não mexe em `plugin.video.smarted`.

## Como conferir depois de instalar

1. Abrir um conteúdo e contar até o primeiro frame (era 10–20 s).
2. Em `userdata/advancedsettings.xml` deve estar `<buffermode>1</buffermode>`,
   `<memorysize>52428800</memorysize>` e `<readfactor>20.0</readfactor>`.
3. No `kodi.log`, o boot deve mostrar
   `pronto após N tentativa(s): … otimizações` **antes** de qualquer `nav-check:`.
4. `nav-check: N destinos testados` aparece ~20 s depois do boot (ou é adiado se houver
   vídeo tocando) — nunca mais no meio da abertura do player.

## Conferência automática no build

O workflow `build-release-classica.yml` falha o build se, dentro do APK publicado:

- o `addon.xml` do skin não estiver em 1.0.18;
- as fileiras da Home não estiverem em `top=570 h=194` (9201) e `top=822 h=194` (9203),
  com a 9202 ausente;
- `MyVideoNav.xml` perder o painel `CC121212` ou o foco `FF1E1E1E`;
- o `performance.py` embarcado não tiver `buffermode 1`, `memorysize 52428800`,
  `readfactor 20.0`, o marker `smartedtv-performance-v2`, os settings novos
  (`memorysize 48`, `readfactor 2000`, `adjustrefreshrate 0`);
- o `service.py` embarcado voltar a chamar `apply_performance()` depois do nav-check;
- `versionName`/`versionCode` não forem `1.0.59` / `2103045`.
