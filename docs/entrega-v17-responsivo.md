# SMARTEDTV 1.0.87 (v17) — responsivo 720p/1080p/4K, tela preta, D-pad e projetor

Pacote universal **arm64-v8a + armeabi-v7a**, Android 8+, mesma assinatura da
v16 (`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`).
Não houve recompilação do Kodi: o pipeline rápido parte do APK universal da
v16 e troca apenas a tela de entrada e o serviço SMARTEDTV.

## O que mudou

### 1. Tela preta depois do carregamento

**Causa raiz:** o `service.smarted.bootstrap` chamava `ReloadSkin()` no meio do
boot, ao mesmo tempo em que a tela de entrada abria a Home. O reload derrubava
a janela que estava sendo montada e o Kodi ficava sem janela ativa (preto) até
um toque/reabertura. Havia ainda dois donos da troca para a Home
(`onAction`/`_sair` e o vigia), cada um disparando `ActivateWindow`/`ReplaceWindow`.

**Correção:**
- `ReloadSkin()` removido do boot (`menu_smarted.py`). O menu é atualizado por
  `Skin.SetString` (sem recarregar a skin inteira).
- Um único dono da Home: `ActivateWindow(Home)` (o `ActivateWindow(Home,return)`
  antigo passava `return` como caminho e não é a forma correta), com
  `ReplaceWindow(Home)` só como segunda tentativa.
- `_sair()` marca `smartedtv.welcome.home=abrindo` antes de fechar; o vigia
  espera **6 s** por essa troca e só assume se ela travar. Sem comandos
  concorrentes, sem `RestartApp`, sem fechar o app.
- A tela de entrada continua sendo aberta pelo `Startup.xml` das skins
  (`AlarmClock` + `RunScript(...,seguro=1)`), não pela Home.

### 2. D-pad/foco perdido depois da tela 312

**Causa raiz:** o foco era pedido no mesmo quadro em que o diálogo de anúncios
acabava de ficar visível; o Kodi recusava o foco no controle ainda invisível e
o D-pad ficava sem destino até um toque na tela. Os botões 905/906/955 também
não tinham navegação explícita e o Kodi procurava controles atrás do overlay.

**Correção:**
- `_focar()` agenda o foco, espera o quadro e confirma por `getFocusId()`
  (até 5 tentativas). Em thread (validação VIP) usa o builtin `SetFocus`, que
  entra na fila da interface, em vez de `setFocusId` direto.
- `_garantir_foco()` roda antes de cada seta/OK: se o foco caiu, devolve para
  905/906 no anúncio, 955 no status ou para o último botão válido da tela.
- Ao fechar o diálogo, o foco volta para 312 (ou para o botão que abriu),
  nunca para um controle invisível.
- `905`, `906` e `955` têm `onleft/onright/onup/ondown` explícitos nos dois XMLs.

### 3. Responsividade 1280×720, 1920×1080 e 3840×2160

Um único desenho de referência em **1920×1080** (`DialogWelcome.xml` e a
variante `DialogWelcomeTV.xml` com área segura de overscan), usando os
mecanismos nativos do Kodi: o skin é escalado por resolução, coordenadas
proporcionais, grupos e `include`s; não há uma interface por resolução. Fontes
`wfNN` já existentes são escaladas pelo próprio Kodi.

- Barra inferior corrigida: os cartões terminam em y=891 e a barra começa em
  y=891 (altura 109), sem sobrepor os botões 123/120/121/122. Textos da barra
  em y=903/905/940.
- QR codes com `aspectratio="keep"` (não esticam em tela larga/estreita).
- Variante TV/box/projetor (overscan) escolhida por resolução **e** nome do
  aparelho; aceita 16:9, 16:10 e 4:3 de projetores antigos, e continua
  rejeitando celulares (18:9+).
- Auditoria estática nas três resoluções: nada fora de 1920×1080, QR quadrado,
  botões com pelo menos 36 px no 720p, 310/311/312 dentro da tela e barra sem
  sobreposição. Provas renderizadas em 720p/1080p/4K e diálogos de anúncio/status.

### 4. Canais sem imagem no projetor Android

**Causa raiz:** o boot forçava `videoplayer.usemediacodecsurface=true` em todos
os aparelhos. Em projetores Android o caminho MediaCodec **Surface** entrega
áudio e nenhum quadro (preto); é o mesmo sintoma relatado nos fóruns do Kodi e
a recomendação dos desenvolvedores é desligar Surface nesses aparelhos.

**Correção:** perfil de vídeo pelo `System.FriendlyName`:
- TV/box/stick: `usemediacodecsurface=true`, `usemediacodec=true` (inalterado).
- Projetor (projetor/projector, XGIMI, Wanbo, Byintek, Magcubic, Salange, Yaber,
  Vankyo, Nebula/Anker, BenQ, Epson, ViewSonic, Optoma, Vivitek, DLP, pico…):
  `usemediacodecsurface=false`, `usemediacodec=true` e
  `adjustrefreshrate=0` (evita renegociar HDMI ao abrir o canal).
- Tudo por JSON-RPC, com leitura de volta, sem derrubar o boot se o aparelho
  recusar uma opção. Nada de “desligar tudo” às cegas: TVs e boxes mantêm o
  caminho rápido.

## Testes executados neste ambiente

- `tools/kodi/static-check.py`: **215 XML válidos, 66 scripts** compilados.
- `tools/kodi/auditar-responsivo.py --falhar`: **OK** em 1280×720, 1920×1080 e
  3840×2160 (116 controles, QR quadrado, botões ≥36 px, barra sem sobreposição).
- `tools/kodi/auditar-tela-entrada.py --falhar` e `--layout DialogWelcomeTV.xml`:
  **OK**, 32 textos medidos com a fonte real em cada layout.
- `tests.test_tela_entrada.CicloDeVidaTest` + `TVBoxStickTest`: **24 OK**
  (foco 905/955, retorno ao 312, navegação explícita, 4:3/16:10/4K).
- `tests.test_favourites_bootstrap.PerformanceTest` +
  `tests.test_menu_brazuca_bingie`: **24 OK** (perfil de projetor, TV mantém
  Surface, boot sem `ReloadSkin`).
- Simulação de boot do APK no workflow (script + Startup + banco + foco).
- Provas visuais geradas pelo renderizador em 720p/1080p/4K e diálogos.

## O que NÃO foi testado

Não há TV, box ou projetor físico neste ambiente. Não foi possível confirmar
em hardware real o brilho/imagem do canal no projetor, o comportamento do
controle remoto de cada fabricante nem a taxa de quadros. O diagnóstico de
Surface é baseado no código do boot, nos fóruns oficiais do Kodi e no perfil
por nome; o APK entrega o fallback documentado, mas a confirmação final precisa
ser feita no projetor do usuário (relatório/log do Kodi).

## Arquivos

- APK: `SMARTEDTV-atual-v17-responsivo-universal.apk`
- SHA-256: publicado junto do APK na release `v1.0.87-responsivo-v17`.
- Código: `1.0.87`, versionCode `2103073`.
- Workflow: `.github/workflows/build-v17-responsivo.yml`.
- Ferramenta de atualização: `tools/kodi/atualizar-apk-v17.py`.
