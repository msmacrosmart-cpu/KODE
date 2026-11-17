# Entrega v11 — correção dos botões 120/121 (SMARTEDTV)

Data: 2026-11-17 · branch `arena/39a14845-kode` · base da continuidade `14296af`

## 1. APK final

| item | valor |
|---|---|
| release | [`v1.0.83-tela-inicial-v11`](https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.83-tela-inicial-v11) |
| download | https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.83-tela-inicial-v11/SMARTEDTV-atual-com-tela-inicial-v11.apk |
| arquivo | `SMARTEDTV-atual-com-tela-inicial-v11.apk` |
| tamanho | 250.441.953 bytes (238,8 MiB) |
| SHA-256 | `b7bc725a0eda9c167eb0c2609308552e863e303103e23919d4a1630e5284d0cb` |
| assinatura | mesma chave do app (certificado `855de171…0951a`, conferido no passo 7) |
| build | [run 44100711709](https://github.com/msmacrosmart-cpu/KODE/actions/runs/44100711709) — **sucesso em 2m33s** |

O APK foi reconstruído a partir dos blocos publicados pelo próprio build
(passo 9) e o SHA-256 bateu com o registrado nas notas da release.

## 2. Commits

| commit | conteúdo |
|---|---|
| `f9d44e1` | correção do `vip.py` + mapeamento 120/121 + testes |
| `9bdae25` | pipeline rápida passa a rodar neste branch e gera a tag v10 (descartada: ainda levava o `vip.py` antigo) |
| `1fb89cb` | injetor substitui o `vip.py` do APK base + passo 6b bloqueante + build v11 |

Nada foi resetado: o branch foi avançado por *fast-forward* até o trabalho
anterior (`14296af`) antes das alterações, preservando todos os commits da tela
inicial, da aba VIP, do QR sem moldura e do VOLTAR na Home.

## 3. Causa raiz dos botões que não abriam

O builtin do Kodi tem a assinatura:

```
StartAndroidActivity(package,intent,dataType,dataURI[,flags,extras,...])
```

(`xbmc/interfaces/builtins/AndroidBuiltins.cpp`, Omega). O primeiro parâmetro é
o **pacote Android**, não a action. O código anterior fazia:

```
StartAndroidActivity(android.intent.action.VIEW,https://…,,)
```

ou seja, o Kodi procurava um pacote chamado `android.intent.action.VIEW`; o
intent morria e nenhum navegador abria. A correção usa o pacote vazio:

```
StartAndroidActivity(,android.intent.action.VIEW,,https://…)
```

No Android o pacote vazio vira `null` (jstring NULL em `libandroidjni`), isto é,
intent implícito: o sistema abre o **navegador padrão** por cima do Kodi.

Além disso, o APK base `v1.0.83-unificado` **já trazia um `vip.py` antigo**.
O injetor pulava arquivos existentes, então a versão corrigida não entrava no
APK e o botão chamava o código antigo. Agora o injetor descarta o `vip.py` do
APK e grava o do repositório (uma única entrada, conferida byte a byte).

## 4. Mapeamento conferido

| ID | rótulo na tela | ação | destino |
|---|---|---|---|
| **120** | Abrir checkout | `_abrir_checkout()` → `vip.abrir_checkout()` | `https://pay.cakto.com.br/nkvbegd_1323120` (conteúdo do QR `qr_checkout.png`) — navegador externo |
| **121** | Compartilhar link | `_abrir_dropbox()` → `vip.abrir_dropbox()` | `https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j&st=p1m6ebvg&dl=0` — navegador externo |
| 121 (toque longo) | — | `_compartilhar()` → `vip.compartilhar()` | `ACTION_SEND` nativo (WhatsApp/Telegram/Gmail) com o link do APK |
| 122 | Baixar APK (Android) | `_baixar_apk()` → `vip.open_apk_download()` | mesmo link do QR com `dl=1` — navegador externo |
| 123 | ATUALIZAR APLICATIVO | `_atualizar()` → `vip.procurar_atualizacao()` | OTA ou página do Dropbox |
| 310/311 | campo/Ativar | `vip.validar()` | `/api/validar` e `/functions/v1/validar-codigo` |
| 312/905/906/955 | anúncios/status | fecha diálogo / libera Home | — |

O endereço do Dropbox **não foi inventado**: foi decodificado do próprio QR
`qr_apk.png` do pacote (com `rlkey`; sem ele o link `/scl/fi/` não abre). O
checkout é o mesmo do QR `qr_checkout.png` e da configuração já existente
(`pay.cakto.com.br`).

Nas duas interfaces:
- **Tela inicial** (`script.smartedtv.welcome` / `DialogWelcome.xml`): os 10
  controles clicáveis têm ação no `default.py` — `tools/kodi/mapear-botoes.py`
  sai com “Todos os botoes do layout tem acao mapeada”.
- **Área VIP** (cartão “Ativação e assinatura”, onde ficam 120/121/122): mesmos
  IDs, mesmas rotas, sem remover controle e sem mudar o desenho.
- **Home das skins**: `skin.estilo.personalizado` 68 botões, `skin.novatv`
  7 botões — todos com `onclick`; `skin.smartedtv.bingie` tem só o botão oculto
  `1000` de foco (o menu real vem de includes). Nenhum ID duplicado.

## 5. Verificações executadas

| verificação | resultado |
|---|---|
| `tools/kodi/static-check.py` | 214 XML válidos, 60 scripts compilados |
| `tools/kodi/mapear-botoes.py` | 10/10 controles mapeados, sem sobra |
| testes `tests/test_vip_botoes_android.py` | 7/7 — ordem do builtin, URLs, ACTION_SEND |
| testes `tests/test_tela_entrada.py` (ciclo + botões + mapa) | 30/30 |
| simulador de boot no APK final | OK (Startup antes da Home, 120→checkout, 121→Dropbox, VOLTAR na Home) |
| conteúdo do APK | `default.py`, `vip.py`, `DialogWelcome.xml` e keymap **byte a byte** iguais ao repositório; `vip.py` com 1 entrada; QR intactos |
| assinatura | apksigner OK, certificado igual ao app |

**Não houve teste em aparelho Android real** (não há dispositivo/emulador neste
ambiente). A abertura do navegador foi validada estaticamente e por stubs; a
confirmação final é instalar o APK e tocar em 120/121.

## 6. Pendência consciente: o arquivo no Dropbox

O link do Dropbox usado por 121/122 resolve hoje para
`/SMARTEDTV-2atual.apk` (242.222.254 bytes, modificado em 2026-11-17 02:39) —
isto é, o build **v9**, que ainda tem o `vip.py` antigo. O APK v11 está na
release do GitHub. O upload pelo conector do Dropbox é limitado a 100 MB, então
não foi possível substituir o arquivo automaticamente.

Para que o próprio botão 122 entregue o v11, basta substituir
`/SMARTEDTV-2atual.apk` no Dropbox pelo arquivo da release (mesmo nome). Se
preferir, o link de 121/122 também pode apontar para a release do GitHub — é uma
linha em `vip.py` (`DROPBOX_URL`/`APK`) e outra no fallback do `default.py`.

## 7. Arquivos alterados nesta continuidade

```
.github/workflows/build-atual-com-tela.yml       (tag v11, passo 6b, simulador bloqueante)
docs/integracao-tela-entrada.md                  (causa e mapeamento)
kodi/addons/script.smartedtv.welcome/default.py  (120/121/122/123, toque longo)
kodi/addons/service.smarted.bootstrap/vip.py     (builtin correto, abrir_dropbox, urllib py3)
tests/test_tela_entrada.py                       (fakes + testes dos fallbacks)
tests/test_vip_botoes_android.py                 (novo)
tools/kodi/injetar-tela-entrada.py               (substitui vip.py do APK base)
tools/kodi/mapear-botoes.py                      (abrir_dropbox)
tools/kodi/simular-boot-tela-entrada.py          (121 → Dropbox)
```
