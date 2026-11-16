# Tela de entrada do SMARTEDTV — a primeira interface do app

Este documento descreve **o que foi entregue** e **por que funciona**: a tela do
ZIP (`SMARTEDTV_Kodi_Omega_Welcome.zip`) é a primeira coisa que o usuário vê ao
abrir o aplicativo, e a Home só é carregada quando ele conclui a tela.

O desenho anterior — abrir a tela por cima de uma Home já carregada — foi
descartado: o serviço (`service.smarted.bootstrap`) só começa **depois** da Home,
então nenhuma janela aberta por ele é a primeira interface do app.

---

## 1. Onde a tela entra no boot do Kodi 21.3 (Omega)

Trechos do código do Kodi (tag `21.3-Omega`) usados como base:

| arquivo | o que ele faz |
|---|---|
| `xbmc/application/Application.cpp` (`CApplication::Initialize`) | carrega a skin, ativa `WINDOW_SPLASH` e depois ativa `g_SkinInfo->GetFirstWindow()` |
| `xbmc/addons/Skin.cpp` (`CSkinInfo::GetFirstWindow`) | se a skin tem `Startup.xml`, devolve `WINDOW_STARTUP_ANIM` (12999) em vez da janela configurada (a Home, 10000) |
| `xbmc/windows/GUIWindowStartup.cpp` | essa janela é `CGUIWindow(WINDOW_STARTUP_ANIM, "Startup.xml")`; o `GUI_MSG_UI_READY` só é enviado quando ela é desativada |
| `xbmc/guilib/GUIWindow.cpp` + `xbmc/guilib/GUIControlFactory.cpp` | cada tag `<onload>` do XML vira uma ação de verdade; várias tags são **acumuladas** na ordem em que aparecem |
| `xbmc/interfaces/builtins/AddonBuiltins.cpp` (`RunScript`) | resolve o argumento como **id de addon habilitado** (o caminho absoluto é só o plano B) |
| `xbmc/addons/AddonDatabase.cpp` (`SyncInstalled`) | toda linha **nova** do banco de addons nasce com `enabled=1` quando o id está no `addon-manifest.xml` (`system` ou `optional`) |
| `xbmc/addons/AddonManager.cpp` (`Init`) | addon do manifest marcado `<addon>` **obrigatório** que não carregue aborta o Kodi (`LOGFATAL`) — por isso a tela usa `optional="true"`, como os outros addons do app |
| `xbmc/interfaces/builtins/AlarmClock.cpp` e `xbmc/utils/AlarmClock.cpp` | `AlarmClock(nome,comando,HH:MM:SS,silent)` executa o comando no prazo; `CancelAlarm(nome)` cancela |

Ou seja: **as três skins do APK já tinham `xml/Startup.xml`** com
`ReplaceWindow($INFO[System.StartupWindow])` (salto direto para a Home). Esse é
o ponto exato onde a tela entra.

## 2. O que o APK entregue tem de diferente

Delta exato sobre o APK da release `v1.0.83-unificado` (nada mais muda):

1. **+15 arquivos** em `assets/addons/script.smartedtv.welcome/` — os arquivos do
   ZIP, byte a byte (layout `DialogWelcome.xml` 1920×1080, as 10 texturas, os
   dois QR Codes originais, `addon.xml`, `README.txt`) e o `default.py`
   adaptado (único arquivo que não é cópia fiel, porque é ele que liga os
   botões ao app).
2. **`xml/Startup.xml`** das 3 skins (`skin.novatv`, `skin.smartedtv.classic`,
   `skin.estuary`) — o salto direto para a Home é substituído por:

   ```xml
   <onload>AlarmClock(smartedtv_entrada,RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>
   <onload>AlarmClock(smartedtv_entrada_seguro,ReplaceWindow($INFO[System.StartupWindow]),00:00:30,silent)</onload>
   ```

   O primeiro dispara a tela imediatamente (`00:00:00`, no próximo ciclo do
   alarme). O segundo é o **seguro**: se o Python não conseguir abrir a tela em
   30 s, a Home é liberada e o app continua utilizável. A tela cancela esse
   alarme no `onInit` — com a tela no ar, não existe Home por trás nem antes.
3. **`xml/Font.xml`** das skins — declaradas as fontes que o layout do ZIP usa e
   as skins do app não tinham (`font20`, `font22`, `font24`, `font30`; e
   `font16` na `skin.estuary`). Sem elas `GUIFontManager::GetFont` cai em
   `font13` e a tela fica fora de escala.
4. **`assets/system/addon-manifest.xml`** — `<addon optional="true">script.smartedtv.welcome</addon>`,
   a mesma forma dos outros addons do app. É o que faz a linha nova do banco de
   addons nascer habilitada, condição para o `RunScript(script.smartedtv.welcome)`
   do `Startup.xml` resolver.

Nada mais: mesma skin, mesma versão (`1.0.83`), mesmo motor, mesma chave de
assinatura, perfil semeado intacto (2731 arquivos com SHA-256 conferido),
`service.smarted.bootstrap` sem uma linha alterada.

