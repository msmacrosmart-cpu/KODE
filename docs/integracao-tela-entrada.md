# Integração da tela inicial do ZIP — SMARTEDTV / Kodi Omega 21

**Origem:** `SMARTEDTV_Kodi_Omega_Welcome.zip` (Dropbox, 34.636 bytes,
SHA-256 `758b017aaa3b040be0e7a0baa0d49ecbcc168077303fb4493dc03883670c9bc4`).
Addon entregue: `script.smartedtv.welcome` (15 arquivos).

**Regra aplicada:** a tela foi copiada **integralmente**, sem redesenho. Nenhum
XML, cor, fonte, texto, posição, cartão, imagem, espaçamento, proporção ou QR
Code foi alterado. A interface principal (`Home` / `skin.novatv`) continua
intacta e não foi substituída.

---

## 1. O que foi copiado (byte a byte)

Destino: `kodi/addons/script.smartedtv.welcome/`.

| Arquivo | Bytes | SHA-256 (16) |
|---|---:|---|
| `addon.xml` | 600 | `a607b7d8771d447b` |
| `README.txt` | 1.241 | `b973624b077a4749` |
| `resources/__init__.py` | 0 | `e3b0c44298fc1c14` |
| `resources/skins/Default/1080i/DialogWelcome.xml` | 10.765 | `41d3d7cfbbe514d9` |
| `resources/skins/Default/media/welcome_background.png` (1920×1080) | 28.245 | `84000614326f58e1` |
| `resources/skins/Default/media/overlay_black.png` (1920×1080) | 10.620 | `332a498541645db2` |
| `resources/skins/Default/media/dialog_panel.png` (820×350) | 2.234 | `f5d01c26eda92e8d` |
| `resources/skins/Default/media/qr_1.png` (444×444) | 2.200 | `11f24709a55fc410` |
| `resources/skins/Default/media/qr_2.png` (444×444) | 2.224 | `3d91d28c9d883de5` |
| `resources/skins/Default/media/button_dark.png`, `white.png`, `edit_focus.png`, `edit_nofocus.png` (64×64) | 329 / 294 / 316 / 310 | — |
| `resources/skins/Default/media/separator.png` (2×64) | 83 | — |

`DialogWelcome.xml` está **idêntico ao do ZIP**: 1920×1080, `<defaultcontrol>310`,
todos os ids (1, 10/11, 20–25, 30–33, 40–43, 50–52, 60, 120, 121, 130/131,
310/311/312, 900–906) e o modal `show_free_dialog` permanecem como entregues.

`default.py` é o único arquivo do ZIP adaptado — apenas nos pontos de integração
(action handlers, log de pendências e `ActivateWindow(Home)`); nenhuma parte
visual foi tocada. O `addon.xml` (`xbmc.python.script`, `xbmc.python` 3.0.0)
também está idêntico.

---

## 2. Pontos de integração (3 alterações em arquivos existentes)

| # | Arquivo | Alteração |
|---|---|---|
| 1 | `kodi/addons/service.smarted.bootstrap/service.py` | Constantes `WELCOME_ADDON` + função `abrir_tela_entrada(monitor)` + uma thread `welcome-entry` iniciada no começo de `main()`. Reaproveita `enable_addons()`/`jsonrpc()`/`log()` que já existiam no serviço de boot. |
| 2 | `tools/kodi/build-release-apk.py` | `script.smartedtv.welcome` entra em `BRIDGE_ADDONS`, para o addon ir a `assets/addons/` e ser registrado em `assets/system/addon-manifest.xml` (o workflow `build-release-apk.yml` já confere automaticamente todos os diretórios de `kodi/addons/`). |
| 3 | `docs/integracao-tela-entrada.md` + `tests/test_tela_entrada.py` | Este relatório e a validação. |

Nenhuma outra tela, skin, XML de layout, cor, módulo Python ou workflow foi
modificado.

### Fluxo de entrada

```
Kodi inicia → service.smarted.bootstrap (start="startup", já existente)
   └─ thread welcome-entry (nova, daemon, uma vez por boot)
        ├─ enable_addons([script.smartedtv.welcome])   [JSON-RPC já usado no boot]
        ├─ espera addon registrado + Home (janela 10000) pronta
        └─ RunScript(script.smartedtv.welcome)          [builtin do Kodi]
              └─ WelcomeDialog("DialogWelcome.xml", <addon>, "Default", "1080i")
                   └─ doModal() → tela 100% idêntica ao ZIP, cobrindo 1920×1080
                        └─ ação do usuário → close() → Home existente responde
```

