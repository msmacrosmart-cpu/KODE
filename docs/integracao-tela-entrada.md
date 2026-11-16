# Integração da tela inicial do ZIP — SMARTEDTV / Kodi Omega 21

**Válido para:** build v2 (release `v1.0.83-tela-inicial-v2`), que corrige a
abertura da tela e as 4 fontes que faltavam na skin (detalhes em §5/§7).

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

## 2. Pontos de integração (mínimos, em arquivos que já existiam)

| # | Arquivo | Alteração |
|---|---|---|
| 1 | `kodi/addons/service.smarted.bootstrap/service.py` | 2 linhas: `from tela_entrada import abrir_tela_entrada` e a thread `welcome-entry` (daemon) iniciada no começo de `main()`. Nenhuma outra linha do serviço foi alterada. |
| 1b | `kodi/addons/service.smarted.bootstrap/tela_entrada.py` | **novo módulo** do mesmo serviço: localiza o `default.py` do ZIP, abre a tela e confirma que ela carregou. Reaproveita `log()` do serviço e grava `userdata/smarted-tela-entrada.log`. |
| 2 | `tools/kodi/build-release-apk.py` | `script.smartedtv.welcome` entra em `BRIDGE_ADDONS`, para o addon ir a `assets/addons/` e ser registrado em `assets/system/addon-manifest.xml` (o workflow `build-release-apk.yml` já confere automaticamente todos os diretórios de `kodi/addons/`). |
| 3 | `docs/integracao-tela-entrada.md` + `tests/test_tela_entrada.py` | Este relatório e a validação. |

Nenhuma outra tela, skin, XML de layout, cor, módulo Python ou workflow foi
modificado.

### Fluxo de entrada

```
Kodi inicia → service.smarted.bootstrap (start="startup", já existente)
   └─ thread welcome-entry (daemon, uma vez por boot)
        ├─ espera a Home (janela 10000) ficar ativa
        ├─ localiza  special://xbmc/addons/script.smartedtv.welcome/default.py
        ├─ abre no próprio interpretador do serviço:
        │     importlib → default.py:open_welcome()
        │        └─ WelcomeDialog("DialogWelcome.xml", <addon>, "Default", "1080i")
        │             └─ doModal() → tela 100% idêntica ao ZIP (1920×1080)
        ├─ onInit() marca Window(10000).Property(smartedtv.welcome.ativa) = 1
        ├─ o serviço confere a marca (prova de que a janela abriu mesmo)
        └─ se não confirmar: plano B com RunScript("<caminho do .py>") e nova
           tentativa; no fim, registra o motivo no log e a Home segue normal
```

O diálogo é **modal e independente**: a Home não é apagada nem substituída, só
fica por baixo. Qualquer erro ao abrir é capturado — a tela de entrada nunca
interrompe o aplicativo.

### Por que não `RunScript(script.smartedtv.welcome)`

O primeiro build usava `RunScript(<id do addon>)` e o cliente instalou sem ver a
tela. No código do Kodi Omega 21 (`xbmc/interfaces/builtins/AddonBuiltins.cpp`)
o `RunScript(addonid)` resolve o addon com `OnlyEnabled::CHOICE_YES`, e
`CAddonDatabase::SyncInstalled` só força `enabled=1` para **addons de sistema
obrigatórios** — este addon é `optional="true"` no `addon-manifest.xml`. Num
perfil que o cliente já tinha (o `ProfileDirectorySeed` preserva o `.kodi`
existente), o `Addons33.db` pode ficar sem/desabilitado para o addon novo: o
comando é então ignorado em silêncio e nenhuma janela abre. Por isso a abertura
agora não depende do banco de addons:

1. carrega o `default.py` por caminho e chama `open_welcome()` no próprio
   interpretador do serviço;
2. confirma pelo `onInit` (propriedade na janela 10000) que a tela entrou no ar;
3. se não confirmar, tenta `RunScript("<caminho absoluto do .py>")`;
4. sempre registra `userdata/smarted-tela-entrada.log` com o que aconteceu.