## 3. O que a tela faz

`kodi/addons/script.smartedtv.welcome/default.py` (`WelcomeDialog`) mantém a
janela do ZIP viva no lugar da Home e liga cada controle ao fluxo que **já
existe** no app:

| controle | ação | implementação reutilizada |
|---|---|---|
| 311 (Ativar) + 310 (campo) | valida o código de ativação no servidor | `service.smarted.bootstrap/vip.py` → `validar()` (rotas `/api/validar`, `/api/codigos/validar`, `/functions/v1/validar-codigo`, …) gravando `vip.json` |
| 120 (Abrir checkout) | abre a compra do plano sem anúncios | `vip.abrir_checkout()` → `https://pay.cakto.com.br/nkvbegd_1323120` (o mesmo QR `qr_1.png` da tela) |
| 121 (Compartilhar link) | compartilha o app | `vip.compartilhar()` (ponte `smartedtv.full.CompartilharActivity`) |
| 312 → 905/906 | confirma "continuar com anúncios" | fecha o modal e libera a Home (versão com anúncios, como hoje) |
| Voltar / menu anterior | volta do modal ou conclui a tela | `ReplaceWindow($INFO[System.StartupWindow])` |
| 130/131 (Android TV / Celular) | seletor visual do ZIP | não existe fluxo equivalente no app: apenas registrado no log |

Nenhuma API, endpoint ou credencial nova: o módulo VIP é importado da pasta do
`service.smarted.bootstrap` que já vem no APK, e o "ir para a Home" usa o mesmo
comando que o `Startup.xml` original usava.

## 4. Robustez: o app nunca fica preso

- `onInit` da tela → `CancelAlarm(smartedtv_entrada_seguro,silent)` (a tela
  assumiu).
- `abrir_tela_entrada()` sempre termina em `ReplaceWindow(...)`: se a pasta da
  tela não existir, se a janela não montar ou se `doModal()` falhar, a Home abre
  igual e o motivo vai para o log.
- Se o Python nem iniciar, o seguro de 30 s do `Startup.xml` abre a Home.

## 5. Como conferir

```bash
# 1. XML + Python de todo o repositório
python3 tools/kodi/static-check.py

# 2. testes (fidelidade ao ZIP, Startup antes da Home, fluxos dos botões)
python3 -m unittest tests.test_tela_entrada tests.test_injetor_tela_entrada

# 3. injetar num APK limpo e simular o boot
python3 tools/kodi/injetar-tela-entrada.py --apk atual.apk --saida bruto.apk
python3 tools/kodi/simular-boot-tela-entrada.py --apk bruto.apk

# 4. prova visual a partir do próprio XML do ZIP
python3 tools/kodi/renderizar-tela-entrada.py --saida prova.png
```

O workflow `.github/workflows/build-atual-com-tela.yml` faz tudo isso e publica
o APK assinado na tag `v1.0.83-tela-inicial-v3`.

## 6. Limitações declaradas

- **Não houve execução em Kodi real**: este ambiente não tem Kodi, emulador
  Android nem dispositivo. O que foi verificado é: código-fonte do Kodi 21.3
  (semântica de `Startup.xml`, `onload`, `RunScript`, `AlarmClock`,
  `SyncInstalled`), o APK gerado (conteúdo, fontes, manifest, perfil intacto,
  assinatura) e uma simulação com stubs do ciclo de vida da janela.
- A prova visual (`tela-entrada-prova.png`) é desenhada a partir do
  `DialogWelcome.xml` + texturas do ZIP; não é captura de tela de um aparelho.
- O `default.py` do ZIP é o único arquivo adaptado — necessário para ligar os
  botões ao app; todo o resto do visual é cópia fiel (SHA-256 conferido).

## 7. Resultado deste build

- Release: `v1.0.83-tela-inicial-v3`
- APK: `SMARTEDTV-atual-com-tela-inicial-v3.apk`, 249.809.500 bytes,
  SHA-256 `e8adc2b5fb3e579bcb63dee49613598431e22d7ac083a3366ad15104ba2e1715`
- Assinatura: `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`
  (a mesma do app; v1/v2/v3 verificados pelo `apksigner`)
- Delta sobre o APK atual: +15 arquivos (o addon do ZIP), 0 removidos e 7
  arquivos alterados (`Startup.xml` e `Font.xml` das 3 skins +
  `assets/system/addon-manifest.xml`).
- Conferido no arquivo final: `Startup.xml` das 3 skins com 2 `onload` e um único
  `ReplaceWindow` (o do seguro); addon registrado como
  `<addon optional="true">`; 2731 arquivos do perfil semeado intactos;
  `service.smarted.bootstrap` sem alteração.
- Workflow `43920447527` (todos os passos verdes), incluindo os passos
  "conferir que nada mais mudou", "assinar com a mesma chave" e a simulação de
  boot.
