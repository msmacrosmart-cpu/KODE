# SMARTEDTV v17 — retoques finais (foco, anúncios, Home e saída)

**Versão:** 1.0.87 / 2103073 (`v1.0.87-responsivo-v17`)
**Commit do código desta rodada:** `070cc08`
**Pipeline rápido:** `build-v17-responsivo.yml`, execução **44154344425** (sucesso)
**APK:** `SMARTEDTV-atual-v17-responsivo-universal.apk` (release `v1.0.87-responsivo-v17`)

> Este documento separa o que foi **validado em teste automatizado/simulador** do
> que **só pode ser confirmado em aparelho físico**. Não há declaração de
> compatibilidade universal.

---

## 1. Aviso de anúncio: um único foco e D-pad previsível

### Causa real encontrada

1. `btn_primary.png` e `btn_primary_focus.png` eram o **mesmo desenho**. O botão
   "Continuar com anúncios" (textura primária) parecia branco/selecionado mesmo
   sem foco, enquanto o "Voltar" (textura quiet) só aparecia quando focado.
   Resultado visual: **dois botões pareciam selecionados**.
2. A tela podia receber foco antes de o grupo 900 (`ads`) ficar visível. Um
   `setFocusId()` no mesmo quadro em que o grupo é mostrado é descartado pelo
   Kodi; o foco continuava no controle anterior/invisível.
3. O `setFocusId` era disparado uma vez, sem conferir se o Kodi aceitou. Não
   havia confirmação de foco depois da animação de abertura.

### Correção aplicada (lógica, não cosmética)

- **Texturas:** `btn_primary.png` passou a ser escuro (R22G22B22, borda cinza) e
  `btn_primary_focus.png` branco com borda preta de 3 px. Só o controle focado
  fica branco. Os textos 311/906/955 usam `FFF7F7F7` normal e `FF080808` no foco
  (contraste nos dois estados).
- **`_focar` da tela de entrada:** espera o grupo 900 ficar visível
  (`Control.IsVisible(900)`), tenta `setFocusId(905)` até 8 vezes com 50 ms entre
  elas e faz **uma confirmação extra de 80 ms**. Se o Kodi devolveu o foco para
  906 sozinho, tenta de novo uma vez. Nunca deixa o foco em controle invisível.
- **`defaultcontrol` do diálogo continua 310**; o foco inicial não é fixado no
  XML para não brigar com o `setFocusId` do Python.
- **Setas:** o Python só consome ←/→/OK quando o foco atual é um dos botões do
  anúncio. Fora disso, deixa o Kodi navegar. OK executa **o controle focado**
  (905 = assistir com anúncio; 906 = voltar), sem atalho por posição.
- **Voltar:** o botão Voltar e o Back do controle fecham o diálogo e devolvem o
  foco à tela anterior (`_fechar_dialogo`), sem prender foco.
- **IDs/visibilidade:** 905 e 906 são os únicos controles do grupo 900; o grupo
  só é mostrado no estado `ads`. Nenhum controle invisível recebe foco.

### Validação

- `tests.test_tela_entrada.CicloDeVidaTest`: **23 testes OK**, incluindo
  - foco inicial em 905;
  - foco restaurado em 312 ao fechar;
  - ←/→/OK agindo no foco atual;
  - Back fechando o diálogo;
  - texturas normal/foco diferentes e `textcolor`/`focusedcolor` corretos.
- `auditar-tela-entrada.py --falhar` e `--layout ... DialogWelcomeTV.xml`: OK.
- `auditar-responsivo.py --falhar`: 116 controles em 720p/1080p/4K, sem corte.

**Pendente em hardware:** repetir com controle D-pad real em TV Android, box e
projetor. O teste automatizado usa o stub do Kodi; não substitui o aparelho.

---

## 2. Home: HERO → grades → HERO

### O que estava errado

A lista do HERO (`9100`) não tinha `onup`/`ondown`; as grades (`grouplist 9500`)
não tinham navegação vertical. O D-pad para baixo a partir do HERO não tinha
destino declarado e o Kodi escolhia o controle geometricamente mais próximo —
às vezes um botão invisível do próprio HERO.

### Correção

- `9100` (HERO):
  - `onup` → `9000` (barra superior);
  - `ondown` condicional → `9500` **somente** se as grades estiverem visíveis
    (`!Skin.HasSetting(hide_widgets)`) e com itens
    (`Container(9500).NumItems > 0`);
  - fallback `ondown` → `9110` (botões do HERO) quando não há grade.
- `9500` (primeira grade):
  - `onup` condicional → `9100` se o HERO estiver visível (`!hide_hero`);
  - fallback `onup` → `9000`.
- Botões do HERO `9110/9111/9112`: `onup` → `9100` (sobem ao HERO, não à barra
  superior). `ondown` já era `9500`.