**Navegação:** setas/OK são resolvidas pelo Kodi a partir das coordenadas do XML
(inalteradas); foco inicial `310` (`defaultcontrol always="true"` + `onInit`);
`ACTION_NAV_BACK` / `ACTION_PREVIOUS_MENU` fecham o modal de confirmação e, fora
dele, fecham a janela e devolvem a Home.

### Fontes que faltavam (o layout não ficava 100% formatado)

`DialogWelcome.xml` usa `font10/12/13/14/16/20/22/24/30`. As skins do APK
(`skin.novatv`, `skin.smartedtv.classic`, `skin.estuary`) declaram
`font10/12/13/14/16` e **não** declaram `font20/22/24/30`. O
`GUIFontManager::GetFont` cai em `font13` quando o nome não existe — ou seja,
títulos como “Sua TV, do seu jeito.” e “Sem anúncios”/“Indique e ganhe”
apareceriam no tamanho errado. O injetor acrescenta **apenas esses 4 nomes
novos** no `Font.xml` das skins do projeto (mesmo arquivo de fonte
`NotoSans-Regular.ttf` e mesmo estilo das vizinhas), sem alterar nenhuma fonte
existente e sem tocar em nenhum outro arquivo de skin. Nenhuma outra tela usa
esses nomes.

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

- `python3 tools/kodi/static-check.py` → 213 XML bem formados e 57 scripts
  compilados, incluindo `DialogWelcome.xml`, `addon.xml`, `default.py` e o novo
  `tela_entrada.py`.
- Fidelidade ao ZIP: dos 15 arquivos, **14 são byte a byte idênticos** ao
  `SMARTEDTV_Kodi_Omega_Welcome.zip` (hash do ZIP
  `758b017aaa3b040be0e7a0baa0d49ecbcc168077303fb4493dc03883670c9bc4`); o único
  adaptado é `default.py`, e só nos pontos de integração (caminho da tela,
  sinal de abertura em `onInit`, log e `ActivateWindow(Home)`). Nenhuma linha
  visual foi tocada.
- `python3 tools/kodi/simular-boot-tela-entrada.py --apk <apk>` → simula o boot
  com `xbmc`/`xbmcgui`/`xbmcvfs` falsos: o `default.py` é carregado por caminho,
  `WelcomeDialog` é criado com `("DialogWelcome.xml", <addon>, "Default",
  "1080i")`, `onInit` foca `310`, a marca de abertura é publicada, as 10
  texturas do layout existem e **todas as 9 fontes usadas existem no `Font.xml`
  da skin** (antes faltavam 4).
- `python3 tools/kodi/renderizar-tela-entrada.py` → desenha a tela a partir do
  próprio `DialogWelcome.xml` + `media/` do ZIP (prova visual
  `artifacts/tela-entrada-prova.png`, 1920×1080).
- `tests/test_tela_entrada.py` (17 testes) → fidelidade byte a byte, texturas,
  ciclo de vida do diálogo (`Default/1080i`, foco `310`, modal
  `show_free_dialog`, `Voltar`, `ActivateWindow(Home)`), ações sem fluxo que não
  simulam sucesso, abertura sem depender de `RunScript(addonid)`/`HasAddon`,
  marca de abertura e as fontes que faltavam.
- `tests/test_injetor_tela_entrada.py` (4 testes) → injeta num APK sintético:
  16 arquivos novos (15 do ZIP + `tela_entrada.py`), 5 arquivos adaptados
  (`service.py`, `addon-manifest.xml` e 3 `Font.xml`), nenhuma outra entrada
  alterada, perfil semeado intacto.
- `python3 -m unittest discover -s tests` → **248 testes OK** (11 skip já
  existentes).

## 6. Build do APK final — **sem skin Bingie**

A pedido do usuário, **o APK final não é um rebuild com Bingie**: ele parte do
**APK atual publicado** (release `v1.0.83-unificado`, asset
`SMARTEDTV-atual.apk`) e recebe **apenas** a tela inicial. Nenhuma skin é
baixada, renomeada ou substituída; versão, motor, `classes.dex`, bibliotecas
nativas, perfil semeado e todas as outras entradas ficam byte a byte iguais.

