# SMARTEDTV 1.0.88 (v18) — reabertura, barra VIP, área segura e addons

**Build:** `44173079531` (concluído em 2026-11-17) · **Commit do APK:** `c60c898` ·
**Tag:** `v1.0.88-reabertura-v18` · **Versão:** 1.0.88 / versionCode 2103074.

- APK: https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.88-reabertura-v18/SMARTEDTV-atual-v18-reabertura-universal.apk
- SHA-256: `b09cc6cfd7123a6a94163f92b1c85b0fb5907dce7bfbc486ed1ecb373014924e`
- Tamanho: 285.488.380 bytes (≈272 MiB), duas ABIs (`arm64-v8a` e `armeabi-v7a`), mesma assinatura da v16/v17.
- Build local: `tools/kodi/atualizar-apk-v17.py` (pipeline rápido), sem recompilar o Kodi e sem alterar os workflows de infraestrutura.

## 1. Causa apurada (sem mudanças aleatórias)

O defeito de "fechar e abrir de novo → tela preta" tem três caminhos concretos no
código, e os três foram tratados:

1. **Processo/Activity reutilizados pelo Android.** O `Quit` do Kodi é a via
   correta, mas em alguns aparelhos ele devolve o controle antes de o processo
   morrer; o Android mantém a Activity/instância antiga. Ao tocar no ícone, o
   Splash reusa esse processo e o Kodi pode chegar sem janela inicial.
2. **Boot sem janela.** O `Startup.xml` antigo abria a janela de startup e
   `ReplaceWindow($INFO[System.StartupWindow])`; depois que a janela 12999 saía de
   cena não havia Home nem tela de entrada. O `Startup.xml` já foi corrigido nas
   versões anteriores; nesta rodada foi acrescentado um **vigia de interface** e
   um **alarme de Home** que só é cancelado quando a tela realmente desenha.
3. **Addon em estado inválido.** O `addon.xml` de
   `service.smarted.bootstrap` declarava `<?xml version="1.1"?>` (o carregador
   de addons do Kodi trabalha com XML 1.0) e tinha **duas extensões
   `xbmc.python.script`** (`check.py` e `vip.py`). Isso produz erro de addon no
   boot e pode deixar o `RunScript` da tela sem destino. O arquivo foi
   normalizado para XML 1.0, a extensão duplicada de `vip.py` foi removida e
   `check.py`/`addon.xml` passaram a ser incluídos no APK rápido.

**Limite da apuração:** não houve acesso ao `kodi.log`/`logcat` do aparelho do
usuário nesta sessão. A causa acima é a que o pacote e o código comprovam; a
confirmação em hardware continua listada como pendência.

## 2. Saída limpa

`script.smartedtv.welcome/default.py` → `sair_do_aplicativo()`:

1. `Dialog.Close(all,true)` fecha diálogos e devolve o foco;
2. `xbmc.Player().stop()` para reprodução e libera o player;
3. limpa **somente** marcas temporárias da tela (`saiu`, `home`, `voltar`,
   `saindo`);
4. espera 250 ms para o Kodi processar o stop/close;
5. no Android, inicia um guarda de 15 s; em PC/CI o guarda nem é criado;
6. chama `Quit` nativo.

O guarda (`_soltar_processo_se_quit_travar`) é o **último recurso**: se o
processo ainda existir 15 s depois do `Quit`, encerra **apenas o próprio PID**
com `os._exit(0)`. Nunca usa `os.kill`, `Kill`, `Shutdown`, `RestartApp` nem
toca em outro aplicativo/sistema. Perfil, VIP, favoritos e `addon_data` não são
apagados.

## 3. Cache e dados

- **Preservados:** `userdata/guisettings.xml`, perfil `.kodi`, favoritos,
  `addon_data`, ativação VIP, preferências e arquivos estáticos.
- **Limpos entre ciclos:** apenas propriedades da janela 10000 e estágios
  `.smarted-seed-<uuid>` deixados por um seed interrompido.
- **Nunca limpos no exit:** perfil, banco de addons, VIP, cache de imagens.
- A varredura de seed roda no boot, restrita ao prefixo `.smarted-seed-`, e não
  entra em `.kodi` nem em `addon_data`.
- A validação VIP continua no servidor (`vip.py`); nenhuma licença é inventada
  ou mantida apenas em memória.

## 4. Recuperação automática

- `service.py` inicia a thread `boot-interface` antes do reparo do Brazuca.
  Se em 25 s não houver `Home`/`Startup`/tela, executa
  `RunScript(script.smartedtv.welcome)`; se em mais 12 s ainda não houver janela,
  executa `ActivateWindow(Home)`. Sem apagar perfil/cache.
- `Startup.xml` recebe `AlarmClock(smartedtv_home_seguro,ActivateWindow(Home),00:00:30,silent)`;
  `WelcomeDialog.onInit()` cancela o alarme com
  `CancelAlarm(smartedtv_home_seguro,silent)`. Se o addon da tela estiver
  desabilitado, o usuário não fica preso na tela preta.
- No boot, `enable_addons(CORE_ADDONS)` habilita a tela, o serviço, o plugin e
  o tema de sons antes do `Startup.xml` chamar o `RunScript`.