Nenhuma posição, tamanho, cor, fonte ou widget foi alterado. As regras são XML
nativo (`onup`/`ondown` + condições), sem timer, script ou `setFocusId` na Home.

### Validação

- `tests.test_home_navegacao`: **5 testes OK** (defaultcontrol 9000, HERO desce
  para 9500 com fallback, grades sobem para 9100/9000, top/height da grade
  inalterados).
- `static-check.py`: 215 XML válidos.

**Pendente em hardware:** percorrer HERO→grades→HERO em 720p, 1080p e 4K com
controle real, incluindo categoria vazia e troca de skin.

---

## 3. Auditoria de anúncios

### Mecanismo existente (auditado, não reescrito)

- Provedor: **Google AdMob**, no app Android que vive no **mesmo APK**
  (`smartedtv.full`), não dentro do binário do Kodi.
- Blocos: abertura `ca-app-pub-2066014755407744/4214378379`; intersticial
  `.../3572039686`.
- Telas nativas: `smartedtv.full.AppOpenActivity` e
  `smartedtv.full.PreRollActivity`.
- Ponte: `StartAndroidActivity(package, intent, dataType, dataURI, flags, extras,
  action, category, className)` — **9 campos**; o `className` é o nono.
- Gatilhos no Kodi: `smart_ads.py` (serviço `service.smarted.bootstrap`).
- VIP: `vip.ativa()` no Python e a checagem equivalente no Java; VIP não pede
  abertura nem pré-roll.
- Encerramento: o controle de fechar/pular é o **controle nativo do anúncio**
  (AdMob). Não existe overlay, botão "pular" falso, diálogo extra nem abertura
  automática de link.

### Causas reais que impediam anúncio

1. **O monitor de pré-roll nunca era iniciado.** Não havia nenhuma chamada a
   `iniciar_monitor()` no `service.py`; o `MonitorPreRoll` existia mas não era
   criado. Sem isso, nenhum canal/filme/série pedia anúncio em nenhum aparelho.
2. **Stream sem metadados** (comum em PVR/projetor): `_chave_conteudo` devolvia
   `'?'`, a chave repetia e o anúncio era descartado como duplicado. Agora há
   **sessão de reprodução** (`MonitorPreRoll.sessao`), incrementada em
   `Started`/`Stopped`/`Ended`; `onAVStarted` reutiliza a sessão do
   `onPlayBackStarted`. O mesmo início pede **um** anúncio; um novo início pede
   de novo, mesmo sem caminho/título.
3. **Aviso "Abrindo anúncio" aparecia mesmo quando o builtin não foi enviado.**
   Agora a notificação só aparece se `tocar_anuncio()` retornou `True`.
4. **Abertura:** agora espera a Home ficar ativa (até 90 s) e desiste se já há
   vídeo ou se o Kodi está encerrando. Nunca cobre a tela de entrada.

### Compatibilidade por dispositivo

| Item | Situação |
|---|---|
| Android 8+ | `minSdk 21` no APK; sem API exclusiva de Android novo na ponte |
| 64 bits / 32 bits | `arm64-v8a` e `armeabi-v7a` preservados no APK |
| Android 11+ (visibilidade de pacote) | componente **explícito** (`className`), não depende de `<queries>` |
| Projetor | mesma activity e mesmo APK; se o aparelho tiver Google Play Services/AdMob, a activity pode preencher |
| Sem inventário | o gatilho retorna sem bloquear; o vídeo segue. Não há tela vazia “simulando” anúncio |
| VIP | não pede anúncio (Python + Java) |
| Falha da activity | o Kodi continua; não há crash nem bloqueio |

O que **não** é possível afirmar sem o aparelho: que exista inventário AdMob para
o perfil do projetor, que o Android 8 aceite a activity na prática e que o
controle de pular do anúncio seja alcançável em todo controle remoto. O código
das activities nativas **não está neste repositório**; esta rodada corrigiu os
gatilhos e a ponte no Kodi, não o SDK.

### Validação

- `tests.test_ads_compatibilidade`: **4 testes OK** — stream sem metadados pede
  um anúncio por sessão; VIP não pede; aviso só após builtin; `onPlayBackStarted`
  + `onAVStarted` não duplicam.
- Teste de serviço: `iniciar_monitor(log)` e `abertura_depois_do_boot` presentes.
- `smart_ads.py`/`service.py` conferidos byte a byte no APK pelo pipeline.

**Pendente em hardware:** ver anúncio real preencher no projetor Android 11 e
em um Android 8; medir tempo até “pular” e alcançar o botão com D-pad.

---

## 4. Saída limpa e reabertura sem tela preta

### Mudanças

