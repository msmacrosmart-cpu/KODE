# Entrega v13 — TV, Box, Projetor e Stick

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.83-tela-inicial-v13/SMARTEDTV-atual-com-tela-inicial-v13.apk  
**Tamanho:** 250.491.256 bytes (~239 MiB)  
**SHA-256:** `1dbaea3de1cee12c20e7499e7cb53eae1b922ddd9acd19abd665a4e3f3a34818`  
**Release:** https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.83-tela-inicial-v13  
**Commit do build:** `cb6d27a` (run `44113164576`)  
**Base:** v12 (`v1.0.83-tela-inicial-v12`) — nada do visual, VIP ou anúncios foi removido.

## O que mudou

A tela inicial agora tem **duas variantes do mesmo layout**:

| Arquivo | Quando abre |
|---|---|
| `DialogWelcome.xml` | Celular/tablet (layout original, sem margem) |
| `DialogWelcomeTV.xml` | TV, box, projetor e stick (área segura contra overscan) |

A variante TV é **gerada** por `tools/kodi/gerar-tela-tv.py` a partir da tela
normal (não editar à mão). Ela:

- desce logo/título/subtítulo 20 px e recua o bloco esquerdo 62 px;
- sobe a barra do código para 880 e a linha campo/Ativar/Assistir para 892;
- recua a barra e os textos do rodapé para dentro dos 5% laterais (x=96/100);
- troca a dica por **“Use as setas e OK do controle.”**.

Nada foi escalado: as fontes continuam as mesmas do layout aprovado, sem risco
de texto estourar. O `defaultcontrol` continua **310** (campo do código), então
no controle remoto o OK já abre o teclado do Kodi e as setas navegam.

## Como o app escolhe a variante

`script.smartedtv.welcome/default.py` (`_modo_tv()`):

1. **`plataforma.txt`** (gravado pelo Java `Plataforma.detectar()` em
   `getFilesDir()`, lido via `special://home/../plataforma.txt`) manda;
2. sem o arquivo, detecta **TV/box/projetor/stick** por:
   - resolução 16:9 com pelo menos 1280×720 (`System.ScreenResolution`), ou
   - nome do aparelho (`System.FriendlyName`) com tv/box/stick/fire/aft/shield/
     chromecast/projetor/leanback;
3. grava o resultado em `plataforma.txt` para o Java usar no mesmo boot.

O Java `AdTela` já lê esse arquivo (`Plataforma.eTV()`) para nascer com o botão
**“Pular anúncio”** focado no controle remoto; o D-pad nunca entra no anúncio e
a tela fecha sozinha (20 s sem anúncio / 45 s com anúncio), sem derrubar o app.
Em aparelho sem Google Play (Fire OS), o AdMob simplesmente não preenche e a
tela fecha sozinha.

## O que já estava pronto no APK e continua valendo

- `LEANBACK_LAUNCHER` na `Splash` + banner de TV;
- `android.software.leanback` e `android.hardware.type.television` **opcionais**;
- `android.hardware.touchscreen` **não obrigatório**;
- orientação paisagem e `configChanges` que não recriam a tela;
- campo 310 aceita `REMOTE_0..9` e o teclado real do Kodi;
- botões 120–123 continuam com as mesmas ações e o mesmo visual;
- anúncios: um por troca de conteúdo, nenhum para VIP, um app-open por instalação;
- VIP: só ativa com `POST /api/public/validar-codigo` e `active:true`.

## Provas deste build

- `tools/kodi/static-check.py`: 215 XML válidos, 62 scripts compilados;
- `tests/test_tela_entrada.py::TVBoxStickTest`: variante TV com área segura,
  detecção por resolução e escolha do XML;
- `DialogWelcomeTV.xml` byte a byte igual dentro do APK (workflow, passo 6);
- injeção byte a byte dos demais arquivos (passo 6) e assinatura com a mesma chave;
- não houve execução em TV/box/stick reais neste ambiente; a prova é estática +
  simulador de boot. Se algum aparelho cortar mais de 5%, use o ajuste de tela
  do Kodi (`Configurações → Sistema → Vídeo → Calibrar tela`).

## Reverter / voltar ao layout de celular

Apague `plataforma.txt` e mude a resolução para menos de 1280×720 (ou use o
seletor de modo do app, quando disponível). O `DialogWelcome.xml` original
continua intacto no APK.
