# Tela de entrada do SMARTEDTV — a primeira interface do app

Este documento descreve **o que foi entregue** e **por que funciona**: a tela do
pacote `smartedtv-src` (Dropbox) é a primeira coisa que o usuário vê ao abrir o
aplicativo, e a Home só é carregada quando ele conclui a tela.

A tela é **sempre horizontal (16:9, 1920×1080)**. O pacote traz também um
layout retrato para celular em pé; essa parte do CSS não é traduzida, porque o
app roda deitado (TV/Android TV) — o seletor “Celular” do pacote é apenas
visual.

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

1. **+31 arquivos** em `assets/addons/script.smartedtv.welcome/` —
   `addon.xml`, `resources/__init__.py`, o `default.py` (único arquivo de lógica:
   liga os botões ao app), o layout `DialogWelcome.xml` (1920×1080, horizontal) e
   as 27 texturas do pacote. A tela é **gerada** do próprio pacote por
   `tools/kodi/gerar-tela-entrada.py`, que lê `css/styles.css` (cores, raios,
   gradientes, `rem`/`vw`/`vh`/`clamp`) e desenha fundo, cartões de vidro,
   botões, pílulas de plano, placa do QR e logo com os mesmos valores. Os dois
   QR Codes (`qr_checkout.png`, `qr_apk.png`) são cópia **byte a byte** de
   `assets/qr-checkout.png` e `assets/qr-apk.png` do pacote.
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
3. **`xml/Font.xml`** das skins — declaradas as fontes `wfNN` do layout (o
   número é a altura em px medida do CSS: `wf11`, `wf13`, `wf15`, `wf17`,
   `wf18`, `wf21`, `wf22`, `wf26`, `wf33`, `wf42`), que as skins do app não
   tinham. Sem elas `GUIFontManager::GetFont` cai em `font13` e a tela fica
   fora de escala. A lista é lida do próprio `DialogWelcome.xml` pelo injetor.
4. **`assets/system/addon-manifest.xml`** — `<addon optional="true">script.smartedtv.welcome</addon>`,
   a mesma forma dos outros addons do app. É o que faz a linha nova do banco de
   addons nascer habilitada, condição para o `RunScript(script.smartedtv.welcome)`
   do `Startup.xml` resolver.

Nada mais: mesma skin, mesma versão (`1.0.83`), mesmo motor, mesma chave de
assinatura, perfil semeado intacto (2731 arquivos com SHA-256 conferido),
`service.smarted.bootstrap` sem uma linha alterada.

## 3. O que a tela faz

`kodi/addons/script.smartedtv.welcome/default.py` (`WelcomeDialog`) mantém a
janela do pacote viva no lugar da Home e liga cada controle ao fluxo que **já
existe** no app:

| controle | ação | implementação reutilizada |
|---|---|---|
| 311 (Ativar) + 310 (campo) | valida o código de ativação no servidor | `service.smarted.bootstrap/vip.py` → `validar()` (rotas `/api/validar`, `/api/codigos/validar`, `/functions/v1/validar-codigo`, …) gravando `vip.json` |
| 120 (Abrir checkout) | abre a compra do plano sem anúncios | `vip.abrir_checkout()` → `https://pay.cakto.com.br/nkvbegd_1323120` (o mesmo destino do QR `qr_checkout.png`) |
| 121 (Compartilhar link) | compartilha o app | `vip.compartilhar()` (ponte `smartedtv.full.CompartilharActivity`) |
| 122 (Baixar APK) | abre o download do app | `vip.abrir_url(vip.APK)` — o link que o próprio módulo VIP usa |
| 123 (ATUALIZAR APLICATIVO) | abre a checagem de versão (OTA) | `vip.procurar_atualizacao()` (ponte `smartedtv.full.AtualizaActivity`); sem essa ponte, cai no download do APK |
| 140/141 (10 min / 1 mês) | escolhe o plano que acompanha o código | o plano é só rótulo: quem decide validade é o servidor de ativação |
| 312 → 905/906 | confirma "continuar com anúncios" | fecha o modal e libera a Home (versão com anúncios, como hoje) |
| Voltar / menu anterior | volta do modal ou conclui a tela | `ReplaceWindow($INFO[System.StartupWindow])` |
| 130/131 (Android TV / Celular) | seletor visual do pacote | a tela é fixa em 16:9 (não há layout retrato): só registrado no log |

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

## 4b. Tipografia: a regra que o build não deixa quebrar

O layout nasceu de um HTML/CSS e o Kodi **não** tem layout automático: cada
texto é uma caixa fixa em 1080p e o que não cabe é cortado em silêncio. Por isso
todo texto passa por medição com a fonte real:

- a altura de cada `<label>` vem de `altura_linha()` (ascendente + descendente da
  Noto Sans naquele tamanho), não de um multiplicador estimado — é o que evita
  cortar "ã", "ç", "J", "g" e "p";