Workflow: `.github/workflows/build-atual-com-tela.yml`. Script:
`tools/kodi/injetar-tela-entrada.py`.

| Passo | Ação |
|---|---|
| 1 | `static-check.py` (XML + Python) |
| 2 | baixa o APK atual da release `v1.0.83-unificado` |
| 3 | diagnóstico: lista addons/skins/perfil do APK antes de mexer |
| 4 | `tools/kodi/setup.sh` (Java 17 + apksigner) |
| 5 | injeta os **15 arquivos** do ZIP em `assets/addons/script.smartedtv.welcome/`, o módulo `tela_entrada.py`, registra o addon no `addon-manifest.xml`, liga a thread `welcome-entry` no `service.py` **que já está no APK** e declara `font20/22/24/30` nos `Font.xml` das skins; em seguida roda `simular-boot-tela-entrada.py` |
| 6 | confere que **exatamente 16 entradas foram adicionadas** e **apenas 5 foram adaptadas**; perfil semeado intacto; `service.py` e `tela_entrada.py` compilam; XML, QR Codes e demais entradas byte a byte iguais |
| 7 | `align-apk.py` + assinatura com a **mesma chave** (`dropbox/smarted-tv-test.jks`, certificado `855de171…`) |
| 7b | `renderizar-tela-entrada.py` gera a prova visual da tela |
| 8 | publica numa release própria (`v1.0.83-tela-inicial-v2`), sem sobrescrever a release atual; sobe o APK, o `.sha256` e a prova visual |
| 9 | publica blocos do APK para reconstrução no workspace |

## 7. Resultado do build (v2)

| Item | Valor |
|---|---|
| Arquivo | `artifacts/SMARTEDTV-atual-com-tela-inicial-v2.apk` |
| Download | `https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.83-tela-inicial-v2/SMARTEDTV-atual-com-tela-inicial-v2.apk` |
| Release | `v1.0.83-tela-inicial-v2` (não substitui `v1.0.83-unificado`) |
| Tamanho | 249.813.698 bytes |
| SHA-256 | `52419b60c2b0ae31382e14778787b63f619f06f4a2094a724ad47ff475d363af` |
| Pacote / versão | `smartedtv.full` · `1.0.83` · versionCode `2103069` (**inalterados**) |
| Assinatura | v1 + v2 + v3 verificados, certificado `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a` (o mesmo do app atual) |
| ZIP | íntegro, 7.897 entradas, 15 arquivos da tela, 2.731 do perfil |

Conferências sobre o APK assinado: 16 arquivos novos (15 do ZIP +
`tela_entrada.py`), 5 arquivos adaptados (`service.py`, `addon-manifest.xml` e os
3 `Font.xml`), `DialogWelcome.xml` e os dois QR Codes idênticos ao ZIP.

**Atenção:** a versão continua a mesma da 1.0.83 (mesma assinatura), então este
APK é uma **reinstalação**, não uma atualização OTA com `versionCode` maior —
foi assim para honrar “manter a última atual”. Para OTA é preciso incrementar
`versionCode` e publicar o `atualizacao.json` correspondente.

### O que mudou em relação ao build anterior (que não mostrou a tela)

| # | Causa provável | Correção aplicada |
|---|---|---|
| 1 | `RunScript(<id>)` só funciona com o addon habilitado no `Addons33.db`; o addon é `optional="true"` e o perfil do cliente já existia | a tela agora é carregada pelo caminho do `default.py` (import + `open_welcome()`) no interpretador do serviço, com `RunScript("<caminho>")` como plano B |
| 2 | o gancho desistia se `System.HasAddon()` fosse falso e não confirmava nada | espera a Home, não usa `HasAddon`, confirma pelo `onInit` (propriedade na janela 10000) e grava `userdata/smarted-tela-entrada.log` |
| 3 | `font20/22/24/30` não existiam nas skins → Kodi caía em `font13` e a tela não ficava 100% formatada | as 4 fontes são declaradas nos `Font.xml` das skins do projeto, sem alterar as existentes |