- O reparo do Brazuca e os anúncios continuam em segundo plano; falha de
  serviço secundário não impede Home/tela.

## 5. Interface

- Barra VIP centralizada e alinhada nas duas variantes (`DialogWelcome.xml` e
  `DialogWelcomeTV.xml`): barra 38,896 → 1882×104; texto em 96/919; campo
  700×57; botões 120×57 e 266×57; divisor removido.
- Área segura de 5% na variante de TV: conteúdo entre x=96 e x=1824, y=60 e
  y=1000; nenhum texto/QR/button encostando na borda.
- Texto do cartão 1 dividido em três linhas na TV ("Ative o VIP com um código" /
  "ou continue gratuitamente" / "com anúncios."), sem reduzir a fonte.
- Cores, tipografia, texturas e QR Codes do pacote preservados.

## 6. Testes executados

| Verificação | Resultado |
|---|---|
| `tools/kodi/static-check.py` | 215 XML válidos, 67 scripts compilados |
| `auditar-responsivo.py --falhar` | 2 layouts, 115 controles, 720p/1080p/4K, QR quadrado, botões ≥36 px |
| `auditar-tela-entrada.py` (default) | 32 textos medidos, sem estouro/colisão/glifo ausente |
| `auditar-tela-entrada.py` (TV) | 33 textos medidos, sem estouro/colisão/glifo ausente |
| `test_tela_entrada.CicloDeVidaTest` + `TVBoxStickTest` | 26 testes OK |
| `test_favourites_bootstrap.PerformanceTest` + `test_menu_brazuca_bingie` | 30 testes OK |
| `test_home_navegacao` + `test_saida_limpa` | 8 testes OK |
| `test_ads_compatibilidade` + `test_atualizar_apk` | 6 testes OK |
| `simular-ciclos-reabertura.py` | 10 ciclos de **simulação de estado** OK (perfil/VIP preservados, estágios temporários removidos) |
| Workflow `build-v17-responsivo` / build 44173079531 | estático, auditorias, testes, boot simulado, versão, assinatura e release: **sucesso** |

As imagens de prova (`tela-720p.png`, `tela-1080p.png`, `tela-4k.png`,
`tela-dialogo-720p.png`, `tela-status-720p.png`) estão anexadas à release.

### O que NÃO foi testado

- **Não houve teste em aparelho físico** (TV Android, TV box, projetor) nesta
  sessão.
- **Não houve instalação do APK v18 em emulador** nesta sessão; o workflow de
  emulador existente compila do código-fonte, não deste APK rápido, e exige
  gatilho próprio.
- Os **10 ciclos reais** (abrir → Home → VIP → anúncios → voltar → SAIR →
  reabrir, incluindo saída no boot/vídeo/diálogo/rede) **ainda precisam ser
  executados em hardware**. O script desta entrega simula apenas o estado; ele
  não substitui essa prova.

## 7. Próximo teste obrigatório (roteiro)

1. Instalar o APK v18 preservando o perfil (não desinstalar).
2. Abrir, esperar a tela e a Home; entrar em VIP e validar um código.
3. Abrir um vídeo com anúncio; voltar; abrir um diálogo; usar rede.
4. Sair pelo menu Energia → Sair do SMARTEDTV.
5. Conferir no `logcat`/`kodi.log`: `saindo do aplicativo`, `Quit() do Kodi`,
   ausência de `FATAL EXCEPTION`, processo `org.xbmc.kodi` encerrado.
6. Reabrir pelo ícone em ≤10 s e depois de alguns minutos; repetir 10 vezes,
   alternando as fases de saída. Registrar screenshot e logs de cada ciclo.
7. Repetir em ARMv7, ARM64, Android TV, box e projetor; declarar apenas o que
   foi realmente executado.

## 8. Arquivos principais alterados

- `kodi/addons/script.smartedtv.welcome/default.py` — guarda de Quit, cancelamento
  do alarme de segurança.
- `kodi/addons/script.smartedtv.welcome/resources/skins/Default/1080i/DialogWelcome.xml`
  e `DialogWelcomeTV.xml` — barra/área segura.
- `kodi/addons/service.smarted.bootstrap/service.py` — vigia de boot, habilitação
  dos addons do app, varredura de estágios de seed.
- `service.smarted.bootstrap/addon.xml` — XML 1.0, sem extensão duplicada,
  versão 1.0.9; tela 1.0.1.
- `tools/kodi/atualizar-apk-v17.py` — `check.py`/`addon.xml` no APK, alarme de
  Home no `Startup.xml`.
- `tools/android/src/.../ProfileDirectoryBootstrap.java` e
  `ProfileDirectorySeed.java` — reset de execução presa e varredura de estágios
  (fonte para builds que recompilam o DEX; **não** entram no APK rápido).
- `tests/*` — regressões de saída, boot, addon e startup.

## 9. Conclusão honesta

O APK v18 corrige os caminhos de código que produzem a tela preta e o erro de
addon, e entrega a barra alinhada. A aceitação final — "sair funciona, processo e
serviços terminam, reabre 10 vezes sem tela preta, sem perder VIP/configurações"
— **só pode ser declarada depois do roteiro físico acima**. Nesta sessão há
evidência de build, auditoria, testes automatizados e simulação; não há
evidência de hardware.