O diálogo é **modal e independente**: a Home não é apagada nem substituída, só
fica por baixo. Se o addon não estiver disponível, o bootstrap registra o aviso
no log e **não abre nada** — o aplicativo continua exatamente como antes.
`open_welcome()` também captura qualquer erro de `doModal()` para a tela de
entrada nunca interromper o app.

**Navegação:** setas/OK são resolvidas pelo Kodi a partir das coordenadas do XML
(inalteradas); foco inicial `310` (`defaultcontrol always="true"` + `onInit`);
`ACTION_NAV_BACK` / `ACTION_PREVIOUS_MENU` fecham o modal de confirmação e, fora
dele, fecham a janela e devolvem a Home.

---

## 3. Mapeamento das ações → fluxos existentes

| Controle | Ação na tela | Fluxo no projeto | Situação |
|---|---|---|---|
| `312` | Continuar com anúncios | Modal de confirmação da própria tela (`show_free_dialog`, foco `905`) | ✅ reutilizado ( ZIP ) |
| `905` | Voltar (modal) | Fecha o modal, foco de volta em `312` | ✅ reutilizado ( ZIP ) |
| `906` | Confirmar modo gratuito | `ActivateWindow(Home)` — mesmo comando já usado pela skin (`MyFavourites.xml`, `MyVideoNav.xml`, `MyMusicNav.xml`) | ✅ encaminha para a interface principal existente |
| Voltar | Sair da entrada | `close()` + `ActivateWindow(Home)` | ✅ encaminha para a interface principal existente |
| `130` / `131` | Android TV / Celular | Seletor visual, sem fluxo no projeto | ⚠️ ver §4 |
| `310` + `311` | Código VIP / Ativar | **Não existe** validação VIP no projeto | ⚠️ ver §4 |
| `120` | Abrir checkout | **Não existe** abertura de checkout no projeto | ⚠️ ver §4 |
| `121` | Compartilhar link | **Não existe** compartilhamento nativo no projeto | ⚠️ ver §4 |

Nos casos ⚠️ o handler apenas grava `xbmc.log(..., LOGWARNING)` e **não simula
sucesso**, não valida código, não abre URL e não cria endpoint.

---

## 4. O que está faltando no projeto (nada foi inventado)

Foram procuradas primeiro as funções/integrações existentes em
`kodi/addons/*`, `kodi/skin*/xml/*`, `tools/kodi/*` e nos documentos do
repositório. Não foram encontrados módulos, settings, rotas de plugin,
`RunPlugin`, intents Android ou URLs de checkout/compartilhamento para estas
ações.

1. **Ativação VIP (`310` + `311`)** — falta uma função que leia o texto do
   `edit` 310 e valide o código. Não há no projeto: serviço de ativação,
   endpoint, credencial, tabela de códigos, setting de VIP, nem gravador de
   estado "assinante". Sem isso o botão `Ativar` só registra a pendência no log.
2. **Checkout (`120`)** — falta uma função já existente que abra o checkout.
   O repositório não contém nenhuma URL de pagamento nem chamada de
   browser/intent. O `qr_1.png` do ZIP codifica
   `https://pay.cakto.com.br/nkvbegd_1323120`; esse endereço existe **dentro da
   imagem entregue**, não como integração de código. Consultar o QR com a
   câmera de outro aparelho continua funcionando; o botão não foi ligado a
   nenhuma API nova.
3. **Compartilhamento (`121`)** — falta integração nativa de share (intent
   Android, addon ou função do app). O `qr_2.png` do ZIP codifica
   `https://smartedtv-vip.lovable.app/`, novamente apenas como imagem. O botão
   não foi ligado a nenhum serviço novo.
4. **Modo gratuito com anúncios (`906`)** — não existe camada de anúncios,
   provedor de anúncios, setting de "modo gratuito" nem fluxo de propaganda no
   projeto. A ação encaminha para a Home real (que hoje não exibe anúncios) e
   **não finge** que anúncios foram ativados. Falta a implementação de anúncios
   e o ponto de decisão gratuito/VIP se esse comportamento for desejado.
5. **Seletor Android TV / Celular (`130`/`131`)** — é apenas visual no ZIP; não
   há fluxo de troca de perfil de dispositivo no projeto.

Também não há, no repositório nem no Dropbox desta conta, **novos QR Codes ou
URLs de substituição**. Por isso os dois QR Codes foram mantidos exatamente
como vieram no ZIP (hashes acima), sem gerar links novos. Para trocar
**somente** os QR Codes, basta substituir `qr_1.png` e `qr_2.png` em
`resources/skins/Default/media/` — nenhum outro arquivo da tela precisa mudar
(apenas as duas entradas `qr_*.png` do mapa `HASHES_ZIP` em
`tests/test_tela_entrada.py`, que existe justamente para provar a fidelidade
ao ZIP).