- onde o texto precisa quebrar linha há **uma `<label>` por linha**, medida, em
  vez de `[CR]` (o `[CR]` só quebra dentro de `<textbox>`);
- a mensagem do servidor no diálogo de status é `<textbox>`: o texto é dinâmico
  e pode ser longo, então quebra sozinho e corta com "..." dentro da caixa;
- botão com ícone tem folga simétrica dos dois lados (`texto + 2×(ícone+folga)`),
  porque o Kodi centraliza o rótulo no botão;
- todo botão precisa de textura de foco diferente da normal (D-pad sem realce =
  usuário não sabe onde está).

O `tools/kodi/auditar-tela-entrada.py` mede isso (37 textos no total) e roda na
CI como passo bloqueante; há também testes em `tests/test_tela_entrada.py`.

## 5. Como conferir

```bash
# 1. XML + Python de todo o repositório
python3 tools/kodi/static-check.py

# 2. testes (fidelidade ao pacote, Startup antes da Home, fluxos dos botões)
python3 -m unittest tests.test_tela_entrada tests.test_injetor_tela_entrada

# 3. injetar num APK limpo e simular o boot
python3 tools/kodi/injetar-tela-entrada.py --apk atual.apk --saida bruto.apk
python3 tools/kodi/simular-boot-tela-entrada.py --apk bruto.apk

# 4. auditoria tipográfica: mede CADA texto com a fonte real no px do Kodi e
#    reprova estouro, corte de acento/descendente, encosto em ícone/borda,
#    glifo ausente (tofu) e botão sem realce de foco
python3 tools/kodi/auditar-tela-entrada.py          # relatório
python3 tools/kodi/auditar-tela-entrada.py --falhar # sai 1 (usado na CI)

# 5. prova visual a partir do próprio XML da tela
python3 tools/kodi/renderizar-tela-entrada.py --saida prova.png
python3 tools/kodi/renderizar-tela-entrada.py --dialogo ads --saida dialogo.png
python3 tools/kodi/renderizar-tela-entrada.py --dialogo status --saida status.png

# 6. regerar a tela a partir do pacote (se o pacote mudar)
python3 tools/kodi/gerar-tela-entrada.py --origem build_test/src_novo/smartedtv
```

O workflow `.github/workflows/build-atual-com-tela.yml` faz tudo isso e publica
o APK assinado na tag `v1.0.83-tela-inicial-v5`, e reprova o build se a
auditoria tipográfica ou o mapa de botões falharem.

## 6. Limitações declaradas

- **Não houve execução em Kodi real**: este ambiente não tem Kodi, emulador
  Android nem dispositivo. O que foi verificado é: código-fonte do Kodi 21.3
  (semântica de `Startup.xml`, `onload`, `RunScript`, `AlarmClock`,
  `SyncInstalled`), o APK gerado (conteúdo, fontes, manifest, perfil intacto,
  assinatura) e uma simulação com stubs do ciclo de vida da janela.
- A prova visual (`tela-entrada-prova.png`) é desenhada a partir do
  `DialogWelcome.xml` + texturas do addon; não é captura de tela de um aparelho.
- A tradução HTML/CSS → XML/texturas é fiel nas cores (os tokens `--ink`,
  `--txt`, `--mut` do CSS são conferidos por teste), nos raios, nos gradientes e
  na geometria (box model de 1920×1080), mas não é um motor de layout CSS: o
  texto é posicionado pelo box model calculado, como o Kodi exige.
- O `default.py` é o único arquivo de lógica; todo o visual vem do pacote.

## 7. Resultado deste build

- Release: `v1.0.83-tela-inicial-v5`
- APK: `SMARTEDTV-atual-com-tela-inicial-v5.apk`, 249.861.331 bytes,
  SHA-256 `ce6c323926ac7554f28f07cc39d1c73430625812b6fd235b36086ae7b7edbd8c`
- Assinatura: `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`
  (a mesma do app; v1/v2/v3 verificados pelo `apksigner`)
- Delta sobre o APK atual: +33 arquivos (o addon da tela), 0 removidos e 7
  arquivos alterados (`Startup.xml` e `Font.xml` das 3 skins +
  `assets/system/addon-manifest.xml`).
- Conferido no arquivo final: `Startup.xml` das 3 skins com 2 `onload` e um único
  `ReplaceWindow` (o do seguro); addon registrado como
  `<addon optional="true">`; 2731 arquivos do perfil semeado intactos;
  `service.smarted.bootstrap` sem alteração.
- Workflow `43967218564` (todos os passos verdes), incluindo auditoria
  tipográfica, mapa de botões, "conferir que nada mais mudou", a simulação de
  boot e a assinatura.
- Conferido no arquivo publicado: os 31 arquivos da tela dentro do APK são
  idênticos, byte a byte, aos do repositório; `Font.xml` das skins declara
  `wf13 wf15 wf17 wf18 wf21 wf22 wf26 wf33 wf42`; o certificado é o mesmo do APK
  base (`855de171…0951a`), e os digests do `MANIFEST.MF` conferem.
