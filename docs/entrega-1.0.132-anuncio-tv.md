# SMARTEDTV 1.0.132 — tag VAST nova e anúncio na TV

APK: `SMARTEDTV-universal.apk` • SHA-256
`b8154bf20aad3df75175843c67fc54172436fad65f22372dd125eaad820ae4f7` •
287312095 bytes • 1.0.132 / código 2103118.

---

## 1. A tag pedida, e o que ela devolve de verdade

Tag do projeto (HilltopAds):

```
https://vapid-size.com/dEmwF.zYdOGYNKvRZ/GoUG/beLmU9TuDZrUJl/koPpTRcX2iNbDMED3/NzDLkpt/N/zFYf0/MsTEcv1sMXwC
```

Medida no runner do CI (o sandbox de trabalho **não** alcança esse domínio —
só GitHub/npm/PyPI —, então a medição foi feita onde há internet, com o
**módulo real** do app):

| etapa | resultado real |
| --- | --- |
| resposta da tag | `http=200`, `text/xml`, ~9,3 KB |
| conteúdo | `<VAST version="3.0">`, 1 `<Ad>`, 1 `<InLine>`, `HilltopAds` |
| criativo | `video/mp4`, **36 s**, `skipoffset 15 s` |
| arquivo do anúncio | `http=200`, `video/mp4` (aberto e lido) |
| impressão/tracking | 1 `<Impression>`, eventos `start`/quartis/`complete` |
| player | recebeu a URL do MP4 do anúncio |

Evidência (run `44594818816`, job "Diagnostico da tag VAST"):

```
tag = https://vapid-size.com/dEmwF.zYdOGYNKvRZ/GoUG/beLmU9TuDZrUJl/koPpTRcX2iNbDMED3/NzDLkpt/N/zFYf0/MsTEcv1sMXwC
resposta: 9290 bytes
criativo = https://www.dismal-library.pro/152327/199275/559488_449f5y.mp4
tipo=video/mp4 duracao=36.0s skip=15s impressoes=1
arquivo do anuncio: http=200 tipo=video/mp4 bytes=4096
player receberia = https://www.dismal-library.pro/152327/199275/559492_3f3f4y.mp4
RESULTADO: caminho completo ate o player (anuncio real, nao simulado)
```

## 2. O defeito que a tag nova revelou (e que já era fatal com ela)

A primeira leitura dessa tag devolveu **`escolher_anuncio = None`** —
`vast-sem-criativo` —, apesar de o XML ser VAST válido. Causa:

```xml
<VAST version="3.0" xmlns="http://www.w3.org/2001/XMLSchema">
```

O XML declara **namespace default**. O `ElementTree` então entrega as tags como
`{http://www.w3.org/2001/XMLSchema}Ad`, `{...}InLine` — e o leitor procurava
`'Ad'`, `'InLine'`, `'Linear'`: encontrava **zero** e desistia. Nenhum anúncio
tocaria na TV, mesmo com tag boa, rede boa e player bom.

Correção: `sem_namespace(xml)` — remove declarações `xmlns` e prefixos
(`vmap:AdBreak` → `AdBreak`) antes de ler. Aplicado em `tag_do_wrapper`,
`tag_do_vmap` e `escolher_anuncio`. **Nenhuma outra função foi alterada** e
o arquivo continua inteiro (13 funções públicas + constantes, checadas por
teste).

## 3. O anúncio continua exclusivo da TV

| onde | o que acontece |
| --- | --- |
| Android TV / TV Box / stick / projetor (`eh_tv()`) | anúncio de **vídeo VAST** da tag do projeto, tocado pelo player do Kodi |
| celular / tablet | **AdMob** da activity nativa, como antes; **zero** pedido VAST |

Provado em `tests/test_vast_tag_padrao.py::ConfinamentoAoModoTVTest`:
na TV a tag do projeto é pedida; no celular **nenhuma** tag VAST é pedida e o
`StartAndroidActivity` do AdMob é disparado.

## 4. Testes executados nesta rodada

| suíte | resultado |
| --- | --- |
| `test_vast_tag_padrao` (tag + namespace + confinamento) | **14 OK** |
| `tests` (ads): `test_ads_por_dispositivo`, `test_ads_vast_tv`, `test_ads_vmap_tv` | OK |
| suíte completa | 601 testes, `failures=11, errors=13` |
| comparação com a base (`git stash`) | **0 regressões**, 0 novas falhas |

As 24 falhas restantes são as **pré-existentes** de skins antigas
(layout/teclado/cores) — nenhuma toca anúncio, addon, navegação ou versão.

## 5. O que NÃO foi provado (e o que fazer)

- **Anúncio tocando numa TV física:** não existe TV/box aqui. O AVD do CI é
  **celular** (API 30, sem leanback) e não tem `python3` no shell — por isso
  removi os dois scripts que eu havia posto para "provar dentro do aparelho":
  eles não poderiam funcionar e eu não deixo prova falsa no projeto. O smoke
  agora diz isso explicitamente.
- **Como fechar em 1 minuto:** instalar este APK na TV → **Ajustes → Testar
  anúncio**. O vídeo de 30 s do HilltopAds deve tocar antes do conteúdo, com
  "Pular" após 15 s. Se não tocar, o `kodi.log` terá as linhas `[SmartAds]` com
  a etapa exata (`tag-sem-resposta`, `vast-sem-criativo`, `player-recusou`,
  `nao-iniciou`).
- A tag entrega **anúncios diferentes a cada pedido** (o CI recebeu criativos
  distintos em cada execução) — isso é normal em rede de anúncios.

## 6. Nada mais foi alterado

Tudo o que já estava aprovado segue igual: único APK universal, ARM 32/64,
Android 5+, AdMob no celular, VIP sem anúncios, regra de frequência, addons,
navegação da Home, canais/filmes/séries, Lovable, checkout Cakto, QR Codes,
splash e atualização por Dropbox/GitHub. O CI desta versão repetiu as provas do
APK: módulos do addon presentes no APK instalado, instalação limpa (v7a),
atualização (arm64), os dois launchers e 3 reaberturas com imagem.