---

## 5. Validação realizada

- `python3 tools/kodi/static-check.py` → todos os XML de `kodi/` e `tools/`
  bem formados e todos os `.py` compilados (`py_compile`), incluindo o novo
  `DialogWelcome.xml`, `addon.xml` e `default.py`.
- Conferência de dependências: todo `<texture>` citado no `DialogWelcome.xml`
  existe em `resources/skins/Default/media/` e são PNGs válidos; os 15 arquivos
  do addon batem byte a byte com o ZIP (exceção: `default.py`, só integração).
- `tests/test_tela_entrada.py` abre e fecha o `WelcomeDialog` com stubs de
  `xbmc`/`xbmcgui`/`xbmcaddon`: verifica `Default/1080i`, `doModal()`, foco
  `310`, modal `show_free_dialog`, `Voltar`, encaminhamento para
  `ActivateWindow(Home)` e que nenhuma ação sem fluxo simula sucesso.
- `python3 -m unittest discover -s tests` → suíte existente sem regressão.
- Empacotamento: `tools/kodi/build-release-apk.py` inclui o addon em
  `BRIDGE_ADDONS`; a checagem do workflow `build-release-apk.yml` já exige que
  **todos** os diretórios de `kodi/addons/` estejam no APK e no
  `addon-manifest.xml`.
- Suite completa + simulação de boot (`tools/kodi/simulate-first-boot.py`) não
  foi executada em Kodi real: este ambiente não tem Kodi, AVD/adbd nem KVM. A
  validação é estática e com stubs; a execução dentro do Kodi Omega 21 em
  aparelho 16:9 continua pendente de teste no dispositivo.

## 6. Build do APK final — **sem skin Bingie**

A pedido do usuário, **o APK final não é um rebuild com Bingie**: ele parte do
**APK atual publicado** (release `v1.0.83-unificado`, asset
`SMARTEDTV-atual.apk`) e recebe **apenas** a tela inicial. Nenhuma skin é
baixada, renomeada ou substituída; versão, motor, `classes.dex`, bibliotecas
nativas, perfil semeado e todas as outras entradas ficam byte a byte iguais.

Workflow: `.github/workflows/build-atual-com-tela.yml` (roda no CI, que tem
acesso ao APK publicado). Script: `tools/kodi/injetar-tela-entrada.py`.

| Passo | Ação |
|---|---|
| 1 | `static-check.py` (XML + Python) |
| 2 | baixa o APK atual da release `v1.0.83-unificado` |
| 3 | diagnóstico: lista addons/skins/perfil do APK antes de mexer |
| 4 | `tools/kodi/setup.sh` (Java 17 + apksigner) |
| 5 | injeta os **15 arquivos** do ZIP em `assets/addons/script.smartedtv.welcome/`, registra o addon no `assets/system/addon-manifest.xml` e acrescenta o gancho `welcome-entry` no `service.smarted.bootstrap/service.py` **que já está no APK** |
| 6 | confere que **exatamente 15 entradas foram adicionadas** e **apenas 2 foram adaptadas**; perfil semeado intacto; `service.py` compila; XML e QR Codes idênticos ao ZIP |
| 7 | `align-apk.py` + assinatura com a **mesma chave** (`dropbox/smarted-tv-test.jks`, certificado `855de171…`) |
| 8 | publica numa release própria (`v1.0.83-tela-inicial`), sem sobrescrever a release atual |
| 9 | publica blocos do APK para reconstrução no workspace |

`tests/test_injetor_tela_entrada.py` reproduz o passo 5 com um APK sintético,
sem precisar do Kodi nem do APK real.

**Limite do ambiente:** o sandbox só alcança `github.com`/`api.github.com`, e
os assets de release ficam em `release-assets.githubusercontent.com`; por isso
o download e a assinatura são feitos no runner do GitHub Actions, não aqui.

### Dependências de skin (observação)

`DialogWelcome.xml` usa `font10/12/13/14/16/20/22/24/30`, resolvidos pelo
Kodi a partir do fontset da skin ativa. A skin padrão do APK (`skin.novatv`,
base Bingie/Estuary) define essa família; a skin clássica define parte dela e o
Kodi faz fallback automático. Nenhum `Font.xml` foi acrescentado para não
alterar a renderização entregue no ZIP.