- Menu Energia (`skin.novatv/DialogButtonMenu.xml`, o XML que o Kodi abre em
  `ActivateWindow(ShutdownMenu)`, e o equivalente `ShutdownMenu.xml`), item 3504:
  - era `Quit` com `visible = System.ShowExitButton` (podia nem aparecer);
  - agora **“Sair do SMARTEDTV”**, sempre visível, chama
    `RunScript(script.smartedtv.welcome,sair)`.
- A tela de entrada reconhece `sair`:

  1. `Dialog.Close(all,true)` fecha diálogos/janelas abertas;
  2. para a reprodução em andamento (`Player().stop()`);
  3. limpa as marcas `voltar`, `aberta`, `saiu`, `home`;
  4. espera 250 ms para o Kodi processar;
  5. executa **`Quit` nativo**. O Android encerra o processo pela via normal.

- **Não** usa `Kill`, `Shutdown` nem mata outro app.
- No próximo boot, o serviço limpa marcas antigas
  (`limpar_estado_interface`) e o `Startup.xml` abre a tela de entrada de novo.
  Não há `ReloadSkin()` nessa saída; o `RestartApp` continua separado, como
  “Reiniciar aplicativo”, e não é o caminho normal de sair.

### Validação

- `tests.test_saida_limpa`: **2 testes OK** (menu aponta para `RunScript(...,sair)`;
  a função usa `Dialog.Close(all,true)` + `Quit`, sem Kill/Shutdown).
- `CicloDeVidaTest`: cobre boot, tela de entrada, Home e retorno.

**Pendente em hardware:** ciclo abrir → navegar → VIP → anúncio → Home → sair →
reabrir, inclusive sair durante rede/reprodução/carregamento. Sem aparelho físico
nesta sessão, não há prova visual de ausência de tela preta no relançamento.

---

## 5. Resultados da validação

| Verificação | Resultado |
|---|---|
| `static-check.py` | 215 XML, 66 scripts — OK |
| `auditar-responsivo.py --falhar` | 2 layouts / 116 controles / 720p, 1080p, 4K — OK |
| `auditar-tela-entrada.py --falhar` | OK |
| `CicloDeVidaTest` | 23 OK |
| `TVBoxStickTest` | 3 OK |
| `PerformanceTest` | 11 OK |
| `test_menu_brazuca_bingie` | 14 OK |
| `test_home_navegacao` | 5 OK |
| `test_ads_compatibilidade` | 4 OK |
| `test_saida_limpa` | 2 OK (confere `DialogButtonMenu.xml` e `ShutdownMenu.xml`) |
| `test_atualizar_apk` | 1 OK (XMLs de skin não somem do APK) |
| Pipeline `build-v17-responsivo.yml` | execução **44154344425**, success (ver seção 6) |

---

## 6. Build e APK

Pipeline rápido existente, sem compilar Kodi e sem trocar o APK base:

- base: release `v1.0.86-tela-inicial-v16`
  (`SMARTEDTV-atual-com-tela-inicial-v16-universal.apk`);
- `tools/kodi/atualizar-apk-v17.py` troca tela, serviço, **smart_ads.py,
  service.py, Home.xml, DialogButtonMenu.xml e ShutdownMenu.xml** e mantém as
  duas ABIs. `ShutdownMenu.xml` só é trocado se existir na base; o menu real do
  skin é `DialogButtonMenu.xml`;
- assinatura com a mesma chave (`dropbox/smarted-tv-test.jks`);
- release `v1.0.87-responsivo-v17`.

**Execução:** [44154344425](https://github.com/msmacrosmart-cpu/KODE/actions/runs/44154344425) — `success` (todos os passos, inclusive assinatura e release)

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.87-responsivo-v17/SMARTEDTV-atual-v17-responsivo-universal.apk

**Tamanho / SHA-256:** 285.488.387 bytes / `a90b324c57dd125a51043df7cb8d61a0ca8fa74ded9c7d6792db7cc7184bc885`

---

## 7. Dispositivos e arquiteturas realmente validados

**Nesta rodada não houve teste em aparelho físico.** Foram feitos:

- simulação de boot e de foco (stub do Kodi);
- testes unitários e auditorias estáticas;
- validação do APK gerado no CI (ABIs, arquivos, assinatura).

O **único** aparelho físico associado a esta versão é o projetor Android 11 do
relato anterior, no qual a v17 foi instalada; esta rodada **não** executou nele
o ciclo de anúncio/saída. Android 8, TV box, Smart TV e controle D-pad real
seguem **pendentes de teste físico**. Arquiteturas presentes no APK:
`arm64-v8a` e `armeabi-v7a` (as duas conferidas no pipeline). Não foi testado
`x86_64` (emulador), nem Android TV/Google TV específico.
